# engine/world/world_map_scene.py
#
# Per-frame orchestrator for the world map: routes events to the active
# overlay (or to the player), advances the fade state machine, runs movement
# + collision + spawner, and delegates rendering to WorldMapRenderer. Map
# loading lives in world_map_init, battle launch in world_map_battle_launcher,
# fade alpha in fade_controller, and overlay routing in world_map_overlays.

import pygame

from engine.audio.bgm_manager import BgmManager
from engine.audio.sfx_manager import SfxManager
from engine.common.game_state_holder import GameStateHolder
from engine.common.scene.scene import Scene
from engine.common.scene.scene_manager import SceneManager
from engine.common.scene.scene_registry import SceneRegistry
from engine.dialogue.dialogue_engine import DialogueEngine
from engine.dialogue.dialogue_scene import DialogueScene
from engine.encounter.encounter_manager import EncounterManager
from engine.encounter.encounter_resolver import EncounterResolver
from engine.encounter.enemy_sprite import EnemySprite
from engine.inn.inn_scene import InnScene
from engine.io.manifest_loader import ManifestLoader
from engine.io.save_manager import GameStateManager
from engine.item.item_effect_handler import ItemEffectHandler
from engine.item.item_catalog import ItemCatalog
from engine.item.magic_core_catalog_state import MagicCoreCatalogState
from engine.shop.apothecary_scene import ApothecaryScene
from engine.shop.item_shop_scene import ItemShopScene
from engine.shop.magic_core_shop_scene import MagicCoreShopScene
from engine.title.save_modal_scene import SaveModalScene
from engine.world.fade_controller import FadeController
from engine.world.item_box import ItemBox
from engine.world.item_box_loader import ItemBoxLoader
from engine.world.item_box_scene import ItemBoxScene
from engine.world.npc_loader import NpcLoader
from engine.world.player import COLLISION_W, COLLISION_H
from engine.world.tile_map_factory import TileMapFactory
from engine.world.world_map_battle_launcher import launch_battle_from_enemy
from engine.world.world_map_init import init_world_map
from engine.world.world_map_logic import (
    _is_player_facing,
    apply_item_box_loot,
    apply_transition,
    check_portals,
    dispatch_dialogue_result,
    load_inn_cost,
    load_recipes,
    load_shop_items,
    try_interact,
    try_interact_item_box,
)
from engine.world.world_map_overlays import WorldMapOverlays
from engine.world.world_map_renderer import WorldMapRenderer


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
        item_box_loader: ItemBoxLoader,
        item_catalog: ItemCatalog,
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
        player_speed: int = 5,
        debug_collision: bool = False,
        balance=None,
        recorder=None,
        rng=None,
        sprite_cache=None,
    ) -> None:
        self._screen_width = screen_width
        self._screen_height = screen_height
        self._tile_size = tile_size
        self._fps = fps
        self._smooth_collision = smooth_collision
        self._player_speed = player_speed
        self._debug_collision = debug_collision
        self._balance = balance
        self._holder = holder
        self._loader = loader
        self._tile_map_factory = tile_map_factory
        self._scene_manager = scene_manager
        self._registry = registry
        self._game_state_manager = game_state_manager
        self._dialogue_engine = dialogue_engine
        self._npc_loader = npc_loader
        self._item_box_loader = item_box_loader
        self._item_catalog = item_catalog
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
        self._sprite_cache = sprite_cache

        self._renderer = WorldMapRenderer()
        self._reset_state()

    def _reset_state(self) -> None:
        self._tile_map = None
        self._camera = None
        self._player = None
        self._npcs = []
        self._item_boxes = []
        self._enemy_spawner = None
        self._engaged_enemy: EnemySprite | None = None

        # Per-frame visibility cache. _refresh_visibility() rebuilds these from
        # current FlagState; both update() and render() consume the cached
        # lists so flag-based filtering happens once per frame instead of
        # three or four times.
        self._visible_npcs: list = []
        self._visible_boxes: list = []
        self._visible_npc_collision_rects: list = []
        self._visible_box_collision_rects: list = []

        self._overlays = WorldMapOverlays()
        self._quit_confirm: bool = False
        self._fade = FadeController()

    def _refresh_visibility(self) -> None:
        """Rebuild the per-frame visibility caches from the current FlagState."""
        flags = self._holder.get().flags
        self._visible_npcs = [n for n in self._npcs if n.is_present(flags)]
        self._visible_boxes = [b for b in self._item_boxes if b.is_present(flags)]
        self._visible_npc_collision_rects = [n.collision_rect for n in self._visible_npcs]
        self._visible_box_collision_rects = [b.collision_rect for b in self._visible_boxes]

    def reset(self) -> None:
        """Re-initialize for a new game/load session. Clears all map state so _init() reruns."""
        self._reset_state()

    def _ensure_init(self) -> None:
        """Run lazy initialization if it hasn't happened yet.

        Called at the top of both update() and render() so the scene is ready
        regardless of which one runs first (the game loop calls update first).
        Pulls the init out of the per-frame render fast path that §1.9 flagged.
        """
        if self._tile_map is None:
            self._init()

    def _init(self) -> None:
        result = init_world_map(
            holder=self._holder,
            loader=self._loader,
            tile_map_factory=self._tile_map_factory,
            npc_loader=self._npc_loader,
            item_box_loader=self._item_box_loader,
            encounter_manager=self._encounter_manager,
            encounter_resolver=self._encounter_resolver,
            bgm_manager=self._bgm_manager,
            sprite_cache=self._sprite_cache,
            balance=self._balance,
            rng=self._rng,
            screen_width=self._screen_width,
            screen_height=self._screen_height,
            tile_size=self._tile_size,
            fps=self._fps,
            smooth_collision=self._smooth_collision,
            player_speed=self._player_speed,
            debug_collision=self._debug_collision,
            enemy_spawn_global_interval=self._enemy_spawn_global_interval,
        )
        self._tile_map = result.tile_map
        self._camera = result.camera
        self._player = result.player
        self._npcs = result.npcs
        self._item_boxes = result.item_boxes
        self._enemy_spawner = result.enemy_spawner
        self._fade.reset()

    # ── Events ────────────────────────────────────────────────

    def handle_events(self, events: list[pygame.event.Event]) -> None:
        if self._fade.blocks_input:
            return

        active_overlay = self._overlays.active
        if active_overlay is not None:
            active_overlay.handle_events(events)
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
                elif event.key == pygame.K_m:
                    self._open_field_menu()

    def _open_field_menu(self) -> None:
        state = self._holder.get()
        state.map.set_position(self._player.tile_position)
        self._scene_manager.switch(self._registry.get("field_menu"))

    def _open_save_modal(self) -> None:
        state = self._holder.get()
        state.map.set_position(self._player.tile_position)
        self._overlays.save_modal = SaveModalScene(
            game_state_manager=self._game_state_manager,
            state=self._holder.get(),
            on_close=self._close_save_modal,
            sfx_manager=self._sfx_manager,
        )

    def _close_save_modal(self) -> None:
        self._overlays.save_modal = None

    def _try_interact(self) -> None:
        state = self._holder.get()

        box = try_interact_item_box(
            self._player, self._item_boxes, state.flags,
            state.opened_boxes, state.map.current,
        )
        if box is not None:
            self._open_item_box(box)
            return

        result, npc = try_interact(
            self._player, self._npcs, state.flags, self._dialogue_engine,
        )
        if result:
            self._overlays.dialogue = DialogueScene(
                result=result,
                on_complete=self._on_dialogue_complete,
                text_speed=self._text_speed,
                portrait=npc.portrait if npc else None,
            )

    def _open_item_box(self, box: ItemBox) -> None:
        self._overlays.item_box_modal = ItemBoxScene(
            box=box,
            item_catalog=self._item_catalog,
            on_confirm=self._confirm_item_box,
            sfx_manager=self._sfx_manager,
        )

    def _confirm_item_box(self, box: ItemBox) -> None:
        state = self._holder.get()
        apply_item_box_loot(box, state.repository, state.opened_boxes, state.map.current)
        self._overlays.item_box_modal = None

    def _on_dialogue_complete(self, on_complete: dict) -> None:
        self._overlays.dialogue = None
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
            self._fade.start_fade_out(transition)

    def _manifest_sprite(self, section: str) -> str:
        manifest = self._loader.load()
        node = manifest.get(section)
        if not isinstance(node, dict) or "sprite" not in node:
            raise ValueError(
                f"manifest.yaml: missing '{section}.sprite'. "
                f"Example:\n{section}:\n  sprite: assets/sprites/npc/example.tsx"
            )
        return node["sprite"]

    # ── Magic Core Shop ───────────────────────────────────────

    def _open_mc_shop(self) -> None:
        self._overlays.mc_shop = MagicCoreShopScene(
            holder=self._holder,
            scene_manager=self._scene_manager,
            registry=self._registry,
            on_close=self._close_mc_shop,
            mc_sizes=self._mc_catalog.sizes,
            confirm_large=self._mc_exchange_confirm_large,
            sfx_manager=self._sfx_manager,
        )

    def _close_mc_shop(self) -> None:
        self._overlays.mc_shop = None

    # ── Inn ───────────────────────────────────────────────────

    def _open_inn(self) -> None:
        state = self._holder.get()
        state.map.set_position(self._player.tile_position)
        map_id = state.map.current
        cost = load_inn_cost(self._loader.scenario_path, map_id)
        sprite_path = self._loader.scenario_path / self._manifest_sprite("inn")
        self._overlays.inn = InnScene(
            holder=self._holder,
            scene_manager=self._scene_manager,
            registry=self._registry,
            on_close=self._close_inn,
            cost=cost,
            sprite_path=sprite_path,
            sfx_manager=self._sfx_manager,
        )

    def _close_inn(self) -> None:
        self._overlays.inn = None

    # ── Item Shop ─────────────────────────────────────────────

    def _open_item_shop(self) -> None:
        state = self._holder.get()
        map_id = state.map.current
        shop_items = load_shop_items(self._loader.scenario_path, map_id)
        sprite_path = self._loader.scenario_path / self._manifest_sprite("item_shop")
        self._overlays.item_shop = ItemShopScene(
            holder=self._holder,
            scene_manager=self._scene_manager,
            registry=self._registry,
            on_close=self._close_item_shop,
            shop_items=shop_items,
            sprite_path=sprite_path,
            sfx_manager=self._sfx_manager,
        )

    def _close_item_shop(self) -> None:
        self._overlays.item_shop = None

    # ── Apothecary ────────────────────────────────────────────

    def _open_apothecary(self) -> None:
        recipes = load_recipes(self._loader.scenario_path)
        sprite_path = self._loader.scenario_path / self._manifest_sprite("apothecary")
        manifest = self._loader.load()
        icon_cfg = manifest.get("apothecary", {}).get("icons", {})
        icon_paths = {
            key: self._loader.scenario_path / rel
            for key, rel in icon_cfg.items()
        }
        self._overlays.apothecary = ApothecaryScene(
            holder=self._holder,
            scene_manager=self._scene_manager,
            registry=self._registry,
            on_close=self._close_apothecary,
            recipes=recipes,
            sprite_path=sprite_path,
            icon_paths=icon_paths,
            sfx_manager=self._sfx_manager,
        )

    def _close_apothecary(self) -> None:
        self._overlays.apothecary = None

    # ── Battle ────────────────────────────────────────────────

    def _launch_battle_from_enemy(self, enemy: EnemySprite) -> None:
        # Store the enemy; it will be deactivated on the first update tick after battle ends.
        self._engaged_enemy = enemy
        launch_battle_from_enemy(
            enemy=enemy,
            holder=self._holder,
            player=self._player,
            encounter_manager=self._encounter_manager,
            encounter_resolver=self._encounter_resolver,
            scene_manager=self._scene_manager,
            registry=self._registry,
            loader=self._loader,
            game_state_manager=self._game_state_manager,
            effect_handler=self._effect_handler,
            bgm_manager=self._bgm_manager,
            sfx_manager=self._sfx_manager,
            rng=self._rng,
            balance=self._balance,
            screen_width=self._screen_width,
            screen_height=self._screen_height,
        )

    # ── Portal ────────────────────────────────────────────────

    def _check_portals(self) -> None:
        transition = check_portals(self._tile_map, self._player)
        if transition:
            self._fade.start_fade_out(transition)

    def _apply_transition(self, transition: dict) -> None:
        apply_transition(
            self._holder, self._game_state_manager,
            self._player, transition,
        )
        self._tile_map = None
        self._player = None
        self._enemy_spawner = None

    # ── Update ────────────────────────────────────────────────

    def update(self, delta: float) -> None:
        self._ensure_init()

        completed_transition = self._fade.update(delta)
        if completed_transition is not None:
            self._apply_transition(completed_transition)
            return

        active_overlay = self._overlays.active
        if active_overlay is not None:
            active_overlay.update(delta)
            return
        if self._quit_confirm:
            return

        # Deactivate the enemy that triggered the last battle (first tick after returning).
        if self._engaged_enemy is not None:
            if self._enemy_spawner:
                self._enemy_spawner.on_enemy_engaged(self._engaged_enemy)
            self._engaged_enemy = None

        keys = self._recorder.get_key_state() if self._recorder else pygame.key.get_pressed()
        frozen = not self._fade.is_idle
        state = self._holder.get()

        # Refresh visibility caches once per tick — render() reuses them and
        # the per-NPC update loop below pulls collision rects without rescanning.
        self._refresh_visibility()

        # Build collision rects — NPCs and item boxes block the player as solid walls.
        # Enemy sprites are trigger volumes: player walks into them to start battle.
        npc_rects = list(self._visible_npc_collision_rects)
        npc_rects += self._visible_box_collision_rects

        self._player.update(keys, self._tile_map.collision_map, frozen, npc_rects=npc_rects)
        self._camera.update(self._player.pixel_position)

        player_pos = self._player.pixel_position
        visible_npcs = self._visible_npcs
        npc_rects_all = self._visible_npc_collision_rects
        for i, npc in enumerate(visible_npcs):
            # Build other_rects without re-scanning the visible list per npc:
            # slice around index i. This keeps allocation linear in N rather
            # than the O(N^2) "filter by identity" comprehension we had before.
            other_rects = npc_rects_all[:i] + npc_rects_all[i + 1:]
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
        self._ensure_init()

        state = self._holder.get()
        # If update() was skipped this frame (e.g. an overlay is active or the
        # scene was just initialized) the visibility caches won't have been
        # rebuilt yet — refresh them now so render isn't reading stale data.
        if not self._visible_npcs and not self._visible_boxes:
            self._refresh_visibility()

        visible_npcs = self._visible_npcs
        visible_boxes = self._visible_boxes
        enemy_sprites = self._enemy_spawner.active_enemies if self._enemy_spawner else []

        map_id = state.map.current
        box_opened = {b.id: state.opened_boxes.is_opened(map_id, b.id) for b in visible_boxes}

        self._renderer.render(
            screen,
            self._tile_map,
            self._camera,
            self._player,
            visible_npcs,
            enemy_sprites,
            self._overlays.render_list(),
            self._overlays.dialogue,
            self._fade.alpha,
            self._quit_confirm,
            item_boxes=visible_boxes,
            box_opened=box_opened,
            debug_collision=self._debug_collision,
        )
