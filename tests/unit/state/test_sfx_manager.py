# tests/unit/core/state/test_sfx_manager.py
#
# Smoke tests for SfxManager: index parsing, play() gate, and the
# play_battle_action dispatcher. Real pygame.mixer.Sound is patched out.

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml


@pytest.fixture(autouse=True)
def _stub_mixer():
    with patch("engine.audio.sfx_manager.pygame.mixer") as mixer:
        mixer.get_init.return_value = True
        # Sound() returns a fresh MagicMock each call with .set_volume() and .play()
        mixer.Sound.side_effect = lambda *_a, **_kw: MagicMock()
        yield mixer


def _make_manager(tmp_path: Path, *, enabled: bool = True, index: dict | None = None):
    audio_root = tmp_path / "assets" / "audio"
    audio_root.mkdir(parents=True)
    if index is not None:
        idx_dir = tmp_path / "data" / "audio"
        idx_dir.mkdir(parents=True)
        (idx_dir / "sfx_index.yaml").write_text(yaml.dump(index))
        for entries in index.values():
            if isinstance(entries, dict):
                for rel in entries.values():
                    full = audio_root / rel
                    full.parent.mkdir(parents=True, exist_ok=True)
                    full.touch()
    from engine.audio.sfx_manager import SfxManager
    return SfxManager(tmp_path, enabled=enabled)


# ── Index parsing ────────────────────────────────────────────

class TestIndexParsing:
    def test_no_index_file_yields_empty_table(self, tmp_path):
        m = _make_manager(tmp_path)
        assert m._sounds == {}

    def test_loads_each_key_under_each_category(self, tmp_path):
        m = _make_manager(tmp_path, index={
            "ui":     {"hover": "hover.wav", "confirm": "confirm.wav"},
            "battle": {"atk_slash": "slash.wav"},
        })
        # All three keys present (note: SfxManager stores keys without category prefix).
        assert "hover" in m._sounds
        assert "confirm" in m._sounds
        assert "atk_slash" in m._sounds

    def test_skips_missing_files(self, tmp_path):
        # Index references file but the file isn't on disk → silently skipped.
        idx_dir = tmp_path / "data" / "audio"
        idx_dir.mkdir(parents=True)
        (tmp_path / "assets" / "audio").mkdir(parents=True)
        (idx_dir / "sfx_index.yaml").write_text(yaml.dump({
            "ui": {"hover": "missing.wav"},
        }))
        from engine.audio.sfx_manager import SfxManager
        m = SfxManager(tmp_path, enabled=True)
        assert "hover" not in m._sounds


# ── play gate ────────────────────────────────────────────────

class TestPlayGate:
    def test_play_invokes_sound_when_enabled(self, tmp_path):
        m = _make_manager(tmp_path, index={"ui": {"hover": "hover.wav"}})
        m.play("hover")
        m._sounds["hover"].play.assert_called_once()

    def test_play_no_op_when_disabled(self, tmp_path):
        m = _make_manager(tmp_path, enabled=False,
                          index={"ui": {"hover": "hover.wav"}})
        m.play("hover")
        m._sounds["hover"].play.assert_not_called()

    def test_play_unknown_key_silent_no_op(self, tmp_path):
        m = _make_manager(tmp_path)
        m.play("never.exists")  # no error, no sound


# ── play_battle_action dispatcher ────────────────────────────

class TestPlayBattleAction:
    def _track(self, m: object) -> list[str]:
        played: list[str] = []
        m.play = lambda key: played.append(key)
        return played

    def test_attack_plays_atk_slash(self, tmp_path):
        m = _make_manager(tmp_path)
        played = self._track(m)
        m.play_battle_action({"type": "attack"})
        assert played == ["atk_slash"]

    def test_defend_plays_defend(self, tmp_path):
        m = _make_manager(tmp_path)
        played = self._track(m)
        m.play_battle_action({"type": "defend"})
        assert played == ["defend"]

    def test_heal_spell_plays_heal(self, tmp_path):
        m = _make_manager(tmp_path)
        played = self._track(m)
        m.play_battle_action({"type": "spell", "data": {"type": "heal"}})
        assert played == ["heal"]

    def test_revive_spell_plays_revive(self, tmp_path):
        m = _make_manager(tmp_path)
        played = self._track(m)
        m.play_battle_action({"type": "spell", "data": {"type": "revive"}})
        assert played == ["revive"]

    def test_def_buff_routes_by_stat(self, tmp_path):
        m = _make_manager(tmp_path)
        played = self._track(m)
        m.play_battle_action({
            "type": "spell",
            "data": {"type": "buff", "effect": {"stat": "def_"}},
        })
        assert played == ["def_buff"]

    def test_atk_buff_routes_by_default_stat(self, tmp_path):
        m = _make_manager(tmp_path)
        played = self._track(m)
        m.play_battle_action({
            "type": "spell",
            "data": {"type": "buff", "effect": {"stat": "atk"}},
        })
        assert played == ["atk_buff"]

    def test_element_spell_uses_element_key(self, tmp_path):
        m = _make_manager(tmp_path)
        played = self._track(m)
        m.play_battle_action({
            "type": "spell",
            "data": {"type": "offense", "element": "fire"},
        })
        assert played == ["spell_fire"]

    def test_item_plays_use_item(self, tmp_path):
        m = _make_manager(tmp_path)
        played = self._track(m)
        m.play_battle_action({"type": "item"})
        assert played == ["use_item"]

    def test_unknown_type_silent_no_op(self, tmp_path):
        m = _make_manager(tmp_path)
        played = self._track(m)
        m.play_battle_action({"type": "wat"})
        assert played == []
