from __future__ import annotations

import argparse
from pathlib import Path

import pygame
from injector import Injector

from engine.app_module import AppModule
from engine.common.font_provider import FontProvider
from engine.common.game_state import GameState
from engine.common.game_state_holder import GameStateHolder
from engine.common.scene.scene import Scene
from engine.common.scene.scene_registry import SceneRegistry
from engine.common.ui.framebuffer import ensure_framebuffer, present_frame
from engine.party.member_state import MemberState
from engine.settings.engine_config_data import EngineConfigData


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCENARIO = ROOT / "rusted_kingdoms"
SCENES = {
    pygame.K_1: ("title", "Title"),
    pygame.K_2: ("field_menu", "Field Menu"),
    pygame.K_3: ("status", "Status"),
    pygame.K_4: ("spells", "Spells"),
    pygame.K_5: ("items", "Items"),
    pygame.K_6: ("equip", "Equipment"),
    pygame.K_7: ("quest_board", "Quests"),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Small real-scene repro for menu title/panel transparency issues."
    )
    parser.add_argument("--scenario", type=Path, default=DEFAULT_SCENARIO)
    parser.add_argument(
        "--scene",
        choices=[name for name, _ in SCENES.values()],
        default="field_menu",
    )
    parser.add_argument(
        "--direct",
        action="store_true",
        help="render directly to the display surface",
    )
    parser.add_argument("--dump-only", action="store_true")
    parser.add_argument("--screenshot", type=Path, default=ROOT / "menu-alpha-repro.png")
    return parser.parse_args()


def make_member(
    member_id: str,
    name: str,
    class_name: str,
    hp: int,
    hp_max: int,
    mp: int,
    mp_max: int,
    *,
    protagonist: bool = False,
) -> MemberState:
    member = MemberState(
        member_id=member_id,
        name=name,
        protagonist=protagonist,
        class_name=class_name,
        level=7,
        exp=640,
        exp_next=1000,
        hp=hp,
        hp_max=hp_max,
        mp=mp,
        mp_max=mp_max,
        str_=16,
        dex=14,
        con=13,
        int_=12,
        equipped={"weapon": "iron_sword", "body": "chainmail"},
    )
    member.equipment_slots = {
        "weapon": ["weapons"],
        "body": ["body"],
        "shield": ["shields"],
        "helmet": ["helmets"],
    }
    return member


def seed_state(holder: GameStateHolder) -> None:
    state = GameState()
    state.map.current = "town_01_ardel"
    state.map.display_name = "Town of Ardel"
    for member in [
        make_member("aric", "Aric", "Hero", 142, 160, 38, 54, protagonist=True),
        make_member("elise", "Elise", "Cleric", 118, 132, 74, 92),
        make_member("reiya", "Reiya", "Sorcerer", 92, 104, 88, 116),
    ]:
        state.party.add_member(member)
    holder.set(state)


def scene_for(registry: SceneRegistry, key: str) -> Scene:
    scene = registry.get(key)
    setter = getattr(scene, "set_return_scene", None)
    if setter is not None:
        setter("field_menu")
    return scene


def print_environment(screen: pygame.Surface) -> None:
    print("Menu alpha repro")
    print(f"pygame={pygame.version.ver} sdl={'.'.join(map(str, pygame.version.SDL))}")
    if hasattr(pygame.font, "get_sdl_ttf_version"):
        print(f"sdl_ttf={'.'.join(map(str, pygame.font.get_sdl_ttf_version()))}")
    print(f"video_driver={pygame.display.get_driver()}")
    print(f"display_size={screen.get_size()} flags={screen.get_flags()} masks={screen.get_masks()}")
    print(
        "keys: 1 title, 2 field, 3 status, 4 spells, 5 items, "
        "6 equip, 7 quests, S screenshot, ESC quit"
    )


def render_scene(
    screen: pygame.Surface,
    framebuffer: pygame.Surface | None,
    scene: Scene,
    label: str,
    *,
    direct: bool,
) -> pygame.Surface | None:
    if direct:
        scene.render(screen)
    else:
        framebuffer = ensure_framebuffer(framebuffer, screen.get_size())
        scene.render(framebuffer)
        present_frame(screen, framebuffer)
    pygame.display.flip()
    print(f"rendered {label}")
    return framebuffer


def main() -> int:
    args = parse_args()
    pygame.init()

    injector = Injector([
        AppModule(
            scenario_path=str(args.scenario),
            mode="normal",
            recording_file="debug-menu-alpha.pkl",
            seed=1,
        )
    ])
    config = injector.get(EngineConfigData)
    screen = pygame.display.set_mode(
        (config.screen_width, config.screen_height),
        pygame.RESIZABLE,
    )
    pygame.display.set_caption("Menu Alpha Repro")

    injector.get(FontProvider)
    registry = injector.get(SceneRegistry)
    holder = injector.get(GameStateHolder)
    seed_state(holder)

    print_environment(screen)

    active_key = args.scene
    active_label = next(label for key, label in SCENES.values() if key == active_key)
    active_scene = scene_for(registry, active_key)
    framebuffer: pygame.Surface | None = None
    framebuffer = render_scene(
        screen,
        framebuffer,
        active_scene,
        active_label,
        direct=args.direct,
    )

    if args.dump_only:
        pygame.image.save(screen, str(args.screenshot))
        print(f"saved {args.screenshot}")
        pygame.quit()
        return 0

    running = True
    while running:
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_s:
                    pygame.image.save(screen, str(args.screenshot))
                    print(f"saved {args.screenshot}")
                elif event.key in SCENES:
                    active_key, active_label = SCENES[event.key]
                    active_scene = scene_for(registry, active_key)
                    framebuffer = render_scene(
                        screen,
                        framebuffer,
                        active_scene,
                        active_label,
                        direct=args.direct,
                    )
        active_scene.handle_events(events)
        active_scene.update(0.0)
        pygame.time.wait(16)

    pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
