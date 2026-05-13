"""Apply portal target changes back to TMX files.

Each call writes a single portal object's target_map/target_position_x/
target_position_y properties in place. The first time a particular TMX is
edited within this run, a sibling .bak file is created so the original can be
restored manually if needed.
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
) -> None:
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


def _set_prop(props_elem: ET.Element, name: str, value: str) -> None:
    for prop in props_elem.findall("property"):
        if prop.get("name") == name:
            prop.set("value", value)
            return
    ET.SubElement(props_elem, "property", attrib={"name": name, "value": value})
