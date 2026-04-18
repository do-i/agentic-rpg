#!/usr/bin/env python
"""
validate.py — Rusted Kingdoms data validator
Usage: python validate.py [--root PATH]
Default root: current working directory (expects manifest.yaml at root)
"""

import argparse
import sys
from pathlib import Path

import yaml


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def load_yaml(path: Path):
    with open(path, "r") as f:
        return yaml.safe_load(f)


def load_yaml_list(path: Path):
    """Some files are YAML lists at top level (e.g. all_recipe.yaml, consumables_*.yaml)."""
    with open(path, "r") as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, list) else [data]


def collect_yaml_files(directory: Path) -> set[Path]:
    return set(directory.rglob("*.yaml"))


# ─────────────────────────────────────────────
# Item registry — build from data/items/**
# ─────────────────────────────────────────────

def build_item_registry(root: Path) -> dict[str, Path]:
    """Returns {item_id: source_file}"""
    registry = {}
    items_dir = root / "data" / "items"
    if not items_dir.exists():
        return registry
    for f in items_dir.rglob("*.yaml"):
        entries = load_yaml_list(f)
        if not entries:
            continue
        for entry in entries:
            if isinstance(entry, dict) and "id" in entry:
                registry[entry["id"]] = f
    return registry


# ─────────────────────────────────────────────
# Character registry — build from data/characters/**
# ─────────────────────────────────────────────

def build_character_registry(root: Path) -> dict[str, Path]:
    """Returns {character_id: source_file}"""
    registry = {}
    chars_dir = root / "data" / "characters"
    if not chars_dir.exists():
        return registry
    for f in chars_dir.rglob("*.yaml"):
        data = load_yaml(f)
        if isinstance(data, dict) and "id" in data:
            registry[data["id"]] = f
    return registry


# ─────────────────────────────────────────────
# Dialogue registry — build from data/dialogue/**
# ─────────────────────────────────────────────

def build_dialogue_registry(root: Path) -> dict[str, Path]:
    """Returns {dialogue_id: source_file}"""
    registry = {}
    dialogue_dir = root / "data" / "dialogue"
    if not dialogue_dir.exists():
        return registry
    for f in dialogue_dir.rglob("*.yaml"):
        data = load_yaml(f)
        if isinstance(data, dict) and "id" in data:
            registry[data["id"]] = f
    return registry


# ─────────────────────────────────────────────
# Flag collection
# ─────────────────────────────────────────────

def collect_flags(root: Path) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    """
    Returns:
        defined_flags:  {flag_id: [source descriptions]}  — set_flag occurrences
        consumed_flags: {flag_id: [source descriptions]}  — requires/excludes/unlock_flag occurrences
    """
    defined: dict[str, list[str]] = {}
    consumed: dict[str, list[str]] = {}

    def add_defined(flag, source):
        defined.setdefault(flag, []).append(source)

    def add_consumed(flag, source):
        consumed.setdefault(flag, []).append(source)

    # bootstrap_flags in manifest
    manifest_path = root / "manifest.yaml"
    if manifest_path.exists():
        manifest = load_yaml(manifest_path)
        for flag in manifest.get("bootstrap_flags", []):
            add_defined(flag, "manifest.yaml:bootstrap_flags")

    for flag in manifest.get("engine_managed_flags", []):
        add_defined(flag, "manifest.yaml:engine_managed_flags")

    # dialogue files
    dialogue_dir = root / "data" / "dialogue"
    if dialogue_dir.exists():
        for f in dialogue_dir.rglob("*.yaml"):
            rel = f.relative_to(root)
            data = load_yaml(f)
            if not isinstance(data, dict):
                continue
            for entry in data.get("entries", []):
                cond = entry.get("condition", {})
                for flag in cond.get("requires", []):
                    add_consumed(flag, str(rel))
                for flag in cond.get("excludes", []):
                    add_consumed(flag, str(rel))
                on_complete = entry.get("on_complete", {})
                set_flags = on_complete.get("set_flag", [])
                if isinstance(set_flags, str):
                    set_flags = [set_flags]
                for flag in set_flags:
                    add_defined(flag, str(rel))

    # encount files — boss.on_complete.set_flag
    encount_dir = root / "data" / "encount"
    if encount_dir.exists():
        for f in encount_dir.rglob("*.yaml"):
            rel = f.relative_to(root)
            data = load_yaml(f)
            if not isinstance(data, dict):
                continue
            boss = data.get("boss", {})
            if boss:
                set_flags = boss.get("on_complete", {}).get("set_flag")
                if set_flags:
                    if isinstance(set_flags, str):
                        set_flags = [set_flags]
                    for flag in set_flags:
                        add_defined(flag, str(rel))

    # map files — shop.items[].unlock_flag, npcs implicitly
    maps_dir = root / "data" / "maps"
    if maps_dir.exists():
        for f in maps_dir.rglob("*.yaml"):
            rel = f.relative_to(root)
            data = load_yaml(f)
            if not isinstance(data, dict):
                continue
            for item in data.get("shop", {}).get("items", []):
                flag = item.get("unlock_flag")
                if flag:
                    add_consumed(flag, str(rel))

            # world map NPC present conditions
            for npc in data.get("npcs", []):
                present = npc.get("present", {})
                for flag in present.get("requires", []):
                    add_consumed(flag, str(rel))
                for flag in present.get("excludes", []):
                    add_consumed(flag, str(rel))

    # recipe files — unlock_flag
    recipe_dir = root / "data" / "recipe"
    if recipe_dir.exists():
        for f in recipe_dir.rglob("*.yaml"):
            rel = f.relative_to(root)
            entries = load_yaml_list(f)
            for entry in entries:
                if isinstance(entry, dict):
                    flag = entry.get("unlock_flag")
                    if flag:
                        add_consumed(flag, str(rel))

    # story scripts / cutscenes — set_flag in on_complete (already covered by dialogue loop)

    return defined, consumed


# ─────────────────────────────────────────────
# Pass 1 — Forward traversal (broken links)
# ─────────────────────────────────────────────

def forward_pass(root: Path, item_reg: dict, char_reg: dict, dialogue_reg: dict) -> tuple[list[str], set[Path]]:
    errors = []
    visited: set[Path] = set()

    def err(msg):
        errors.append(msg)

    def visit(path: Path):
        visited.add(path.resolve())

    manifest_path = root / "manifest.yaml"
    if not manifest_path.exists():
        err(f"CRITICAL: manifest.yaml not found at {root}")
        return errors, visited

    visit(manifest_path)
    manifest = load_yaml(manifest_path)

    # manifest → protagonist character file
    proto_char = manifest.get("protagonist", {}).get("character")
    if proto_char:
        p = root / proto_char
        if not p.exists():
            err(f"[manifest] protagonist.character not found: {proto_char}")
        else:
            visit(p)

    # manifest → intro_dialogue
    intro = manifest.get("start", {}).get("intro_dialogue")
    if intro:
        p = root / intro
        if not p.exists():
            err(f"[manifest] start.intro_dialogue not found: {intro}")
        else:
            visit(p)

    # manifest → refs.party
    party_ref = manifest.get("refs", {}).get("party")
    if party_ref:
        party_path = root / party_ref
        if not party_path.exists():
            err(f"[manifest] refs.party not found: {party_ref}")
        else:
            visit(party_path)
            party_data = load_yaml(party_path)
            for member in party_data.get("party", []):
                char_file = member.get("character")
                if char_file:
                    p = root / char_file
                    if not p.exists():
                        err(f"[party.yaml] character file not found: {char_file} (member: {member.get('id')})")
                    else:
                        visit(p)

    # maps — traverse all map files
    maps_dir = root / "data" / "maps"
    if maps_dir.exists():
        for map_file in maps_dir.rglob("*.yaml"):
            visit(map_file)
            data = load_yaml(map_file)
            if not isinstance(data, dict):
                continue
            rel = map_file.relative_to(root)

            # shop items → item registry
            for item in data.get("shop", {}).get("items", []):
                item_id = item.get("id")
                if item_id and item_id not in item_reg:
                    err(f"[map:{rel}] shop item id not found in items registry: '{item_id}'")

            # npcs → dialogue files
            for npc in data.get("npcs", []):
                dlg = npc.get("dialogue")
                if dlg:
                    # dialogue can be referenced by id or by path
                    dlg_path = root / "data" / "dialogue" / f"{dlg}.yaml"
                    alt_path = root / dlg  # fallback for explicit paths
                    if dlg_path.exists():
                        visit(dlg_path)
                    elif alt_path.exists():
                        visit(alt_path)
                    elif dlg not in dialogue_reg:
                        err(f"[map:{rel}] npc '{npc.get('id')}' dialogue not found: '{dlg}'")
                    else:
                        visit(dialogue_reg[dlg])

    # dialogue files — on_complete references
    dialogue_dir = root / "data" / "dialogue"
    if dialogue_dir.exists():
        for dlg_file in dialogue_dir.rglob("*.yaml"):
            visit(dlg_file)
            data = load_yaml(dlg_file)
            if not isinstance(data, dict):
                continue
            rel = dlg_file.relative_to(root)
            for entry in data.get("entries", []):
                on_complete = entry.get("on_complete", {})
                if not on_complete:
                    continue
                # join_party → character registry
                join = on_complete.get("join_party")
                if join and join not in char_reg:
                    err(f"[dialogue:{rel}] on_complete.join_party character not found: '{join}'")
                elif join:
                    visit(char_reg[join])
                # give_items → item registry
                for gift in on_complete.get("give_items", []):
                    item_id = gift.get("id")
                    if item_id and item_id not in item_reg:
                        err(f"[dialogue:{rel}] on_complete.give_items id not found: '{item_id}'")

    # recipe files → item registry
    recipe_dir = root / "data" / "recipe"
    if recipe_dir.exists():
        for recipe_file in recipe_dir.rglob("*.yaml"):
            visit(recipe_file)
            entries = load_yaml_list(recipe_file)
            rel = recipe_file.relative_to(root)
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                # output item
                output_id = entry.get("output", {}).get("item")
                if output_id and output_id not in item_reg:
                    err(f"[recipe:{rel}] output.item not found in items registry: '{output_id}' (recipe: {entry.get('id')})")
                # input items
                for inp in entry.get("inputs", {}).get("items", []):
                    item_id = inp.get("id")
                    if item_id and item_id not in item_reg:
                        err(f"[recipe:{rel}] inputs.items id not found in items registry: '{item_id}' (recipe: {entry.get('id')})")

    # visit all item files
    items_dir = root / "data" / "items"
    if items_dir.exists():
        for f in items_dir.rglob("*.yaml"):
            visit(f)

    # visit all character files
    chars_dir = root / "data" / "characters"
    if chars_dir.exists():
        for f in chars_dir.rglob("*.yaml"):
            visit(f)

    # visit all encount files
    encount_dir = root / "data" / "encount"
    if encount_dir.exists():
        for f in encount_dir.rglob("*.yaml"):
            visit(f)

    # visit all enemy files (rank files + boss move sets)
    enemies_dir = root / "data" / "enemies"
    if enemies_dir.exists():
        for f in enemies_dir.rglob("*.yaml"):
            visit(f)

    # visit all class files
    classes_dir = root / "data" / "classes"
    if classes_dir.exists():
        for f in classes_dir.rglob("*.yaml"):
            visit(f)

    # visit all audio index files
    audio_dir = root / "data" / "audio"
    if audio_dir.exists():
        for f in audio_dir.rglob("*.yaml"):
            visit(f)

    return errors, visited


# ─────────────────────────────────────────────
# Pass 2 — Unreachable files
# ─────────────────────────────────────────────

def unreachable_pass(root: Path, visited: set[Path]) -> list[str]:
    all_yaml = collect_yaml_files(root / "data")
    # also include manifest and party
    all_yaml.add(root / "manifest.yaml")
    party_path = root / "data" / "party.yaml"
    if party_path.exists():
        all_yaml.add(party_path)

    unreachable = []
    for f in sorted(all_yaml):
        if f.resolve() not in visited:
            unreachable.append(str(f.relative_to(root)))
    return unreachable


# ─────────────────────────────────────────────
# Pass 3 — Flag audit
# ─────────────────────────────────────────────

def flag_audit(defined: dict, consumed: dict, engine_managed: set) -> tuple[list[str], list[str], list[str]]:
    defined_set = set(defined.keys())
    consumed_set = set(consumed.keys())
    broken = sorted(consumed_set - defined_set)    # consumed but never defined
    orphan = sorted(defined_set - consumed_set - engine_managed)    # defined but never consumed

    broken_msgs = [
        f"  '{f}' — consumed in: {consumed[f][0]}" for f in broken
    ]
    orphan_msgs = [
        f"  '{f}' — defined in: {defined[f][0]}" for f in orphan
    ]

    return broken_msgs, orphan_msgs, sorted(defined_set)


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Validate Rusted Kingdoms data files.")
    parser.add_argument("--root", default="../../rusted_kingdoms", help="Path to scenario root (default: current directory)")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    print(f"Validating: {root}\n")

    manifest = load_yaml(root / "manifest.yaml")

    # Build registries
    item_reg = build_item_registry(root)
    char_reg = build_character_registry(root)
    dialogue_reg = build_dialogue_registry(root)

    # Pass 1 — broken links
    link_errors, visited = forward_pass(root, item_reg, char_reg, dialogue_reg)

    # Pass 2 — unreachable files
    unreachable = unreachable_pass(root, visited)

    # Pass 3 — flag audit
    defined_flags, consumed_flags = collect_flags(root)
    engine_managed = set(manifest.get("engine_managed_flags", []))
    broken_flags, orphan_flags, all_defined = flag_audit(defined_flags, consumed_flags, engine_managed)

    # ── Output ──────────────────────────────

    exit_code = 0

    print("=" * 60)
    print("BROKEN LINKS")
    print("=" * 60)
    if link_errors:
        for e in link_errors:
            print(f"  ✗ {e}")
        exit_code = 1
    else:
        print("  ✓ None")

    print()
    print("=" * 60)
    print("UNREACHABLE FILES")
    print("=" * 60)
    if unreachable:
        for f in unreachable:
            print(f"  ⚠  {f}")
    else:
        print("  ✓ None")

    print()
    print("=" * 60)
    print("FLAG AUDIT")
    print("=" * 60)
    print(f"  Defined : {len(defined_flags)} flags")
    print(f"  Consumed: {len(consumed_flags)} flags")

    if broken_flags:
        print(f"\n  ✗ Consumed but never defined ({len(broken_flags)}):")
        for msg in broken_flags:
            print(msg)
        exit_code = 1
    else:
        print("  ✓ No undefined flags consumed")

    if orphan_flags:
        print(f"\n  ⚠  Defined but never consumed ({len(orphan_flags)}):")
        for msg in orphan_flags:
            print(msg)
    else:
        print("  ✓ No orphan flags")

    print()
    print("=" * 60)
    print(f"RESULT: {'FAIL' if exit_code else 'PASS'}")
    print("=" * 60)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
