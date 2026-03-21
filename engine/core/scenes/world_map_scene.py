# engine/core/scenes/world_map_scene.py

import pygame
from engine.core.scene import Scene
from engine.core.scene_manager import SceneManager
from engine.core.scene_registry import SceneRegistry
from engine.core.settings import Settings
from engine.core.state.game_state_holder import GameStateHolder
from engine.core.state.save_manager import SaveManager
from engine.core.dialogue.dialogue_engine import DialogueEngine
from engine.core.scenes.save_modal_scene import SaveModalScene
from engine.core.scenes.dialogue_scene import DialogueScene
from engine.data.loader import ManifestLoader
from engine.world.tile_map import TileMap
from engine.world.tile_map_factory import TileMapFactory
from engine.world.camera import Camera
from engine.world.player import Player
from engine.world.npc import Npc
from engine.world.npc_loader import NpcLoader


class WorldMapScene(Scene):
    """
    Phase 2 — tile map + player + camera + NPC interaction + save modal.
    """

    def __init__(
        self,
        holder: GameStateHolder,
        loader: ManifestLoader,
        tile_map_factory: TileMapFactory,
        scene_manager: SceneManager,
        registry: SceneRegistry,
        save_manager: SaveManager,
        dialogue_engine: DialogueEngine,
        npc_loader: NpcLoader,
        text_speed: str = "fast",
    ) -> None:
        self._holder = holder
        self._loader = loader
        self._tile_map_factory = tile_map_factory
        self._scene_manager = scene_manager
        self._registry = registry
        self._save_manager = save_manager
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

    def _init(self) -> None:
        scenario_path = self._loader.scenario_path
        state = self._holder.get()
        map_id = state.map.current

        tmx_path = scenario_path / "data" / "tmx" / f"{map_id}.tmx"
        self._tile_map = self._tile_map_factory.create(str(tmx_path))
        self._camera = Camera(self._tile_map.width_px, self._tile_map.height_px)
        self._player = Player(
            start=state.map.position,
            map_width_px=self._tile_map.width_px,
            map_height_px=self._tile_map.height_px,
        )

        # load NPCs for current map
        map_yaml = scenario_path / "data" / "maps" / f"{map_id}.yaml"
        self._npcs = self._npc_loader.load_from_map(map_yaml)

    # ── Events ────────────────────────────────────────────────

    def handle_events(self, events: list[pygame.event.Event]) -> None:
        # overlays get events first
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
        self._save_modal = SaveModalScene(
            save_manager=self._save_manager,
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
        # transition handled here
        transition = remaining.get("transition")
        if transition:
            self._handle_transition(transition)

    def _handle_transition(self, transition: dict) -> None:
        # autosave before map transition
        state = self._holder.get()
        self._save_manager.save(state, slot_index=0)
        # stub — Phase 2b: implement full map switch
        # For now: update map state only
        from engine.core.models.position import Position
        new_map = transition.get("map", state.map.current)
        pos = transition.get("position", [0, 0])
        state.map.move_to(new_map, Position.from_list(pos))
        # full scene reload on next render cycle
        self._tile_map = None

    # ── Update ────────────────────────────────────────────────

    def update(self, delta: float) -> None:
        if self._dialogue:
            self._dialogue.update(delta)
            return
        if self._save_modal:
            self._save_modal.update(delta)
            return
        if self._player is None:
            return
        keys = pygame.key.get_pressed()
        self._player.update(keys)
        self._camera.update(self._player.pixel_position)

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
