from dataclasses import dataclass

from environment.scenario import Scenario
from environment.scenario_manager import ScenarioManager, ScenarioSummary
from visualization.lidar_view import LIDAR_VIEW_MINIMAL


HOME = "HOME"
SIMULATION = "SIMULATION"
RESULTS = "RESULTS"
REPLAY = "REPLAY"
MAP_EDITOR = "MAP_EDITOR"
EXPERIMENT_SETUP = "EXPERIMENT_SETUP"
EXPERIMENT_RUNNING = "EXPERIMENT_RUNNING"
EXPERIMENT_RESULTS = "EXPERIMENT_RESULTS"

MODE_MANUAL = "Manual"
MODE_AUTONOMOUS = "Autonomous"
MODE_EXPLORATION = "Exploration"


@dataclass
class SimulationSettings:
    scenario_index: int = 0
    planner: str = "A*"
    mode: str = MODE_AUTONOMOUS
    lidar_view_mode: int = LIDAR_VIEW_MINIMAL
    lidar_noise: str = "Medium"
    dynamic_obstacles_enabled: bool = True
    show_localization: bool = True
    show_planned_path: bool = True
    auto_advance: bool = False
    battery_simulation_enabled: bool = True
    auto_return_to_charger: bool = True
    custom_scenario: Scenario | None = None
    custom_map_name: str = ""
    custom_semantic_locations: dict[str, tuple[int, int]] | None = None


@dataclass
class SimulationOutcome:
    action: str
    summary: ScenarioSummary | None = None
    replay_file: str = ""


class AppController:
    def __init__(self, scenario_manager: ScenarioManager | None = None) -> None:
        self.scenario_manager = scenario_manager or ScenarioManager()
        self.state = HOME
        self.settings = SimulationSettings()
        self.latest_summary: ScenarioSummary | None = None
        self.selected_replay_file = ""
        self.editor_source_path = ""
        self.robot_stopped = False
        self.experiment_config = None

    def select_scenario(self, index: int) -> None:
        self.scenario_manager.load_scenario(index)
        self.settings.scenario_index = index

    def select_next_scenario(self) -> None:
        next_index = (self.settings.scenario_index + 1) % self.scenario_manager.total_scenarios
        self.select_scenario(next_index)

    def select_previous_scenario(self) -> None:
        previous_index = (self.settings.scenario_index - 1) % self.scenario_manager.total_scenarios
        self.select_scenario(previous_index)

    def set_planner(self, planner: str) -> None:
        self.settings.planner = planner

    def set_mode(self, mode: str) -> None:
        self.settings.mode = mode

    def set_lidar_view_mode(self, lidar_view_mode: int) -> None:
        self.settings.lidar_view_mode = lidar_view_mode

    def configure_demo_mode(self) -> None:
        for index, scenario in enumerate(self.scenario_manager.scenarios):
            if scenario.name == "Warehouse":
                self.select_scenario(index)
                break
        self.settings.planner = "A*"
        self.settings.mode = MODE_AUTONOMOUS
        self.settings.lidar_view_mode = LIDAR_VIEW_MINIMAL
        self.settings.dynamic_obstacles_enabled = True
        self.settings.show_localization = True
        self.settings.show_planned_path = True
        self.settings.battery_simulation_enabled = True
        self.settings.auto_return_to_charger = True
        self.settings.custom_scenario = None
        self.settings.custom_map_name = ""
        self.settings.custom_semantic_locations = None

    def start_simulation(self) -> SimulationSettings:
        self.state = SIMULATION
        self.robot_stopped = False
        self.settings.custom_scenario = None
        self.settings.custom_map_name = ""
        self.settings.custom_semantic_locations = None
        self.scenario_manager.load_scenario(self.settings.scenario_index)
        return self.settings

    def start_custom_simulation(self) -> SimulationSettings:
        self.state = SIMULATION
        self.robot_stopped = False
        return self.settings

    def open_map_editor(self, source_path: str = "") -> None:
        self.editor_source_path = source_path
        self.state = MAP_EDITOR

    def open_experiments(self) -> None:
        self.state = EXPERIMENT_SETUP

    def start_experiment(self, config) -> None:
        self.experiment_config = config
        self.state = EXPERIMENT_RUNNING

    def show_experiment_results(self) -> None:
        self.state = EXPERIMENT_RESULTS

    def return_home(self) -> None:
        self.state = HOME
        self.robot_stopped = True

    def show_results(self, summary: ScenarioSummary | None) -> None:
        self.latest_summary = summary
        self.state = RESULTS

    def retry(self) -> SimulationSettings:
        if self.settings.custom_scenario is not None:
            return self.start_custom_simulation()
        return self.start_simulation()

    def next_scenario_from_results(self) -> SimulationSettings | None:
        if self.settings.custom_scenario is not None:
            self.return_home()
            return None
        if self.settings.scenario_index >= self.scenario_manager.total_scenarios - 1:
            self.return_home()
            return None
        self.select_scenario(self.settings.scenario_index + 1)
        return self.start_simulation()

    def launch_replay(self, replay_file: str = "") -> None:
        self.selected_replay_file = replay_file
        self.state = REPLAY
