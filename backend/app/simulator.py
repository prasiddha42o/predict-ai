"""Synthetic sensor generator -- section 18 of the PRD ("Sensor Simulator").

Milling machines: AI4I has no per-machine trajectories to replay (see the
root README's "Scope change" note -- each row is an independent snapshot), so
this synthesises a plausible one: values drift slowly, then occasionally an
"episode" pushes them toward one of the three *deterministic* failure modes
notebook 02 reconstructed (overstrain, heat dissipation, power), then resets
("repaired"), like the PRD's 72C -> 76C -> 81C -> 85C escalation example.

Turbofan engines: replays real NASA C-MAPSS test-set trajectories cycle by
cycle. That data already *is* a genuine run-to-failure sequence, so nothing
needs to be synthesised for it -- reusing it is more honest than inventing one.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from ml import cmapss as C

_EPISODE_LENGTH_TICKS = 12
_EPISODE_START_PROB = 0.03
_EPISODE_RESET_PROB = 0.3


@dataclass
class MillingSimState:
    """Per-machine drift generator. One instance per milling machine, held
    for the process lifetime so successive `tick()` calls form a trajectory.
    """

    quality_type: str = "M"
    seed: int = 0
    tool_wear_min: float = 0.0
    episode_mode: str = "none"  # "none" | "overstrain" | "heat_dissipation" | "power"
    episode_tick: int = 0
    _rng: random.Random = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._rng = random.Random(self.seed)

    def tick(self) -> dict:
        if self.episode_mode == "none" and self._rng.random() < _EPISODE_START_PROB:
            self.episode_mode = self._rng.choice(["overstrain", "heat_dissipation", "power"])
            self.episode_tick = 0

        air = 298.0 + self._rng.gauss(0, 0.6)
        process = air + 10.5 + self._rng.gauss(0, 0.4)
        rpm = 1500 + self._rng.gauss(0, 40)
        torque = 40.0 + self._rng.gauss(0, 3)
        self.tool_wear_min = min(self.tool_wear_min + self._rng.uniform(0.5, 2.0), 253)

        if self.episode_mode != "none":
            self.episode_tick += 1
            progress = min(self.episode_tick / _EPISODE_LENGTH_TICKS, 1.0)
            if self.episode_mode == "overstrain":
                torque += progress * 45
            elif self.episode_mode == "heat_dissipation":
                process = air + (10.5 - progress * 4.5)
                rpm -= progress * 250
            elif self.episode_mode == "power":
                torque += progress * 30
                rpm += progress * 500
            if progress >= 1.0 and self._rng.random() < _EPISODE_RESET_PROB:
                self.episode_mode = "none"
                self.tool_wear_min = 0.0

        return {
            "air_temp_k": round(air, 2),
            "process_temp_k": round(process, 2),
            "rotational_speed_rpm": round(rpm, 1),
            "torque_nm": round(max(torque, 3.0), 2),
            "tool_wear_min": round(self.tool_wear_min, 1),
            "type": self.quality_type,
        }


@dataclass
class TurbofanSimState:
    """Replays one real C-MAPSS FD001 test-set engine, cycle by cycle, looping."""

    unit: int
    _cursor: int = field(default=0, init=False)
    _trajectory: list[dict] = field(default_factory=list, init=False, repr=False)

    def __post_init__(self) -> None:
        _, test, _ = C.load_subset("FD001")
        g = test[test["unit"] == self.unit].sort_values("cycle")
        if g.empty:
            raise ValueError(f"no C-MAPSS FD001 test engine with unit={self.unit}")
        self._trajectory = g.to_dict("records")

    def tick(self) -> dict:
        row = self._trajectory[self._cursor % len(self._trajectory)]
        self._cursor += 1
        return {
            "cycle": int(row["cycle"]),
            "op_setting_1": row["op_setting_1"],
            "op_setting_2": row["op_setting_2"],
            "op_setting_3": row["op_setting_3"],
            "sensors": {f"sensor_{i}": row[f"sensor_{i}"] for i in range(1, 22)},
        }
