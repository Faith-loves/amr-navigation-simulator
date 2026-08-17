from pathlib import Path

from experiments.experiment_analysis import (
    best_unique,
    format_mean_std,
    generate_observations,
    mean,
    metric_stats,
    planner_analyses,
    standard_deviation,
    summary_cards,
)
from experiments.experiment_manager import ExperimentManager
from experiments.experiment_result import ExperimentResult, SUCCESS, TIMEOUT


def test_mean_calculation() -> None:
    assert mean([10.0, 14.0, 18.0]) == 14.0
    assert mean([]) is None


def test_standard_deviation_calculation() -> None:
    assert round(standard_deviation([10.0, 12.0, 14.0]), 3) == 2.0
    assert standard_deviation([10.0]) is None


def test_success_rate_calculation() -> None:
    manager = ExperimentManager()
    manager.results = [
        _result("A*", 1, success=True),
        _result("A*", 2, success=True),
        _result("A*", 3, success=False),
    ]

    summary = manager.grouped_summaries()[0]

    assert summary.success_rate == 2 / 3


def test_failed_runs_excluded_from_completion_time_averages() -> None:
    manager = ExperimentManager()
    manager.results = [
        _result("A*", 1, success=True, completion_time=10.0),
        _result("A*", 2, success=False, completion_time=None),
        _result("A*", 3, success=True, completion_time=14.0),
    ]

    summary = manager.grouped_summaries()[0]
    analysis = planner_analyses(manager.results, [summary])[0]

    assert summary.average_completion_time == 12.0
    assert analysis.completion_time.mean == 12.0
    assert analysis.completion_time.count == 2


def test_tie_handling_does_not_declare_winner() -> None:
    manager = ExperimentManager()
    manager.results = [
        _result("A*", 1, success=True, completion_time=10.0),
        _result("Dijkstra", 1, success=True, completion_time=10.0),
    ]
    analyses = planner_analyses(manager.results, manager.grouped_summaries())

    assert best_unique(analyses, lambda analysis: analysis.completion_time.mean) == "Tie"
    assert summary_cards(analyses)["FASTEST PLANNER"] == "Tie"


def test_observation_generation_uses_actual_metrics() -> None:
    manager = ExperimentManager()
    manager.results = [
        _result("A*", 1, success=True, completion_time=9.0, planning_time=2.0, nodes=100),
        _result("A*", 2, success=True, completion_time=11.0, planning_time=2.2, nodes=120),
        _result("Dijkstra", 1, success=True, completion_time=12.0, planning_time=6.0, nodes=420),
        _result("Dijkstra", 2, success=True, completion_time=14.0, planning_time=6.2, nodes=440),
    ]
    analyses = planner_analyses(manager.results, manager.grouped_summaries())

    observations = generate_observations(analyses)

    assert any("A* achieved the lowest average completion time" in item for item in observations)
    assert any("Dijkstra expanded" in item and "A*" in item for item in observations)


def test_one_planner_does_not_cause_comparison_errors() -> None:
    manager = ExperimentManager()
    manager.results = [_result("A*", 1, success=True)]
    analyses = planner_analyses(manager.results, manager.grouped_summaries())

    cards = summary_cards(analyses)

    assert cards["BEST SUCCESS RATE"] == "Insufficient data"
    assert cards["FASTEST PLANNER"] == "Insufficient data"
    assert generate_observations(analyses)


def test_one_run_handles_standard_deviation_safely() -> None:
    stats = metric_stats([12.4])

    assert stats.mean == 12.4
    assert stats.stddev is None
    assert format_mean_std(stats, "s") == "12.4s"


def test_all_failed_experiment_does_not_crash_analysis() -> None:
    manager = ExperimentManager()
    manager.results = [
        _result("A*", 1, success=False),
        _result("Dijkstra", 1, success=False),
    ]
    analyses = planner_analyses(manager.results, manager.grouped_summaries())

    cards = summary_cards(analyses)
    observations = generate_observations(analyses)

    assert cards["FASTEST PLANNER"] == "Insufficient data"
    assert observations


def test_results_screen_contains_required_dashboard_sections() -> None:
    source = Path("ui/experiment_results_screen.py").read_text()

    for label in ["OVERVIEW", "NAVIGATION", "PLANNING", "LOCALIZATION", "RUNS"]:
        assert label in source
    for label in ["NEW EXPERIMENT", "EXPORT DATA", "HOME", "REPLAY RUN"]:
        assert label in source
    assert "Export writes CSV and JSON experiment data." in source
    assert "EXPORT COMPLETE" in source


def _result(
    planner: str,
    run_number: int,
    *,
    success: bool,
    completion_time: float | None = None,
    planning_time: float = 3.0,
    nodes: int = 100,
    path_length: float = 500.0,
    ekf_error: float = 2.0,
) -> ExperimentResult:
    return ExperimentResult(
        experiment_name="Planner Comparison - House",
        scenario="House",
        planner=planner,
        run_number=run_number,
        random_seed=42 + run_number,
        outcome=SUCCESS if success else TIMEOUT,
        success=success,
        completion_time=completion_time if success else None,
        path_length=path_length,
        actual_distance=path_length,
        replans=1,
        collisions=0,
        goal_distance=0.0 if success else 90.0,
        initial_planning_time=planning_time,
        average_planning_time=planning_time,
        total_planning_time=planning_time,
        nodes_expanded=nodes,
        average_odometry_error=1.0,
        final_odometry_error=1.2,
        average_ekf_error=ekf_error,
        final_ekf_error=ekf_error,
        maximum_ekf_error=ekf_error + 0.5,
        average_fps=60.0,
        average_lidar_update_time=0.5,
        average_mapping_time=0.7,
    )
