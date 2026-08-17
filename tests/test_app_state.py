from environment.scenario_manager import ScenarioManager, ScenarioSummary
from ui.app_state import HOME, REPLAY, RESULTS, SIMULATION, AppController, MODE_MANUAL
from visualization.lidar_view import LIDAR_VIEW_FULL


def test_app_starts_in_home_state() -> None:
    controller = AppController()

    assert controller.state == HOME


def test_scenario_can_be_selected() -> None:
    controller = AppController()

    controller.select_scenario(2)

    assert controller.settings.scenario_index == 2
    assert controller.scenario_manager.current_scenario.name == "House Layout"


def test_selected_scenario_is_passed_to_simulation() -> None:
    controller = AppController()
    controller.select_scenario(3)

    settings = controller.start_simulation()

    assert controller.state == SIMULATION
    assert settings.scenario_index == 3


def test_planner_selection_works() -> None:
    controller = AppController()

    controller.set_planner("Dijkstra")

    assert controller.settings.planner == "Dijkstra"


def test_simulation_settings_persist_correctly() -> None:
    controller = AppController()

    controller.set_planner("RRT*")
    controller.set_mode(MODE_MANUAL)
    controller.set_lidar_view_mode(LIDAR_VIEW_FULL)
    settings = controller.start_simulation()

    assert settings.planner == "RRT*"
    assert settings.mode == MODE_MANUAL
    assert settings.lidar_view_mode == LIDAR_VIEW_FULL


def test_return_to_home_safely_stops_robot() -> None:
    controller = AppController()
    controller.start_simulation()

    controller.return_home()

    assert controller.state == HOME
    assert controller.robot_stopped


def test_next_scenario_selection_works() -> None:
    controller = AppController()
    controller.select_scenario(0)

    controller.select_next_scenario()

    assert controller.settings.scenario_index == 1


def test_final_scenario_results_do_not_crash() -> None:
    controller = AppController()
    controller.select_scenario(controller.scenario_manager.total_scenarios - 1)
    controller.show_results(_summary("Office"))

    next_settings = controller.next_scenario_from_results()

    assert next_settings is None
    assert controller.state == HOME


def test_replay_selection_launches_replay_state() -> None:
    controller = AppController()

    controller.launch_replay("logs/run_test.jsonl")

    assert controller.state == REPLAY
    assert controller.selected_replay_file == "logs/run_test.jsonl"


def test_scenario_manager_remains_source_of_scenario_data() -> None:
    manager = ScenarioManager()
    controller = AppController(manager)

    assert controller.scenario_manager.scenarios is manager.scenarios


def _summary(name: str) -> ScenarioSummary:
    return ScenarioSummary(
        name=name,
        planner="A*",
        completion_time=12.0,
        path_length=300.0,
        replans=1,
        collisions=0,
        ekf_error=2.0,
    )
