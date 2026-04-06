# engine/core/scenes/world_map_scene.py
# Thin orchestrator: delegates logic to world_map_logic.

import sys

import pygame
import yaml
from engine.core.models.position import Position
from engine.core.scene import Scene
from engine.core.scene_manager import SceneManager
from engine.core.scene_registry import SceneRegistry
from engine.core.settings import Settings
from engine.core.state.game_state_holder import GameStateHolder
from engine.core.state.game_state_manager import GameStateManager
from engine.core.dialogue.dialogue_engine import DialogueEngine
from engine.core.scenes.save_modal_scene import SaveModalScene
from engine.core.scenes.dialogue_scene import DialogueScene
from engine.core.scenes.battle_scene import BattleScene
from engine.core.scenes.magic_core_shop_scene import MagicCoreShopScene
from engine.core.scenes.inn_scene import InnScene
from engine.core.scenes.item_shop_scene import ItemShopScene
from engine.core.scenes.apothecary_scene import ApothecaryScene
from engine.core.encounter.encounter_manager import EncounterManager
from engine.core.item.item_effect_handler import ItemEffectHandler
from engine.core.scenes.item_logic import MCCatalog
from engine.core.scenes.world_map_logic import (
    FADE_SPEED, try_interact, dispatch_dialogue_result,
    check_encounter, check_portals, apply_transition,
    load_inn_cost, load_shop_items, load_recipes, _is_player_facing,
)
from engine.data.loader import ManifestLoader
from engine.world.tile_map import TileMap
from engine.world.tile_map_factory import TileMapFactory
from engine.world.camera import Camera
from engine.world.player import Player
from engine.world.sprite_sheet import SpriteSheet
from engine.world.npc import Npc
from engine.world.npc_loader import NpcLoader


class WorldMapScene(Scene):
    """
    Phase 6 — adds Magic Core Shop overlay support.
    """

    def __init__(
        self,
        holder: GameStateHolder,
        loader: ManifestLoader,
        tile_map_factory: TileMapFactory,
        scene_manager: SceneManager,
        registry: SceneRegistry,
        game_state_manager: GameStateManager,
        dialogue_engine: DialogueEngine,
        npc_loader: NpcLoader,
        encounter_manager: EncounterManager,
        effect_handler: ItemEffectHandler | None = None,
        mc_catalog: MCCatalog | None = None,
        text_speed: str = "fast",
        smooth_collision: bool = True,
        mc_exchange_confirm_large: bool = True,
    ) -> None:
        self._smooth_collision = smooth_collision
        self._holder = holder
        self._loader = loader
        self._tile_map_factory = tile_map_factory
        self._scene_manager = scene_manager
        self._registry = registry
        self._game_state_manager = game_state_manager
        self._dialogue_engine = dialogue_engine
        self._npc_loader = npc_loader
        self._encounter_manager = encounter_manager
        self._effect_handler = effect_handler
        self._text_speed = text_speed
        self._mc_exchange_confirm_large = mc_exchange_confirm_large
        self._mc_catalog = mc_catalog or MCCatalog()

        self._tile_map: TileMap | None = None
        self._camera: Camera | None = None
        self._player: Player | None = None
        self._npcs: list[Npc] = []

        self._save_modal: SaveModalScene | None = None
        self._dialogue: DialogueScene | None = None
        self._mc_shop: MagicCoreShopScene | None = None
        self._inn: InnScene | None = None
        self._item_shop: ItemShopScene | None = None
        self._apothecary: ApothecaryScene | None = None
        self._quit_confirm: bool = False
        self._quit_font: pygame.font.Font | None = None

        self._fade_alpha: int = 255
        self._fade_dir: int = -1
        self._pending_transition: dict | None = None

        self._last_tile: Position | None = None

    def _init(self) -> None:
        scenario_path = self._loader.scenario_path
        manifest = self._loader.load()
        state = self._holder.get()
        map_id = state.map.current

        tmx_path = scenario_path / "assets" / "maps" / f"{map_id}.tmx"
        self._tile_map = self._tile_map_factory.create(str(tmx_path))
        self._camera = Camera(self._tile_map.width_px, self._tile_map.height_px)

        sprite_sheet = self._load_protagonist_sprite(manifest, scenario_path)
        self._player = Player(
            start=state.map.position,
            map_width_px=self._tile_map.width_px,
            map_height_px=self._tile_map.height_px,
            sprite_sheet=sprite_sheet,
            smooth_collision=self._smooth_collision,
        )

        map_yaml = scenario_path / "data" / "maps" / f"{map_id}.yaml"
        self._npcs = self._npc_loader.load_from_map(map_yaml)

        self._encounter_manager.set_zone(map_id)
        self._last_tile = self._player.tile_position

        self._fade_alpha = 255
        self._fade_dir = -1
        self._pending_transition = None

        print(f"[DEBUG] loading map={map_id} pos={state.map.position}")

    def _load_protagonist_sprite(self, manifest: dict, scenario_path) -> SpriteSheet | None:
        sprite_path = manifest.get("protagonist", {}).get("sprite")
        if not sprite_path:
            return None
        full_path = scenario_path / sprite_path
        if not full_path.exists():
            print(f"[WARN] sprite not found: {full_path}")
            return None
        try:
            return SpriteSheet(full_path)
        except Exception as e:
            print(f"[WARN] failed to load sprite: {e}")
            return None

    # ── Events ────────────────────────────────────────────────

    def handle_events(self, events: list[pygame.event.Event]) -> None:
        if self._fade_alpha > 0 and self._fade_dir == -1:
            return
        if self._fade_dir == 1:
            return

        if self._dialogue:
            self._dialogue.handle_events(events)
            return
        if self._save_modal:
            self._save_modal.handle_events(events)
            return
        if self._mc_shop:
            self._mc_shop.handle_events(events)
            return
        if self._inn:
            self._inn.handle_events(events)
            return
        if self._item_shop:
            self._item_shop.handle_events(events)
            return
        if self._apothecary:
            self._apothecary.handle_events(events)
            return
        if self._quit_confirm:
            for event in events:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        pygame.quit()
                        sys.exit(0)
                    elif event.key == pygame.K_ESCAPE:
                        self._quit_confirm = False
            return

        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self._quit_confirm = True
                elif event.key == pygame.K_F2:
                    self._open_save_modal()
                elif event.key == pygame.K_s:
                    self._scene_manager.switch(self._registry.get("status"))
                elif event.key == pygame.K_RETURN:
                    self._try_interact()
                elif event.key == pygame.K_i:
                    self._scene_manager.switch(self._registry.get("items"))

    def _open_save_modal(self) -> None:
        state = self._holder.get()
        state.map.set_position(self._player.tile_position)
        self._save_modal = SaveModalScene(
            game_state_manager=self._game_state_manager,
            state=self._holder.get(),
            on_close=self._close_save_modal,
        )

    def _close_save_modal(self) -> None:
        self._save_modal = None

    def _try_interact(self) -> None:
        state = self._holder.get()
        result, npc = try_interact(
            self._player, self._npcs, state.flags, self._dialogue_engine,
        )
        if result:
            self._dialogue = DialogueScene(
                result=result,
                on_complete=self._on_dialogue_complete,
                text_speed=self._text_speed,
                portrait=npc.portrait if npc else None,
            )

    def _on_dialogue_complete(self, on_complete: dict) -> None:
        self._dialogue = None
        if not on_complete:
            return
        state = self._holder.get()
        remaining = dispatch_dialogue_result(
            on_complete, state.flags, state.repository, self._dialogue_engine,
        )

        shop_type = remaining.get("open_shop")
        if shop_type == "magic_core":
            self._open_mc_shop()
            return
        if shop_type == "item":
            self._open_item_shop()
            return

        if remaining.get("open_apothecary"):
            self._open_apothecary()
            return

        if remaining.get("open_inn"):
            self._open_inn()
            return

        transition = remaining.get("transition")
        if transition:
            self._start_fade_out(transition)

    # ── Magic Core Shop ───────────────────────────────────────

    def _open_mc_shop(self) -> None:
        self._mc_shop = MagicCoreShopScene(
            holder=self._holder,
            scene_manager=self._scene_manager,
            registry=self._registry,
            on_close=self._close_mc_shop,
            mc_sizes=self._mc_catalog.sizes,
            confirm_large=self._mc_exchange_confirm_large,
        )

    def _close_mc_shop(self) -> None:
        self._mc_shop = None

    # ── Inn ───────────────────────────────────────────────────

    def _open_inn(self) -> None:
        state    = self._holder.get()
        state.map.set_position(self._player.tile_position)
        map_id   = state.map.current
        cost = load_inn_cost(self._loader.scenario_path, map_id)
        sprite_path = self._loader.scenario_path / "assets" / "sprites" / "npc" / "female_blue_01.tsx"
        self._inn = InnScene(
            holder=self._holder,
            scene_manager=self._scene_manager,
            registry=self._registry,
            on_close=self._close_inn,
            cost=cost,
            sprite_path=sprite_path,
        )

    def _close_inn(self) -> None:
        self._inn = None

    # ── Item Shop ─────────────────────────────────────────────

    def _open_item_shop(self) -> None:
        state    = self._holder.get()
        map_id   = state.map.current
        shop_items = load_shop_items(self._loader.scenario_path, map_id)
        sprite_path = self._loader.scenario_path / "assets" / "sprites" / "npc" / "teen_halfmessy_01.tsx"
        self._item_shop = ItemShopScene(
            holder=self._holder,
            scene_manager=self._scene_manager,
            registry=self._registry,
            on_close=self._close_item_shop,
            shop_items=shop_items,
            sprite_path=sprite_path,
        )

    def _close_item_shop(self) -> None:
        self._item_shop = None

    # ── Apothecary ────────────────────────────────────────────

    def _open_apothecary(self) -> None:
        recipes = load_recipes(self._loader.scenario_path)
        sprite_path = self._loader.scenario_path / "assets" / "sprites" / "npc" / "female_wiz_01.tsx"
        self._apothecary = ApothecaryScene(
            holder=self._holder,
            scene_manager=self._scene_manager,
            registry=self._registry,
            on_close=self._close_apothecary,
            recipes=recipes,
            sprite_path=sprite_path,
        )

    def _close_apothecary(self) -> None:
        self._apothecary = None

    # ── Encounter ─────────────────────────────────────────────

    def _check_encounter(self) -> bool:
        battle_state, boss_flag = check_encounter(
            self._holder, self._encounter_manager, self._player,
        )
        if battle_state is None:
            return False
        self._launch_battle(battle_state, boss_flag=boss_flag)
        return True

    def _launch_battle(self, battle_state, boss_flag: str = "") -> None:
        scene = BattleScene(
            battle_state=battle_state,
            scene_manager=self._scene_manager,
            registry=self._registry,
            holder=self._holder,
            scenario_path=str(self._loader.scenario_path),
            boss_flag=boss_flag,
            effect_handler=self._effect_handler,
            game_state_manager=self._game_state_manager,
        )
        self._scene_manager.switch(scene)

    def _on_battle_defeat(self) -> None:
        self._scene_manager.switch(self._registry.get("world_map"))

    # ── Portal ────────────────────────────────────────────────

    def _check_portals(self) -> None:
        transition = check_portals(self._tile_map, self._player)
        if transition:
            self._start_fade_out(transition)

    # ── Fade & Transition ─────────────────────────────────────

    def _start_fade_out(self, transition: dict) -> None:
        if self._fade_dir == 1:
            return
        self._pending_transition = transition
        self._fade_dir = 1
        self._fade_alpha = 0

    def _apply_transition(self) -> None:
        apply_transition(
            self._holder, self._game_state_manager,
            self._player, self._pending_transition,
        )
        self._tile_map = None
        self._player = None

    # ── Update ────────────────────────────────────────────────

    def update(self, delta: float) -> None:
        if self._fade_dir != 0:
            self._fade_alpha += int(FADE_SPEED * delta) * self._fade_dir
            if self._fade_dir == 1 and self._fade_alpha >= 255:
                self._fade_alpha = 255
                self._fade_dir = 0
                self._apply_transition()
                return
            elif self._fade_dir == -1 and self._fade_alpha <= 0:
                self._fade_alpha = 0
                self._fade_dir = 0

        if self._dialogue:
            self._dialogue.update(delta)
            return
        if self._save_modal:
            self._save_modal.update(delta)
            return
        if self._mc_shop:
            self._mc_shop.update(delta)
            return
        if self._inn:
            self._inn.update(delta)
            return
        if self._item_shop:
            self._item_shop.update(delta)
            return
        if self._apothecary:
            self._apothecary.update(delta)
            return
        if self._quit_confirm:
            return
        if self._player is None:
            return

        keys = pygame.key.get_pressed()
        frozen = self._fade_dir != 0
        state = self._holder.get()
        npc_rects = [
            npc.collision_rect
            for npc in self._npcs
            if npc.is_present(state.flags)
        ]
        self._player.update(keys, self._tile_map.collision_map, frozen, npc_rects=npc_rects)
        self._camera.update(self._player.pixel_position)

        player_pos = self._player.pixel_position
        visible_npcs = [n for n in self._npcs if n.is_present(state.flags)]
        for npc in visible_npcs:
            other_rects = [n.collision_rect for n in visible_npcs if n is not npc]
            notices = (npc.is_near(player_pos)
                       and npc.is_facing_toward(player_pos)
                       and _is_player_facing(self._player, npc.pixel_position))
            npc.update(delta, near=notices,
                       collision_map=self._tile_map.collision_map,
                       npc_rects=other_rects)

        current_tile = self._player.tile_position
        if current_tile != self._last_tile:
            self._last_tile = current_tile
            if not self._check_encounter():
                self._check_portals()
        else:
            self._check_portals()

    # ── Quit Confirm ──────────────────────────────────────────

    def _render_quit_confirm(self, screen: pygame.Surface) -> None:
        if self._quit_font is None:
            self._quit_font = pygame.font.SysFont("Arial", 20, bold=True)
        font = self._quit_font
        hint_font = pygame.font.SysFont("Arial", 16)

        w, h = 320, 110
        x = (Settings.SCREEN_WIDTH - w) // 2
        y = (Settings.SCREEN_HEIGHT - h) // 2

        overlay = pygame.Surface((Settings.SCREEN_WIDTH, Settings.SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        screen.blit(overlay, (0, 0))

        pygame.draw.rect(screen, (20, 20, 45), (x, y, w, h))
        pygame.draw.rect(screen, (160, 160, 100), (x, y, w, h), 2)

        title = font.render("Quit Game?", True, (220, 220, 180))
        screen.blit(title, (x + w // 2 - title.get_width() // 2, y + 18))

        hint = hint_font.render("ENTER  confirm       ESC  cancel", True, (160, 160, 120))
        screen.blit(hint, (x + w // 2 - hint.get_width() // 2, y + 68))

    # ── Render ────────────────────────────────────────────────

    def render(self, screen: pygame.Surface) -> None:
        if self._tile_map is None:
            self._init()

        screen.fill((0, 0, 0))
        self._tile_map.render(screen, self._camera.offset_x, self._camera.offset_y)

        state = self._holder.get()
        player_pos = self._player.pixel_position

        visible_npcs = [npc for npc in self._npcs if npc.is_present(state.flags)]

        def render_player():
            self._player.render(screen, self._camera.offset_x, self._camera.offset_y)

        def render_npc(npc):
            near = (npc.is_near(player_pos)
                    and npc.is_facing_toward(player_pos)
                    and _is_player_facing(self._player, npc.pixel_position)
                    and self._dialogue is None)
            npc.render(
                screen,
                self._camera.offset_x,
                self._camera.offset_y,
                near=near,
                player_pos=player_pos,
            )

        drawables = [(player_pos.y, render_player)] + [
            (npc._py, lambda n=npc: render_npc(n)) for npc in visible_npcs
        ]
        for _, draw in sorted(drawables, key=lambda d: d[0]):
            draw()

        if self._save_modal:
            self._save_modal.render(screen)
        if self._dialogue:
            self._dialogue.render(screen)
        if self._mc_shop:
            self._mc_shop.render(screen)
        if self._inn:
            self._inn.render(screen)
        if self._item_shop:
            self._item_shop.render(screen)
        if self._apothecary:
            self._apothecary.render(screen)
        if self._quit_confirm:
            self._render_quit_confirm(screen)

        if self._fade_alpha > 0:
            fade_surf = pygame.Surface(
                (Settings.SCREEN_WIDTH, Settings.SCREEN_HEIGHT), pygame.SRCALPHA
            )
            fade_surf.fill((0, 0, 0, self._fade_alpha))
            screen.blit(fade_surf, (0, 0))
