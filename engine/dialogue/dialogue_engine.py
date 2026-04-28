# engine/dialogue/dialogue_engine.py

from pathlib import Path

from engine.io.yaml_loader import load_yaml_optional_cached
from engine.common.flag_state import FlagState
from engine.party.repository_state import RepositoryState


class DialogueEntry:
    """Parsed single dialogue entry with condition and lines."""

    def __init__(self, data: dict) -> None:
        cond = data.get("condition", {})
        self.requires: list[str] = cond.get("requires", [])
        self.excludes: list[str] = cond.get("excludes", [])
        self.lines: list[str] = data.get("lines", [])
        self.on_complete: dict = data.get("on_complete", {}) or {}

    def matches(self, flags: FlagState) -> bool:
        return flags.has_all(self.requires) and flags.has_none(self.excludes)


class DialogueResult:
    """Resolved dialogue — lines to display + actions to fire."""

    def __init__(self, lines: list[str], on_complete: dict) -> None:
        self.lines = lines
        self.on_complete = on_complete

    @property
    def has_actions(self) -> bool:
        return bool(self.on_complete)


class DialogueEngine:
    """
    Loads a dialogue YAML, evaluates conditions against FlagState,
    returns the first matching DialogueResult.
    Dispatches on_complete actions: set_flag, give_items.
    join_party, transition, open_shop are returned for the caller to handle.
    """

    def __init__(self, dialogue_dir: Path) -> None:
        self._dir = dialogue_dir

    def resolve(self, dialogue_id: str, flags: FlagState) -> DialogueResult | None:
        """
        Load dialogue file, walk entries top-to-bottom,
        return first matching entry as DialogueResult.
        Returns None if no entry matches.
        """
        path = self._dir / f"{dialogue_id}.yaml"
        data = load_yaml_optional_cached(path)
        if not isinstance(data, dict):
            return None

        # cutscene type — no condition, single lines block
        if data.get("type") == "cutscene":
            lines = data.get("lines", [])
            on_complete = data.get("on_complete", {}) or {}
            return DialogueResult(lines, on_complete)

        for entry_data in data.get("entries", []):
            entry = DialogueEntry(entry_data)
            if entry.matches(flags):
                return DialogueResult(entry.lines, entry.on_complete)

        return None

    def dispatch_on_complete(
        self,
        on_complete: dict,
        flags: FlagState,
        repository: RepositoryState,
    ) -> dict:
        """
        Execute side-effect actions that this layer can handle.
        Returns remaining actions for caller:
          join_party, transition, start_battle, open_shop.
        """
        if not on_complete:
            return {}

        remaining = {}

        # set_flag
        set_flags = on_complete.get("set_flag", [])
        if isinstance(set_flags, str):
            set_flags = [set_flags]
        for flag in set_flags:
            flags.add_flag(flag)

        # give_items
        for gift in on_complete.get("give_items", []):
            item_id = gift.get("id")
            qty = gift.get("qty", 1)
            if item_id:
                repository.add_item(item_id, qty)

        # pass through to caller
        for key in ("join_party", "transition", "start_battle", "open_shop", "open_inn", "open_apothecary"):
            if key in on_complete:
                remaining[key] = on_complete[key]

        return remaining
