# engine/io/save_manager.py

import binascii
import re
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

from engine.common.save_slot_data import SaveSlot
from engine.common.game_state import GameState
from engine.io.game_state_loader import from_save
from engine.util.playtime import Playtime

if TYPE_CHECKING:
    from engine.item.item_catalog import ItemCatalog

AUTOSAVE_INDEX    = 0
PLAYER_SLOT_COUNT = 100
AUTOSAVE_PREFIX   = "autosave"
SAVE_PREFIX       = "save"


def _crc32(data: str) -> str:
    return f"{binascii.crc32(data.encode()) & 0xFFFFFFFF:08X}"


def _make_filename(timestamp: str, prefix: str, slot_index: int) -> str:
    crc = _crc32(timestamp + prefix)
    return f"{prefix}-{timestamp}-{slot_index:03d}-{crc}.yaml"


def _parse_timestamp(filename: str) -> str:
    m = re.search(r"(\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2})", filename)
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
    classes_dir required to restore stat_growth on load.
    """

    def __init__(
        self,
        saves_dir: str | Path,
        classes_dir: Path,
        item_catalog: ItemCatalog | None = None,
    ) -> None:
        self._dir        = Path(saves_dir).expanduser()
        self._classes_dir = classes_dir
        self._item_catalog = item_catalog
        self._dir.mkdir(parents=True, exist_ok=True)

    # ── Save ──────────────────────────────────────────────────

    def save(
        self,
        state: GameState,
        slot_index: int,
        overwrite_path: Path | None = None,
    ) -> Path:
        state.playtime.commit_session()

        now        = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        is_autosave = slot_index == AUTOSAVE_INDEX
        prefix     = AUTOSAVE_PREFIX if is_autosave else SAVE_PREFIX

        if overwrite_path and overwrite_path.exists():
            path = overwrite_path
        else:
            if is_autosave:
                for old in self._dir.glob(f"{AUTOSAVE_PREFIX}-*.yaml"):
                    old.unlink()
            path = self._dir / _make_filename(now, prefix, slot_index)

        data = self._serialize(state, is_autosave)
        with open(path, "w") as f:
            yaml.dump(data, f, allow_unicode=True, sort_keys=False)

        return path

    # ── Load ──────────────────────────────────────────────────

    def load(self, path: Path) -> GameState:
        with open(path, "r") as f:
            data = yaml.safe_load(f)
        return from_save(data, self._classes_dir, self._item_catalog)

    # ── Slot list ─────────────────────────────────────────────

    def list_slots(self) -> list[SaveSlot]:
        autosave_files = sorted(
            self._dir.glob(f"{AUTOSAVE_PREFIX}-*.yaml"), reverse=True
        )
        player_files = sorted(
            self._dir.glob(f"{SAVE_PREFIX}-*.yaml"), reverse=True
        )

        slots: list[SaveSlot] = []

        if autosave_files:
            slots.append(self._slot_from_file(autosave_files[0], 0, is_autosave=True))
        else:
            slots.append(SaveSlot(slot_index=0, path=None, is_autosave=True))

        slot_map: dict[int, SaveSlot] = {}
        for f in player_files:
            idx = _slot_index_from_filename(f.name)
            slot_map[idx] = self._slot_from_file(f, idx)

        for i in range(1, PLAYER_SLOT_COUNT + 1):
            slots.append(slot_map[i] if i in slot_map
                         else SaveSlot(slot_index=i, path=None))

        return slots

    # ── Helpers ───────────────────────────────────────────────

    def _slot_from_file(
        self, path: Path, index: int, is_autosave: bool = False
    ) -> SaveSlot:
        try:
            with open(path, "r") as f:
                data = yaml.safe_load(f)
            meta  = data["meta"]
            party = data["party"]
            proto = next((m for m in party if m.get("protagonist")), party[0])
            return SaveSlot(
                slot_index=index,
                path=path,
                timestamp=_parse_timestamp(path.name),
                playtime_display=Playtime.format(meta["playtime_seconds"]),
                location=meta["location_display"],
                protagonist_name=proto["name"],
                level=proto["level"],
                is_autosave=is_autosave,
            )
        except Exception:
            return SaveSlot(slot_index=index, path=path, is_autosave=is_autosave)

    def _serialize(self, state: GameState, is_autosave: bool) -> dict:
        now = datetime.now()

        # ── Party — all members, not just protagonist ──────────
        party_data = []
        for m in state.party.members:
            party_data.append({
                "id":          m.id,
                "name":        m.name,
                "protagonist": m.protagonist,
                "class":       m.class_name,
                "level":       m.level,
                "exp":         m.exp,
                "exp_next":    m.exp_next,
                "hp":          m.hp,
                "hp_max":      m.hp_max,
                "mp":          m.mp,
                "mp_max":      m.mp_max,
                "str":         m.str_,
                "dex":         m.dex,
                "con":         m.con,
                "int":         m.int_,
                "equipped":    m.equipped,
            })

        # ── Items — full repository contents ──────────────────
        items_data = []
        for entry in state.repository.items:
            items_data.append({
                "id":     entry.id,
                "qty":    entry.qty,
                "tags":   sorted(entry.tags),
                "locked": entry.locked,
            })

        return {
            "meta": {
                "timestamp":        now.strftime("%Y-%m-%d-%H-%M-%S"),
                "playtime_seconds": state.playtime.to_seconds(),
                "location_display": state.map.current,
                "is_autosave":      is_autosave,
            },
            "party": party_data,
            "party_repository": {
                "gp":    state.repository.gp,
                "items": items_data,
            },
            "flags": state.flags.to_list(),
            "map":   state.map.to_dict(),
        }