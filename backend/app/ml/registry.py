"""Loads every trained model artifact under `models/` once, at process start.

One registry, loaded once, so a request handler never touches disk or
reconstructs a model -- it just asks the registry for whichever bundle it
needs. Same "single source of truth" discipline as `ml/data.py`: if two
request handlers redefined how a model gets loaded, they could silently
diverge on which features, threshold or scaler is actually in use.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

# xgboost MUST be imported before torch. Both bundle their own libomp.dylib on
# macOS; if torch's copy initialises first, constructing an XGBClassifier
# segfaults the process (no Python exception, just SIGSEGV) the moment its
# OpenMP threadpool spins up. Reordering these two imports is the entire fix.
import xgboost as xgb
import torch

import joblib

from app.config import MODELS_DIR
from ml.training.autoencoder import SensorAutoencoder
from ml.training.rul_lstm import RULLSTM


@dataclass
class FailureClassifierBundle:
    model: xgb.XGBClassifier
    features: list[str]
    threshold: float
    explainability: dict[str, Any]


@dataclass
class AnomalyDetectorBundle:
    model: Any  # sklearn IsolationForest
    features: list[str]
    threshold: float


@dataclass
class AutoencoderBundle:
    model: SensorAutoencoder
    scaler: Any  # sklearn StandardScaler
    features: list[str]
    threshold: float


@dataclass
class RulModelBundle:
    model: RULLSTM
    scaler: Any
    features: list[str]
    window: int
    rul_cap: int


@dataclass
class ModelRegistry:
    failure_classifier: FailureClassifierBundle
    anomaly_detector: AnomalyDetectorBundle
    autoencoder: AutoencoderBundle
    rul_model: RulModelBundle


def _load_failure_classifier() -> FailureClassifierBundle:
    d = MODELS_DIR / "failure_classifier"
    model = xgb.XGBClassifier()
    model.load_model(str(d / "model.json"))
    feature_config = json.loads((d / "feature_config.json").read_text())
    meta = json.loads((d / "model_metadata.json").read_text())
    explainability = json.loads((d / "explainability.json").read_text())
    return FailureClassifierBundle(
        model=model,
        features=feature_config["features"],
        threshold=meta["decision_threshold"],
        explainability=explainability,
    )


def _load_anomaly_detector() -> AnomalyDetectorBundle:
    d = MODELS_DIR / "anomaly_detector"
    model = joblib.load(d / "isolation_forest.pkl")
    meta = json.loads((d / "model_metadata.json").read_text())
    return AnomalyDetectorBundle(
        model=model, features=meta["features"], threshold=meta["raw_score_threshold"]
    )


def _load_autoencoder() -> AutoencoderBundle:
    d = MODELS_DIR / "autoencoder"
    checkpoint = torch.load(d / "model.pt", map_location="cpu", weights_only=False)
    model = SensorAutoencoder.from_config(checkpoint["config"])
    model.load_state_dict(checkpoint["state_dict"])
    model.eval()
    scaler = joblib.load(d / "scaler.pkl")
    meta = json.loads((d / "model_metadata.json").read_text())
    return AutoencoderBundle(
        model=model,
        scaler=scaler,
        features=meta["features"],
        threshold=meta["raw_score_threshold"],
    )


def _load_rul_model() -> RulModelBundle:
    d = MODELS_DIR / "rul_model"
    checkpoint = torch.load(d / "model.pt", map_location="cpu", weights_only=False)
    model = RULLSTM.from_config(checkpoint["config"])
    model.load_state_dict(checkpoint["state_dict"])
    model.eval()
    scaler = joblib.load(d / "scaler.pkl")
    meta = json.loads((d / "model_metadata.json").read_text())
    return RulModelBundle(
        model=model,
        scaler=scaler,
        features=meta["features"],
        window=meta["window"],
        rul_cap=meta["rul_cap"],
    )


@lru_cache
def get_registry() -> ModelRegistry:
    """Load (once) and cache every production model artifact.

    `lru_cache` on a zero-arg function is a cheap process-wide singleton --
    the first request pays the load cost (reading 4 model files + 2 scalers
    off disk), every request after that reuses the same in-memory bundle.
    """
    return ModelRegistry(
        failure_classifier=_load_failure_classifier(),
        anomaly_detector=_load_anomaly_detector(),
        autoencoder=_load_autoencoder(),
        rul_model=_load_rul_model(),
    )
