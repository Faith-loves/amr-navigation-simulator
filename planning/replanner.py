from collections import deque
from dataclasses import dataclass
from typing import Protocol

from planning.astar import PlannerMetrics
from planning.path_smoother import PathSmoother
from robot.state import RobotState


class GridPlanner(Protocol):
    grid: list[list[int]]
    rows: int
    cols: int
    latest_metrics: PlannerMetrics

    def set_grid(self, grid: list[list[int]]) -> None:
        ...

    def plan(self, start: tuple[int, int], goal: tuple[int, int]) -> list[tuple[int, int]]:
        ...


@dataclass
class ReplanResult:
    success: bool
    original_path: list[tuple[int, int]]
    smoothed_path: list[tuple[int, int]]
    waypoints: list[tuple[float, float]]
    planning_time_ms: float
    planner_metrics: PlannerMetrics
    goal_cell: tuple[int, int] | None = None


class Replanner:
    def __init__(
        self,
        planner: GridPlanner,
        path_smoother: PathSmoother,
        cell_size: int,
    ) -> None:
        self.planner = planner
        self.path_smoother = path_smoother
        self.cell_size = cell_size

    def set_planner(self, planner: GridPlanner) -> None:
        self.planner = planner

    def set_planning_grid(self, grid: list[list[int]]) -> None:
        self.planner.set_grid(grid)
        self.path_smoother.set_grid(grid)

    def replan(
        self,
        robot_state: RobotState,
        goal_cell: tuple[int, int],
        planning_grid: list[list[int]],
    ) -> ReplanResult:
        self.set_planning_grid(planning_grid)
        start_cell = self._pixel_to_cell(robot_state.x, robot_state.y)
        original_path = self.planner.plan(start_cell, goal_cell)
        planner_metrics = self.planner.latest_metrics
        active_goal_cell = goal_cell

        if not original_path:
            reachable_goal_cell = self._nearest_reachable_cell(start_cell, goal_cell)
            if reachable_goal_cell is not None and reachable_goal_cell != goal_cell:
                active_goal_cell = reachable_goal_cell
                original_path = self.planner.plan(start_cell, active_goal_cell)
                planner_metrics = self.planner.latest_metrics

        if original_path:
            smoothed_path = self.path_smoother.smooth(original_path)
            waypoints = self._path_to_waypoints(smoothed_path)
            success = True
        else:
            smoothed_path = []
            waypoints = []
            success = False

        return ReplanResult(
            success=success,
            original_path=original_path,
            smoothed_path=smoothed_path,
            waypoints=waypoints,
            planning_time_ms=planner_metrics.planning_time_ms,
            planner_metrics=planner_metrics,
            goal_cell=active_goal_cell if success else None,
        )

    def path_is_valid(
        self,
        smoothed_path: list[tuple[int, int]],
        planning_grid: list[list[int]],
    ) -> bool:
        self.set_planning_grid(planning_grid)

        if not smoothed_path:
            return False

        for cell in smoothed_path:
            if not self._is_free(cell):
                return False

        for index in range(len(smoothed_path) - 1):
            start = smoothed_path[index]
            end = smoothed_path[index + 1]
            if not self.path_smoother._has_line_of_sight(start, end):
                return False

        return True

    def _nearest_reachable_cell(
        self,
        start_cell: tuple[int, int],
        desired_goal_cell: tuple[int, int],
    ) -> tuple[int, int] | None:
        if not self._is_free(start_cell):
            return None

        queue = deque([start_cell])
        visited = {start_cell}
        best_cell = start_cell
        best_score = self._goal_distance_score(start_cell, desired_goal_cell)

        while queue:
            cell = queue.popleft()
            score = self._goal_distance_score(cell, desired_goal_cell)
            if score < best_score:
                best_cell = cell
                best_score = score

            for neighbor in self._cardinal_neighbors(cell):
                if neighbor in visited or not self._is_free(neighbor):
                    continue
                visited.add(neighbor)
                queue.append(neighbor)

        return best_cell

    def _cardinal_neighbors(self, cell: tuple[int, int]) -> list[tuple[int, int]]:
        row, col = cell
        return [
            (row - 1, col),
            (row + 1, col),
            (row, col - 1),
            (row, col + 1),
        ]

    def _goal_distance_score(
        self,
        cell: tuple[int, int],
        desired_goal_cell: tuple[int, int],
    ) -> int:
        row, col = cell
        goal_row, goal_col = desired_goal_cell
        return (goal_row - row) * (goal_row - row) + (goal_col - col) * (goal_col - col)

    def _pixel_to_cell(self, x: float, y: float) -> tuple[int, int]:
        col = int(x // self.cell_size)
        row = int(y // self.cell_size)
        return row, col

    def _path_to_waypoints(
        self,
        path: list[tuple[int, int]],
    ) -> list[tuple[float, float]]:
        return [
            (col * self.cell_size + self.cell_size / 2, row * self.cell_size + self.cell_size / 2)
            for row, col in path
        ]

    def _is_free(self, cell: tuple[int, int]) -> bool:
        row, col = cell
        if row < 0 or row >= self.planner.rows:
            return False
        if col < 0 or col >= self.planner.cols:
            return False
        return self.planner.grid[row][col] == 0
