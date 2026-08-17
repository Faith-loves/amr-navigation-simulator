from __future__ import annotations

from dataclasses import dataclass


TARGET_SCENARIO = "Scenario"
TARGET_MISSION = "Mission"
TARGET_EXPLORATION = "Exploration"
TARGET_TEMPORARY = "Temporary"
TARGET_MANUAL = "Manual"


@dataclass(frozen=True)
class TargetChange:
    previous_label: str
    next_label: str
    reason: str


@dataclass
class NavigationTarget:
    cell: tuple[int, int] | None
    label: str
    target_type: str


class GoalManager:
    def __init__(self, scenario_goal: tuple[int, int], scenario_label: str = "Scenario Objective") -> None:
        self.scenario_goal = scenario_goal
        self.active_target = NavigationTarget(scenario_goal, scenario_label, TARGET_SCENARIO)
        self.temporary_target: NavigationTarget | None = None
        self.mission_target: NavigationTarget | None = None
        self.exploration_target: NavigationTarget | None = None
        self._pre_temporary_target: NavigationTarget | None = None
        self.change_log: list[TargetChange] = []

    @property
    def active_goal(self) -> tuple[int, int] | None:
        return self.active_target.cell

    @property
    def active_label(self) -> str:
        return self.active_target.label

    @property
    def active_type(self) -> str:
        return self.active_target.target_type

    def set_scenario_goal(self, reason: str = "Scenario reset") -> None:
        self.mission_target = None
        self.exploration_target = None
        self.temporary_target = None
        self._pre_temporary_target = None
        self._set_active(NavigationTarget(self.scenario_goal, "Scenario Objective", TARGET_SCENARIO), reason)

    def set_manual_goal(self, cell: tuple[int, int], label: str = "Manual Target") -> None:
        self._set_active(NavigationTarget(cell, label, TARGET_MANUAL), "Manual target selected")

    def set_mission_goal(self, cell: tuple[int, int], label: str, reason: str) -> None:
        self.mission_target = NavigationTarget(cell, label, TARGET_MISSION)
        self._set_active(self.mission_target, reason)

    def set_exploration_goal(self, cell: tuple[int, int], label: str, reason: str) -> None:
        self.exploration_target = NavigationTarget(cell, label, TARGET_EXPLORATION)
        self._set_active(self.exploration_target, reason)

    def stop_exploration(self, reason: str = "Exploration stopped") -> None:
        self.exploration_target = None
        if self.mission_target is not None:
            self._set_active(self.mission_target, reason)
        else:
            self._set_active(NavigationTarget(self.scenario_goal, "Scenario Objective", TARGET_SCENARIO), reason)

    def set_temporary_goal(self, cell: tuple[int, int], label: str, reason: str) -> None:
        if self.temporary_target is None:
            self._pre_temporary_target = self.active_target
        self.temporary_target = NavigationTarget(cell, label, TARGET_TEMPORARY)
        self._set_active(self.temporary_target, reason)

    def clear_temporary_goal(self, reason: str = "Temporary target complete") -> tuple[int, int] | None:
        self.temporary_target = None
        restore = self._pre_temporary_target or NavigationTarget(self.scenario_goal, "Scenario Objective", TARGET_SCENARIO)
        self._pre_temporary_target = None
        self._set_active(restore, reason)
        return self.active_goal

    def replan_target(self) -> tuple[int, int] | None:
        return self.active_goal

    def record_path_repair(self, result_goal: tuple[int, int] | None) -> None:
        # Replanning may change the route. It must not change the owned target.
        return

    def snapshot(self) -> dict[str, object]:
        return {
            "scenario_goal": self.scenario_goal,
            "active_goal": self.active_goal,
            "navigation_target": self.active_label,
            "target_type": self.active_type,
            "last_target_change": None if not self.change_log else self.change_log[-1].__dict__,
        }

    def _set_active(self, target: NavigationTarget, reason: str) -> None:
        previous = self.active_target
        if previous.cell == target.cell and previous.target_type == target.target_type and previous.label == target.label:
            return
        self.active_target = target
        self.change_log.append(TargetChange(previous.label, target.label, reason))
