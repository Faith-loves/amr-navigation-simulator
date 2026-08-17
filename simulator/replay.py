import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from robot.state import RobotState


@dataclass
class ReplayFrame:
    robot_true_pose: RobotState | None
    odometry_pose: RobotState | None
    ekf_pose: RobotState | None
    goal_position: tuple[float, float] | None
    current_planner: str
    autonomous_mode: bool
    exploration_mode: bool
    replan_count: int
    collision_status: bool
    distance_to_goal: float | None
    mission_info: dict[str, Any]
    battery_percentage: float | None = None
    battery_state: str = ""
    charging: bool = False
    energy_consumed: float = 0.0


class ReplayPlayer:
    def __init__(self, log_dir: str = "logs", frame_time: float = 1 / 30) -> None:
        self.log_dir = Path(log_dir)
        self.frame_time = frame_time
        self.frames: list[ReplayFrame] = []
        self.frame_index = 0
        self.playing = False
        self.file_path: Path | None = None
        self._time_since_frame = 0.0

    @property
    def is_active(self) -> bool:
        return bool(self.frames)

    @property
    def file_name(self) -> str:
        if self.file_path is None:
            return ""
        return self.file_path.name

    @property
    def frame_count(self) -> int:
        return len(self.frames)

    @property
    def current_frame(self) -> ReplayFrame | None:
        if not self.frames:
            return None
        return self.frames[self.frame_index]

    def load_latest(self) -> bool:
        files = sorted(
            self.log_dir.glob("run_*.jsonl"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )

        if not files:
            return False

        return self.load(files[0])

    def load(self, file_path: str | Path) -> bool:
        path = Path(file_path)
        frames = []

        if not path.exists():
            return False

        with path.open("r", encoding="utf-8") as file:
            for line in file:
                line = line.strip()
                if not line:
                    continue
                frames.append(self._parse_frame(json.loads(line)))

        if not frames:
            return False

        self.frames = frames
        self.frame_index = 0
        self.playing = False
        self.file_path = path
        self._time_since_frame = 0.0
        return True

    def toggle_playback(self) -> None:
        if self.is_active:
            self.playing = not self.playing

    def next_frame(self) -> None:
        if not self.is_active:
            return
        self.frame_index = min(self.frame_index + 1, len(self.frames) - 1)

    def previous_frame(self) -> None:
        if not self.is_active:
            return
        self.frame_index = max(self.frame_index - 1, 0)

    def update(self, dt: float) -> None:
        if not self.is_active or not self.playing:
            return

        self._time_since_frame += dt
        while self._time_since_frame >= self.frame_time:
            self._time_since_frame -= self.frame_time
            if self.frame_index >= len(self.frames) - 1:
                self.playing = False
                break
            self.next_frame()

    def exit(self) -> None:
        self.frames = []
        self.frame_index = 0
        self.playing = False
        self.file_path = None
        self._time_since_frame = 0.0

    def _parse_frame(self, data: dict[str, Any]) -> ReplayFrame:
        return ReplayFrame(
            robot_true_pose=self._pose_from_dict(data.get("robot_true_pose")),
            odometry_pose=self._pose_from_dict(data.get("odometry_pose")),
            ekf_pose=self._pose_from_dict(data.get("ekf_pose")),
            goal_position=self._point_from_dict(data.get("goal_position")),
            current_planner=str(data.get("current_planner", "--")),
            autonomous_mode=bool(data.get("autonomous_mode", False)),
            exploration_mode=bool(data.get("exploration_mode", False)),
            replan_count=int(data.get("replans_count", 0)),
            collision_status=bool(data.get("collision_status", False)),
            distance_to_goal=data.get("distance_to_goal"),
            mission_info=dict(data.get("mission") or {}),
            battery_percentage=data.get("battery_percentage"),
            battery_state=str(data.get("battery_state", "")),
            charging=bool(data.get("charging", False)),
            energy_consumed=float(data.get("energy_consumed", 0.0)),
        )

    def _pose_from_dict(self, data: dict[str, Any] | None) -> RobotState | None:
        if not data:
            return None
        return RobotState(
            x=float(data.get("x", 0.0)),
            y=float(data.get("y", 0.0)),
            theta=float(data.get("theta", 0.0)),
        )

    def _point_from_dict(self, data: dict[str, Any] | None) -> tuple[float, float] | None:
        if not data:
            return None
        return float(data.get("x", 0.0)), float(data.get("y", 0.0))
