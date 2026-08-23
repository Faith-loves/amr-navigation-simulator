from pathlib import Path

from ui.app_state import AppController, MODE_AUTONOMOUS
from utils import startup_validation
from visualization.lidar_view import LIDAR_VIEW_MINIMAL


def test_version_file_marks_portfolio_release() -> None:
    assert Path("VERSION").read_text().strip() == "1.0.0"


def test_readme_uses_required_portfolio_sections() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    for section in [
        "# AMR Navigation Simulator",
        "## Demo Preview",
        "## Core Capabilities",
        "## Architecture",
        "## Algorithms",
        "## Scenarios",
        "## AI Mission System",
        "## Experiment Mode",
        "## Installation",
        "## Controls",
        "## Running Tests",
        "## Example Experiment Results",
        "## Limitations",
        "## Future Work",
    ]:
        assert section in readme
    assert "software simulation" in readme
    assert "Demo video: coming soon" in readme


def test_docs_include_architecture_and_data_flow_diagrams() -> None:
    architecture = Path("docs/ARCHITECTURE.md").read_text(encoding="utf-8")

    assert "flowchart TD" in architecture
    assert "flowchart LR" in architecture
    assert "LiDAR" in architecture
    assert "EKF" in architecture
    assert "Experiment Runner" in architecture


def test_algorithms_doc_covers_required_topics() -> None:
    algorithms = Path("docs/ALGORITHMS.md").read_text(encoding="utf-8")

    for topic in [
        "Unicycle Kinematics",
        "LiDAR Ray Casting",
        "Gaussian Noise",
        "Occupancy Mapping",
        "A*",
        "Dijkstra",
        "RRT*",
        "EKF Localization",
        "Path Smoothing",
        "Replanning",
        "Frontier Exploration",
    ]:
        assert topic in algorithms


def test_experiments_doc_explains_export_and_limits() -> None:
    experiments = Path("docs/EXPERIMENTS.md").read_text(encoding="utf-8")

    assert "random seed" in experiments.lower()
    assert "runs.csv" in experiments
    assert "summary.csv" in experiments
    assert "Simulation-based comparisons" in experiments


def test_screenshot_and_example_placeholders_exist() -> None:
    assert Path("docs/screenshots/README.md").exists()
    assert Path("experiment_results/example/README.md").exists()


def test_requirements_are_minimal_and_used() -> None:
    requirements = Path("requirements.txt").read_text(encoding="utf-8").splitlines()

    assert requirements == ["numpy", "fastapi", "pydantic"]
    desktop_requirements = Path("requirements-desktop.txt").read_text(encoding="utf-8").splitlines()
    assert desktop_requirements == ["-r requirements.txt", "pygame", "pytest", "httpx2"]


def test_demo_mode_configures_strong_default() -> None:
    controller = AppController()

    controller.configure_demo_mode()

    scenario = controller.scenario_manager.scenarios[controller.settings.scenario_index]
    assert scenario.name == "Warehouse"
    assert controller.settings.planner == "A*"
    assert controller.settings.mode == MODE_AUTONOMOUS
    assert controller.settings.lidar_view_mode == LIDAR_VIEW_MINIMAL
    assert controller.settings.dynamic_obstacles_enabled
    assert controller.settings.show_localization
    assert controller.settings.battery_simulation_enabled
    assert controller.settings.auto_return_to_charger


def test_startup_validation_creates_required_directories(tmp_path) -> None:
    original = startup_validation.REQUIRED_DIRECTORIES
    startup_validation.REQUIRED_DIRECTORIES = (
        tmp_path / "logs",
        tmp_path / "reports",
        tmp_path / "custom_maps",
        tmp_path / "experiment_results",
        tmp_path / "docs" / "screenshots",
    )
    try:
        startup_validation.ensure_startup_directories()
    finally:
        required = startup_validation.REQUIRED_DIRECTORIES
        startup_validation.REQUIRED_DIRECTORIES = original

    for directory in required:
        assert directory.exists()
