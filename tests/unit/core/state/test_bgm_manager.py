# tests/unit/core/state/test_bgm_manager.py
#
# Smoke tests for BgmManager: index parsing, key resolution, and the
# enabled gate. Actual pygame.mixer.music calls are patched out.

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml


@pytest.fixture(autouse=True)
def _stub_mixer():
    """All BgmManager methods touch pygame.mixer.music — patch it for every
    test so we don't depend on real audio init."""
    with patch("engine.audio.bgm_manager.pygame.mixer") as mixer:
        mixer.get_init.return_value = True   # skip the lazy mixer.init() branch
        yield mixer


def _make_manager(tmp_path: Path, *, enabled: bool = True, index: dict | None = None):
    """Build a scenario layout: data/audio/bgm_index.yaml + audio files."""
    audio_root = tmp_path / "assets" / "audio"
    audio_root.mkdir(parents=True)
    if index is not None:
        idx_dir = tmp_path / "data" / "audio"
        idx_dir.mkdir(parents=True)
        (idx_dir / "bgm_index.yaml").write_text(yaml.dump(index))
        # Touch every referenced file so play_key resolves them.
        for entries in index.values():
            if isinstance(entries, dict):
                for rel in entries.values():
                    full = audio_root / rel
                    full.parent.mkdir(parents=True, exist_ok=True)
                    full.touch()
    from engine.audio.bgm_manager import BgmManager
    return BgmManager(scenario_path=tmp_path, enabled=enabled)


# ── Construction + index parsing ─────────────────────────────

class TestIndexParsing:
    def test_no_index_file_leaves_empty_table(self, tmp_path):
        m = _make_manager(tmp_path)
        assert m._index == {}

    def test_basic_index_parses_to_category_dot_key(self, tmp_path):
        m = _make_manager(tmp_path, index={
            "battle":  {"normal": "battle.ogg", "boss": "boss.ogg"},
            "world":   {"forest": "forest.ogg"},
        })
        assert "battle.normal" in m._index
        assert "battle.boss" in m._index
        assert "world.forest" in m._index

    def test_non_dict_category_is_skipped(self, tmp_path):
        # Some index files may have stray top-level keys; the parser only
        # recurses into dict values.
        idx_dir = tmp_path / "data" / "audio"
        idx_dir.mkdir(parents=True)
        (idx_dir / "bgm_index.yaml").write_text(yaml.dump({
            "battle": {"normal": "battle.ogg"},
            "version": "v1",
        }))
        from engine.audio.bgm_manager import BgmManager
        m = BgmManager(scenario_path=tmp_path, enabled=True)
        assert "battle.normal" in m._index
        assert all(not k.startswith("version.") for k in m._index)


# ── play / play_key gate behavior ────────────────────────────

class TestPlayBehavior:
    def test_play_no_op_when_disabled(self, tmp_path, _stub_mixer):
        m = _make_manager(tmp_path, enabled=False)
        m.play("/audio/x.ogg")
        _stub_mixer.music.load.assert_not_called()

    def test_play_loads_and_plays(self, tmp_path, _stub_mixer):
        m = _make_manager(tmp_path)
        m.play("/audio/x.ogg")
        _stub_mixer.music.load.assert_called_with("/audio/x.ogg")
        _stub_mixer.music.play.assert_called()

    def test_play_skips_if_already_current(self, tmp_path, _stub_mixer):
        m = _make_manager(tmp_path)
        m.play("/audio/x.ogg")
        _stub_mixer.music.load.reset_mock()
        m.play("/audio/x.ogg")  # same path, should be a no-op
        _stub_mixer.music.load.assert_not_called()

    def test_play_key_resolves_known_key(self, tmp_path, _stub_mixer):
        m = _make_manager(tmp_path, index={"battle": {"normal": "battle.ogg"}})
        m.play_key("battle.normal")
        _stub_mixer.music.load.assert_called()
        loaded = _stub_mixer.music.load.call_args.args[0]
        assert "battle.ogg" in loaded

    def test_play_key_unknown_is_no_op(self, tmp_path, _stub_mixer):
        m = _make_manager(tmp_path, index={"battle": {"normal": "battle.ogg"}})
        m.play_key("never.exists")
        _stub_mixer.music.load.assert_not_called()

    def test_play_key_no_op_when_disabled(self, tmp_path, _stub_mixer):
        m = _make_manager(tmp_path, enabled=False,
                          index={"battle": {"normal": "battle.ogg"}})
        m.play_key("battle.normal")
        _stub_mixer.music.load.assert_not_called()


# ── stop ─────────────────────────────────────────────────────

class TestStop:
    def test_stop_clears_current_and_fades(self, tmp_path, _stub_mixer):
        m = _make_manager(tmp_path)
        m.play("/audio/x.ogg")
        m.stop()
        assert m.current == ""
        _stub_mixer.music.fadeout.assert_called()

    def test_stop_no_op_when_disabled_still_clears_current(self, tmp_path, _stub_mixer):
        m = _make_manager(tmp_path, enabled=False)
        m._current = "/audio/x.ogg"
        m.stop()
        assert m.current == ""
        _stub_mixer.music.fadeout.assert_not_called()
