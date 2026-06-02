"""Score a reading: store it, run it through the right model(s), store the result.

One endpoint, dispatching on `machine.machine_type` -- milling machines are
scored from the single reading just submitted; turbofan engines are scored
from their last `window` stored readings, since the RUL model needs a
sequence. Either way the caller gets the same `PredictionOut` shape back.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.ml.inference_milling import score_milling_reading
from app.ml.inference_turbofan import score_turbofan_window
from app.ml.registry import ModelRegistry, get_registry
from app.models import HealthStatus, Machine, MachineType, Prediction, SensorReading
from app.schemas import MillingReadingIn, PredictionOut, TurbofanReadingIn

router = APIRouter(tags=["predictions"])


def _flatten_turbofan(reading: TurbofanReadingIn) -> dict:
    """`{op_setting_1, op_setting_2, op_setting_3, sensors: {...}}` -> one flat dict.

    This is the storage/inference contract every turbofan reading follows --
    see `inference_turbofan`'s docstring.
    """
    return {
        "op_setting_1": reading.op_setting_1,
        "op_setting_2": reading.op_setting_2,
        "op_setting_3": reading.op_setting_3,
        **reading.sensors,
    }


@router.post("/machines/{machine_id}/score", response_model=PredictionOut, status_code=201)
def score_reading(
    machine_id: int,
    body: dict,
    db: Session = Depends(get_db),
    registry: ModelRegistry = Depends(get_registry),
) -> Prediction:
    machine = db.get(Machine, machine_id)
    if machine is None:
        raise HTTPException(404, f"machine {machine_id} not found")

    try:
        if machine.machine_type == MachineType.MILLING:
            parsed = MillingReadingIn.model_validate(body)
            payload = parsed.model_dump()
            cycle = None
        else:
            parsed = TurbofanReadingIn.model_validate(body)
            payload = _flatten_turbofan(parsed)
            cycle = parsed.cycle
    except ValidationError as exc:
        raise HTTPException(422, exc.errors()) from exc

    reading = SensorReading(machine_id=machine_id, cycle=cycle, payload=payload)
    db.add(reading)
    db.flush()  # assigns reading.id without committing yet

    if machine.machine_type == MachineType.MILLING:
        result = score_milling_reading(payload, registry)
    else:
        history = db.scalars(
            select(SensorReading)
            .where(SensorReading.machine_id == machine_id)
            .order_by(SensorReading.cycle)
        ).all()
        readings = [r.payload for r in history]
        result = score_turbofan_window(readings, registry.rul_model)

    prediction = Prediction(
        machine_id=machine_id,
        reading_id=reading.id,
        ts=datetime.utcnow(),
        failure_probability=result.get("failure_probability"),
        anomaly_score=result.get("anomaly_score"),
        rul_cycles=result.get("rul_cycles"),
        status=HealthStatus(result["status"]),
        explanation=result.get("explanation"),
    )
    db.add(prediction)
    db.commit()
    db.refresh(prediction)
    return prediction
