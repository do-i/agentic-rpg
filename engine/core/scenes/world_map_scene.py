# engine/core/scenes/world_map_scene.py

import pygame
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
from engine.data.loader import ManifestLoader
from engine.world.tile_map import TileMap
from engine.world.tile_map_factory import TileMapFactory
from engine.world.camera import Camera
from engine.world.player import Player
from engine.world.sprite_sheet import SpriteSheet
from engine.world.npc import Npc
from engine.world.npc_loader import NpcLoader
from engine.world.player import COLLISION_W, COLLISION_H

FADE_SPEED = 300  # alpha units per second (0-255)


class WorldMapScene(Scene):
    """
    Phase 3 — tile map + player sprite + camera + NPC interaction +
               portal transitions + save modal.
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
        text_speed: str = "fast",
    ) -> None:
        self._holder = holder
        self._loader = loader
        self._tile_map_factory = tile_map_factory
        self._scene_manager = scene_manager
        self._registry = registry
        self._game_state_manager = game_state_manager
        self._dialogue_engine = dialogue_engine
        self._npc_loader = npc_loader
        self._text_speed = text_speed

        self._tile_map: TileMap | None = None
        self._camera: Camera | None = None
        self._player: Player | None = None
        self._npcs: list[Npc] = []

        # overlays (None = inactive)
        self._save_modal: SaveModalScene | None = None
        self._dialogue: DialogueScene | None = None

        # fade state
        self._fade_alpha: int = 255       # start fully black → fade in
        self._fade_dir: int = -1          # -1 = fade in, +1 = fade out
        self._pending_transition: dict | None = None  # set during fade out

    def _init(self) -> None:
        scenario_path = self._loader.scenario_path
        manifest = self._loader.load()
        state = self._holder.get()
        map_id = state.map.current

        tmx_path = scenario_path / "assets" / "maps" / f"{map_id}.tmx"
        self._tile_map = self._tile_map_factory.create(str(tmx_path))
        self._camera = Camera(self._tile_map.width_px, self._tile_map.height_px)

        # load sprite sheet for protagonist
        sprite_sheet = self._load_protagonist_sprite(manifest, scenario_path)

        self._player = Player(
            start=state.map.position,
            map_width_px=self._tile_map.width_px,
            map_height_px=self._tile_map.height_px,
            sprite_sheet=sprite_sheet,
        )

        # load NPCs for current map
        map_yaml = scenario_path / "data" / "maps" / f"{map_id}.yaml"
        self._npcs = self._npc_loader.load_from_map(map_yaml)

        # start fade in
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
        # block input during fade
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

        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F2:
                    self._open_save_modal()
                elif event.key == pygame.K_RETURN:
                    self._try_interact()

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
        if self._player is None:
            return
        state = self._holder.get()
        flags = state.flags
        player_pos = self._player.pixel_position

        for npc in self._npcs:
            if not npc.is_present(flags):
                continue
            if not npc.is_near(player_pos):
                continue
            result = self._dialogue_engine.resolve(npc.dialogue_id, flags)
            if result:
                self._dialogue = DialogueScene(
                    result=result,
                    on_complete=self._on_dialogue_complete,
                    text_speed=self._text_speed,
                )
            break

    def _on_dialogue_complete(self, on_complete: dict) -> None:
        self._dialogue = None
        if not on_complete:
            return
        state = self._holder.get()
        remaining = self._dialogue_engine.dispatch_on_complete(
            on_complete, state.flags, state.repository
        )
        # stub — Phase 5: handle join_party
        # stub — Phase 4: handle start_battle
        transition = remaining.get("transition")
        if transition:
            self._start_fade_out(transition)

    # ── Portal ────────────────────────────────────────────────

    def _check_portals(self) -> None:
        if self._tile_map is None or self._player is None:
            return
        col = self._player.collision_rect_position
        for portal in self._tile_map.portals:
            if portal.is_triggered_by(col.x, col.y, COLLISION_W, COLLISION_H):
                self._start_fade_out({
                    "map": portal.target_map,
                    "position": [portal.target_position.x, portal.target_position.y],
                })
                break

    # ── Fade & Transition ─────────────────────────────────────

    def _start_fade_out(self, transition: dict) -> None:
        if self._fade_dir == 1:
            return  # already fading out
        self._pending_transition = transition
        self._fade_dir = 1   # fade out
        self._fade_alpha = 0

    def _apply_transition(self) -> None:
        state = self._holder.get()
        state.map.set_position(self._player.tile_position)
        self._game_state_manager.save(state, slot_index=0)

        transition = self._pending_transition
        new_map = transition.get("map", state.map.current)
        pos = transition.get("position", [0, 0])
        state.map.move_to(new_map, Position.from_list(pos))

        # trigger full reload
        self._tile_map = None
        self._player = None

    # ── Update ────────────────────────────────────────────────

    def update(self, delta: float) -> None:
        # handle fade
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
        if self._player is None:
            return

        keys = pygame.key.get_pressed()
        frozen = self._fade_dir != 0
        self._player.update(keys, self._tile_map.collision_map, frozen)
        self._camera.update(self._player.pixel_position)
        self._check_portals()

    # ── Render ────────────────────────────────────────────────

    def render(self, screen: pygame.Surface) -> None:
        if self._tile_map is None:
            self._init()

        screen.fill((0, 0, 0))
        self._tile_map.render(screen, self._camera.offset_x, self._camera.offset_y)

        # NPCs
        state = self._holder.get()
        player_pos = self._player.pixel_position
        for npc in self._npcs:
            if npc.is_present(state.flags):
                near = npc.is_near(player_pos) and self._dialogue is None
                npc.render(screen, self._camera.offset_x, self._camera.offset_y, near=near)

        self._player.render(screen, self._camera.offset_x, self._camera.offset_y)

        # overlays
        if self._save_modal:
            self._save_modal.render(screen)
        if self._dialogue:
            self._dialogue.render(screen)

        # fade overlay
        if self._fade_alpha > 0:
            fade_surf = pygame.Surface(
                (Settings.SCREEN_WIDTH, Settings.SCREEN_HEIGHT), pygame.SRCALPHA
            )
            fade_surf.fill((0, 0, 0, self._fade_alpha))
            screen.blit(fade_surf, (0, 0))