# engine/dto/member_state.py

from __future__ import annotations


class MemberState:
    """
    Holds all per-member state for display, battle, and save/load.

    stat_growth: dict loaded from class YAML, e.g.:
        {"str": [3,2,3,...], "dex": [2,2,...], "con": [2,3,...], "int": [1,1,...]}
    Each list is 10 entries, cycled via modulo on level-up.
    Set via load_stat_growth() at party join or load time.
    """

    def __init__(
        self,
        member_id: str,
        name: str,
        protagonist: bool,
        class_name: str,
        level: int,
        exp: int,
        hp: int,
        hp_max: int,
        mp: int,
        mp_max: int,
        str_: int,
        dex: int,
        con: int,
        int_: int,
        equipped: dict,
        exp_next: int = 0,
    ) -> None:
        self.id          = member_id
        self.name        = name
        self.protagonist = protagonist
        self.class_name  = class_name
        self.level       = level
        self.exp         = exp
        self.hp          = hp
        self.hp_max      = hp_max
        self.mp          = mp
        self.mp_max      = mp_max
        self.str_        = str_
        self.dex         = dex
        self.con         = con
        self.int_        = int_
        self.equipped    = equipped
        self.exp_next    = exp_next

        # Battle row — overridden by load_class_data() from class YAML's
        # default_row, then optionally by save data via direct assignment.
        # Initial "front" is a placeholder that production paths always replace.
        self.row: str = "front"

        # stat_growth loaded from class YAML — None until load_class_data() called
        self.stat_growth: dict[str, list[int]] | None = None
        self.exp_base:   int = 0
        self.exp_factor: float = 0.0
        # Class's equipment_slots: {slot_name: [allowed_categories]} (or ["all"]).
        # Empty dict means load_class_data hasn't run yet.
        self.equipment_slots: dict[str, list[str]] = {}

    def load_class_data(self, class_data: dict) -> None:
        """
        Cache class-derived data (stat_growth, exp curve, equipment_slots) from the class YAML.
        Call at party join and after load_game.
        Expected class_data shape:
            {
              "stat_growth": {"str": [...], "dex": [...], "con": [...], "int": [...]},
              "exp_base": <int>, "exp_factor": <float>,
              "equipment_slots": {"weapon": [...], "shield": [...], ...}
            }
        """
        growth = class_data.get("stat_growth", {})
        self.stat_growth = {
            "str": growth["str"],
            "dex": growth["dex"],
            "con": growth["con"],
            "int": growth["int"],
        }
        if "exp_base" in class_data:
            self.exp_base = int(class_data["exp_base"])
        if "exp_factor" in class_data:
            self.exp_factor = float(class_data["exp_factor"])
        slots = class_data.get("equipment_slots") or {}
        self.equipment_slots = {str(k): list(v or []) for k, v in slots.items()}
        if "default_row" in class_data:
            row = class_data["default_row"]
            if row not in ("front", "back"):
                raise ValueError(
                    f"class YAML default_row must be 'front' or 'back', got "
                    f"{row!r} (e.g. 'default_row: front')"
                )
            self.row = row

    # Kept for backward compatibility — tests and legacy callers.
    def load_stat_growth(self, class_data: dict) -> None:
        self.load_class_data(class_data)

    def __repr__(self) -> str:
        tag = " [protagonist]" if self.protagonist else ""
        return f"MemberState({self.id!r}, name={self.name!r}{tag})"
