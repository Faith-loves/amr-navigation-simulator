from environment.grid_map import GridMap
from environment.scenario_manager import ScenarioManager
from planning.astar import AStarPlanner
from planning.dijkstra import DijkstraPlanner
from simulator.simulation_loop import _navigation_snapshot
from simulator.goal_manager import (
    TARGET_EXPLORATION,
    TARGET_MANUAL,
    TARGET_MISSION,
    TARGET_SCENARIO,
    TARGET_TEMPORARY,
    GoalManager,
)


def test_scenario_goal_remains_unchanged_during_normal_autonomous_navigation() -> None:
    scenario = ScenarioManager().current_scenario
    manager = GoalManager(scenario.goal_cell, scenario.mission_label)

    manager.record_path_repair((12, 12))

    assert manager.scenario_goal == scenario.goal_cell
    assert manager.active_goal == scenario.goal_cell
    assert manager.active_type == TARGET_SCENARIO


def test_replanning_does_not_modify_active_goal() -> None:
    manager = GoalManager((26, 17), "Delivery Point")

    manager.record_path_repair((25, 16))

    assert manager.active_goal == (26, 17)


def test_dynamic_obstacle_does_not_modify_goal() -> None:
    manager = GoalManager((26, 17), "Delivery Point")

    manager.record_path_repair((20, 10))

    assert manager.scenario_goal == (26, 17)
    assert manager.active_goal == (26, 17)


def test_astar_replanning_uses_same_destination() -> None:
    scenario = ScenarioManager().current_scenario
    grid_map = GridMap(scenario)
    planner = AStarPlanner(grid_map.get_planning_grid(), cell_size=grid_map.cell_size)

    path = planner.plan(scenario.start_cell, scenario.goal_cell)

    assert path[-1] == scenario.goal_cell


def test_dijkstra_replanning_uses_same_destination() -> None:
    scenario = ScenarioManager().current_scenario
    grid_map = GridMap(scenario)
    planner = DijkstraPlanner(grid_map.get_planning_grid(), cell_size=grid_map.cell_size)

    path = planner.plan(scenario.start_cell, scenario.goal_cell)

    assert path[-1] == scenario.goal_cell


def test_rrt_request_does_not_mutate_destination_when_falling_back() -> None:
    scenario = ScenarioManager().current_scenario
    manager = GoalManager(scenario.goal_cell, "RRT* requested target")

    manager.record_path_repair((8, 8))

    assert manager.active_goal == scenario.goal_cell


def test_mission_target_changes_only_after_previous_task_completion() -> None:
    manager = GoalManager((26, 17), "Scenario Objective")
    manager.set_mission_goal((4, 14), "Kitchen", "AI mission command")

    assert manager.active_goal == (4, 14)
    assert manager.active_type == TARGET_MISSION

    manager.record_path_repair((26, 16))
    assert manager.active_goal == (4, 14)

    manager.set_mission_goal((26, 16), "Bedroom", "Mission task completed")
    assert manager.active_goal == (26, 16)
    assert manager.change_log[-1].reason == "Mission task completed"


def test_exploration_target_does_not_overwrite_scenario_goal() -> None:
    manager = GoalManager((26, 17), "Scenario Objective")

    manager.set_exploration_goal((12, 9), "Frontier 3", "Exploration frontier selected")

    assert manager.scenario_goal == (26, 17)
    assert manager.active_goal == (12, 9)
    assert manager.active_type == TARGET_EXPLORATION


def test_turning_exploration_off_restores_normal_target() -> None:
    manager = GoalManager((26, 17), "Scenario Objective")
    manager.set_exploration_goal((12, 9), "Frontier 3", "Exploration frontier selected")

    manager.stop_exploration()

    assert manager.active_goal == (26, 17)
    assert manager.active_type == TARGET_SCENARIO


def test_temporary_charger_target_preserves_original_destination() -> None:
    manager = GoalManager((26, 17), "Scenario Objective")
    manager.set_mission_goal((26, 16), "Bedroom", "AI mission command")

    manager.set_temporary_goal((24, 3), "Charging Station", "Critical battery")

    assert manager.active_goal == (24, 3)
    assert manager.active_type == TARGET_TEMPORARY

    restored = manager.clear_temporary_goal("Battery charged")

    assert restored == (26, 16)
    assert manager.active_type == TARGET_MISSION


def test_reset_restores_original_scenario_goal() -> None:
    manager = GoalManager((26, 17), "Scenario Objective")
    manager.set_mission_goal((4, 14), "Kitchen", "AI mission command")
    manager.set_temporary_goal((24, 3), "Charging Station", "Critical battery")

    manager.set_scenario_goal()

    assert manager.active_goal == (26, 17)
    assert manager.temporary_target is None
    assert manager.mission_target is None


def test_manual_target_does_not_mutate_scenario_configuration() -> None:
    manager = GoalManager((26, 17), "Scenario Objective")

    manager.set_manual_goal((10, 10))

    assert manager.scenario_goal == (26, 17)
    assert manager.active_goal == (10, 10)
    assert manager.active_type == TARGET_MANUAL


def test_navigation_snapshot_combines_mission_and_goal_state() -> None:
    manager = GoalManager((26, 17), "Scenario Objective")
    manager.set_mission_goal((4, 14), "Kitchen", "AI mission command")

    snapshot = _navigation_snapshot(
        {"mission_status": "RUNNING", "current_target": "Kitchen", "confidence": 0.92},
        manager,
    )

    assert snapshot["mission_status"] == "RUNNING"
    assert snapshot["current_target"] == "Kitchen"
    assert snapshot["navigation_target"] == "Kitchen"
    assert snapshot["target_type"] == TARGET_MISSION
    assert snapshot["active_goal"] == (4, 14)
    assert snapshot["scenario_goal"] == (26, 17)