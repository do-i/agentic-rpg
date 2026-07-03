# tests/conftest.py

from __future__ import annotations

import pytest
from engine.world.position_data import Position
from engine.common.map_state import MapState


@pytest.fixture(autouse=True)
def _stub_theme_assets(tmp_path_factory):
    """Give every test a configured theme (normally done by AppModule at DI
    time from ui.menu_backdrop). The backdrop file doesn't exist, so
    render_backdrop falls back to its solid fill — fine for unit tests.
    test_ui_theme.py re-clears this to exercise the strict path."""
    from engine.common.ui import theme
    root = tmp_path_factory.mktemp("theme_assets")
    theme._ASSET_ROOT = root
    theme._MENU_BACKDROP = root / "images" / "backdrop.webp"
    yield
    theme._ASSET_ROOT = None
    theme._MENU_BACKDROP = None


@pytest.fixture
def origin():
    return Position(0, 0)


@pytest.fixture
def pos():
    return Position(5, 3)


@pytest.fixture
def empty_map_state():
    return MapState()


@pytest.fixture
def map_state():
    return MapState(
        current="town_01",
        position=Position(5, 3),
        visited={"zone_01"},
    )