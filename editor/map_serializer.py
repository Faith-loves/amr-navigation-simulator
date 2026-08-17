from __future__ import annotations

import json
import re
from pathlib import Path

from editor.editor_state import CustomMap


CUSTOM_MAPS_DIR = Path("custom_maps")


def save_custom_map(custom_map: CustomMap, directory: Path = CUSTOM_MAPS_DIR) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{_slug(custom_map.name)}.json"
    path.write_text(json.dumps(to_json_data(custom_map), indent=2), encoding="utf-8")
    return path


def export_custom_map(custom_map: CustomMap, path: Path | str) -> Path:
    export_path = Path(path)
    export_path.parent.mkdir(parents=True, exist_ok=True)
    export_path.write_text(json.dumps(to_json_data(custom_map), indent=2), encoding="utf-8")
    return export_path


def import_custom_map(path: Path | str) -> CustomMap:
    return load_custom_map(path)


def load_custom_map(path: Path | str) -> CustomMap:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return from_json_data(data)


def list_custom_maps(directory: Path = CUSTOM_MAPS_DIR) -> list[Path]:
    if not directory.exists():
        return []
    return sorted(directory.glob("*.json"), key=lambda path: path.stem.lower())


def to_json_data(custom_map: CustomMap) -> dict:
    return {
        "name": custom_map.name,
        "width": custom_map.cols,
        "height": custom_map.rows,
        "resolution": custom_map.resolution,
        "start": list(custom_map.start) if custom_map.start else None,
        "goal": list(custom_map.goal) if custom_map.goal else None,
        "walls": [list(cell) for cell in sorted(custom_map.walls)],
        "obstacles": [list(obstacle) for obstacle in custom_map.obstacles],
        "semantic_locations": {
            name: list(cell)
            for name, cell in sorted(custom_map.semantic_locations.items())
        },
    }


def from_json_data(data: dict) -> CustomMap:
    custom_map = CustomMap(
        name=data.get("name", "Untitled Environment"),
        rows=int(data.get("height", 30)),
        cols=int(data.get("width", 20)),
        resolution=int(data.get("resolution", 20)),
    )
    custom_map.walls = {tuple(cell) for cell in data.get("walls", [])}
    custom_map.obstacles = [tuple(obstacle) for obstacle in data.get("obstacles", [])]
    custom_map.start = tuple(data["start"]) if data.get("start") else None
    custom_map.goal = tuple(data["goal"]) if data.get("goal") else None
    custom_map.semantic_locations = {
        str(name).strip().lower(): tuple(cell)
        for name, cell in data.get("semantic_locations", {}).items()
    }
    return custom_map


def _slug(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return slug or "custom_environment"
