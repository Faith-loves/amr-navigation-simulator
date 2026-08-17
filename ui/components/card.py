from __future__ import annotations

import pygame

from ui.theme import Radius, Spacing, Theme


def draw_card(
    screen: pygame.Surface,
    rect: pygame.Rect,
    title: str = "",
    font: pygame.font.Font | None = None,
    *,
    selected: bool = False,
    hovered: bool = False,
    fill: tuple[int, int, int] | None = None,
) -> None:
    background = fill or (Theme.SURFACE_ALT if hovered else Theme.CARD if selected else Theme.SURFACE)
    border = Theme.PRIMARY if selected else Theme.BORDER
    pygame.draw.rect(screen, background, rect, border_radius=Radius.LG)
    pygame.draw.rect(screen, border, rect, 1, border_radius=Radius.LG)
    if title and font is not None:
        screen.blit(font.render(title, True, Theme.TEXT_PRIMARY), (rect.x + Spacing.CARD, rect.y + Spacing.MD))
