from __future__ import annotations

import pygame

from ui.theme import Radius, Theme


def draw_keycap(screen: pygame.Surface, rect: pygame.Rect, label: str, font: pygame.font.Font) -> None:
    pygame.draw.rect(screen, Theme.SURFACE_ALT, rect, border_radius=Radius.SM)
    pygame.draw.rect(screen, Theme.BORDER, rect, 1, border_radius=Radius.SM)
    surface = font.render(label, True, Theme.TEXT_PRIMARY)
    screen.blit(surface, (rect.centerx - surface.get_width() // 2, rect.centery - surface.get_height() // 2))
