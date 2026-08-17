import pygame

from environment.scenario_manager import ScenarioManager, ScenarioSummary
from ui.app_state import SimulationSettings
from ui.components import draw_button, draw_card, draw_metric_card
from ui.theme import Theme, load_fonts
from visualization.pygame_dashboard import WINDOW_HEIGHT, WINDOW_WIDTH


class ResultsScreen:
    def __init__(self, scenario_manager: ScenarioManager, settings: SimulationSettings) -> None:
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("AMR Navigation Simulator - Results")
        self.clock = pygame.time.Clock()
        self.scenario_manager = scenario_manager
        self.settings = settings
        fonts = load_fonts()
        self.font = fonts.section
        self.small_font = fonts.body
        self.title_font = fonts.app_title
        self.background = Theme.BACKGROUND
        self.panel = Theme.SURFACE
        self.inner = Theme.CARD
        self.border = Theme.BORDER
        self.text = Theme.TEXT_PRIMARY
        self.subtle = Theme.TEXT_SECONDARY
        self.accent = Theme.PRIMARY
        self.buttons: dict[str, pygame.Rect] = {}

    def run(self, summary: ScenarioSummary | None) -> str:
        while True:
            mouse_pos = pygame.mouse.get_pos()
            for event in pygame.event.get():
                action = self._handle_event(event)
                if action:
                    return action
            self.draw(summary, mouse_pos)
            self.clock.tick(60)

    def draw(self, summary: ScenarioSummary | None, mouse_pos: tuple[int, int]) -> None:
        self.buttons = {}
        self.screen.fill(self.background)
        panel = pygame.Rect(260, 88, 680, 520)
        draw_card(self.screen, panel)

        title = self.title_font.render("MISSION COMPLETE", True, self.text)
        self.screen.blit(title, (panel.centerx - title.get_width() // 2, panel.y + 34))

        rows = self._rows(summary)[:6]
        card_w = 180
        for index, (label, value) in enumerate(rows):
            col = index % 3
            row = index // 3
            metric_rect = pygame.Rect(panel.x + 56 + col * (card_w + 18), panel.y + 110 + row * 84, card_w, 66)
            draw_metric_card(self.screen, metric_rect, value, label, self.font, self.small_font, tone=Theme.ACCENT if label == "Completion Time" else Theme.TEXT_PRIMARY)

        next_label = "FINISH / HOME" if self.settings.scenario_index >= self.scenario_manager.total_scenarios - 1 else "NEXT SCENARIO"
        buttons = [
            ("next", next_label),
            ("retry", "RETRY"),
            ("home", "HOME"),
            ("replay", "REPLAY RUN"),
        ]
        x = panel.x + 78
        for name, label in buttons:
            rect = pygame.Rect(x, panel.bottom - 72, 126, 36)
            self._draw_button(name, rect, label, mouse_pos, primary=name == "next")
            x += 138

        pygame.display.flip()

    def _handle_event(self, event: pygame.event.Event) -> str | None:
        if event.type == pygame.QUIT:
            return "QUIT"
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return "HOME"
            if event.key == pygame.K_RETURN:
                return "NEXT"
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for name, rect in self.buttons.items():
                if rect.collidepoint(event.pos):
                    return name.upper()
        return None

    def _rows(self, summary: ScenarioSummary | None) -> list[tuple[str, str]]:
        if summary is None:
            return [("Result", "No run summary available")]
        return [
            ("Scenario", summary.name),
            ("Planner", summary.planner),
            ("Completion Time", f"{summary.completion_time:.1f}s"),
            ("Path Length", f"{summary.path_length:.0f}px"),
            ("Replans", str(summary.replans)),
            ("Collisions", str(summary.collisions)),
            ("Odometry Error", "Captured in simulator"),
            ("EKF Error", "--" if summary.ekf_error is None else f"{summary.ekf_error:.1f}px"),
            ("Battery Start", f"{summary.battery_start:.0f}%"),
            ("Battery End", f"{summary.battery_end:.0f}%"),
            ("Energy Used", f"{summary.energy_used:.2f}"),
            ("Charging Stops", str(summary.charging_stops)),
            ("Energy / Distance", f"{summary.energy_per_distance:.4f}"),
            ("Planning Time", "See profiler / logs"),
        ]

    def _draw_button(self, name: str, rect: pygame.Rect, label: str, mouse_pos: tuple[int, int], primary: bool = False) -> None:
        self.buttons[name] = rect
        draw_button(self.screen, rect, label, self.small_font, mouse_pos, variant="primary" if primary else "secondary")
