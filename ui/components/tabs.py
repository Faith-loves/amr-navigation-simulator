from __future__ import annotations

import pygame

from ui.theme import Radius, Theme


def draw_tabs(
    screen: pygame.Surface,
    tabs: list[str],
    active: str,
    start: tuple[int, int],
    width: int,
    font: pygame.font.Font,
    mouse_pos: tuple[int, int],
) -> dict[str, pygame.Rect]:
    rects: dict[str, pygame.Rect] = {}
    tab_width = width // max(1, len(tabs))
    x, y = start
    for index, tab in enumerate(tabs):
        rect = pygame.Rect(x + index * tab_width, y, tab_width - 4, 30)
        rects[tab] = rect
        selected = active == tab
        hovered = rect.collidepoint(mouse_pos)
        fill = Theme.SURFACE_ALT if hovered or selected else Theme.SURFACE
        pygame.draw.rect(screen, fill, rect, border_radius=Radius.SM)
        if selected:
            indicator = pygame.Rect(rect.x + 10, rect.bottom - 3, rect.width - 20, 3)
            pygame.draw.rect(screen, Theme.PRIMARY, indicator, border_radius=2)
        pygame.draw.rect(screen, Theme.BORDER, rect, 1, border_radius=Radius.SM)
        color = Theme.TEXT_PRIMARY if selected else Theme.TEXT_SECONDARY
        surface = font.render(tab, True, color)
        screen.blit(surface, (rect.centerx - surface.get_width() // 2, rect.centery - surface.get_height() // 2 - 1))
    return rects
