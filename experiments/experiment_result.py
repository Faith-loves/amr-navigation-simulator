from __future__ import annotations

from dataclasses import dataclass


SUCCESS = "SUCCESS"
TIMEOUT = "TIMEOUT"
COLLISION_FAILURE = "COLLISION_FAILURE"
NO_PATH = "NO_PATH"
ERROR = "ERROR"
CANCELLED = "CANCELLED"


@dataclass
class ExperimentResult:
    experiment_name: str
    scenario: str
    planner: str
    run_number: int
    random_seed: int
    outcome: str
    success: bool
    completion_time: float | None
    path_length: float
    actual_distance: float
    replans: int
    collisions: int
    goal_distance: float
    initial_planning_time: float
    average_planning_time: float
    total_planning_time: float
    nodes_expanded: int
    average_odometry_error: float
    final_odometry_error: float
    average_ekf_error: float
    final_ekf_error: float
    maximum_ekf_error: float
    average_fps: float
    average_lidar_update_time: float
    average_mapping_time: float
    energy_consumed: float = 0.0
    final_battery_percentage: float = 100.0
    charging_stops: int = 0


@dataclass
class PlannerSummary:
    planner: str
    total_runs: int
    successful_runs: int
    success_rate: float
    average_completion_time: float | None
    average_path_length: float
    average_actual_distance: float
    average_replans: float
    average_collisions: float
    average_planning_time: float
    average_nodes_expanded: float
    average_ekf_error: float
