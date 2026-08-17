from __future__ import annotations

from dataclasses import dataclass

from environment.grid_map import ROBOT_RADIUS, FREE_SPACE
from environment.scenario import cell_center
from planning.astar import AStarPlanner

from editor.editor_state import CustomMap


@dataclass
class ValidationResult:
    valid: bool
    messages: list[str]
    path: list[tuple[int, int]]


class MapValidator:
    def validate(self, custom_map: CustomMap) -> ValidationResult:
        messages: list[str] = []
        grid = custom_map.to_grid()

        if custom_map.start is None:
            messages.append("AMR Start is missing.")
        if custom_map.goal is None:
            messages.append("Goal is missing.")

        if custom_map.start is not None:
            self._validate_cell(custom_map, custom_map.start, "AMR Start", messages)
        if custom_map.goal is not None:
            self._validate_cell(custom_map, custom_map.goal, "Goal", messages)

        for name, cell in custom_map.semantic_locations.items():
            self._validate_cell(custom_map, cell, f"Semantic Location '{name.title()}'", messages)

        if messages:
            return ValidationResult(False, messages, [])

        clearance_grid = self._clearance_grid(custom_map)
        start = custom_map.start
        goal = custom_map.goal
        assert start is not None and goal is not None

        if clearance_grid[start[0]][start[1]] != FREE_SPACE:
            return ValidationResult(False, ["Corridor near AMR Start is too narrow for the AMR."], [])
        if clearance_grid[goal[0]][goal[1]] != FREE_SPACE:
            return ValidationResult(False, ["Corridor near Goal is too narrow for the AMR."], [])

        planner = AStarPlanner(clearance_grid, cell_size=custom_map.resolution)
        path = planner.plan(start, goal)
        if not path:
            return ValidationResult(False, ["No valid route exists between START and GOAL."], [])

        return ValidationResult(True, ["MAP VALID"], path)

    def _validate_cell(
        self,
        custom_map: CustomMap,
        cell: tuple[int, int],
        label: str,
        messages: list[str],
    ) -> None:
        if not custom_map.in_bounds(cell):
            messages.append(f"{label} is outside the map boundaries.")
            return
        if custom_map.is_blocked(cell):
            messages.append(f"{label} is inside an obstacle.")

    def _clearance_grid(self, custom_map: CustomMap) -> list[list[int]]:
        grid = custom_map.to_grid()
        clearance_grid = [row.copy() for row in grid]
        radius = max(1, int((ROBOT_RADIUS + custom_map.resolution - 1) // custom_map.resolution))
        for row in range(custom_map.rows):
            for col in range(custom_map.cols):
                if grid[row][col] != FREE_SPACE:
                    continue
                for check_row in range(row - radius, row + radius + 1):
                    for check_col in range(col - radius, col + radius + 1):
                        if check_row < 0 or check_row >= custom_map.rows or check_col < 0 or check_col >= custom_map.cols:
                            clearance_grid[row][col] = 1
                        elif grid[check_row][check_col] != FREE_SPACE:
                            clearance_grid[row][col] = 1
        return clearance_grid
