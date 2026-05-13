from __future__ import annotations

import argparse
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TRUNCATION_MARKER = "..."
MIN_DESCRIPTION_WIDTH = 24


@dataclass(frozen=True)
class CacheGroup:
    key: str
    label: str
    patterns: tuple[str, ...]
    protected: bool = False


CACHE_GROUPS: tuple[CacheGroup, ...] = (
    CacheGroup(
        key="python",
        label="Python/runtime caches",
        patterns=("**/__pycache__/", "*.pyc", ".pytest_cache/", ".coverage"),
    ),
    CacheGroup(
        key="build",
        label="Build/package artifacts",
        patterns=("build/", "agentic_rpg_engine.egg-info/"),
    ),
    CacheGroup(
        key="maps",
        label="Map visualization generated files",
        patterns=("maps_graph.html", "maps_graph.assets/"),
    ),
    CacheGroup(
        key="state",
        label="Game/editor local state",
        patterns=("rusted_kingdoms/assets/maps/*.tiled-session",),
    ),
    CacheGroup(
        key="recordings",
        label="Recording/generated run artifacts",
        patterns=("recording.json", "recording.pkl", "recording*"),
    ),
    CacheGroup(
        key="local-config",
        label="Local IDE/agent config",
        patterns=(".claude/settings.local.json", ".vscode/"),
    ),
    CacheGroup(
        key="venv",
        label="Python environment",
        patterns=(".venv/",),
        protected=True,
    ),
)


@dataclass(frozen=True)
class Target:
    path: Path
    display: str
    is_dir: bool
    file_count: int
    byte_count: int


def path_is_under_repo(path: Path) -> bool:
    try:
        path.absolute().relative_to(REPO_ROOT)
    except ValueError:
        return False

    if path.is_symlink():
        return True

    try:
        path.resolve(strict=False).relative_to(REPO_ROOT)
    except ValueError:
        return False

    return True


def display_path(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


def path_sort_key(path: Path) -> str:
    return display_path(path)


def iter_matches(pattern: str) -> list[Path]:
    clean_pattern = pattern.rstrip("/")

    if any(char in clean_pattern for char in "*?["):
        if "/" in clean_pattern:
            matches = [path for path in REPO_ROOT.glob(clean_pattern) if path.exists() or path.is_symlink()]
        else:
            matches = [path for path in REPO_ROOT.rglob(clean_pattern) if path.exists() or path.is_symlink()]
    else:
        path = REPO_ROOT / clean_pattern
        matches = [path] if path.exists() or path.is_symlink() else []

    if pattern.endswith("/"):
        matches = [path for path in matches if path.is_dir() and not path.is_symlink()]

    return sorted(matches, key=path_sort_key)


def count_path(path: Path) -> tuple[int, int]:
    if path.is_symlink():
        try:
            return 1, path.lstat().st_size
        except OSError:
            return 0, 0

    if path.is_file():
        try:
            return 1, path.stat().st_size
        except OSError:
            return 0, 0

    if not path.is_dir():
        return 0, 0

    file_count = 0
    byte_count = 0
    for child in path.rglob("*"):
        if child.is_dir() and not child.is_symlink():
            continue
        try:
            byte_count += child.lstat().st_size if child.is_symlink() else child.stat().st_size
            file_count += 1
        except OSError:
            continue

    return file_count, byte_count


def is_descendant(path: Path, maybe_parent: Path) -> bool:
    try:
        path.absolute().relative_to(maybe_parent.absolute())
    except ValueError:
        return False
    return path != maybe_parent


def protected_roots() -> list[Path]:
    roots: list[Path] = []
    for group in CACHE_GROUPS:
        if not group.protected:
            continue
        for pattern in group.patterns:
            if any(char in pattern for char in "*?["):
                continue
            path = REPO_ROOT / pattern.rstrip("/")
            if path.exists() or path.is_symlink():
                roots.append(path)
    return roots


def is_inside(path: Path, maybe_parent: Path) -> bool:
    try:
        path.absolute().relative_to(maybe_parent.absolute())
    except ValueError:
        return False
    return True


def group_targets(group: CacheGroup) -> list[Target]:
    seen: set[Path] = set()
    candidates: list[Path] = []
    protected_paths = protected_roots() if not group.protected else []
    for pattern in group.patterns:
        for path in iter_matches(pattern):
            if not path_is_under_repo(path):
                continue
            if any(is_inside(path, protected_path) for protected_path in protected_paths):
                continue
            absolute = path.absolute()
            if absolute in seen:
                continue
            seen.add(absolute)
            candidates.append(path)

    parent_paths = [path for path in candidates if path.is_dir() and not path.is_symlink()]
    candidates = [
        path
        for path in candidates
        if not any(is_descendant(path, parent) for parent in parent_paths)
    ]

    targets: list[Target] = []
    for path in sorted(candidates, key=path_sort_key):
        file_count, byte_count = count_path(path)
        targets.append(
            Target(
                path=path,
                display=display_path(path),
                is_dir=path.is_dir() and not path.is_symlink(),
                file_count=file_count,
                byte_count=byte_count,
            )
        )

    return targets


def all_group_targets() -> dict[str, list[Target]]:
    return {group.key: group_targets(group) for group in CACHE_GROUPS}


def format_size(byte_count: int) -> str:
    units = ("B", "KiB", "MiB", "GiB")
    size = float(byte_count)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{byte_count} B"
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{byte_count} B"


def summarize_targets(targets: list[Target]) -> tuple[int, int]:
    return sum(target.file_count for target in targets), sum(target.byte_count for target in targets)


def format_summary(file_count: int, byte_count: int) -> str:
    file_word = "file" if file_count == 1 else "files"
    return f"{file_count:>5} {file_word:<5} | {format_size(byte_count):>8}"


def format_target(target: Target) -> str:
    suffix = "/" if target.is_dir else ""
    return f"{target.display}{suffix}"


def format_target_description(targets: list[Target]) -> str:
    if not targets:
        return "none"
    return ", ".join(format_target(target) for target in targets)


def truncate_description(text: str, width: int) -> str:
    if len(text) <= width:
        return text
    if width <= len(TRUNCATION_MARKER):
        return TRUNCATION_MARKER[:width]
    return f"{text[: width - len(TRUNCATION_MARKER)].rstrip()}{TRUNCATION_MARKER}"


def print_report(targets_by_group: dict[str, list[Target]]) -> None:
    print("Cache groups:")
    for group in CACHE_GROUPS:
        targets = targets_by_group[group.key]
        file_count, byte_count = summarize_targets(targets)
        protected = " [protected]" if group.protected else ""
        print(f"- {group.key}: {group.label}{protected}")
        print(f"  {format_summary(file_count, byte_count)}")
        if targets:
            print("  targets:")
            for target in targets:
                print(f"    {format_target(target)}")
        else:
            print("  targets: none")


def print_confirmation(selection_name: str, targets: list[Target]) -> None:
    file_count, byte_count = summarize_targets(targets)
    dir_targets = [target for target in targets if target.is_dir]
    file_targets = [target for target in targets if not target.is_dir]

    print("Confirm removal")
    print(f"Selection: {selection_name}")
    print(f"Total:     {format_summary(file_count, byte_count)}")
    print(f"Targets:   {len(dir_targets)} dirs, {len(file_targets)} files")
    if targets:
        print("Paths:")
        for target in targets:
            print(f"  {format_target(target)}")
    else:
        print("Paths: none")


def confirm_go_cancel(assume_yes: bool) -> bool:
    if assume_yes:
        return True

    print()
    print("g. Go")
    print("c. Cancel")
    answer = input("Choose an option: ").strip().lower()
    return answer in {"g", "go"}


def remove_target(target: Target) -> None:
    path = target.path
    if not path_is_under_repo(path):
        raise RuntimeError(f"Refusing to remove path outside repository: {path}")
    if not path.exists() and not path.is_symlink():
        return

    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def delete_targets(targets: list[Target], assume_yes: bool, selection_name: str = "Selected cache paths") -> int:
    print_confirmation(selection_name, targets)
    if not targets:
        return 0

    if not confirm_go_cancel(assume_yes):
        print("Cancelled.")
        return 0

    for target in targets:
        remove_target(target)

    print("Removed selected cache paths.")
    return 0


def group_by_key(key: str) -> CacheGroup | None:
    for group in CACHE_GROUPS:
        if group.key == key:
            return group
    return None


def safe_groups(include_venv: bool) -> list[CacheGroup]:
    return [group for group in CACHE_GROUPS if include_venv or not group.protected]


def collect_groups(groups: list[CacheGroup], targets_by_group: dict[str, list[Target]]) -> list[Target]:
    seen: set[Path] = set()
    targets: list[Target] = []
    for group in groups:
        for target in targets_by_group[group.key]:
            absolute = target.path.absolute()
            if absolute in seen:
                continue
            seen.add(absolute)
            targets.append(target)
    return targets


def interactive_menu(targets_by_group: dict[str, list[Target]]) -> int:
    columns = shutil.get_terminal_size(fallback=(120, 24)).columns
    child_indent = "   "
    print("Cache buster")
    print()
    all_safe_targets = collect_groups(safe_groups(include_venv=False), targets_by_group)
    all_safe_files, all_safe_bytes = summarize_targets(all_safe_targets)
    print(f"1. {format_summary(all_safe_files, all_safe_bytes)}  All safe groups")
    for index, group in enumerate(CACHE_GROUPS, start=2):
        if group.protected:
            continue
        targets = targets_by_group[group.key]
        file_count, byte_count = summarize_targets(targets)
        prefix = f"{child_indent}{index}. {format_summary(file_count, byte_count)}  {group.label}: "
        width = max(MIN_DESCRIPTION_WIDTH, columns - len(prefix))
        target_text = truncate_description(format_target_description(targets), width)
        print(f"{prefix}{target_text}")

    venv_targets = targets_by_group["venv"]
    venv_files, venv_bytes = summarize_targets(venv_targets)
    print(f"v. {format_summary(venv_files, venv_bytes)}  .venv")
    print("q. Quit")
    print()

    choice = input("Choose an option: ").strip().lower()
    if choice == "q":
        print("No changes made.")
        return 0
    if choice == "v":
        return delete_targets(venv_targets, assume_yes=False, selection_name=".venv")
    if choice == "1":
        targets = collect_groups(safe_groups(include_venv=False), targets_by_group)
        return delete_targets(targets, assume_yes=False, selection_name="All safe groups")

    if choice.isdigit():
        selected_index = int(choice)
        selectable = [group for group in CACHE_GROUPS if not group.protected]
        offset = selected_index - 2
        if 0 <= offset < len(selectable):
            group = selectable[offset]
            return delete_targets(targets_by_group[group.key], assume_yes=False, selection_name=group.label)

    print(f"Unknown option: {choice}")
    return 1


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="List and remove generated cache artifacts.")
    parser.add_argument("--list", action="store_true", help="Show cache groups and matching paths.")
    parser.add_argument("--all", action="store_true", help="Delete all safe groups.")
    parser.add_argument("--group", choices=[group.key for group in CACHE_GROUPS], help="Delete one group by key.")
    parser.add_argument("--include-venv", action="store_true", help="Allow --all to include .venv.")
    parser.add_argument("--yes", action="store_true", help="Skip deletion confirmation.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    targets_by_group = all_group_targets()

    if args.list:
        print_report(targets_by_group)
        return 0

    if args.all and args.group:
        print("Error: use either --all or --group, not both.", file=sys.stderr)
        return 2

    if args.all:
        targets = collect_groups(safe_groups(include_venv=args.include_venv), targets_by_group)
        selection_name = "All groups" if args.include_venv else "All safe groups"
        return delete_targets(targets, assume_yes=args.yes, selection_name=selection_name)

    if args.group:
        group = group_by_key(args.group)
        if group is None:
            print(f"Error: unknown group: {args.group}", file=sys.stderr)
            return 2
        if group.protected and not args.include_venv:
            print("Error: .venv is protected. Use --include-venv to delete it.", file=sys.stderr)
            return 2
        return delete_targets(targets_by_group[group.key], assume_yes=args.yes, selection_name=group.label)

    return interactive_menu(targets_by_group)


if __name__ == "__main__":
    raise SystemExit(main())
