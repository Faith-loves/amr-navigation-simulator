from planning.astar import AStarPlanner


def test_astar_returns_path_on_empty_grid() -> None:
    grid = [[0 for _ in range(5)] for _ in range(5)]
    planner = AStarPlanner(grid)

    path = planner.plan((0, 0), (4, 4))

    assert path[0] == (0, 0)
    assert path[-1] == (4, 4)
    assert len(path) > 1


def test_astar_routes_around_wall_with_gap() -> None:
    grid = [[0 for _ in range(5)] for _ in range(5)]
    for row in [0, 1, 3, 4]:
        grid[row][2] = 1
    planner = AStarPlanner(grid)

    path = planner.plan((2, 0), (2, 4))

    assert path[0] == (2, 0)
    assert path[-1] == (2, 4)
    assert (2, 2) in path
    assert all(grid[row][col] == 0 for row, col in path)


def test_astar_returns_no_path_when_goal_is_blocked() -> None:
    grid = [[0 for _ in range(5)] for _ in range(5)]
    for row in range(1, 4):
        for col in range(1, 4):
            if (row, col) != (2, 2):
                grid[row][col] = 1
    planner = AStarPlanner(grid)

    path = planner.plan((0, 0), (2, 2))

    assert path == []
