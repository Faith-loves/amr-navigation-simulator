from ai.mission_parser import (
    INTENT_UNKNOWN,
    MISSION_COMPLETED,
    MISSION_FAILED,
    MISSION_IDLE,
    MISSION_RUNNING,
    TASK_ACTIVE,
    TASK_COMPLETED,
    TASK_FAILED,
    TASK_PENDING,
    Mission,
    MissionTask,
)


MISSION_PAUSED = "PAUSED"
MISSION_CANCELLED = "CANCELLED"


class MissionManager:
    def __init__(self) -> None:
        self.mission: Mission | None = None
        self.last_error = ""
        self.command_history: list[str] = []

    @property
    def mission_status(self) -> str:
        if self.mission is None:
            return MISSION_IDLE
        return self.mission.mission_status

    @property
    def current_task(self) -> MissionTask | None:
        if self.mission is None:
            return None
        return self.mission.current_task

    @property
    def raw_command(self) -> str:
        if self.mission is None:
            return ""
        return self.mission.raw_command

    @property
    def current_task_index(self) -> int:
        if self.mission is None:
            return 0
        return self.mission.current_task_index

    @property
    def completed_task_count(self) -> int:
        if self.mission is None:
            return 0
        return sum(1 for task in self.mission.tasks if task.status == TASK_COMPLETED)

    def start(self, mission: Mission) -> MissionTask | None:
        self._record_command(mission.raw_command)
        self.mission = mission
        self.last_error = ""
        if not mission.tasks:
            mission.mission_status = MISSION_FAILED
            self.last_error = "No valid destination found."
            return None
        mission.current_task_index = 0
        mission.mission_status = MISSION_RUNNING
        mission.tasks[0].status = TASK_ACTIVE
        for task in mission.tasks[1:]:
            task.status = TASK_PENDING
        return mission.tasks[0]

    def complete_current_task(self) -> MissionTask | None:
        if self.mission is None or self.mission.mission_status != MISSION_RUNNING:
            return None

        task = self.mission.current_task
        if task is None:
            self.mission.mission_status = MISSION_COMPLETED
            return None

        task.status = TASK_COMPLETED
        self.mission.current_task_index += 1

        next_task = self.mission.current_task
        if next_task is None:
            self.mission.mission_status = MISSION_COMPLETED
            return None

        next_task.status = TASK_ACTIVE
        return next_task

    def fail_current_task(self, reason: str) -> None:
        self.last_error = reason
        if self.mission is None:
            return
        task = self.mission.current_task
        if task is not None:
            task.status = TASK_FAILED
        self.mission.mission_status = MISSION_FAILED

    def pause(self) -> None:
        if self.mission is not None and self.mission.mission_status == MISSION_RUNNING:
            self.mission.mission_status = MISSION_PAUSED

    def resume(self) -> MissionTask | None:
        if self.mission is None:
            return None
        if self.mission.mission_status == MISSION_PAUSED:
            self.mission.mission_status = MISSION_RUNNING
            task = self.mission.current_task
            if task is not None:
                task.status = TASK_ACTIVE
            return task
        return self.mission.current_task

    def cancel(self) -> None:
        if self.mission is not None and self.mission.mission_status not in {MISSION_COMPLETED, MISSION_FAILED}:
            self.mission.mission_status = MISSION_CANCELLED
        self.last_error = ""

    def reset(self) -> None:
        self.mission = None
        self.last_error = ""

    def reached_current_target(self, robot_x: float, robot_y: float, tolerance: float) -> bool:
        task = self.current_task
        if task is None or self.mission_status != MISSION_RUNNING:
            return False

        target_x, target_y = task.target_position
        dx = target_x - robot_x
        dy = target_y - robot_y
        return dx * dx + dy * dy <= tolerance * tolerance

    def snapshot(self) -> dict[str, object]:
        task = self.current_task
        return {
            "raw_command": self.raw_command,
            "mission_status": self.mission_status,
            "intent": INTENT_UNKNOWN if self.mission is None else self.mission.intent,
            "confidence": 0.0 if self.mission is None else self.mission.confidence,
            "current_target": "" if task is None else task.target_name,
            "current_task_index": self.current_task_index,
            "current_target_position": None if task is None else task.target_position,
            "completed_task_count": self.completed_task_count,
            "tasks": [] if self.mission is None else [
                {"target_name": task.target_name, "status": task.status}
                for task in self.mission.tasks
            ],
            "last_error": self.last_error,
            "command_history": self.command_history[-5:],
        }

    def _record_command(self, raw_command: str) -> None:
        command = raw_command.strip()
        if not command:
            return
        self.command_history.append(command)
        if len(self.command_history) > 5:
            del self.command_history[0 : len(self.command_history) - 5]
