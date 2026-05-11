from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path
import zipfile

import pytest

from tools.visualize_maps import (
    build_html,
    collect_portal_edit_data,
    collect_portal_edges,
    load_colors,
    parse_tmx_portals,
)


def write_tmx(tmp_path, name: str = "source_map") -> str:
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<map version="1.10" tiledversion="1.11.0" orientation="orthogonal" renderorder="right-down" width="10" height="8" tilewidth="16" tileheight="16">
 <objectgroup id="2" name="portals">
  <object id="7" name="north gate" x="32" y="48" width="16" height="32">
   <properties>
    <property name="target_map" value="dest_map"/>
    <property name="target_position_x" value="4"/>
    <property name="target_position_y" value="5"/>
    <property name="untouched" value="keep-me"/>
   </properties>
  </object>
 </objectgroup>
</map>
"""
    (tmp_path / f"{name}.tmx").write_text(xml)
    return xml


def test_parse_tmx_portals_includes_edit_metadata(tmp_path):
    original_xml = write_tmx(tmp_path)

    parsed = parse_tmx_portals(tmp_path / "source_map.tmx")

    assert parsed is not None
    assert parsed["map_id"] == "source_map"
    assert parsed["tmx_file"] == "source_map.tmx"
    assert parsed["xml"] == original_xml
    assert parsed["tile_w"] == 16
    assert parsed["tile_h"] == 16
    assert parsed["map_w"] == 10
    assert parsed["map_h"] == 8
    assert parsed["portals"] == [{
        "id": "7",
        "name": "north gate",
        "bounds_px": [32.0, 48.0, 16.0, 32.0],
        "source_pos": [2, 3],
        "source_size": [1, 2],
        "target_map": "dest_map",
        "target_pos": [4, 5],
    }]


def test_collect_portal_edges_keeps_portal_object_id(tmp_path):
    write_tmx(tmp_path)

    assert collect_portal_edges(tmp_path) == [{
        "source": "source_map",
        "target": "dest_map",
        "label": "north gate",
        "portal_id": "7",
        "source_pos": [2, 3],
        "source_size": [1, 2],
        "target_pos": [4, 5],
    }]


def test_build_html_embeds_mapping_editor_payload(tmp_path):
    write_tmx(tmp_path)
    edit_data = collect_portal_edit_data(tmp_path)
    colors = load_colors(Path("tools/visualize_maps_colors.yaml"))

    html = build_html(
        "Test",
        {"source_map": {"id": "source_map", "name": "Source"}},
        collect_portal_edges(tmp_path),
        colors,
        edit_data,
    )

    assert "const TMX_EDIT_DATA =" in html
    assert 'id="mapping-toggle"' in html
    assert "Mapping Edit Mode" in html
    assert "Select Source Map Node" in html
    assert "Select Source Tile" in html
    assert "Select Destination Node" in html
    assert "Select Destination Tile" in html
    assert 'id="tile-modal"' in html
    assert "function makeZip" in html
    assert "source_map.tmx" in html
    assert "north gate" in html
    assert "target_position_x" in html


def test_browser_export_retargets_only_portal_contract_fields(tmp_path):
    playwright = pytest.importorskip("playwright.sync_api")
    write_tmx(tmp_path)
    edit_data = collect_portal_edit_data(tmp_path)
    colors = load_colors(Path("tools/visualize_maps_colors.yaml"))
    html = build_html(
        "Test",
        {
            "source_map": {"id": "source_map", "name": "Source"},
            "dest_map": {"id": "dest_map", "name": "Dest"},
        },
        collect_portal_edges(tmp_path),
        colors,
        edit_data,
    )
    html_path = tmp_path / "maps.html"
    html_path.write_text(html)

    with playwright.sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.add_init_script("""
          window.vis = {
            DataSet: class {
              constructor(items) { this.items = new Map((items || []).map(i => [i.id, i])); }
              get(id) { return this.items.get(id); }
              update(item) { this.items.set(item.id, Object.assign({}, this.items.get(item.id) || {}, item)); }
            },
            Network: class {
              constructor() {}
              on() {}
              redraw() {}
              selectNodes() {}
              unselectAll() {}
              focus() {}
            }
          };
        """)
        page.goto(html_path.as_uri())
        xml = page.evaluate("""
          () => {
            window.__portalEditorTest.setPortalEdit("source_map", "7", "dest_map", 9, 1);
            return window.__portalEditorTest.serializeChangedMap("source_map");
          }
        """)
        browser.close()

    root = ET.fromstring(xml)
    obj = root.find("./objectgroup/object")
    props = {
        prop.get("name"): prop.get("value")
        for prop in obj.findall("./properties/property")
    }
    assert props["target_map"] == "dest_map"
    assert props["target_position_x"] == "9"
    assert props["target_position_y"] == "1"
    assert props["untouched"] == "keep-me"
    assert obj.get("name") == "north gate"
    assert re.search(r'name="untouched" value="keep-me"', xml)


def test_browser_zip_export_contains_changed_tmx(tmp_path):
    playwright = pytest.importorskip("playwright.sync_api")
    write_tmx(tmp_path)
    edit_data = collect_portal_edit_data(tmp_path)
    colors = load_colors(Path("tools/visualize_maps_colors.yaml"))
    html = build_html(
        "Test",
        {
            "source_map": {"id": "source_map", "name": "Source"},
            "dest_map": {"id": "dest_map", "name": "Dest"},
        },
        collect_portal_edges(tmp_path),
        colors,
        edit_data,
    )
    html_path = tmp_path / "maps.html"
    html_path.write_text(html)

    with playwright.sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.add_init_script("""
          window.vis = {
            DataSet: class {
              constructor(items) { this.items = new Map((items || []).map(i => [i.id, i])); }
              get(id) { return this.items.get(id); }
              update(item) { this.items.set(item.id, Object.assign({}, this.items.get(item.id) || {}, item)); }
            },
            Network: class {
              constructor() {}
              on() {}
              redraw() {}
              selectNodes() {}
              unselectAll() {}
              focus() {}
            }
          };
        """)
        page.goto(html_path.as_uri())
        zip_bytes = page.evaluate("""
          async () => {
            window.__portalEditorTest.setPortalEdit("source_map", "7", "dest_map", 2, 6);
            const xml = window.__portalEditorTest.serializeChangedMap("source_map");
            const blob = window.__portalEditorTest.makeZip([{ name: "source_map.tmx", text: xml }]);
            return Array.from(new Uint8Array(await blob.arrayBuffer()));
          }
        """)
        browser.close()

    zip_path = tmp_path / "changes.zip"
    zip_path.write_bytes(bytes(zip_bytes))
    with zipfile.ZipFile(zip_path) as zf:
        assert zf.namelist() == ["source_map.tmx"]
        xml = zf.read("source_map.tmx").decode()

    root = ET.fromstring(xml)
    props = {
        prop.get("name"): prop.get("value")
        for prop in root.findall("./objectgroup/object/properties/property")
    }
    assert props["target_map"] == "dest_map"
    assert props["target_position_x"] == "2"
    assert props["target_position_y"] == "6"
    assert props["untouched"] == "keep-me"
