# engine/battle/enemy_loader.py
#
# Phase 4 — Battle system

from __future__ import annotations

import logging
from pathlib import Path

import yaml

from engine.io.yaml_loader import iter_yaml_documents, load_yaml_required
from engine.battle.combatant import Combatant

_log = logging.getLogger(__name__)


# Filename convention from docs/design/battle.md:
#   enemies_rank_1_SS.yaml, enemies_rank_2_S.yaml, ..., enemies_rank_8_F.yaml
# Build an index at startup: {enemy_id: Path}

class EnemyLoader:
    """
    Two-phase loader (matches docs/design/battle.md):
      Phase 1 (startup) — scan all rank files, build id → file index.
      Phase 2 (battle)  — load only the specific enemy docs needed.

    Also loads class YAML for ability lists when scenario_path is set.
    """

    def __init__(self, enemies_dir: Path, classes_dir: Path | None = None) -> None:
        self._enemies_dir = enemies_dir
        self._classes_dir = classes_dir
        self._index: dict[str, Path] = {}
        self._class_cache: dict[str, list[dict]] = {}
        self._build_index()

    # ── Index ─────────────────────────────────────────────────

    def _build_index(self) -> None:
        if not self._enemies_dir.exists():
            return
        for path in self._enemies_dir.glob("enemies_rank_*.yaml"):
            for doc in iter_yaml_documents(path):
                if isinstance(doc, dict) and "id" in doc:
                    self._index[doc["id"]] = path

    # ── Load ──────────────────────────────────────────────────

    def load(self, enemy_id: str) -> Combatant | None:
        path = self._index.get(enemy_id)
        if not path:
            return None
        for doc in iter_yaml_documents(path):
            if isinstance(doc, dict) and doc.get("id") == enemy_id:
                return self._build(doc)
        return None

    _REQUIRED = ("name", "hp", "atk", "def", "mres", "dex", "exp")

    def _build(self, data: dict) -> Combatant:
        enemy_id = data["id"]
        missing = [k for k in self._REQUIRED if k not in data]
        if missing:
            raise KeyError(
                f"enemy {enemy_id!r}: missing required fields "
                f"{missing} (from rank YAML)"
            )
        ai_data = self._load_ai_data(data)

        return Combatant(
            id=enemy_id,
            name=data["name"],
            hp=data["hp"],
            hp_max=data["hp"],
            mp=0,       # enemies don't manage MP — docs/design/enemy.md
            mp_max=0,
            atk=data["atk"],
            def_=data["def"],
            mres=data["mres"],
            dex=data["dex"],
            is_enemy=True,
            boss=data.get("boss", False),          # absent = not a boss
            sprite_id=enemy_id,
            sprite_scale=data.get("sprite_scale", 100),  # visual tweak only
            exp_yield=data["exp"],
            drops=data.get("drops", {}),
            ai_data=ai_data,
        )

    # ── AI loading ────────────────────────────────────────────

    def _load_ai_data(self, data: dict) -> dict:
        """Load AI + targeting from inline ai: block or external ai_ref: file."""
        ai_ref = data.get("ai_ref")
        if ai_ref and self._enemies_dir:
            ref_path = self._enemies_dir / ai_ref
            if ref_path.exists():
                try:
                    ref_data = load_yaml_required(ref_path)
                    return {
                        "ai": ref_data.get("ai", {}),
                        "targeting": ref_data.get("targeting", {}),
                    }
                except (yaml.YAMLError, OSError, KeyError) as e:
                    _log.warning("AI ref reload failed: %s — %s", ref_path, e)

        return {
            "ai": data.get("ai", {}),
            "targeting": data.get("targeting", {}),
        }

    # ── Registry query ────────────────────────────────────────

    @property
    def known_ids(self) -> list[str]:
        return list(self._index.keys())
