from __future__ import annotations

import pygame

from ui.theme import Radius, Theme


def draw_text_input(
    screen: pygame.Surface,
    rect: pygame.Rect,
    text: str,
    placeholder: str,
    font: pygame.font.Font,
    *,
    focused: bool = False,
) -> None:
    pygame.draw.rect(screen, Theme.SURFACE, rect, border_radius=Radius.MD)
    pygame.draw.rect(screen, Theme.PRIMARY if focused else Theme.BORDER, rect, 1, border_radius=Radius.MD)
    shown = text or placeholder
    color = Theme.TEXT_PRIMARY if text else Theme.TEXT_MUTED
    surface = font.render(shown, True, color)
    screen.blit(surface, (rect.x + 10, rect.centery - surface.get_height() // 2))
