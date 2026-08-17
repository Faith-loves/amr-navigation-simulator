from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


PLANNERS = ("A*", "Dijkstra", "RRT*")
RUN_OPTIONS = (1, 3, 5, 10)
NOISE_LEVELS = ("None", "Low", "Medium", "High")


@dataclass(frozen=True)
class ExperimentConfig:
    experiment_name: str = "Planner Comparison"
    scenario_name: str = "House Layout"
    planners: tuple[str, ...] = ("A*", "Dijkstra", "RRT*")
    runs_per_planner: int = 3
    lidar_noise_level: str = "Medium"
    dynamic_obstacles_enabled: bool | None = None
    battery_enabled: bool = False
    random_seed: int = 42
    timeout_seconds: float = 60.0
    fast_mode: bool = True
    created_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))

    def run_seed(self, planner: str, run_number: int) -> int:
        planner_offset = sum(ord(char) for char in planner)
        return self.random_seed + planner_offset + run_number

    @property
    def total_runs(self) -> int:
        return len(self.planners) * self.runs_per_planner
