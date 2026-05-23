"""NASA C-MAPSS turbofan degradation data: loading, RUL targets, sequencing.

Companion to `ml/data.py` for the AI4I side of the project. AI4I has no machine
identifier or timestamp, so it cannot support sequence modelling or a
"time until failure" target -- C-MAPSS has both (`unit`, `cycle`) and is where
notebook 07 does the actual RUL regression.

Every function a notebook needs to reproduce the RUL target, the engine-level
split and the windowing lives here, for the same reason `ml/data.py`
centralises the AI4I schema: notebook 08's comparison table is only honest if
nothing that touches this dataset quietly redefines what it's measuring.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

from .paths import CMAPSS_RAW, DATA_PROCESSED

RANDOM_SEED = 42

#: Cap applied to the RUL target. A healthy engine 300 cycles from failure
#: looks identical to one 250 cycles out -- nothing has degraded in either --
#: so asking a regressor to tell them apart is asking it to fit noise. Capping
#: makes the target piecewise-linear: constant while healthy, linear once
#: degradation starts. 125 is the standard value used in the C-MAPSS RUL
#: literature this dataset comes from.
RUL_CAP = 125

OP_COLS = [f"op_setting_{i}" for i in (1, 2, 3)]
SENSOR_COLS = [f"sensor_{i}" for i in range(1, 22)]
COLUMNS = ["unit", "cycle"] + OP_COLS + SENSOR_COLS


def _read_columns(path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Run `python scripts/download_cmapss.py` first."
        )
    df = pd.read_csv(path, sep=r"\s+", header=None, names=COLUMNS)
    df["unit"] = df["unit"].astype(int)
    df["cycle"] = df["cycle"].astype(int)
    return df


def load_subset(subset: str = "FD001") -> tuple[pd.DataFrame, pd.DataFrame, np.ndarray]:
    """Load one C-MAPSS subset: `(train, test, true RUL at test truncation)`."""
    train = _read_columns(CMAPSS_RAW / f"train_{subset}.txt")
    test = _read_columns(CMAPSS_RAW / f"test_{subset}.txt")
    rul_path = CMAPSS_RAW / f"RUL_{subset}.txt"
    rul_truth = pd.read_csv(rul_path, sep=r"\s+", header=None)[0].to_numpy()
    return train, test, rul_truth


def constant_sensors(train: pd.DataFrame, cols: list[str] | None = None) -> list[str]:
    """Operating-setting/sensor columns that never change in the training data.

    FD001 runs at a single operating condition, so `op_setting_3` and several
    sensors never move; leaving them in would divide by a nonzero-but-tiny std
    at scaling time and blow those columns up to huge magnitudes, contributing
    nothing but numerical instability. Checked by range rather than `.std() ==
    0`: a handful of these columns are constant to the exact bit but the
    variance formula's rounding still turns that into ~1e-15, not 0.
    """
    cols = cols or (OP_COLS + SENSOR_COLS)
    return [c for c in cols if train[c].max() == train[c].min()]


def add_train_rul(df: pd.DataFrame, cap: int | None = RUL_CAP) -> pd.DataFrame:
    """Attach the RUL target for training rows: cycles remaining until that engine's last cycle."""
    out = df.copy()
    last_cycle = out.groupby("unit")["cycle"].transform("max")
    rul = last_cycle - out["cycle"]
    out["rul"] = np.minimum(rul, cap) if cap is not None else rul
    return out


def add_test_rul(df: pd.DataFrame, rul_truth, cap: int | None = RUL_CAP) -> pd.DataFrame:
    """Attach the RUL target for test rows, using the supplied truth at truncation.

    Test trajectories are cut short before failure; `rul_truth[u]` is how many
    cycles engine `u` had left *after* its last observed row. RUL at any
    earlier row is that plus however many cycles remain to the last observed
    row of that engine.
    """
    units = sorted(df["unit"].unique())
    truth_by_unit = dict(zip(units, np.asarray(rul_truth)))

    out = df.copy()
    last_cycle = out.groupby("unit")["cycle"].transform("max")
    tail_at_truncation = out["unit"].map(truth_by_unit)
    rul = tail_at_truncation + (last_cycle - out["cycle"])
    out["rul"] = np.minimum(rul, cap) if cap is not None else rul
    return out


def split_units(
    df: pd.DataFrame, val_fraction: float = 0.2, seed: int = RANDOM_SEED
) -> tuple[list[int], list[int]]:
    """Split engine units -- not rows -- into train/validation.

    Windows from the same engine overlap almost completely, so a row-level
    split would put near-duplicates on both sides. See notebook 07 section 5
    for how much that leaks.
    """
    units = sorted(int(u) for u in df["unit"].unique())
    rng = np.random.RandomState(seed)
    shuffled = rng.permutation(units)
    cut = int(round(len(units) * (1 - val_fraction)))
    train_units = sorted(int(u) for u in shuffled[:cut])
    val_units = sorted(int(u) for u in shuffled[cut:])
    return train_units, val_units


def save_split(train_units: list[int], val_units: list[int], subset: str) -> None:
    """Persist the engine-level split so it can be audited or reused outside the notebook."""
    path = DATA_PROCESSED / f"cmapss_{subset.lower()}_split.json"
    path.write_text(
        json.dumps({"train_units": train_units, "val_units": val_units}, indent=2)
    )


def make_sequences(
    df: pd.DataFrame, features: list[str], window: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Slide a `window`-length window (stride 1) over every unit's cycles.

    Returns `(X, y, units)`: `X` is `(n_windows, window, n_features)`, `y` is
    the RUL target at each window's *last* cycle, `units` records which engine
    each window came from -- needed to keep a later train/val split honest.
    """
    Xs, ys, us = [], [], []
    for u, g in df.sort_values("cycle").groupby("unit"):
        feats = g[features].to_numpy(dtype=np.float32)
        rul = g["rul"].to_numpy(dtype=np.float32)
        if len(feats) < window:
            continue
        for end in range(window, len(feats) + 1):
            Xs.append(feats[end - window : end])
            ys.append(rul[end - 1])
            us.append(u)
    if not Xs:
        return (
            np.empty((0, window, len(features)), dtype=np.float32),
            np.empty(0, dtype=np.float32),
            np.empty(0, dtype=int),
        )
    return np.stack(Xs), np.array(ys, dtype=np.float32), np.array(us)


def last_window_per_unit(
    df: pd.DataFrame, features: list[str], window: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """The most recent `window` cycles for each unit -- one sequence per engine.

    Used at test time: a truncated test engine is scored on where it actually
    is, not on every historical window of it. Engines with fewer than `window`
    cycles observed are front-padded by repeating their first row.
    """
    Xs, ys, us = [], [], []
    for u, g in df.sort_values("cycle").groupby("unit"):
        feats = g[features].to_numpy(dtype=np.float32)
        rul = g["rul"].to_numpy(dtype=np.float32)
        if len(feats) < window:
            pad = np.repeat(feats[:1], window - len(feats), axis=0)
            feats = np.concatenate([pad, feats], axis=0)
        Xs.append(feats[-window:])
        ys.append(rul[-1])
        us.append(u)
    return np.stack(Xs), np.array(ys, dtype=np.float32), np.array(us)


def nasa_score(y_true, y_pred) -> float:
    """Official C-MAPSS scoring function: penalises late predictions harder than early ones.

    A late prediction (predicted RUL > actual) means the engine is scheduled
    for maintenance after it would already have failed; an early prediction
    only costs an unnecessarily early service. `d = predicted - actual`.
    """
    d = np.asarray(y_pred, dtype=float) - np.asarray(y_true, dtype=float)
    penalty = np.where(d < 0, np.exp(-d / 13) - 1, np.exp(d / 10) - 1)
    return float(np.sum(penalty))


def regression_metrics(y_true, y_pred) -> dict:
    """RMSE, MAE, the NASA score, and sample count -- the one scoring function every model here goes through."""
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    err = y_pred - y_true
    return {
        "rmse": float(np.sqrt(np.mean(err**2))),
        "mae": float(np.mean(np.abs(err))),
        "nasa_score": nasa_score(y_true, y_pred),
        "n": int(len(y_true)),
    }
