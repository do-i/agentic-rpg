# engine/main.py

import argparse
from injector import Injector
from engine.core.app_module import AppModule
from engine.core.game import Game


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", default="./rusted_kingdoms")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    injector = Injector([AppModule(scenario_path=args.scenario)])
    injector.get(Game).run()
