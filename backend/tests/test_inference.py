"""Inference pipeline tests -- the part it matters most to get right.

These reproduce training-time preprocessing exactly, so a passing test here
is a guarantee that a live sensor reading gets transformed the same way a
training row was, not just that the code runs.
"""

from __future__ import annotations

from app.ml.inference_milling import score_milling_reading
from app.ml.inference_turbofan import score_turbofan_window
from app.ml.registry import get_registry

from ml import cmapss as C

registry = get_registry()


def test_milling_normal_reading_scores_low_and_normal():
    reading = {
        "air_temp_k": 298.1,
        "process_temp_k": 308.6,
        "rotational_speed_rpm": 1551,
        "torque_nm": 42.8,
        "tool_wear_min": 0,
        "type": "M",
    }
    result = score_milling_reading(reading, registry)
    assert result["status"] == "normal"
    assert result["failure_probability"] < 0.1
    assert result["rul_cycles"] is None


def test_milling_overstrain_reading_scores_critical():
    """High tool wear x torque is exactly the OSF failure mode notebook 02 documents."""
    reading = {
        "air_temp_k": 302.5,
        "process_temp_k": 312.0,
        "rotational_speed_rpm": 1350,
        "torque_nm": 62.0,
        "tool_wear_min": 220,
        "type": "L",
    }
    result = score_milling_reading(reading, registry)
    assert result["status"] == "critical"
    assert result["failure_probability"] > 0.5
    top_driver = result["explanation"]["failure_drivers"][0]["feature"]
    assert top_driver in ("wear_torque", "tool_wear_min", "torque_nm")


def test_milling_explanation_has_shap_attribution_and_anomaly_signals():
    reading = {
        "air_temp_k": 298.1,
        "process_temp_k": 308.6,
        "rotational_speed_rpm": 1551,
        "torque_nm": 42.8,
        "tool_wear_min": 0,
        "type": "M",
    }
    result = score_milling_reading(reading, registry)
    explanation = result["explanation"]
    assert len(explanation["failure_drivers"]) == 5
    assert all({"feature", "shap_value", "pct"} <= d.keys() for d in explanation["failure_drivers"])
    assert len(explanation["anomaly_signals"]) == 3


def test_turbofan_insufficient_history_returns_none_rul():
    result = score_turbofan_window([{"sensor_2": 1.0}] * 5, registry.rul_model)
    assert result["rul_cycles"] is None
    assert "insufficient history" in result["explanation"]["note"]


def test_turbofan_full_window_matches_true_rul_within_tolerance():
    """Sanity-checks the whole chain (features, scaler, model) against a real engine."""
    _, test, rul_truth = C.load_subset("FD001")
    unit = 1
    g = test[test["unit"] == unit].sort_values("cycle")
    readings = g[registry.rul_model.features].to_dict("records")

    result = score_turbofan_window(readings, registry.rul_model)

    assert result["rul_cycles"] is not None
    true_rul = float(rul_truth[unit - 1])
    # Notebook 07's own test RMSE is ~17 cycles; a generous tolerance here
    # catches a broken pipeline, not normal model error.
    assert abs(result["rul_cycles"] - true_rul) < 30


def test_turbofan_status_thresholds():
    from app.ml.inference_turbofan import status_for_rul

    assert status_for_rul(10, rul_cap=125) == "critical"
    assert status_for_rul(35, rul_cap=125) == "warning"
    assert status_for_rul(100, rul_cap=125) == "normal"
    assert status_for_rul(124.5, rul_cap=125) == "normal"  # at cap: no degradation detected
