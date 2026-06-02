"""Inference for NASA C-MAPSS-style "turbofan engine" readings.

Unlike the milling models, the RUL model consumes a *sequence*, not a single
snapshot: the last `bundle.window` cycles of one engine. Each reading is a
flat dict keyed by the same feature names in `bundle.features`
(`op_setting_1`, `op_setting_2`, `sensor_2`, `sensor_3`, ...) -- the constant
columns notebook 07 dropped are never part of the contract in the first
place, so there is nothing to filter out here.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import torch

from app.ml.registry import RulModelBundle

#: Below this many cycles remaining, notebook 07's stage analysis found the
#: tightest error (MAE ~2.1) -- close to failure, and close enough to trust.
CRITICAL_RUL_CYCLES = 20

#: The "transition zone" notebook 07 found hardest to call: degradation has
#: started but is not yet obvious (MAE peaks here). Surfaced as a warning,
#: not a number to trust to the cycle.
WARNING_RUL_CYCLES = 50


def status_for_rul(rul_cycles: float, rul_cap: int) -> str:
    if rul_cycles >= rul_cap - 1:
        # At/near the cap: per the model's own known_limits, this means "no
        # degradation detected", not "125 cycles precisely".
        return "normal"
    if rul_cycles < CRITICAL_RUL_CYCLES:
        return "critical"
    if rul_cycles < WARNING_RUL_CYCLES:
        return "warning"
    return "normal"


def score_turbofan_window(readings: list[dict], bundle: RulModelBundle) -> dict:
    """Score the most recent `bundle.window` cycles of one turbofan engine.

    `readings` must be ordered oldest-to-newest. Returns `rul_cycles=None`
    if fewer than `bundle.window` cycles are available -- the LSTM has no
    defined behaviour on a shorter sequence, so "not enough history yet" is
    the honest answer, not a padded guess.
    """
    if len(readings) < bundle.window:
        return {
            "rul_cycles": None,
            "status": "normal",
            "explanation": {
                "note": f"insufficient history: {len(readings)}/{bundle.window} cycles observed"
            },
        }

    window = readings[-bundle.window :]
    raw = pd.DataFrame([{f: r[f] for f in bundle.features} for r in window])
    scaled = bundle.scaler.transform(raw)

    with torch.no_grad():
        x = torch.tensor(scaled, dtype=torch.float32).unsqueeze(0)
        pred = bundle.model(x).item()
    rul_cycles = float(np.clip(pred, 0, bundle.rul_cap))
    status = status_for_rul(rul_cycles, bundle.rul_cap)
    at_cap = rul_cycles >= bundle.rul_cap - 1

    return {
        "rul_cycles": rul_cycles,
        "status": status,
        "explanation": {
            "window_cycles": bundle.window,
            "rul_cap": bundle.rul_cap,
            "note": "no degradation detected (at cap)" if at_cap else None,
        },
    }
