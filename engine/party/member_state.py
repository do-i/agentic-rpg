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

        # stat_growth loaded from class YAML — None until load_stat_growth() called
        self.stat_growth: dict[str, list[int]] | None = None

    def load_stat_growth(self, class_data: dict) -> None:
        """
        Cache stat_growth from the class YAML dict.
        Call at party join and after load_game.
        Expected class_data shape:
            {"stat_growth": {"str": [...], "dex": [...], "con": [...], "int": [...]}}
        """
        growth = class_data.get("stat_growth", {})
        self.stat_growth = {
            "str": growth["str"],
            "dex": growth["dex"],
            "con": growth["con"],
            "int": growth["int"],
        }

    def __repr__(self) -> str:
        tag = " [protagonist]" if self.protagonist else ""
        return f"MemberState({self.id!r}, name={self.name!r}{tag})"
