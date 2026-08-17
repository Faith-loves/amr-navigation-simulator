import math

import pygame

from ai.mission_manager import MISSION_PAUSED, MissionManager
from ai.semantic_locations import locations_for_scenario, register_custom_locations
from ai.mission_parser import (
    INTENT_CANCEL,
    INTENT_NAVIGATE,
    INTENT_MULTI_STOP,
    INTENT_PAUSE,
    INTENT_RESUME,
    INTENT_RETURN,
    INTENT_STATUS,
    INTENT_STOP,
    MISSION_RUNNING,
    MissionParseError,
    MissionParser,
)
from environment.grid_map import GridMap
from environment.scenario import Scenario
from environment.scenario_manager import ScenarioManager, ScenarioSummary
from mapping.occupancy_grid import OccupancyGrid
from planning.astar import AStarPlanner, PlannerMetrics
from planning.dijkstra import DijkstraPlanner
from planning.frontier_explorer import FrontierCluster, FrontierExplorer
from planning.path_smoother import PathSmoother
from planning.replanner import Replanner, ReplanResult
from robot.battery import BatteryManager, BatteryModel, CHARGE_CHARGED, CHARGE_CHARGING, CHARGE_DOCKING, CHARGE_NAVIGATING, CHARGE_NO_STATION, CHARGE_RESUMING
from robot.ekf import EKFLocalization
from robot.kinematics import get_next_robot_state, update_robot_state
from robot.odometry import Odometry
from robot.state import RobotState
from sensors.lidar import Lidar
from simulator.control_helpers import emergency_stop, has_manual_input, manual_command
from simulator.goal_manager import GoalManager
from simulator.replay import ReplayFrame, ReplayPlayer
from simulator.run_logger import RunLogger
from simulator.scenario_runtime import complete_current_scenario, create_scenario_runtime
from ui.app_state import MODE_AUTONOMOUS, MODE_EXPLORATION, SimulationOutcome, SimulationSettings
from utils.profiler import Profiler
from utils.report_generator import ReportGenerator
from visualization.lidar_view import LIDAR_VIEW_MINIMAL, next_lidar_view_mode
from visualization.pygame_dashboard import GROUND_TRUTH_MAP_X, GROUND_TRUTH_MAP_Y, MAP_HEIGHT, MAP_WIDTH, WINDOW_WIDTH, PygameDashboard


LINEAR_SPEED = 150
ANGULAR_SPEED = 2
K_V = 2.0
K_OMEGA = 4.0
MAX_LINEAR_SPEED = 120
MAX_ANGULAR_SPEED = 3.0
WAYPOINT_TOLERANCE = 10
REPLAN_INTERVAL = 2.0
TRAIL_MIN_DISTANCE = 3
MAX_TRAIL_POINTS = 2000
MISSION_COMPLETE_DURATION = 1.5
GOAL_REACHED_STATUS = "Goal reached."


def run_simulation(
    robot_state: RobotState,
    settings: SimulationSettings | None = None,
    replay_file: str = "",
) -> SimulationOutcome:
    settings = settings or SimulationSettings()
    if settings.custom_scenario is not None:
        scenario_manager = ScenarioManager([settings.custom_scenario])
        scenario_manager.load_scenario(0)
        register_custom_locations(settings.custom_scenario.name, settings.custom_semantic_locations)
    else:
        scenario_manager = ScenarioManager()
        scenario_manager.load_scenario(settings.scenario_index)
    current_planner_name = settings.planner
    (
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
        current_waypoint_index,
        planner_metrics,
        trajectory,
    ) = create_scenario_runtime(
        robot_state,
        scenario_manager.current_scenario,
        current_planner_name,
        settings.dynamic_obstacles_enabled,
    )
    frontier_explorer = FrontierExplorer()
    lidar = Lidar()
    odometry = Odometry(robot_state)
    ekf = EKFLocalization(robot_state)
    dashboard = PygameDashboard()
    run_logger = RunLogger()
    replay_player = ReplayPlayer()
    profiler = Profiler()
    report_generator = ReportGenerator()
    mission_parser = MissionParser()
    mission_manager = MissionManager()
    goal_manager = GoalManager(scenario_manager.current_scenario.goal_cell, scenario_manager.current_scenario.mission_label)
    battery_manager = BatteryManager(
        BatteryModel(),
        enabled=settings.battery_simulation_enabled,
        auto_return_enabled=settings.auto_return_to_charger,
    )
    battery_start_percentage = battery_manager.battery.percentage

    autonomous_mode = settings.mode == MODE_AUTONOMOUS
    exploration_mode = settings.mode == MODE_EXPLORATION
    seconds_since_replan = 0.0
    replan_count = 0
    last_replan_time_ms = 0.0
    status_message = ""
    collision_status = False
    previous_collision_status = False
    collision_count = 0
    mission_elapsed = 0.0
    mission_complete_timer = 0.0
    mission_summary: ScenarioSummary | None = None
    all_missions_complete = False
    frontier_cells: list[tuple[int, int]] = []
    frontier_clusters: list[FrontierCluster] = []
    current_frontier_target: tuple[int, int] | None = None
    v = 0.0
    omega = 0.0
    show_profiler = False
    lidar_view_mode = settings.lidar_view_mode
    stopped_timer = 0.0
    simulation_outcome = SimulationOutcome(action="HOME")
    if replay_file:
        replay_player.load(replay_file)

    running = True

    while running:
        dt = dashboard.tick()
        profiler.start_section("frame")

        if autonomous_mode:
            seconds_since_replan += dt
        else:
            seconds_since_replan = 0.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            submitted_command, mission_event_consumed = dashboard.handle_mission_event(event)
            if submitted_command:
                previous_goal_cell = goal_cell
                (
                    goal_cell,
                    original_path,
                    smoothed_path,
                    waypoints,
                    current_waypoint_index,
                    planner_metrics,
                    autonomous_mode,
                    exploration_mode,
                    status_message,
                    seconds_since_replan,
                    last_replan_time_ms,
                ) = _submit_mission_command(
                    raw_command=submitted_command,
                    scenario_name=scenario_manager.current_scenario.name,
                    mission_parser=mission_parser,
                    mission_manager=mission_manager,
                    robot_state=robot_state,
                    grid_map=grid_map,
                    replanner=replanner,
                    profiler=profiler,
                    autonomous_mode=autonomous_mode,
                    exploration_mode=exploration_mode,
                    fallback_goal_cell=goal_cell,
                    fallback_original_path=original_path,
                    fallback_smoothed_path=smoothed_path,
                    fallback_waypoints=waypoints,
                    fallback_waypoint_index=current_waypoint_index,
                    fallback_planner_metrics=planner_metrics,
                    fallback_seconds_since_replan=seconds_since_replan,
                    fallback_last_replan_time_ms=last_replan_time_ms,
                )
                if goal_cell is not None and goal_cell != previous_goal_cell and status_message.startswith("Mission task:"):
                    goal_manager.set_mission_goal(goal_cell, status_message.replace("Mission task:", "").strip(), "AI mission command")
            if mission_event_consumed:
                continue

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_1:
                    active_planner = astar
                    current_planner_name = "A*"
                    replanner.set_planner(active_planner)
                    planner_metrics = active_planner.latest_metrics

                if event.key == pygame.K_2:
                    active_planner = dijkstra
                    current_planner_name = "Dijkstra"
                    replanner.set_planner(active_planner)
                    planner_metrics = active_planner.latest_metrics

                if event.key == pygame.K_f:
                    if autonomous_mode:
                        autonomous_mode = False
                        mission_manager.pause()
                        status_message = "Manual control."
                    elif waypoints:
                        if mission_manager.mission_status == MISSION_PAUSED:
                            mission_manager.resume()
                        autonomous_mode = True
                        current_waypoint_index = _skip_reached_waypoints(
                            robot_state,
                            waypoints,
                            current_waypoint_index,
                        )
                        seconds_since_replan = 0.0
                        status_message = "Autonomous navigation started."
                    else:
                        status_message = "No path to follow."
                        print(status_message)

                if event.key == pygame.K_SPACE:
                    stop_command = emergency_stop()
                    v = stop_command.v
                    omega = stop_command.omega
                    autonomous_mode = False
                    mission_manager.pause()
                    stopped_timer = 1.2
                    status_message = "STOPPED"

                if event.key == pygame.K_v:
                    lidar_view_mode = next_lidar_view_mode(lidar_view_mode)

                if event.key == pygame.K_3:
                    status_message = "RRT* planner is not available in this build."

                if event.key == pygame.K_k:
                    battery_manager.battery.set_percentage(22.0)
                    status_message = "Demo Low Battery: 22%."

                if event.key == pygame.K_t:
                    show_profiler = not show_profiler

                if event.key == pygame.K_x:
                    report_path = report_generator.generate_from_latest_log()
                    if report_path is None:
                        status_message = "No log file found for report."
                        print(status_message)
                    else:
                        status_message = f"Report generated: {report_path.name}"
                        print(status_message)

                if event.key == pygame.K_l:
                    if not replay_player.is_active:
                        run_logger.toggle()

                if event.key == pygame.K_o:
                    run_logger.stop()
                    if replay_player.load_latest():
                        autonomous_mode = False
                        exploration_mode = False
                        status_message = "Replay loaded."
                    else:
                        status_message = "No replay log found."
                        print(status_message)

                if event.key == pygame.K_p:
                    replay_player.toggle_playback()

                if event.key == pygame.K_n:
                    replay_player.next_frame()

                if event.key == pygame.K_b:
                    replay_player.previous_frame()

                if event.key == pygame.K_ESCAPE and replay_player.is_active:
                    replay_player.exit()
                    simulation_outcome = SimulationOutcome(action="HOME")
                    running = False
                    continue

                if event.key == pygame.K_ESCAPE:
                    autonomous_mode = False
                    exploration_mode = False
                    v = 0.0
                    omega = 0.0
                    mission_manager.pause()
                    simulation_outcome = SimulationOutcome(action="HOME")
                    running = False
                    continue

                if event.key == pygame.K_e:
                    exploration_mode = not exploration_mode
                    autonomous_mode = False
                    current_waypoint_index = 0

                    if exploration_mode:
                        goal_manager.set_exploration_goal(goal_cell or scenario_manager.current_scenario.goal_cell, "Exploration", "Exploration mode enabled")
                        goal_cell = None
                        original_path = []
                        smoothed_path = []
                        waypoints = []
                        current_frontier_target = None
                        status_message = "Exploration started."
                    else:
                        goal_manager.stop_exploration()
                        goal_cell = goal_manager.active_goal
                        status_message = "Exploration stopped."

                if event.key == pygame.K_r:
                    if all_missions_complete:
                        scenario_manager.restart_from_first()
                    (
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
                        current_waypoint_index,
                        planner_metrics,
                        trajectory,
                    ) = create_scenario_runtime(
                        robot_state,
                        scenario_manager.current_scenario,
                        current_planner_name,
                        settings.dynamic_obstacles_enabled,
                    )
                    odometry.reset(robot_state)
                    ekf.reset(robot_state)
                    autonomous_mode = False
                    exploration_mode = False
                    seconds_since_replan = 0.0
                    replan_count = 0
                    last_replan_time_ms = 0.0
                    status_message = "Reset complete."
                    collision_status = False
                    previous_collision_status = False
                    collision_count = 0
                    mission_elapsed = 0.0
                    mission_complete_timer = 0.0
                    mission_summary = None
                    all_missions_complete = False
                    frontier_cells = []
                    frontier_clusters = []
                    current_frontier_target = None
                    v = 0.0
                    omega = 0.0
                    mission_manager.reset()
                    goal_manager = GoalManager(scenario_manager.current_scenario.goal_cell, scenario_manager.current_scenario.mission_label)
                    goal_cell = goal_manager.active_goal

                if event.key == pygame.K_RIGHTBRACKET:
                    if scenario_manager.load_next_scenario() is not None:
                        (
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
                            current_waypoint_index,
                            planner_metrics,
                            trajectory,
                        ) = create_scenario_runtime(
                            robot_state,
                            scenario_manager.current_scenario,
                            current_planner_name,
                            settings.dynamic_obstacles_enabled,
                        )
                        odometry.reset(robot_state)
                        ekf.reset(robot_state)
                        autonomous_mode = False
                        exploration_mode = False
                        seconds_since_replan = 0.0
                        replan_count = 0
                        last_replan_time_ms = 0.0
                        status_message = ""
                        collision_status = False
                        previous_collision_status = False
                        collision_count = 0
                        mission_elapsed = 0.0
                        mission_complete_timer = 0.0
                        mission_summary = None
                        all_missions_complete = False
                        frontier_cells = []
                        frontier_clusters = []
                        current_frontier_target = None
                        v = 0.0
                        omega = 0.0

                if event.key == pygame.K_LEFTBRACKET:
                    scenario_manager.load_previous_scenario()
                    (
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
                        current_waypoint_index,
                        planner_metrics,
                        trajectory,
                    ) = create_scenario_runtime(
                        robot_state,
                        scenario_manager.current_scenario,
                        current_planner_name,
                        settings.dynamic_obstacles_enabled,
                    )
                    odometry.reset(robot_state)
                    ekf.reset(robot_state)
                    autonomous_mode = False
                    exploration_mode = False
                    seconds_since_replan = 0.0
                    replan_count = 0
                    last_replan_time_ms = 0.0
                    status_message = ""
                    collision_status = False
                    previous_collision_status = False
                    collision_count = 0
                    mission_elapsed = 0.0
                    mission_complete_timer = 0.0
                    mission_summary = None
                    all_missions_complete = False
                    frontier_cells = []
                    frontier_clusters = []
                    current_frontier_target = None
                    v = 0.0
                    omega = 0.0
                    mission_manager.reset()
                    goal_manager = GoalManager(scenario_manager.current_scenario.goal_cell, scenario_manager.current_scenario.mission_label)
                    goal_cell = goal_manager.active_goal

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_x, mouse_y = event.pos
                if _mouse_on_auto_badge(mouse_x, mouse_y):
                    if autonomous_mode:
                        autonomous_mode = False
                        status_message = "Manual control."
                    elif waypoints and not all_missions_complete:
                        autonomous_mode = True
                        exploration_mode = False
                        current_waypoint_index = _skip_reached_waypoints(
                            robot_state,
                            waypoints,
                            current_waypoint_index,
                        )
                        seconds_since_replan = 0.0
                        status_message = "Autonomous navigation started."
                    else:
                        status_message = "No path to follow."
                        print(status_message)

        if stopped_timer > 0.0:
            stopped_timer = max(0.0, stopped_timer - dt)
            if stopped_timer == 0.0 and status_message == "STOPPED":
                status_message = ""

        if mission_complete_timer > 0.0:
            mission_complete_timer = max(0.0, mission_complete_timer - dt)
            if mission_complete_timer == 0.0:
                if not settings.auto_advance:
                    simulation_outcome = SimulationOutcome(action="RESULTS", summary=mission_summary)
                    running = False
                elif scenario_manager.is_final_scenario:
                    all_missions_complete = True
                    status_message = "ALL MISSIONS COMPLETE"
                else:
                    scenario_manager.load_next_scenario()
                    (
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
                        current_waypoint_index,
                        planner_metrics,
                        trajectory,
                    ) = create_scenario_runtime(
                        robot_state,
                        scenario_manager.current_scenario,
                        current_planner_name,
                        settings.dynamic_obstacles_enabled,
                    )
                    odometry.reset(robot_state)
                    ekf.reset(robot_state)
                    autonomous_mode = False
                    exploration_mode = False
                    seconds_since_replan = 0.0
                    replan_count = 0
                    last_replan_time_ms = 0.0
                    status_message = ""
                    collision_status = False
                    previous_collision_status = False
                    collision_count = 0
                    mission_elapsed = 0.0
                    mission_summary = None
                    frontier_cells = []
                    frontier_clusters = []
                    current_frontier_target = None
                    v = 0.0
                    omega = 0.0
                    mission_manager.reset()
                    goal_manager = GoalManager(scenario_manager.current_scenario.goal_cell, scenario_manager.current_scenario.mission_label)
                    goal_cell = goal_manager.active_goal
                    stopped_timer = 0.0
        elif not all_missions_complete:
            mission_elapsed += dt

        if replay_player.is_active:
            profiler.record("physics", 0.0)
            profiler.record("lidar", 0.0)
            profiler.record("mapping", 0.0)
            profiler.record("planner", 0.0)
            replay_player.update(dt)
            profiler.start_section("render")
            _draw_replay_frame(
                dashboard=dashboard,
                frame=replay_player.current_frame,
                grid_map=grid_map,
                occupancy_grid=occupancy_grid,
                replay_player=replay_player,
                logging_mode=run_logger.is_logging,
                log_file_name=run_logger.current_file_name,
                status_message=status_message,
                profiler_visible=show_profiler,
                profiler_metrics=_profiler_metrics(profiler),
            )
            profiler.end_section("render")
            profiler.end_section("frame")
            continue

        profiler.start_section("physics")
        grid_map.update_dynamic_obstacles(dt)
        profiler.end_section("physics")

        if autonomous_mode and goal_cell is not None and mission_complete_timer == 0.0 and not all_missions_complete:
            planning_grid = grid_map.get_planning_grid()
            needs_replan = (
                not smoothed_path
                or not waypoints
                or not replanner.path_is_valid(smoothed_path, planning_grid)
                or seconds_since_replan >= REPLAN_INTERVAL
            )

            if battery_manager.should_request_charger(autonomous_mode, not autonomous_mode and not exploration_mode):
                charger_cell = _charging_station_cell(scenario_manager.current_scenario.name, grid_map.cell_size)
                if battery_manager.start_return_to_charger(goal_manager.active_goal, charger_cell):
                    mission_manager.pause()
                    if charger_cell is not None:
                        goal_manager.set_temporary_goal(charger_cell, "Charging Station", "Critical battery")
                    goal_cell = goal_manager.active_goal
                    result = _profiled_replan(profiler, replanner, robot_state, goal_cell, planning_grid)
                    planner_metrics = result.planner_metrics
                    replan_count += 1
                    last_replan_time_ms = result.planning_time_ms
                    seconds_since_replan = 0.0
                    if result.success:
                        goal_manager.record_path_repair(result.goal_cell)
                        original_path, smoothed_path, waypoints = _apply_replan_result(result)
                        current_waypoint_index = _skip_reached_waypoints(robot_state, waypoints, 0)
                        autonomous_mode = True
                        exploration_mode = False
                        status_message = "BATTERY CRITICAL - RETURNING TO CHARGER"
                    else:
                        battery_manager.charge_state = CHARGE_NO_STATION
                        autonomous_mode = False
                        status_message = "CRITICAL BATTERY - NO CHARGING STATION"
                else:
                    status_message = "CRITICAL BATTERY - NO CHARGING STATION"

            if needs_replan and battery_manager.charge_state != CHARGE_CHARGING:
                result = _profiled_replan(profiler, replanner, robot_state, goal_cell, planning_grid)
                planner_metrics = result.planner_metrics
                replan_count += 1
                last_replan_time_ms = result.planning_time_ms
                seconds_since_replan = 0.0

                if result.success:
                    goal_manager.record_path_repair(result.goal_cell)
                    original_path, smoothed_path, waypoints = _apply_replan_result(result)
                    current_waypoint_index = _skip_reached_waypoints(robot_state, waypoints, 0)
                    status_message = ""
                else:
                    autonomous_mode = False
                    exploration_mode = False
                    if mission_manager.mission_status == MISSION_RUNNING:
                        mission_manager.fail_current_task("Planning failed for mission target.")
                    status_message = "Replanning failed: no valid path."
                    print(status_message)

        profiler.start_section("physics")
        if battery_manager.battery.is_depleted():
            v = 0.0
            omega = 0.0
            autonomous_mode = False
            exploration_mode = False
            status_message = "BATTERY DEPLETED"
        elif battery_manager.charge_state == CHARGE_CHARGING:
            v = 0.0
            omega = 0.0
        elif stopped_timer > 0.0 or mission_complete_timer > 0.0 or all_missions_complete:
            v = 0.0
            omega = 0.0
        elif autonomous_mode:
            manual_v, manual_omega = _manual_control()
            if _manual_input_active(manual_v, manual_omega):
                v = manual_v
                omega = manual_omega
                autonomous_mode = False
                mission_manager.pause()
                current_waypoint_index = _skip_reached_waypoints(
                    robot_state,
                    waypoints,
                    current_waypoint_index,
                )
                status_message = "MANUAL OVERRIDE"
            else:
                v, omega, current_waypoint_index, autonomous_mode, status_message = _follow_path(
                    robot_state,
                    waypoints,
                    current_waypoint_index,
                    autonomous_mode,
                    status_message,
                )
                if battery_manager.charge_state == CHARGE_DOCKING:
                    v = min(v, 35.0)
                    omega = max(-1.0, min(omega, 1.0))
        else:
            v, omega = _manual_control()

        battery_manager.update_consumption(v, omega, dt)
        if battery_manager.battery.is_critical() and not autonomous_mode and not status_message:
            status_message = "BATTERY CRITICAL"
        elif battery_manager.battery.is_low() and not status_message:
            status_message = "LOW BATTERY"
        next_state = get_next_robot_state(robot_state, v, omega, dt)
        collision_status = grid_map.collides_with_wall(next_state.x, next_state.y)

        if collision_status and not previous_collision_status:
            collision_count += 1
        previous_collision_status = collision_status

        if not collision_status:
            update_robot_state(robot_state, next_state)
            odometry.update(v, omega, dt)
            ekf.step(v, omega, dt, robot_state)
        else:
            if autonomous_mode and goal_cell is not None:
                result = _profiled_replan(profiler, replanner,
                    robot_state,
                    goal_cell,
                    grid_map.get_planning_grid(),
                )
                planner_metrics = result.planner_metrics
                replan_count += 1
                last_replan_time_ms = result.planning_time_ms
                seconds_since_replan = 0.0

                if result.success:
                    goal_manager.record_path_repair(result.goal_cell)
                    original_path, smoothed_path, waypoints = _apply_replan_result(result)
                    current_waypoint_index = _skip_reached_waypoints(robot_state, waypoints, 0)
                    status_message = ""
                else:
                    autonomous_mode = False
                    exploration_mode = False
                    v = 0.0
                    omega = 0.0
                    status_message = "Replanning failed: no valid path."
                    print(status_message)
            else:
                robot_state.theta = next_state.theta

        _add_trajectory_point(trajectory, robot_state)
        if battery_manager.returning_to_charger:
            distance_to_charger = _distance_to_goal(robot_state, battery_manager.charger_cell, grid_map.cell_size)
            battery_manager.update_docking(distance_to_charger)
            if battery_manager.charge_state == CHARGE_DOCKING:
                status_message = "DOCKING"
            if battery_manager.charge_state == CHARGE_CHARGING:
                autonomous_mode = False
                v = 0.0
                omega = 0.0
                status_message = "CHARGING"
                if battery_manager.update_charging(dt):
                    status_message = "CHARGED"
                    resume_goal = battery_manager.begin_resume()
                    if resume_goal is not None:
                        result = _profiled_replan(profiler, replanner, robot_state, resume_goal, grid_map.get_planning_grid())
                        planner_metrics = result.planner_metrics
                        last_replan_time_ms = result.planning_time_ms
                        if result.success:
                            goal_cell = goal_manager.clear_temporary_goal("Battery charged") or resume_goal
                            original_path, smoothed_path, waypoints = _apply_replan_result(result)
                            current_waypoint_index = _skip_reached_waypoints(robot_state, waypoints, 0)
                            mission_manager.resume()
                            autonomous_mode = True
                            exploration_mode = False
                            status_message = "RESUMING MISSION"
                            battery_manager.finish_resume()
                        else:
                            status_message = "Unable to resume mission after charging."

        if not battery_manager.returning_to_charger and mission_manager.reached_current_target(robot_state.x, robot_state.y, WAYPOINT_TOLERANCE):
            next_task = mission_manager.complete_current_task()
            if next_task is None:
                autonomous_mode = False
                status_message = "MISSION COMPLETE"
            else:
                result = _profiled_replan(
                    profiler,
                    replanner,
                    robot_state,
                    _position_to_cell(next_task.target_position, grid_map.cell_size),
                    grid_map.get_planning_grid(),
                )
                planner_metrics = result.planner_metrics
                seconds_since_replan = 0.0
                last_replan_time_ms = result.planning_time_ms
                if result.success:
                    next_goal_cell = _position_to_cell(next_task.target_position, grid_map.cell_size)
                    goal_manager.set_mission_goal(next_goal_cell, next_task.target_name, "Mission task completed")
                    goal_cell = goal_manager.active_goal
                    original_path, smoothed_path, waypoints = _apply_replan_result(result)
                    current_waypoint_index = _skip_reached_waypoints(robot_state, waypoints, 0)
                    autonomous_mode = True
                    exploration_mode = False
                    status_message = f"Mission task: {next_task.target_name}"
                else:
                    mission_manager.fail_current_task("Planning failed for mission target.")
                    autonomous_mode = False
                    status_message = mission_manager.last_error

        reached_scenario_goal = _reached_scenario_goal(
            robot_state,
            goal_cell,
            scenario_manager.current_scenario.goal_cell,
            grid_map.cell_size,
        )
        if (
            not battery_manager.returning_to_charger
            and (status_message == GOAL_REACHED_STATUS or reached_scenario_goal)
            and mission_complete_timer == 0.0
            and not all_missions_complete
        ):
            mission_summary = complete_current_scenario(
                scenario_manager=scenario_manager,
                current_planner_name=current_planner_name,
                mission_elapsed=mission_elapsed,
                path_length=planner_metrics.path_length_pixels,
                replan_count=replan_count,
                collision_count=collision_count,
                ekf_error=ekf.position_error(robot_state),
                battery_start=battery_start_percentage,
                battery_end=battery_manager.battery.percentage,
                energy_used=battery_manager.battery.energy_consumed,
                charging_stops=battery_manager.charging_stops,
            )
            mission_complete_timer = MISSION_COMPLETE_DURATION
            status_message = "MISSION COMPLETE"
            autonomous_mode = False
            exploration_mode = False
            if not settings.auto_advance:
                simulation_outcome = SimulationOutcome(action="RESULTS", summary=mission_summary)
                running = False
        profiler.end_section("physics")

        profiler.start_section("lidar")
        lidar_rays = lidar.scan(robot_state, grid_map)
        profiler.end_section("lidar")

        profiler.start_section("mapping")
        occupancy_grid.update_from_lidar(lidar_rays)
        profiler.end_section("mapping")

        robot_cell = _pixel_to_cell(robot_state.x, robot_state.y, grid_map.cell_size)
        frontier_clusters = frontier_explorer.find_frontier_clusters(occupancy_grid, robot_cell)
        frontier_cells = [cell for cluster in frontier_clusters for cell in cluster.cells]

        if exploration_mode and not autonomous_mode:
            if frontier_clusters:
                result, selected_frontier = _plan_to_best_frontier(
                    frontier_clusters,
                    robot_state,
                    grid_map,
                    replanner,
                    profiler,
                )
                planner_metrics = result.planner_metrics
                seconds_since_replan = 0.0

                if result.success and selected_frontier is not None:
                    goal_manager.set_exploration_goal(selected_frontier.centroid_cell, "Exploration Frontier", "Exploration frontier selected")
                    goal_cell = goal_manager.active_goal
                    current_frontier_target = goal_cell
                    original_path, smoothed_path, waypoints = _apply_replan_result(result)
                    current_waypoint_index = _skip_reached_waypoints(robot_state, waypoints, 0)
                    autonomous_mode = True
                    status_message = ""
                else:
                    exploration_mode = False
                    autonomous_mode = False
                    status_message = "Replanning failed: no valid path."
                    print(status_message)
            else:
                exploration_mode = False
                autonomous_mode = False
                current_frontier_target = None
                goal_manager.stop_exploration("Exploration complete")
                goal_cell = goal_manager.active_goal
                status_message = "Exploration complete."
                print(status_message)

        current_target = _current_target_waypoint(waypoints, current_waypoint_index, autonomous_mode)
        distance_to_goal = _distance_to_goal(robot_state, goal_cell, grid_map.cell_size)
        odometry_state = odometry.get_pose()
        ekf_state = ekf.get_pose()

        run_logger.log_frame(
            robot_state=robot_state,
            odometry_state=odometry_state,
            ekf_state=ekf_state,
            goal_position=_goal_cell_to_position(goal_manager.active_goal, grid_map.cell_size),
            current_planner=current_planner_name,
            autonomous_mode=autonomous_mode,
            exploration_mode=exploration_mode,
            replan_count=replan_count,
            collision_status=collision_status,
            distance_to_goal=distance_to_goal,
            mission_info=_navigation_snapshot(mission_manager.snapshot(), goal_manager),
            battery_info=battery_manager.snapshot(),
        )

        profiler.start_section("render")
        dashboard.draw(
            robot_state=robot_state,
            grid_map=grid_map,
            lidar_rays=lidar_rays,
            occupancy_grid=occupancy_grid,
            goal_cell=goal_manager.active_goal,
            original_path=original_path,
            smoothed_path=smoothed_path,
            status_message=status_message,
            autonomous_mode=autonomous_mode,
            current_target=current_target,
            replan_count=replan_count,
            last_replan_time_ms=last_replan_time_ms,
            planner_metrics=planner_metrics,
            trajectory=trajectory,
            linear_velocity=v,
            angular_velocity=omega,
            distance_to_goal=distance_to_goal,
            collision_status=collision_status,
            odometry_state=odometry_state,
            odometry_error=odometry.position_error(robot_state),
            ekf_state=ekf_state,
            ekf_error=ekf.position_error(robot_state),
            ekf_covariance_trace=ekf.covariance_trace(),
            current_planner_name=current_planner_name,
            exploration_mode=exploration_mode,
            frontier_cells=frontier_cells,
            frontier_cluster_count=len(frontier_clusters),
            current_frontier_target=current_frontier_target,
            logging_mode=run_logger.is_logging,
            log_file_name=run_logger.current_file_name,
            replay_mode=replay_player.is_active,
            replay_frame_index=replay_player.frame_index,
            replay_frame_count=replay_player.frame_count,
            replay_file_name=replay_player.file_name,
            profiler_visible=show_profiler,
            profiler_metrics=_profiler_metrics(profiler),
            scenario_level=scenario_manager.level_number,
            scenario_count=scenario_manager.total_scenarios,
            scenario_name=scenario_manager.current_scenario.name,
            scenario_difficulty=scenario_manager.current_scenario.difficulty,
            mission_label=scenario_manager.current_scenario.mission_label,
            start_cell=scenario_manager.current_scenario.start_cell,
            mission_complete=mission_complete_timer > 0.0,
            all_missions_complete=all_missions_complete,
            mission_summary=mission_summary,
            all_mission_summaries=scenario_manager.summaries,
            mission_snapshot=_navigation_snapshot(mission_manager.snapshot(), goal_manager),
            battery_snapshot=battery_manager.snapshot(),
            lidar_view_mode=lidar_view_mode,
            control_mode=_control_mode(autonomous_mode, exploration_mode, stopped_timer, status_message),
        )
        profiler.end_section("render")
        profiler.end_section("frame")

    run_logger.close()
    dashboard.close()
    return simulation_outcome






def _submit_mission_command(
    raw_command: str,
    scenario_name: str,
    mission_parser: MissionParser,
    mission_manager: MissionManager,
    robot_state: RobotState,
    grid_map: GridMap,
    replanner: Replanner,
    profiler: Profiler,
    autonomous_mode: bool,
    exploration_mode: bool,
    fallback_goal_cell: tuple[int, int] | None,
    fallback_original_path: list[tuple[int, int]],
    fallback_smoothed_path: list[tuple[int, int]],
    fallback_waypoints: list[tuple[float, float]],
    fallback_waypoint_index: int,
    fallback_planner_metrics: PlannerMetrics,
    fallback_seconds_since_replan: float,
    fallback_last_replan_time_ms: float,
) -> tuple[
    tuple[int, int] | None,
    list[tuple[int, int]],
    list[tuple[int, int]],
    list[tuple[float, float]],
    int,
    PlannerMetrics,
    bool,
    bool,
    str,
    float,
    float,
]:
    parsed = mission_parser.parse_intent(raw_command, scenario_name)

    if parsed.intent == INTENT_STOP:
        mission_manager.pause()
        return _mission_fallback(
            fallback_goal_cell,
            fallback_original_path,
            fallback_smoothed_path,
            fallback_waypoints,
            fallback_waypoint_index,
            fallback_planner_metrics,
            False,
            exploration_mode,
            "STOPPED",
            fallback_seconds_since_replan,
            fallback_last_replan_time_ms,
        )

    if parsed.intent == INTENT_PAUSE:
        mission_manager.pause()
        return _mission_fallback(
            fallback_goal_cell,
            fallback_original_path,
            fallback_smoothed_path,
            fallback_waypoints,
            fallback_waypoint_index,
            fallback_planner_metrics,
            False,
            exploration_mode,
            "Mission paused.",
            fallback_seconds_since_replan,
            fallback_last_replan_time_ms,
        )

    if parsed.intent == INTENT_CANCEL:
        mission_manager.cancel()
        return _mission_fallback(
            fallback_goal_cell,
            fallback_original_path,
            fallback_smoothed_path,
            fallback_waypoints,
            fallback_waypoint_index,
            fallback_planner_metrics,
            False,
            False,
            "Mission cancelled.",
            fallback_seconds_since_replan,
            fallback_last_replan_time_ms,
        )

    if parsed.intent == INTENT_STATUS:
        task = mission_manager.current_task
        target = "no active target" if task is None else task.target_name
        return _mission_fallback(
            fallback_goal_cell,
            fallback_original_path,
            fallback_smoothed_path,
            fallback_waypoints,
            fallback_waypoint_index,
            fallback_planner_metrics,
            autonomous_mode,
            exploration_mode,
            f"Mission status: {mission_manager.mission_status}, target: {target}.",
            fallback_seconds_since_replan,
            fallback_last_replan_time_ms,
        )

    if parsed.intent == INTENT_RESUME:
        task = mission_manager.resume()
        if task is None:
            if fallback_waypoints:
                return _mission_fallback(
                    fallback_goal_cell,
                    fallback_original_path,
                    fallback_smoothed_path,
                    fallback_waypoints,
                    fallback_waypoint_index,
                    fallback_planner_metrics,
                    True,
                    False,
                    "Autonomous navigation resumed.",
                    0.0,
                    fallback_last_replan_time_ms,
                )
            return _mission_fallback(
                fallback_goal_cell,
                fallback_original_path,
                fallback_smoothed_path,
                fallback_waypoints,
                fallback_waypoint_index,
                fallback_planner_metrics,
                autonomous_mode,
                exploration_mode,
                "No mission to resume.",
                fallback_seconds_since_replan,
                fallback_last_replan_time_ms,
            )
        return _plan_mission_task(
            task,
            mission_manager,
            robot_state,
            grid_map,
            replanner,
            profiler,
            fallback_goal_cell,
            fallback_original_path,
            fallback_smoothed_path,
            fallback_waypoints,
            fallback_waypoint_index,
            fallback_planner_metrics,
            "Mission resumed.",
        )

    if parsed.intent not in {INTENT_NAVIGATE, INTENT_MULTI_STOP, INTENT_RETURN}:
        return _mission_fallback(
            fallback_goal_cell,
            fallback_original_path,
            fallback_smoothed_path,
            fallback_waypoints,
            fallback_waypoint_index,
            fallback_planner_metrics,
            autonomous_mode,
            exploration_mode,
            parsed.error_message or "No valid destination found.",
            fallback_seconds_since_replan,
            fallback_last_replan_time_ms,
        )

    try:
        mission = mission_parser.parse(raw_command, scenario_name)
    except MissionParseError as error:
        mission_manager.reset()
        return _mission_fallback(
            fallback_goal_cell,
            fallback_original_path,
            fallback_smoothed_path,
            fallback_waypoints,
            fallback_waypoint_index,
            fallback_planner_metrics,
            autonomous_mode,
            exploration_mode,
            str(error),
            fallback_seconds_since_replan,
            fallback_last_replan_time_ms,
        )

    task = mission_manager.start(mission)
    if task is None:
        return _mission_fallback(
            fallback_goal_cell,
            fallback_original_path,
            fallback_smoothed_path,
            fallback_waypoints,
            fallback_waypoint_index,
            fallback_planner_metrics,
            False,
            False,
            mission_manager.last_error or "No valid destination found.",
            fallback_seconds_since_replan,
            fallback_last_replan_time_ms,
        )

    return _plan_mission_task(
        task,
        mission_manager,
        robot_state,
        grid_map,
        replanner,
        profiler,
        fallback_goal_cell,
        fallback_original_path,
        fallback_smoothed_path,
        fallback_waypoints,
        fallback_waypoint_index,
        fallback_planner_metrics,
        f"Mission task: {task.target_name}",
    )


def _mission_fallback(
    goal_cell: tuple[int, int] | None,
    original_path: list[tuple[int, int]],
    smoothed_path: list[tuple[int, int]],
    waypoints: list[tuple[float, float]],
    waypoint_index: int,
    planner_metrics: PlannerMetrics,
    autonomous_mode: bool,
    exploration_mode: bool,
    status_message: str,
    seconds_since_replan: float,
    last_replan_time_ms: float,
) -> tuple[
    tuple[int, int] | None,
    list[tuple[int, int]],
    list[tuple[int, int]],
    list[tuple[float, float]],
    int,
    PlannerMetrics,
    bool,
    bool,
    str,
    float,
    float,
]:
    return (
        goal_cell,
        original_path,
        smoothed_path,
        waypoints,
        waypoint_index,
        planner_metrics,
        autonomous_mode,
        exploration_mode,
        status_message,
        seconds_since_replan,
        last_replan_time_ms,
    )


def _plan_mission_task(
    task,
    mission_manager: MissionManager,
    robot_state: RobotState,
    grid_map: GridMap,
    replanner: Replanner,
    profiler: Profiler,
    fallback_goal_cell: tuple[int, int] | None,
    fallback_original_path: list[tuple[int, int]],
    fallback_smoothed_path: list[tuple[int, int]],
    fallback_waypoints: list[tuple[float, float]],
    fallback_waypoint_index: int,
    fallback_planner_metrics: PlannerMetrics,
    success_message: str,
) -> tuple[
    tuple[int, int] | None,
    list[tuple[int, int]],
    list[tuple[int, int]],
    list[tuple[float, float]],
    int,
    PlannerMetrics,
    bool,
    bool,
    str,
    float,
    float,
]:
    target_cell = _position_to_cell(task.target_position, grid_map.cell_size)
    result = _profiled_replan(profiler, replanner, robot_state, target_cell, grid_map.get_planning_grid())
    planner_metrics = result.planner_metrics

    if not result.success:
        mission_manager.fail_current_task("Planning failed for mission target.")
        return _mission_fallback(
            fallback_goal_cell,
            fallback_original_path,
            fallback_smoothed_path,
            fallback_waypoints,
            fallback_waypoint_index,
            planner_metrics,
            False,
            False,
            mission_manager.last_error,
            0.0,
            result.planning_time_ms,
        )

    original_path, smoothed_path, waypoints = _apply_replan_result(result)
    return (
        target_cell,
        original_path,
        smoothed_path,
        waypoints,
        _skip_reached_waypoints(robot_state, waypoints, 0),
        planner_metrics,
        True,
        False,
        success_message,
        0.0,
        result.planning_time_ms,
    )


def _draw_replay_frame(
    dashboard: PygameDashboard,
    frame: ReplayFrame | None,
    grid_map: GridMap,
    occupancy_grid: OccupancyGrid,
    replay_player: ReplayPlayer,
    logging_mode: bool,
    log_file_name: str,
    status_message: str,
    profiler_visible: bool,
    profiler_metrics: dict[str, tuple[float, float]],
) -> None:
    if frame is None:
        return

    robot_pose = frame.robot_true_pose or RobotState(MAP_WIDTH / 2, MAP_HEIGHT / 2, 0.0)
    odometry_pose = frame.odometry_pose or robot_pose
    ekf_pose = frame.ekf_pose or robot_pose
    goal_cell = _position_to_cell(frame.goal_position, grid_map.cell_size)

    dashboard.draw(
        robot_state=robot_pose,
        grid_map=grid_map,
        lidar_rays=[],
        occupancy_grid=occupancy_grid,
        goal_cell=goal_cell,
        original_path=[],
        smoothed_path=[],
        status_message=status_message,
        autonomous_mode=frame.autonomous_mode,
        current_target=None,
        replan_count=frame.replan_count,
        last_replan_time_ms=0.0,
        planner_metrics=PlannerMetrics(),
        trajectory=[],
        linear_velocity=0.0,
        angular_velocity=0.0,
        distance_to_goal=frame.distance_to_goal,
        collision_status=frame.collision_status,
        odometry_state=odometry_pose,
        odometry_error=_pose_distance(robot_pose, odometry_pose),
        ekf_state=ekf_pose,
        ekf_error=_pose_distance(robot_pose, ekf_pose),
        ekf_covariance_trace=0.0,
        current_planner_name=frame.current_planner,
        exploration_mode=frame.exploration_mode,
        frontier_cells=[],
        frontier_cluster_count=0,
        current_frontier_target=None,
        logging_mode=logging_mode,
        log_file_name=log_file_name,
        replay_mode=True,
        replay_frame_index=replay_player.frame_index,
        replay_frame_count=replay_player.frame_count,
        replay_file_name=replay_player.file_name,
        profiler_visible=profiler_visible,
        profiler_metrics=profiler_metrics,
        battery_snapshot={
            "percentage": frame.battery_percentage,
            "battery_state": frame.battery_state,
            "charging": frame.charging,
            "energy_consumed": frame.energy_consumed,
        },
    )

def _new_occupancy_grid(grid_map: GridMap) -> OccupancyGrid:
    return OccupancyGrid(
        rows=len(grid_map.grid),
        cols=len(grid_map.grid[0]),
        cell_size=grid_map.cell_size,
    )


def _reset_robot(robot_state: RobotState, scenario: Scenario | None = None) -> None:
    if scenario is None:
        robot_state.x = MAP_WIDTH / 2
        robot_state.y = MAP_HEIGHT / 2
        robot_state.theta = 0.0
        return

    robot_state.x = scenario.robot_start_x
    robot_state.y = scenario.robot_start_y
    robot_state.theta = scenario.robot_start_theta


def _add_trajectory_point(
    trajectory: list[tuple[float, float]],
    robot_state: RobotState,
) -> None:
    last_x, last_y = trajectory[-1]
    dx = robot_state.x - last_x
    dy = robot_state.y - last_y

    if math.sqrt(dx * dx + dy * dy) >= TRAIL_MIN_DISTANCE:
        trajectory.append((robot_state.x, robot_state.y))

    if len(trajectory) > MAX_TRAIL_POINTS:
        del trajectory[0]


def _distance_to_goal(
    robot_state: RobotState,
    goal_cell: tuple[int, int] | None,
    cell_size: int,
) -> float | None:
    if goal_cell is None:
        return None

    goal_row, goal_col = goal_cell
    goal_x = goal_col * cell_size + cell_size / 2
    goal_y = goal_row * cell_size + cell_size / 2
    dx = goal_x - robot_state.x
    dy = goal_y - robot_state.y
    return math.sqrt(dx * dx + dy * dy)



def _position_to_cell(
    position: tuple[float, float] | None,
    cell_size: int,
) -> tuple[int, int] | None:
    if position is None:
        return None

    x, y = position
    return _pixel_to_cell(x, y, cell_size)


def _pose_distance(first: RobotState, second: RobotState) -> float:
    dx = first.x - second.x
    dy = first.y - second.y
    return math.sqrt(dx * dx + dy * dy)

def _charging_station_cell(scenario_name: str, cell_size: int) -> tuple[int, int] | None:
    locations = locations_for_scenario(scenario_name)
    for name in ("charging station", "charger", "charging dock"):
        location = locations.get(name)
        if location is not None:
            return location.cell
    return None



def _goal_cell_to_position(
    goal_cell: tuple[int, int] | None,
    cell_size: int,
) -> tuple[float, float] | None:
    if goal_cell is None:
        return None

    row, col = goal_cell
    return (col * cell_size + cell_size / 2, row * cell_size + cell_size / 2)


def _navigation_snapshot(
    mission_snapshot: dict[str, object],
    goal_manager: GoalManager,
) -> dict[str, object]:
    snapshot = dict(mission_snapshot)
    snapshot.update(goal_manager.snapshot())
    return snapshot


def _apply_replan_result(
    result: ReplanResult,
) -> tuple[list[tuple[int, int]], list[tuple[int, int]], list[tuple[float, float]]]:
    return result.original_path, result.smoothed_path, result.waypoints



def _control_mode(autonomous_mode: bool, exploration_mode: bool, stopped_timer: float, status_message: str = "") -> str:
    if stopped_timer > 0.0:
        return "STOPPED"
    if status_message == "MANUAL OVERRIDE":
        return "MANUAL OVERRIDE"
    if exploration_mode:
        return "EXPLORATION"
    if autonomous_mode:
        return "AUTONOMOUS"
    return "MANUAL"


def _manual_input_active(v: float, omega: float) -> bool:
    return has_manual_input(manual_command(v > 0.0, v < 0.0, omega < 0.0, omega > 0.0, abs(v), abs(omega)))


def _manual_control() -> tuple[float, float]:
    keys = pygame.key.get_pressed()
    v = 0.0
    omega = 0.0

    command = manual_command(
        forward=keys[pygame.K_w] or keys[pygame.K_UP],
        backward=keys[pygame.K_s] or keys[pygame.K_DOWN],
        rotate_left=keys[pygame.K_a] or keys[pygame.K_LEFT],
        rotate_right=keys[pygame.K_d] or keys[pygame.K_RIGHT],
        linear_speed=LINEAR_SPEED,
        angular_speed=ANGULAR_SPEED,
    )

    return command.v, command.omega


def _follow_path(
    robot_state: RobotState,
    waypoints: list[tuple[float, float]],
    current_waypoint_index: int,
    autonomous_mode: bool,
    status_message: str,
) -> tuple[float, float, int, bool, str]:
    current_waypoint_index = _skip_reached_waypoints(
        robot_state,
        waypoints,
        current_waypoint_index,
    )

    if current_waypoint_index >= len(waypoints):
        if autonomous_mode:
            print("Goal reached.")
        return 0.0, 0.0, current_waypoint_index, False, GOAL_REACHED_STATUS

    target_x, target_y = waypoints[current_waypoint_index]
    dx = target_x - robot_state.x
    dy = target_y - robot_state.y
    distance_error = math.sqrt(dx * dx + dy * dy)

    desired_theta = math.atan2(dy, dx)
    theta_error = math.atan2(
        math.sin(desired_theta - robot_state.theta),
        math.cos(desired_theta - robot_state.theta),
    )

    v = K_V * distance_error * max(0, math.cos(theta_error))
    omega = K_OMEGA * theta_error

    v = max(0, min(v, MAX_LINEAR_SPEED))
    omega = max(-MAX_ANGULAR_SPEED, min(omega, MAX_ANGULAR_SPEED))

    return v, omega, current_waypoint_index, autonomous_mode, status_message


def _skip_reached_waypoints(
    robot_state: RobotState,
    waypoints: list[tuple[float, float]],
    current_waypoint_index: int,
) -> int:
    while current_waypoint_index < len(waypoints):
        target_x, target_y = waypoints[current_waypoint_index]
        dx = target_x - robot_state.x
        dy = target_y - robot_state.y
        distance = math.sqrt(dx * dx + dy * dy)

        if distance > WAYPOINT_TOLERANCE:
            break

        current_waypoint_index += 1

    return current_waypoint_index


def _reached_scenario_goal(
    robot_state: RobotState,
    goal_cell: tuple[int, int] | None,
    scenario_goal_cell: tuple[int, int],
    cell_size: int,
) -> bool:
    if goal_cell != scenario_goal_cell:
        return False
    distance = _distance_to_goal(robot_state, goal_cell, cell_size)
    return distance is not None and distance <= WAYPOINT_TOLERANCE


def _current_target_waypoint(
    waypoints: list[tuple[float, float]],
    current_waypoint_index: int,
    autonomous_mode: bool,
) -> tuple[float, float] | None:
    if not autonomous_mode:
        return None
    if current_waypoint_index >= len(waypoints):
        return None
    return waypoints[current_waypoint_index]


def _mouse_on_auto_badge(x: float, y: float) -> bool:
    return WINDOW_WIDTH - 430 <= x <= WINDOW_WIDTH - 350 and 17 <= y <= 43


def _mouse_on_ground_truth_map(x: float, y: float) -> bool:
    return (
        GROUND_TRUTH_MAP_X <= x < GROUND_TRUTH_MAP_X + MAP_WIDTH
        and GROUND_TRUTH_MAP_Y <= y < GROUND_TRUTH_MAP_Y + MAP_HEIGHT
    )


def _pixel_to_cell(x: float, y: float, cell_size: int) -> tuple[int, int]:
    col = int(x // cell_size)
    row = int(y // cell_size)
    return row, col


def _plan_to_best_frontier(
    frontier_clusters: list[FrontierCluster],
    robot_state: RobotState,
    grid_map: GridMap,
    replanner: Replanner,
    profiler: Profiler,
) -> tuple[ReplanResult, FrontierCluster | None]:
    planning_grid = grid_map.get_planning_grid()
    last_result = ReplanResult(
        success=False,
        original_path=[],
        smoothed_path=[],
        waypoints=[],
        planning_time_ms=0.0,
        planner_metrics=PlannerMetrics(),
        goal_cell=None,
    )

    for frontier in sorted(frontier_clusters, key=lambda cluster: cluster.score, reverse=True):
        result = _profiled_replan(profiler, replanner, robot_state, frontier.centroid_cell, planning_grid)
        last_result = result
        if result.success:
            return result, frontier

    return last_result, None






def _profiled_replan(
    profiler: Profiler,
    replanner: Replanner,
    robot_state: RobotState,
    goal_cell: tuple[int, int],
    planning_grid: list[list[int]],
) -> ReplanResult:
    profiler.start_section("planner")
    result = replanner.replan(robot_state, goal_cell, planning_grid)
    profiler.end_section("planner")
    return result


def _profiler_metrics(profiler: Profiler) -> dict[str, tuple[float, float]]:
    names = ["frame", "physics", "lidar", "mapping", "planner", "render"]
    return {
        name: (profiler.get_latest(name), profiler.get_average(name))
        for name in names
    }












