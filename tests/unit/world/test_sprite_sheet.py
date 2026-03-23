# tests/unit/world/test_sprite_sheet.py

import pytest
import pygame
from pathlib import Path
from unittest.mock import patch, MagicMock
from engine.world.sprite_sheet import SpriteSheet, Direction, FRAME_WIDTH, FRAME_HEIGHT, FRAMES_PER_ROW


@pytest.fixture(autouse=True)
def init_pygame():
    pygame.display.init()
    pygame.display.set_mode((1, 1))
    yield
    pygame.quit()


def make_fake_sheet() -> pygame.Surface:
    """4 rows x 8 cols of 64x64 frames."""
    surface = pygame.Surface((FRAME_WIDTH * FRAMES_PER_ROW, FRAME_HEIGHT * 4), pygame.SRCALPHA)
    return surface


def make_tsx(tmp_path: Path, image_filename: str) -> Path:
    tsx_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<tileset version="1.10" name="hero" tilewidth="{FRAME_WIDTH}" tileheight="{FRAME_HEIGHT}" tilecount="32" columns="{FRAMES_PER_ROW}">
 <image source="{image_filename}" width="{FRAME_WIDTH * FRAMES_PER_ROW}" height="{FRAME_HEIGHT * 4}"/>
</tileset>"""
    tsx_path = tmp_path / "hero.tsx"
    tsx_path.write_text(tsx_content)
    return tsx_path


@pytest.fixture
def sprite_sheet(tmp_path):
    image_path = tmp_path / "hero.png"
    sheet = make_fake_sheet()
    pygame.image.save(sheet, str(image_path))
    tsx_path = make_tsx(tmp_path, "hero.png")
    return SpriteSheet(tsx_path)


# ── Construction ──────────────────────────────────────────────

class TestSpriteSheetInit:
    def test_loads_all_frames(self, sprite_sheet):
        assert len(sprite_sheet._frames) == 32  # 4 directions x 8 frames

    def test_repr(self, sprite_sheet):
        assert "hero.tsx" in repr(sprite_sheet)
        assert "32" in repr(sprite_sheet)

    def test_missing_image_raises(self, tmp_path):
        tsx_path = make_tsx(tmp_path, "nonexistent.png")
        with pytest.raises(Exception):
            SpriteSheet(tsx_path)


# ── get_frame ─────────────────────────────────────────────────

class TestGetFrame:
    def test_returns_surface(self, sprite_sheet):
        frame = sprite_sheet.get_frame(Direction.DOWN, 0)
        assert isinstance(frame, pygame.Surface)

    def test_all_directions(self, sprite_sheet):
        for direction in Direction:
            for i in range(FRAMES_PER_ROW):
                frame = sprite_sheet.get_frame(direction, i)
                assert isinstance(frame, pygame.Surface)

    def test_frame_index_wraps(self, sprite_sheet):
        f1 = sprite_sheet.get_frame(Direction.DOWN, 0)
        f2 = sprite_sheet.get_frame(Direction.DOWN, FRAMES_PER_ROW)
        assert f1 is f2

    def test_frame_size(self, sprite_sheet):
        frame = sprite_sheet.get_frame(Direction.UP, 0)
        assert frame.get_width() == FRAME_WIDTH
        assert frame.get_height() == FRAME_HEIGHT


# ── frame_count ───────────────────────────────────────────────

class TestFrameCount:
    def test_frame_count(self, sprite_sheet):
        assert sprite_sheet.frame_count == FRAMES_PER_ROW
