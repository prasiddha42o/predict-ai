"""Score-and-store, shared by the REST prediction endpoint and the WebSocket
simulator loop so the two paths can't diverge on what "scoring a reading"
means.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.alerts import maybe_create_alerts
from app.ml.inference_milling import score_milling_reading
from app.ml.inference_turbofan import score_turbofan_window
from app.ml.registry import ModelRegistry
from app.models import HealthStatus, Machine, MachineType, Prediction, SensorReading


def score_and_store(
    db: Session,
    machine: Machine,
    payload: dict,
    cycle: int | None,
    registry: ModelRegistry,
) -> Prediction:
    reading = SensorReading(machine_id=machine.id, cycle=cycle, payload=payload)
    db.add(reading)
    db.flush()  # assigns reading.id without committing yet

    if machine.machine_type == MachineType.MILLING:
        result = score_milling_reading(payload, registry)
    else:
        history = db.scalars(
            select(SensorReading)
            .where(SensorReading.machine_id == machine.id)
            .order_by(SensorReading.cycle)
        ).all()
        result = score_turbofan_window([r.payload for r in history], registry.rul_model)

    prediction = Prediction(
        machine_id=machine.id,
        reading_id=reading.id,
        ts=datetime.utcnow(),
        failure_probability=result.get("failure_probability"),
        anomaly_score=result.get("anomaly_score"),
        rul_cycles=result.get("rul_cycles"),
        status=HealthStatus(result["status"]),
        explanation=result.get("explanation"),
    )
    db.add(prediction)
    db.flush()
    maybe_create_alerts(db, machine, prediction)
    db.commit()
    db.refresh(prediction)
    return prediction
