from __future__ import annotations

import pygame

from ui.components.button import draw_button
from ui.components.card import draw_card
from ui.theme import Theme


def draw_modal(
    screen: pygame.Surface,
    rect: pygame.Rect,
    title: str,
    message: str,
    title_font: pygame.font.Font,
    body_font: pygame.font.Font,
    mouse_pos: tuple[int, int],
    buttons: list[tuple[str, pygame.Rect, str, str]],
) -> dict[str, pygame.Rect]:
    overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
    overlay.fill(Theme.OVERLAY)
    screen.blit(overlay, (0, 0))
    draw_card(screen, rect)
    title_surface = title_font.render(title, True, Theme.TEXT_PRIMARY)
    screen.blit(title_surface, (rect.x + 24, rect.y + 22))
    screen.blit(body_font.render(message, True, Theme.TEXT_SECONDARY), (rect.x + 24, rect.y + 64))
    rects: dict[str, pygame.Rect] = {}
    for name, button_rect, label, variant in buttons:
        rects[name] = button_rect
        draw_button(screen, button_rect, label, body_font, mouse_pos, variant=variant)
    return rects
