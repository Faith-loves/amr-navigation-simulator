from environment.scenario import Scenario, build_grid, cell_center
from environment.scenario_manager import ScenarioManager
from experiments.experiment_config import ExperimentConfig
from experiments.experiment_manager import ExperimentManager
from experiments.experiment_result import NO_PATH, SUCCESS, TIMEOUT
from experiments.experiment_runner import ExperimentRunContext, ExperimentRunner


def test_experiment_config_creation() -> None:
    config = ExperimentConfig(scenario_name="House Layout", planners=("A*",), runs_per_planner=3)

    assert config.scenario_name == "House Layout"
    assert config.total_runs == 3
    assert config.random_seed == 42


def test_experiment_runner_resets_between_runs() -> None:
    runner = ExperimentRunner()
    config = ExperimentConfig(planners=("A*",), runs_per_planner=3, scenario_name="Open Space")

    runner.run(config)

    assert runner.reset_count == 3


def test_selected_planners_execute_correct_number_of_runs() -> None:
    manager = ExperimentManager()
    config = ExperimentConfig(planners=("A*", "Dijkstra", "RRT*"), runs_per_planner=3, scenario_name="House Layout")

    results = manager.run_experiment(config)

    assert len(results) == 9
    assert [result.planner for result in results].count("A*") == 3
    assert [result.planner for result in results].count("Dijkstra") == 3
    assert [result.planner for result in results].count("RRT*") == 3


def test_timeout_ends_run() -> None:
    runner = ExperimentRunner()
    scenario = ScenarioManager().current_scenario
    config = ExperimentConfig(planners=("A*",), runs_per_planner=1, timeout_seconds=0.01)

    result = runner.run_single(config, scenario, ExperimentRunContext("A*", 1, 1, 1, 42))

    assert result.outcome == TIMEOUT
    assert not result.success


def test_successful_goal_produces_success() -> None:
    result = ExperimentRunner().run(ExperimentConfig(planners=("A*",), runs_per_planner=1, scenario_name="Open Space"))[0]

    assert result.outcome == SUCCESS
    assert result.success
    assert result.completion_time is not None


def test_no_path_produces_no_path() -> None:
    scenario = _blocked_scenario()
    runner = ExperimentRunner()
    config = ExperimentConfig(planners=("A*",), runs_per_planner=1)

    result = runner.run_single(config, scenario, ExperimentRunContext("A*", 1, 1, 1, 42))

    assert result.outcome == NO_PATH
    assert not result.success


def test_result_contains_required_metrics() -> None:
    result = ExperimentRunner().run(ExperimentConfig(planners=("A*",), runs_per_planner=1, scenario_name="Open Space"))[0]

    assert result.experiment_name
    assert result.scenario
    assert result.planner == "A*"
    assert result.nodes_expanded >= 0
    assert result.average_fps > 0
    assert result.average_lidar_update_time >= 0
    assert result.average_mapping_time >= 0


def test_same_seed_produces_reproducible_results() -> None:
    config = ExperimentConfig(planners=("A*", "RRT*"), runs_per_planner=2, scenario_name="House Layout", random_seed=42)

    first = ExperimentRunner().run(config)
    second = ExperimentRunner().run(config)

    assert [(result.planner, result.run_number, result.random_seed, result.outcome) for result in first] == [
        (result.planner, result.run_number, result.random_seed, result.outcome)
        for result in second
    ]


def test_scenario_goal_remains_fixed_across_planner_comparison() -> None:
    runner = ExperimentRunner()
    config = ExperimentConfig(planners=("A*", "Dijkstra", "RRT*"), runs_per_planner=2, scenario_name="Warehouse")

    runner.run(config)

    assert len(set(runner.goal_cells_seen)) == 1


def test_grouped_success_rate_calculation() -> None:
    manager = ExperimentManager()
    config = ExperimentConfig(planners=("A*",), runs_per_planner=3, scenario_name="Open Space")

    manager.run_experiment(config)
    summary = manager.grouped_summaries()[0]

    assert summary.planner == "A*"
    assert summary.total_runs == 3
    assert summary.success_rate == 1.0


def test_failed_runs_handled_correctly() -> None:
    manager = ExperimentManager()
    runner = ExperimentRunner()
    config = ExperimentConfig(planners=("A*",), runs_per_planner=1)
    failed = runner.run_single(config, _blocked_scenario(), ExperimentRunContext("A*", 1, 1, 1, 42))
    manager.results = [failed]

    summary = manager.grouped_summaries()[0]

    assert summary.successful_runs == 0
    assert summary.average_completion_time is None


def test_cancelling_experiment_exits_safely() -> None:
    manager = ExperimentManager()
    config = ExperimentConfig(planners=("A*", "Dijkstra"), runs_per_planner=5, scenario_name="Open Space")

    def cancel_on_first_progress(_progress) -> None:
        manager.cancel()

    results = manager.run_experiment(config, cancel_on_first_progress)

    assert manager.cancelled
    assert len(results) <= 1


def _blocked_scenario() -> Scenario:
    start_x, start_y = cell_center(1, 1)
    goal_x, goal_y = cell_center(3, 3)
    return Scenario(
        name="Blocked",
        description="No route",
        difficulty="Test",
        grid=build_grid(rows=5, cols=5, rectangles=[(2, 1, 1, 3)]),
        robot_start_x=start_x,
        robot_start_y=start_y,
        robot_start_theta=0.0,
        goal_x=goal_x,
        goal_y=goal_y,
    )
