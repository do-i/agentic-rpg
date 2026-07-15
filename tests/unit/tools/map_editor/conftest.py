# tests/unit/tools/map_editor/conftest.py

from __future__ import annotations

from pathlib import Path

import pytest


def _portal_xml(
    obj_id: int,
    rect_px: tuple[int, int, int, int],
    target_map: str,
    target_tile: tuple[int, int],
) -> str:
    x, y, w, h = rect_px
    return (
        f'  <object id="{obj_id}" x="{x}" y="{y}" width="{w}" height="{h}">\n'
        f"   <properties>\n"
        f'    <property name="target_map" value="{target_map}"/>\n'
        f'    <property name="target_position_x" type="int" value="{target_tile[0]}"/>\n'
        f'    <property name="target_position_y" type="int" value="{target_tile[1]}"/>\n'
        f"   </properties>\n"
        f"  </object>\n"
    )


def write_tmx(path: Path, portals: list[str], next_object_id: int) -> None:
    path.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<map version="1.10" orientation="orthogonal" renderorder="right-down"'
        f' width="10" height="8" tilewidth="16" tileheight="16"'
        f' nextobjectid="{next_object_id}">\n'
        ' <objectgroup name="portals">\n'
        + "".join(portals)
        + " </objectgroup>\n"
        "</map>\n",
        encoding="utf-8",
    )


@pytest.fixture
def scenario_root(tmp_path: Path) -> Path:
    """A minimal scenario: two maps, one portal town -> town_house."""
    root = tmp_path / "scenario"
    maps_dir = root / "assets" / "maps"
    data_maps = root / "data" / "maps"
    maps_dir.mkdir(parents=True)
    data_maps.mkdir(parents=True)

    (root / "manifest.yaml").write_text(
        "refs:\n  maps: data/maps/\n", encoding="utf-8"
    )
    write_tmx(
        maps_dir / "town.tmx",
        [_portal_xml(1, (32, 48, 16, 16), "town_house", (3, 4))],
        next_object_id=2,
    )
    write_tmx(maps_dir / "town_house.tmx", [], next_object_id=1)
    (data_maps / "town.yaml").write_text(
        "name: Town\nbgm: town_theme\ninn:\n  price: 10\n", encoding="utf-8"
    )
    return root
