from __future__ import annotations

import pygame

from environment.scenario_manager import ScenarioManager
from experiments.experiment_config import ExperimentConfig, NOISE_LEVELS, PLANNERS, RUN_OPTIONS
from experiments.experiment_manager import ExperimentManager
from experiments.experiment_result import PlannerSummary
from ui.components import draw_button, draw_card, draw_progress_bar
from ui.theme import Theme, load_fonts
from visualization.pygame_dashboard import WINDOW_HEIGHT, WINDOW_WIDTH


class ExperimentSetupScreen:
    def __init__(self, scenario_manager: ScenarioManager, manager: ExperimentManager) -> None:
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("AMR Navigation Simulator - Experiments")
        self.clock = pygame.time.Clock()
        self.scenario_manager = scenario_manager
        self.manager = manager
        fonts = load_fonts()
        self.font = fonts.section
        self.small_font = fonts.body
        self.title_font = fonts.page_title
        self.background = Theme.BACKGROUND
        self.panel = Theme.SURFACE
        self.inner = Theme.CARD
        self.border = Theme.BORDER
        self.text = Theme.TEXT_PRIMARY
        self.subtle = Theme.TEXT_SECONDARY
        self.accent = Theme.PRIMARY
        self.buttons: dict[str, pygame.Rect] = {}
        self.scenario_name = "House Layout"
        self.selected_planners = {"A*", "Dijkstra", "RRT*"}
        self.runs_per_planner = 3
        self.noise = "Medium"
        self.dynamic_obstacles_enabled = False
        self.battery_enabled = False
        self.random_seed = 42

    def run(self) -> tuple[str, ExperimentConfig | None]:
        while True:
            mouse_pos = pygame.mouse.get_pos()
            for event in pygame.event.get():
                action = self._handle_event(event)
                if action:
                    return action
            self.draw(mouse_pos)
            self.clock.tick(60)

    def draw(self, mouse_pos: tuple[int, int]) -> None:
        self.buttons = {}
        self.screen.fill(self.background)
        self.screen.blit(self.title_font.render("EXPERIMENT SETUP", True, self.text), (34, 28))
        self.screen.blit(self.small_font.render("Automated planner comparison with fixed scenario objectives and controlled seeds.", True, self.subtle), (34, 64))
        panel = pygame.Rect(120, 102, 960, 500)
        draw_card(self.screen, panel)
        y = panel.y + 28
        self._section("SCENARIO", panel.x + 32, y)
        x = panel.x + 170
        for scenario in self.scenario_manager.scenarios:
            self._button(f"scenario:{scenario.name}", pygame.Rect(x, y - 6, 134, 28), scenario.name[:15], mouse_pos, selected=self.scenario_name == scenario.name)
            x += 144
        y += 62
        self._section("PLANNERS", panel.x + 32, y)
        x = panel.x + 170
        for planner in PLANNERS:
            self._button(f"planner:{planner}", pygame.Rect(x, y - 6, 110, 28), planner, mouse_pos, selected=planner in self.selected_planners)
            x += 120
        y += 62
        self._section("RUNS", panel.x + 32, y)
        x = panel.x + 170
        for runs in RUN_OPTIONS:
            self._button(f"runs:{runs}", pygame.Rect(x, y - 6, 70, 28), str(runs), mouse_pos, selected=self.runs_per_planner == runs)
            x += 82
        y += 62
        self._section("LIDAR NOISE", panel.x + 32, y)
        x = panel.x + 170
        for noise in NOISE_LEVELS:
            self._button(f"noise:{noise}", pygame.Rect(x, y - 6, 92, 28), noise, mouse_pos, selected=self.noise == noise)
            x += 102
        y += 62
        self._section("OPTIONS", panel.x + 32, y)
        self._button("dynamic", pygame.Rect(panel.x + 170, y - 6, 150, 28), f"Dynamic: {'On' if self.dynamic_obstacles_enabled else 'Off'}", mouse_pos, selected=self.dynamic_obstacles_enabled)
        self._button("battery", pygame.Rect(panel.x + 334, y - 6, 150, 28), f"Battery: {'On' if self.battery_enabled else 'Off'}", mouse_pos, selected=self.battery_enabled)
        self._section("SEED", panel.x + 530, y)
        self._button("seed_down", pygame.Rect(panel.x + 600, y - 6, 34, 28), "-", mouse_pos)
        self.screen.blit(self.font.render(str(self.random_seed), True, self.text), (panel.x + 646, y))
        self._button("seed_up", pygame.Rect(panel.x + 714, y - 6, 34, 28), "+", mouse_pos)

        total = len(self.selected_planners) * self.runs_per_planner
        self.screen.blit(self.font.render(f"Total runs: {total}", True, self.accent), (panel.x + 32, panel.bottom - 84))
        self._button("run", pygame.Rect(panel.right - 238, panel.bottom - 92, 180, 42), "RUN EXPERIMENT", mouse_pos, primary=True)
        self._button("home", pygame.Rect(panel.x + 32, panel.bottom - 92, 120, 42), "HOME", mouse_pos)
        pygame.display.flip()

    def _handle_event(self, event: pygame.event.Event) -> tuple[str, ExperimentConfig | None] | None:
        if event.type == pygame.QUIT:
            return "HOME", None
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            return "HOME", None
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for name, rect in self.buttons.items():
                if rect.collidepoint(event.pos):
                    return self._action(name)
        return None

    def _action(self, name: str) -> tuple[str, ExperimentConfig | None] | None:
        if name == "home":
            return "HOME", None
        if name == "run" and self.selected_planners:
            return "RUN", self._config()
        if name.startswith("scenario:"):
            self.scenario_name = name.split(":", 1)[1]
        elif name.startswith("planner:"):
            planner = name.split(":", 1)[1]
            if planner in self.selected_planners and len(self.selected_planners) > 1:
                self.selected_planners.remove(planner)
            else:
                self.selected_planners.add(planner)
        elif name.startswith("runs:"):
            self.runs_per_planner = int(name.split(":", 1)[1])
        elif name.startswith("noise:"):
            self.noise = name.split(":", 1)[1]
        elif name == "dynamic":
            self.dynamic_obstacles_enabled = not self.dynamic_obstacles_enabled
        elif name == "battery":
            self.battery_enabled = not self.battery_enabled
        elif name == "seed_down":
            self.random_seed -= 1
        elif name == "seed_up":
            self.random_seed += 1
        return None

    def _config(self) -> ExperimentConfig:
        return ExperimentConfig(
            experiment_name=f"Planner Comparison - {self.scenario_name}",
            scenario_name=self.scenario_name,
            planners=tuple(planner for planner in PLANNERS if planner in self.selected_planners),
            runs_per_planner=self.runs_per_planner,
            lidar_noise_level=self.noise,
            dynamic_obstacles_enabled=self.dynamic_obstacles_enabled,
            battery_enabled=self.battery_enabled,
            random_seed=self.random_seed,
        )

    def _section(self, label: str, x: int, y: int) -> None:
        self.screen.blit(self.font.render(label, True, self.text), (x, y))

    def _button(self, name: str, rect: pygame.Rect, label: str, mouse_pos: tuple[int, int], primary: bool = False, selected: bool = False) -> None:
        self.buttons[name] = rect
        fill = self.accent if primary or selected else (31, 37, 50) if rect.collidepoint(mouse_pos) else self.inner
        color = self.background if primary or selected else self.text
        draw_button(self.screen, rect, label, self.small_font, mouse_pos, variant="primary" if primary else "secondary", selected=selected)


class ExperimentProgressScreen:
    def __init__(self, manager: ExperimentManager) -> None:
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("AMR Navigation Simulator - Experiment Running")
        self.clock = pygame.time.Clock()
        self.manager = manager
        fonts = load_fonts()
        self.font = fonts.section
        self.title_font = fonts.page_title
        self.background = Theme.BACKGROUND
        self.panel = Theme.SURFACE
        self.border = Theme.BORDER
        self.text = Theme.TEXT_PRIMARY
        self.subtle = Theme.TEXT_SECONDARY
        self.accent = Theme.PRIMARY
        self.progress: dict[str, object] = {}

    def run(self, config: ExperimentConfig) -> str:
        def update(progress: dict[str, object]) -> None:
            self.progress = progress
            self._pump_cancel_events()
            self.draw()

        self.manager.run_experiment(config, update)
        return "CANCELLED" if self.manager.cancelled else "DONE"

    def draw(self) -> None:
        self.screen.fill(self.background)
        panel = pygame.Rect(270, 150, 660, 360)
        draw_card(self.screen, panel)
        self.screen.blit(self.title_font.render("EXPERIMENT RUNNING", True, self.text), (panel.x + 42, panel.y + 36))
        rows = [
            ("Experiment", str(self.progress.get("experiment", "--"))),
            ("Scenario", str(self.progress.get("scenario", "--"))),
            ("Planner", str(self.progress.get("planner", "--"))),
            ("Run", f"{self.progress.get('run', '--')} / {self.progress.get('runs_per_planner', '--')}"),
            ("Overall", f"{self.progress.get('overall', '--')} / {self.progress.get('total', '--')}"),
            ("Status", str(self.progress.get("status", "Navigating"))),
        ]
        y = panel.y + 100
        for label, value in rows:
            self.screen.blit(self.font.render(label, True, self.subtle), (panel.x + 42, y))
            self.screen.blit(self.font.render(value, True, self.text), (panel.x + 180, y))
            y += 32
        total = max(1, int(self.progress.get("total", 1)))
        overall = int(self.progress.get("overall", 0))
        bar = pygame.Rect(panel.x + 42, panel.bottom - 66, panel.width - 84, 18)
        draw_progress_bar(self.screen, bar, overall / total, fill=Theme.ACCENT)
        self.screen.blit(self.font.render("ESC cancels experiment", True, self.subtle), (panel.x + 42, panel.bottom - 36))
        pygame.display.flip()
        self.clock.tick(30)

    def _pump_cancel_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                self.manager.cancel()


class ExperimentResultsScreen:
    def __init__(self, manager: ExperimentManager) -> None:
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("AMR Navigation Simulator - Experiment Results")
        self.clock = pygame.time.Clock()
        self.manager = manager
        fonts = load_fonts()
        self.font = fonts.section
        self.small_font = fonts.body
        self.title_font = fonts.page_title
        self.background = Theme.BACKGROUND
        self.panel = Theme.SURFACE
        self.border = Theme.BORDER
        self.text = Theme.TEXT_PRIMARY
        self.subtle = Theme.TEXT_SECONDARY
        self.accent = Theme.PRIMARY

    def run(self) -> str:
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return "HOME"
                if event.type == pygame.KEYDOWN and event.key in {pygame.K_ESCAPE, pygame.K_RETURN}:
                    return "HOME"
            self.draw()
            self.clock.tick(60)

    def draw(self) -> None:
        self.screen.fill(self.background)
        panel = pygame.Rect(170, 90, 860, 540)
        draw_card(self.screen, panel)
        self.screen.blit(self.title_font.render("EXPERIMENT RESULTS", True, self.text), (panel.x + 36, panel.y + 30))
        y = panel.y + 92
        headers = ["Planner", "Runs", "Success", "Avg Time", "Avg Path", "Avg Replans", "Avg EKF"]
        xs = [panel.x + 36, panel.x + 170, panel.x + 250, panel.x + 350, panel.x + 470, panel.x + 590, panel.x + 720]
        for x, header in zip(xs, headers):
            self.screen.blit(self.small_font.render(header, True, self.accent), (x, y))
        y += 30
        for summary in self.manager.grouped_summaries():
            values = self._summary_values(summary)
            for x, value in zip(xs, values):
                self.screen.blit(self.small_font.render(value, True, self.text), (x, y))
            y += 28
        footer = "ENTER / ESC  Home"
        self.screen.blit(self.font.render(footer, True, self.subtle), (panel.x + 36, panel.bottom - 44))
        pygame.display.flip()

    def _summary_values(self, summary: PlannerSummary) -> list[str]:
        average_time = "--" if summary.average_completion_time is None else f"{summary.average_completion_time:.1f}s"
        return [
            summary.planner,
            str(summary.total_runs),
            f"{summary.success_rate * 100:.0f}%",
            average_time,
            f"{summary.average_path_length or 0.0:.0f}px",
            f"{summary.average_replans or 0.0:.1f}",
            f"{summary.average_ekf_error or 0.0:.1f}",
        ]
