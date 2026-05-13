from __future__ import annotations

import argparse
from pathlib import Path

from tools.map_editor.app import App


def main() -> None:
    parser = argparse.ArgumentParser(prog="map_editor", description="JRPG scenario map viewer/editor.")
    parser.add_argument(
        "--scenario",
        required=True,
        type=Path,
        help="Path to a scenario root (containing manifest.yaml), e.g. ./rusted_kingdoms",
    )
    args = parser.parse_args()
    App(args.scenario).run()


if __name__ == "__main__":
    main()
