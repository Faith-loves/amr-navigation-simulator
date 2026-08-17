class PathSmoother:
    def __init__(self, grid: list[list[int]]) -> None:
        self.set_grid(grid)

    def set_grid(self, grid: list[list[int]]) -> None:
        self.grid = grid
        self.rows = len(grid)
        self.cols = len(grid[0])

    def smooth(self, path: list[tuple[int, int]]) -> list[tuple[int, int]]:
        if len(path) <= 2:
            return path

        smoothed_path = [path[0]]
        current_index = 0

        while current_index < len(path) - 1:
            next_index = len(path) - 1

            while next_index > current_index + 1:
                if self._has_line_of_sight(path[current_index], path[next_index]):
                    break
                next_index -= 1

            smoothed_path.append(path[next_index])
            current_index = next_index

        return smoothed_path

    def _has_line_of_sight(
        self,
        start: tuple[int, int],
        end: tuple[int, int],
    ) -> bool:
        for row, col in self._bresenham_line(start, end):
            if not self._is_free(row, col):
                return False
        return True

    def _is_free(self, row: int, col: int) -> bool:
        if row < 0 or row >= self.rows:
            return False
        if col < 0 or col >= self.cols:
            return False
        return self.grid[row][col] == 0

    def _bresenham_line(
        self,
        start: tuple[int, int],
        end: tuple[int, int],
    ) -> list[tuple[int, int]]:
        start_row, start_col = start
        end_row, end_col = end

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
