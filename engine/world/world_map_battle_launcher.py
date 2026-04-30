# engine/world/world_map_battle_launcher.py
#
# Builds a BattleState from a visible enemy sprite (boss or wandering formation)
# and switches the SceneManager to a freshly-constructed BattleScene. Extracted
# from WorldMapScene so the scene only needs to delegate.
from __future__ import annotations

from engine.audio.bgm_manager import BgmManager
from engine.audio.sfx_manager import SfxManager
from engine.battle.battle_scene import BattleScene
from engine.common.game_state_holder import GameStateHolder
from engine.common.scene.scene_manager import SceneManager
from engine.common.scene.scene_registry import SceneRegistry
from engine.encounter.encounter_manager import EncounterManager
from engine.encounter.encounter_resolver import EncounterResolver
from engine.encounter.enemy_sprite import EnemySprite
from engine.encounter.encounter_zone_data import Formation
from engine.io.manifest_loader import ManifestLoader
from engine.io.save_manager import GameStateManager
from engine.item.item_effect_handler import ItemEffectHandler
from engine.world.player import Player


def launch_battle_from_enemy(
    *,
    enemy: EnemySprite,
    holder: GameStateHolder,
    player: Player,
    encounter_manager: EncounterManager,
    encounter_resolver: EncounterResolver,
    scene_manager: SceneManager,
    registry: SceneRegistry,
    loader: ManifestLoader,
    game_state_manager: GameStateManager,
    effect_handler: ItemEffectHandler | None,
    bgm_manager: BgmManager | None,
    sfx_manager: SfxManager,
    rng,
    balance,
    screen_width: int,
    screen_height: int,
) -> bool:
    """Build a BattleState from `enemy` and switch to BattleScene.

    Returns True if a battle was launched, False if the encounter zone or
    formation produced no valid battle (caller may skip the engagement).
    """
    state = holder.get()
    zone = encounter_manager.get_zone()
    inventory_ids: set[str] = {entry.id for entry in state.repository.items}

    if enemy.is_boss and zone:
        battle_state = encounter_resolver.build_battle_from_boss(zone, state.flags)
    elif zone:
        formation = Formation(
            enemy_ids=enemy.formation,
            weight=1,
            chase_range=enemy.chase_range,
        )
        battle_state = encounter_resolver.build_battle_from_formation(
            formation, zone, inventory_ids,
        )
    else:
        return False

    if battle_state is None:
        return False

    boss_flag = getattr(battle_state, "boss_flag", "")
    battle_state = encounter_manager.fill_party(
        battle_state, state.party, set(state.flags.to_list()),
    )
    state.map.set_position(player.tile_position)

    scene = BattleScene(
        battle_state=battle_state,
        scene_manager=scene_manager,
        registry=registry,
        holder=holder,
        screen_width=screen_width,
        screen_height=screen_height,
        scenario_path=str(loader.scenario_path),
        boss_flag=boss_flag,
        effect_handler=effect_handler,
        game_state_manager=game_state_manager,
        bgm_manager=bgm_manager,
        sfx_manager=sfx_manager,
        rng=rng,
        balance=balance,
    )
    scene_manager.switch(scene)
    return True
