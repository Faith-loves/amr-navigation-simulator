from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai.mission_parser import MissionParseError, MissionParser
from ai.semantic_locations import locations_for_scenario
from environment.grid_map import CELL_SIZE, GridMap
from environment.scenario import Scenario
from environment.scenario_manager import ScenarioManager
from planning.astar import AStarPlanner, PlannerMetrics
from planning.dijkstra import DijkstraPlanner
from robot.kinematics import get_next_robot_state
from robot.state import RobotState
from sensors.lidar import Lidar

app = FastAPI(title="AMR Navigation Simulator API", version="1.0.0")
MAX_PLANNING_TIME_MS = 2000.0


class RobotPayload(BaseModel):
    x: float
    y: float
    theta: float = 0.0


class PointPayload(BaseModel):
    x: float
    y: float


class ControlPayload(BaseModel):
    v: float = 0.0
    omega: float = 0.0


class SimulationStepRequest(BaseModel):
    robot: RobotPayload
    control: ControlPayload = Field(default_factory=ControlPayload)
    dt: float = Field(default=0.05, ge=0.0, le=0.25)
    scenario: str = "Open Space"
    lidar: bool = True
    goal: PointPayload | tuple[float, float] | None = None


class SimulationResetRequest(BaseModel):
    scenario: str = "Open Space"


class GoalRequest(BaseModel):
    scenario: str = "Open Space"
    goal: PointPayload | tuple[float, float]


class PlannerRequest(BaseModel):
    planner: Literal["astar", "dijkstra", "rrtstar", "A*", "Dijkstra", "RRT*"] = "astar"
    scenario: str = "Open Space"
    start: PointPayload | tuple[float, float]
    goal: PointPayload | tuple[float, float]


class MissionParseRequest(BaseModel):
    scenario: str = "Open Space"
    command: str


def _scenario_key(value: str) -> str:
    return value.strip().lower().replace("_", " ").replace("-", " ")


def _scenario_slug(scenario: Scenario) -> str:
    return scenario.name.lower().replace(" ", "-")


def _scenario_for(value: str) -> Scenario:
    key = _scenario_key(value)
    for scenario in ScenarioManager().scenarios:
        if key in {_scenario_key(scenario.name), _scenario_slug(scenario)}:
            return scenario
    raise HTTPException(status_code=404, detail=f"Unknown scenario: {value}")


def _cell_from_xy(point: PointPayload | tuple[float, float], cell_size: int = CELL_SIZE) -> tuple[int, int]:
    if isinstance(point, PointPayload):
        x, y = point.x, point.y
    else:
        x, y = point
    return int(y // cell_size), int(x // cell_size)


def _xy_from_cell(cell: tuple[int, int], cell_size: int = CELL_SIZE) -> dict[str, float]:
    row, col = cell
    return {"x": col * cell_size + cell_size / 2, "y": row * cell_size + cell_size / 2}


def _serialise_robot(robot: RobotState) -> dict[str, float]:
    return {"x": robot.x, "y": robot.y, "theta": robot.theta}


def _serialise_metrics(metrics: PlannerMetrics) -> dict[str, float | int | bool]:
    return {
        "planning_time_ms": metrics.planning_time_ms,
        "nodes_expanded": metrics.nodes_expanded,
        "path_length_pixels": metrics.path_length_pixels,
        "raw_waypoints_count": metrics.raw_waypoints_count,
        "success": metrics.success,
    }


def _planner_for(name: str, grid: list[list[int]], cell_size: int):
    key = name.strip().lower().replace("*", "star")
    if key in {"astar", "a"}:
        return AStarPlanner(grid, cell_size=cell_size), None
    if key == "dijkstra":
        return DijkstraPlanner(grid, cell_size=cell_size), None
    if key == "rrtstar":
        return AStarPlanner(grid, cell_size=cell_size), "RRT* runtime planner is not implemented in this checkout; using A* fallback."
    raise HTTPException(status_code=400, detail=f"Unsupported planner: {name}")


def _path_to_points(path: list[tuple[int, int]], cell_size: int) -> list[dict[str, float]]:
    return [_xy_from_cell(cell, cell_size) for cell in path]


def _cell_is_free(grid: list[list[int]], cell: tuple[int, int]) -> bool:
    row, col = cell
    return 0 <= row < len(grid) and 0 <= col < len(grid[0]) and grid[row][col] == 0


def _semantic_locations(scenario_name: str) -> list[dict[str, object]]:
    unique = {}
    for location in locations_for_scenario(scenario_name).values():
        unique[location.name] = location
    return [
        {
            "name": location.name,
            "cell": list(location.cell),
            "position": {"x": location.position[0], "y": location.position[1]},
            "aliases": list(location.aliases),
        }
        for location in sorted(unique.values(), key=lambda item: item.name)
    ]


def _scenario_json(scenario: Scenario) -> dict[str, object]:
    rows = len(scenario.grid)
    cols = len(scenario.grid[0]) if rows else 0
    return {
        "name": scenario.name,
        "slug": _scenario_slug(scenario),
        "difficulty": scenario.difficulty,
        "description": scenario.description,
        "recommended_planner": scenario.recommended_planner,
        "mission_label": scenario.mission_label,
        "cell_size": CELL_SIZE,
        "rows": rows,
        "cols": cols,
        "width": cols * CELL_SIZE,
        "height": rows * CELL_SIZE,
        "start": {"cell": list(scenario.start_cell), "x": scenario.robot_start_x, "y": scenario.robot_start_y, "theta": scenario.robot_start_theta},
        "goal": {"cell": list(scenario.goal_cell), "x": scenario.goal_x, "y": scenario.goal_y},
        "grid": scenario.copy_grid(),
        "obstacles": [
            {"row": row, "col": col, "height": height, "width": width}
            for row, col, height, width in scenario.static_obstacles
        ],
        "dynamic_obstacles": [obstacle.__dict__ for obstacle in scenario.dynamic_obstacles],
        "semantic_locations": _semantic_locations(scenario.name),
    }


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "AMR Navigation Simulator API"}


@app.get("/api/scenarios")
def scenarios() -> dict[str, object]:
    return {"scenarios": [_scenario_json(scenario) for scenario in ScenarioManager().scenarios]}


@app.post("/api/simulation/reset")
def simulation_reset(request: SimulationResetRequest) -> dict[str, object]:
    scenario = _scenario_for(request.scenario)
    return {"scenario": _scenario_json(scenario), "robot": {"x": scenario.robot_start_x, "y": scenario.robot_start_y, "theta": scenario.robot_start_theta}}


@app.post("/api/simulation/step")
def simulation_step(request: SimulationStepRequest) -> dict[str, object]:
    scenario = _scenario_for(request.scenario)
    grid_map = GridMap(scenario)
    current = RobotState(request.robot.x, request.robot.y, request.robot.theta)
    proposed = get_next_robot_state(current, request.control.v, request.control.omega, request.dt)
    collision = grid_map.collides_with_wall(proposed.x, proposed.y)
    robot = current if collision else proposed

    lidar_rays = []
    if request.lidar:
        lidar = Lidar()
        lidar_rays = [
            {"start": {"x": ray.start[0], "y": ray.start[1]}, "end": {"x": ray.end[0], "y": ray.end[1]}, "distance": ray.noisy_distance, "hit": ray.hit}
            for ray in lidar.scan(robot, grid_map)
        ]

    if isinstance(request.goal, PointPayload):
        target_x, target_y = request.goal.x, request.goal.y
    elif request.goal:
        target_x, target_y = request.goal
    else:
        target_x, target_y = scenario.goal_x, scenario.goal_y
    goal_dx = target_x - robot.x
    goal_dy = target_y - robot.y
    return {
        "robot": _serialise_robot(robot),
        "collision": collision,
        "goal_distance": math.sqrt(goal_dx * goal_dx + goal_dy * goal_dy),
        "lidar": lidar_rays,
    }


@app.post("/api/simulation/goal")
def simulation_goal(request: GoalRequest) -> dict[str, object]:
    scenario = _scenario_for(request.scenario)
    grid_map = GridMap(scenario)
    row, col = _cell_from_xy(request.goal, grid_map.cell_size)
    valid = 0 <= row < len(grid_map.grid) and 0 <= col < len(grid_map.grid[0]) and not grid_map.is_wall(row, col)
    if not valid:
        raise HTTPException(status_code=400, detail={"error": "INVALID_GOAL", "goal_cell": [row, col]})
    return {"valid": True, "goal_cell": [row, col], "goal": _xy_from_cell((row, col), grid_map.cell_size)}


@app.post("/api/planner/plan")
def planner_plan(request: PlannerRequest) -> dict[str, object]:
    scenario = _scenario_for(request.scenario)
    grid_map = GridMap(scenario)
    grid = grid_map.get_planning_grid()
    planner, note = _planner_for(request.planner, grid, grid_map.cell_size)
    start = _cell_from_xy(request.start, grid_map.cell_size)
    goal = _cell_from_xy(request.goal, grid_map.cell_size)
    if not _cell_is_free(grid, start):
        raise HTTPException(status_code=400, detail={"error": "INVALID_START", "start_cell": list(start)})
    if not _cell_is_free(grid, goal):
        raise HTTPException(status_code=400, detail={"error": "INVALID_GOAL", "goal_cell": list(goal)})

    path = planner.plan(start, goal)
    if planner.latest_metrics.planning_time_ms > MAX_PLANNING_TIME_MS:
        return {
            "success": False,
            "error": "PLANNING_TIMEOUT",
            "planner": request.planner,
            "note": note,
            "start_cell": list(start),
            "goal_cell": list(goal),
            "path_cells": [],
            "path": [],
            **_serialise_metrics(planner.latest_metrics),
        }

    error = "" if path else "NO_PATH"
    return {
        "success": bool(path),
        "error": error,
        "planner": request.planner,
        "note": note,
        "start_cell": list(start),
        "goal_cell": list(goal),
        "path_cells": [list(cell) for cell in path],
        "path": _path_to_points(path, grid_map.cell_size),
        **_serialise_metrics(planner.latest_metrics),
    }


@app.post("/api/mission/parse")
def mission_parse(request: MissionParseRequest) -> dict[str, object]:
    scenario = _scenario_for(request.scenario)
    parser = MissionParser()
    parsed = parser.parse_intent(request.command, scenario.name)
    tasks = []
    if not parsed.error_message:
        try:
            mission = parser.parse(request.command, scenario.name)
            tasks = [
                {"target_name": task.target_name, "target_position": {"x": task.target_position[0], "y": task.target_position[1]}}
                for task in mission.tasks
            ]
        except MissionParseError:
            tasks = []
    return {
        "intent": parsed.intent,
        "destinations": parsed.destinations,
        "confidence": parsed.confidence,
        "normalized_text": parsed.normalized_text,
        "error": parsed.error_message,
        "tasks": tasks,
    }





