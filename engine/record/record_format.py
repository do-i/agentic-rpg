from dataclasses import dataclass, field

RECORDING_VERSION = 2


@dataclass
class RecordedFrame:
    frame_index: int
    events: list   # list of {"type": int, "dict": dict} — pygame events serialized
    key_state: dict  # sparse dict of {key_constant: 1} for all pressed keys


@dataclass
class RecordedSession:
    version: int = RECORDING_VERSION
    fps: int = 60
    frames: list[RecordedFrame] = field(default_factory=list)
