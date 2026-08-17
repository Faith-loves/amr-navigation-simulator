from pathlib import Path
from tempfile import TemporaryDirectory

from ai.mission_manager import MISSION_PAUSED, MissionManager
from ai.mission_parser import MISSION_RUNNING, MissionParser
from robot.battery import (
    BATTERY_CRITICAL,
    BATTERY_LOW,
    CHARGE_CHARGED,
    CHARGE_CHARGING,
    CHARGE_DOCKING,
    CHARGE_NO_STATION,
    BatteryManager,
    BatteryModel,
)
from simulator.replay import ReplayPlayer


def test_battery_begins_at_100() -> None:
    battery = BatteryModel()

    assert battery.percentage == 100.0


def test_movement_consumes_battery() -> None:
    battery = BatteryModel()

    battery.consume(linear_velocity=100.0, angular_velocity=1.0, dt=1.0)

    assert battery.percentage < 100.0
    assert battery.energy_consumed > 0.0


def test_battery_never_exceeds_100() -> None:
    battery = BatteryModel(current_charge=99.0)

    battery.charge(10.0)

    assert battery.percentage == 100.0


def test_battery_never_falls_below_0() -> None:
    battery = BatteryModel(current_charge=1.0)

    battery.consume(linear_velocity=10000.0, angular_velocity=1000.0, dt=60.0)

    assert battery.percentage == 0.0


def test_low_threshold_detected() -> None:
    battery = BatteryModel()
    battery.set_percentage(30.0)

    assert battery.state == BATTERY_LOW


def test_critical_threshold_detected() -> None:
    battery = BatteryModel()
    battery.set_percentage(20.0)

    assert battery.state == BATTERY_CRITICAL


def test_autonomous_mode_requests_charger_at_critical_battery() -> None:
    manager = BatteryManager(BatteryModel())
    manager.battery.set_percentage(20.0)

    assert manager.should_request_charger(autonomous_mode=True, manual_mode=False)


def test_current_mission_is_preserved_when_paused_for_charging() -> None:
    mission = MissionParser().parse("Go to kitchen then bedroom", "House Layout")
    mission_manager = MissionManager()
    mission_manager.start(mission)

    mission_manager.pause()

    assert mission_manager.mission_status == MISSION_PAUSED
    assert mission_manager.current_task is not None
    assert mission_manager.current_task.target_name == "Kitchen"


def test_reaching_charger_starts_charging() -> None:
    manager = BatteryManager(BatteryModel())
    manager.start_return_to_charger((5, 5), (2, 2))

    manager.update_docking(10.0)

    assert manager.charge_state == CHARGE_CHARGING
    assert manager.battery.charging
    assert manager.charging_stops == 1


def test_docking_state_before_charging() -> None:
    manager = BatteryManager(BatteryModel())
    manager.start_return_to_charger((5, 5), (2, 2))

    manager.update_docking(40.0)

    assert manager.charge_state == CHARGE_DOCKING


def test_charging_increases_battery() -> None:
    battery = BatteryModel()
    battery.set_percentage(40.0)
    manager = BatteryManager(battery)
    manager.start_return_to_charger((5, 5), (2, 2))
    manager.update_docking(1.0)

    before = battery.percentage
    manager.update_charging(1.0)

    assert battery.percentage > before


def test_charging_stops_at_100() -> None:
    battery = BatteryModel()
    battery.set_percentage(99.0)
    manager = BatteryManager(battery)
    manager.start_return_to_charger((5, 5), (2, 2))
    manager.update_docking(1.0)

    assert manager.update_charging(5.0)
    assert battery.percentage == 100.0
    assert manager.charge_state == CHARGE_CHARGED


def test_interrupted_mission_resumes_after_charging() -> None:
    mission = MissionParser().parse("Go to kitchen then bedroom", "House Layout")
    mission_manager = MissionManager()
    mission_manager.start(mission)
    mission_manager.pause()
    manager = BatteryManager(BatteryModel())
    manager.start_return_to_charger((4, 14), (24, 3))

    resume_goal = manager.begin_resume()
    resumed_task = mission_manager.resume()
    manager.finish_resume()

    assert resume_goal == (4, 14)
    assert resumed_task is not None
    assert mission_manager.mission_status == MISSION_RUNNING


def test_missing_charging_station_handled_safely() -> None:
    manager = BatteryManager(BatteryModel())

    assert not manager.start_return_to_charger((5, 5), None)
    assert manager.charge_state == CHARGE_NO_STATION


def test_0_percent_battery_stops_movement_state() -> None:
    battery = BatteryModel()
    battery.set_percentage(0.0)

    assert battery.is_depleted()


def test_manual_mode_does_not_unexpectedly_take_control() -> None:
    manager = BatteryManager(BatteryModel())
    manager.battery.set_percentage(20.0)

    assert not manager.should_request_charger(autonomous_mode=False, manual_mode=True)


def test_charge_command_parses_to_charging_station() -> None:
    mission = MissionParser().parse("Charge the robot", "House Layout")

    assert mission.tasks[0].target_name == "Charging Station"


def test_old_replay_logs_without_battery_fields_still_work() -> None:
    with TemporaryDirectory() as temp_dir:
        path = Path(temp_dir) / "run_old.jsonl"
        path.write_text(
            '{"robot_true_pose":{"x":1,"y":2,"theta":0},"current_planner":"A*","mission":{}}\n',
            encoding="utf-8",
        )
        player = ReplayPlayer(log_dir=temp_dir)

        assert player.load(path)
        assert player.current_frame is not None
        assert player.current_frame.battery_percentage is None
        assert player.current_frame.energy_consumed == 0.0
