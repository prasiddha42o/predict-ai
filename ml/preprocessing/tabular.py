"""Tabular preprocessing shared by training and inference.

The PredictAI inference service must transform an incoming sensor payload exactly
the way the training pipeline did. Any divergence -- a different category encoding,
a column in a different order -- produces silently wrong predictions rather than an
error. Both paths therefore call `to_model_matrix` in this file.
"""

from __future__ import annotations

import json

import pandas as pd

from ..data import ENGINEERED_COLS, TREE_FEATURES, TYPE_ORDER, engineer_features


def to_model_matrix(df: pd.DataFrame, features: list[str] = None) -> pd.DataFrame:
    """Build the numeric feature matrix for the tree models.

    Gradient boosting needs no scaling, so the only transform is encoding the
    quality variant ordinally and pinning the column order.
    """
    features = features or TREE_FEATURES
    if any(c in features for c in ENGINEERED_COLS) and "power_w" not in df.columns:
        df = engineer_features(df)
    X = df[features].copy()
    if "type" in X.columns:
        X["type"] = X["type"].map(TYPE_ORDER).astype("int8")
    return X


def save_feature_config(path, features: list[str]) -> None:
    """Persist the exact feature contract next to the model artefact."""
    config = {
        "features": list(features),
        "type_encoding": TYPE_ORDER,
        "engineered": {
            "temp_diff_k": "process_temp_k - air_temp_k",
            "power_w": "torque_nm * rotational_speed_rpm * 2*pi/60",
            "wear_torque": "tool_wear_min * torque_nm",
            "type_ordinal": "type mapped through type_encoding",
        },
    }
    path.write_text(json.dumps(config, indent=2))


def load_feature_config(path) -> dict:
    return json.loads(path.read_text())
