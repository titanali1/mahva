"""Color themes used by the text-card renderer."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    key: str
    label: str
    bg_top: tuple[int, int, int]
    bg_bottom: tuple[int, int, int]
    text: tuple[int, int, int]
    muted: tuple[int, int, int]
    accent: tuple[int, int, int]
    scrim: int = 205          # 0..255, strength of the dark scrim over images
    light: bool = False       # light theme -> dark text on light background


THEMES: dict[str, Theme] = {
    "midnight": Theme(
        key="midnight",
        label="نیمه‌شب",
        bg_top=(13, 20, 38),
        bg_bottom=(4, 7, 16),
        text=(243, 246, 252),
        muted=(160, 176, 205),
        accent=(84, 176, 255),
    ),
    "sunset": Theme(
        key="sunset",
        label="غروب",
        bg_top=(58, 22, 45),
        bg_bottom=(14, 9, 22),
        text=(255, 246, 240),
        muted=(226, 178, 168),
        accent=(255, 138, 92),
    ),
    "forest": Theme(
        key="forest",
        label="جنگل",
        bg_top=(12, 36, 33),
        bg_bottom=(5, 15, 18),
        text=(238, 248, 244),
        muted=(156, 196, 182),
        accent=(94, 214, 158),
    ),
    "amber": Theme(
        key="amber",
        label="کهربا",
        bg_top=(38, 27, 12),
        bg_bottom=(12, 9, 5),
        text=(255, 248, 235),
        muted=(216, 190, 148),
        accent=(255, 196, 84),
    ),
    "paper": Theme(
        key="paper",
        label="کاغذی (روشن)",
        bg_top=(250, 248, 244),
        bg_bottom=(228, 226, 222),
        text=(26, 28, 34),
        muted=(96, 102, 116),
        accent=(196, 84, 44),
        scrim=170,
        light=True,
    ),
    "ink": Theme(
        key="ink",
        label="مرکب (روشن)",
        bg_top=(240, 244, 250),
        bg_bottom=(214, 224, 238),
        text=(16, 26, 44),
        muted=(84, 100, 126),
        accent=(28, 108, 200),
        scrim=165,
        light=True,
    ),
}

DEFAULT_THEME = "midnight"


def get_theme(name: str | None) -> Theme:
    if not name:
        return THEMES[DEFAULT_THEME]
    return THEMES.get(name.strip().lower(), THEMES[DEFAULT_THEME])


def theme_choices() -> list[dict[str, str]]:
    return [{"key": t.key, "label": t.label} for t in THEMES.values()]
