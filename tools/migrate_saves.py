#!/usr/bin/env python3
"""
One-time migration: rename legacy save files to the new {slot:03d}.yaml format
and inject a checksum key into each file.

Legacy pattern:  save-YYYY-MM-DD-HH-MM-SS-{slot:03d}-{CRC}.yaml
                 autosave-YYYY-MM-DD-HH-MM-SS-{CRC}.yaml  (slot 000)
New format:      {slot:03d}.yaml  (checksum stored inside)

Usage:
    python tools/migrate_saves.py --saves-dir <path>
    python tools/migrate_saves.py --saves-dir <path> --archive   # move originals to legacy/
"""

import argparse
import binascii
import re
import sys
from pathlib import Path

import yaml


def _checksum(content: str) -> str:
    return f"{binascii.crc32(content.encode()) & 0xFFFFFFFF:08X}"


def _parse_legacy_filename(name: str) -> tuple[int, str] | None:
    """Return (slot_index, timestamp_str) or None if not a legacy file."""
    # autosave: autosave-YYYY-MM-DD-HH-MM-SS-{CRC}.yaml  (slot 0)
    m = re.match(r"^autosave-(\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2})-[0-9A-Fa-f]{8}\.yaml$", name)
    if m:
        return 0, m.group(1)

    # player save: save-YYYY-MM-DD-HH-MM-SS-{slot:03d}-{CRC}.yaml
    m = re.match(r"^save-(\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2})-(\d{3})-[0-9A-Fa-f]{8}\.yaml$", name)
    if m:
        return int(m.group(2)), m.group(1)

    return None


def migrate(saves_dir: Path, archive: bool) -> None:
    if not saves_dir.exists():
        print(f"ERROR: saves directory does not exist: {saves_dir}")
        sys.exit(1)

    legacy_dir = saves_dir / "legacy"

    # Collect legacy files grouped by slot index; keep newest per slot (sort desc)
    slot_candidates: dict[int, list[tuple[str, Path]]] = {}
    for f in saves_dir.glob("*.yaml"):
        parsed = _parse_legacy_filename(f.name)
        if parsed is None:
            continue
        slot_idx, ts = parsed
        slot_candidates.setdefault(slot_idx, []).append((ts, f))

    if not slot_candidates:
        print("No legacy save files found.")
        return

    migrated = 0
    skipped  = 0
    errors   = 0

    for slot_idx, candidates in sorted(slot_candidates.items()):
        # Pick the file with the highest (most recent) timestamp
        candidates.sort(key=lambda x: x[0], reverse=True)
        best_ts, best_path = candidates[0]
        stale = [p for _, p in candidates[1:]]

        target = saves_dir / f"{slot_idx:03d}.yaml"

        if target.exists():
            print(f"  SKIP  slot {slot_idx:03d} — {target.name} already exists")
            skipped += 1
            continue

        try:
            data = yaml.safe_load(best_path.read_text())
            if not isinstance(data, dict):
                raise ValueError("unexpected YAML structure")

            # Strip any old checksum key (shouldn't exist in legacy files, but be safe)
            data.pop("checksum", None)

            body = yaml.dump(data, allow_unicode=True, sort_keys=False)
            data["checksum"] = _checksum(body)

            target.write_text(yaml.dump(data, allow_unicode=True, sort_keys=False))
            print(f"  OK    slot {slot_idx:03d} ← {best_path.name}")
            migrated += 1
        except Exception as e:
            print(f"  ERROR slot {slot_idx:03d} ({best_path.name}): {e}")
            errors += 1
            continue

        # Handle originals (best + stale)
        all_originals = [best_path] + stale
        if archive:
            legacy_dir.mkdir(exist_ok=True)
            for p in all_originals:
                dest = legacy_dir / p.name
                p.rename(dest)
                print(f"        archived → legacy/{p.name}")
        else:
            for p in all_originals:
                p.unlink()
                print(f"        deleted  {p.name}")

    print(f"\nDone — migrated: {migrated}, skipped: {skipped}, errors: {errors}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate legacy save files to new format.")
    parser.add_argument("--saves-dir", required=True, type=Path, help="Path to saves directory")
    parser.add_argument("--archive", action="store_true",
                        help="Move originals to legacy/ subfolder instead of deleting")
    args = parser.parse_args()
    migrate(args.saves_dir.expanduser(), args.archive)


if __name__ == "__main__":
    main()
