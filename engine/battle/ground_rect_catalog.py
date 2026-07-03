# engine/battle/ground_rect_catalog.py
#
# Per-battle-background ground bounding box, loaded from scenario YAML.
# Anchors enemy sprite placement to the actual visible ground area of each
# background image instead of a fixed screen-center offset.

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from engine.io.yaml_loader import load_yaml_required

_REQUIRED_RECT_FIELDS = ("x", "y", "width", "height")

# Every background id ends in its own pixel dimensions, e.g.
# "zone7-bg-1280x468" -> 1280x468. Used to catch a ground_rect that
# overshoots the actual image bounds at load time instead of producing a
# feet position past the real screen edge at runtime.
_DIM_SUFFIX_RE = re.compile(r"-(\d+)x(\d+)$")


@dataclass(frozen=True)
class GroundRect:
    """A bounding box in the background image's own 1280x468 pixel space."""
    x: int
    y: int
    width: int
    height: int

    @property
    def left(self) -> int:
        return self.x

    @property
    def right(self) -> int:
        return self.x + self.width

    @property
    def top(self) -> int:
        return self.y

    @property
    def bottom(self) -> int:
        return self.y + self.height


class GroundRectCatalog:
    """
    Loads every entry in data/battle_backgrounds.yaml and provides
    O(1) ground_rect lookup by background id.
    """

    def __init__(self, path: Path) -> None:
        self._rects: dict[str, GroundRect] = {}
        self._load(path)

    def _load(self, path: Path) -> None:
        entries = load_yaml_required(path) or []
        for entry in entries:
            if "id" not in entry:
                raise ValueError(
                    f"{path.name}: entry missing required field 'id'. "
                    f"Example:\n  - id: zone1-bg-1280x468\n"
                    f"    ground_rect: {{x: 0, y: 0, width: 1280, height: 468}}"
                )
            bg_id = entry["id"]
            if "ground_rect" not in entry:
                raise KeyError(
                    f"background {bg_id!r} ({path.name}): missing required field 'ground_rect'"
                )
            rect_data = entry["ground_rect"]
            for field_name in _REQUIRED_RECT_FIELDS:
                if field_name not in rect_data:
                    raise KeyError(
                        f"background {bg_id!r} ({path.name}): ground_rect missing "
                        f"required field {field_name!r}"
                    )
            rect = GroundRect(
                x=rect_data["x"], y=rect_data["y"],
                width=rect_data["width"], height=rect_data["height"],
            )
            self._validate_within_canvas(rect, bg_id, path.name)
            self._rects[bg_id] = rect

    @staticmethod
    def _validate_within_canvas(rect: GroundRect, bg_id: str, filename: str) -> None:
        m = _DIM_SUFFIX_RE.search(bg_id)
        if not m:
            return
        canvas_w, canvas_h = int(m.group(1)), int(m.group(2))
        if rect.x < 0 or rect.y < 0 or rect.right > canvas_w or rect.bottom > canvas_h:
            raise ValueError(
                f"background {bg_id!r} ({filename}): ground_rect {rect} falls "
                f"outside the {canvas_w}x{canvas_h} image bounds "
                f"(right={rect.right}, bottom={rect.bottom})"
            )

    def get(self, bg_id: str) -> GroundRect:
        if bg_id not in self._rects:
            raise KeyError(
                f"No ground_rect defined for battle background {bg_id!r}. "
                f"Add an entry to data/battle_backgrounds.yaml, e.g.:\n"
                f"  - id: {bg_id}\n    ground_rect: {{x: 0, y: 0, width: 1280, height: 468}}"
            )
        return self._rects[bg_id]

    def __contains__(self, bg_id: str) -> bool:
        return bg_id in self._rects

    def __len__(self) -> int:
        return len(self._rects)
