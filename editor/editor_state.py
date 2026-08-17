from __future__ import annotations

from dataclasses import dataclass, field

from environment.grid_map import CELL_SIZE, FREE_SPACE, WALL
from environment.scenario import Rectangle, Scenario, build_grid, cell_center


DEFAULT_ROWS = 30
DEFAULT_COLS = 20


@dataclass
class CustomMap:
    name: str = "Untitled Environment"
    rows: int = DEFAULT_ROWS
    cols: int = DEFAULT_COLS
    resolution: int = CELL_SIZE
    walls: set[tuple[int, int]] = field(default_factory=set)
    obstacles: list[Rectangle] = field(default_factory=list)
    start: tuple[int, int] | None = None
    goal: tuple[int, int] | None = None
    semantic_locations: dict[str, tuple[int, int]] = field(default_factory=dict)

    def in_bounds(self, cell: tuple[int, int]) -> bool:
        row, col = cell
        return 0 <= row < self.rows and 0 <= col < self.cols

    def is_blocked(self, cell: tuple[int, int]) -> bool:
        if not self.in_bounds(cell):
            return True
        if cell in self.walls:
            return True
        row, col = cell
        return any(
            start_row <= row < start_row + height and start_col <= col < start_col + width
            for start_row, start_col, height, width in self.obstacles
        )

    def add_wall(self, cell: tuple[int, int]) -> None:
        if self.in_bounds(cell):
            self.walls.add(cell)
            self._remove_marker_if_blocked(cell)

    def add_obstacle(self, start: tuple[int, int], end: tuple[int, int]) -> None:
        start_row, start_col = start
        end_row, end_col = end
        top = max(0, min(start_row, end_row))
        left = max(0, min(start_col, end_col))
        bottom = min(self.rows - 1, max(start_row, end_row))
        right = min(self.cols - 1, max(start_col, end_col))
        obstacle = (top, left, bottom - top + 1, right - left + 1)
        self.obstacles.append(obstacle)
        self._remove_markers_inside(obstacle)

    def erase_cell(self, cell: tuple[int, int]) -> None:
        self.walls.discard(cell)
        row, col = cell
        self.obstacles = [
            obstacle
            for obstacle in self.obstacles
            if not (obstacle[0] <= row < obstacle[0] + obstacle[2] and obstacle[1] <= col < obstacle[1] + obstacle[3])
        ]
        if self.start == cell:
            self.start = None
        if self.goal == cell:
            self.goal = None
        for name, location in list(self.semantic_locations.items()):
            if location == cell:
                del self.semantic_locations[name]

    def set_start(self, cell: tuple[int, int]) -> bool:
        if self.in_bounds(cell) and not self.is_blocked(cell):
            self.start = cell
            return True
        return False

    def set_goal(self, cell: tuple[int, int]) -> bool:
        if self.in_bounds(cell) and not self.is_blocked(cell):
            self.goal = cell
            return True
        return False

    def add_semantic_location(self, name: str, cell: tuple[int, int]) -> bool:
        clean_name = name.strip().lower()
        if clean_name and self.in_bounds(cell) and not self.is_blocked(cell):
            self.semantic_locations[clean_name] = cell
            return True
        return False

    def clear(self) -> None:
        self.walls.clear()
        self.obstacles.clear()
        self.start = None
        self.goal = None
        self.semantic_locations.clear()

    def copy(self) -> "CustomMap":
        return CustomMap(
            name=self.name,
            rows=self.rows,
            cols=self.cols,
            resolution=self.resolution,
            walls=set(self.walls),
            obstacles=list(self.obstacles),
            start=self.start,
            goal=self.goal,
            semantic_locations=dict(self.semantic_locations),
        )

    def to_grid(self) -> list[list[int]]:
        grid = build_grid(rows=self.rows, cols=self.cols)
        for row, col in self.walls:
            if 0 <= row < self.rows and 0 <= col < self.cols:
                grid[row][col] = WALL
        for start_row, start_col, height, width in self.obstacles:
            for row in range(start_row, start_row + height):
                for col in range(start_col, start_col + width):
                    if 0 <= row < self.rows and 0 <= col < self.cols:
                        grid[row][col] = WALL
        return grid

    def to_scenario(self) -> Scenario:
        start_cell = self.start or (1, 1)
        goal_cell = self.goal or (self.rows - 2, self.cols - 2)
        start_x, start_y = cell_center(*start_cell)
        goal_x, goal_y = cell_center(*goal_cell)
        wall_rectangles = [(row, col, 1, 1) for row, col in sorted(self.walls)]
        return Scenario(
            name=self.name.strip() or "Custom Environment",
            description="Custom user-built environment.",
            difficulty="Custom",
            grid=self.to_grid(),
            robot_start_x=start_x,
            robot_start_y=start_y,
            robot_start_theta=0.0,
            goal_x=goal_x,
            goal_y=goal_y,
            static_obstacles=wall_rectangles + list(self.obstacles),
            recommended_planner="A*",
            mission_label="CUSTOM START -> GOAL",
        )

    def _remove_marker_if_blocked(self, cell: tuple[int, int]) -> None:
        if self.start == cell:
            self.start = None
        if self.goal == cell:
            self.goal = None
        for name, location in list(self.semantic_locations.items()):
            if location == cell:
                del self.semantic_locations[name]

    def _remove_markers_inside(self, obstacle: Rectangle) -> None:
        start_row, start_col, height, width = obstacle
        cells = {
            (row, col)
            for row in range(start_row, start_row + height)
            for col in range(start_col, start_col + width)
        }
        for cell in cells:
            self._remove_marker_if_blocked(cell)
