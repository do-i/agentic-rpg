# engine/main.py

from __future__ import annotations

import argparse
import pygame
from injector import Injector
from engine.app_module import AppModule
from engine.game import Game


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", required=True,
                        help="path to a scenario package directory")
    parser.add_argument(
        "--mode",
        choices=["normal", "record", "playback"],
        default="record",
    )
    parser.add_argument("--recording-file", default="recording.pkl")
    parser.add_argument("--playback-speed", type=float, default=1.0)

    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument(
        "--profile",
        metavar="FILE",
        default=None,
        help="profile the run with cProfile; writes pstats data to FILE "
             "and prints the top functions by cumulative time on exit",
    )
    return parser.parse_args()


def run_profiled(game: Game, stats_file: str) -> None:
    import cProfile
    import pstats

    profiler = cProfile.Profile()
    try:
        profiler.runcall(game.run)
    finally:
        # Dump even on Ctrl-C so an interrupted session still yields a profile.
        profiler.dump_stats(stats_file)
        pstats.Stats(profiler).sort_stats("cumulative").print_stats(30)
        print(f"profile written to {stats_file}")


if __name__ == "__main__":
    args = parse_args()
    pygame.init()
    injector = Injector([AppModule(
        scenario_path=args.scenario,
        mode=args.mode,
        recording_file=args.recording_file,
        playback_speed=args.playback_speed,
        seed=args.seed,
    )])
    game = injector.get(Game)
    if args.profile:
        run_profiled(game, args.profile)
    else:
        game.run()
