from ai.mission_parser import (
    INTENT_CANCEL,
    INTENT_MULTI_STOP,
    INTENT_NAVIGATE,
    INTENT_PAUSE,
    INTENT_RESUME,
    INTENT_STOP,
    MissionParser,
)
from robot.kinematics import get_next_robot_state
from robot.state import RobotState
from simulator.control_helpers import emergency_stop, manual_command, manual_override_active
from visualization.lidar_view import (
    LIDAR_VIEW_FULL,
    LIDAR_VIEW_MINIMAL,
    LIDAR_VIEW_OFF,
    visible_lidar_rays,
)


def test_fuzzy_matching_kichen_to_kitchen() -> None:
    result = MissionParser().parse_intent("can you go to the kichen please", "House Layout")

    assert result.intent == INTENT_NAVIGATE
    assert result.destinations == ["kitchen"]
    assert result.confidence >= 0.72


def test_low_confidence_unknown_terms_are_rejected() -> None:
    result = MissionParser().parse_intent("go to marsbase", "House Layout")

    assert result.destinations == []
    assert result.error_message == "Unknown location: Marsbase"


def test_charging_dock_alias_resolves() -> None:
    result = MissionParser().parse_intent("return to the charging dock", "House Layout")

    assert result.destinations == ["charging station"]


def test_navigate_intent() -> None:
    result = MissionParser().parse_intent("Take the robot to reception", "Office")

    assert result.intent == INTENT_NAVIGATE
    assert result.destinations == ["reception"]


def test_multi_stop_intent() -> None:
    result = MissionParser().parse_intent("Visit reception then meeting room", "Office")

    assert result.intent == INTENT_MULTI_STOP
    assert result.destinations == ["reception", "meeting room"]


def test_stop_pause_resume_cancel_intents() -> None:
    parser = MissionParser()

    assert parser.parse_intent("Stop the robot", "Office").intent == INTENT_STOP
    assert parser.parse_intent("Pause navigation", "Office").intent == INTENT_PAUSE
    assert parser.parse_intent("Continue", "Office").intent == INTENT_RESUME
    assert parser.parse_intent("Cancel this mission", "Office").intent == INTENT_CANCEL


def test_manual_control_updates_robot_state() -> None:
    command = manual_command(True, False, False, False, linear_speed=100, angular_speed=2)
    next_state = get_next_robot_state(RobotState(10, 10, 0), command.v, command.omega, 0.5)

    assert next_state.x == 60
    assert next_state.y == 10


def test_manual_override_pauses_autonomy() -> None:
    command = manual_command(True, False, False, False, linear_speed=100, angular_speed=2)

    assert manual_override_active(True, command)


def test_emergency_stop_sets_velocity_to_zero() -> None:
    command = emergency_stop()

    assert command.v == 0
    assert command.omega == 0


def test_lidar_off_does_not_require_empty_sensor_scan() -> None:
    rays = list(range(41))

    assert len(rays) == 41
    assert visible_lidar_rays(rays, LIDAR_VIEW_OFF) == []


def test_lidar_minimal_renders_fewer_rays_than_full() -> None:
    rays = list(range(41))

    minimal = visible_lidar_rays(rays, LIDAR_VIEW_MINIMAL)
    full = visible_lidar_rays(rays, LIDAR_VIEW_FULL)

    assert len(minimal) < len(full)
    assert full == rays


def test_text_input_focus_can_be_cleared_without_control_state() -> None:
    command = manual_command(False, False, True, False, linear_speed=100, angular_speed=2)

    assert command.omega == -2
