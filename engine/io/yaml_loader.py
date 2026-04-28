# engine/io/yaml_loader.py
#
# Centralized YAML file loading for the engine. All scenario YAML reads should
# route through these helpers so we have one place to add caching, error
# context, or schema enforcement later.

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterator

import yaml


# Process-wide cache for YAML files that don't change between loads.
# Keyed on the resolved path. Use clear_yaml_cache() on scenario reload.
_CACHE: dict[Path, Any] = {}


def clear_yaml_cache() -> None:
    """Drop all cached YAML payloads. Call on scenario reload or in tests."""
    _CACHE.clear()


def load_yaml_required_cached(path: Path) -> Any:
    """Cached variant of load_yaml_required.

    Used for files that are read repeatedly during a session and don't change
    until the scenario itself reloads (class ability sheets, dialogue trees).
    """
    key = path.resolve()
    if key in _CACHE:
        return _CACHE[key]
    payload = load_yaml_required(path)
    _CACHE[key] = payload
    return payload


def load_yaml_optional_cached(path: Path) -> Any | None:
    """Cached variant of load_yaml_optional.

    A None payload (missing file) is also cached so we don't re-stat on every
    lookup. Use clear_yaml_cache() if a file is created at runtime.
    """
    key = path.resolve()
    if key in _CACHE:
        return _CACHE[key]
    payload = load_yaml_optional(path)
    _CACHE[key] = payload
    return payload


def load_yaml_required(path: Path) -> Any:
    """Load and parse a YAML file that must exist.

    Raises FileNotFoundError with the absolute path if the file is missing.
    Raises yaml.YAMLError on parse failure. Returns whatever yaml.safe_load
    produces (typically a dict, list, or None for empty files).
    """
    if not path.exists():
        raise FileNotFoundError(f"Required YAML file not found: {path}")
    with open(path, "r") as f:
        return yaml.safe_load(f)


def load_yaml_optional(path: Path) -> Any | None:
    """Load and parse a YAML file if it exists, else return None.

    Use this when a file's absence is a valid runtime state (e.g. a map with
    no NPC list). Callers must distinguish None (missing file) from an empty
    parse result themselves.
    """
    if not path.exists():
        return None
    with open(path, "r") as f:
        return yaml.safe_load(f)


def iter_yaml_documents(path: Path) -> Iterator[Any]:
    """Iterate over every document in a multi-document YAML file.

    Raises FileNotFoundError if the file is missing. Used by enemy_loader for
    its rank YAML files which pack many enemy definitions per file.
    """
    if not path.exists():
        raise FileNotFoundError(f"Required YAML file not found: {path}")
    with open(path, "r") as f:
        yield from yaml.safe_load_all(f)
