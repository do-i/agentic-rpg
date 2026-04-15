# tests/unit/core/record/test_recorder.py

import pickle
from collections import defaultdict

import pygame
import pytest

from engine.record.record_format import RecordedFrame, RecordedSession, RECORDING_VERSION
from engine.record.recorder import RecordPlaybackManager


@pytest.fixture(autouse=True)
def init_pygame():
    pygame.init()
    yield
    pygame.quit()


def _make_keydown(key: int) -> pygame.event.Event:
    return pygame.event.Event(pygame.KEYDOWN, {"key": key, "mod": 0, "unicode": "", "scancode": 0})


def _make_frame(index: int, key: int, held_keys: dict | None = None) -> RecordedFrame:
    return RecordedFrame(index, [
        {"type": pygame.KEYDOWN, "dict": {"key": key, "mod": 0, "unicode": "", "scancode": 0}},
    ], held_keys or {})


# ── Normal mode ───────────────────────────────────────────────

class TestNormalMode:
    def test_delegates_to_pygame(self, monkeypatch):
        fake_events = [_make_keydown(pygame.K_UP)]
        monkeypatch.setattr(pygame.event, "get", lambda: fake_events)
        mgr = RecordPlaybackManager("normal", "unused.pkl")
        assert mgr.get_events() == fake_events

    def test_save_is_noop(self, tmp_path):
        mgr = RecordPlaybackManager("normal", str(tmp_path / "out.pkl"))
        mgr.save()
        assert not (tmp_path / "out.pkl").exists()

    def test_get_key_state_delegates_to_pygame(self, monkeypatch):
        real_keys = pygame.key.get_pressed()
        monkeypatch.setattr(pygame.key, "get_pressed", lambda: real_keys)
        mgr = RecordPlaybackManager("normal", "unused.pkl")
        assert mgr.get_key_state() is real_keys


# ── Record mode ───────────────────────────────────────────────

class TestRecordMode:
    def test_records_frames_in_order(self, monkeypatch, tmp_path):
        frames_iter = iter([
            [_make_keydown(pygame.K_UP)],
            [_make_keydown(pygame.K_DOWN)],
            [],
        ])
        monkeypatch.setattr(pygame.event, "get", lambda: next(frames_iter))
        mgr = RecordPlaybackManager("record", str(tmp_path / "out.pkl"))

        for _ in range(3):
            mgr.get_events()

        assert len(mgr._session.frames) == 3
        assert mgr._session.frames[0].frame_index == 0
        assert mgr._session.frames[1].frame_index == 1
        assert mgr._session.frames[2].frame_index == 2

    def test_records_pressed_keys_as_sparse_dict(self, monkeypatch, tmp_path):
        monkeypatch.setattr(pygame.event, "get", lambda: [])
        # Fake get_pressed so that K_RIGHT appears pressed
        real_pressed = pygame.key.get_pressed()
        monkeypatch.setattr(pygame.key, "get_pressed",
                            lambda: {pygame.K_RIGHT: 1}.get  # won't be used directly
                            )
        # Use a wrapper that returns 1 only for K_RIGHT
        class FakePressed:
            def __getitem__(self, k):
                return 1 if k == pygame.K_RIGHT else 0
        monkeypatch.setattr(pygame.key, "get_pressed", lambda: FakePressed())

        mgr = RecordPlaybackManager("record", str(tmp_path / "out.pkl"))
        mgr.get_events()

        assert mgr._session.frames[0].key_state == {pygame.K_RIGHT: 1}

    def test_serializes_event_type_and_dict(self, monkeypatch, tmp_path):
        event = _make_keydown(pygame.K_LEFT)
        monkeypatch.setattr(pygame.event, "get", lambda: [event])
        mgr = RecordPlaybackManager("record", str(tmp_path / "out.pkl"))
        mgr.get_events()

        serialized = mgr._session.frames[0].events[0]
        assert serialized["type"] == pygame.KEYDOWN
        assert serialized["dict"]["key"] == pygame.K_LEFT

    def test_save_writes_pickle(self, monkeypatch, tmp_path):
        monkeypatch.setattr(pygame.event, "get", lambda: [])
        out = tmp_path / "out.pkl"
        mgr = RecordPlaybackManager("record", str(out))
        mgr.get_events()
        mgr.save()

        assert out.exists()
        with open(out, "rb") as f:
            session = pickle.load(f)
        assert isinstance(session, RecordedSession)
        assert session.version == RECORDING_VERSION


# ── Pickle roundtrip ──────────────────────────────────────────

class TestPickleRoundtrip:
    def test_roundtrip_preserves_events(self, monkeypatch, tmp_path):
        frames_iter = iter([
            [_make_keydown(pygame.K_UP)],
            [_make_keydown(pygame.K_LEFT), _make_keydown(pygame.K_RIGHT)],
        ])
        monkeypatch.setattr(pygame.event, "get", lambda: next(frames_iter))
        out = tmp_path / "session.pkl"

        recorder = RecordPlaybackManager("record", str(out))
        recorder.get_events()
        recorder.get_events()
        recorder.save()

        player = RecordPlaybackManager("playback", str(out))

        frame0 = player.get_events()
        assert len(frame0) == 1
        assert frame0[0].type == pygame.KEYDOWN
        assert frame0[0].key == pygame.K_UP

        frame1 = player.get_events()
        assert len(frame1) == 2
        assert frame1[0].key == pygame.K_LEFT
        assert frame1[1].key == pygame.K_RIGHT

    def test_roundtrip_preserves_key_state(self, monkeypatch, tmp_path):
        monkeypatch.setattr(pygame.event, "get", lambda: [])

        class FakePressed:
            def __getitem__(self, k):
                return 1 if k == pygame.K_UP else 0

        monkeypatch.setattr(pygame.key, "get_pressed", lambda: FakePressed())
        out = tmp_path / "s.pkl"

        recorder = RecordPlaybackManager("record", str(out))
        recorder.get_events()
        recorder.save()

        player = RecordPlaybackManager("playback", str(out))
        player.get_events()
        assert player.get_key_state()[pygame.K_UP] == 1
        assert player.get_key_state()[pygame.K_DOWN] == 0


# ── Playback mode ─────────────────────────────────────────────

class TestPlaybackMode:
    def test_returns_events_in_order(self, tmp_path):
        session = RecordedSession(frames=[
            _make_frame(0, pygame.K_UP),
            _make_frame(1, pygame.K_DOWN),
        ])
        pkl = tmp_path / "s.pkl"
        with open(pkl, "wb") as f:
            pickle.dump(session, f)

        mgr = RecordPlaybackManager("playback", str(pkl))
        e0 = mgr.get_events()
        e1 = mgr.get_events()

        assert e0[0].key == pygame.K_UP
        assert e1[0].key == pygame.K_DOWN

    def test_injects_quit_when_frames_exhausted(self, tmp_path):
        session = RecordedSession(frames=[])
        pkl = tmp_path / "s.pkl"
        with open(pkl, "wb") as f:
            pickle.dump(session, f)

        mgr = RecordPlaybackManager("playback", str(pkl))
        events = mgr.get_events()

        assert len(events) == 1
        assert events[0].type == pygame.QUIT

    def test_get_key_state_returns_recorded_state(self, tmp_path):
        session = RecordedSession(frames=[
            RecordedFrame(0, [], {pygame.K_LEFT: 1}),
        ])
        pkl = tmp_path / "s.pkl"
        with open(pkl, "wb") as f:
            pickle.dump(session, f)

        mgr = RecordPlaybackManager("playback", str(pkl))
        mgr.get_events()
        assert mgr.get_key_state()[pygame.K_LEFT] == 1
        assert mgr.get_key_state()[pygame.K_RIGHT] == 0  # defaultdict → 0

    def test_get_key_state_before_first_frame_returns_zeros(self, tmp_path):
        session = RecordedSession(frames=[_make_frame(0, pygame.K_UP)])
        pkl = tmp_path / "s.pkl"
        with open(pkl, "wb") as f:
            pickle.dump(session, f)

        mgr = RecordPlaybackManager("playback", str(pkl))
        assert mgr.get_key_state()[pygame.K_UP] == 0

    def test_version_mismatch_raises(self, tmp_path):
        session = RecordedSession(version=999, frames=[])
        pkl = tmp_path / "s.pkl"
        with open(pkl, "wb") as f:
            pickle.dump(session, f)

        with pytest.raises(ValueError, match="version mismatch"):
            RecordPlaybackManager("playback", str(pkl))


# ── Multi-frame consumption (speed > 1) ──────────────────────

class TestMultiFrameConsumption:
    def _make_session(self, tmp_path, frames):
        pkl = tmp_path / "s.pkl"
        session = RecordedSession(frames=frames)
        with open(pkl, "wb") as f:
            pickle.dump(session, f)
        return pkl

    def test_speed_2_merges_two_frames_per_tick(self, tmp_path):
        pkl = self._make_session(tmp_path, [
            _make_frame(0, pygame.K_UP),
            _make_frame(1, pygame.K_DOWN),
            _make_frame(2, pygame.K_LEFT),
            _make_frame(3, pygame.K_RIGHT),
        ])
        mgr = RecordPlaybackManager("playback", str(pkl), playback_speed=2.0)

        tick0 = mgr.get_events()
        assert len(tick0) == 2
        assert tick0[0].key == pygame.K_UP
        assert tick0[1].key == pygame.K_DOWN

        tick1 = mgr.get_events()
        assert len(tick1) == 2
        assert tick1[0].key == pygame.K_LEFT
        assert tick1[1].key == pygame.K_RIGHT

    def test_speed_2_key_state_is_last_consumed_frame(self, tmp_path):
        pkl = self._make_session(tmp_path, [
            RecordedFrame(0, [], {pygame.K_UP: 1}),
            RecordedFrame(1, [], {pygame.K_DOWN: 1}),
        ])
        mgr = RecordPlaybackManager("playback", str(pkl), playback_speed=2.0)
        mgr.get_events()

        # key state should reflect the last consumed frame (frame 1 = K_DOWN)
        assert mgr.get_key_state()[pygame.K_UP] == 0
        assert mgr.get_key_state()[pygame.K_DOWN] == 1

    def test_quit_injected_when_exhausted_mid_batch(self, tmp_path):
        pkl = self._make_session(tmp_path, [_make_frame(0, pygame.K_UP)])
        mgr = RecordPlaybackManager("playback", str(pkl), playback_speed=2.0)

        # only 1 frame available but speed=2 wants 2 — should get QUIT
        events = mgr.get_events()
        assert any(e.type == pygame.QUIT for e in events)
