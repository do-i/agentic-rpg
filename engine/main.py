# engine/main.py

import argparse
from engine.core.container import Container


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", required=True)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    container = Container()
    container.config.scenario_path.from_value(args.scenario)

    container.scene_manager().switch(container.boot_scene())
    container.game().run()