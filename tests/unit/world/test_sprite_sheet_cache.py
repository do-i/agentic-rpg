# tests/unit/world/test_sprite_sheet_cache.py

from pathlib import Path
from unittest.mock import patch

import pytest

from engine.world import sprite_sheet_cache as ssc_module
from engine.world.sprite_sheet_cache import SpriteSheetCache


class _FakeSheet:
    pass


class TestGet:
    def test_missing_path_returns_none(self, tmp_path: Path) -> None:
        cache = SpriteSheetCache()
        assert cache.get(tmp_path / "nope.tsx") is None

    def test_missing_path_cached(self, tmp_path: Path) -> None:
        cache = SpriteSheetCache()
        path = tmp_path / "nope.tsx"
        cache.get(path)
        # second call should not re-stat — patch exists to blow up if called
        with patch.object(Path, "exists", side_effect=AssertionError("re-stat")):
            assert cache.get(path) is None

    def test_loads_and_caches(self, tmp_path: Path) -> None:
        path = tmp_path / "x.tsx"
        path.write_text("")  # exists
        with patch.object(ssc_module, "SpriteSheet", return_value=_FakeSheet()) as ctor:
            cache = SpriteSheetCache()
            first = cache.get(path)
            second = cache.get(path)
        assert first is second
        assert ctor.call_count == 1

    def test_load_failure_cached_as_none(self, tmp_path: Path) -> None:
        path = tmp_path / "broken.tsx"
        path.write_text("")
        with patch.object(ssc_module, "SpriteSheet", side_effect=ValueError("bad")) as ctor:
            cache = SpriteSheetCache()
            assert cache.get(path) is None
            assert cache.get(path) is None
        assert ctor.call_count == 1


class TestClear:
    def test_clear_empties_cache(self, tmp_path: Path) -> None:
        path = tmp_path / "x.tsx"
        path.write_text("")
        with patch.object(ssc_module, "SpriteSheet", return_value=_FakeSheet()) as ctor:
            cache = SpriteSheetCache()
            cache.get(path)
            cache.clear()
            cache.get(path)
        assert ctor.call_count == 2
