import csv
import json
from datetime import datetime

from experiments.experiment_config import ExperimentConfig
from experiments.experiment_manager import ExperimentManager
from experiments.experiment_result import ExperimentResult, SUCCESS, TIMEOUT
from experiments.exporter import ExperimentExporter


def test_export_directory_created(tmp_path) -> None:
    folder = _export(tmp_path, [_result("A*", 1, success=True)])

    assert folder.exists()
    assert folder.name.startswith("house_layout_planner_comparison_")


def test_runs_csv_created_with_one_row_per_run(tmp_path) -> None:
    folder = _export(
        tmp_path,
        [
            _result("A*", 1, success=True),
            _result("A*", 2, success=False),
            _result("Dijkstra", 1, success=True),
        ],
    )

    rows = _read_csv(folder / "runs.csv")

    assert len(rows) == 3
    assert rows[0]["experiment_name"] == "Planner Comparison"
    assert rows[0]["seed"] == "43"


def test_summary_csv_created_with_one_row_per_planner(tmp_path) -> None:
    folder = _export(
        tmp_path,
        [
            _result("A*", 1, success=True, completion_time=10.0),
            _result("A*", 2, success=True, completion_time=14.0),
            _result("Dijkstra", 1, success=False),
        ],
    )

    rows = _read_csv(folder / "summary.csv")
    by_planner = {row["planner"]: row for row in rows}

    assert len(rows) == 2
    assert by_planner["A*"]["total_runs"] == "2"
    assert by_planner["A*"]["successful_runs"] == "2"
    assert by_planner["A*"]["mean_completion_time"] == "12"
    assert by_planner["Dijkstra"]["failed_runs"] == "1"


def test_config_json_matches_experiment_configuration(tmp_path) -> None:
    folder = _export(tmp_path, [_result("A*", 1, success=True)])

    config = json.loads((folder / "config.json").read_text(encoding="utf-8"))

    assert config["experiment_name"] == "Planner Comparison"
    assert config["scenario_name"] == "House Layout"
    assert config["planners"] == ["A*", "Dijkstra", "RRT*"]
    assert config["runs_per_planner"] == 3
    assert config["random_seed"] == 42


def test_metadata_does_not_expose_personal_absolute_paths(tmp_path) -> None:
    folder = _export(tmp_path, [_result("A*", 1, success=True)])

    metadata_text = (folder / "metadata.json").read_text(encoding="utf-8")
    metadata = json.loads(metadata_text)

    assert metadata["project"] == "AMR Navigation Simulator"
    assert metadata["export_version"] == 1
    assert "C:\\" not in metadata_text
    assert "/Users/" not in metadata_text
    assert "\\Users\\" not in metadata_text


def test_failed_run_missing_values_exported_correctly(tmp_path) -> None:
    folder = _export(tmp_path, [_result("RRT*", 3, success=False)])

    row = _read_csv(folder / "runs.csv")[0]

    assert row["status"] == TIMEOUT
    assert row["success"] == "False"
    assert row["completion_time_s"] == ""
    assert row["planned_path_length"] == ""
    assert row["actual_distance_travelled"] == ""
    assert row["nodes_expanded"] == "120"


def test_utf8_export(tmp_path) -> None:
    manager = _manager([_result("A*", 1, success=True)], experiment_name="Planner Comparison - Café")

    folder = ExperimentExporter(tmp_path).export(manager, datetime(2026, 8, 17, 14, 35, 0))

    text = (folder / "config.json").read_text(encoding="utf-8")
    assert "Café" in text


def test_duplicate_export_does_not_overwrite_previous_experiment(tmp_path) -> None:
    manager = _manager([_result("A*", 1, success=True)])
    exporter = ExperimentExporter(tmp_path)
    timestamp = datetime(2026, 8, 17, 14, 35, 0)

    first = exporter.export(manager, timestamp)
    second = exporter.export(manager, timestamp)

    assert first != second
    assert first.exists()
    assert second.exists()
    assert second.name.endswith("_2")


def test_raw_json_export_can_be_loaded_again(tmp_path) -> None:
    folder = _export(tmp_path, [_result("A*", 1, success=True), _result("Dijkstra", 1, success=True)])

    payload = json.loads((folder / "raw_results.json").read_text(encoding="utf-8"))

    assert payload["config"]["scenario_name"] == "House Layout"
    assert len(payload["individual_runs"]) == 2
    assert len(payload["grouped_summaries"]) == 2


def _export(tmp_path, results: list[ExperimentResult]):
    manager = _manager(results)
    return ExperimentExporter(tmp_path).export(manager, datetime(2026, 8, 17, 14, 35, 0))


def _manager(results: list[ExperimentResult], experiment_name: str = "Planner Comparison") -> ExperimentManager:
    manager = ExperimentManager()
    manager.config = ExperimentConfig(
        experiment_name=experiment_name,
        scenario_name="House Layout",
        planners=("A*", "Dijkstra", "RRT*"),
        runs_per_planner=3,
        lidar_noise_level="Medium",
        random_seed=42,
    )
    manager.results = results
    return manager


def _read_csv(path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _result(
    planner: str,
    run_number: int,
    *,
    success: bool,
    completion_time: float | None = 10.0,
) -> ExperimentResult:
    return ExperimentResult(
        experiment_name="Planner Comparison",
        scenario="House Layout",
        planner=planner,
        run_number=run_number,
        random_seed=42 + run_number,
        outcome=SUCCESS if success else TIMEOUT,
        success=success,
        completion_time=completion_time if success else None,
        path_length=510.0,
        actual_distance=520.0,
        replans=1,
        collisions=0,
        goal_distance=0.0 if success else 84.0,
        initial_planning_time=2.4,
        average_planning_time=2.8,
        total_planning_time=8.4,
        nodes_expanded=120,
        average_odometry_error=1.8,
        final_odometry_error=2.0,
        average_ekf_error=1.2,
        final_ekf_error=1.4,
        maximum_ekf_error=2.2,
        average_fps=58.0,
        average_lidar_update_time=0.6,
        average_mapping_time=0.9,
        energy_consumed=4.5,
        final_battery_percentage=95.5,
        charging_stops=0,
    )
