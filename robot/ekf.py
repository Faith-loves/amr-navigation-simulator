import math

import numpy as np

from robot.kinematics import normalize_angle
from robot.state import RobotState


class EKFLocalization:
    def __init__(self, initial_state: RobotState) -> None:
        self.Q = np.diag([2.0, 2.0, 0.05])
        self.R = np.diag([8.0, 8.0])
        self.linear_noise_std = 2.0
        self.angular_noise_std = 0.05
        self.position_noise_std = math.sqrt(8.0)
        self.reset(initial_state)

    def reset(self, robot_state: RobotState) -> None:
        self.x = np.array(
            [robot_state.x, robot_state.y, robot_state.theta],
            dtype=float,
        )
        self.P = np.eye(3)

    def predict(self, true_v: float, true_omega: float, dt: float) -> None:
        noisy_v = true_v + np.random.normal(0, self.linear_noise_std)
        noisy_omega = true_omega + np.random.normal(0, self.angular_noise_std)

        theta = self.x[2]
        self.x[0] += noisy_v * math.cos(theta) * dt
        self.x[1] += noisy_v * math.sin(theta) * dt
        self.x[2] = normalize_angle(self.x[2] + noisy_omega * dt)

        F = np.array(
            [
                [1, 0, -noisy_v * math.sin(theta) * dt],
                [0, 1, noisy_v * math.cos(theta) * dt],
                [0, 0, 1],
            ],
            dtype=float,
        )
        self.P = F @ self.P @ F.T + self.Q

    def update_with_position_measurement(self, robot_state: RobotState) -> None:
        z = np.array(
            [
                robot_state.x + np.random.normal(0, self.position_noise_std),
                robot_state.y + np.random.normal(0, self.position_noise_std),
            ],
            dtype=float,
        )

        H = np.array(
            [
                [1, 0, 0],
                [0, 1, 0],
            ],
            dtype=float,
        )

        innovation = z - H @ self.x
        S = H @ self.P @ H.T + self.R
        K = self.P @ H.T @ np.linalg.inv(S)

        self.x = self.x + K @ innovation
        self.x[2] = normalize_angle(self.x[2])

        I = np.eye(3)
        self.P = (I - K @ H) @ self.P

    def step(self, true_v: float, true_omega: float, dt: float, robot_state: RobotState) -> None:
        self.predict(true_v, true_omega, dt)
        self.update_with_position_measurement(robot_state)

    def get_pose(self) -> RobotState:
        return RobotState(
            x=float(self.x[0]),
            y=float(self.x[1]),
            theta=float(self.x[2]),
        )

    def position_error(self, robot_state: RobotState) -> float:
        dx = robot_state.x - self.x[0]
        dy = robot_state.y - self.x[1]
        return math.sqrt(dx * dx + dy * dy)

    def covariance_trace(self) -> float:
        return float(np.trace(self.P))
