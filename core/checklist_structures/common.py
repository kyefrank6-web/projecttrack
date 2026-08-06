from __future__ import annotations

from typing import Union

CHECKBOX_MAX_RATING = 1
HEADER_MAX_RATING = 0

ObsItem = Union[str, tuple[str, int]]

OBSERVATION_RATING_LABELS_CHECKBOX = [
    (0, "Not met"),
    (1, "Met"),
]

OBSERVATION_RATING_LABELS_SCALE = [
    (0, "Not demonstrated"),
    (1, "Partially demonstrated"),
    (2, "Adequately demonstrated"),
    (3, "Excellently demonstrated"),
]


def parse_observation_item(item: ObsItem) -> tuple[str, int]:
    if isinstance(item, tuple):
        return item[0], item[1]
    return item, CHECKBOX_MAX_RATING
