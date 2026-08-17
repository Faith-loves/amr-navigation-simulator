from dataclasses import dataclass


@dataclass(frozen=True)
class ControlCommand:
    v: float
    omega: float


def manual_command(
    forward: bool,
    backward: bool,
    rotate_left: bool,
    rotate_right: bool,
    linear_speed: float,
    angular_speed: float,
) -> ControlCommand:
    v = 0.0
    omega = 0.0

    if forward:
        v = linear_speed
    if backward:
        v = -linear_speed
    if rotate_left:
        omega = -angular_speed
    if rotate_right:
        omega = angular_speed

    return ControlCommand(v=v, omega=omega)


def has_manual_input(command: ControlCommand) -> bool:
    return command.v != 0.0 or command.omega != 0.0


def manual_override_active(autonomous_mode: bool, command: ControlCommand) -> bool:
    return autonomous_mode and has_manual_input(command)


def emergency_stop() -> ControlCommand:
    return ControlCommand(v=0.0, omega=0.0)
