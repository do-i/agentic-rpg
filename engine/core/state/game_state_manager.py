# engine/core/state/game_state_manager.py

import binascii
import re
from datetime import datetime
from pathlib import Path

import yaml

from engine.core.models.save_slot import SaveSlot
from engine.core.state.game_state import GameState
from engine.core.state.playtime import Playtime

AUTOSAVE_INDEX = 0
PLAYER_SLOT_COUNT = 100
AUTOSAVE_PREFIX = "autosave"
SAVE_PREFIX = "save"


def _crc32(data: str) -> str:
    return f"{binascii.crc32(data.encode()) & 0xFFFFFFFF:08X}"


def _make_filename(timestamp: str, prefix: str, slot_index: int) -> str:
    crc = _crc32(timestamp + prefix)
    return f"{prefix}-{timestamp}-{slot_index:03d}-{crc}.yaml"


def _parse_timestamp(filename: str) -> str:
    """Extract display timestamp from filename."""
    m = re.match(r"(\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2})", filename)
    if m:
        raw = m.group(1)
        return raw[:10] + " " + raw[11:].replace("-", ":")
    return ""

def _slot_index_from_filename(filename: str) -> int:
    m = re.search(r"-(\d{3})-[0-9A-F]{8}\.yaml$", filename)
    return int(m.group(1)) if m else 0

class GameStateManager:
    """
    Handles save/load slot management and GameState serialization.

    Directory layout:
        saves_dir/
            autosave-<timestamp>-<crc>.yaml   ← slot 0
            save-<timestamp>-<crc>.yaml       ← slots 1-100 (newest first)
    """

    def __init__(self, saves_dir: str | Path = "~/user_save_data") -> None:
        self._dir = Path(saves_dir).expanduser()
        self._dir.mkdir(parents=True, exist_ok=True)

    # ── Save ──────────────────────────────────────────────────

    def save(self, state: GameState, slot_index: int, overwrite_path: Path | None = None) -> Path:
        """
        Write GameState to disk.
        slot_index=0 → autosave file (replaces previous autosave).
        slot_index>0 → new timestamped file, or overwrite existing.
        Returns path of written file.
        """
        state.playtime.commit_session()

        now = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        is_autosave = slot_index == AUTOSAVE_INDEX
        prefix = AUTOSAVE_PREFIX if is_autosave else SAVE_PREFIX

        if overwrite_path and overwrite_path.exists():
            path = overwrite_path
        else:
            if is_autosave:
                # remove old autosave
                for old in self._dir.glob(f"{AUTOSAVE_PREFIX}-*.yaml"):
                    old.unlink()
            path = self._dir / _make_filename(now, prefix, slot_index)

        data = self._serialize(state, is_autosave)
        with open(path, "w") as f:
            yaml.dump(data, f, allow_unicode=True, sort_keys=False)

        return path

    # ── Load ──────────────────────────────────────────────────

    def load(self, path: Path) -> GameState:
        """Deserialize a save file into GameState."""
        with open(path, "r") as f:
            data = yaml.safe_load(f)
        return GameState.from_save(data)

    # ── Slot list ─────────────────────────────────────────────

    def list_slots(self) -> list[SaveSlot]:
        """
        Returns slot list: index 0 = autosave, 1-N = player saves newest first.
        Always returns autosave slot + up to PLAYER_SLOT_COUNT player slots.
        Empty slots included at end if fewer than max.
        """
        autosave_files = sorted(self._dir.glob(f"{AUTOSAVE_PREFIX}-*.yaml"), reverse=True)
        player_files = sorted(self._dir.glob(f"{SAVE_PREFIX}-*.yaml"), reverse=True)

        slots: list[SaveSlot] = []

        # slot 0 — autosave
        if autosave_files:
            slots.append(self._slot_from_file(autosave_files[0], 0, is_autosave=True))
        else:
            slots.append(SaveSlot(slot_index=0, path=None, is_autosave=True))

        slot_map: dict[int, SaveSlot] = {}
        for f in player_files:
            idx = _slot_index_from_filename(f.name)
            slot_map[idx] = self._slot_from_file(f, idx)

        for i in range(1, PLAYER_SLOT_COUNT + 1):
            if i in slot_map:
                slots.append(slot_map[i])
            else:
                slots.append(SaveSlot(slot_index=i, path=None))


        return slots

    # ── Helpers ───────────────────────────────────────────────

    def _slot_from_file(self, path: Path, index: int, is_autosave: bool = False) -> SaveSlot:
        try:
            with open(path, "r") as f:
                data = yaml.safe_load(f)
            meta = data.get("meta", {})
            party = data.get("party", [{}])
            proto = next((m for m in party if m.get("protagonist")), party[0] if party else {})
            return SaveSlot(
                slot_index=index,
                path=path,
                timestamp=_parse_timestamp(path.name),
                playtime_display=Playtime.format(meta.get("playtime_seconds", 0)),
                location=meta.get("location_display", ""),
                protagonist_name=proto.get("name", ""),
                level=proto.get("level", 1),
                is_autosave=is_autosave,
            )
        except Exception:
            return SaveSlot(slot_index=index, path=path, is_autosave=is_autosave)

    def _serialize(self, state: GameState, is_autosave: bool) -> dict:
        now = datetime.now()
        proto = state.party.protagonist
        map_state = state.map
        print(f"[DEBUG] party members={state.party.members}")
        # stub — Phase 5: full party serialization
        party_data = []
        if proto:
            party_data.append({
                "id": proto.id,
                "name": proto.name,
                "protagonist": True,
                "level": 1,  # stub — Phase 4
            })

        return {
            "meta": {
                "timestamp": now.strftime("%Y-%m-%d-%H-%M-%S"),
                "playtime_seconds": state.playtime.to_seconds(),
                "location_display": map_state.current,
                "is_autosave": is_autosave,
            },
            "party": party_data,
            "party_repository": {
                "gp": state.repository.gp,
                "items": [],  # stub — Phase 6
            },
            "flags": state.flags.to_list(),
            "map": map_state.to_dict(),
        }
