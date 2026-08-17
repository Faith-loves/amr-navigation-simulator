import math
from dataclasses import dataclass

import numpy as np

from environment.grid_map import GridMap
from robot.state import RobotState


@dataclass
class LidarRay:
    start: tuple[float, float]
    end: tuple[float, float]
    true_distance: float
    noisy_distance: float
    hit: bool


class Lidar:
    def __init__(self) -> None:
        self.max_range = 250
        self.num_rays = 41
        self.field_of_view = math.radians(270)
        self.step_size = 4
        self.noise_std = 3.0

    def scan(self, robot_state: RobotState, grid_map: GridMap) -> list[LidarRay]:
        rays = []
        start_angle = robot_state.theta - self.field_of_view / 2
        angle_step = self.field_of_view / (self.num_rays - 1)

        for ray_index in range(self.num_rays):
            ray_angle = start_angle + ray_index * angle_step
            ray = self._cast_ray(robot_state, grid_map, ray_angle)
            rays.append(ray)

        return rays

    def _cast_ray(
        self,
        robot_state: RobotState,
        grid_map: GridMap,
        ray_angle: float,
    ) -> LidarRay:
        start = (robot_state.x, robot_state.y)
        true_distance = 0
        hit = False

        while true_distance < self.max_range:
            true_distance += self.step_size
            test_x = robot_state.x + math.cos(ray_angle) * true_distance
            test_y = robot_state.y + math.sin(ray_angle) * true_distance

            col = int(test_x // grid_map.cell_size)
            row = int(test_y // grid_map.cell_size)

            if grid_map.is_wall(row, col):
                hit = True
                break

        if true_distance > self.max_range:
            true_distance = self.max_range

        noisy_distance = true_distance + np.random.normal(0, self.noise_std)
        noisy_distance = max(0, min(noisy_distance, self.max_range))

        end_x = robot_state.x + math.cos(ray_angle) * noisy_distance
        end_y = robot_state.y + math.sin(ray_angle) * noisy_distance

        return LidarRay(
            start=start,
            end=(end_x, end_y),
            true_distance=true_distance,
            noisy_distance=noisy_distance,
            hit=hit,
        )
