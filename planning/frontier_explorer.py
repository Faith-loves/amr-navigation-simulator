from collections import deque
from dataclasses import dataclass

from mapping.occupancy_grid import FREE, UNKNOWN, OccupancyGrid


@dataclass
class FrontierCluster:
    cells: list[tuple[int, int]]
    centroid_cell: tuple[int, int]
    distance_to_robot: float
    size: int
    score: float


class FrontierExplorer:
    def find_frontier_cells(self, occupancy_grid: OccupancyGrid) -> list[tuple[int, int]]:
        frontier_cells = []

        for row in range(occupancy_grid.rows):
            for col in range(occupancy_grid.cols):
                if occupancy_grid.grid[row][col] != FREE:
                    continue

                if self._has_unknown_neighbor(occupancy_grid, row, col):
                    frontier_cells.append((row, col))

        return frontier_cells

    def find_frontier_clusters(
        self,
        occupancy_grid: OccupancyGrid,
        robot_cell: tuple[int, int],
    ) -> list[FrontierCluster]:
        frontier_cells = set(self.find_frontier_cells(occupancy_grid))
        visited: set[tuple[int, int]] = set()
        clusters = []

        for cell in frontier_cells:
            if cell in visited:
                continue

            cluster_cells = self._grow_cluster(cell, frontier_cells, visited)
            cluster = self._build_cluster(cluster_cells, robot_cell)
            clusters.append(cluster)

        return clusters

    def choose_best_frontier(
        self,
        occupancy_grid: OccupancyGrid,
        robot_cell: tuple[int, int],
    ) -> FrontierCluster | None:
        clusters = self.find_frontier_clusters(occupancy_grid, robot_cell)

        if not clusters:
            return None

        return max(clusters, key=lambda cluster: cluster.score)

    def _grow_cluster(
        self,
        start_cell: tuple[int, int],
        frontier_cells: set[tuple[int, int]],
        visited: set[tuple[int, int]],
    ) -> list[tuple[int, int]]:
        queue = deque([start_cell])
        visited.add(start_cell)
        cluster_cells = []

        while queue:
            cell = queue.popleft()
            cluster_cells.append(cell)

            for neighbor in self._neighbors(cell):
                if neighbor in frontier_cells and neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)

        return cluster_cells

    def _build_cluster(
        self,
        cells: list[tuple[int, int]],
        robot_cell: tuple[int, int],
    ) -> FrontierCluster:
        row_sum = sum(row for row, _ in cells)
        col_sum = sum(col for _, col in cells)
        centroid_row = round(row_sum / len(cells))
        centroid_col = round(col_sum / len(cells))
        centroid_cell = (centroid_row, centroid_col)

        robot_row, robot_col = robot_cell
        row_distance = centroid_row - robot_row
        col_distance = centroid_col - robot_col
        distance_to_robot = (row_distance * row_distance + col_distance * col_distance) ** 0.5
        size = len(cells)
        score = size - 0.05 * distance_to_robot

        return FrontierCluster(
            cells=cells,
            centroid_cell=centroid_cell,
            distance_to_robot=distance_to_robot,
            size=size,
            score=score,
        )

    def _has_unknown_neighbor(self, occupancy_grid: OccupancyGrid, row: int, col: int) -> bool:
        for neighbor_row, neighbor_col in self._neighbors((row, col)):
            if not self._in_bounds(occupancy_grid, neighbor_row, neighbor_col):
                continue
            if occupancy_grid.grid[neighbor_row][neighbor_col] == UNKNOWN:
                return True
        return False

    def _neighbors(self, cell: tuple[int, int]) -> list[tuple[int, int]]:
        row, col = cell
        return [
            (row - 1, col),
            (row + 1, col),
            (row, col - 1),
            (row, col + 1),
            (row - 1, col - 1),
            (row - 1, col + 1),
            (row + 1, col - 1),
            (row + 1, col + 1),
        ]

    def _in_bounds(self, occupancy_grid: OccupancyGrid, row: int, col: int) -> bool:
        return 0 <= row < occupancy_grid.rows and 0 <= col < occupancy_grid.cols
