from ai.mission_manager import MissionManager
from ai.mission_parser import (
    MISSION_COMPLETED,
    MISSION_FAILED,
    MISSION_RUNNING,
    TASK_ACTIVE,
    TASK_COMPLETED,
    TASK_FAILED,
    MissionParseError,
    MissionParser,
)


def test_parse_single_destination() -> None:
    mission = MissionParser().parse("Go to the kitchen", "House Layout")

    assert [task.target_name for task in mission.tasks] == ["Kitchen"]


def test_parse_two_sequential_destinations() -> None:
    mission = MissionParser().parse("Go to the kitchen then the bedroom", "House Layout")

    assert [task.target_name for task in mission.tasks] == ["Kitchen", "Bedroom"]


def test_parse_three_destinations() -> None:
    mission = MissionParser().parse(
        "Visit the living room then the hallway then the bedroom",
        "House Layout",
    )

    assert [task.target_name for task in mission.tasks] == ["Living Room", "Hallway", "Bedroom"]


def test_parse_return_to_command() -> None:
    mission = MissionParser().parse(
        "Go to the kitchen then return to the charging station",
        "House Layout",
    )

    assert [task.target_name for task in mission.tasks] == ["Kitchen", "Charging Station"]


def test_parse_aliases() -> None:
    mission = MissionParser().parse("Take me to the charger", "Office")

    assert [task.target_name for task in mission.tasks] == ["Charging Station"]


def test_unknown_location_rejected() -> None:
    try:
        MissionParser().parse("Go to Mars", "House Layout")
    except MissionParseError as error:
        assert str(error) == "Unknown location: Mars"
    else:
        raise AssertionError("Expected MissionParseError")



def test_no_valid_destination_found() -> None:
    try:
        MissionParser().parse("Go somewhere", "House Layout")
    except MissionParseError as error:
        assert str(error) == "No valid destination found."
    else:
        raise AssertionError("Expected MissionParseError")


def test_scenario_specific_location_validation() -> None:
    try:
        MissionParser().parse("Go to the kitchen", "Warehouse")
    except MissionParseError as error:
        assert str(error) == "Unknown location: Kitchen"
    else:
        raise AssertionError("Expected MissionParseError")


def test_mission_queue_progression() -> None:
    mission = MissionParser().parse("Go to aisle 1 then aisle 3", "Warehouse")
    manager = MissionManager()

    task = manager.start(mission)

    assert manager.mission_status == MISSION_RUNNING
    assert task is not None
    assert task.target_name == "Aisle 1"
    assert task.status == TASK_ACTIVE


def test_completed_task_automatically_activates_next_task() -> None:
    mission = MissionParser().parse("Go to aisle 1 then aisle 3", "Warehouse")
    manager = MissionManager()
    manager.start(mission)

    next_task = manager.complete_current_task()

    assert mission.tasks[0].status == TASK_COMPLETED
    assert next_task is not None
    assert next_task.target_name == "Aisle 3"
    assert next_task.status == TASK_ACTIVE


def test_complete_mission_sets_status_completed() -> None:
    mission = MissionParser().parse("Go to the charging station", "Office")
    manager = MissionManager()
    manager.start(mission)

    next_task = manager.complete_current_task()

    assert next_task is None
    assert manager.mission_status == MISSION_COMPLETED


def test_failed_planner_marks_task_failed() -> None:
    mission = MissionParser().parse("Go to the charging station", "Office")
    manager = MissionManager()
    manager.start(mission)

    manager.fail_current_task("Planning failed for mission target.")

    assert manager.mission_status == MISSION_FAILED
    assert mission.tasks[0].status == TASK_FAILED
    assert manager.last_error == "Planning failed for mission target."
