import json
import math
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


class ReportGenerator:
    def __init__(self, log_dir: str = "logs", report_dir: str = "reports") -> None:
        self.log_dir = Path(log_dir)
        self.report_dir = Path(report_dir)
        self.report_dir.mkdir(exist_ok=True)

    def generate_from_latest_log(self) -> Path | None:
        latest_log = self.latest_log_file()
        if latest_log is None:
            return None
        return self.generate(latest_log)

    def latest_log_file(self) -> Path | None:
        files = sorted(
            self.log_dir.glob("run_*.jsonl"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        if not files:
            return None
        return files[0]

    def generate(self, log_file: str | Path) -> Path | None:
        log_path = Path(log_file)
        frames = self._read_frames(log_path)

        if not frames:
            return None

        summary = self._summarize(frames)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = self.report_dir / f"report_{timestamp}.txt"
        report_path.write_text(self._format_report(log_path, summary), encoding="utf-8")
        return report_path

    def _read_frames(self, log_path: Path) -> list[dict[str, Any]]:
        if not log_path.exists():
            return []

        frames = []
        with log_path.open("r", encoding="utf-8") as file:
            for line in file:
                line = line.strip()
                if not line:
                    continue
                frames.append(json.loads(line))
        return frames

    def _summarize(self, frames: list[dict[str, Any]]) -> dict[str, Any]:
        odometry_errors = []
        ekf_errors = []
        planners = []
        autonomous_frames = 0
        exploration_frames = 0
        collision_count = 0
        replan_counts = []

        for frame in frames:
            true_pose = frame.get("robot_true_pose")
            odometry_pose = frame.get("odometry_pose")
            ekf_pose = frame.get("ekf_pose")

            odometry_error = self._pose_error(true_pose, odometry_pose)
            if odometry_error is not None:
                odometry_errors.append(odometry_error)

            ekf_error = self._pose_error(true_pose, ekf_pose)
            if ekf_error is not None:
                ekf_errors.append(ekf_error)

            planner = frame.get("current_planner")
            if planner:
                planners.append(str(planner))

            if frame.get("autonomous_mode", False):
                autonomous_frames += 1
            if frame.get("exploration_mode", False):
                exploration_frames += 1
            if frame.get("collision_status", False):
                collision_count += 1

            replan_counts.append(int(frame.get("replans_count", 0)))

        frame_count = len(frames)
        return {
            "total_run_time": self._total_run_time(frames),
            "final_distance_to_goal": frames[-1].get("distance_to_goal"),
            "average_odometry_error": self._average(odometry_errors),
            "average_ekf_error": self._average(ekf_errors),
            "maximum_ekf_error": max(ekf_errors) if ekf_errors else 0.0,
            "replans_count": max(replan_counts) if replan_counts else 0,
            "collision_count": collision_count,
            "planner_used": self._planner_used(planners),
            "autonomous_percent": autonomous_frames / frame_count * 100,
            "exploration_percent": exploration_frames / frame_count * 100,
            "frame_count": frame_count,
        }

    def _format_report(self, log_path: Path, summary: dict[str, Any]) -> str:
        final_distance = summary["final_distance_to_goal"]
        final_distance_text = "N/A" if final_distance is None else f"{final_distance:.2f} px"

        return "\n".join(
            [
                "AMR Navigation Simulator Experiment Report",
                "==========================================",
                f"Source log: {log_path.name}",
                f"Generated: {datetime.now().isoformat(timespec='seconds')}",
                "",
                f"Total run time: {summary['total_run_time']:.2f} s",
                f"Frames analyzed: {summary['frame_count']}",
                f"Final distance to goal: {final_distance_text}",
                f"Average odometry error: {summary['average_odometry_error']:.2f} px",
                f"Average EKF error: {summary['average_ekf_error']:.2f} px",
                f"Maximum EKF error: {summary['maximum_ekf_error']:.2f} px",
                f"Replans count: {summary['replans_count']}",
                f"Collision count: {summary['collision_count']}",
                f"Planner used: {summary['planner_used']}",
                f"Autonomous mode: {summary['autonomous_percent']:.1f}% of frames",
                f"Exploration mode: {summary['exploration_percent']:.1f}% of frames",
                "",
            ]
        )

    def _total_run_time(self, frames: list[dict[str, Any]]) -> float:
        if len(frames) < 2:
            return 0.0

        start = self._parse_timestamp(frames[0].get("timestamp"))
        end = self._parse_timestamp(frames[-1].get("timestamp"))
        if start is None or end is None:
            return 0.0
        return max(0.0, (end - start).total_seconds())

    def _parse_timestamp(self, value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None

    def _pose_error(
        self,
        true_pose: dict[str, Any] | None,
        estimated_pose: dict[str, Any] | None,
    ) -> float | None:
        if not true_pose or not estimated_pose:
            return None

        dx = float(true_pose.get("x", 0.0)) - float(estimated_pose.get("x", 0.0))
        dy = float(true_pose.get("y", 0.0)) - float(estimated_pose.get("y", 0.0))
        return math.sqrt(dx * dx + dy * dy)

    def _average(self, values: list[float]) -> float:
        if not values:
            return 0.0
        return sum(values) / len(values)

    def _planner_used(self, planners: list[str]) -> str:
        if not planners:
            return "Unknown"

        counts = Counter(planners)
        if len(counts) == 1:
            return planners[-1]

        return ", ".join(sorted(counts))
