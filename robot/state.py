from dataclasses import dataclass


@dataclass
class RobotState:
    x: float
    y: float
    theta: float
