import heapq
import math
import time
from dataclasses import dataclass


STRAIGHT_COST = 1
DIAGONAL_COST = 1.414


@dataclass
class PlannerMetrics:
    planning_time_ms: float = 0.0
    nodes_expanded: int = 0
    path_length_pixels: float = 0.0
    raw_waypoints_count: int = 0
    success: bool = False


class AStarPlanner:
    def __init__(self, grid: list[list[int]], cell_size: int = 50) -> None:
        self.cell_size = cell_size
        self.latest_metrics = PlannerMetrics()
        self.set_grid(grid)

    def set_grid(self, grid: list[list[int]]) -> None:
        self.grid = grid
        self.rows = len(grid)
        self.cols = len(grid[0])

    def plan(
        self,
        start: tuple[int, int],
        goal: tuple[int, int],
    ) -> list[tuple[int, int]]:
        start_time = time.perf_counter()
        nodes_expanded = 0

        if not self._is_free(start) or not self._is_free(goal):
            self._update_metrics(start_time, nodes_expanded, [])
            return []

        open_set = []
        heapq.heappush(open_set, (0, start))

        came_from: dict[tuple[int, int], tuple[int, int]] = {}
        g_score = {start: 0.0}

        while open_set:
            current = heapq.heappop(open_set)[1]
            nodes_expanded += 1

            if current == goal:
                path = self._reconstruct_path(came_from, current)
                self._update_metrics(start_time, nodes_expanded, path)
                return path

            for neighbor, move_cost in self._neighbors(current):
                new_g_score = g_score[current] + move_cost

                if neighbor not in g_score or new_g_score < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = new_g_score
                    f_score = new_g_score + self._heuristic(neighbor, goal)
                    heapq.heappush(open_set, (f_score, neighbor))

        self._update_metrics(start_time, nodes_expanded, [])
        return []

    def _update_metrics(
        self,
        start_time: float,
        nodes_expanded: int,
        path: list[tuple[int, int]],
    ) -> None:
        self.latest_metrics = PlannerMetrics(
            planning_time_ms=(time.perf_counter() - start_time) * 1000,
            nodes_expanded=nodes_expanded,
            path_length_pixels=self._path_length_pixels(path),
            raw_waypoints_count=len(path),
            success=bool(path),
        )

    def _path_length_pixels(self, path: list[tuple[int, int]]) -> float:
        if len(path) < 2:
            return 0.0

        total_length = 0.0
        for index in range(len(path) - 1):
            row_a, col_a = path[index]
            row_b, col_b = path[index + 1]
            row_distance = row_b - row_a
            col_distance = col_b - col_a
            total_length += math.sqrt(row_distance * row_distance + col_distance * col_distance)

        return total_length * self.cell_size

    def _neighbors(
        self,
        cell: tuple[int, int],
    ) -> list[tuple[tuple[int, int], float]]:
        row, col = cell
        moves = [
            (-1, 0, STRAIGHT_COST),
            (1, 0, STRAIGHT_COST),
            (0, -1, STRAIGHT_COST),
            (0, 1, STRAIGHT_COST),
            (-1, -1, DIAGONAL_COST),
            (-1, 1, DIAGONAL_COST),
            (1, -1, DIAGONAL_COST),
            (1, 1, DIAGONAL_COST),
        ]

        neighbors = []

        for row_change, col_change, cost in moves:
            neighbor = (row + row_change, col + col_change)
            if self._is_free(neighbor):
                neighbors.append((neighbor, cost))

        return neighbors

    def _is_free(self, cell: tuple[int, int]) -> bool:
        row, col = cell
        if row < 0 or row >= self.rows:
            return False
        if col < 0 or col >= self.cols:
            return False
        return self.grid[row][col] == 0

    def _heuristic(
        self,
        cell: tuple[int, int],
        goal: tuple[int, int],
    ) -> float:
        row, col = cell
        goal_row, goal_col = goal
        return math.sqrt((goal_row - row) ** 2 + (goal_col - col) ** 2)

    def _reconstruct_path(
        self,
        came_from: dict[tuple[int, int], tuple[int, int]],
        current: tuple[int, int],
    ) -> list[tuple[int, int]]:
        path = [current]

        while current in came_from:
            current = came_from[current]
            path.append(current)

        path.reverse()
        return path
