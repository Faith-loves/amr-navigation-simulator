from __future__ import annotations

from pathlib import Path


REQUIRED_DIRECTORIES = (
    Path("logs"),
    Path("reports"),
    Path("custom_maps"),
    Path("experiment_results"),
    Path("docs/screenshots"),
)


def ensure_startup_directories() -> None:
    for directory in REQUIRED_DIRECTORIES:
        directory.mkdir(parents=True, exist_ok=True)
