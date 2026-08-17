from __future__ import annotations

import pygame

from experiments.experiment_analysis import (
    PlannerAnalysis,
    format_mean_std,
    generate_observations,
    planner_analyses,
    summary_cards,
)
from experiments.exporter import ExperimentExporter
from experiments.experiment_manager import ExperimentManager
from experiments.experiment_result import ExperimentResult
from ui.components import draw_button, draw_card, draw_metric_card, draw_tabs
from ui.theme import Theme, load_fonts
from visualization.pygame_dashboard import WINDOW_HEIGHT, WINDOW_WIDTH


TABS = ("OVERVIEW", "NAVIGATION", "PLANNING", "LOCALIZATION", "RUNS")


class ExperimentResultsDashboard:
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
        self.inner = Theme.CARD
        self.border = Theme.BORDER
        self.text = Theme.TEXT_PRIMARY
        self.subtle = Theme.TEXT_SECONDARY
        self.accent = Theme.PRIMARY
        self.warn = Theme.WARNING
        self.error = Theme.DANGER
        self.blue = Theme.PRIMARY
        self.active_tab = "OVERVIEW"
        self.scroll_offsets = {tab: 0 for tab in TABS}
        self.buttons: dict[str, pygame.Rect] = {}
        self.tab_rects: dict[str, pygame.Rect] = {}
        self.export_status = ""

    def run(self) -> str:
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
        self.tab_rects = {}
        self.screen.fill(self.background)
        config = self.manager.config
        summaries = self.manager.grouped_summaries()
        analyses = planner_analyses(self.manager.results, summaries)

        self._draw_header(config)
        self._draw_tabs(mouse_pos)
        content = pygame.Rect(28, 160, 1144, 480)
        draw_card(self.screen, content)

        previous_clip = self.screen.get_clip()
        self.screen.set_clip(content.inflate(-20, -20))
        if not self.manager.results:
            self._draw_no_data(content)
        elif self.active_tab == "OVERVIEW":
            self._draw_overview(content, analyses)
        elif self.active_tab == "NAVIGATION":
            self._draw_chart_tab(
                content,
                analyses,
                [
                    ("Completion Time (s)", lambda item: item.completion_time.mean, "s"),
                    ("Path Length (px)", lambda item: item.path_length.mean, "px"),
                    ("Success Rate (%)", lambda item: item.summary.success_rate * 100.0, "%"),
                ],
            )
        elif self.active_tab == "PLANNING":
            self._draw_chart_tab(
                content,
                analyses,
                [
                    ("Planning Time (ms)", lambda item: item.planning_time.mean, "ms"),
                    ("Nodes Expanded", lambda item: item.summary.average_nodes_expanded, ""),
                    ("Replans", lambda item: item.summary.average_replans, ""),
                ],
            )
        elif self.active_tab == "LOCALIZATION":
            self._draw_chart_tab(
                content,
                analyses,
                [
                    ("Odometry Error (px)", lambda item: item.odometry_error.mean, "px"),
                    ("EKF Error (px)", lambda item: item.ekf_error.mean, "px"),
                ],
            )
        else:
            self._draw_runs(content)
        self.screen.set_clip(previous_clip)

        self._draw_footer(mouse_pos)
        pygame.display.flip()

    def _handle_event(self, event: pygame.event.Event) -> str | None:
        if event.type == pygame.QUIT:
            return "HOME"
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return "HOME"
            if event.key == pygame.K_RIGHT:
                self._select_relative_tab(1)
            if event.key == pygame.K_LEFT:
                self._select_relative_tab(-1)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for tab, rect in self.tab_rects.items():
                if rect.collidepoint(event.pos):
                    self.active_tab = tab
                    return None
            for name, rect in self.buttons.items():
                if rect.collidepoint(event.pos):
                    if name == "EXPORT_DATA":
                        self._export_data()
                        return None
                    return name
        if event.type == pygame.MOUSEBUTTONDOWN and event.button in {4, 5}:
            delta = -26 if event.button == 4 else 26
            self._scroll(delta)
        if event.type == pygame.MOUSEWHEEL:
            self._scroll(-event.y * 26)
        return None

    def _draw_header(self, config) -> None:
        self.screen.blit(self.title_font.render("EXPERIMENT RESULTS", True, self.text), (28, 22))
        total_runs = len(self.manager.results)
        rows = [
            ("Experiment", "--" if config is None else config.experiment_name),
            ("Scenario", "--" if config is None else config.scenario_name),
            ("Runs", str(total_runs)),
            ("Seed", "--" if config is None else str(config.random_seed)),
            ("Noise", "--" if config is None else config.lidar_noise_level),
        ]
        x = 28
        y = 64
        for label, value in rows:
            self.screen.blit(self.small_font.render(label, True, self.subtle), (x, y))
            self.screen.blit(self.small_font.render(str(value), True, self.text), (x, y + 18))
            x += 220

    def _draw_tabs(self, mouse_pos: tuple[int, int]) -> None:
        self.tab_rects = draw_tabs(self.screen, list(TABS), self.active_tab, (28, 118), 790, self.small_font, mouse_pos)

    def _draw_overview(self, rect: pygame.Rect, analyses: list[PlannerAnalysis]) -> None:
        cards = summary_cards(analyses)
        x = rect.x + 18
        y = rect.y + 18
        card_width = 264
        for title, value in cards.items():
            card = pygame.Rect(x, y, card_width, 76)
            draw_metric_card(self.screen, card, value, title, self.font, self.small_font, tone=self.accent if value not in {"Tie", "Insufficient data"} else self.warn)
            x += card_width + 16

        self._draw_comparison_table(pygame.Rect(rect.x + 18, rect.y + 116, 720, 250), analyses)
        self._draw_observations(pygame.Rect(rect.x + 770, rect.y + 116, 350, 250), analyses)

    def _draw_comparison_table(self, rect: pygame.Rect, analyses: list[PlannerAnalysis]) -> None:
        headers = ["Planner", "Success", "Avg Time", "Avg Path", "Avg Planning", "Avg Nodes", "Avg Replans", "Avg EKF"]
        xs = [rect.x, rect.x + 90, rect.x + 164, rect.x + 250, rect.x + 338, rect.x + 444, rect.x + 538, rect.x + 646]
        for x, header in zip(xs, headers):
            self.screen.blit(self.small_font.render(header, True, self.accent), (x, rect.y))
        y = rect.y + 26
        for analysis in analyses:
            values = [
                analysis.summary.planner,
                f"{analysis.summary.success_rate * 100:.0f}%",
                format_mean_std(analysis.completion_time, "s"),
                format_mean_std(analysis.path_length, "px"),
                format_mean_std(analysis.planning_time, "ms"),
                f"{analysis.summary.average_nodes_expanded or 0.0:.0f}",
                f"{analysis.summary.average_replans or 0.0:.1f}",
                format_mean_std(analysis.ekf_error, "px"),
            ]
            for x, value in zip(xs, values):
                self.screen.blit(self.small_font.render(value, True, self.text), (x, y))
            y += 28
        if not analyses:
            self.screen.blit(self.font.render("No planner results available.", True, self.warn), (rect.x, rect.y + 44))

    def _draw_observations(self, rect: pygame.Rect, analyses: list[PlannerAnalysis]) -> None:
        draw_card(self.screen, rect)
        self.screen.blit(self.font.render("OBSERVATIONS", True, self.text), (rect.x + 14, rect.y + 14))
        y = rect.y + 48
        for observation in generate_observations(analyses):
            y = self._draw_wrapped(observation, rect.x + 14, y, rect.width - 28, self.subtle)
            y += 12

    def _draw_chart_tab(self, rect: pygame.Rect, analyses: list[PlannerAnalysis], charts) -> None:
        if not analyses:
            self._draw_no_data(rect)
            return
        chart_width = 352
        chart_height = 188
        positions = [
            (rect.x + 22, rect.y + 28),
            (rect.x + 396, rect.y + 28),
            (rect.x + 770, rect.y + 28),
            (rect.x + 22, rect.y + 250),
            (rect.x + 396, rect.y + 250),
            (rect.x + 770, rect.y + 250),
        ]
        for (title, getter, unit), (x, y) in zip(charts, positions):
            self._draw_bar_chart(pygame.Rect(x, y, chart_width, chart_height), title, analyses, getter, unit)

    def _draw_bar_chart(self, rect: pygame.Rect, title: str, analyses: list[PlannerAnalysis], getter, unit: str) -> None:
        draw_card(self.screen, rect)
        self.screen.blit(self.small_font.render(title, True, self.text), (rect.x + 12, rect.y + 10))
        values = [(analysis.summary.planner, getter(analysis)) for analysis in analyses if getter(analysis) is not None]
        if not values:
            self.screen.blit(self.small_font.render("N/A", True, self.warn), (rect.x + 12, rect.y + 48))
            return
        max_value = max(max(value for _planner, value in values), 1.0)
        axis = pygame.Rect(rect.x + 42, rect.y + 42, rect.width - 68, rect.height - 82)
        pygame.draw.line(self.screen, self.border, (axis.x, axis.bottom), (axis.right, axis.bottom), 1)
        bar_width = max(20, axis.width // (len(values) * 2))
        for index, (planner, value) in enumerate(values):
            bar_height = int(axis.height * float(value) / max_value)
            x = axis.x + index * (bar_width * 2) + bar_width // 2
            bar = pygame.Rect(x, axis.bottom - bar_height, bar_width, bar_height)
            pygame.draw.rect(self.screen, self.blue, bar, border_radius=3)
            self.screen.blit(self.small_font.render(planner, True, self.subtle), (x - 8, axis.bottom + 6))
            value_text = f"{float(value):.1f}{unit}"
            self.screen.blit(self.small_font.render(value_text, True, self.text), (x - 8, max(axis.y, bar.y - 18)))
        self.screen.blit(self.small_font.render(title, True, self.subtle), (rect.x + 12, rect.bottom - 22))

    def _draw_runs(self, rect: pygame.Rect) -> None:
        rows = self.manager.results
        offset = self.scroll_offsets["RUNS"]
        y = rect.y + 20 - offset
        headers = ["Run", "Planner", "Status", "Time", "Path", "Replans", "Collisions", "EKF Error"]
        xs = [rect.x + 22, rect.x + 88, rect.x + 180, rect.x + 330, rect.x + 430, rect.x + 540, rect.x + 650, rect.x + 780]
        for x, header in zip(xs, headers):
            self.screen.blit(self.small_font.render(header, True, self.accent), (x, y))
        y += 28
        for result in rows:
            if rect.y <= y <= rect.bottom - 22:
                values = [
                    str(result.run_number),
                    result.planner,
                    result.outcome,
                    "N/A" if not result.success or result.completion_time is None else f"{result.completion_time:.1f}s",
                    "N/A" if not result.success else f"{result.path_length:.0f}px",
                    str(result.replans),
                    str(result.collisions),
                    f"{result.average_ekf_error:.1f}px",
                ]
                color = self.text if result.success else self.warn
                for x, value in zip(xs, values):
                    self.screen.blit(self.small_font.render(value, True, color), (x, y))
            y += 24
        if not rows:
            self.screen.blit(self.font.render("No individual run data available.", True, self.warn), (rect.x + 22, rect.y + 54))

    def _draw_no_data(self, rect: pygame.Rect) -> None:
        self.screen.blit(self.font.render("No experiment results are available yet.", True, self.warn), (rect.x + 24, rect.y + 36))

    def _draw_footer(self, mouse_pos: tuple[int, int]) -> None:
        y = 660
        self._button("NEW_EXPERIMENT", pygame.Rect(28, y, 160, 36), "NEW EXPERIMENT", mouse_pos, primary=True)
        self._button("EXPORT_DATA", pygame.Rect(204, y, 140, 36), "EXPORT DATA", mouse_pos)
        self._button("REPLAY_RUN", pygame.Rect(360, y, 130, 36), "REPLAY RUN", mouse_pos)
        self._button("HOME", pygame.Rect(1042, y, 130, 36), "HOME", mouse_pos)
        message = self.export_status or "Export writes CSV and JSON experiment data."
        color = self.accent if self.export_status.startswith("EXPORT COMPLETE") else self.subtle
        self.screen.blit(self.small_font.render(message, True, color), (510, y + 10))

    def _export_data(self) -> None:
        try:
            folder = ExperimentExporter().export(self.manager)
        except Exception as exc:
            self.export_status = f"EXPORT FAILED: {exc}"
            return
        self.export_status = f"EXPORT COMPLETE  Folder: {folder.name}"

    def _button(self, name: str, rect: pygame.Rect, label: str, mouse_pos: tuple[int, int], primary: bool = False) -> None:
        self.buttons[name] = rect
        fill = self.accent if primary else (31, 37, 50) if rect.collidepoint(mouse_pos) else self.inner
        color = self.background if primary else self.text
        draw_button(self.screen, rect, label, self.small_font, mouse_pos, variant="primary" if primary else "secondary")

    def _draw_wrapped(self, text: str, x: int, y: int, width: int, color: tuple[int, int, int]) -> int:
        line = ""
        for word in text.split():
            candidate = word if not line else f"{line} {word}"
            if self.small_font.size(candidate)[0] <= width:
                line = candidate
            else:
                self.screen.blit(self.small_font.render(line, True, color), (x, y))
                y += 18
                line = word
        if line:
            self.screen.blit(self.small_font.render(line, True, color), (x, y))
            y += 18
        return y

    def _scroll(self, delta: int) -> None:
        if self.active_tab != "RUNS":
            return
        current = self.scroll_offsets["RUNS"]
        max_scroll = max(0, len(self.manager.results) * 24 - 390)
        self.scroll_offsets["RUNS"] = max(0, min(max_scroll, current + delta))

    def _select_relative_tab(self, delta: int) -> None:
        index = TABS.index(self.active_tab)
        self.active_tab = TABS[(index + delta) % len(TABS)]
