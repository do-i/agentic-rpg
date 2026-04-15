# engine/main.py

import argparse
from injector import Injector
from engine.app_module import AppModule
from engine.game import Game


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", default="./rusted_kingdoms")
    parser.add_argument(
        "--mode",
        choices=["normal", "record", "playback"],
        default="normal",
    )
    parser.add_argument("--recording-file", default="recording.pkl")
    parser.add_argument("--playback-speed", type=float, default=1.0)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    injector = Injector([AppModule(
        scenario_path=args.scenario,
        mode=args.mode,
        recording_file=args.recording_file,
        playback_speed=args.playback_speed,
    )])
    injector.get(Game).run()
