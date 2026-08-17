from __future__ import annotations

import pygame

from ui.components.card import draw_card
from ui.theme import Spacing, Theme


def draw_metric_card(
    screen: pygame.Surface,
    rect: pygame.Rect,
    value: str,
    label: str,
    value_font: pygame.font.Font,
    label_font: pygame.font.Font,
    *,
    tone: tuple[int, int, int] = Theme.TEXT_PRIMARY,
) -> None:
    draw_card(screen, rect)
    screen.blit(value_font.render(value, True, tone), (rect.x + Spacing.MD, rect.y + 10))
    screen.blit(label_font.render(label, True, Theme.TEXT_SECONDARY), (rect.x + Spacing.MD, rect.y + 38))
