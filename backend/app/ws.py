"""Live sensor + prediction stream -- section 18 of the PRD.

One simulator state per machine, ticked every `settings.simulator_interval_seconds`
by a single background task started at app startup. Every connected WebSocket
client receives every tick as JSON: `{machine_id, reading, prediction}`. One
broadcast loop fanned out to whoever is connected, not per-client polling --
Redis pub/sub is the natural next step if this ever needs to run behind more
than one backend process, but for one process an in-memory fan-out is enough.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.config import get_settings
from app.db import SessionLocal
from app.ml.registry import get_registry
from app.models import Machine, MachineType
from app.scoring import score_and_store
from app.simulator import MillingSimState, TurbofanSimState

router = APIRouter()
settings = get_settings()


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._connections.add(ws)

    def disconnect(self, ws: WebSocket) -> None:
        self._connections.discard(ws)

    async def broadcast(self, message: dict) -> None:
        dead = []
        for ws in self._connections:
            try:
                await ws.send_text(json.dumps(message, default=str))
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()
_sim_states: dict[int, Any] = {}


def _get_sim_state(machine: Machine):
    if machine.id not in _sim_states:
        if machine.machine_type == MachineType.MILLING:
            _sim_states[machine.id] = MillingSimState(
                quality_type=machine.quality_type or "M", seed=machine.id
            )
        else:
            # Cycle through the 100 real FD001 test engines by machine id, so
            # distinct turbofan machines replay distinct real trajectories.
            unit = ((machine.id - 1) % 100) + 1
            _sim_states[machine.id] = TurbofanSimState(unit=unit)
    return _sim_states[machine.id]


def _reading_to_payload(machine: Machine, reading: dict) -> tuple[dict, int | None]:
    if machine.machine_type == MachineType.MILLING:
        return reading, None
    cycle = reading["cycle"]
    payload = {
        "op_setting_1": reading["op_setting_1"],
        "op_setting_2": reading["op_setting_2"],
        "op_setting_3": reading["op_setting_3"],
        **reading["sensors"],
    }
    return payload, cycle


async def simulator_loop() -> None:
    registry = get_registry()
    while True:
        await asyncio.sleep(settings.simulator_interval_seconds)
        if not manager._connections:
            continue  # nothing to score for; nobody is watching
        db = SessionLocal()
        try:
            machines = db.scalars(select(Machine)).all()
            for machine in machines:
                state = _get_sim_state(machine)
                payload, cycle = _reading_to_payload(machine, state.tick())
                prediction = score_and_store(db, machine, payload, cycle, registry)
                await manager.broadcast(
                    {
                        "machine_id": machine.id,
                        "machine_name": machine.name,
                        "machine_type": machine.machine_type.value,
                        "reading": payload,
                        "prediction": {
                            "failure_probability": prediction.failure_probability,
                            "anomaly_score": prediction.anomaly_score,
                            "rul_cycles": prediction.rul_cycles,
                            "status": prediction.status.value,
                            "ts": prediction.ts.isoformat(),
                        },
                    }
                )
        finally:
            db.close()


@router.websocket("/ws/live")
async def live_feed(websocket: WebSocket) -> None:
    """Connect, then just listen -- the server pushes every tick, the client sends nothing."""
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
