from environment.grid_map import GridMap
from environment.scenario import Scenario
from environment.scenario_manager import ScenarioManager, ScenarioSummary
from planning.astar import AStarPlanner, PlannerMetrics
from robot.state import RobotState


def create_scenario_runtime(
    robot_state: RobotState,
    scenario: Scenario,
    current_planner_name: str,
    dynamic_obstacles_enabled: bool = True,
) -> tuple[
    object,
    object,
    object,
    object,
    object,
    object,
    object,
    tuple[int, int],
    list[tuple[int, int]],
    list[tuple[int, int]],
    list[tuple[float, float]],
    int,
    PlannerMetrics,
    list[tuple[float, float]],
]:
    from mapping.occupancy_grid import OccupancyGrid
    from planning.dijkstra import DijkstraPlanner
    from planning.path_smoother import PathSmoother
    from planning.replanner import Replanner

    reset_robot_to_scenario(robot_state, scenario)
    grid_map = GridMap(scenario)
    if not dynamic_obstacles_enabled:
        grid_map.dynamic_obstacles = []
    occupancy_grid = OccupancyGrid(
        rows=len(grid_map.grid),
        cols=len(grid_map.grid[0]),
        cell_size=grid_map.cell_size,
    )
    planning_grid = grid_map.get_planning_grid()
    astar = AStarPlanner(planning_grid, cell_size=grid_map.cell_size)
    dijkstra = DijkstraPlanner(planning_grid, cell_size=grid_map.cell_size)
    active_planner = dijkstra if current_planner_name == "Dijkstra" else astar
    path_smoother = PathSmoother(planning_grid)
    replanner = Replanner(active_planner, path_smoother, grid_map.cell_size)
    goal_cell = grid_map.default_goal_cell
    result = replanner.replan(robot_state, goal_cell, planning_grid)
    planner_metrics = result.planner_metrics

    if result.success:
        original_path = result.original_path
        smoothed_path = result.smoothed_path
        waypoints = result.waypoints
    else:
        original_path = []
        smoothed_path = []
        waypoints = []
        planner_metrics = PlannerMetrics()

    return (
        grid_map,
        occupancy_grid,
        astar,
        dijkstra,
        active_planner,
        path_smoother,
        replanner,
        goal_cell,
        original_path,
        smoothed_path,
        waypoints,
        0,
        planner_metrics,
        [(robot_state.x, robot_state.y)],
    )


def reset_robot_to_scenario(robot_state: RobotState, scenario: Scenario) -> None:
    robot_state.x = scenario.robot_start_x
    robot_state.y = scenario.robot_start_y
    robot_state.theta = scenario.robot_start_theta


def complete_current_scenario(
    scenario_manager: ScenarioManager,
    current_planner_name: str,
    mission_elapsed: float,
    path_length: float,
    replan_count: int,
    collision_count: int,
    ekf_error: float | None,
    battery_start: float = 100.0,
    battery_end: float = 100.0,
    energy_used: float = 0.0,
    charging_stops: int = 0,
) -> ScenarioSummary:
    summary = ScenarioSummary(
        name=scenario_manager.current_scenario.name,
        planner=current_planner_name,
        completion_time=mission_elapsed,
        path_length=path_length,
        replans=replan_count,
        collisions=collision_count,
        ekf_error=ekf_error,
        battery_start=battery_start,
        battery_end=battery_end,
        energy_used=energy_used,
        charging_stops=charging_stops,
        energy_per_distance=0.0 if path_length <= 0 else energy_used / path_length,
    )
    scenario_manager.mark_current_completed(summary)
    return summary
