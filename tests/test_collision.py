from environment.grid_map import GridMap


def test_robot_collides_inside_static_obstacle_cell() -> None:
    grid_map = GridMap()

    assert grid_map.collides_with_wall(x=90, y=70)


def test_robot_does_not_collide_in_free_cell() -> None:
    grid_map = GridMap()

    assert grid_map.collides_with_wall(x=200, y=300) is False
