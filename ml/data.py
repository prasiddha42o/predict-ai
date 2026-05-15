"""Dataset contract for the AI4I 2020 predictive maintenance data.

This module is the single source of truth for:
  * column naming
  * which columns are legitimate features vs. label leakage
  * the physics-derived engineered features
  * the frozen train/validation/test split

Every notebook imports from here. If a notebook re-defined its own split or its
own feature list, the model comparison table in notebook 08 would be comparing
models trained on different data, which is the most common way a benchmark
quietly becomes meaningless.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from .paths import CLEAN_PARQUET, RAW_CSV, SPLIT_JSON

RANDOM_SEED = 42

# --------------------------------------------------------------------------- #
# Schema
# --------------------------------------------------------------------------- #

COLUMN_MAP = {
    "UDI": "udi",
    "Product ID": "product_id",
    "Type": "type",
    "Air temperature [K]": "air_temp_k",
    "Process temperature [K]": "process_temp_k",
    "Rotational speed [rpm]": "rotational_speed_rpm",
    "Torque [Nm]": "torque_nm",
    "Tool wear [min]": "tool_wear_min",
    "Machine failure": "machine_failure",
    "TWF": "twf",
    "HDF": "hdf",
    "PWF": "pwf",
    "OSF": "osf",
    "RNF": "rnf",
}

TARGET = "machine_failure"

#: The five per-mode labels. These are recorded *at the same instant* as the
#: target and are components of it. Using them as features would give a model
#: near-perfect scores that collapse the moment it sees live sensor data.
FAILURE_MODES = ["twf", "hdf", "pwf", "osf", "rnf"]

FAILURE_MODE_NAMES = {
    "twf": "Tool Wear Failure",
    "hdf": "Heat Dissipation Failure",
    "pwf": "Power Failure",
    "osf": "Overstrain Failure",
    "rnf": "Random Failure",
}

IDENTIFIER_COLS = ["udi", "product_id"]

#: What a real sensor gateway would actually transmit.
SENSOR_COLS = [
    "air_temp_k",
    "process_temp_k",
    "rotational_speed_rpm",
    "torque_nm",
    "tool_wear_min",
]

CATEGORICAL_COLS = ["type"]

#: Derived in `engineer_features`. Each one corresponds to a quantity that the
#: documented failure modes are actually defined on (see notebook 02).
ENGINEERED_COLS = [
    "temp_diff_k",
    "power_w",
    "wear_torque",
    "type_ordinal",
]

RAW_FEATURES = SENSOR_COLS + CATEGORICAL_COLS

#: Linear models one-hot encode `type`, so they take the three continuous
#: engineered features and leave `type_ordinal` out.
LINEAR_FEATURES = SENSOR_COLS + CATEGORICAL_COLS + [
    "temp_diff_k",
    "power_w",
    "wear_torque",
]

#: Tree models take the category as a single ordinal column instead. Including
#: both `type` and `type_ordinal` would put two identical columns in the matrix,
#: which splits their importance and hides it from permutation-based attribution.
TREE_FEATURES = SENSOR_COLS + ENGINEERED_COLS

#: Product quality variant -> ordinal. L (low) is the cheapest tolerance class,
#: H (high) the tightest, so the ordering carries real information.
TYPE_ORDER = {"L": 0, "M": 1, "H": 2}


# --------------------------------------------------------------------------- #
# Loading
# --------------------------------------------------------------------------- #


def load_raw(path=RAW_CSV) -> pd.DataFrame:
    """Read the raw CSV and apply canonical column names. No other changes."""
    df = pd.read_csv(path)
    missing = set(COLUMN_MAP) - set(df.columns)
    if missing:
        raise ValueError(
            f"Unexpected schema in {path}. Missing columns: {sorted(missing)}"
        )
    return df.rename(columns=COLUMN_MAP)


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add physics-derived features. Pure function: returns a new frame.

    temp_diff_k  Process minus air temperature. Heat dissipation failures are
                 defined on this difference, not on either temperature alone.
    power_w      Mechanical power, torque [Nm] x angular velocity [rad/s].
                 Power failures are defined on this product.
    wear_torque  Tool wear [min] x torque [Nm]. Overstrain failures are defined
                 on this product, with a threshold that varies by quality tier.
    type_ordinal Quality variant as an ordered integer.
    """
    out = df.copy()
    out["temp_diff_k"] = out["process_temp_k"] - out["air_temp_k"]
    out["power_w"] = out["torque_nm"] * out["rotational_speed_rpm"] * 2 * np.pi / 60
    out["wear_torque"] = out["tool_wear_min"] * out["torque_nm"]
    out["type_ordinal"] = out["type"].map(TYPE_ORDER).astype("int8")
    return out


def load_clean(path=CLEAN_PARQUET) -> pd.DataFrame:
    """Load the cleaned + feature-engineered frame written by notebook 01."""
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Run notebooks/01_dataset_analysis.ipynb first."
        )
    return pd.read_parquet(path)


# --------------------------------------------------------------------------- #
# Splitting
# --------------------------------------------------------------------------- #


def make_split(
    df: pd.DataFrame,
    test_size: float = 0.20,
    val_size: float = 0.20,
    seed: int = RANDOM_SEED,
    save: bool = True,
) -> dict[str, list[int]]:
    """Create a stratified train/val/test split keyed on `udi`.

    Stratification matters here: at a 3.4% positive rate, an unstratified 20%
    test split can easily land 20+ failures away from the expected count, which
    is enough to move recall by several points for reasons that have nothing to
    do with the model.

    Returns a dict of udi lists and writes it to data/processed/split_indices.json
    so that every downstream notebook trains and scores on identical rows.
    """
    train_val_udi, test_udi = train_test_split(
        df["udi"].to_numpy(),
        test_size=test_size,
        stratify=df[TARGET],
        random_state=seed,
    )
    tv = df[df["udi"].isin(train_val_udi)]
    train_udi, val_udi = train_test_split(
        tv["udi"].to_numpy(),
        test_size=val_size / (1 - test_size),
        stratify=tv[TARGET],
        random_state=seed,
    )
    split = {
        "train": sorted(int(u) for u in train_udi),
        "val": sorted(int(u) for u in val_udi),
        "test": sorted(int(u) for u in test_udi),
        "seed": seed,
    }
    if save:
        SPLIT_JSON.write_text(json.dumps(split))
    return split


def load_split(path=SPLIT_JSON) -> dict:
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Run notebooks/01_dataset_analysis.ipynb first."
        )
    return json.loads(path.read_text())


def apply_split(df: pd.DataFrame, split: dict | None = None):
    """Return (train_df, val_df, test_df) using the frozen split."""
    split = split or load_split()
    return tuple(
        df[df["udi"].isin(split[part])].reset_index(drop=True)
        for part in ("train", "val", "test")
    )


def xy(df: pd.DataFrame, features: list[str]):
    """Split a frame into (X, y) for a given feature list."""
    return df[features].copy(), df[TARGET].to_numpy()
