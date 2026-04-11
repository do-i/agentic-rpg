# engine/dto/item_defs.py

from __future__ import annotations
from dataclasses import dataclass


@dataclass
class FieldItemDef:
    """Parsed definition from field_use.yaml for one item."""
    id:           str
    effect:       str                  # restore_hp | restore_mp | restore_full | cure | revive
    target:       str                  # single_alive | single_ko | all_alive
    amount:       int        = 0       # for restore_hp / restore_mp
    cures:        list[str]  = None    # for cure / restore_full
    revive_hp_pct: float     = 0.0    # for revive
    consumable:   bool       = True    # False = key item, never removed

    def __post_init__(self):
        if self.cures is None:
            self.cures = []


@dataclass
class UseResult:
    """Returned by apply() — describes what happened."""
    success:  bool
    warning:  str = ""    # non-empty = warn-and-allow was triggered
    messages: list[str] = None

    def __post_init__(self):
        if self.messages is None:
            self.messages = []
