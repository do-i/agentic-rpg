from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEO_CENTERED", "1")

import pygame

from engine.common.scene.scene_manager import SceneManager
from tools.map_editor.graph.portal_graph import GraphNode, build_portal_graph
from tools.map_editor.graph.thumbnails import ThumbnailCache
from tools.map_editor.io.scenario_loader import ScenarioMaps, load_scenario_maps
from tools.map_editor.scenes.graph_scene import GraphScene
from tools.map_editor.scenes.map_view_scene import MapViewScene


WINDOW_SIZE = (1280, 800)
FPS = 60


class App:
    def __init__(self, scenario_root: Path) -> None:
        self._scenario: ScenarioMaps = load_scenario_maps(scenario_root)
        pygame.init()
        pygame.display.set_caption(f"Map Editor — {scenario_root.name}")
        self._screen = pygame.display.set_mode(WINDOW_SIZE, pygame.RESIZABLE)
        try:
            pygame.scrap.init()
        except (pygame.error, AttributeError):
            pass
        self._clock = pygame.time.Clock()
        self._font = pygame.font.SysFont("monospace", 16)
        self._small_font = pygame.font.SysFont("monospace", 13)
        self._header_font = pygame.font.SysFont("monospace", 22, bold=True)
        self._scene_manager = SceneManager()

        self._thumbnails = ThumbnailCache(self._scenario.scenario_root)
        self._graph = build_portal_graph(
            tmx_paths=self._scenario.tmx_paths,
            yaml_for=self._scenario.yaml_for,
        )
        self._show_graph()

    def _show_graph(self) -> None:
        scene = GraphScene(
            graph=self._graph,
            thumbnails=self._thumbnails,
            on_open_map=self._open_node,
            font=self._font,
            small_font=self._small_font,
            header_font=self._header_font,
        )
        self._scene_manager.switch(scene)

    def _open_node(self, node: GraphNode) -> None:
        try:
            scene = MapViewScene(
                tmx_path=node.tmx_path,
                yaml_path=node.yaml_path,
                on_back=self._show_graph,
                font=self._font,
            )
        except Exception as e:
            print(f"Failed to open {node.tmx_path.name}: {e}", file=sys.stderr)
            return
        self._scene_manager.switch(scene)

    def run(self) -> None:
        running = True
        while running:
            delta = self._clock.tick(FPS) / 1000.0
            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    running = False
                elif (
                    event.type == pygame.KEYDOWN
                    and event.key == pygame.K_q
                    and event.mod & (pygame.KMOD_CTRL | pygame.KMOD_META)
                ):
                    running = False
                elif event.type == pygame.VIDEORESIZE:
                    self._screen = pygame.display.set_mode(
                        (event.w, event.h), pygame.RESIZABLE
                    )
            self._scene_manager.handle_events(events)
            self._scene_manager.update(delta)
            self._scene_manager.render(self._screen)
            pygame.display.flip()
        pygame.quit()
