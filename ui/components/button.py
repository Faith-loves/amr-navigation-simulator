from __future__ import annotations

import pygame

from ui.theme import Radius, Theme


def draw_button(
    screen: pygame.Surface,
    rect: pygame.Rect,
    label: str,
    font: pygame.font.Font,
    mouse_pos: tuple[int, int],
    *,
    variant: str = "secondary",
    selected: bool = False,
    disabled: bool = False,
) -> None:
    hovered = rect.collidepoint(mouse_pos) and not disabled
    if disabled:
        fill = Theme.SURFACE
        border = Theme.BORDER
        text_color = Theme.TEXT_MUTED
    elif variant == "primary":
        fill = Theme.PRIMARY_HOVER if hovered else Theme.PRIMARY
        border = Theme.PRIMARY_HOVER if hovered else Theme.PRIMARY
        text_color = Theme.TEXT_PRIMARY
    elif variant == "danger":
        fill = Theme.DANGER if hovered or selected else Theme.SURFACE_ALT
        border = Theme.DANGER
        text_color = Theme.TEXT_PRIMARY
    elif variant == "ghost":
        fill = Theme.SURFACE_ALT if hovered or selected else Theme.BACKGROUND
        border = Theme.PRIMARY if selected else fill
        text_color = Theme.TEXT_PRIMARY if hovered or selected else Theme.TEXT_SECONDARY
    else:
        fill = Theme.SURFACE_ALT if hovered or selected else Theme.SURFACE
        border = Theme.PRIMARY if selected else Theme.BORDER
        text_color = Theme.TEXT_PRIMARY

    pygame.draw.rect(screen, fill, rect, border_radius=Radius.MD)
    pygame.draw.rect(screen, border, rect, 1, border_radius=Radius.MD)
    surface = font.render(label, True, text_color)
    screen.blit(surface, (rect.centerx - surface.get_width() // 2, rect.centery - surface.get_height() // 2))
