import math

import numpy as np

from robot.kinematics import normalize_angle
from robot.state import RobotState


class Odometry:
    def __init__(
        self,
        initial_state: RobotState,
        linear_noise_std: float = 2.0,
        angular_noise_std: float = 0.05,
    ) -> None:
        self.linear_noise_std = linear_noise_std
        self.angular_noise_std = angular_noise_std
        self.reset(initial_state)

    def reset(self, robot_state: RobotState) -> None:
        self.odom_x = robot_state.x
        self.odom_y = robot_state.y
        self.odom_theta = robot_state.theta

    def update(self, true_v: float, true_omega: float, dt: float) -> None:
        noisy_v = true_v + np.random.normal(0, self.linear_noise_std)
        noisy_omega = true_omega + np.random.normal(0, self.angular_noise_std)

        self.odom_x += noisy_v * math.cos(self.odom_theta) * dt
        self.odom_y += noisy_v * math.sin(self.odom_theta) * dt
        self.odom_theta = normalize_angle(self.odom_theta + noisy_omega * dt)

    def get_pose(self) -> RobotState:
        return RobotState(
            x=self.odom_x,
            y=self.odom_y,
            theta=self.odom_theta,
        )

    def position_error(self, robot_state: RobotState) -> float:
        dx = robot_state.x - self.odom_x
        dy = robot_state.y - self.odom_y
        return math.sqrt(dx * dx + dy * dy)
