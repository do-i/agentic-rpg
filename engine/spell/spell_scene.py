# engine/spell/spell_scene.py
#
# Field Menu Spells screen: character picker → learned spells list → target
# select for field-castable spells (heal/cure/buff). Battle-only spells
# appear as inspect-only rows. Built on engine.common.wizard_scene; the
# casting flow lives in FieldCastMixin (shared with StatusScene) and
# drawing in spell_renderer.SpellRenderer.

from __future__ import annotations

import pygame

from engine.common.scene.scene_manager import SceneManager
from engine.common.scene.scene_registry import SceneRegistry
from engine.common.game_state_holder import GameStateHolder
from engine.io.save_manager import GameStateManager
from engine.common.wizard_scene import WizardPage, WizardScene
from engine.spell.field_cast_mixin import FieldCastMixin
from engine.spell.spell_renderer import PAGE_MEMBER, PAGE_SPELL, SpellRenderer


class SpellScene(FieldCastMixin, WizardScene):
    """Field spell browser with optional casting.

    Pages: MEMBER → SPELL. Castable spells open a target overlay. Battle-only
    spells are rendered in a dimmed color and produce a 'cancel' beep on ENTER.
    """

    def __init__(
        self,
        holder: GameStateHolder,
        scene_manager: SceneManager,
        registry: SceneRegistry,
        scenario_path: str,
        return_scene_name: str,
        sfx_manager,
        game_state_manager: GameStateManager,
    ) -> None:
        super().__init__(scene_manager, registry, return_scene_name, sfx_manager)
        self._init_field_cast(holder, scenario_path, game_state_manager)
        self._renderer = SpellRenderer()

        self._register_page(WizardPage(
            name=PAGE_MEMBER,
            count_fn=lambda: len(self._members()),
            on_confirm=self._confirm_member,
            on_back=lambda: None,           # close scene
        ))
        self._register_page(WizardPage(
            name=PAGE_SPELL,
            count_fn=lambda: len(self._spells),
            on_confirm=self._confirm_spell,
            on_back=lambda: PAGE_MEMBER,
        ))

    # ── Page confirm callbacks ───────────────────────────────

    def _confirm_member(self) -> str | None:
        self._spells = self._load_spells()
        if not self._spells:
            member = self._current_member()
            self._show_popup(f"{member.name} has no spells.")
            self._play("cancel")
            return None
        self._play("confirm")
        return PAGE_SPELL

    def _confirm_spell(self) -> str | None:
        sel = self._page(PAGE_SPELL).selection
        spell = self._spells[sel]
        caster = self._current_member()
        if caster is None:
            return None
        return self._cast_spell(spell, caster)

    # ── Render ────────────────────────────────────────────────

    def render(self, screen: pygame.Surface) -> None:
        self._renderer.render(
            screen,
            page_id=self.page_id,
            members=self._members(),
            member=self._current_member(),
            member_selection=self._page(PAGE_MEMBER).selection,
            spell_selection=self._page(PAGE_SPELL).selection,
            spells=self._spells,
        )
        self._render_field_cast_overlays(screen)
