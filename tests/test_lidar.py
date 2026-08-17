import pytest

from robot.state import RobotState
from sensors.lidar import Lidar


class SimpleWallMap:
    cell_size = 10

    def is_wall(self, row: int, col: int) -> bool:
        return row == 0 and col == 10


def test_center_lidar_ray_detects_wall_about_100_pixels_ahead() -> None:
    lidar = Lidar()
    lidar.noise_std = 0
    robot_state = RobotState(x=0, y=5, theta=0)

    rays = lidar.scan(robot_state, SimpleWallMap())
    center_ray = rays[lidar.num_rays // 2]

    assert center_ray.hit is True
    assert center_ray.true_distance == pytest.approx(100, abs=lidar.step_size)
