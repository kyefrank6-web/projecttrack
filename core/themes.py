from __future__ import annotations

from typing import TypedDict


class ThemeSpec(TypedDict):
    id: str
    name: str
    primary: str
    primary_dark: str
    secondary: str
    accent: str


THEMES: dict[str, ThemeSpec] = {
    "royal_blue": {
        "id": "royal_blue",
        "name": "Royal Blue",
        "primary": "#0b5ed7",
        "primary_dark": "#084298",
        "secondary": "#6610f2",
        "accent": "#198754",
    },
    "forest_green": {
        "id": "forest_green",
        "name": "Forest Green",
        "primary": "#198754",
        "primary_dark": "#146c43",
        "secondary": "#20c997",
        "accent": "#0d6efd",
    },
    "purple_violet": {
        "id": "purple_violet",
        "name": "Purple Violet",
        "primary": "#6f42c1",
        "primary_dark": "#59359a",
        "secondary": "#d63384",
        "accent": "#6610f2",
    },
    "sunset_orange": {
        "id": "sunset_orange",
        "name": "Sunset Orange",
        "primary": "#fd7e14",
        "primary_dark": "#ca6510",
        "secondary": "#ffc107",
        "accent": "#dc3545",
    },
    "crimson_red": {
        "id": "crimson_red",
        "name": "Crimson Red",
        "primary": "#dc3545",
        "primary_dark": "#b02a37",
        "secondary": "#fd7e14",
        "accent": "#6f42c1",
    },
    "teal_ocean": {
        "id": "teal_ocean",
        "name": "Teal Ocean",
        "primary": "#0dcaf0",
        "primary_dark": "#0aa2c0",
        "secondary": "#0d6efd",
        "accent": "#198754",
    },
    "navy_gold": {
        "id": "navy_gold",
        "name": "Navy & Gold",
        "primary": "#1e3a5f",
        "primary_dark": "#152a45",
        "secondary": "#ffc107",
        "accent": "#0d6efd",
    },
    "rose_pink": {
        "id": "rose_pink",
        "name": "Rose Pink",
        "primary": "#d63384",
        "primary_dark": "#ab296a",
        "secondary": "#e685b5",
        "accent": "#6f42c1",
    },
}

DEFAULT_THEME_KEY = "royal_blue"


def get_theme(key: str | None) -> ThemeSpec:
    if key and key in THEMES:
        return THEMES[key]
    return THEMES[DEFAULT_THEME_KEY]


def theme_choices() -> list[tuple[str, str]]:
    return [(t["id"], t["name"]) for t in THEMES.values()]
