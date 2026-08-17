from dataclasses import dataclass

from environment.scenario import (
    DynamicObstacleConfig,
    Rectangle,
    Scenario,
    build_grid,
    cell_center,
)


@dataclass
class ScenarioSummary:
    name: str
    planner: str
    completion_time: float
    path_length: float
    replans: int
    collisions: int
    ekf_error: float | None
    battery_start: float = 100.0
    battery_end: float = 100.0
    energy_used: float = 0.0
    charging_stops: int = 0
    energy_per_distance: float = 0.0


class ScenarioManager:
    def __init__(self, scenarios: list[Scenario] | None = None) -> None:
        self.scenarios = scenarios or create_default_scenarios()
        self.current_index = 0
        self.completed_indices: set[int] = set()
        self.summaries: list[ScenarioSummary] = []

    @property
    def current_scenario(self) -> Scenario:
        return self.scenarios[self.current_index]

    @property
    def total_scenarios(self) -> int:
        return len(self.scenarios)

    @property
    def level_number(self) -> int:
        return self.current_index + 1

    @property
    def is_final_scenario(self) -> bool:
        return self.current_index == len(self.scenarios) - 1

    def load_scenario(self, index: int) -> Scenario:
        if not 0 <= index < len(self.scenarios):
            raise IndexError(f"Scenario index out of range: {index}")
        self.current_index = index
        return self.current_scenario

    def restart_current_scenario(self) -> Scenario:
        return self.current_scenario

    def load_next_scenario(self) -> Scenario | None:
        if self.is_final_scenario:
            return None
        self.current_index += 1
        return self.current_scenario

    def load_previous_scenario(self) -> Scenario:
        self.current_index = max(0, self.current_index - 1)
        return self.current_scenario

    def mark_current_completed(self, summary: ScenarioSummary) -> None:
        self.completed_indices.add(self.current_index)
        self.summaries.append(summary)

    def restart_from_first(self) -> Scenario:
        self.current_index = 0
        self.completed_indices.clear()
        self.summaries.clear()
        return self.current_scenario


def create_default_scenarios() -> list[Scenario]:
    return [
        _open_space(),
        _tight_corridor(),
        _house_layout(),
        _warehouse(),
        _office(),
    ]


def _open_space() -> Scenario:
    obstacles: list[Rectangle] = [
        (5, 5, 4, 3),
        (8, 13, 3, 3),
        (15, 4, 5, 2),
        (18, 11, 4, 4),
        (24, 6, 2, 7),
    ]
    start_x, start_y = cell_center(3, 2)
    goal_x, goal_y = cell_center(26, 17)
    return Scenario(
        name="Open Space",
        description="Mostly open map with several rectangular obstacles and wide navigation paths.",
        difficulty="Beginner",
        grid=build_grid(rectangles=obstacles),
        robot_start_x=start_x,
        robot_start_y=start_y,
        robot_start_theta=0.0,
        goal_x=goal_x,
        goal_y=goal_y,
        static_obstacles=obstacles,
        recommended_planner="A*",
    )


def _tight_corridor() -> Scenario:
    obstacles: list[Rectangle] = [
        (3, 4, 20, 2),
        (7, 8, 20, 2),
        (3, 12, 20, 2),
        (11, 16, 15, 2),
    ]
    clear_cells = [
        (23, 4),
        (23, 5),
        (6, 8),
        (6, 9),
        (23, 12),
        (23, 13),
        (10, 16),
        (10, 17),
    ]
    start_x, start_y = cell_center(3, 2)
    goal_x, goal_y = cell_center(26, 17)
    return Scenario(
        name="Tight Corridor",
        description="Narrow corridor network with turns sized for the robot and obstacle inflation.",
        difficulty="Easy",
        grid=build_grid(rectangles=obstacles, clear_cells=clear_cells),
        robot_start_x=start_x,
        robot_start_y=start_y,
        robot_start_theta=0.0,
        goal_x=goal_x,
        goal_y=goal_y,
        static_obstacles=obstacles,
        recommended_planner="A*",
    )


def _house_layout() -> Scenario:
    obstacles: list[Rectangle] = [
        (6, 1, 1, 7),
        (6, 10, 1, 9),
        (14, 1, 1, 9),
        (14, 12, 1, 7),
        (22, 1, 1, 6),
        (22, 9, 1, 10),
        (1, 7, 5, 1),
        (8, 7, 6, 1),
        (15, 7, 7, 1),
        (1, 12, 6, 1),
        (9, 12, 5, 1),
        (15, 12, 7, 1),
        (17, 3, 2, 2),
        (3, 15, 2, 2),
    ]
    clear_cells = [
        (6, 5),
        (6, 6),
        (6, 7),
        (6, 8),
        (6, 9),
        (14, 7),
        (14, 8),
        (14, 9),
        (14, 10),
        (14, 11),
        (14, 12),
        (14, 13),
        (14, 14),
        (22, 7),
        (22, 8),
        (22, 9),
        (22, 10),
        (22, 11),
        (22, 12),
        (22, 13),
        (22, 14),
        (22, 15),
        (22, 16),
        (22, 17),
    ]
    start_x, start_y = cell_center(3, 3)
    goal_x, goal_y = cell_center(10, 11)
    return Scenario(
        name="House Layout",
        description="Simplified house floor plan with rooms, a hallway, and door openings.",
        difficulty="Intermediate",
        grid=build_grid(rectangles=obstacles, clear_cells=clear_cells),
        robot_start_x=start_x,
        robot_start_y=start_y,
        robot_start_theta=0.0,
        goal_x=goal_x,
        goal_y=goal_y,
        static_obstacles=obstacles,
        recommended_planner="A*",
    )


def _warehouse() -> Scenario:
    obstacles: list[Rectangle] = [
        (4, 3, 9, 2),
        (16, 3, 9, 2),
        (4, 7, 9, 2),
        (16, 7, 9, 2),
        (4, 11, 9, 2),
        (16, 11, 9, 2),
        (4, 15, 9, 2),
        (16, 15, 9, 2),
        (26, 2, 1, 7),
        (26, 12, 1, 6),
    ]
    start_x, start_y = cell_center(27, 2)
    goal_x, goal_y = cell_center(2, 17)
    return Scenario(
        name="Warehouse",
        description="Warehouse aisles with shelving rows, intersections, and a loading area.",
        difficulty="Intermediate / Advanced",
        grid=build_grid(rectangles=obstacles),
        robot_start_x=start_x,
        robot_start_y=start_y,
        robot_start_theta=-1.57,
        goal_x=goal_x,
        goal_y=goal_y,
        static_obstacles=obstacles,
        dynamic_obstacles=[
            DynamicObstacleConfig(110, 275, 18, 18, 35, 0, 100, 310, 275, 293),
            DynamicObstacleConfig(250, 55, 18, 18, -25, 0, 225, 365, 55, 73),
            DynamicObstacleConfig(335, 300, 18, 18, 0, 30, 335, 353, 260, 390),
        ],
        recommended_planner="A*",
    )


def _office() -> Scenario:
    obstacles: list[Rectangle] = [
        (5, 1, 1, 6),
        (5, 9, 1, 10),
        (12, 1, 1, 8),
        (12, 11, 1, 8),
        (20, 1, 1, 7),
        (20, 10, 1, 9),
        (1, 6, 4, 1),
        (7, 6, 5, 1),
        (13, 6, 7, 1),
        (1, 13, 4, 1),
        (7, 13, 5, 1),
        (14, 13, 6, 1),
        (7, 2, 2, 2),
        (8, 15, 2, 2),
        (15, 3, 2, 2),
        (16, 9, 2, 2),
        (23, 14, 2, 3),
        (25, 4, 2, 3),
    ]
    clear_cells = [
        (5, 6),
        (5, 7),
        (12, 6),
        (12, 7),
        (20, 6),
        (20, 7),
        (5, 13),
        (5, 14),
        (12, 13),
        (12, 14),
        (20, 13),
        (20, 14),
    ]
    start_x, start_y = cell_center(26, 2)
    goal_x, goal_y = cell_center(2, 17)
    return Scenario(
        name="Office",
        description="Office rooms, hallways, desks, multiple routes, and tighter turns.",
        difficulty="Advanced",
        grid=build_grid(rectangles=obstacles, clear_cells=clear_cells),
        robot_start_x=start_x,
        robot_start_y=start_y,
        robot_start_theta=-1.57,
        goal_x=goal_x,
        goal_y=goal_y,
        static_obstacles=obstacles,
        dynamic_obstacles=[
            DynamicObstacleConfig(150, 155, 18, 18, 30, 0, 140, 250, 155, 173),
            DynamicObstacleConfig(300, 430, 18, 18, -24, 0, 220, 360, 430, 448),
        ],
        recommended_planner="A*",
    )
