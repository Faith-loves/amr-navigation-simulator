from __future__ import annotations

from dataclasses import dataclass

import pygame

from ui.components.card import draw_card
from ui.theme import Theme


@dataclass
class Toast:
    message: str
    tone: str = "neutral"
    ttl: float = 3.0


class ToastManager:
    def __init__(self) -> None:
        self.toasts: list[Toast] = []

    def push(self, message: str, tone: str = "neutral", ttl: float = 3.0) -> None:
        self.toasts.append(Toast(message, tone, ttl))

    def update(self, dt: float) -> None:
        for toast in self.toasts:
            toast.ttl -= dt
        self.toasts = [toast for toast in self.toasts if toast.ttl > 0]

    def draw(self, screen: pygame.Surface, font: pygame.font.Font) -> None:
        y = 76
        for toast in self.toasts[-3:]:
            surface = font.render(toast.message, True, _tone_color(toast.tone))
            rect = pygame.Rect(screen.get_width() - surface.get_width() - 44, y, surface.get_width() + 24, 34)
            draw_card(screen, rect)
            screen.blit(surface, (rect.x + 12, rect.centery - surface.get_height() // 2))
            y += 42


def _tone_color(tone: str) -> tuple[int, int, int]:
    if tone == "success":
        return Theme.ACCENT
    if tone == "warning":
        return Theme.WARNING
    if tone == "danger":
        return Theme.DANGER
    return Theme.TEXT_PRIMARY
