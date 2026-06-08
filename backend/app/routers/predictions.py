"""Score a reading: validate it, then hand off to the shared scoring path.

Dispatches on `machine.machine_type` -- milling machines are scored from the
single reading just submitted; turbofan engines are scored from their last
`window` stored readings, since the RUL model needs a sequence. The actual
store-and-score work is shared with the WebSocket simulator loop via
`app.scoring.score_and_store`.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.db import get_db
from app.ml.registry import ModelRegistry, get_registry
from app.models import Machine, MachineType, Prediction
from app.schemas import MillingReadingIn, PredictionOut, TurbofanReadingIn
from app.scoring import score_and_store

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

    return score_and_store(db, machine, payload, cycle, registry)
