from pathlib import Path

import pygame

from editor.map_serializer import list_custom_maps, load_custom_map
from environment.scenario_manager import ScenarioManager, ScenarioSummary
from ui.app_state import MODE_AUTONOMOUS, MODE_EXPLORATION, MODE_MANUAL, SimulationSettings
from ui.components import draw_badge, draw_button, draw_card
from ui.scenario_card import ScenarioCard
from ui.theme import Theme, load_fonts
from visualization.lidar_view import LIDAR_VIEW_FULL, LIDAR_VIEW_MINIMAL, LIDAR_VIEW_OFF
from visualization.pygame_dashboard import WINDOW_HEIGHT, WINDOW_WIDTH


class HomeScreen:
    def __init__(self, scenario_manager: ScenarioManager, settings: SimulationSettings) -> None:
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("AMR Navigation Simulator")
        self.clock = pygame.time.Clock()
        self.scenario_manager = scenario_manager
        self.settings = settings
        fonts = load_fonts()
        self.font = fonts.section
        self.small_font = fonts.small
        self.body_font = fonts.body
        self.title_font = fonts.app_title
        self.background = Theme.BACKGROUND
        self.panel = Theme.SURFACE
        self.inner = Theme.CARD
        self.border = Theme.BORDER
        self.text = Theme.TEXT_PRIMARY
        self.subtle = Theme.TEXT_SECONDARY
        self.accent = Theme.PRIMARY
        self.selected = Theme.SURFACE_ALT
        self.hover = Theme.SURFACE_ALT
        self.goal = Theme.DANGER
        self.start = Theme.ACCENT
        self.wall = Theme.OBSTACLE
        self.advanced_open = False
        self.buttons: dict[str, pygame.Rect] = {}
        self.card_rects: list[pygame.Rect] = []

    def run(self, latest_summary: ScenarioSummary | None = None) -> tuple[str, SimulationSettings]:
        while True:
            mouse_pos = pygame.mouse.get_pos()
            for event in pygame.event.get():
                action = self._handle_event(event)
                if action:
                    return action, self.settings
            self.draw(mouse_pos, latest_summary)
            self.clock.tick(60)

    def draw(self, mouse_pos: tuple[int, int], latest_summary: ScenarioSummary | None = None) -> None:
        self.buttons = {}
        self.screen.fill(self.background)
        self._draw_header()
        self._draw_cards(mouse_pos)
        self._draw_launch_panel(mouse_pos)
        self._draw_footer(latest_summary, mouse_pos)
        pygame.display.flip()

    def _handle_event(self, event: pygame.event.Event) -> str | None:
        if event.type == pygame.QUIT:
            return "QUIT"
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                return "START"
            if event.key == pygame.K_LEFT:
                self.settings.scenario_index = (self.settings.scenario_index - 1) % self.scenario_manager.total_scenarios
            if event.key == pygame.K_RIGHT:
                self.settings.scenario_index = (self.settings.scenario_index + 1) % self.scenario_manager.total_scenarios
            if event.key == pygame.K_1:
                self.settings.planner = "A*"
            if event.key == pygame.K_2:
                self.settings.planner = "Dijkstra"
            if event.key == pygame.K_3:
                self.settings.planner = "RRT*"

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for index, rect in enumerate(self.card_rects):
                if rect.collidepoint(event.pos):
                    if index >= self.scenario_manager.total_scenarios:
                        return "MAP_EDITOR"
                    self.settings.scenario_index = index
                    return None
            for name, rect in self.buttons.items():
                if rect.collidepoint(event.pos):
                    return self._button_action(name)
        return None

    def _button_action(self, name: str) -> str | None:
        if name == "start":
            return "START"
        if name == "replay":
            return "REPLAY"
        if name == "experiments":
            return "EXPERIMENTS"
        if name == "demo":
            return "DEMO_MODE"
        if name == "MAP_EDITOR":
            return "MAP_EDITOR"
        if name.startswith("run_custom:"):
            return "RUN_CUSTOM:" + name.split(":", 1)[1]
        if name.startswith("edit_custom:"):
            return "EDIT_CUSTOM:" + name.split(":", 1)[1]
        if name.startswith("delete_custom:"):
            Path(name.split(":", 1)[1]).unlink(missing_ok=True)
            return None
        if name == "advanced":
            self.advanced_open = not self.advanced_open
            return None
        if name.startswith("planner:"):
            self.settings.planner = name.split(":", 1)[1]
        if name.startswith("mode:"):
            self.settings.mode = name.split(":", 1)[1]
        if name.startswith("lidar:"):
            self.settings.lidar_view_mode = int(name.split(":", 1)[1])
        if name == "dynamic":
            self.settings.dynamic_obstacles_enabled = not self.settings.dynamic_obstacles_enabled
        if name == "localization":
            self.settings.show_localization = not self.settings.show_localization
        if name == "path":
            self.settings.show_planned_path = not self.settings.show_planned_path
        if name == "battery":
            self.settings.battery_simulation_enabled = not self.settings.battery_simulation_enabled
        if name == "auto_charge":
            self.settings.auto_return_to_charger = not self.settings.auto_return_to_charger
        return None

    def _draw_header(self) -> None:
        self.screen.blit(self.title_font.render("AMR Navigation Simulator", True, self.text), (30, 24))
        draw_badge(self.screen, pygame.Rect(420, 32, 76, 24), "v1.0.0", self.small_font, tone="neutral")
        draw_badge(self.screen, pygame.Rect(506, 32, 94, 24), "OFFLINE", self.small_font, tone="success")

    def _draw_cards(self, mouse_pos: tuple[int, int]) -> None:
        self.screen.blit(self.font.render("Scenarios", True, self.text), (30, 84))
        self.card_rects = []
        colors = {
            "panel": self.panel,
            "inner": self.inner,
            "border": self.border,
            "text": self.text,
            "subtle": self.subtle,
            "accent": self.accent,
            "selected": self.selected,
            "hover": self.hover,
            "goal": self.goal,
            "start": self.start,
            "wall": self.wall,
        }
        width = 250
        height = 166
        for index, scenario in enumerate(self.scenario_manager.scenarios):
            row = 0 if index < 3 else 1
            col = index if index < 3 else index - 3
            rect = pygame.Rect(30 + col * (width + 18), 118 + row * (height + 18), width, height)
            self.card_rects.append(rect)
            ScenarioCard(rect, scenario, index).draw(
                self.screen,
                self.font,
                self.small_font,
                selected=index == self.settings.scenario_index,
                hovered=rect.collidepoint(mouse_pos),
                colors=colors,
            )

        custom_rect = pygame.Rect(30 + 2 * (width + 18), 118 + height + 18, width, height)
        self.card_rects.append(custom_rect)
        draw_card(self.screen, custom_rect, selected=custom_rect.collidepoint(mouse_pos), hovered=custom_rect.collidepoint(mouse_pos))
        self.screen.blit(self.font.render("CUSTOM MAP", True, self.text), (custom_rect.x + 14, custom_rect.y + 14))
        self._draw_button("MAP_EDITOR", pygame.Rect(custom_rect.x + 14, custom_rect.y + 70, 150, 38), "CREATE MAP", mouse_pos, primary=True)

    def _draw_launch_panel(self, mouse_pos: tuple[int, int]) -> None:
        panel_rect = pygame.Rect(830, 118, 340, 506)
        draw_card(self.screen, panel_rect)
        scenario = self.scenario_manager.scenarios[self.settings.scenario_index]

        self.screen.blit(self.font.render("Launch", True, self.text), (panel_rect.x + 20, panel_rect.y + 20))
        self.screen.blit(self.title_font.render(self._short_scenario(scenario.name), True, self.text), (panel_rect.x + 20, panel_rect.y + 56))
        draw_badge(self.screen, pygame.Rect(panel_rect.x + 20, panel_rect.y + 106, 98, 24), scenario.difficulty[:10], self.small_font, tone="primary")
        if scenario.dynamic_obstacles:
            draw_badge(self.screen, pygame.Rect(panel_rect.x + 130, panel_rect.y + 106, 90, 24), "DYNAMIC", self.small_font, tone="success")

        y = panel_rect.y + 154
        y = self._draw_option_group("Planner", ["A*", "Dijkstra", "RRT*"], self.settings.planner, panel_rect.x + 20, y, mouse_pos)
        y = self._draw_option_group("Mode", [MODE_MANUAL, MODE_AUTONOMOUS, MODE_EXPLORATION], self.settings.mode, panel_rect.x + 20, y + 10, mouse_pos)
        lidar_options = [(LIDAR_VIEW_OFF, "Off"), (LIDAR_VIEW_MINIMAL, "Minimal"), (LIDAR_VIEW_FULL, "Full")]
        self._draw_lidar_options(panel_rect.x + 20, y + 10, mouse_pos, lidar_options)

        self._draw_button("start", pygame.Rect(panel_rect.x + 20, panel_rect.bottom - 58, 142, 40), "START", mouse_pos, primary=True)
        self._draw_button("demo", pygame.Rect(panel_rect.x + 176, panel_rect.bottom - 58, 132, 40), "DEMO", mouse_pos)

    def _draw_footer(self, latest_summary: ScenarioSummary | None, mouse_pos: tuple[int, int]) -> None:
        left = pygame.Rect(30, 510, 364, 150)
        middle = pygame.Rect(414, 510, 364, 150)
        draw_card(self.screen, left)
        draw_card(self.screen, middle)

        self.screen.blit(self.font.render("Last Run", True, self.text), (left.x + 18, left.y + 18))
        if latest_summary is None:
            self.screen.blit(self.body_font.render("No completed run yet.", True, self.subtle), (left.x + 18, left.y + 58))
        else:
            self.screen.blit(self.body_font.render(latest_summary.name, True, self.text), (left.x + 18, left.y + 56))
            self.screen.blit(self.body_font.render(f"{latest_summary.completion_time:.1f}s  |  {latest_summary.replans} replans", True, self.subtle), (left.x + 18, left.y + 84))

        self.screen.blit(self.font.render("Tools", True, self.text), (middle.x + 18, middle.y + 18))
        self._draw_button("experiments", pygame.Rect(middle.x + 18, middle.y + 58, 136, 38), "EXPERIMENTS", mouse_pos)
        self._draw_button("replay", pygame.Rect(middle.x + 168, middle.y + 58, 112, 38), "REPLAY", mouse_pos)

        maps = list_custom_maps()[:2]
        if maps:
            x = middle.x + 18
            y = middle.y + 108
            for map_path in maps:
                try:
                    custom_map = load_custom_map(map_path)
                    label = custom_map.name[:14]
                except Exception:
                    label = map_path.stem[:14]
                self._draw_button(f"run_custom:{map_path}", pygame.Rect(x, y, 72, 24), label, mouse_pos)
                x += 82

    def _draw_option_group(self, key: str, options: list[str], selected: str, x: int, y: int, mouse_pos: tuple[int, int]) -> int:
        self.screen.blit(self.small_font.render(key.upper(), True, self.subtle), (x, y))
        button_x = x
        for option in options:
            rect = pygame.Rect(button_x, y + 24, 96, 30)
            self._draw_button(f"{key.lower()}:{option}", rect, option, mouse_pos, selected=option == selected)
            button_x += 106
        return y + 58

    def _draw_lidar_options(self, x: int, y: int, mouse_pos: tuple[int, int], options: list[tuple[int, str]]) -> int:
        self.screen.blit(self.small_font.render("LIDAR", True, self.subtle), (x, y))
        button_x = x
        for value, label in options:
            rect = pygame.Rect(button_x, y + 24, 96, 30)
            self._draw_button(f"lidar:{value}", rect, label, mouse_pos, selected=value == self.settings.lidar_view_mode)
            button_x += 106
        return y + 58

    def _draw_advanced(self, x: int, y: int, mouse_pos: tuple[int, int]) -> None:
        rows = [
            ("dynamic", "Dynamic", self.settings.dynamic_obstacles_enabled),
            ("localization", "Localization", self.settings.show_localization),
            ("path", "Path", self.settings.show_planned_path),
            ("battery", "Battery", self.settings.battery_simulation_enabled),
            ("auto_charge", "Auto charge", self.settings.auto_return_to_charger),
        ]
        for name, label, enabled in rows:
            rect = pygame.Rect(x, y, 130, 24)
            self._draw_button(name, rect, f"{label}: {'On' if enabled else 'Off'}", mouse_pos, selected=enabled)
            y += 28

    def _draw_button(self, name: str, rect: pygame.Rect, label: str, mouse_pos: tuple[int, int], primary: bool = False, selected: bool = False) -> None:
        self.buttons[name] = rect
        draw_button(self.screen, rect, label, self.small_font, mouse_pos, variant="primary" if primary else "secondary", selected=selected)

    def _short_scenario(self, name: str) -> str:
        return "House" if name == "House Layout" else name.replace("Tight ", "")

    def _mission_examples(self, name: str) -> list[str]:
        return {
            "House Layout": ["Kitchen -> Bedroom -> Charger", "Return to charger"],
            "Warehouse": ["Loading -> Packing", "Return to charger"],
            "Office": ["Reception -> Meeting Room", "Return to charger"],
        }.get(name, ["Go to target", "Return to charger"])
