# engine/dto/flag_state.py


class FlagState:
    """
    Boolean flag registry.
    Flags are write-once — once set, never cleared (V1 rule).
    Presence = True, absence = False.
    Uses set internally — duplicates are silently ignored.
    """

    def __init__(self, flags: set[str] | None = None) -> None:
        self._flags: set[str] = set(flags) if flags else set()

    # -- Mutation --

    def add_flag(self, flag: str) -> None:
        self._flags.add(flag)

    def add_flags(self, flags: set[str] | list[str]) -> None:
        for flag in flags:
            self._flags.add(flag)

    # -- Query --

    def has_flag(self, flag: str) -> bool:
        return flag in self._flags

    def has_all(self, flags: set[str] | list[str]) -> bool:
        """True if ALL flags are set (AND)."""
        return all(f in self._flags for f in flags)

    def has_any(self, flags: set[str] | list[str]) -> bool:
        """True if AT LEAST ONE flag is set (OR)."""
        return any(f in self._flags for f in flags)

    def has_none(self, flags: set[str] | list[str]) -> bool:
        """True if NONE of the flags are set (excludes check)."""
        return not any(f in self._flags for f in flags)

    # -- Serialization --

    def to_list(self) -> list[str]:
        return sorted(self._flags)

    @classmethod
    def from_set(cls, flags: set[str]) -> "FlagState":
        return cls(flags)

    def __repr__(self) -> str:
        return f"FlagState({sorted(self._flags)})"
