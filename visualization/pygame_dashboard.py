import math

import pygame

from environment.scenario_manager import ScenarioSummary
from environment.grid_map import GridMap, ROBOT_RADIUS, WALL
from mapping.occupancy_grid import FREE, OCCUPIED, OccupancyGrid
from planning.astar import PlannerMetrics
from robot.state import RobotState
from sensors.lidar import LidarRay
from ui.components import draw_badge, draw_card, draw_keycap, draw_metric_card, draw_progress_bar, draw_tabs, draw_text_input
from ui.theme import Theme, load_fonts
from visualization.lidar_view import LIDAR_VIEW_MINIMAL, LIDAR_VIEW_NAMES, visible_lidar_rays
from visualization.robot_renderer import RobotRenderer


WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 720
TOP_BAR_HEIGHT = 60
PADDING = 12
GAP = 12

MAP_WIDTH = 400
MAP_HEIGHT = 600
METRICS_WIDTH = 252
GRID_SPACING = 40

LEFT_PANEL = pygame.Rect(PADDING, TOP_BAR_HEIGHT + PADDING, 480, WINDOW_HEIGHT - TOP_BAR_HEIGHT - PADDING * 2)
BELIEF_PANEL = pygame.Rect(LEFT_PANEL.right + GAP, TOP_BAR_HEIGHT + PADDING, 420, LEFT_PANEL.height)
METRICS_PANEL = pygame.Rect(BELIEF_PANEL.right + GAP, TOP_BAR_HEIGHT + PADDING, METRICS_WIDTH, LEFT_PANEL.height)

GROUND_TRUTH_MAP_X = LEFT_PANEL.x + (LEFT_PANEL.width - MAP_WIDTH) // 2
GROUND_TRUTH_MAP_Y = LEFT_PANEL.y + 24
BELIEF_MAP_X = BELIEF_PANEL.x + (BELIEF_PANEL.width - MAP_WIDTH) // 2
BELIEF_MAP_Y = BELIEF_PANEL.y + 24


class PygameDashboard:
    def __init__(self) -> None:
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("AMR Navigation Simulator")
        self.clock = pygame.time.Clock()
        fonts = load_fonts()
        self.font = fonts.body
        self.small_font = fonts.small
        self.title_font = fonts.section
        self.brand_font = fonts.app_title

        self.background_color = Theme.BACKGROUND
        self.top_bar_color = Theme.SURFACE
        self.panel_color = Theme.SURFACE
        self.panel_inner_color = Theme.CARD
        self.panel_border_color = Theme.BORDER
        self.grid_color = Theme.GRID
        self.wall_color = Theme.OBSTACLE
        self.dynamic_obstacle_color = Theme.WARNING
        self.lidar_color = Theme.ACCENT
        self.lidar_hit_color = Theme.WARNING
        self.robot_color = Theme.PRIMARY
        self.odometry_color = (209, 120, 255)
        self.ekf_color = Theme.ACCENT
        self.heading_color = Theme.TEXT_PRIMARY
        self.unknown_color = Theme.UNKNOWN_MAP
        self.free_color = Theme.FREE_MAP
        self.occupied_color = Theme.DANGER
        self.original_path_color = Theme.TEXT_MUTED
        self.smoothed_path_color = Theme.PRIMARY
        self.target_waypoint_color = Theme.ACCENT
        self.frontier_cell_color = Theme.PRIMARY_HOVER
        self.frontier_target_color = Theme.WARNING
        self.goal_color = Theme.DANGER
        self.trail_color = (94, 135, 210)
        self.text_color = Theme.TEXT_PRIMARY
        self.subtle_text_color = Theme.TEXT_SECONDARY
        self.badge_on_color = Theme.ACCENT
        self.badge_off_color = Theme.SURFACE_ALT
        self.collision_color = Theme.DANGER
        self.clear_color = Theme.ACCENT
        self.robot_renderer = RobotRenderer()
        self.mission_input_text = ""
        self.mission_input_active = False
        self._last_mission_input_rect = pygame.Rect(METRICS_PANEL.x + 12, METRICS_PANEL.bottom - 70, METRICS_PANEL.width - 24, 24)
        self.active_metrics_tab = "STATUS"
        self.metrics_scroll_offsets = {"STATUS": 0, "METRICS": 0, "CONTROLS": 0, "MISSION": 0}
        self._metrics_tab_rects: dict[str, pygame.Rect] = {}

    def draw(
        self,
        robot_state: RobotState,
        grid_map: GridMap,
        lidar_rays: list[LidarRay],
        occupancy_grid: OccupancyGrid,
        goal_cell: tuple[int, int] | None,
        original_path: list[tuple[int, int]],
        smoothed_path: list[tuple[int, int]],
        status_message: str,
        autonomous_mode: bool,
        current_target: tuple[float, float] | None,
        replan_count: int,
        last_replan_time_ms: float,
        planner_metrics: PlannerMetrics,
        trajectory: list[tuple[float, float]],
        linear_velocity: float,
        angular_velocity: float,
        distance_to_goal: float | None,
        collision_status: bool,
        odometry_state: RobotState,
        odometry_error: float,
        ekf_state: RobotState,
        ekf_error: float,
        ekf_covariance_trace: float,
        current_planner_name: str,
        exploration_mode: bool,
        frontier_cells: list[tuple[int, int]],
        frontier_cluster_count: int,
        current_frontier_target: tuple[int, int] | None,
        logging_mode: bool,
        log_file_name: str,
        replay_mode: bool,
        replay_frame_index: int,
        replay_frame_count: int,
        replay_file_name: str,
        profiler_visible: bool,
        profiler_metrics: dict[str, tuple[float, float]],
        scenario_level: int = 1,
        scenario_count: int = 1,
        scenario_name: str = "",
        scenario_difficulty: str = "",
        mission_label: str = "START -> TARGET",
        start_cell: tuple[int, int] | None = None,
        mission_complete: bool = False,
        all_missions_complete: bool = False,
        mission_summary: ScenarioSummary | None = None,
        all_mission_summaries: list[ScenarioSummary] | None = None,
        mission_snapshot: dict[str, object] | None = None,
        battery_snapshot: dict[str, object] | None = None,
        lidar_view_mode: int = LIDAR_VIEW_MINIMAL,
        control_mode: str = "MANUAL",
    ) -> None:
        self.screen.fill(self.background_color)
        self._draw_top_bar(
            autonomous_mode,
            exploration_mode,
            logging_mode,
            replay_mode,
            scenario_level,
            scenario_count,
            scenario_name,
            scenario_difficulty,
            battery_snapshot,
        )
        self._draw_panel(LEFT_PANEL, "Ground Truth Map")
        self._draw_panel(BELIEF_PANEL, "Robot Belief Map")
        self._draw_panel(METRICS_PANEL, "Dashboard")

        self._draw_ground_truth_panel(
            robot_state,
            odometry_state,
            ekf_state,
            grid_map,
            lidar_rays,
            goal_cell,
            original_path,
            smoothed_path,
            current_target,
            trajectory,
            start_cell,
            mission_snapshot,
            battery_snapshot,
            autonomous_mode,
            exploration_mode,
            collision_status,
            mission_complete,
            lidar_view_mode,
        )
        self._draw_belief_panel(occupancy_grid, frontier_cells, current_frontier_target)
        self._draw_metrics_panel(
            robot_state=robot_state,
            odometry_state=odometry_state,
            ekf_state=ekf_state,
            lidar_rays=lidar_rays,
            original_path=original_path,
            smoothed_path=smoothed_path,
            status_message=status_message,
            autonomous_mode=autonomous_mode,
            current_target=current_target,
            replan_count=replan_count,
            last_replan_time_ms=last_replan_time_ms,
            planner_metrics=planner_metrics,
            linear_velocity=linear_velocity,
            angular_velocity=angular_velocity,
            distance_to_goal=distance_to_goal,
            collision_status=collision_status,
            odometry_error=odometry_error,
            ekf_error=ekf_error,
            ekf_covariance_trace=ekf_covariance_trace,
            current_planner_name=current_planner_name,
            exploration_mode=exploration_mode,
            frontier_cluster_count=frontier_cluster_count,
            current_frontier_target=current_frontier_target,
            logging_mode=logging_mode,
            log_file_name=log_file_name,
            replay_mode=replay_mode,
            replay_frame_index=replay_frame_index,
            replay_frame_count=replay_frame_count,
            replay_file_name=replay_file_name,
            profiler_visible=profiler_visible,
            profiler_metrics=profiler_metrics,
            scenario_level=scenario_level,
            scenario_count=scenario_count,
            scenario_name=scenario_name,
            scenario_difficulty=scenario_difficulty,
            mission_label=mission_label,
            mission_snapshot=mission_snapshot,
            battery_snapshot=battery_snapshot,
            lidar_view_mode=lidar_view_mode,
            control_mode=control_mode,
        )
        if mission_complete:
            self._draw_completion_overlay("MISSION COMPLETE", mission_summary, all_mission_summaries)
        if all_missions_complete:
            self._draw_completion_overlay("ALL MISSIONS COMPLETE", None, all_mission_summaries)
        pygame.display.flip()


    def handle_mission_event(self, event: pygame.event.Event) -> tuple[str | None, bool]:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for tab_name, rect in self._metrics_tab_rects.items():
                if rect.collidepoint(event.pos):
                    self.active_metrics_tab = tab_name
                    self.mission_input_active = False
                    return None, True
            if self.active_metrics_tab == "MISSION":
                self.mission_input_active = self._last_mission_input_rect.collidepoint(event.pos)
                return None, self.mission_input_active
            self.mission_input_active = False
            return None, False

        if event.type == pygame.MOUSEBUTTONDOWN and event.button in {4, 5}:
            if METRICS_PANEL.collidepoint(event.pos):
                delta = -22 if event.button == 4 else 22
                self._scroll_active_tab(delta)
                return None, True

        if event.type == pygame.MOUSEWHEEL:
            if METRICS_PANEL.collidepoint(pygame.mouse.get_pos()):
                self._scroll_active_tab(-event.y * 22)
                return None, True

        if event.type == pygame.KEYDOWN:
            tab_keys = {
                pygame.K_F1: "STATUS",
                pygame.K_F2: "METRICS",
                pygame.K_F3: "CONTROLS",
                pygame.K_F4: "MISSION",
            }
            if event.key in tab_keys:
                self.active_metrics_tab = tab_keys[event.key]
                self.mission_input_active = False
                return None, True

        if event.type != pygame.KEYDOWN or not self.mission_input_active:
            return None, False

        if event.key == pygame.K_ESCAPE:
            self.mission_input_text = ""
            self.mission_input_active = False
            return None, True

        if event.key == pygame.K_RETURN:
            command = self.mission_input_text.strip()
            self.mission_input_active = False
            return command or None, True

        if event.key == pygame.K_BACKSPACE:
            self.mission_input_text = self.mission_input_text[:-1]
            return None, True

        if event.unicode and event.unicode.isprintable() and len(self.mission_input_text) < 80:
            self.mission_input_text += event.unicode
            return None, True

        return None, True

    def _mission_input_rect(self) -> pygame.Rect:
        return self._last_mission_input_rect.copy()

    def tick(self) -> float:
        return self.clock.tick(60) / 1000

    def close(self) -> None:
        pygame.quit()

    def _draw_top_bar(
        self,
        autonomous_mode: bool,
        exploration_mode: bool,
        logging_mode: bool,
        replay_mode: bool,
        scenario_level: int,
        scenario_count: int,
        scenario_name: str,
        scenario_difficulty: str,
        battery_snapshot: dict[str, object] | None = None,
    ) -> None:
        pygame.draw.rect(self.screen, self.top_bar_color, (0, 0, WINDOW_WIDTH, TOP_BAR_HEIGHT))
        pygame.draw.line(self.screen, self.panel_border_color, (0, TOP_BAR_HEIGHT - 1), (WINDOW_WIDTH, TOP_BAR_HEIGHT - 1), 1)
        title = self.brand_font.render("AMR Navigation Simulator", True, self.text_color)
        self.screen.blit(title, (20, 7))
        level_text = f"LEVEL {scenario_level} / {scenario_count}  {scenario_name}"
        if scenario_difficulty:
            level_text += f"  Difficulty: {scenario_difficulty}"
        level_surface = self.small_font.render(level_text, True, self.subtle_text_color)
        self.screen.blit(level_surface, (20, 37))

        battery = battery_snapshot or {}
        battery_percentage = battery.get("percentage")
        battery_label = "BAT --" if battery_percentage is None else f"BAT {float(battery_percentage):.0f}%"
        badges = [
            (control_mode_label(autonomous_mode, exploration_mode), "primary"),
            (battery_label, "success" if battery_percentage is None or float(battery_percentage) > 25 else "warning"),
            ("LOG" if logging_mode else "LOG OFF", "success" if logging_mode else "neutral"),
            ("REPLAY" if replay_mode else "LIVE", "warning" if replay_mode else "neutral"),
        ]
        x = WINDOW_WIDTH - 450
        for label, tone in badges:
            surface = self.small_font.render(label, True, self.text_color)
            rect = pygame.Rect(x, 17, max(62, surface.get_width() + 18), 26)
            draw_badge(self.screen, rect, label, self.small_font, tone=tone)
            x = rect.right + 8

    def _draw_badge(self, label: str, enabled: bool, x: int, y: int) -> int:
        color = self.badge_on_color if enabled else self.badge_off_color
        text = f"{label}: {'ON' if enabled else 'OFF'}"
        surface = self.small_font.render(text, True, self.text_color)
        rect = pygame.Rect(x, y, surface.get_width() + 18, 26)
        pygame.draw.rect(self.screen, color, rect, border_radius=6)
        self.screen.blit(surface, (rect.x + 9, rect.y + 7))
        return rect.right + 8

    def _draw_panel(self, rect: pygame.Rect, title: str) -> None:
        draw_card(self.screen, rect)
        title_surface = self.font.render(title.upper(), True, self.text_color)
        self.screen.blit(title_surface, (rect.x + 14, rect.y + 8))

    def _draw_map_background(self, x: int, y: int) -> None:
        pygame.draw.rect(self.screen, self.panel_inner_color, (x, y, MAP_WIDTH, MAP_HEIGHT), border_radius=8)
        pygame.draw.rect(self.screen, self.panel_border_color, (x, y, MAP_WIDTH, MAP_HEIGHT), 1, border_radius=8)

    def _draw_ground_truth_panel(
        self,
        robot_state: RobotState,
        odometry_state: RobotState,
        ekf_state: RobotState,
        grid_map: GridMap,
        lidar_rays: list[LidarRay],
        goal_cell: tuple[int, int] | None,
        original_path: list[tuple[int, int]],
        smoothed_path: list[tuple[int, int]],
        current_target: tuple[float, float] | None,
        trajectory: list[tuple[float, float]],
        start_cell: tuple[int, int] | None,
        mission_snapshot: dict[str, object] | None,
        battery_snapshot: dict[str, object] | None,
        autonomous_mode: bool,
        exploration_mode: bool,
        collision_status: bool,
        mission_complete: bool,
        lidar_view_mode: int,
    ) -> None:
        x_offset = GROUND_TRUTH_MAP_X
        y_offset = GROUND_TRUTH_MAP_Y
        self._draw_map_background(x_offset, y_offset)
        self._draw_grid(x_offset, y_offset)
        self._draw_walls(grid_map, x_offset, y_offset)
        self._draw_dynamic_obstacles(grid_map, x_offset, y_offset)
        self._draw_trajectory(trajectory, x_offset, y_offset)
        self._draw_lidar(lidar_rays, x_offset, y_offset, lidar_view_mode)
        self._draw_original_path(original_path, grid_map.cell_size, x_offset, y_offset)
        self._draw_smoothed_path(smoothed_path, grid_map.cell_size, x_offset, y_offset)
        self._draw_current_target(current_target, x_offset, y_offset)
        self._draw_start(start_cell, grid_map.cell_size, x_offset, y_offset)
        self._draw_goal(goal_cell, grid_map.cell_size, x_offset, y_offset)
        self._draw_mission_destination(mission_snapshot, grid_map.cell_size, x_offset, y_offset)
        self._draw_charger_marker(battery_snapshot, grid_map.cell_size, x_offset, y_offset)
        self._draw_odometry(odometry_state, x_offset, y_offset)
        self._draw_ekf(ekf_state, x_offset, y_offset)
        self._draw_robot(
            robot_state,
            x_offset,
            y_offset,
            autonomous_mode,
            exploration_mode,
            collision_status,
            mission_complete,
        )

    def _draw_belief_panel(
        self,
        occupancy_grid: OccupancyGrid,
        frontier_cells: list[tuple[int, int]],
        current_frontier_target: tuple[int, int] | None,
    ) -> None:
        x_offset = BELIEF_MAP_X
        y_offset = BELIEF_MAP_Y
        self._draw_map_background(x_offset, y_offset)
        for row, cells in enumerate(occupancy_grid.grid):
            for col, cell in enumerate(cells):
                rectangle = pygame.Rect(
                    x_offset + col * occupancy_grid.cell_size,
                    y_offset + row * occupancy_grid.cell_size,
                    occupancy_grid.cell_size,
                    occupancy_grid.cell_size,
                )
                pygame.draw.rect(self.screen, self._belief_cell_color(cell), rectangle)

        self._draw_frontier_cells(frontier_cells, occupancy_grid.cell_size, x_offset, y_offset)
        self._draw_frontier_target(current_frontier_target, occupancy_grid.cell_size, x_offset, y_offset)
        self._draw_grid(x_offset, y_offset)

    def _draw_metrics_panel(
        self,
        robot_state: RobotState,
        odometry_state: RobotState,
        ekf_state: RobotState,
        lidar_rays: list[LidarRay],
        original_path: list[tuple[int, int]],
        smoothed_path: list[tuple[int, int]],
        status_message: str,
        autonomous_mode: bool,
        current_target: tuple[float, float] | None,
        replan_count: int,
        last_replan_time_ms: float,
        planner_metrics: PlannerMetrics,
        linear_velocity: float,
        angular_velocity: float,
        distance_to_goal: float | None,
        collision_status: bool,
        odometry_error: float,
        ekf_error: float,
        ekf_covariance_trace: float,
        current_planner_name: str,
        exploration_mode: bool,
        frontier_cluster_count: int,
        current_frontier_target: tuple[int, int] | None,
        logging_mode: bool,
        log_file_name: str,
        replay_mode: bool,
        replay_frame_index: int,
        replay_frame_count: int,
        replay_file_name: str,
        profiler_visible: bool,
        profiler_metrics: dict[str, tuple[float, float]],
        scenario_level: int,
        scenario_count: int,
        scenario_name: str,
        scenario_difficulty: str,
        mission_label: str,
        mission_snapshot: dict[str, object] | None,
        battery_snapshot: dict[str, object] | None,
        lidar_view_mode: int,
        control_mode: str,
    ) -> None:
        self._last_mission_input_rect = pygame.Rect(0, 0, 0, 0)
        self._draw_dashboard_tabs()
        content_rect = pygame.Rect(METRICS_PANEL.x + 12, METRICS_PANEL.y + 74, METRICS_PANEL.width - 24, METRICS_PANEL.height - 106)
        footer_y = METRICS_PANEL.bottom - 24
        hint = self.small_font.render("F1 Status   F2 Metrics   F3 Controls   F4 Mission", True, self.subtle_text_color)
        self.screen.blit(hint, (METRICS_PANEL.x + 12, footer_y))

        goal_text = "--" if distance_to_goal is None else f"{distance_to_goal:.0f}px"
        lidar_view_text = LIDAR_VIEW_NAMES.get(lidar_view_mode, "Minimal")
        battery = battery_snapshot or {}
        battery_percentage = battery.get("percentage")
        battery_text = "--" if battery_percentage is None else f"{float(battery_percentage):.0f}%"
        battery_state = str(battery.get("battery_state", "NORMAL") or "NORMAL").replace("_", " ")
        energy_used = float(battery.get("energy_consumed", 0.0) or 0.0)
        snapshot = mission_snapshot or {}
        navigation_target = str(snapshot.get("navigation_target", "Scenario Objective"))
        target_type = str(snapshot.get("target_type", "Scenario"))
        mission_status = str(snapshot.get("mission_status", "IDLE"))
        replay_text = "--" if not replay_mode or replay_frame_count <= 0 else f"{replay_frame_index + 1}/{replay_frame_count}"
        profiler_rows = self._profiler_rows(profiler_metrics)
        profiler_lookup = {label: value for label, value, _color in profiler_rows}

        previous_clip = self.screen.get_clip()
        self.screen.set_clip(content_rect)
        if self.active_metrics_tab == "STATUS":
            rows = [
                ("Control", control_mode),
                ("Scenario", self._shorten(scenario_name, 18)),
                ("Planner", current_planner_name),
                ("Nav Target", self._shorten(navigation_target, 18)),
                ("Target Type", target_type),
                ("Battery", f"{battery_text} {battery_state}"),
                ("Mission", mission_status),
                ("LiDAR", lidar_view_text),
                ("Goal Dist", goal_text),
                ("Collision", "BLOCKED" if collision_status else "CLEAR"),
            ]
            self._draw_tab_rows(content_rect, rows, status_message=status_message)
        elif self.active_metrics_tab == "METRICS":
            rows = [
                ("FPS", f"{self.clock.get_fps():.1f}"),
                ("Planning", f"{planner_metrics.planning_time_ms:.1f} ms"),
                ("Nodes", str(planner_metrics.nodes_expanded)),
                ("Path", f"{planner_metrics.path_length_pixels:.0f} px"),
                ("Replans", str(replan_count)),
                ("LiDAR Time", profiler_lookup.get("LiDAR", "--")),
                ("Mapping", profiler_lookup.get("Mapping", "--")),
                ("Render", profiler_lookup.get("Render", "--")),
                ("Odom Err", f"{odometry_error:.1f} px"),
                ("EKF Err", f"{ekf_error:.1f} px"),
                ("Cov Trace", f"{ekf_covariance_trace:.2f}"),
                ("Energy", f"{energy_used:.2f}"),
                ("Collision", "1" if collision_status else "0"),
                ("Linear v", f"{linear_velocity:.0f}"),
                ("Angular w", f"{angular_velocity:.2f}"),
                ("Waypoints", f"{len(original_path)} -> {len(smoothed_path)}"),
                ("Frontiers", str(frontier_cluster_count)),
                ("Replay", replay_text),
            ]
            if logging_mode:
                rows.append(("Log", self._shorten(log_file_name, 18)))
            if replay_mode:
                rows.append(("Replay File", self._shorten(replay_file_name, 18)))
            self._draw_tab_rows(content_rect, rows)
        elif self.active_metrics_tab == "CONTROLS":
            self._draw_controls_tab(content_rect)
        else:
            self._draw_mission_tab(content_rect, mission_snapshot)
        self.screen.set_clip(previous_clip)

    def _draw_dashboard_tabs(self) -> None:
        self._metrics_tab_rects = draw_tabs(
            self.screen,
            ["STATUS", "METRICS", "CONTROLS", "MISSION"],
            self.active_metrics_tab,
            (METRICS_PANEL.x + 10, METRICS_PANEL.y + 32),
            METRICS_PANEL.width - 20,
            self.small_font,
            pygame.mouse.get_pos(),
        )

    def _draw_tab_rows(
        self,
        rect: pygame.Rect,
        rows: list[tuple[str, str]],
        status_message: str = "",
    ) -> None:
        y = rect.y - self.metrics_scroll_offsets.get(self.active_metrics_tab, 0)
        bottom = rect.bottom
        for label, value in rows:
            if rect.y - 18 <= y <= bottom:
                self._draw_metric_row(label, value, rect.x, y, self.text_color)
            y += 21
        if status_message:
            y += 8
            if y <= bottom:
                self._draw_wrapped_text(status_message, rect.x, y, rect.width, self.subtle_text_color)

    def _draw_controls_tab(self, rect: pygame.Rect) -> None:
        columns = [
            ("NAVIGATION", [
                ("W / Up", "Forward"),
                ("S / Down", "Backward"),
                ("A / Left", "Rotate Left"),
                ("D / Right", "Rotate Right"),
                ("SPACE", "Emergency Stop"),
            ]),
            ("SIMULATION", [
                ("F", "Auto"),
                ("E", "Explore"),
                ("V", "LiDAR View"),
                ("1", "A*"),
                ("2", "Dijkstra"),
                ("3", "RRT*"),
                ("L", "Logging"),
                ("R", "Restart"),
                ("ESC", "Home"),
                ("K", "Demo Low Battery"),
            ]),
        ]
        col_width = rect.width // 2
        for col_index, (title, rows) in enumerate(columns):
            x = rect.x + col_index * col_width
            y = rect.y
            self.screen.blit(self.font.render(title, True, self.text_color), (x, y))
            y += 28
            for key, label in rows:
                key_rect = pygame.Rect(x, y - 4, 48, 22)
                draw_keycap(self.screen, key_rect, key, self.small_font)
                self.screen.blit(self.small_font.render(label, True, self.subtle_text_color), (x + 58, y))
                y += 26

    def _draw_mission_tab(self, rect: pygame.Rect, mission_snapshot: dict[str, object] | None) -> None:
        y = rect.y - self.metrics_scroll_offsets.get("MISSION", 0)
        if y <= rect.bottom:
            y = self._draw_mission_panel(mission_snapshot, rect.x, y)

    def _scroll_active_tab(self, delta: int) -> None:
        current = self.metrics_scroll_offsets.get(self.active_metrics_tab, 0)
        self.metrics_scroll_offsets[self.active_metrics_tab] = max(0, min(320, current + delta))

    def _draw_mission_panel(
        self,
        mission_snapshot: dict[str, object] | None,
        x: int,
        y: int,
    ) -> int:
        label_text = "MISSION INPUT: ACTIVE" if self.mission_input_active else "MISSION COMMAND"
        title = self.font.render(label_text, True, self.text_color)
        self.screen.blit(title, (x, y))
        y += 22

        input_rect = pygame.Rect(x, y, METRICS_PANEL.width - 24, 24)
        self._last_mission_input_rect = input_rect.copy()
        placeholder = "Go to the kitchen then return to the charging station"
        input_text = self._shorten(self.mission_input_text, 34)
        draw_text_input(self.screen, input_rect, input_text, placeholder, self.small_font, focused=self.mission_input_active)
        y = input_rect.bottom + 8

        hint = self.small_font.render("Press ENTER to execute", True, self.subtle_text_color)
        self.screen.blit(hint, (x, y))
        y += 18

        snapshot = mission_snapshot or {}
        status = str(snapshot.get("mission_status", "IDLE"))
        navigation_target = str(snapshot.get("navigation_target", "Scenario Objective"))
        target_type = str(snapshot.get("target_type", "Scenario"))
        command = str(snapshot.get("raw_command", ""))
        current = str(snapshot.get("current_target", ""))
        intent = str(snapshot.get("intent", "UNKNOWN"))
        confidence = float(snapshot.get("confidence", 0.0))
        rows = [
            ("AI MISSION", ""),
            ("Intent", intent),
            ("Confidence", f"{confidence * 100:.0f}%"),
            ("Status", status),
            ("NAV TARGET", self._shorten(navigation_target, 18)),
            ("TARGET TYPE", target_type),
        ]
        if command:
            rows.append(("Command", self._shorten(command, 18)))
        if current:
            rows.append(("Current", current))

        for label, value in rows:
            color = self.text_color if label == "MISSION" else self.subtle_text_color
            self._draw_metric_row(label, value, x, y, color)
            y += 14

        tasks = snapshot.get("tasks", [])
        if isinstance(tasks, list) and tasks:
            for index, task in enumerate(tasks[:3], start=1):
                if isinstance(task, dict):
                    name = str(task.get("target_name", ""))
                    task_status = str(task.get("status", ""))
                    self._draw_metric_row(f"{index}. {self._shorten(name, 10)}", task_status, x, y, self.text_color)
                    y += 14

        history = snapshot.get("command_history", [])
        if isinstance(history, list) and history:
            self._draw_metric_row("RECENT", "", x, y, self.text_color)
            y += 14
            for index, command in enumerate(history[-5:], start=1):
                self._draw_metric_row(f"{index}.", self._shorten(str(command), 20), x, y, self.subtle_text_color)
                y += 14

        error = str(snapshot.get("last_error", ""))
        if error:
            self._draw_wrapped_text(error, x, y, METRICS_PANEL.width - 24, self.collision_color)
            y += 28

        return y

    def _profiler_rows(
        self,
        profiler_metrics: dict[str, tuple[float, float]],
    ) -> list[tuple[str, str, tuple[int, int, int]]]:
        labels = [
            ("frame", "Frame"),
            ("physics", "Physics"),
            ("lidar", "LiDAR"),
            ("mapping", "Mapping"),
            ("planner", "Planner"),
            ("render", "Render"),
        ]
        rows = []
        for key, label in labels:
            latest, average = profiler_metrics.get(key, (0.0, 0.0))
            rows.append((label, f"{latest:.1f} ({average:.1f})", self.text_color))
        return rows

    def _draw_wrapped_text(self, text: str, x: int, y: int, width: int, color: tuple[int, int, int]) -> None:
        words = text.split()
        line = ""
        for word in words:
            candidate = word if not line else f"{line} {word}"
            if self.small_font.size(candidate)[0] <= width:
                line = candidate
            else:
                self.screen.blit(self.small_font.render(line, True, color), (x, y))
                y += 15
                line = word
        if line:
            self.screen.blit(self.small_font.render(line, True, color), (x, y))

    def _shorten(self, text: str, max_length: int) -> str:
        if len(text) <= max_length:
            return text
        return text[: max_length - 3] + "..."

    def _frontier_target_text(self, target_cell: tuple[int, int] | None) -> str:
        if target_cell is None:
            return "--"
        row, col = target_cell
        return f"{row}, {col}"

    def _draw_metric_row(self, label: str, value: str, x: int, y: int, value_color: tuple[int, int, int]) -> None:
        label_surface = self.small_font.render(label, True, self.subtle_text_color)
        value_surface = self.small_font.render(value, True, value_color)
        self.screen.blit(label_surface, (x, y))
        self.screen.blit(value_surface, (x + 92, y))

    def _belief_cell_color(self, cell: int) -> tuple[int, int, int]:
        if cell == FREE:
            return self.free_color
        if cell == OCCUPIED:
            return self.occupied_color
        return self.unknown_color

    def _draw_grid(self, x_offset: int, y_offset: int) -> None:
        for x in range(0, MAP_WIDTH + 1, GRID_SPACING):
            pygame.draw.line(self.screen, self.grid_color, (x_offset + x, y_offset), (x_offset + x, y_offset + MAP_HEIGHT))
        for y in range(0, MAP_HEIGHT + 1, GRID_SPACING):
            pygame.draw.line(self.screen, self.grid_color, (x_offset, y_offset + y), (x_offset + MAP_WIDTH, y_offset + y))

    def _draw_walls(self, grid_map: GridMap, x_offset: int, y_offset: int) -> None:
        for row, cells in enumerate(grid_map.grid):
            for col, cell in enumerate(cells):
                if cell == WALL:
                    rectangle = pygame.Rect(
                        x_offset + col * grid_map.cell_size,
                        y_offset + row * grid_map.cell_size,
                        grid_map.cell_size,
                        grid_map.cell_size,
                    )
                    pygame.draw.rect(self.screen, self.wall_color, rectangle)

    def _draw_dynamic_obstacles(self, grid_map: GridMap, x_offset: int, y_offset: int) -> None:
        for obstacle in grid_map.dynamic_obstacles:
            rectangle = pygame.Rect(x_offset + int(obstacle.x), y_offset + int(obstacle.y), obstacle.width, obstacle.height)
            pygame.draw.rect(self.screen, self.dynamic_obstacle_color, rectangle, border_radius=3)

    def _draw_trajectory(self, trajectory: list[tuple[float, float]], x_offset: int, y_offset: int) -> None:
        if len(trajectory) < 2:
            return
        points = [(x_offset + int(x), y_offset + int(y)) for x, y in trajectory]
        pygame.draw.lines(self.screen, self.trail_color, False, points, 2)

    def _draw_lidar(self, lidar_rays: list[LidarRay], x_offset: int, y_offset: int, lidar_view_mode: int) -> None:
        visible_rays = visible_lidar_rays(lidar_rays, lidar_view_mode)
        full_mode = lidar_view_mode == 2
        color = self.lidar_color if full_mode else (65, 145, 120)
        max_visible_length = None if full_mode else 80
        for ray in visible_rays:
            start = (x_offset + int(ray.start[0]), y_offset + int(ray.start[1]))
            end_x, end_y = ray.end
            if max_visible_length is not None:
                dx = end_x - ray.start[0]
                dy = end_y - ray.start[1]
                length = math.sqrt(dx * dx + dy * dy)
                if length > max_visible_length and length > 0:
                    scale = max_visible_length / length
                    end_x = ray.start[0] + dx * scale
                    end_y = ray.start[1] + dy * scale
            end = (x_offset + int(end_x), y_offset + int(end_y))
            pygame.draw.line(self.screen, color, start, end, 1)
            if ray.hit and full_mode:
                pygame.draw.circle(self.screen, self.lidar_hit_color, end, 2)
            elif ray.hit:
                pygame.draw.circle(self.screen, self.lidar_hit_color, end, 1)

    def _draw_original_path(self, path: list[tuple[int, int]], cell_size: int, x_offset: int, y_offset: int) -> None:
        for cell in path:
            pygame.draw.circle(self.screen, self.original_path_color, self._cell_center(cell, cell_size, x_offset, y_offset), 2)

    def _draw_smoothed_path(self, path: list[tuple[int, int]], cell_size: int, x_offset: int, y_offset: int) -> None:
        if not path:
            return
        points = [self._cell_center(cell, cell_size, x_offset, y_offset) for cell in path]
        if len(points) > 1:
            pygame.draw.lines(self.screen, self.smoothed_path_color, False, points, 3)
        for point in points:
            pygame.draw.circle(self.screen, self.smoothed_path_color, point, 4)

    def _draw_current_target(self, current_target: tuple[float, float] | None, x_offset: int, y_offset: int) -> None:
        if current_target is None:
            return
        x, y = current_target
        center = (x_offset + int(x), y_offset + int(y))
        pygame.draw.circle(self.screen, self.target_waypoint_color, center, 6)
        pygame.draw.circle(self.screen, self.heading_color, center, 6, 1)

    def _draw_start(self, start_cell: tuple[int, int] | None, cell_size: int, x_offset: int, y_offset: int) -> None:
        if start_cell is None:
            return
        center = self._cell_center(start_cell, cell_size, x_offset, y_offset)
        pygame.draw.circle(self.screen, self.clear_color, center, 10, 1)
        label = self.small_font.render("START", True, self.clear_color)
        self.screen.blit(label, (center[0] - label.get_width() // 2, center[1] + 11))

    def _draw_goal(self, goal_cell: tuple[int, int] | None, cell_size: int, x_offset: int, y_offset: int) -> None:
        if goal_cell is None:
            return
        center = self._cell_center(goal_cell, cell_size, x_offset, y_offset)
        pygame.draw.circle(self.screen, self.goal_color, center, 12, 2)
        pygame.draw.circle(self.screen, self.goal_color, center, 4)
        label = self.small_font.render("GOAL", True, self.goal_color)
        self.screen.blit(label, (center[0] - label.get_width() // 2, center[1] - 27))


    def _draw_charger_marker(
        self,
        battery_snapshot: dict[str, object] | None,
        cell_size: int,
        x_offset: int,
        y_offset: int,
    ) -> None:
        snapshot = battery_snapshot or {}
        cell = snapshot.get("charger_cell")
        if not isinstance(cell, tuple) and not isinstance(cell, list):
            return
        if len(cell) != 2:
            return
        center = self._cell_center((int(cell[0]), int(cell[1])), cell_size, x_offset, y_offset)
        pygame.draw.rect(self.screen, self.lidar_color, pygame.Rect(center[0] - 8, center[1] - 8, 16, 16), 2, border_radius=3)
        label = self.small_font.render("CHARGER", True, self.lidar_color)
        self.screen.blit(label, (center[0] - label.get_width() // 2, center[1] - 25))

    def _draw_mission_destination(
        self,
        mission_snapshot: dict[str, object] | None,
        cell_size: int,
        x_offset: int,
        y_offset: int,
    ) -> None:
        snapshot = mission_snapshot or {}
        active_goal = snapshot.get("active_goal")
        if isinstance(active_goal, (tuple, list)) and len(active_goal) == 2:
            center = self._cell_center((int(active_goal[0]), int(active_goal[1])), cell_size, x_offset, y_offset)
        else:
            position = snapshot.get("current_target_position")
            if not isinstance(position, tuple) and not isinstance(position, list):
                return
            if len(position) != 2:
                return
            x, y = float(position[0]), float(position[1])
            center = (x_offset + int(x), y_offset + int(y))
        pygame.draw.circle(self.screen, self.target_waypoint_color, center, 10, 2)
        pygame.draw.circle(self.screen, self.target_waypoint_color, center, 3)
        label_text = str(snapshot.get("navigation_target") or snapshot.get("current_target", "TARGET")).upper()
        label = self.small_font.render(label_text, True, self.target_waypoint_color)
        self.screen.blit(label, (center[0] - label.get_width() // 2, center[1] + 13))

    def _draw_robot(
        self,
        robot_state: RobotState,
        x_offset: int,
        y_offset: int,
        autonomous_mode: bool,
        exploration_mode: bool,
        collision_status: bool,
        mission_complete: bool,
    ) -> None:
        self.robot_renderer.draw(
            self.screen,
            robot_state,
            x_offset,
            y_offset,
            autonomous_mode,
            exploration_mode,
            collision_status,
            mission_complete,
        )

    def _draw_odometry(self, odometry_state: RobotState, x_offset: int, y_offset: int) -> None:
        self._draw_pose_marker(odometry_state, x_offset, y_offset, self.odometry_color, radius=5, heading_length=12)

    def _draw_ekf(self, ekf_state: RobotState, x_offset: int, y_offset: int) -> None:
        self._draw_pose_marker(ekf_state, x_offset, y_offset, self.ekf_color, radius=8, heading_length=14)

    def _draw_pose_marker(
        self,
        pose: RobotState,
        x_offset: int,
        y_offset: int,
        color: tuple[int, int, int],
        radius: int,
        heading_length: int,
    ) -> None:
        center = (x_offset + int(pose.x), y_offset + int(pose.y))
        pygame.draw.circle(self.screen, color, center, radius, 1)
        heading_end = (
            x_offset + int(pose.x + math.cos(pose.theta) * heading_length),
            y_offset + int(pose.y + math.sin(pose.theta) * heading_length),
        )
        pygame.draw.line(self.screen, color, center, heading_end, 1)

    def _draw_frontier_cells(
        self,
        frontier_cells: list[tuple[int, int]],
        cell_size: int,
        x_offset: int,
        y_offset: int,
    ) -> None:
        for row, col in frontier_cells:
            center = self._cell_center((row, col), cell_size, x_offset, y_offset)
            pygame.draw.circle(self.screen, self.frontier_cell_color, center, 3)

    def _draw_frontier_target(
        self,
        target_cell: tuple[int, int] | None,
        cell_size: int,
        x_offset: int,
        y_offset: int,
    ) -> None:
        if target_cell is None:
            return
        center = self._cell_center(target_cell, cell_size, x_offset, y_offset)
        pygame.draw.circle(self.screen, self.frontier_target_color, center, 7, 2)
        pygame.draw.circle(self.screen, self.heading_color, center, 3)


    def _draw_completion_overlay(
        self,
        title: str,
        mission_summary: ScenarioSummary | None,
        all_mission_summaries: list[ScenarioSummary] | None,
    ) -> None:
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((5, 8, 14, 190))
        self.screen.blit(overlay, (0, 0))

        panel = pygame.Rect(WINDOW_WIDTH // 2 - 210, WINDOW_HEIGHT // 2 - 145, 420, 290)
        draw_card(self.screen, panel)

        title_surface = self.title_font.render(title, True, self.text_color)
        self.screen.blit(title_surface, (panel.centerx - title_surface.get_width() // 2, panel.y + 22))

        y = panel.y + 66
        if title == "ALL MISSIONS COMPLETE":
            summaries = all_mission_summaries or []
            total_time = sum(summary.completion_time for summary in summaries)
            total_path = sum(summary.path_length for summary in summaries)
            total_replans = sum(summary.replans for summary in summaries)
            total_collisions = sum(summary.collisions for summary in summaries)
            rows = [
                ("Levels", f"{len(summaries)}"),
                ("Total time", f"{total_time:.1f}s"),
                ("Total path", f"{total_path:.0f}px"),
                ("Total replans", str(total_replans)),
                ("Total collisions", str(total_collisions)),
                ("R", "restart from Level 1"),
            ]
        elif mission_summary is not None:
            ekf_text = "--" if mission_summary.ekf_error is None else f"{mission_summary.ekf_error:.1f}px"
            rows = [
                ("Level", mission_summary.name),
                ("Planner", mission_summary.planner),
                ("Time", f"{mission_summary.completion_time:.1f}s"),
                ("Path length", f"{mission_summary.path_length:.0f}px"),
                ("Replans", str(mission_summary.replans)),
                ("Collisions", str(mission_summary.collisions)),
                ("EKF error", ekf_text),
                ("Battery end", f"{mission_summary.battery_end:.0f}%"),
                ("Energy used", f"{mission_summary.energy_used:.2f}"),
                ("Charging stops", str(mission_summary.charging_stops)),
            ]
        else:
            rows = []

        for label, value in rows:
            self._draw_metric_row(label, value, panel.x + 38, y, self.text_color)
            y += 22

    def _cell_center(self, cell: tuple[int, int], cell_size: int, x_offset: int, y_offset: int) -> tuple[int, int]:
        row, col = cell
        return (
            x_offset + col * cell_size + cell_size // 2,
            y_offset + row * cell_size + cell_size // 2,
        )


def control_mode_label(autonomous_mode: bool, exploration_mode: bool) -> str:
    if exploration_mode:
        return "EXPLORE"
    if autonomous_mode:
        return "AUTO"
    return "MANUAL"
