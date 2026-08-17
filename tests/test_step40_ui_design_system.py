from pathlib import Path


def test_theme_defines_required_design_tokens() -> None:
    source = Path("ui/theme.py").read_text()

    for token in [
        "BACKGROUND",
        "SURFACE",
        "CARD",
        "BORDER",
        "PRIMARY",
        "ACCENT",
        "WARNING",
        "DANGER",
        "TEXT_PRIMARY",
        "TEXT_SECONDARY",
        "GRID",
        "UNKNOWN_MAP",
        "FREE_MAP",
        "OBSTACLE",
    ]:
        assert token in source


def test_reusable_component_files_exist() -> None:
    component_dir = Path("ui/components")

    for filename in [
        "button.py",
        "card.py",
        "badge.py",
        "tabs.py",
        "text_input.py",
        "progress_bar.py",
        "toast.py",
        "modal.py",
        "metric_card.py",
        "keycap.py",
    ]:
        assert (component_dir / filename).exists()


def test_major_screens_use_shared_theme_and_components() -> None:
    files = [
        Path("ui/home_screen.py"),
        Path("ui/results_screen.py"),
        Path("ui/experiment_screens.py"),
        Path("ui/experiment_results_screen.py"),
        Path("editor/map_editor.py"),
        Path("visualization/pygame_dashboard.py"),
    ]

    for path in files:
        source = path.read_text()
        assert "Theme" in source
        assert "ui.components" in source


def test_simulation_sidebar_keeps_required_tabs() -> None:
    source = Path("visualization/pygame_dashboard.py").read_text()

    for tab in ["STATUS", "METRICS", "CONTROLS", "MISSION"]:
        assert tab in source
    assert "draw_tabs" in source


def test_keyboard_controls_use_keycaps() -> None:
    source = Path("visualization/pygame_dashboard.py").read_text()

    assert "draw_keycap" in source
    for key in ["SPACE", "ESC", "RRT*"]:
        assert key in source


def test_mission_input_uses_text_input_component() -> None:
    source = Path("visualization/pygame_dashboard.py").read_text()

    assert "draw_text_input" in source
    assert "MISSION COMMAND" in source


def test_modal_component_is_used_for_map_editor_confirmations() -> None:
    source = Path("editor/map_editor.py").read_text()

    assert "draw_modal" in source
    assert "Unsaved changes" in source


def test_results_screen_uses_metric_cards_not_metric_wall() -> None:
    source = Path("ui/results_screen.py").read_text()

    assert "draw_metric_card" in source
    assert "self._rows(summary)[:6]" in source
