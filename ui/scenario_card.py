import pygame

from environment.grid_map import WALL
from environment.scenario import Scenario
from ui.components import draw_badge, draw_card
from ui.theme import Theme


class ScenarioCard:
    def __init__(self, rect: pygame.Rect, scenario: Scenario, index: int) -> None:
        self.rect = rect
        self.scenario = scenario
        self.index = index

    def draw(
        self,
        screen: pygame.Surface,
        font: pygame.font.Font,
        small_font: pygame.font.Font,
        selected: bool,
        hovered: bool,
        colors: dict[str, tuple[int, int, int]],
    ) -> None:
        draw_card(screen, self.rect, selected=selected, hovered=hovered)
        title = font.render(self._short_name(self.scenario.name).upper(), True, Theme.TEXT_PRIMARY)
        screen.blit(title, (self.rect.x + 14, self.rect.y + 12))

        badge = pygame.Rect(self.rect.right - 90, self.rect.y + 12, 76, 22)
        draw_badge(screen, badge, self._difficulty_label(self.scenario.difficulty), small_font, tone="primary" if selected else "neutral")

        preview = pygame.Rect(self.rect.x + 14, self.rect.y + 48, self.rect.width - 28, 92)
        self._draw_preview(screen, preview)

        if self.scenario.dynamic_obstacles:
            draw_badge(screen, pygame.Rect(self.rect.x + 14, self.rect.bottom - 30, 84, 22), "DYNAMIC", small_font, tone="success")
        else:
            draw_badge(screen, pygame.Rect(self.rect.x + 14, self.rect.bottom - 30, 70, 22), "STATIC", small_font, tone="neutral")

        if selected:
            pygame.draw.circle(screen, Theme.ACCENT, (self.rect.right - 18, self.rect.bottom - 19), 7)
            pygame.draw.line(screen, Theme.BACKGROUND, (self.rect.right - 22, self.rect.bottom - 19), (self.rect.right - 19, self.rect.bottom - 16), 2)
            pygame.draw.line(screen, Theme.BACKGROUND, (self.rect.right - 19, self.rect.bottom - 16), (self.rect.right - 14, self.rect.bottom - 23), 2)

    def _draw_preview(self, screen: pygame.Surface, rect: pygame.Rect) -> None:
        pygame.draw.rect(screen, Theme.CARD, rect, border_radius=8)
        rows = len(self.scenario.grid)
        cols = len(self.scenario.grid[0])
        cell_w = rect.width / cols
        cell_h = rect.height / rows

        for row, cells in enumerate(self.scenario.grid):
            for col, cell in enumerate(cells):
                if cell == WALL:
                    wall_rect = pygame.Rect(
                        int(rect.x + col * cell_w),
                        int(rect.y + row * cell_h),
                        max(1, int(cell_w + 1)),
                        max(1, int(cell_h + 1)),
                    )
                    pygame.draw.rect(screen, Theme.OBSTACLE, wall_rect)

        start_row, start_col = self.scenario.start_cell
        goal_row, goal_col = self.scenario.goal_cell
        self._draw_preview_marker(screen, rect, rows, cols, start_row, start_col, Theme.ACCENT)
        self._draw_preview_marker(screen, rect, rows, cols, goal_row, goal_col, Theme.DANGER)

    def _draw_preview_marker(
        self,
        screen: pygame.Surface,
        rect: pygame.Rect,
        rows: int,
        cols: int,
        row: int,
        col: int,
        color: tuple[int, int, int],
    ) -> None:
        x = int(rect.x + (col + 0.5) * rect.width / cols)
        y = int(rect.y + (row + 0.5) * rect.height / rows)
        pygame.draw.circle(screen, color, (x, y), 4)

    def _difficulty_label(self, difficulty: str) -> str:
        labels = {
            "Beginner": "Beginner",
            "Easy": "Easy",
            "Intermediate": "Medium",
            "Intermediate / Advanced": "Medium",
            "Advanced": "Advanced",
        }
        return labels.get(difficulty, difficulty[:8])

    def _short_name(self, name: str) -> str:
        return {
            "House Layout": "House",
            "Tight Corridor": "Corridor",
        }.get(name, name)
