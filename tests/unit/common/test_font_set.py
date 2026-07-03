# tests/unit/common/test_font_set.py
#
# FontSet: declarative lazy font bundle replacing per-scene
# _fonts_ready/_init_fonts boilerplate.

from __future__ import annotations

import pygame
import pytest

from engine.common import font_provider
from engine.common.font_provider import FontSet, init_fonts


@pytest.fixture(autouse=True)
def _fonts():
    pygame.init()
    init_fonts(None, {"small": 12, "medium": 16, "large": 22, "xlarge": 28})
    yield
    font_provider._instance = None
    pygame.quit()


class TestFontSet:
    def test_int_spec_means_regular_weight(self):
        fs = FontSet(row=16)
        assert isinstance(fs.row, pygame.font.Font)
        assert not fs.row.get_bold()

    def test_tuple_spec_sets_bold(self):
        fs = FontSet(title=(22, True))
        assert fs.title.get_bold()

    def test_construction_needs_no_provider(self):
        font_provider._instance = None
        fs = FontSet(row=16)  # must not raise — resolution is lazy
        with pytest.raises(RuntimeError, match="init_fonts"):
            _ = fs.row

    def test_fonts_cached_across_accesses(self):
        fs = FontSet(row=16)
        assert fs.row is fs.row

    def test_undeclared_name_raises_attribute_error(self):
        fs = FontSet(row=16)
        with pytest.raises(AttributeError, match="declared"):
            _ = fs.title
