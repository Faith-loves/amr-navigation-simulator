from pathlib import Path

import pygame

from robot.state import RobotState
from editor.map_editor import MapEditor
from editor.map_serializer import load_custom_map
from experiments.experiment_manager import ExperimentManager
from simulator.simulation_loop import run_simulation
from utils.startup_validation import ensure_startup_directories
from ui.app_state import EXPERIMENT_RESULTS, EXPERIMENT_RUNNING, EXPERIMENT_SETUP, HOME, MAP_EDITOR, REPLAY, RESULTS, SIMULATION, AppController, SimulationOutcome
from ui.experiment_results_screen import ExperimentResultsDashboard
from ui.experiment_screens import ExperimentProgressScreen, ExperimentSetupScreen
from ui.home_screen import HomeScreen
from ui.results_screen import ResultsScreen
from visualization.pygame_dashboard import MAP_HEIGHT, MAP_WIDTH


class AMRApplication:
    def __init__(self) -> None:
        ensure_startup_directories()
        self.controller = AppController()
        self.experiment_manager = ExperimentManager()

    def run(self) -> None:
        running = True
        while running:
            if self.controller.state == HOME:
                action, settings = HomeScreen(
                    self.controller.scenario_manager,
                    self.controller.settings,
                ).run(self.controller.latest_summary)
                if action == "QUIT":
                    running = False
                elif action == "START":
                    self.controller.start_simulation()
                elif action == "REPLAY":
                    self.controller.launch_replay(self._latest_log_file())
                elif action == "MAP_EDITOR":
                    self.controller.open_map_editor()
                elif action.startswith("EDIT_CUSTOM:"):
                    self.controller.open_map_editor(action.split(":", 1)[1])
                elif action.startswith("RUN_CUSTOM:"):
                    self._load_custom_for_simulation(action.split(":", 1)[1])
                elif action == "EXPERIMENTS":
                    self.controller.open_experiments()
                elif action == "DEMO_MODE":
                    self.controller.configure_demo_mode()
                    self.controller.start_simulation()

            elif self.controller.state == EXPERIMENT_SETUP:
                action, config = ExperimentSetupScreen(self.controller.scenario_manager, self.experiment_manager).run()
                if action == "RUN" and config is not None:
                    self.controller.start_experiment(config)
                else:
                    self.controller.return_home()

            elif self.controller.state == EXPERIMENT_RUNNING:
                if self.controller.experiment_config is None:
                    self.controller.return_home()
                else:
                    action = ExperimentProgressScreen(self.experiment_manager).run(self.controller.experiment_config)
                    if action == "DONE":
                        self.controller.show_experiment_results()
                    else:
                        self.controller.open_experiments()

            elif self.controller.state == EXPERIMENT_RESULTS:
                action = ExperimentResultsDashboard(self.experiment_manager).run()
                if action == "NEW_EXPERIMENT":
                    self.controller.open_experiments()
                elif action == "REPLAY_RUN":
                    self.controller.launch_replay(self._latest_log_file())
                elif action == "EXPORT_DATA":
                    self.controller.show_experiment_results()
                else:
                    self.controller.return_home()

            elif self.controller.state == MAP_EDITOR:
                custom_map = None
                if self.controller.editor_source_path:
                    custom_map = load_custom_map(self.controller.editor_source_path)
                action, settings, edited_map, source_path = MapEditor(
                    custom_map,
                    self.controller.settings,
                    self.controller.editor_source_path,
                ).run()
                self.controller.editor_source_path = source_path
                if action == "RUN_CUSTOM":
                    self.controller.start_custom_simulation()
                else:
                    self.controller.return_home()

            elif self.controller.state == SIMULATION:
                robot_state = RobotState(MAP_WIDTH / 2, MAP_HEIGHT / 2, 0.0)
                outcome = run_simulation(robot_state, self.controller.settings)
                self._handle_simulation_outcome(outcome)

            elif self.controller.state == RESULTS:
                action = ResultsScreen(
                    self.controller.scenario_manager,
                    self.controller.settings,
                ).run(self.controller.latest_summary)
                if action == "QUIT":
                    running = False
                elif action == "HOME":
                    self.controller.return_home()
                elif action == "RETRY":
                    self.controller.retry()
                elif action == "REPLAY":
                    self.controller.launch_replay(self._latest_log_file())
                elif action == "NEXT":
                    self.controller.next_scenario_from_results()

            elif self.controller.state == REPLAY:
                robot_state = RobotState(MAP_WIDTH / 2, MAP_HEIGHT / 2, 0.0)
                outcome = run_simulation(robot_state, self.controller.settings, replay_file=self.controller.selected_replay_file)
                self._handle_simulation_outcome(outcome)

        pygame.quit()

    def _handle_simulation_outcome(self, outcome: SimulationOutcome | None) -> None:
        if outcome is None:
            self.controller.return_home()
            return
        if outcome.action == "RESULTS":
            self.controller.show_results(outcome.summary)
        elif outcome.action == "HOME":
            self.controller.return_home()
        elif outcome.action == "REPLAY":
            self.controller.launch_replay(outcome.replay_file)
        else:
            self.controller.return_home()

    def _load_custom_for_simulation(self, path: str) -> None:
        custom_map = load_custom_map(path)
        self.controller.settings.custom_scenario = custom_map.to_scenario()
        self.controller.settings.custom_map_name = custom_map.name
        self.controller.settings.custom_semantic_locations = dict(custom_map.semantic_locations)
        self.controller.start_custom_simulation()

    def _latest_log_file(self) -> str:
        logs = sorted(Path("logs").glob("run_*.jsonl"), key=lambda path: path.stat().st_mtime, reverse=True)
        return str(logs[0]) if logs else ""
