from __future__ import annotations

from pathlib import Path

import pygame

from editor.editor_state import CustomMap
from editor.editor_tools import ERASER, GOAL, LOCATION, OBSTACLE, SELECT, START, TOOLS, WALL
from editor.map_serializer import CUSTOM_MAPS_DIR, export_custom_map, import_custom_map, load_custom_map, save_custom_map
from editor.map_validator import MapValidator, ValidationResult
from ui.app_state import MODE_AUTONOMOUS, MODE_EXPLORATION, MODE_MANUAL, SimulationSettings
from ui.components import draw_button, draw_card, draw_modal
from ui.theme import Theme, load_fonts
from visualization.lidar_view import LIDAR_VIEW_FULL, LIDAR_VIEW_MINIMAL, LIDAR_VIEW_OFF
from visualization.pygame_dashboard import WINDOW_HEIGHT, WINDOW_WIDTH


class MapEditor:
    def __init__(
        self,
        custom_map: CustomMap | None = None,
        settings: SimulationSettings | None = None,
        source_path: str = "",
    ) -> None:
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("AMR Navigation Simulator - Custom Environment Builder")
        self.clock = pygame.time.Clock()
        self.custom_map = custom_map or CustomMap()
        self.settings = settings or SimulationSettings()
        self.source_path = source_path
        self.tool = WALL
        self.validator = MapValidator()
        self.validation = self.validator.validate(self.custom_map)
        self.unsaved = False
        self.confirm_clear = False
        self.confirm_home = False
        self.drag_start: tuple[int, int] | None = None
        self.selected_obstacle_index: int | None = None
        self.location_name = "Kitchen"
        self.undo_stack: list[CustomMap] = []
        self.buttons: dict[str, pygame.Rect] = {}
        self.tool_rects: dict[str, pygame.Rect] = {}
        self.grid_rect = pygame.Rect(218, 104, 400, 600)
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

    def run(self) -> tuple[str, SimulationSettings, CustomMap | None, str]:
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
        self.tool_rects = {}
        self.screen.fill(self.background)
        self._draw_header()
        self._draw_tools(mouse_pos)
        self._draw_grid()
        self._draw_properties(mouse_pos)
        self._draw_footer(mouse_pos)
        if self.confirm_clear:
            self._draw_confirm("Clear this environment?", "clear_yes", "clear_cancel", mouse_pos)
        if self.confirm_home:
            self._draw_unsaved_confirm(mouse_pos)
        pygame.display.flip()

    def _handle_event(self, event: pygame.event.Event) -> tuple[str, SimulationSettings, CustomMap | None, str] | None:
        if event.type == pygame.QUIT:
            return self._attempt_home()
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if self.confirm_clear or self.confirm_home:
                    self.confirm_clear = False
                    self.confirm_home = False
                    return None
                return self._attempt_home()
            if event.key == pygame.K_DELETE:
                self._delete_selected()
            if event.key == pygame.K_s and pygame.key.get_mods() & pygame.KMOD_CTRL:
                self._save()
            if event.key == pygame.K_z and pygame.key.get_mods() & pygame.KMOD_CTRL:
                self._undo()
            if event.key == pygame.K_BACKSPACE:
                self.custom_map.name = self.custom_map.name[:-1]
                self.unsaved = True
            elif event.unicode and event.unicode.isprintable():
                if len(self.custom_map.name) < 32:
                    self.custom_map.name += event.unicode
                    self.unsaved = True

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            self.drag_start = None
            self.confirm_clear = False
            return None

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return self._handle_click(event.pos)

        if event.type == pygame.MOUSEMOTION and event.buttons[0]:
            cell = self._cell_from_pos(event.pos)
            if cell and self.tool == WALL:
                self._push_undo_once()
                self.custom_map.add_wall(cell)
                self._mark_changed()

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            cell = self._cell_from_pos(event.pos)
            if cell and self.drag_start and self.tool == OBSTACLE:
                self._push_undo()
                self.custom_map.add_obstacle(self.drag_start, cell)
                self._mark_changed()
            self.drag_start = None

        return None

    def _handle_click(self, pos: tuple[int, int]) -> tuple[str, SimulationSettings, CustomMap | None, str] | None:
        for name, rect in self.buttons.items():
            if rect.collidepoint(pos):
                return self._button_action(name)
        for tool, rect in self.tool_rects.items():
            if rect.collidepoint(pos):
                self.tool = tool
                return None

        cell = self._cell_from_pos(pos)
        if cell is None:
            return None

        if self.tool == SELECT:
            self.selected_obstacle_index = self._obstacle_at(cell)
        elif self.tool == WALL:
            self._push_undo()
            self.custom_map.add_wall(cell)
            self._mark_changed()
        elif self.tool == OBSTACLE:
            self.drag_start = cell
        elif self.tool == START:
            self._push_undo()
            if self.custom_map.set_start(cell):
                self._mark_changed()
        elif self.tool == GOAL:
            self._push_undo()
            if self.custom_map.set_goal(cell):
                self._mark_changed()
        elif self.tool == LOCATION:
            self._push_undo()
            if self.custom_map.add_semantic_location(self.location_name, cell):
                self._mark_changed()
        elif self.tool == ERASER:
            self._push_undo()
            self.custom_map.erase_cell(cell)
            self._mark_changed()
        return None

    def _button_action(self, name: str) -> tuple[str, SimulationSettings, CustomMap | None, str] | None:
        if name == "home":
            return self._attempt_home()
        if name == "save":
            self._save()
        if name == "validate":
            self.validation = self.validator.validate(self.custom_map)
        if name == "export":
            export_custom_map(self.custom_map, CUSTOM_MAPS_DIR / f"export_{self.custom_map.name.lower().replace(' ', '_')}.json")
        if name == "import":
            import_path = CUSTOM_MAPS_DIR / "import_map.json"
            if import_path.exists():
                self._push_undo()
                self.custom_map = import_custom_map(import_path)
                self._mark_changed()
        if name == "run" and self.validation.valid:
            self.settings.custom_scenario = self.custom_map.to_scenario()
            self.settings.custom_map_name = self.custom_map.name
            self.settings.custom_semantic_locations = dict(self.custom_map.semantic_locations)
            return "RUN_CUSTOM", self.settings, self.custom_map, self.source_path
        if name == "clear":
            self.confirm_clear = True
        if name == "clear_yes":
            self._push_undo()
            self.custom_map.clear()
            self.confirm_clear = False
            self._mark_changed()
        if name == "clear_cancel":
            self.confirm_clear = False
        if name == "discard_home":
            return "HOME", self.settings, None, self.source_path
        if name == "cancel_home":
            self.confirm_home = False
        if name == "save_home":
            self._save()
            return "HOME", self.settings, None, self.source_path
        if name.startswith("planner:"):
            self.settings.planner = name.split(":", 1)[1]
        if name.startswith("mode:"):
            self.settings.mode = name.split(":", 1)[1]
        if name.startswith("lidar:"):
            self.settings.lidar_view_mode = int(name.split(":", 1)[1])
        if name.startswith("location:"):
            self.location_name = name.split(":", 1)[1]
        return None

    def _attempt_home(self) -> tuple[str, SimulationSettings, CustomMap | None, str] | None:
        if self.unsaved:
            self.confirm_home = True
            return None
        return "HOME", self.settings, None, self.source_path

    def _save(self) -> None:
        path = save_custom_map(self.custom_map)
        self.source_path = str(path)
        self.unsaved = False

    def _mark_changed(self) -> None:
        self.validation = self.validator.validate(self.custom_map)
        self.unsaved = True

    def _push_undo_once(self) -> None:
        if not self.undo_stack:
            self._push_undo()

    def _push_undo(self) -> None:
        self.undo_stack.append(self.custom_map.copy())
        if len(self.undo_stack) > 20:
            del self.undo_stack[0]

    def _undo(self) -> None:
        if self.undo_stack:
            self.custom_map = self.undo_stack.pop()
            self.validation = self.validator.validate(self.custom_map)
            self.unsaved = True

    def _delete_selected(self) -> None:
        if self.selected_obstacle_index is not None and self.selected_obstacle_index < len(self.custom_map.obstacles):
            self._push_undo()
            del self.custom_map.obstacles[self.selected_obstacle_index]
            self.selected_obstacle_index = None
            self._mark_changed()

    def _draw_header(self) -> None:
        self.screen.blit(self.title_font.render("CUSTOM ENVIRONMENT BUILDER", True, self.text), (28, 22))
        status = "Unsaved changes" if self.unsaved else "Saved"
        self.screen.blit(self.small_font.render(status, True, self.warn if self.unsaved else self.accent), (28, 58))

    def _draw_tools(self, mouse_pos: tuple[int, int]) -> None:
        panel = pygame.Rect(28, 88, 164, 552)
        draw_card(self.screen, panel)
        self.screen.blit(self.font.render("TOOLS", True, self.text), (panel.x + 14, panel.y + 14))
        y = panel.y + 52
        for tool in TOOLS:
            rect = pygame.Rect(panel.x + 14, y, 136, 30)
            self.tool_rects[tool] = rect
            selected = self.tool == tool
            draw_button(self.screen, rect, tool, self.small_font, mouse_pos, variant="secondary", selected=selected)
            y += 38
        self.screen.blit(self.small_font.render("Ctrl+S Save", True, self.subtle), (panel.x + 14, panel.bottom - 72))
        self.screen.blit(self.small_font.render("Ctrl+Z Undo", True, self.subtle), (panel.x + 14, panel.bottom - 50))
        self.screen.blit(self.small_font.render("ESC Home", True, self.subtle), (panel.x + 14, panel.bottom - 28))

    def _draw_grid(self) -> None:
        pygame.draw.rect(self.screen, Theme.CARD, self.grid_rect, border_radius=8)
        grid = self.custom_map.to_grid()
        cell_size = self.grid_rect.width // self.custom_map.cols
        for row in range(self.custom_map.rows):
            for col in range(self.custom_map.cols):
                rect = pygame.Rect(self.grid_rect.x + col * cell_size, self.grid_rect.y + row * cell_size, cell_size, cell_size)
                if grid[row][col] == 1:
                    pygame.draw.rect(self.screen, Theme.OBSTACLE, rect)
                pygame.draw.rect(self.screen, Theme.GRID, rect, 1)
        if self.selected_obstacle_index is not None and self.selected_obstacle_index < len(self.custom_map.obstacles):
            row, col, height, width = self.custom_map.obstacles[self.selected_obstacle_index]
            pygame.draw.rect(
                self.screen,
                self.warn,
                pygame.Rect(self.grid_rect.x + col * cell_size, self.grid_rect.y + row * cell_size, width * cell_size, height * cell_size),
                3,
            )
        self._draw_marker(self.custom_map.start, "START", Theme.ACCENT, cell_size)
        self._draw_marker(self.custom_map.goal, "GOAL", Theme.DANGER, cell_size)
        for name, cell in self.custom_map.semantic_locations.items():
            self._draw_marker(cell, name[:8].upper(), Theme.PRIMARY, cell_size)

    def _draw_marker(self, cell: tuple[int, int] | None, label: str, color: tuple[int, int, int], cell_size: int) -> None:
        if cell is None:
            return
        row, col = cell
        rect = pygame.Rect(self.grid_rect.x + col * cell_size, self.grid_rect.y + row * cell_size, cell_size, cell_size)
        pygame.draw.circle(self.screen, color, rect.center, max(5, cell_size // 3))
        surface = self.small_font.render(label, True, self.text)
        self.screen.blit(surface, (rect.x + 2, rect.y + 2))

    def _draw_properties(self, mouse_pos: tuple[int, int]) -> None:
        panel = pygame.Rect(642, 88, 530, 552)
        draw_card(self.screen, panel)
        y = panel.y + 14
        self.screen.blit(self.font.render("PROPERTIES", True, self.text), (panel.x + 14, y))
        y += 34
        self._row("Map Name", self.custom_map.name, panel.x + 14, y)
        y += 26
        self._row("Grid Size", f"{self.custom_map.cols} x {self.custom_map.rows}", panel.x + 14, y)
        y += 34
        y = self._option_group("planner", ["A*", "Dijkstra", "RRT*"], self.settings.planner, panel.x + 14, y, mouse_pos)
        y = self._option_group("mode", [MODE_MANUAL, MODE_AUTONOMOUS, MODE_EXPLORATION], self.settings.mode, panel.x + 14, y + 8, mouse_pos)
        y = self._lidar_group(panel.x + 14, y + 8, mouse_pos)
        y += 12
        self.screen.blit(self.small_font.render("Location Name", True, self.subtle), (panel.x + 14, y))
        names = ["Kitchen", "Bedroom", "Charging Station", "Reception", "Loading Area", "Laboratory"]
        x = panel.x + 126
        for index, name in enumerate(names):
            rect = pygame.Rect(x + (index % 2) * 132, y - 4 + (index // 2) * 28, 124, 24)
            self._button(f"location:{name}", rect, name, mouse_pos, selected=self.location_name == name)
        y += 94
        self.screen.blit(self.font.render("VALIDATION", True, self.text), (panel.x + 14, y))
        y += 30
        for message in self.validation.messages[:6]:
            color = self.accent if self.validation.valid else self.error
            self.screen.blit(self.small_font.render(message, True, color), (panel.x + 14, y))
            y += 22
        if self.custom_map.semantic_locations:
            y += 12
            self.screen.blit(self.font.render("SEMANTIC LOCATIONS", True, self.text), (panel.x + 14, y))
            y += 26
            for name, cell in list(self.custom_map.semantic_locations.items())[:7]:
                self._row(name.title(), str(cell), panel.x + 14, y)
                y += 20

    def _draw_footer(self, mouse_pos: tuple[int, int]) -> None:
        y = 658
        self._button("clear", pygame.Rect(28, y, 120, 36), "CLEAR", mouse_pos)
        self._button("save", pygame.Rect(164, y, 120, 36), "SAVE MAP", mouse_pos)
        self._button("validate", pygame.Rect(300, y, 120, 36), "VALIDATE", mouse_pos)
        self._button("export", pygame.Rect(436, y, 112, 36), "EXPORT", mouse_pos)
        self._button("import", pygame.Rect(564, y, 112, 36), "IMPORT", mouse_pos)
        self._button("run", pygame.Rect(692, y, 160, 36), "RUN SIMULATION", mouse_pos, primary=self.validation.valid, disabled=not self.validation.valid)
        self._button("home", pygame.Rect(1012, y, 160, 36), "HOME", mouse_pos)

    def _draw_confirm(self, title: str, yes: str, cancel: str, mouse_pos: tuple[int, int]) -> None:
        rect = pygame.Rect(420, 250, 360, 150)
        draw_modal(
            self.screen,
            rect,
            title,
            "This action cannot be undone.",
            self.font,
            self.small_font,
            mouse_pos,
            [
                (yes, pygame.Rect(rect.x + 54, rect.y + 88, 110, 34), "CONFIRM", "danger"),
                (cancel, pygame.Rect(rect.x + 196, rect.y + 88, 110, 34), "CANCEL", "secondary"),
            ],
        )
        self.buttons[yes] = pygame.Rect(rect.x + 54, rect.y + 88, 110, 34)
        self.buttons[cancel] = pygame.Rect(rect.x + 196, rect.y + 88, 110, 34)

    def _draw_unsaved_confirm(self, mouse_pos: tuple[int, int]) -> None:
        rect = pygame.Rect(390, 236, 420, 176)
        draw_modal(
            self.screen,
            rect,
            "Unsaved changes",
            "Save before leaving the map editor?",
            self.font,
            self.small_font,
            mouse_pos,
            [
                ("save_home", pygame.Rect(rect.x + 34, rect.y + 104, 104, 34), "SAVE", "primary"),
                ("discard_home", pygame.Rect(rect.x + 158, rect.y + 104, 104, 34), "DISCARD", "danger"),
                ("cancel_home", pygame.Rect(rect.x + 282, rect.y + 104, 104, 34), "CANCEL", "secondary"),
            ],
        )
        self.buttons["save_home"] = pygame.Rect(rect.x + 34, rect.y + 104, 104, 34)
        self.buttons["discard_home"] = pygame.Rect(rect.x + 158, rect.y + 104, 104, 34)
        self.buttons["cancel_home"] = pygame.Rect(rect.x + 282, rect.y + 104, 104, 34)

    def _option_group(self, key: str, options: list[str], selected: str, x: int, y: int, mouse_pos: tuple[int, int]) -> int:
        self.screen.blit(self.small_font.render(key.upper(), True, self.subtle), (x, y))
        button_x = x + 104
        for option in options:
            rect = pygame.Rect(button_x, y - 4, 92, 24)
            self._button(f"{key}:{option}", rect, option, mouse_pos, selected=option == selected)
            button_x += 98
        return y + 32

    def _lidar_group(self, x: int, y: int, mouse_pos: tuple[int, int]) -> int:
        self.screen.blit(self.small_font.render("LIDAR VIEW", True, self.subtle), (x, y))
        options = [(LIDAR_VIEW_OFF, "Off"), (LIDAR_VIEW_MINIMAL, "Minimal"), (LIDAR_VIEW_FULL, "Full")]
        button_x = x + 104
        for value, label in options:
            rect = pygame.Rect(button_x, y - 4, 92, 24)
            self._button(f"lidar:{value}", rect, label, mouse_pos, selected=value == self.settings.lidar_view_mode)
            button_x += 98
        return y + 32

    def _button(
        self,
        name: str,
        rect: pygame.Rect,
        label: str,
        mouse_pos: tuple[int, int],
        primary: bool = False,
        selected: bool = False,
        disabled: bool = False,
    ) -> None:
        self.buttons[name] = rect
        draw_button(
            self.screen,
            rect,
            label,
            self.small_font,
            mouse_pos,
            variant="primary" if primary else "secondary",
            selected=selected,
            disabled=disabled,
        )

    def _row(self, label: str, value: str, x: int, y: int) -> None:
        self.screen.blit(self.small_font.render(label, True, self.subtle), (x, y))
        self.screen.blit(self.small_font.render(value, True, self.text), (x + 126, y))

    def _cell_from_pos(self, pos: tuple[int, int]) -> tuple[int, int] | None:
        if not self.grid_rect.collidepoint(pos):
            return None
        cell_size = self.grid_rect.width // self.custom_map.cols
        col = (pos[0] - self.grid_rect.x) // cell_size
        row = (pos[1] - self.grid_rect.y) // cell_size
        cell = (int(row), int(col))
        return cell if self.custom_map.in_bounds(cell) else None

    def _obstacle_at(self, cell: tuple[int, int]) -> int | None:
        row, col = cell
        for index, obstacle in enumerate(self.custom_map.obstacles):
            start_row, start_col, height, width = obstacle
            if start_row <= row < start_row + height and start_col <= col < start_col + width:
                return index
        return None
