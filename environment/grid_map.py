from typing import TYPE_CHECKING, Optional

from environment.dynamic_obstacle import DynamicObstacle

if TYPE_CHECKING:
    from environment.scenario import Scenario


CELL_SIZE = 20
FREE_SPACE = 0
WALL = 1
ROBOT_RADIUS = 7


class GridMap:
    def __init__(self, scenario: Optional["Scenario"] = None) -> None:
        self.cell_size = CELL_SIZE
        if scenario is None:
            self.default_goal_cell = (27, 17)
            self.grid = self._create_grid()
            self.dynamic_obstacles = self._create_dynamic_obstacles()
            self.static_obstacles = []
        else:
            self.default_goal_cell = scenario.goal_cell
            self.grid = scenario.copy_grid()
            self.dynamic_obstacles = scenario.create_dynamic_obstacles()
            self.static_obstacles = scenario.static_obstacles

    def _create_grid(self) -> list[list[int]]:
        rows = 30
        cols = 20
        grid = [[FREE_SPACE for _ in range(cols)] for _ in range(rows)]

        for row in range(rows):
            grid[row][0] = WALL
            grid[row][cols - 1] = WALL

        for col in range(cols):
            grid[0][col] = WALL
            grid[rows - 1][col] = WALL

        # Maze-like internal structure. Gaps are left intentionally so paths remain valid.
        self._add_rectangle(grid, start_row=3, start_col=4, height=9, width=1)
        self._add_rectangle(grid, start_row=15, start_col=4, height=10, width=1)
        self._add_rectangle(grid, start_row=5, start_col=4, height=1, width=6)
        self._add_rectangle(grid, start_row=5, start_col=12, height=1, width=5)
        self._add_rectangle(grid, start_row=8, start_col=8, height=9, width=1)
        self._add_rectangle(grid, start_row=18, start_col=8, height=7, width=1)
        self._add_rectangle(grid, start_row=10, start_col=11, height=1, width=6)
        self._add_rectangle(grid, start_row=13, start_col=13, height=9, width=1)
        self._add_rectangle(grid, start_row=17, start_col=6, height=1, width=7)
        self._add_rectangle(grid, start_row=23, start_col=10, height=1, width=7)
        self._add_rectangle(grid, start_row=25, start_col=2, height=1, width=7)
        self._add_rectangle(grid, start_row=3, start_col=16, height=5, width=1)

        # Keep the reset/start area and default goal area clear.
        self._clear_rectangle(grid, start_row=13, start_col=8, height=5, width=5)
        self._clear_rectangle(grid, start_row=26, start_col=16, height=2, width=2)

        return grid

    def _create_dynamic_obstacles(self) -> list[DynamicObstacle]:
        return [
            DynamicObstacle(
                x=120,
                y=250,
                width=18,
                height=18,
                vx=35,
                vy=0,
                min_x=100,
                max_x=220,
                min_y=250,
                max_y=268,
            ),
            DynamicObstacle(
                x=280,
                y=390,
                width=18,
                height=18,
                vx=-28,
                vy=0,
                min_x=220,
                max_x=360,
                min_y=390,
                max_y=408,
            ),
            DynamicObstacle(
                x=300,
                y=150,
                width=18,
                height=18,
                vx=0,
                vy=26,
                min_x=300,
                max_x=318,
                min_y=120,
                max_y=240,
            ),
        ]

    def _add_rectangle(
        self,
        grid: list[list[int]],
        start_row: int,
        start_col: int,
        height: int,
        width: int,
    ) -> None:
        for row in range(start_row, start_row + height):
            for col in range(start_col, start_col + width):
                grid[row][col] = WALL

    def _clear_rectangle(
        self,
        grid: list[list[int]],
        start_row: int,
        start_col: int,
        height: int,
        width: int,
    ) -> None:
        for row in range(start_row, start_row + height):
            for col in range(start_col, start_col + width):
                grid[row][col] = FREE_SPACE

    def update_dynamic_obstacles(self, dt: float) -> None:
        for obstacle in self.dynamic_obstacles:
            obstacle.update(dt)

    def get_planning_grid(self) -> list[list[int]]:
        planning_grid = [row.copy() for row in self.grid]

        for row in range(len(planning_grid)):
            for col in range(len(planning_grid[0])):
                if self.dynamic_cell_is_blocked(row, col):
                    planning_grid[row][col] = WALL

        return planning_grid

    def is_wall(self, row: int, col: int) -> bool:
        if row < 0 or row >= len(self.grid):
            return True
        if col < 0 or col >= len(self.grid[0]):
            return True
        return self.grid[row][col] == WALL or self.dynamic_cell_is_blocked(row, col)

    def dynamic_cell_is_blocked(self, row: int, col: int) -> bool:
        for obstacle in self.dynamic_obstacles:
            if obstacle.touches_cell(row, col, self.cell_size):
                return True
        return False

    def _static_cell_is_blocked(self, row: int, col: int) -> bool:
        if row < 0 or row >= len(self.grid):
            return True
        if col < 0 or col >= len(self.grid[0]):
            return True
        return self.grid[row][col] == WALL

    def collides_with_wall(self, x: float, y: float, radius: int = ROBOT_RADIUS) -> bool:
        left_col = int((x - radius) // self.cell_size)
        right_col = int((x + radius) // self.cell_size)
        top_row = int((y - radius) // self.cell_size)
        bottom_row = int((y + radius) // self.cell_size)

        for row in range(top_row, bottom_row + 1):
            for col in range(left_col, right_col + 1):
                if self._static_cell_is_blocked(row, col) and self._circle_touches_cell(x, y, radius, row, col):
                    return True

        for obstacle in self.dynamic_obstacles:
            if obstacle.touches_circle(x, y, radius):
                return True

        return False

    def _circle_touches_cell(
        self,
        x: float,
        y: float,
        radius: int,
        row: int,
        col: int,
    ) -> bool:
        cell_left = col * self.cell_size
        cell_right = cell_left + self.cell_size
        cell_top = row * self.cell_size
        cell_bottom = cell_top + self.cell_size

        closest_x = min(max(x, cell_left), cell_right)
        closest_y = min(max(y, cell_top), cell_bottom)

        distance_x = x - closest_x
        distance_y = y - closest_y

        return distance_x * distance_x + distance_y * distance_y <= radius * radius
