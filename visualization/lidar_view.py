LIDAR_VIEW_OFF = 0
LIDAR_VIEW_MINIMAL = 1
LIDAR_VIEW_FULL = 2

LIDAR_VIEW_NAMES = {
    LIDAR_VIEW_OFF: "Off",
    LIDAR_VIEW_MINIMAL: "Minimal",
    LIDAR_VIEW_FULL: "Full",
}


def next_lidar_view_mode(mode: int) -> int:
    return (mode + 1) % 3


def visible_lidar_rays(rays: list[object], mode: int, target_count: int = 18) -> list[object]:
    if mode == LIDAR_VIEW_OFF:
        return []
    if mode == LIDAR_VIEW_FULL:
        return rays
    if not rays:
        return []

    step = max(1, len(rays) // target_count)
    return rays[::step]
