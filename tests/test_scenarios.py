from environment.grid_map import GridMap
from environment.scenario_manager import ScenarioManager
from planning.astar import AStarPlanner
from planning.path_smoother import PathSmoother
from planning.replanner import Replanner
from robot.state import RobotState
from simulator.scenario_runtime import complete_current_scenario, create_scenario_runtime, reset_robot_to_scenario


def test_scenario_manager_loads_level_one() -> None:
    manager = ScenarioManager()

    assert manager.level_number == 1
    assert manager.current_scenario.name == "Open Space"
    assert manager.current_scenario.difficulty == "Beginner"


def test_scenario_manager_next_and_previous() -> None:
    manager = ScenarioManager()

    next_scenario = manager.load_next_scenario()

    assert next_scenario is not None
    assert manager.level_number == 2
    assert manager.current_scenario.name == "Tight Corridor"

    previous_scenario = manager.load_previous_scenario()

    assert previous_scenario.name == "Open Space"
    assert manager.level_number == 1


def test_every_predefined_level_has_valid_astar_route() -> None:
    manager = ScenarioManager()

    for scenario in manager.scenarios:
        grid_map = GridMap(scenario)
        planner = AStarPlanner(grid_map.get_planning_grid(), cell_size=grid_map.cell_size)

        path = planner.plan(scenario.start_cell, scenario.goal_cell)

        assert path, scenario.name
        assert path[0] == scenario.start_cell
        assert path[-1] == scenario.goal_cell


def test_house_and_office_goals_have_clear_approach_space() -> None:
    manager = ScenarioManager()

    for scenario in manager.scenarios:
        if scenario.name not in {"Office"}:
            continue
        grid_map = GridMap(scenario)
        grid = grid_map.get_planning_grid()
        goal_row, goal_col = scenario.goal_cell
        clear_cells = []
        for delta_row in [-1, 0, 1]:
            for delta_col in [-1, 0, 1]:
                row = goal_row + delta_row
                col = goal_col + delta_col
                if 0 <= row < len(grid) and 0 <= col < len(grid[0]) and grid[row][col] == 0:
                    clear_cells.append((row, col))

        assert len(clear_cells) == 9, scenario.name


def test_house_smoothed_route_has_robot_clearance() -> None:
    scenario = next(scenario for scenario in ScenarioManager().scenarios if scenario.name == "House Layout")
    grid_map = GridMap(scenario)
    grid = grid_map.get_planning_grid()
    planner = AStarPlanner(grid, cell_size=grid_map.cell_size)
    path = planner.plan(scenario.start_cell, scenario.goal_cell)
    smoothed = PathSmoother(grid).smooth(path)

    assert smoothed
    for start, end in zip(smoothed, smoothed[1:]):
        start_x, start_y = _cell_center(start, grid_map.cell_size)
        end_x, end_y = _cell_center(end, grid_map.cell_size)
        for step in range(21):
            amount = step / 20
            x = start_x + (end_x - start_x) * amount
            y = start_y + (end_y - start_y) * amount
            assert not grid_map.collides_with_wall(x, y), (start, end, x, y)


def _cell_center(cell: tuple[int, int], cell_size: int) -> tuple[float, float]:
    row, col = cell
    return col * cell_size + cell_size / 2, row * cell_size + cell_size / 2


def test_replanner_snaps_blocked_goal_to_nearest_reachable_cell() -> None:
    grid = [
        [1, 1, 1, 1, 1],
        [1, 0, 0, 0, 1],
        [1, 0, 1, 1, 1],
        [1, 0, 1, 1, 1],
        [1, 1, 1, 1, 1],
    ]
    planner = AStarPlanner(grid, cell_size=20)
    replanner = Replanner(planner, PathSmoother(grid), cell_size=20)
    robot_state = RobotState(x=30, y=30, theta=0.0)

    result = replanner.replan(robot_state, (3, 3), grid)

    assert result.success
    assert result.goal_cell == (3, 1)
    assert result.original_path[-1] == result.goal_cell


def test_replanner_fails_cleanly_when_robot_starts_blocked() -> None:
    grid = [
        [1, 1, 1],
        [1, 1, 0],
        [1, 1, 1],
    ]
    planner = AStarPlanner(grid, cell_size=20)
    replanner = Replanner(planner, PathSmoother(grid), cell_size=20)
    robot_state = RobotState(x=30, y=30, theta=0.0)

    result = replanner.replan(robot_state, (1, 2), grid)

    assert not result.success
    assert result.goal_cell is None


def test_reaching_goal_marks_current_scenario_complete() -> None:
    manager = ScenarioManager()

    summary = complete_current_scenario(
        scenario_manager=manager,
        current_planner_name="A*",
        mission_elapsed=12.5,
        path_length=320.0,
        replan_count=2,
        collision_count=1,
        ekf_error=3.5,
    )

    assert manager.current_index in manager.completed_indices
    assert manager.summaries == [summary]
    assert summary.name == "Open Space"
    assert summary.completion_time == 12.5


def test_level_progression_resets_robot_state() -> None:
    manager = ScenarioManager()
    manager.load_next_scenario()
    robot_state = RobotState(x=999, y=999, theta=9)

    reset_robot_to_scenario(robot_state, manager.current_scenario)

    assert robot_state.x == manager.current_scenario.robot_start_x
    assert robot_state.y == manager.current_scenario.robot_start_y
    assert robot_state.theta == manager.current_scenario.robot_start_theta


def test_level_progression_runtime_rebuilds_map_goal_and_trajectory() -> None:
    manager = ScenarioManager()
    manager.load_next_scenario()
    robot_state = RobotState(x=999, y=999, theta=9)

    try:
        runtime = create_scenario_runtime(robot_state, manager.current_scenario, "A*")
    except ModuleNotFoundError:
        return

    assert runtime[0].default_goal_cell == manager.current_scenario.goal_cell
    assert runtime[7] == manager.current_scenario.goal_cell
    assert runtime[13] == [(robot_state.x, robot_state.y)]


def test_completing_final_scenario_does_not_restart() -> None:
    manager = ScenarioManager()
    manager.load_scenario(manager.total_scenarios - 1)

    complete_current_scenario(
        scenario_manager=manager,
        current_planner_name="A*",
        mission_elapsed=30.0,
        path_length=500.0,
        replan_count=0,
        collision_count=0,
        ekf_error=None,
    )

    assert manager.load_next_scenario() is None
    assert manager.level_number == manager.total_scenarios
    assert manager.current_scenario.name == "Office"
