"""Maintenance history -- section 20 of the PRD.

Technician-recorded ground truth: what was actually done, when, and at what
cost. Deliberately just CRUD -- the analysis this enables ("machines with
frequent vibration anomalies need maintenance roughly every X operating
hours") is a query over this table plus `alerts`/`predictions`, not a feature
of the table itself.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import MaintenanceRecord
from app.schemas import MaintenanceRecordIn, MaintenanceRecordOut

router = APIRouter(prefix="/maintenance", tags=["maintenance"])


@router.get("", response_model=list[MaintenanceRecordOut])
def list_maintenance(
    machine_id: int | None = None, db: Session = Depends(get_db)
) -> list[MaintenanceRecord]:
    stmt = select(MaintenanceRecord).order_by(MaintenanceRecord.maintenance_date.desc())
    if machine_id is not None:
        stmt = stmt.where(MaintenanceRecord.machine_id == machine_id)
    return list(db.scalars(stmt).all())


@router.post("", response_model=MaintenanceRecordOut, status_code=201)
def create_maintenance(
    payload: MaintenanceRecordIn, db: Session = Depends(get_db)
) -> MaintenanceRecord:
    record = MaintenanceRecord(**payload.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.delete("/{record_id}", status_code=204)
def delete_maintenance(record_id: int, db: Session = Depends(get_db)) -> None:
    record = db.get(MaintenanceRecord, record_id)
    if record is None:
        raise HTTPException(404, f"maintenance record {record_id} not found")
    db.delete(record)
    db.commit()
