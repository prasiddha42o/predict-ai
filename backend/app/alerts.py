"""Alert generation -- section 19 of the PRD: fire when a threshold is crossed.

Alerts fire on *transition*, not on every reading: a machine sitting at 90%
failure probability for an hour should produce one alert a technician can act
on, not one per sensor tick. The rule is simple -- if there is already an
unacknowledged alert of the same (machine, kind), don't create another one.
Acknowledging closes the episode and lets the next crossing raise a fresh one.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Alert, AlertKind, AlertSeverity, HealthStatus, Machine, Prediction

#: Top SHAP-attributed feature -> what a technician should actually go check.
#: Grounded in the failure physics notebook 02 established, not guesses:
#: wear x torque drives overstrain, temp_diff drives heat dissipation, power
#: drives power failure.
_FAILURE_FEATURE_ACTIONS = {
    "wear_torque": "Inspect tool wear and torque load — overstrain risk.",
    "tool_wear_min": "Inspect tool wear and torque load — overstrain risk.",
    "temp_diff_k": "Inspect cooling and heat dissipation system.",
    "air_temp_k": "Inspect cooling and heat dissipation system.",
    "process_temp_k": "Inspect cooling and heat dissipation system.",
    "power_w": "Inspect drive power and rotational speed regulation.",
    "rotational_speed_rpm": "Inspect drive power and rotational speed regulation.",
    "torque_nm": "Inspect drive power and rotational speed regulation.",
    "type_ordinal": "Review product quality-tier tolerances.",
}

_DEFAULT_ACTION = "Inspect machine — contributing signal not conclusive."


def _failure_recommended_action(explanation: dict | None) -> str:
    drivers = (explanation or {}).get("failure_drivers") or []
    if not drivers:
        return _DEFAULT_ACTION
    top_feature = drivers[0]["feature"]
    return _FAILURE_FEATURE_ACTIONS.get(top_feature, _DEFAULT_ACTION)


def _has_open_alert(db: Session, machine_id: int, kind: AlertKind) -> bool:
    return (
        db.scalar(
            select(Alert.id)
            .where(
                Alert.machine_id == machine_id,
                Alert.kind == kind,
                Alert.acknowledged.is_(False),
            )
            .limit(1)
        )
        is not None
    )


def maybe_create_alerts(db: Session, machine: Machine, prediction: Prediction) -> list[Alert]:
    """Create any alerts this prediction newly warrants. Does not commit."""
    created: list[Alert] = []

    if prediction.status == HealthStatus.NORMAL:
        return created

    severity = (
        AlertSeverity.CRITICAL if prediction.status == HealthStatus.CRITICAL else AlertSeverity.WARNING
    )

    if prediction.failure_probability is not None and prediction.status == HealthStatus.CRITICAL:
        if not _has_open_alert(db, machine.id, AlertKind.FAILURE_PROBABILITY):
            created.append(
                Alert(
                    machine_id=machine.id,
                    severity=severity,
                    kind=AlertKind.FAILURE_PROBABILITY,
                    message=(
                        f"Failure probability has reached "
                        f"{prediction.failure_probability * 100:.0f}%."
                    ),
                    recommended_action=_failure_recommended_action(prediction.explanation),
                )
            )

    if prediction.anomaly_score is not None and prediction.status != HealthStatus.NORMAL:
        if not _has_open_alert(db, machine.id, AlertKind.ANOMALY_SCORE):
            signals = (prediction.explanation or {}).get("anomaly_signals") or []
            created.append(
                Alert(
                    machine_id=machine.id,
                    severity=severity,
                    kind=AlertKind.ANOMALY_SCORE,
                    message=f"Anomaly score {prediction.anomaly_score:.2f} — unusual sensor pattern.",
                    recommended_action=(
                        f"Inspect: {', '.join(signals[:3])}." if signals else _DEFAULT_ACTION
                    ),
                )
            )

    if prediction.rul_cycles is not None and prediction.status != HealthStatus.NORMAL:
        if not _has_open_alert(db, machine.id, AlertKind.RUL):
            created.append(
                Alert(
                    machine_id=machine.id,
                    severity=severity,
                    kind=AlertKind.RUL,
                    message=f"Estimated remaining useful life: {prediction.rul_cycles:.0f} cycles.",
                    recommended_action="Schedule maintenance inspection.",
                )
            )

    db.add_all(created)
    return created
