# engine/item/item_effect_handler.py
#
# Phase 6 — Shop + Apothecary

from __future__ import annotations
from pathlib import Path
from typing import Callable
import yaml

from engine.party.member_state import MemberState
from engine.common.party_state import PartyState
from engine.party.repository_state import RepositoryState
from engine.common.item_defs_data import FieldItemDef, UseResult

# Re-export so existing imports keep working
__all__ = ["FieldItemDef", "UseResult", "ItemEffectHandler"]


class ItemEffectHandler:
    """
    Loads field_use.yaml and applies item effects to MemberState(s).
    Warn-and-allow: if item would have no effect, still applies but
    returns a warning message so the UI can inform the player.
    """

    def __init__(self, field_use_path: Path) -> None:
        self._defs: dict[str, FieldItemDef] = {}
        self._load(field_use_path)

    # ── Load ──────────────────────────────────────────────────

    def _load(self, path: Path) -> None:
        if not path.exists():
            return
        with open(path, "r") as f:
            data = yaml.safe_load(f) or []
        for entry in data:
            item_id = entry.get("id")
            if not item_id:
                continue
            self._defs[item_id] = FieldItemDef(
                id=item_id,
                effect=entry.get("effect", ""),
                target=entry.get("target", "single_alive"),
                amount=entry.get("amount", 0),
                cures=entry.get("cures", []),
                revive_hp_pct=float(entry.get("revive_hp_pct", 0.0)),
                consumable=entry.get("consumable", True),
            )

    # ── Queries ───────────────────────────────────────────────

    def get_def(self, item_id: str) -> FieldItemDef | None:
        return self._defs.get(item_id)

    def is_field_usable(self, item_id: str) -> bool:
        return item_id in self._defs

    def valid_targets(
        self, item_id: str, party: PartyState
    ) -> list[MemberState]:
        """Returns members that can be targeted by this item."""
        defn = self._defs.get(item_id)
        if not defn:
            return []
        if defn.target in ("single_alive", "all_alive"):
            return [m for m in party.members if m.hp > 0]
        if defn.target == "single_ko":
            return [m for m in party.members if m.hp <= 0]
        return []

    # ── Apply ─────────────────────────────────────────────────

    def apply(
        self,
        item_id: str,
        targets: list[MemberState],
        repository: RepositoryState,
    ) -> UseResult:
        """
        Apply item effect to target(s). Decrement qty if consumable.
        Returns UseResult — always succeeds (warn-and-allow).
        """
        defn = self._defs.get(item_id)
        if not defn:
            return UseResult(success=False, warning="Unknown item.")

        messages: list[str] = []
        warnings: list[str] = []

        for member in targets:
            w = self._apply_to_member(defn, member)
            if w:
                warnings.append(w)
            else:
                messages.append(f"{member.name} used {item_id}.")

        # decrement qty if consumable
        if defn.consumable:
            repository.remove_item(item_id, 1)

        warning_str = "  ".join(warnings) if warnings else ""
        return UseResult(success=True, warning=warning_str, messages=messages)

    def _apply_to_member(self, defn: FieldItemDef, member: MemberState) -> str:
        """
        Apply effect to one member.
        Returns a warning string if item would have no effect, else "".
        """
        effect = defn.effect

        if effect == "restore_hp":
            if member.hp >= member.hp_max:
                member.hp = member.hp_max   # apply anyway (warn-and-allow)
                return f"{member.name} is already at full HP."
            member.hp = min(member.hp_max, member.hp + defn.amount)

        elif effect == "restore_mp":
            if member.mp >= member.mp_max:
                member.mp = member.mp_max
                return f"{member.name} is already at full MP."
            member.mp = min(member.mp_max, member.mp + defn.amount)

        elif effect == "restore_full":
            warn_parts = []
            if member.hp >= member.hp_max:
                warn_parts.append("HP")
            if member.mp_max > 0 and member.mp >= member.mp_max:
                warn_parts.append("MP")
            member.hp = member.hp_max
            if member.mp_max > 0:
                member.mp = member.mp_max
            for status in defn.cures:
                if hasattr(member, "status_effects"):
                    member.status_effects = [
                        s for s in member.status_effects
                        if s.name.lower() != status.lower()
                    ]
            if warn_parts:
                return f"{member.name}'s {' and '.join(warn_parts)} already full."

        elif effect == "cure":
            if not hasattr(member, "status_effects"):
                return ""
            cured_any = False
            for status in defn.cures:
                before = len(member.status_effects)
                member.status_effects = [
                    s for s in member.status_effects
                    if s.name.lower() != status.lower()
                ]
                if len(member.status_effects) < before:
                    cured_any = True
            if not cured_any:
                return f"{member.name} has no matching status effect."

        elif effect == "revive":
            if member.hp > 0:
                return f"{member.name} is not KO'd."
            member.hp = max(1, int(member.hp_max * defn.revive_hp_pct))

        return ""
