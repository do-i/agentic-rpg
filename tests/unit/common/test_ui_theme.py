# tests/unit/common/test_ui_theme.py
#
# Theme assets come from the scenario manifest (ui.menu_backdrop) — the
# engine holds no hardcoded scenario path. Unconfigured use fails loudly.

from __future__ import annotations

from pathlib import Path

import pytest

from engine.common.ui import theme
from engine.io.yaml_require import require


@pytest.fixture(autouse=True)
def _reset_theme_state():
    """Each test starts unconfigured and leaves no global state behind."""
    theme._ASSET_ROOT = None
    theme._MENU_BACKDROP = None
    yield
    theme._ASSET_ROOT = None
    theme._MENU_BACKDROP = None


def make_scenario(tmp_path: Path) -> tuple[Path, dict]:
    backdrop = tmp_path / "assets" / "images" / "bg.webp"
    backdrop.parent.mkdir(parents=True)
    backdrop.write_bytes(b"stub")
    manifest = {"ui": {"menu_backdrop": "assets/images/bg.webp"}}
    return tmp_path, manifest


class TestInitThemeAssets:
    def test_resolves_backdrop_and_asset_root(self, tmp_path):
        scenario, manifest = make_scenario(tmp_path)
        theme.init_theme_assets(scenario, manifest)
        assert theme.theme_asset_root() == scenario / "assets"
        assert theme.menu_backdrop_path() == scenario / "assets" / "images" / "bg.webp"

    def test_missing_ui_section_raises(self, tmp_path):
        with pytest.raises(ValueError, match="ui"):
            theme.init_theme_assets(tmp_path, {})

    def test_missing_menu_backdrop_key_raises(self, tmp_path):
        with pytest.raises(ValueError, match="ui.menu_backdrop"):
            theme.init_theme_assets(tmp_path, {"ui": {}})

    def test_nonexistent_backdrop_file_raises(self, tmp_path):
        manifest = {"ui": {"menu_backdrop": "assets/missing.webp"}}
        with pytest.raises(ValueError, match="missing file"):
            theme.init_theme_assets(tmp_path, manifest)


class TestUnconfiguredAccess:
    def test_asset_root_raises_before_init(self):
        with pytest.raises(RuntimeError, match="init_theme_assets"):
            theme.theme_asset_root()

    def test_member_icon_path_raises_before_init(self):
        with pytest.raises(RuntimeError, match="init_theme_assets"):
            theme.member_icon_path("aric")


class TestRequire:
    def test_returns_nested_value(self):
        data = {"a": {"b": {"c": 7}}}
        assert require(data, "a.b.c", "f.yaml", "a:\n  b:\n    c: 7") == 7

    def test_missing_leaf_names_full_path(self):
        with pytest.raises(ValueError, match=r'"a\.b" in f\.yaml'):
            require({"a": {}}, "a.b", "f.yaml", "a:\n  b: 1")

    def test_non_mapping_midway_raises(self):
        with pytest.raises(ValueError, match=r'"a\.b"'):
            require({"a": 3}, "a.b", "f.yaml", "a:\n  b: 1")
