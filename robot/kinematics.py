import math

from robot.state import RobotState


def get_next_robot_state(
    robot_state: RobotState,
    v: float,
    omega: float,
    dt: float,
) -> RobotState:
    return RobotState(
        x=robot_state.x + v * math.cos(robot_state.theta) * dt,
        y=robot_state.y + v * math.sin(robot_state.theta) * dt,
        theta=normalize_angle(robot_state.theta + omega * dt),
    )


def update_robot_state(
    robot_state: RobotState,
    next_state: RobotState,
) -> None:
    robot_state.x = next_state.x
    robot_state.y = next_state.y
    robot_state.theta = normalize_angle(next_state.theta)


def normalize_angle(angle: float) -> float:
    return math.atan2(math.sin(angle), math.cos(angle))
