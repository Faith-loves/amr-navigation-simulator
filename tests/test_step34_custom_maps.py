from pathlib import Path
from tempfile import TemporaryDirectory

from ai.mission_parser import MissionParser
from ai.semantic_locations import register_custom_locations
from editor.editor_state import CustomMap
from editor.map_serializer import export_custom_map, import_custom_map, load_custom_map, save_custom_map
from editor.map_validator import MapValidator
from planning.astar import AStarPlanner


def test_create_empty_custom_map() -> None:
    custom_map = CustomMap()

    assert custom_map.name == "Untitled Environment"
    assert custom_map.start is None
    assert custom_map.goal is None
    assert custom_map.to_grid()[0][0] == 1


def test_place_start() -> None:
    custom_map = CustomMap()

    assert custom_map.set_start((3, 3))
    assert custom_map.start == (3, 3)


def test_place_goal() -> None:
    custom_map = CustomMap()

    assert custom_map.set_goal((26, 16))
    assert custom_map.goal == (26, 16)


def test_add_obstacle() -> None:
    custom_map = CustomMap()

    custom_map.add_obstacle((5, 5), (7, 8))

    assert custom_map.is_blocked((6, 6))


def test_reject_start_inside_obstacle() -> None:
    custom_map = CustomMap()
    custom_map.add_obstacle((4, 4), (6, 6))

    assert not custom_map.set_start((5, 5))
    assert custom_map.start is None


def test_reject_goal_inside_obstacle() -> None:
    custom_map = CustomMap()
    custom_map.add_obstacle((4, 4), (6, 6))

    assert not custom_map.set_goal((5, 5))
    assert custom_map.goal is None


def test_detect_impossible_route() -> None:
    custom_map = _valid_open_map()
    for col in range(1, custom_map.cols - 1):
        custom_map.add_wall((15, col))

    result = MapValidator().validate(custom_map)

    assert not result.valid
    assert "No valid route exists between START and GOAL." in result.messages


def test_validate_reachable_map() -> None:
    result = MapValidator().validate(_valid_open_map())

    assert result.valid
    assert result.path


def test_save_map_json() -> None:
    custom_map = _valid_open_map()
    custom_map.name = "My House"

    with TemporaryDirectory() as temp_dir:
        path = save_custom_map(custom_map, Path(temp_dir))

        assert path.name == "my_house.json"
        assert '"name": "My House"' in path.read_text(encoding="utf-8")


def test_load_saved_map() -> None:
    custom_map = _valid_open_map()
    custom_map.name = "Research Lab"

    with TemporaryDirectory() as temp_dir:
        path = save_custom_map(custom_map, Path(temp_dir))
        loaded = load_custom_map(path)

    assert loaded.name == "Research Lab"
    assert loaded.start == custom_map.start
    assert loaded.goal == custom_map.goal


def test_saved_and_loaded_maps_contain_same_important_data() -> None:
    custom_map = _valid_open_map()
    custom_map.add_obstacle((10, 8), (12, 10))
    custom_map.add_semantic_location("Kitchen", (5, 5))

    with TemporaryDirectory() as temp_dir:
        loaded = load_custom_map(save_custom_map(custom_map, Path(temp_dir)))

    assert loaded.walls == custom_map.walls
    assert loaded.obstacles == custom_map.obstacles
    assert loaded.semantic_locations == custom_map.semantic_locations


def test_semantic_location_saved_correctly() -> None:
    custom_map = _valid_open_map()
    custom_map.add_semantic_location("Charging Station", (4, 4))

    with TemporaryDirectory() as temp_dir:
        loaded = load_custom_map(save_custom_map(custom_map, Path(temp_dir)))

    assert loaded.semantic_locations["charging station"] == (4, 4)


def test_invalid_semantic_location_rejected() -> None:
    custom_map = _valid_open_map()
    custom_map.add_wall((8, 8))

    assert not custom_map.add_semantic_location("Kitchen", (8, 8))
    assert "kitchen" not in custom_map.semantic_locations


def test_export_import_map_json_is_portable() -> None:
    custom_map = _valid_open_map()
    custom_map.name = "Portable Map"

    with TemporaryDirectory() as temp_dir:
        export_path = export_custom_map(custom_map, Path(temp_dir) / "portable_map.json")
        loaded = import_custom_map(export_path)
        exported_text = export_path.read_text(encoding="utf-8")

    assert loaded.name == "Portable Map"
    assert loaded.start == custom_map.start
    assert "C:\\" not in exported_text


def test_custom_map_converts_to_scenario_correctly() -> None:
    custom_map = _valid_open_map()
    custom_map.name = "Hospital Wing"

    scenario = custom_map.to_scenario()

    assert scenario.name == "Hospital Wing"
    assert scenario.start_cell == custom_map.start
    assert scenario.goal_cell == custom_map.goal


def test_astar_can_navigate_valid_custom_map() -> None:
    custom_map = _valid_open_map()
    scenario = custom_map.to_scenario()
    planner = AStarPlanner(scenario.copy_grid(), cell_size=custom_map.resolution)

    path = planner.plan(scenario.start_cell, scenario.goal_cell)

    assert path
    assert path[0] == scenario.start_cell
    assert path[-1] == scenario.goal_cell


def test_custom_semantic_locations_work_with_mission_parser() -> None:
    custom_map = _valid_open_map()
    custom_map.name = "My House Test"
    custom_map.add_semantic_location("Kitchen", (5, 5))
    custom_map.add_semantic_location("Bedroom", (20, 12))
    register_custom_locations(custom_map.name, custom_map.semantic_locations)

    mission = MissionParser().parse("Go to kitchen then bedroom", custom_map.name)

    assert [task.target_name for task in mission.tasks] == ["Kitchen", "Bedroom"]


def _valid_open_map() -> CustomMap:
    custom_map = CustomMap(name="Valid Custom Map")
    assert custom_map.set_start((3, 3))
    assert custom_map.set_goal((26, 16))
    return custom_map
