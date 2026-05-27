"""SQLAlchemy ORM models.

Two machine types, not one: `MILLING` machines are scored by the AI4I models
(failure probability, anomaly score) from a single sensor snapshot; `TURBOFAN`
engines are scored by the C-MAPSS LSTM (remaining useful life) over a rolling
30-cycle window. These are genuinely different modelling problems -- see the
root README's "Scope change" note -- so a machine's type determines which
readings and predictions apply to it rather than every machine carrying every
field.
"""

from __future__ import annotations

import enum
from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, Enum, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class HealthStatus(str, enum.Enum):
    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertSeverity(str, enum.Enum):
    WARNING = "warning"
    CRITICAL = "critical"


class AlertKind(str, enum.Enum):
    FAILURE_PROBABILITY = "failure_probability"
    ANOMALY_SCORE = "anomaly_score"
    RUL = "rul"


class MachineType(str, enum.Enum):
    MILLING = "milling"
    TURBOFAN = "turbofan"


class Machine(Base):
    __tablename__ = "machines"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    machine_type: Mapped[MachineType] = mapped_column(Enum(MachineType))
    #: AI4I quality variant (L/M/H), only meaningful for milling machines.
    quality_type: Mapped[str | None] = mapped_column(String(1), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    readings: Mapped[list["SensorReading"]] = relationship(
        back_populates="machine", cascade="all, delete-orphan"
    )
    predictions: Mapped[list["Prediction"]] = relationship(
        back_populates="machine", cascade="all, delete-orphan"
    )
    alerts: Mapped[list["Alert"]] = relationship(
        back_populates="machine", cascade="all, delete-orphan"
    )
    maintenance_records: Mapped[list["MaintenanceRecord"]] = relationship(
        back_populates="machine", cascade="all, delete-orphan"
    )


class SensorReading(Base):
    """One sensor snapshot. `payload` shape depends on the machine's type.

    Milling: air_temp_k, process_temp_k, rotational_speed_rpm, torque_nm,
    tool_wear_min. Turbofan: sensor_2..sensor_21 (minus the constant ones) and
    op_setting_1/2, plus `cycle`, the engine's own operating-cycle counter --
    the LSTM's window is defined on cycle order, not wall-clock time.
    """

    __tablename__ = "sensor_readings"

    id: Mapped[int] = mapped_column(primary_key=True)
    machine_id: Mapped[int] = mapped_column(ForeignKey("machines.id"))
    ts: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    cycle: Mapped[int | None] = mapped_column(nullable=True)
    payload: Mapped[dict] = mapped_column(JSON)

    machine: Mapped[Machine] = relationship(back_populates="readings")


class Prediction(Base):
    """One scored reading. Milling fields and turbofan fields are mutually
    exclusive -- which ones are populated follows from `machine.machine_type`.
    """

    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(primary_key=True)
    machine_id: Mapped[int] = mapped_column(ForeignKey("machines.id"))
    reading_id: Mapped[int | None] = mapped_column(
        ForeignKey("sensor_readings.id"), nullable=True
    )
    ts: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    # Milling machines
    failure_probability: Mapped[float | None] = mapped_column(Float, nullable=True)
    anomaly_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Turbofan engines
    rul_cycles: Mapped[float | None] = mapped_column(Float, nullable=True)

    status: Mapped[HealthStatus] = mapped_column(Enum(HealthStatus))
    #: Top contributing signals, e.g. SHAP attribution or per-feature
    #: reconstruction error -- whatever the model that produced this
    #: prediction can explain itself with.
    explanation: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    machine: Mapped[Machine] = relationship(back_populates="predictions")


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True)
    machine_id: Mapped[int] = mapped_column(ForeignKey("machines.id"))
    ts: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    severity: Mapped[AlertSeverity] = mapped_column(Enum(AlertSeverity))
    kind: Mapped[AlertKind] = mapped_column(Enum(AlertKind))
    message: Mapped[str] = mapped_column(Text)
    recommended_action: Mapped[str] = mapped_column(Text)
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False)

    machine: Mapped[Machine] = relationship(back_populates="alerts")


class MaintenanceRecord(Base):
    """Manually logged maintenance history -- section 20 of the PRD.

    Kept independent of predictions/alerts: a technician records what was
    actually done, which is ground truth that the model's alerts can later be
    checked against ("machines with frequent vibration anomalies need
    maintenance roughly every X operating hours").
    """

    __tablename__ = "maintenance_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    machine_id: Mapped[int] = mapped_column(ForeignKey("machines.id"))
    maintenance_date: Mapped[date] = mapped_column(Date)
    issue: Mapped[str] = mapped_column(Text)
    action_taken: Mapped[str] = mapped_column(Text)
    parts_replaced: Mapped[str | None] = mapped_column(Text, nullable=True)
    technician: Mapped[str] = mapped_column(String(120))
    cost: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    machine: Mapped[Machine] = relationship(back_populates="maintenance_records")
