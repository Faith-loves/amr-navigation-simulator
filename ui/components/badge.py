from __future__ import annotations

import pygame

from ui.theme import Radius, Theme


def draw_badge(
    screen: pygame.Surface,
    rect: pygame.Rect,
    label: str,
    font: pygame.font.Font,
    *,
    tone: str = "neutral",
) -> None:
    tones = {
        "primary": Theme.PRIMARY,
        "success": Theme.ACCENT,
        "warning": Theme.WARNING,
        "danger": Theme.DANGER,
        "neutral": Theme.SURFACE_ALT,
    }
    fill = tones.get(tone, Theme.SURFACE_ALT)
    text_color = Theme.BACKGROUND if tone in {"success", "warning"} else Theme.TEXT_PRIMARY
    pygame.draw.rect(screen, fill, rect, border_radius=Radius.SM)
    pygame.draw.rect(screen, Theme.BORDER, rect, 1, border_radius=Radius.SM)
    surface = font.render(label, True, text_color)
    screen.blit(surface, (rect.centerx - surface.get_width() // 2, rect.centery - surface.get_height() // 2))
