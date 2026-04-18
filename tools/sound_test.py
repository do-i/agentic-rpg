"""
Standalone sound test for diagnosing audio issues.

Run:
    python tools/sound_test.py
    python tools/sound_test.py --driver pulseaudio
    python tools/sound_test.py --scenario ./rusted_kingdoms --bgm town.default
    python tools/sound_test.py --list

Exit codes:
    0 = played successfully
    1 = audio subsystem failure
    2 = file not found / asset error
"""

from __future__ import annotations

import argparse
import ctypes
import os
import subprocess
import sys
import time
from pathlib import Path

import yaml


def _bar(label: str) -> None:
    print(f"\n=== {label} ===")


def _current_audio_driver() -> str:
    try:
        sdl = ctypes.CDLL("libSDL2-2.0.so.0")
        sdl.SDL_GetCurrentAudioDriver.restype = ctypes.c_char_p
        drv = sdl.SDL_GetCurrentAudioDriver()
        return drv.decode() if drv else "(none)"
    except Exception as e:
        return f"(unknown: {e})"


def _load_index(scenario: Path, kind: str) -> dict[str, Path]:
    """BGM uses "category.key"; SFX uses the leaf key — matches the engine's managers."""
    index_path = scenario / "data" / "audio" / f"{kind}_index.yaml"
    if not index_path.exists():
        print(f"  {index_path} not found")
        return {}
    with open(index_path) as f:
        data: dict = yaml.safe_load(f) or {}
    audio_root = scenario / "assets" / "audio"
    out: dict[str, Path] = {}
    for category, entries in data.items():
        if isinstance(entries, dict):
            for key, rel in entries.items():
                name = key if kind == "sfx" else f"{category}.{key}"
                out[name] = audio_root / rel
    return out


def _diag_env() -> None:
    _bar("Environment")
    print(f"  python:           {sys.version.split()[0]}")
    for var in ("SDL_AUDIODRIVER", "PULSE_SERVER", "XDG_RUNTIME_DIR", "WAYLAND_DISPLAY", "DISPLAY"):
        print(f"  {var:17s} {os.environ.get(var, '(unset)')}")


def _diag_mixer() -> None:
    import pygame
    _bar("Mixer")
    print(f"  pygame.version:   {pygame.version.ver}  (SDL {'.'.join(str(x) for x in pygame.version.SDL)})")
    print(f"  mixer init:       {pygame.mixer.get_init()}")
    print(f"  num channels:     {pygame.mixer.get_num_channels()}")
    print(f"  music volume:     {pygame.mixer.music.get_volume():.3f}")
    print(f"  SDL audio driver: {_current_audio_driver()}")


def _play_bgm(path: Path, seconds: float, volume: float) -> bool:
    import pygame
    _bar(f"BGM: {path.name}")
    if not path.exists():
        print(f"  MISSING: {path}")
        return False
    print(f"  path:     {path}  ({path.stat().st_size} bytes)")
    pygame.mixer.music.set_volume(volume)
    pygame.mixer.music.load(str(path))
    pygame.mixer.music.play()
    time.sleep(0.2)
    busy = pygame.mixer.music.get_busy()
    print(f"  busy:     {busy}")
    print(f"  volume:   {pygame.mixer.music.get_volume():.3f}")
    if not busy:
        print("  >>> mixer says NOT busy. Audio backend or decode failed.")
        return False
    print(f"  playing for {seconds:.1f}s... (ctrl-c to cut short)")
    try:
        time.sleep(seconds)
    except KeyboardInterrupt:
        print("  interrupted")
    pygame.mixer.music.stop()
    return True


def _play_sfx(path: Path, volume: float) -> bool:
    import pygame
    _bar(f"SFX: {path.name}")
    if not path.exists():
        print(f"  MISSING: {path}")
        return False
    print(f"  path:     {path}  ({path.stat().st_size} bytes)")
    sound = pygame.mixer.Sound(str(path))
    sound.set_volume(volume)
    ch = sound.play()
    time.sleep(0.1)
    print(f"  channel:  {ch}, busy: {ch.get_busy() if ch else 'n/a'}")
    length = sound.get_length()
    print(f"  length:   {length:.2f}s, volume: {sound.get_volume():.3f}")
    try:
        time.sleep(min(length + 0.2, 3.0))
    except KeyboardInterrupt:
        print("  interrupted")
    return True


def _run(cmd: list[str]) -> str:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        return (r.stdout or r.stderr).strip()
    except FileNotFoundError:
        return f"({cmd[0]} not installed)"
    except Exception as e:
        return f"(error: {e})"


def _pa_snapshot(label: str) -> None:
    _bar(f"PulseAudio {label}")
    print("  default sink:")
    print("    " + _run(["pactl", "get-default-sink"]).replace("\n", "\n    "))
    print("  default sink mute/volume:")
    default_sink = _run(["pactl", "get-default-sink"])
    if default_sink and not default_sink.startswith("("):
        print("    " + _run(["pactl", "get-sink-mute", default_sink]))
        print("    " + _run(["pactl", "get-sink-volume", default_sink]))
    print("  sink-inputs (active streams):")
    out = _run(["pactl", "list", "sink-inputs"])
    if not out or out.startswith("("):
        print(f"    {out or '(none)'}")
    else:
        for line in out.splitlines():
            s = line.strip()
            if any(k in s for k in (
                "Sink Input #", "Sink:", "Mute:", "Volume:", "application.name",
                "application.process.binary", "media.name",
            )):
                print(f"    {s}")


def _probe_drivers(drivers: list[str], path: Path, seconds: float, volume: float) -> None:
    """Fork a child per driver so each gets a fresh pygame/SDL init."""
    _bar("Driver probe")
    script = Path(__file__).resolve()
    for drv in drivers:
        print(f"\n  --- trying SDL_AUDIODRIVER={drv} ---")
        env = os.environ.copy()
        env["SDL_AUDIODRIVER"] = drv
        r = subprocess.run(
            [sys.executable, str(script),
             "--driver", drv, "--bgm", str(path),
             "--seconds", str(seconds), "--bgm-volume", str(volume),
             "--no-sfx", "--no-probe"],
            env=env, capture_output=True, text=True,
        )
        for line in (r.stdout + r.stderr).splitlines():
            print(f"    {line}")


def _list_index(scenario: Path) -> None:
    _bar("Indexed BGM")
    for k, p in sorted(_load_index(scenario, "bgm").items()):
        flag = "OK" if p.exists() else "MISSING"
        print(f"  [{flag:7s}] {k:32s} {p}")
    _bar("Indexed SFX")
    for k, p in sorted(_load_index(scenario, "sfx").items()):
        flag = "OK" if p.exists() else "MISSING"
        print(f"  [{flag:7s}] {k:32s} {p}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scenario", default="./rusted_kingdoms", type=Path)
    ap.add_argument("--bgm",    help="BGM index key (e.g. town.default) or a direct path")
    ap.add_argument("--sfx",    help="SFX index key (e.g. confirm) or a direct path")
    ap.add_argument("--seconds", type=float, default=3.0, help="BGM playback duration")
    ap.add_argument("--bgm-volume", type=float, default=0.6)
    ap.add_argument("--sfx-volume", type=float, default=0.9)
    ap.add_argument("--driver",  help="Force SDL_AUDIODRIVER (e.g. pulseaudio, alsa, pipewire)")
    ap.add_argument("--list",   action="store_true", help="List indexed BGM/SFX assets and exit")
    ap.add_argument("--probe-drivers", action="store_true",
                    help="Run the BGM test once per SDL driver in subprocesses")
    ap.add_argument("--no-sfx",   action="store_true", help="Skip SFX playback (internal)")
    ap.add_argument("--no-probe", action="store_true", help="Skip PulseAudio snapshot (internal)")
    args = ap.parse_args()

    if args.driver:
        os.environ["SDL_AUDIODRIVER"] = args.driver

    _diag_env()

    import pygame
    pygame.init()
    _diag_mixer()
    if not pygame.mixer.get_init():
        print("\nERROR: mixer failed to initialize.")
        return 1

    scenario: Path = args.scenario
    if args.list:
        _list_index(scenario)
        return 0

    # Default: play one known-good BGM and one SFX if none specified.
    bgm_index = _load_index(scenario, "bgm")
    sfx_index = _load_index(scenario, "sfx")
    bgm_key   = args.bgm or "town.default"
    sfx_key   = args.sfx or "confirm"

    def _resolve(key: str, index: dict[str, Path]) -> Path:
        direct = Path(key)
        if direct.exists():
            return direct
        return index.get(key, Path(f"<unresolved:{key}>"))

    bgm_path = _resolve(bgm_key, bgm_index)
    sfx_path = _resolve(sfx_key, sfx_index)

    if args.probe_drivers:
        pygame.mixer.quit()
        pygame.quit()
        _probe_drivers(
            ["pulseaudio", "pipewire", "alsa", "sndio", "jack"],
            bgm_path, min(args.seconds, 2.0), args.bgm_volume,
        )
        return 0

    if not args.no_probe:
        _pa_snapshot("before play")

    ok_bgm = _play_bgm(bgm_path, args.seconds, args.bgm_volume)

    if not args.no_probe:
        # snapshot while still playing
        pygame.mixer.music.load(str(bgm_path))
        pygame.mixer.music.set_volume(args.bgm_volume)
        pygame.mixer.music.play()
        time.sleep(0.3)
        _pa_snapshot("during play (second pass)")
        pygame.mixer.music.stop()
    ok_sfx = False if args.no_sfx else _play_sfx(sfx_path, args.sfx_volume)

    _bar("Result")
    print(f"  BGM played: {ok_bgm}")
    print(f"  SFX played: {ok_sfx}")
    print("\nIf mixer says 'busy: True' but you hear nothing, the mixer is fine")
    print("and the problem is elsewhere: system output device, volume, or sink routing.")
    print("Try:  paplay <any wav>    or    --driver alsa    to bypass pulseaudio.")

    pygame.quit()
    return 0 if (ok_bgm or ok_sfx) else 2


if __name__ == "__main__":
    sys.exit(main())
