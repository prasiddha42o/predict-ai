"""Alert list and acknowledgement endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Alert
from app.schemas import AlertOut

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=list[AlertOut])
def list_alerts(
    unacknowledged_only: bool = False, db: Session = Depends(get_db)
) -> list[Alert]:
    stmt = select(Alert).order_by(Alert.ts.desc())
    if unacknowledged_only:
        stmt = stmt.where(Alert.acknowledged.is_(False))
    return list(db.scalars(stmt).all())


@router.post("/{alert_id}/acknowledge", response_model=AlertOut)
def acknowledge_alert(alert_id: int, db: Session = Depends(get_db)) -> Alert:
    alert = db.get(Alert, alert_id)
    if alert is None:
        raise HTTPException(404, f"alert {alert_id} not found")
    alert.acknowledged = True
    db.commit()
    db.refresh(alert)
    return alert
