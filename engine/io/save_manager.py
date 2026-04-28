# engine/io/save_manager.py

import binascii
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
AUTOSAVE_PREFIX   = "autosave"  # kept for display label only


def _checksum(content: str) -> str:
    return f"{binascii.crc32(content.encode()) & 0xFFFFFFFF:08X}"


def _slot_path(saves_dir: Path, slot_index: int) -> Path:
    return saves_dir / f"{slot_index:03d}.yaml"


_META_TS_FORMAT     = "%Y-%m-%d-%H-%M-%S"
_META_TS_DISPLAY_FMT = "%Y-%m-%d %H:%M:%S"


def _meta_ts_to_display(ts: str) -> str:
    """Convert a save's stored timestamp into the user-facing display form.

    Stored format is `_serialize`'s `now.strftime("%Y-%m-%d-%H-%M-%S")`.
    Use strptime/strftime so a future schema change to either format
    surfaces as a ValueError instead of silently producing nonsense
    (the original hand-rolled string surgery would happily mangle a
    differently-shaped string).
    """
    try:
        return datetime.strptime(ts, _META_TS_FORMAT).strftime(_META_TS_DISPLAY_FMT)
    except ValueError:
        return ts


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
        self._dir         = Path(saves_dir).expanduser()
        self._classes_dir = classes_dir
        self._item_catalog = item_catalog
        self._dir.mkdir(parents=True, exist_ok=True)

    # ── Save ──────────────────────────────────────────────────

    def save(
        self,
        state: GameState,
        slot_index: int,
        overwrite_path: Path | None = None,  # ignored; path is always {slot:03d}.yaml
    ) -> Path:
        state.playtime.commit_session()
        is_autosave = slot_index == AUTOSAVE_INDEX
        path = _slot_path(self._dir, slot_index)

        data = self._serialize(state, is_autosave)
        body = yaml.dump(data, allow_unicode=True, sort_keys=False)
        data["checksum"] = _checksum(body)

        with open(path, "w") as f:
            yaml.dump(data, f, allow_unicode=True, sort_keys=False)

        return path

    # ── Load ──────────────────────────────────────────────────

    def load(self, path: Path) -> GameState:
        with open(path, "r") as f:
            data = yaml.safe_load(f)
        data.pop("checksum", None)
        return from_save(data, self._classes_dir, self._item_catalog)

    # ── Slot list ─────────────────────────────────────────────

    def list_slots(self) -> list[SaveSlot]:
        file_map: dict[int, Path] = {}
        for f in self._dir.glob("[0-9][0-9][0-9].yaml"):
            try:
                idx = int(f.stem)
            except ValueError:
                continue
            if 0 <= idx <= PLAYER_SLOT_COUNT:
                file_map[idx] = f

        slots: list[SaveSlot] = []

        if 0 in file_map:
            slots.append(self._slot_from_file(file_map[0], 0, is_autosave=True))
        else:
            slots.append(SaveSlot(slot_index=0, path=None, is_autosave=True))

        for i in range(1, PLAYER_SLOT_COUNT + 1):
            slots.append(
                self._slot_from_file(file_map[i], i)
                if i in file_map
                else SaveSlot(slot_index=i, path=None)
            )

        return slots

    # ── Helpers ───────────────────────────────────────────────

    def _slot_from_file(
        self, path: Path, index: int, is_autosave: bool = False
    ) -> SaveSlot:
        try:
            raw  = path.read_text()
            data = yaml.safe_load(raw)

            stored = data.pop("checksum", None)
            if stored is not None:
                recomputed = _checksum(yaml.dump(data, allow_unicode=True, sort_keys=False))
                if recomputed != stored:
                    return SaveSlot(slot_index=index, path=path, is_autosave=is_autosave)

            meta  = data["meta"]
            party = data["party"]
            proto = next((m for m in party if m.get("protagonist")), party[0])
            return SaveSlot(
                slot_index=index,
                path=path,
                timestamp=_meta_ts_to_display(meta.get("timestamp", "")),
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
                "location_display": state.map.display_name or state.map.current,
                "is_autosave":      is_autosave,
            },
            "party": party_data,
            "party_repository": {
                "gp":    state.repository.gp,
                "items": items_data,
            },
            "flags": state.flags.to_list(),
            "map":   state.map.to_dict(),
            "opened_boxes": state.opened_boxes.to_list(),
        }
