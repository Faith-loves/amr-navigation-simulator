from __future__ import annotations

import pygame

from ui.theme import Radius, Theme


def draw_progress_bar(
    screen: pygame.Surface,
    rect: pygame.Rect,
    value: float,
    *,
    fill: tuple[int, int, int] = Theme.ACCENT,
    background: tuple[int, int, int] = Theme.SURFACE_ALT,
) -> None:
    clamped = max(0.0, min(1.0, value))
    pygame.draw.rect(screen, background, rect, border_radius=Radius.SM)
    if clamped > 0:
        filled = pygame.Rect(rect.x, rect.y, int(rect.width * clamped), rect.height)
        pygame.draw.rect(screen, fill, filled, border_radius=Radius.SM)
    pygame.draw.rect(screen, Theme.BORDER, rect, 1, border_radius=Radius.SM)
