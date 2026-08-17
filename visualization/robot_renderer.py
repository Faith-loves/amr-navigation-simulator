import math

import pygame

from environment.grid_map import ROBOT_RADIUS
from robot.state import RobotState
from ui.theme import Theme


class RobotRenderer:
    def __init__(self) -> None:
        self.body_color = Theme.PRIMARY
        self.body_shadow_color = (18, 27, 42)
        self.panel_color = Theme.PRIMARY_HOVER
        self.front_color = Theme.TEXT_PRIMARY
        self.wheel_color = Theme.BACKGROUND
        self.wheel_detail_color = Theme.TEXT_MUTED
        self.lidar_color = Theme.SURFACE
        self.lidar_glow_color = Theme.ACCENT
        self.manual_status_color = Theme.PRIMARY_HOVER
        self.auto_status_color = Theme.ACCENT
        self.explore_status_color = Theme.WARNING
        self.success_status_color = Theme.ACCENT
        self.warning_status_color = Theme.DANGER
        self.outline_color = Theme.TEXT_PRIMARY

    def draw(
        self,
        screen: pygame.Surface,
        robot_state: RobotState,
        x_offset: int,
        y_offset: int,
        autonomous_mode: bool,
        exploration_mode: bool,
        collision_status: bool,
        mission_complete: bool,
    ) -> None:
        robot_surface = self._build_robot_surface(
            autonomous_mode=autonomous_mode,
            exploration_mode=exploration_mode,
            collision_status=collision_status,
            mission_complete=mission_complete,
        )
        degrees = -math.degrees(robot_state.theta)
        rotated = pygame.transform.rotate(robot_surface, degrees)
        center = (x_offset + int(robot_state.x), y_offset + int(robot_state.y))
        rect = rotated.get_rect(center=center)
        screen.blit(rotated, rect)

    def _build_robot_surface(
        self,
        autonomous_mode: bool,
        exploration_mode: bool,
        collision_status: bool,
        mission_complete: bool,
    ) -> pygame.Surface:
        width = 30
        height = 24
        surface = pygame.Surface((width, height), pygame.SRCALPHA)

        body_rect = pygame.Rect(4, 4, 22, 16)
        pygame.draw.rect(surface, self.body_shadow_color, body_rect.move(1, 1), border_radius=5)
        pygame.draw.rect(surface, self.body_color, body_rect, border_radius=5)
        pygame.draw.rect(surface, self.outline_color, body_rect, 1, border_radius=5)

        top_wheel = pygame.Rect(7, 1, 14, 5)
        bottom_wheel = pygame.Rect(7, height - 6, 14, 5)
        pygame.draw.rect(surface, self.wheel_color, top_wheel, border_radius=2)
        pygame.draw.rect(surface, self.wheel_color, bottom_wheel, border_radius=2)
        pygame.draw.line(surface, self.wheel_detail_color, (9, 3), (19, 3), 1)
        pygame.draw.line(surface, self.wheel_detail_color, (9, height - 4), (19, height - 4), 1)

        front_points = [(25, 7), (29, height // 2), (25, height - 7)]
        pygame.draw.polygon(surface, self.front_color, front_points)
        pygame.draw.line(surface, self.body_shadow_color, (24, 8), (24, height - 8), 1)

        pygame.draw.rect(surface, self.panel_color, (8, 8, 8, 8), border_radius=2)
        lidar_center = (17, height // 2)
        pygame.draw.circle(surface, self.lidar_glow_color, lidar_center, ROBOT_RADIUS - 2, 1)
        pygame.draw.circle(surface, self.lidar_color, lidar_center, 4)
        pygame.draw.circle(surface, self.lidar_glow_color, lidar_center, 2)

        status_color = self._status_color(
            autonomous_mode=autonomous_mode,
            exploration_mode=exploration_mode,
            collision_status=collision_status,
            mission_complete=mission_complete,
        )
        pygame.draw.circle(surface, status_color, (10, 7), 2)
        pygame.draw.circle(surface, self.outline_color, (10, 7), 2, 1)

        return surface

    def _status_color(
        self,
        autonomous_mode: bool,
        exploration_mode: bool,
        collision_status: bool,
        mission_complete: bool,
    ) -> tuple[int, int, int]:
        if collision_status:
            return self.warning_status_color
        if mission_complete:
            return self.success_status_color
        if exploration_mode:
            return self.explore_status_color
        if autonomous_mode:
            return self.auto_status_color
        return self.manual_status_color
