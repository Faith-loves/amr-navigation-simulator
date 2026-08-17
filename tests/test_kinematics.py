import math

import pytest

from robot.kinematics import get_next_robot_state, update_robot_state
from robot.state import RobotState


def test_robot_moves_forward_with_zero_heading() -> None:
    robot_state = RobotState(x=0, y=0, theta=0)

    next_state = get_next_robot_state(robot_state, v=10, omega=0, dt=1)

    assert next_state.x == pytest.approx(10)
    assert next_state.y == pytest.approx(0)


def test_theta_stays_between_minus_pi_and_pi() -> None:
    robot_state = RobotState(x=0, y=0, theta=math.pi)

    next_state = get_next_robot_state(robot_state, v=0, omega=10, dt=1)
    update_robot_state(robot_state, next_state)

    assert -math.pi <= robot_state.theta <= math.pi
