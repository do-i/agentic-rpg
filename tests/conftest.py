# tests/conftest.py

from __future__ import annotations

import pytest
from engine.world.position_data import Position
from engine.common.map_state import MapState


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