"""Pydantic request/response schemas.

Kept separate from the ORM models (`app/models.py`) on purpose: the API
contract and the storage schema are allowed to drift -- e.g. a reading payload
is a flat dict in the DB but a validated, machine-type-specific shape here.
"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models import AlertKind, AlertSeverity, HealthStatus, MachineType

# --------------------------------------------------------------------------- #
# Machines
# --------------------------------------------------------------------------- #


class MachineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    machine_type: MachineType
    quality_type: str | None
    created_at: datetime


class MachineCreate(BaseModel):
    name: str
    machine_type: MachineType
    quality_type: str | None = None


class MachineSummary(MachineOut):
    """Machine plus its latest known status, for the fleet dashboard list."""

    latest_status: HealthStatus | None = None
    latest_failure_probability: float | None = None
    latest_anomaly_score: float | None = None
    latest_rul_cycles: float | None = None
    latest_prediction_ts: datetime | None = None


# --------------------------------------------------------------------------- #
# Sensor readings
# --------------------------------------------------------------------------- #


class MillingReadingIn(BaseModel):
    """Raw AI4I-style sensor payload -- same fields `ml.data.SENSOR_COLS` expects."""

    air_temp_k: float
    process_temp_k: float
    rotational_speed_rpm: float
    torque_nm: float
    tool_wear_min: float
    type: str = Field(pattern="^[LMH]$")


class TurbofanReadingIn(BaseModel):
    """One C-MAPSS cycle: 21 sensors + 3 operating settings, before dropping constants."""

    cycle: int
    op_setting_1: float
    op_setting_2: float
    op_setting_3: float
    sensors: dict[str, float] = Field(
        description="sensor_1..sensor_21 -> value"
    )


class ReadingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    machine_id: int
    ts: datetime
    cycle: int | None
    payload: dict


# --------------------------------------------------------------------------- #
# Predictions
# --------------------------------------------------------------------------- #


class PredictionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    machine_id: int
    ts: datetime
    failure_probability: float | None
    anomaly_score: float | None
    rul_cycles: float | None
    status: HealthStatus
    explanation: dict | None


# --------------------------------------------------------------------------- #
# Alerts
# --------------------------------------------------------------------------- #


class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    machine_id: int
    ts: datetime
    severity: AlertSeverity
    kind: AlertKind
    message: str
    recommended_action: str
    acknowledged: bool


# --------------------------------------------------------------------------- #
# Maintenance history
# --------------------------------------------------------------------------- #


class MaintenanceRecordIn(BaseModel):
    machine_id: int
    maintenance_date: date
    issue: str
    action_taken: str
    parts_replaced: str | None = None
    technician: str
    cost: float


class MaintenanceRecordOut(MaintenanceRecordIn):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
