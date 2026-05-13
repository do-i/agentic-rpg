"""Apply portal target changes back to TMX files.

Each call either rewrites the target properties of an existing portal object
or creates a brand-new portal object at a given tile. The first time a
particular TMX is edited within this run, a sibling .bak file is created so
the original can be restored manually if needed.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from xml.etree import ElementTree as ET


def save_portal_target(
    tmx_path: Path,
    portal_obj_id: int,
    new_target_map: str,
    new_target_tile: tuple[int, int],
) -> int:
    """Update the named portal's target properties.

    Returns the portal's obj_id (unchanged for existing portals).
    """
    _ensure_backup(tmx_path)
    tree = ET.parse(tmx_path)
    root = tree.getroot()
    obj = _find_portal_object(root, portal_obj_id)
    if obj is None:
        raise ValueError(
            f"Portal object id={portal_obj_id} not found in {tmx_path}"
        )
    props = obj.find("properties")
    if props is None:
        props = ET.SubElement(obj, "properties")
    _set_prop(props, "target_map", new_target_map)
    _set_prop(props, "target_position_x", str(int(new_target_tile[0])))
    _set_prop(props, "target_position_y", str(int(new_target_tile[1])))
    tree.write(tmx_path, encoding="utf-8", xml_declaration=True)
    return portal_obj_id


def create_portal(
    tmx_path: Path,
    source_tile: tuple[int, int],
    new_target_map: str,
    new_target_tile: tuple[int, int],
) -> int:
    """Append a new portal object on `tmx_path` at the given source tile.

    Returns the Tiled object id of the newly created portal.
    """
    _ensure_backup(tmx_path)
    tree = ET.parse(tmx_path)
    root = tree.getroot()
    tile_w = int(root.get("tilewidth", "0"))
    tile_h = int(root.get("tileheight", "0"))
    if tile_w == 0 or tile_h == 0:
        raise ValueError(f"{tmx_path}: missing tilewidth/tileheight on map")

    portals = _find_or_create_portals_group(root)
    new_id = _next_object_id(root)

    col, row = source_tile
    obj = ET.SubElement(
        portals,
        "object",
        attrib={
            "id": str(new_id),
            "x": str(col * tile_w),
            "y": str(row * tile_h),
            "width": str(tile_w),
            "height": str(tile_h),
        },
    )
    props = ET.SubElement(obj, "properties")
    _set_prop(props, "target_map", new_target_map)
    _set_prop(props, "target_position_x", str(int(new_target_tile[0])))
    _set_prop(props, "target_position_y", str(int(new_target_tile[1])))

    # Tiled tracks the next-available object id on the root map element.
    root.set("nextobjectid", str(new_id + 1))
    tree.write(tmx_path, encoding="utf-8", xml_declaration=True)
    return new_id


def _ensure_backup(tmx_path: Path) -> None:
    bak = tmx_path.with_suffix(tmx_path.suffix + ".bak")
    if not bak.exists():
        shutil.copy2(tmx_path, bak)


def _find_portal_object(root: ET.Element, obj_id: int) -> ET.Element | None:
    for group in root.findall("objectgroup"):
        if group.get("name") != "portals":
            continue
        for obj in group.findall("object"):
            if obj.get("id") == str(obj_id):
                return obj
    return None


def _find_or_create_portals_group(root: ET.Element) -> ET.Element:
    for group in root.findall("objectgroup"):
        if group.get("name") == "portals":
            return group
    return ET.SubElement(root, "objectgroup", attrib={"name": "portals"})


def _next_object_id(root: ET.Element) -> int:
    existing_max = 0
    for group in root.findall("objectgroup"):
        for obj in group.findall("object"):
            try:
                existing_max = max(existing_max, int(obj.get("id", "0")))
            except (TypeError, ValueError):
                pass
    declared = int(root.get("nextobjectid", "0") or 0)
    return max(declared, existing_max + 1)


def _set_prop(props_elem: ET.Element, name: str, value: str) -> None:
    for prop in props_elem.findall("property"):
        if prop.get("name") == name:
            prop.set("value", value)
            return
    ET.SubElement(props_elem, "property", attrib={"name": name, "value": value})
