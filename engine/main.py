# engine/main.py

import argparse
from engine.core.container import Container


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--scenario",
        required=True,
        help="Path to scenario directory (e.g. ./rusted_kingdoms)"
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    container = Container()
    game = container.game()
    game.run()
