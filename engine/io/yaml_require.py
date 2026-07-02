# engine/io/yaml_require.py
#
# Repo convention: scenario data has no silent fallback values. A missing
# required property raises ValueError naming the file, the property, and
# an example, so scenario authors get an actionable error instead of a
# quietly wrong default.

from __future__ import annotations

from pathlib import Path
from typing import Any


def require(mapping: Any, key_path: str, source: Path | str, example: str) -> Any:
    """Return the value at dotted `key_path` inside `mapping`.

    Raises ValueError naming `source`, the missing property, and `example`
    when any segment of the path is absent or a non-mapping is traversed.
    """
    current = mapping
    walked: list[str] = []
    for segment in key_path.split("."):
        walked.append(segment)
        if not isinstance(current, dict) or segment not in current:
            missing = ".".join(walked)
            raise ValueError(
                f'Missing "{missing}" in {source} — e.g.\n{example}'
            )
        current = current[segment]
    return current
