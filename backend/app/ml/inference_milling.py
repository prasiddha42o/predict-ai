"""Inference for AI4I-style "milling machine" readings.

A single sensor snapshot goes through three of the four production models:
the XGBoost classifier (failure probability), the Isolation Forest (anomaly
score), and the autoencoder (anomaly score + per-feature attribution). All
three consume the exact same feature matrix, built by `ml.preprocessing.
tabular.to_model_matrix` -- the same function notebooks 03-06 and 09 trained
against, not a reimplementation of it.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import shap

from app.ml.registry import ModelRegistry
from ml.preprocessing.tabular import to_model_matrix
from ml.training.autoencoder import reconstruction_error


def _shap_contributions(bundle, X: pd.DataFrame) -> list[dict]:
    """Per-feature attribution for one prediction, as signed % of total |impact|.

    Matches the PRD's "Vibration +31%, Temperature +24%..." presentation: each
    feature's share of the decision, signed by whether it pushed the
    prediction up or down.
    """
    explainer = shap.TreeExplainer(bundle.model)
    raw = explainer.shap_values(X)
    values = np.asarray(raw)[0] if np.ndim(raw) == 2 else np.asarray(raw)
    total = float(np.abs(values).sum()) or 1.0
    contributions = [
        {"feature": f, "shap_value": float(v), "pct": round(float(v) / total * 100, 1)}
        for f, v in zip(X.columns, values)
    ]
    return sorted(contributions, key=lambda c: abs(c["pct"]), reverse=True)


def _autoencoder_signals(bundle, X: pd.DataFrame, top_n: int = 3) -> list[str]:
    """The `top_n` features contributing most to the autoencoder's reconstruction error."""
    Z = bundle.scaler.transform(X.to_numpy(dtype=float))
    per_feature = reconstruction_error(bundle.model, Z, per_feature=True)[0]
    order = np.argsort(per_feature)[::-1][:top_n]
    return [X.columns[i] for i in order]


def score_milling_reading(reading: dict, registry: ModelRegistry) -> dict:
    """Score one milling-machine reading against all three AI4I models.

    `reading` has the raw AI4I fields: air_temp_k, process_temp_k,
    rotational_speed_rpm, torque_nm, tool_wear_min, type.
    """
    df = pd.DataFrame([reading])

    fc = registry.failure_classifier
    X_tree = to_model_matrix(df, features=fc.features)
    failure_probability = float(fc.model.predict_proba(X_tree)[0, 1])

    iso = registry.anomaly_detector
    X_iso = to_model_matrix(df, features=iso.features)
    isoforest_score = float(-iso.model.score_samples(X_iso)[0])

    ae = registry.autoencoder
    X_ae = to_model_matrix(df, features=ae.features)
    Z_ae = ae.scaler.transform(X_ae.to_numpy(dtype=float))
    autoencoder_score = float(reconstruction_error(ae.model, Z_ae)[0])

    is_failure_predicted = failure_probability >= fc.threshold
    is_anomalous = isoforest_score > iso.threshold or autoencoder_score > ae.threshold

    if is_failure_predicted:
        status = "critical"
    elif is_anomalous:
        status = "warning"
    else:
        status = "normal"

    explanation = {
        "failure_drivers": _shap_contributions(fc, X_tree)[:5],
        "anomaly_signals": _autoencoder_signals(ae, X_ae),
        "isoforest_score": isoforest_score,
        "isoforest_threshold": iso.threshold,
        "autoencoder_score": autoencoder_score,
        "autoencoder_threshold": ae.threshold,
    }

    return {
        "failure_probability": failure_probability,
        "anomaly_score": isoforest_score,
        "rul_cycles": None,
        "status": status,
        "explanation": explanation,
    }
