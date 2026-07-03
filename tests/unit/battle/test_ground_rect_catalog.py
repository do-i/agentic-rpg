# tests/unit/battle/test_ground_rect_catalog.py

from __future__ import annotations

from pathlib import Path

import pytest

from engine.battle.ground_rect_catalog import GroundRect, GroundRectCatalog


@pytest.fixture
def bg_file(tmp_path):
    path = tmp_path / "battle_backgrounds.yaml"
    path.write_text(
        "- id: zone1-bg-1280x468\n"
        "  ground_rect: { x: 0, y: 0, width: 1280, height: 468 }\n"
        "- id: zone7-bg-1280x468\n"
        "  ground_rect: { x: 160, y: 310, width: 960, height: 158 }\n"
    )
    return path


class TestGroundRectCatalogLoad:
    def test_loads_entries(self, bg_file):
        cat = GroundRectCatalog(bg_file)
        assert len(cat) == 2
        assert "zone1-bg-1280x468" in cat
        assert "zone10-bg-1280x468" not in cat

    def test_get_returns_ground_rect(self, bg_file):
        cat = GroundRectCatalog(bg_file)
        rect = cat.get("zone7-bg-1280x468")
        assert rect == GroundRect(x=160, y=310, width=960, height=158)
        assert rect.left == 160
        assert rect.right == 1120
        assert rect.top == 310
        assert rect.bottom == 468

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            GroundRectCatalog(tmp_path / "missing.yaml")

    def test_unknown_id_raises(self, bg_file):
        cat = GroundRectCatalog(bg_file)
        with pytest.raises(KeyError, match="zone99-bg"):
            cat.get("zone99-bg")


class TestGroundRectCatalogValidation:
    def test_entry_missing_id_raises(self, tmp_path):
        path = tmp_path / "battle_backgrounds.yaml"
        path.write_text("- ground_rect: { x: 0, y: 0, width: 1280, height: 468 }\n")
        with pytest.raises(ValueError, match="'id'"):
            GroundRectCatalog(path)

    def test_entry_missing_ground_rect_raises(self, tmp_path):
        path = tmp_path / "battle_backgrounds.yaml"
        path.write_text("- id: zone1-bg-1280x468\n")
        with pytest.raises(KeyError, match="ground_rect"):
            GroundRectCatalog(path)

    def test_ground_rect_missing_field_raises(self, tmp_path):
        path = tmp_path / "battle_backgrounds.yaml"
        path.write_text(
            "- id: zone1-bg-1280x468\n"
            "  ground_rect: { x: 0, y: 0, width: 1280 }\n"
        )
        with pytest.raises(KeyError, match="height"):
            GroundRectCatalog(path)

    def test_ground_rect_extending_past_canvas_bottom_raises(self, tmp_path):
        # id encodes a 1280x468 canvas; y + height = 518 overshoots it.
        path = tmp_path / "battle_backgrounds.yaml"
        path.write_text(
            "- id: zone7-bg-1280x468\n"
            "  ground_rect: { x: 120, y: 360, width: 910, height: 158 }\n"
        )
        with pytest.raises(ValueError, match="outside the 1280x468 image bounds"):
            GroundRectCatalog(path)

    def test_ground_rect_extending_past_canvas_right_raises(self, tmp_path):
        path = tmp_path / "battle_backgrounds.yaml"
        path.write_text(
            "- id: zone7-bg-1280x468\n"
            "  ground_rect: { x: 800, y: 0, width: 600, height: 100 }\n"
        )
        with pytest.raises(ValueError, match="outside the 1280x468 image bounds"):
            GroundRectCatalog(path)

    def test_id_without_dimension_suffix_skips_canvas_check(self, tmp_path):
        # Ids that don't end in "-WxH" have no known canvas to validate
        # against — accepted as-is rather than assuming a size.
        path = tmp_path / "battle_backgrounds.yaml"
        path.write_text(
            "- id: some_custom_bg\n"
            "  ground_rect: { x: 0, y: 0, width: 9999, height: 9999 }\n"
        )
        cat = GroundRectCatalog(path)
        assert cat.get("some_custom_bg").width == 9999


class TestGroundRectCatalogRealData:
    """Smoke test against actual scenario data."""

    def test_loads_rusted_kingdoms_and_covers_all_backgrounds(self):
        path = Path("rusted_kingdoms/data/battle_backgrounds.yaml")
        if not path.is_file():
            pytest.skip("Scenario data not available")
        cat = GroundRectCatalog(path)

        bg_dir = Path("rusted_kingdoms/assets/images/battle_bg")
        bg_ids = {p.stem for p in bg_dir.glob("*.webp")}
        assert bg_ids
        for bg_id in bg_ids:
            assert bg_id in cat, f"{bg_id} has no ground_rect entry"
