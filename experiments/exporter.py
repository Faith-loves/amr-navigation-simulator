from __future__ import annotations

import csv
import json
import platform
import re
import sys
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from experiments.experiment_analysis import planner_analyses
from experiments.experiment_manager import ExperimentManager
from experiments.experiment_result import ExperimentResult


EXPORT_VERSION = 1


class ExperimentExporter:
    def __init__(self, base_dir: str | Path = "experiment_results") -> None:
        self.base_dir = Path(base_dir)

    def export(self, manager: ExperimentManager, timestamp: datetime | None = None) -> Path:
        if manager.config is None:
            raise ValueError("Cannot export experiment data without an experiment configuration.")

        stamp = (timestamp or datetime.now()).strftime("%Y%m%d_%H%M%S")
        directory = self._unique_directory(self._safe_name(f"{manager.config.scenario_name}_{manager.config.experiment_name}_{stamp}"))
        directory.mkdir(parents=True, exist_ok=False)

        summaries = manager.grouped_summaries()
        analyses = planner_analyses(manager.results, summaries)

        self._write_config(directory / "config.json", manager)
        self._write_runs(directory / "runs.csv", manager.results)
        self._write_summary(directory / "summary.csv", analyses)
        self._write_metadata(directory / "metadata.json", manager, stamp)
        self._write_raw_results(directory / "raw_results.json", manager, summaries)
        return directory

    def _unique_directory(self, name: str) -> Path:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        candidate = self.base_dir / name
        suffix = 2
        while candidate.exists():
            candidate = self.base_dir / f"{name}_{suffix}"
            suffix += 1
        return candidate

    def _safe_name(self, value: str) -> str:
        normalized = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower()).strip("_")
        return normalized or "experiment"

    def _write_config(self, path: Path, manager: ExperimentManager) -> None:
        assert manager.config is not None
        self._write_json(path, asdict(manager.config))

    def _write_runs(self, path: Path, results: list[ExperimentResult]) -> None:
        fieldnames = [
            "experiment_name",
            "scenario",
            "planner",
            "run_number",
            "seed",
            "status",
            "success",
            "completion_time_s",
            "planned_path_length",
            "actual_distance_travelled",
            "initial_planning_time_ms",
            "average_planning_time_ms",
            "total_planning_time_ms",
            "nodes_expanded",
            "replans",
            "collisions",
            "final_goal_distance",
            "average_odometry_error",
            "final_odometry_error",
            "average_ekf_error",
            "final_ekf_error",
            "max_ekf_error",
            "average_fps",
            "average_lidar_time_ms",
            "average_mapping_time_ms",
            "energy_consumed",
            "final_battery_percentage",
            "charging_stops",
        ]
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for result in results:
                writer.writerow(
                    {
                        "experiment_name": result.experiment_name,
                        "scenario": result.scenario,
                        "planner": result.planner,
                        "run_number": result.run_number,
                        "seed": result.random_seed,
                        "status": result.outcome,
                        "success": result.success,
                        "completion_time_s": _successful_value(result, result.completion_time),
                        "planned_path_length": _successful_value(result, result.path_length),
                        "actual_distance_travelled": _successful_value(result, result.actual_distance),
                        "initial_planning_time_ms": _csv_value(result.initial_planning_time),
                        "average_planning_time_ms": _csv_value(result.average_planning_time),
                        "total_planning_time_ms": _csv_value(result.total_planning_time),
                        "nodes_expanded": _csv_value(result.nodes_expanded),
                        "replans": _csv_value(result.replans),
                        "collisions": _csv_value(result.collisions),
                        "final_goal_distance": _csv_value(result.goal_distance),
                        "average_odometry_error": _csv_value(result.average_odometry_error),
                        "final_odometry_error": _csv_value(result.final_odometry_error),
                        "average_ekf_error": _csv_value(result.average_ekf_error),
                        "final_ekf_error": _csv_value(result.final_ekf_error),
                        "max_ekf_error": _csv_value(result.maximum_ekf_error),
                        "average_fps": _csv_value(result.average_fps),
                        "average_lidar_time_ms": _csv_value(result.average_lidar_update_time),
                        "average_mapping_time_ms": _csv_value(result.average_mapping_time),
                        "energy_consumed": _csv_value(result.energy_consumed),
                        "final_battery_percentage": _csv_value(result.final_battery_percentage),
                        "charging_stops": _csv_value(result.charging_stops),
                    }
                )

    def _write_summary(self, path: Path, analyses) -> None:
        fieldnames = [
            "planner",
            "total_runs",
            "successful_runs",
            "failed_runs",
            "success_rate",
            "mean_completion_time",
            "std_completion_time",
            "mean_path_length",
            "std_path_length",
            "mean_actual_distance",
            "mean_planning_time",
            "std_planning_time",
            "mean_nodes_expanded",
            "mean_replans",
            "mean_collisions",
            "mean_odometry_error",
            "mean_ekf_error",
            "std_ekf_error",
        ]
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for analysis in analyses:
                summary = analysis.summary
                writer.writerow(
                    {
                        "planner": summary.planner,
                        "total_runs": summary.total_runs,
                        "successful_runs": summary.successful_runs,
                        "failed_runs": summary.total_runs - summary.successful_runs,
                        "success_rate": _csv_value(summary.success_rate),
                        "mean_completion_time": _csv_value(analysis.completion_time.mean),
                        "std_completion_time": _csv_value(analysis.completion_time.stddev),
                        "mean_path_length": _csv_value(analysis.path_length.mean),
                        "std_path_length": _csv_value(analysis.path_length.stddev),
                        "mean_actual_distance": _csv_value(summary.average_actual_distance),
                        "mean_planning_time": _csv_value(analysis.planning_time.mean),
                        "std_planning_time": _csv_value(analysis.planning_time.stddev),
                        "mean_nodes_expanded": _csv_value(summary.average_nodes_expanded),
                        "mean_replans": _csv_value(summary.average_replans),
                        "mean_collisions": _csv_value(summary.average_collisions),
                        "mean_odometry_error": _csv_value(analysis.odometry_error.mean),
                        "mean_ekf_error": _csv_value(analysis.ekf_error.mean),
                        "std_ekf_error": _csv_value(analysis.ekf_error.stddev),
                    }
                )

    def _write_metadata(self, path: Path, manager: ExperimentManager, stamp: str) -> None:
        successful_runs = sum(1 for result in manager.results if result.success)
        metadata = {
            "project": "AMR Navigation Simulator",
            "export_version": EXPORT_VERSION,
            "python_version": sys.version.split()[0],
            "platform": platform.platform(),
            "timestamp": stamp,
            "total_runs": len(manager.results),
            "completed_runs": len(manager.results),
            "successful_runs": successful_runs,
            "failed_runs": len(manager.results) - successful_runs,
        }
        self._write_json(path, metadata)

    def _write_raw_results(self, path: Path, manager: ExperimentManager, summaries) -> None:
        assert manager.config is not None
        payload = {
            "config": asdict(manager.config),
            "individual_runs": [asdict(result) for result in manager.results],
            "grouped_summaries": [asdict(summary) for summary in summaries],
        }
        self._write_json(path, payload)

    def _write_json(self, path: Path, payload: dict[str, Any]) -> None:
        with path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
            handle.write("\n")


def _csv_value(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.6g}"
    return value


def _successful_value(result: ExperimentResult, value: Any) -> Any:
    if not result.success:
        return ""
    return _csv_value(value)
