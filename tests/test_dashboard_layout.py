from pathlib import Path


DASHBOARD_SOURCE = Path("visualization/pygame_dashboard.py").read_text(encoding="utf-8")


def test_dashboard_has_required_tabs() -> None:
    for tab in ["STATUS", "METRICS", "CONTROLS", "MISSION"]:
        assert f'"{tab}"' in DASHBOARD_SOURCE


def test_dashboard_defaults_to_status_tab() -> None:
    assert 'self.active_metrics_tab = "STATUS"' in DASHBOARD_SOURCE


def test_controls_tab_contains_all_visible_controls() -> None:
    for control in [
        "W / Up",
        "S / Down",
        "A / Left",
        "D / Right",
        "SPACE",
        "F",
        "E",
        "V",
        "1",
        "2",
        "3",
        "L",
        "R",
        "ESC",
        "K",
    ]:
        assert f'"{control}"' in DASHBOARD_SOURCE


def test_dashboard_supports_f_key_tab_switching() -> None:
    for key in ["K_F1", "K_F2", "K_F3", "K_F4"]:
        assert f"pygame.{key}" in DASHBOARD_SOURCE


def test_dashboard_clips_tab_content_for_internal_scroll() -> None:
    assert "self.screen.set_clip(content_rect)" in DASHBOARD_SOURCE
    assert "_scroll_active_tab" in DASHBOARD_SOURCE
