"""Machine list and detail endpoints -- the fleet dashboard's main data source."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Machine, Prediction
from app.schemas import MachineCreate, MachineOut, MachineSummary, PredictionOut, ReadingOut

router = APIRouter(prefix="/machines", tags=["machines"])


def _latest_prediction(db: Session, machine_id: int) -> Prediction | None:
    return db.scalar(
        select(Prediction)
        .where(Prediction.machine_id == machine_id)
        .order_by(Prediction.ts.desc())
        .limit(1)
    )


@router.get("", response_model=list[MachineSummary])
def list_machines(db: Session = Depends(get_db)) -> list[MachineSummary]:
    """Every machine, with its latest known status -- backs the fleet dashboard tiles."""
    machines = db.scalars(select(Machine).order_by(Machine.id)).all()
    out = []
    for m in machines:
        latest = _latest_prediction(db, m.id)
        out.append(
            MachineSummary(
                **MachineOut.model_validate(m).model_dump(),
                latest_status=latest.status if latest else None,
                latest_failure_probability=latest.failure_probability if latest else None,
                latest_anomaly_score=latest.anomaly_score if latest else None,
                latest_rul_cycles=latest.rul_cycles if latest else None,
                latest_prediction_ts=latest.ts if latest else None,
            )
        )
    return out


@router.post("", response_model=MachineOut, status_code=201)
def create_machine(payload: MachineCreate, db: Session = Depends(get_db)) -> Machine:
    machine = Machine(**payload.model_dump())
    db.add(machine)
    db.commit()
    db.refresh(machine)
    return machine


def _get_or_404(db: Session, machine_id: int) -> Machine:
    machine = db.get(Machine, machine_id)
    if machine is None:
        raise HTTPException(404, f"machine {machine_id} not found")
    return machine


@router.get("/{machine_id}", response_model=MachineOut)
def get_machine(machine_id: int, db: Session = Depends(get_db)) -> Machine:
    return _get_or_404(db, machine_id)


@router.get("/{machine_id}/readings", response_model=list[ReadingOut])
def get_machine_readings(
    machine_id: int, limit: int = 100, db: Session = Depends(get_db)
) -> list[ReadingOut]:
    """Most recent readings, oldest-first -- what the detail page's sensor charts plot."""
    _get_or_404(db, machine_id)
    from app.models import SensorReading

    rows = db.scalars(
        select(SensorReading)
        .where(SensorReading.machine_id == machine_id)
        .order_by(SensorReading.ts.desc())
        .limit(limit)
    ).all()
    return list(reversed(rows))


@router.get("/{machine_id}/predictions", response_model=list[PredictionOut])
def get_machine_predictions(
    machine_id: int, limit: int = 100, db: Session = Depends(get_db)
) -> list[PredictionOut]:
    _get_or_404(db, machine_id)
    rows = db.scalars(
        select(Prediction)
        .where(Prediction.machine_id == machine_id)
        .order_by(Prediction.ts.desc())
        .limit(limit)
    ).all()
    return list(reversed(rows))
