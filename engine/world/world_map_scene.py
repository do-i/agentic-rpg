# engine/world/world_map_scene.py
# Thin orchestrator: delegates logic to world_map_logic.


import pygame
import yaml
from engine.world.position_data import Position
from engine.common.scene.scene import Scene
from engine.common.scene.scene_manager import SceneManager
from engine.common.scene.scene_registry import SceneRegistry
from engine.common.game_state_holder import GameStateHolder
from engine.io.save_manager import GameStateManager
from engine.dialogue.dialogue_engine import DialogueEngine
from engine.title.save_modal_scene import SaveModalScene
from engine.dialogue.dialogue_scene import DialogueScene
from engine.battle.battle_scene import BattleScene
from engine.shop.magic_core_shop_scene import MagicCoreShopScene
from engine.inn.inn_scene import InnScene
from engine.shop.item_shop_scene import ItemShopScene
from engine.shop.apothecary_scene import ApothecaryScene
from engine.encounter.encounter_manager import EncounterManager
from engine.encounter.encounter_resolver import EncounterResolver
from engine.encounter.enemy_spawner import EnemySpawner
from engine.encounter.enemy_sprite import EnemySprite
from engine.item.item_effect_handler import ItemEffectHandler
from engine.item.magic_core_catalog_state import MagicCoreCatalogState
from engine.world.world_map_logic import (
    FADE_SPEED, try_interact, dispatch_dialogue_result,
    check_portals, apply_transition,
    load_inn_cost, load_shop_items, load_recipes, _is_player_facing,
)
from engine.world.player import COLLISION_W, COLLISION_H
from engine.io.manifest_loader import ManifestLoader
from engine.world.tile_map import TileMap
from engine.world.tile_map_factory import TileMapFactory
from engine.world.camera import Camera
from engine.world.player import Player
from engine.world.sprite_sheet import SpriteSheet
from engine.world.npc import Npc
from engine.world.npc_loader import NpcLoader
from engine.world.world_map_renderer import WorldMapRenderer
from engine.audio.bgm_manager import BgmManager
from engine.audio.sfx_manager import SfxManager


class WorldMapScene(Scene):
    """
    Phase 6 — adds Magic Core Shop overlay support.
    Visible enemy system: enemies spawn on the map and battle triggers on collision.
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
        encounter_resolver: EncounterResolver | None = None,
        enemy_spawn_global_interval: float = 30.0,
        effect_handler: ItemEffectHandler | None = None,
        mc_catalog: MagicCoreCatalogState | None = None,
        text_speed: str = "fast",
        smooth_collision: bool = True,
        mc_exchange_confirm_large: bool = True,
        bgm_manager: BgmManager | None = None,
        sfx_manager: SfxManager | None = None,
        screen_width: int = 1280,
        screen_height: int = 766,
        tile_size: int = 32,
        fps: int = 60,
        recorder=None,
        rng=None,
    ) -> None:
        self._screen_width = screen_width
        self._screen_height = screen_height
        self._tile_size = tile_size
        self._fps = fps
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
        self._encounter_resolver = encounter_resolver
        self._enemy_spawn_global_interval = enemy_spawn_global_interval
        self._effect_handler = effect_handler
        self._text_speed = text_speed
        self._mc_exchange_confirm_large = mc_exchange_confirm_large
        self._mc_catalog = mc_catalog or MagicCoreCatalogState()
        self._bgm_manager = bgm_manager
        self._sfx_manager = sfx_manager
        self._recorder = recorder
        self._rng = rng

        self._renderer = WorldMapRenderer()
        self._reset_state()

    def _reset_state(self) -> None:
        self._tile_map: TileMap | None = None
        self._camera: Camera | None = None
        self._player: Player | None = None
        self._npcs: list[Npc] = []
        self._enemy_spawner: EnemySpawner | None = None
        self._engaged_enemy: EnemySprite | None = None

        self._save_modal: SaveModalScene | None = None
        self._dialogue: DialogueScene | None = None
        self._mc_shop: MagicCoreShopScene | None = None
        self._inn: InnScene | None = None
        self._item_shop: ItemShopScene | None = None
        self._apothecary: ApothecaryScene | None = None
        self._quit_confirm: bool = False

        self._fade_alpha: int = 255
        self._fade_dir: int = -1
        self._pending_transition: dict | None = None

    def reset(self) -> None:
        """Re-initialize for a new game/load session. Clears all map state so _init() reruns."""
        self._reset_state()

    def _init(self) -> None:
        scenario_path = self._loader.scenario_path
        manifest = self._loader.load()
        state = self._holder.get()
        map_id = state.map.current

        tmx_path = scenario_path / "assets" / "maps" / f"{map_id}.tmx"
        self._tile_map = self._tile_map_factory.create(str(tmx_path))
        self._camera = Camera(
            self._tile_map.width_px, self._tile_map.height_px,
            self._screen_width, self._screen_height,
        )

        sprite_sheet = self._load_protagonist_sprite(manifest, scenario_path)
        self._player = Player(
            start=state.map.position,
            map_width_px=self._tile_map.width_px,
            map_height_px=self._tile_map.height_px,
            sprite_sheet=sprite_sheet,
            smooth_collision=self._smooth_collision,
            tile_size=self._tile_size,
            fps=self._fps,
        )

        map_yaml_path = scenario_path / "data" / "maps" / f"{map_id}.yaml"
        self._npcs = self._npc_loader.load_from_map(map_yaml_path)

        # BGM
        if self._bgm_manager and map_yaml_path.exists():
            with open(map_yaml_path) as f:
                map_data = yaml.safe_load(f) or {}
            bgm_key = map_data.get("bgm")
            if bgm_key:
                self._bgm_manager.play_key(bgm_key)

        # Encounter zone + enemy spawner
        self._encounter_manager.set_zone(map_id)
        self._enemy_spawner = self._build_spawner(map_yaml_path, map_id, scenario_path)
        if self._enemy_spawner:
            self._enemy_spawner.init_spawn(state.flags)

        self._fade_alpha = 255
        self._fade_dir = -1
        self._pending_transition = None

    def _build_spawner(self, map_yaml_path, map_id, scenario_path) -> EnemySpawner | None:
        """Create EnemySpawner if this map has an encounter zone and spawn tiles."""
        zone = self._encounter_manager.get_zone()
        if zone is None:
            return None   # town or non-encounter map
        if self._encounter_resolver is None:
            return None
        if not self._tile_map.enemy_spawn_tiles:
            return None   # no spawn points defined in TMX

        # Parse map-level spawn config
        map_interval: float | None = None
        if map_yaml_path.exists():
            with open(map_yaml_path) as f:
                map_data = yaml.safe_load(f) or {}
            spawn_cfg = map_data.get("enemy_spawn") or {}
            raw_interval = spawn_cfg.get("interval")
            if raw_interval is not None:
                map_interval = float(raw_interval)

        return EnemySpawner(
            zone=zone,
            spawn_tiles=self._tile_map.enemy_spawn_tiles,
            map_interval=map_interval,
            global_interval=self._enemy_spawn_global_interval,
            resolver=self._encounter_resolver,
            scenario_path=scenario_path,
            rng=self._rng,
            tile_size=self._tile_size,
            boss_tile=self._tile_map.boss_spawn_tile,
        )

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
                        pygame.event.post(pygame.event.Event(pygame.QUIT))
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
            sfx_manager=self._sfx_manager,
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
            sfx_manager=self._sfx_manager,
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
            sfx_manager=self._sfx_manager,
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
            sfx_manager=self._sfx_manager,
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
            sfx_manager=self._sfx_manager,
        )

    def _close_apothecary(self) -> None:
        self._apothecary = None

    # ── Battle ────────────────────────────────────────────────

    def _launch_battle_from_enemy(self, enemy: EnemySprite) -> None:
        """Build a BattleState from a visible enemy sprite and switch to BattleScene."""
        state = self._holder.get()

        # Store the enemy; it will be deactivated on the first update tick after battle ends.
        self._engaged_enemy = enemy

        # Build battle state
        zone = self._encounter_manager.get_zone()
        inventory_ids: set[str] = {entry.id for entry in state.repository.items}

        if enemy.is_boss and zone:
            from engine.common.flag_state import FlagState
            battle_state = self._encounter_resolver.build_battle_from_boss(
                zone, state.flags
            )
        elif zone:
            from engine.encounter.encounter_zone_data import Formation
            formation = Formation(
                enemy_ids=enemy.formation,
                weight=1,
                chase_range=enemy.chase_range,
            )
            battle_state = self._encounter_resolver.build_battle_from_formation(
                formation, zone, inventory_ids
            )
        else:
            return

        if battle_state is None:
            return

        boss_flag = getattr(battle_state, "boss_flag", "")
        battle_state = self._encounter_manager.fill_party(battle_state, state.party)
        state.map.set_position(self._player.tile_position)

        scene = BattleScene(
            battle_state=battle_state,
            scene_manager=self._scene_manager,
            registry=self._registry,
            holder=self._holder,
            scenario_path=str(self._loader.scenario_path),
            boss_flag=boss_flag,
            effect_handler=self._effect_handler,
            game_state_manager=self._game_state_manager,
            bgm_manager=self._bgm_manager,
            sfx_manager=self._sfx_manager,
            rng=self._rng,
        )
        self._scene_manager.switch(scene)

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
        self._enemy_spawner = None

    # ── Update ────────────────────────────────────────────────

    def update(self, delta: float) -> None:
        # Deactivate the enemy that triggered the last battle (first tick after returning).
        if self._engaged_enemy is not None:
            if self._enemy_spawner:
                self._enemy_spawner.on_enemy_engaged(self._engaged_enemy)
            self._engaged_enemy = None

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

        keys = self._recorder.get_key_state() if self._recorder else pygame.key.get_pressed()
        frozen = self._fade_dir != 0
        state = self._holder.get()

        # Build collision rects — only NPCs block the player as solid walls.
        # Enemy sprites are trigger volumes: player walks into them to start battle.
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

        # Update enemy spawner and check for collision-based battle trigger
        if self._enemy_spawner and not frozen:
            self._enemy_spawner.update(
                delta,
                player_pos.x,
                player_pos.y,
                self._tile_map.collision_map,
                state.party,
            )
            col = self._player.collision_rect_position
            player_rect = (col.x, col.y, COLLISION_W, COLLISION_H)
            colliding = self._enemy_spawner.check_player_collision(player_rect)
            if colliding:
                self._launch_battle_from_enemy(colliding)
                return

        self._check_portals()

    # ── Render (delegates to WorldMapRenderer) ─────────────────

    def render(self, screen: pygame.Surface) -> None:
        if self._tile_map is None:
            self._init()

        state = self._holder.get()
        visible_npcs = [npc for npc in self._npcs if npc.is_present(state.flags)]
        enemy_sprites = self._enemy_spawner.active_enemies if self._enemy_spawner else []

        overlays = [
            o for o in (
                self._save_modal, self._dialogue, self._mc_shop,
                self._inn, self._item_shop, self._apothecary,
            ) if o is not None
        ]

        self._renderer.render(
            screen,
            self._tile_map,
            self._camera,
            self._player,
            visible_npcs,
            enemy_sprites,
            overlays,
            self._dialogue,
            self._fade_alpha,
            self._quit_confirm,
        )
