# engine/item/item_effect_handler.py
#
# Phase 6 — Shop + Apothecary

from __future__ import annotations
from pathlib import Path
from typing import Callable

from engine.io.yaml_loader import load_yaml_optional
from engine.party.member_state import MemberState
from engine.party.party_state import PartyState
from engine.party.repository_state import RepositoryState
from engine.item.item_defs_data import FieldItemDef, UseResult

# Re-export so existing imports keep working
__all__ = ["FieldItemDef", "UseResult", "ItemEffectHandler"]


def _status_name(s) -> str:
    """Status entries are ActiveStatus on Combatants; enum names live on .effect."""
    effect = getattr(s, "effect", s)
    return effect.name


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
        data = load_yaml_optional(path) or []
        for entry in data:
            if "id" not in entry:
                raise ValueError(
                    f"{path.name}: field-use entry missing required field 'id'. "
                    f"Example:\n  - id: potion\n    effect: restore_hp\n    amount: 30"
                )
            item_id = entry["id"]
            if "effect" not in entry:
                raise ValueError(
                    f"item {item_id!r} ({path.name}): missing required field 'effect'. "
                    f"Valid: restore_hp | restore_mp | restore_full | cure | revive. "
                    f"Example:\n  effect: restore_hp"
                )
            if "target" not in entry:
                raise ValueError(
                    f"item {item_id!r} ({path.name}): missing required field 'target'. "
                    f"Valid: single_alive | single_ko | all_alive. "
                    f"Example:\n  target: single_alive"
                )
            effect = entry["effect"]
            if effect in ("restore_hp", "restore_mp") and "amount" not in entry:
                raise ValueError(
                    f"item {item_id!r} ({path.name}): effect {effect!r} requires "
                    f"'amount'. Example:\n  amount: 30"
                )
            if effect == "cure" and "cures" not in entry:
                raise ValueError(
                    f"item {item_id!r} ({path.name}): effect 'cure' requires "
                    f"'cures' list. Example:\n  cures: [poison]"
                )
            if effect == "revive" and "revive_hp_pct" not in entry:
                raise ValueError(
                    f"item {item_id!r} ({path.name}): effect 'revive' requires "
                    f"'revive_hp_pct'. Example:\n  revive_hp_pct: 0.5"
                )
            self._defs[item_id] = FieldItemDef(
                id=item_id,
                effect=effect,
                target=entry["target"],
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
            w = self.apply_to_target(defn, member)
            if w:
                warnings.append(w)
            else:
                messages.append(f"{member.name} used {item_id}.")

        # decrement qty if consumable
        if defn.consumable:
            repository.remove_item(item_id, 1)

        warning_str = "  ".join(warnings) if warnings else ""
        return UseResult(success=True, warning=warning_str, messages=messages)

    def apply_to_target(self, defn: FieldItemDef, member: MemberState) -> str:
        """
        Apply effect to one member or combatant. The target can be either a
        MemberState (field use) or a Combatant (battle use) — both expose the
        hp/mp/status_effects fields this method reads.

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
                        if _status_name(s).lower() != status.lower()
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
                    if _status_name(s).lower() != status.lower()
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
