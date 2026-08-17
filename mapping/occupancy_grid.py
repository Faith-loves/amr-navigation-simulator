from sensors.lidar import LidarRay


UNKNOWN = -1
FREE = 0
OCCUPIED = 1


class OccupancyGrid:
    def __init__(self, rows: int, cols: int, cell_size: int) -> None:
        self.rows = rows
        self.cols = cols
        self.cell_size = cell_size
        self.grid = [[UNKNOWN for _ in range(cols)] for _ in range(rows)]

    def update_from_lidar(self, lidar_rays: list[LidarRay]) -> None:
        for ray in lidar_rays:
            start_cell = self._point_to_cell(ray.start)
            end_cell = self._point_to_cell(ray.end)
            cells = self._bresenham_line(start_cell, end_cell)

            if ray.hit:
                free_cells = cells[:-1]
                occupied_cell = cells[-1]
            else:
                free_cells = cells
                occupied_cell = None

            for row, col in free_cells:
                self._set_cell(row, col, FREE)

            if occupied_cell is not None:
                row, col = occupied_cell
                self._set_cell(row, col, OCCUPIED)

    def _point_to_cell(self, point: tuple[float, float]) -> tuple[int, int]:
        x, y = point
        col = int(x // self.cell_size)
        row = int(y // self.cell_size)
        return row, col

    def _set_cell(self, row: int, col: int, value: int) -> None:
        if 0 <= row < self.rows and 0 <= col < self.cols:
            self.grid[row][col] = value

    def _bresenham_line(
        self,
        start_cell: tuple[int, int],
        end_cell: tuple[int, int],
    ) -> list[tuple[int, int]]:
        start_row, start_col = start_cell
        end_row, end_col = end_cell

        cells = []
        row = start_row
        col = start_col

        row_step = 1 if end_row > start_row else -1
        col_step = 1 if end_col > start_col else -1

        row_distance = abs(end_row - start_row)
        col_distance = abs(end_col - start_col)

        cells.append((row, col))

        if col_distance > row_distance:
            error = col_distance / 2
            while col != end_col:
                col += col_step
                error -= row_distance
                if error < 0:
                    row += row_step
                    error += col_distance
                cells.append((row, col))
        else:
            error = row_distance / 2
            while row != end_row:
                row += row_step
                error -= col_distance
                if error < 0:
                    col += col_step
                    error += row_distance
                cells.append((row, col))

        return cells
