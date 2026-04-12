# engine/dto/item_defs.py

from __future__ import annotations
from dataclasses import dataclass, field


@dataclass(frozen=True)
class FieldItemDef:
    """Parsed definition from field_use.yaml for one item."""
    id:           str
    effect:       str                  # restore_hp | restore_mp | restore_full | cure | revive
    target:       str                  # single_alive | single_ko | all_alive
    amount:       int        = 0       # for restore_hp / restore_mp
    cures:        list[str]  = field(default_factory=list)   # for cure / restore_full
    revive_hp_pct: float     = 0.0    # for revive
    consumable:   bool       = True    # False = key item, never removed


@dataclass(frozen=True)
class UseResult:
    """Returned by apply() — describes what happened."""
    success:  bool
    warning:  str = ""    # non-empty = warn-and-allow was triggered
    messages: list[str] = field(default_factory=list)
