# engine/dto/save_slot.py

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SaveSlot:
    """
    Metadata for a single save file entry.
    Displayed in save/load slot list UI.
    """
    slot_index: int          # 0 = autosave, 1-100 = player slots
    path: Path | None        # None = empty slot
    timestamp: str = ""      # "2024-03-15 14:22"
    playtime_display: str = ""  # "04d 06h 00m 30s"
    location: str = ""       # map display name
    protagonist_name: str = ""
    level: int = 0
    is_autosave: bool = False

    @property
    def is_empty(self) -> bool:
        return self.path is None

    @property
    def label(self) -> str:
        if self.is_autosave:
            return "Autosave"
        return f"Slot {self.slot_index:02d}"

    def display_line(self) -> str:
        """Single-line summary for slot list UI."""
        if self.is_empty:
            return "--- Empty ---"
        return (
            f"{self.protagonist_name}  Lv{self.level}"
            f"  {self.playtime_display}  {self.location}"
            f"  {self.timestamp}"
        )

    def __repr__(self) -> str:
        return f"SaveSlot({self.label}, empty={self.is_empty})"
