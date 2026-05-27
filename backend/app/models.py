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
from datetime import datetime

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


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
