"""Seed a demo fleet.

Usage:
    python -m app.seed

Creates 24 machines (18 milling, 6 turbofan) plus a handful of maintenance
records, matching the scale of the PRD's dashboard example ("24 machines: 17
healthy, 5 warning, 2 critical"). Actual health status isn't set here -- it
only exists once a machine has been scored at least once, which the
WebSocket simulator does continuously once machines exist. Safe to re-run:
skips seeding if any machine already exists.
"""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select

from app.db import Base, SessionLocal, engine
from app.models import MaintenanceRecord, Machine, MachineType

MILLING_QUALITY_MIX = ["L"] * 9 + ["M"] * 6 + ["H"] * 3  # matches AI4I's own 6:3:1-ish tiering
N_TURBOFAN = 6

_MAINTENANCE_SAMPLE = [
    ("Excess tool wear", "Replaced end mill tool", "end mill bit", "A. Rai", 120.0),
    ("Elevated vibration flagged by anomaly detector", "Inspected spindle bearing", None, "S. Gurung", 85.5),
    ("Overstrain alert", "Reduced feed rate, replaced worn tool", "end mill bit", "A. Rai", 145.0),
    ("Routine inspection", "No issue found", None, "P. Shrestha", 40.0),
]


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.scalar(select(Machine.id).limit(1)) is not None:
            print("Machines already exist -- skipping seed.")
            return

        machines: list[Machine] = []
        for i, quality in enumerate(MILLING_QUALITY_MIX, start=1):
            machines.append(
                Machine(name=f"Machine #{i}", machine_type=MachineType.MILLING, quality_type=quality)
            )
        for i in range(1, N_TURBOFAN + 1):
            machines.append(Machine(name=f"Engine #{i}", machine_type=MachineType.TURBOFAN))
        db.add_all(machines)
        db.commit()
        for m in machines:
            db.refresh(m)

        milling_machines = [m for m in machines if m.machine_type == MachineType.MILLING]
        for i, (issue, action, parts, tech, cost) in enumerate(_MAINTENANCE_SAMPLE):
            db.add(
                MaintenanceRecord(
                    machine_id=milling_machines[i % len(milling_machines)].id,
                    maintenance_date=date.today() - timedelta(days=30 * (i + 1)),
                    issue=issue,
                    action_taken=action,
                    parts_replaced=parts,
                    technician=tech,
                    cost=cost,
                )
            )
        db.commit()

        print(f"Seeded {len(machines)} machines ({len(milling_machines)} milling, "
              f"{N_TURBOFAN} turbofan) and {len(_MAINTENANCE_SAMPLE)} maintenance records.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
