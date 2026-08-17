from __future__ import annotations

from dataclasses import dataclass

import pygame


Color = tuple[int, int, int]


class Theme:
    BACKGROUND: Color = (9, 13, 26)
    SURFACE: Color = (16, 23, 37)
    SURFACE_ALT: Color = (23, 34, 54)
    CARD: Color = (18, 28, 46)
    BORDER: Color = (42, 58, 84)
    PRIMARY: Color = (73, 132, 245)
    PRIMARY_HOVER: Color = (103, 157, 255)
    ACCENT: Color = (34, 211, 166)
    WARNING: Color = (246, 185, 74)
    DANGER: Color = (240, 100, 100)
    TEXT_PRIMARY: Color = (244, 247, 251)
    TEXT_SECONDARY: Color = (168, 178, 194)
    TEXT_MUTED: Color = (104, 117, 138)
    GRID: Color = (31, 42, 60)
    UNKNOWN_MAP: Color = (38, 49, 65)
    FREE_MAP: Color = (70, 86, 106)
    OBSTACLE: Color = (215, 223, 233)
    OVERLAY: tuple[int, int, int, int] = (5, 8, 14, 190)


class Spacing:
    XS = 4
    SM = 8
    MD = 12
    LG = 16
    XL = 24
    XXL = 32
    PAGE = 24
    CARD = 16
    GAP = 12


class Radius:
    SM = 6
    MD = 8
    LG = 10
    XL = 12


class Typography:
    APP_TITLE = 32
    PAGE_TITLE = 24
    SECTION_TITLE = 18
    BODY = 15
    SMALL = 13
    METRIC = 20


@dataclass(frozen=True)
class FontSet:
    app_title: pygame.font.Font
    page_title: pygame.font.Font
    section: pygame.font.Font
    body: pygame.font.Font
    small: pygame.font.Font
    metric: pygame.font.Font


def load_fonts() -> FontSet:
    font_name = "Arial"
    return FontSet(
        app_title=pygame.font.SysFont(font_name, Typography.APP_TITLE),
        page_title=pygame.font.SysFont(font_name, Typography.PAGE_TITLE),
        section=pygame.font.SysFont(font_name, Typography.SECTION_TITLE),
        body=pygame.font.SysFont(font_name, Typography.BODY),
        small=pygame.font.SysFont(font_name, Typography.SMALL),
        metric=pygame.font.SysFont(font_name, Typography.METRIC),
    )


def with_alpha(color: Color, alpha: int) -> tuple[int, int, int, int]:
    return color[0], color[1], color[2], alpha
