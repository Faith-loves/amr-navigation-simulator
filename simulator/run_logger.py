import json
from datetime import datetime
from pathlib import Path
from typing import Any

from robot.state import RobotState


class RunLogger:
    def __init__(self, log_dir: str = "logs") -> None:
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.file = None
        self.current_file_path: Path | None = None

    @property
    def is_logging(self) -> bool:
        return self.file is not None

    @property
    def current_file_name(self) -> str:
        if self.current_file_path is None:
            return ""
        return self.current_file_path.name

    def start(self) -> None:
        if self.is_logging:
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.current_file_path = self.log_dir / f"run_{timestamp}.jsonl"
        self.file = self.current_file_path.open("a", encoding="utf-8")

    def stop(self) -> None:
        if self.file is None:
            return

        self.file.close()
        self.file = None

    def toggle(self) -> None:
        if self.is_logging:
            self.stop()
        else:
            self.start()

    def log_frame(
        self,
        robot_state: RobotState | None,
        odometry_state: RobotState | None,
        ekf_state: RobotState | None,
        goal_position: tuple[float, float] | None,
        current_planner: str,
        autonomous_mode: bool,
        exploration_mode: bool,
        replan_count: int,
        collision_status: bool,
        distance_to_goal: float | None,
        mission_info: dict[str, object] | None = None,
        battery_info: dict[str, object] | None = None,
    ) -> None:
        if self.file is None:
            return

        entry = {
            "timestamp": datetime.now().isoformat(timespec="milliseconds"),
            "robot_true_pose": self._pose_to_dict(robot_state),
            "odometry_pose": self._pose_to_dict(odometry_state),
            "ekf_pose": self._pose_to_dict(ekf_state),
            "goal_position": self._point_to_dict(goal_position),
            "current_planner": current_planner,
            "autonomous_mode": autonomous_mode,
            "exploration_mode": exploration_mode,
            "replans_count": replan_count,
            "collision_status": collision_status,
            "distance_to_goal": distance_to_goal,
            "mission": mission_info or {},
            "battery_percentage": None if battery_info is None else battery_info.get("percentage"),
            "battery_state": "" if battery_info is None else battery_info.get("battery_state", ""),
            "charging": False if battery_info is None else bool(battery_info.get("charging", False)),
            "energy_consumed": 0.0 if battery_info is None else float(battery_info.get("energy_consumed", 0.0)),
        }

        self.file.write(json.dumps(entry) + "\n")
        self.file.flush()

    def close(self) -> None:
        self.stop()

    def _pose_to_dict(self, pose: RobotState | None) -> dict[str, float] | None:
        if pose is None:
            return None
        return {
            "x": pose.x,
            "y": pose.y,
            "theta": pose.theta,
        }

    def _point_to_dict(self, point: tuple[float, float] | None) -> dict[str, float] | None:
        if point is None:
            return None

        x, y = point
        return {
            "x": x,
            "y": y,
        }
