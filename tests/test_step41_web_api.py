from fastapi.testclient import TestClient

from api.index import app


client = TestClient(app)


def test_step41_health_endpoint() -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "AMR Navigation Simulator API"}


def test_step41_scenarios_are_serialized_for_web() -> None:
    response = client.get("/api/scenarios")

    assert response.status_code == 200
    scenarios = response.json()["scenarios"]
    house = next(item for item in scenarios if item["slug"] == "house-layout")
    assert house["width"] > 0
    assert house["height"] > 0
    assert house["start"]["cell"]
    assert house["goal"]["cell"] == [10, 11]
    assert house["semantic_locations"]


def test_step41_planner_endpoint_uses_python_astar() -> None:
    response = client.post(
        "/api/planner/plan",
        json={"planner": "astar", "scenario": "house-layout", "start": [70, 70], "goal": [230, 210]},
    )

    body = response.json()
    assert response.status_code == 200
    assert body["success"]
    assert body["path"]
    assert body["nodes_expanded"] > 0
    assert body["planning_time_ms"] >= 0


def test_step41_rrtstar_returns_explicit_fallback_note() -> None:
    response = client.post(
        "/api/planner/plan",
        json={"planner": "rrtstar", "scenario": "open-space", "start": [50, 50], "goal": [350, 530]},
    )

    body = response.json()
    assert response.status_code == 200
    assert body["success"]
    assert "fallback" in body["note"].lower()


def test_step41_simulation_step_is_stateless() -> None:
    request = {"scenario": "open-space", "robot": {"x": 50, "y": 50, "theta": 0}, "control": {"v": 40, "omega": 0}, "dt": 0.1, "lidar": True}

    first = client.post("/api/simulation/step", json=request).json()
    second = client.post("/api/simulation/step", json=request).json()

    assert first["robot"] == second["robot"]
    assert first["lidar"]
    assert isinstance(first["collision"], bool)


def test_step41_mission_parse_reuses_local_parser() -> None:
    response = client.post("/api/mission/parse", json={"scenario": "house-layout", "command": "go to the kitchen then bedroom"})

    body = response.json()
    assert response.status_code == 200
    assert body["intent"] == "MULTI_STOP"
    assert body["destinations"] == ["kitchen", "bedroom"]
    assert len(body["tasks"]) == 2

def test_step42_planner_rejects_blocked_goal_cleanly() -> None:
    response = client.post(
        "/api/planner/plan",
        json={"planner": "astar", "scenario": "open-space", "start": [50, 50], "goal": [10, 10]},
    )

    assert response.status_code == 400
    assert response.json()["detail"]["error"] == "INVALID_GOAL"


def test_step42_goal_endpoint_rejects_invalid_goal_cleanly() -> None:
    response = client.post("/api/simulation/goal", json={"scenario": "open-space", "goal": [10, 10]})

    assert response.status_code == 400
    assert response.json()["detail"]["error"] == "INVALID_GOAL"