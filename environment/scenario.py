from dataclasses import dataclass, field

from environment.dynamic_obstacle import DynamicObstacle
from environment.grid_map import CELL_SIZE, FREE_SPACE, WALL


Grid = list[list[int]]
Rectangle = tuple[int, int, int, int]


@dataclass(frozen=True)
class DynamicObstacleConfig:
    x: float
    y: float
    width: int
    height: int
    vx: float
    vy: float
    min_x: float
    max_x: float
    min_y: float
    max_y: float

    def create(self) -> DynamicObstacle:
        return DynamicObstacle(
            x=self.x,
            y=self.y,
            width=self.width,
            height=self.height,
            vx=self.vx,
            vy=self.vy,
            min_x=self.min_x,
            max_x=self.max_x,
            min_y=self.min_y,
            max_y=self.max_y,
        )


@dataclass(frozen=True)
class Scenario:
    name: str
    description: str
    difficulty: str
    grid: Grid
    robot_start_x: float
    robot_start_y: float
    robot_start_theta: float
    goal_x: float
    goal_y: float
    static_obstacles: list[Rectangle] = field(default_factory=list)
    dynamic_obstacles: list[DynamicObstacleConfig] = field(default_factory=list)
    recommended_planner: str | None = None
    mission_label: str = "START -> TARGET"

    @property
    def start_cell(self) -> tuple[int, int]:
        return _position_to_cell(self.robot_start_x, self.robot_start_y)

    @property
    def goal_cell(self) -> tuple[int, int]:
        return _position_to_cell(self.goal_x, self.goal_y)

    def copy_grid(self) -> Grid:
        return [row.copy() for row in self.grid]

    def create_dynamic_obstacles(self) -> list[DynamicObstacle]:
        return [obstacle.create() for obstacle in self.dynamic_obstacles]


def _position_to_cell(x: float, y: float) -> tuple[int, int]:
    return int(y // CELL_SIZE), int(x // CELL_SIZE)


def cell_center(row: int, col: int) -> tuple[float, float]:
    return col * CELL_SIZE + CELL_SIZE / 2, row * CELL_SIZE + CELL_SIZE / 2


def build_grid(
    rows: int = 30,
    cols: int = 20,
    rectangles: list[Rectangle] | None = None,
    clear_cells: list[tuple[int, int]] | None = None,
) -> Grid:
    grid = [[FREE_SPACE for _ in range(cols)] for _ in range(rows)]

    for row in range(rows):
        grid[row][0] = WALL
        grid[row][cols - 1] = WALL

    for col in range(cols):
        grid[0][col] = WALL
        grid[rows - 1][col] = WALL

    for start_row, start_col, height, width in rectangles or []:
        add_rectangle(grid, start_row, start_col, height, width)

    for row, col in clear_cells or []:
        if 0 <= row < rows and 0 <= col < cols:
            grid[row][col] = FREE_SPACE

    return grid


def add_rectangle(
    grid: Grid,
    start_row: int,
    start_col: int,
    height: int,
    width: int,
) -> None:
    for row in range(start_row, start_row + height):
        for col in range(start_col, start_col + width):
            if 0 <= row < len(grid) and 0 <= col < len(grid[0]):
                grid[row][col] = WALL
