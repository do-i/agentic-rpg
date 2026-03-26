# engine/core/encounter/enemy_loader.py
#
# Phase 4 — Battle system

from __future__ import annotations
from pathlib import Path
import yaml

from engine.core.battle.combatant import Combatant


# Filename convention from docs/03-Battle.md:
#   enemies_rank_1_SS.yaml, enemies_rank_2_S.yaml, ..., enemies_rank_8_F.yaml
# Build an index at startup: {enemy_id: Path}

class EnemyLoader:
    """
    Two-phase loader (matches docs/03-Battle.md):
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
            try:
                with open(path, "r") as f:
                    for doc in yaml.safe_load_all(f):
                        if isinstance(doc, dict) and "id" in doc:
                            self._index[doc["id"]] = path
            except Exception:
                pass

    # ── Load ──────────────────────────────────────────────────

    def load(self, enemy_id: str) -> Combatant | None:
        path = self._index.get(enemy_id)
        if not path:
            return None
        try:
            with open(path, "r") as f:
                for doc in yaml.safe_load_all(f):
                    if isinstance(doc, dict) and doc.get("id") == enemy_id:
                        return self._build(doc)
        except Exception:
            pass
        return None

    def _build(self, data: dict) -> Combatant:
        enemy_id = data["id"]
        abilities = self._load_class_abilities(data.get("class"))

        return Combatant(
            id=enemy_id,
            name=data.get("name", enemy_id),
            hp=data.get("hp", 10),
            hp_max=data.get("hp", 10),
            mp=0,       # enemies don't manage MP — docs/10-Enemy.md
            mp_max=0,
            atk=data.get("atk", 5),
            def_=data.get("def", 3),
            mres=data.get("mres", 2),
            dex=data.get("dex", 8),
            is_enemy=True,
            boss=data.get("boss", False),
            sprite_id=enemy_id,
            abilities=abilities,
        )

    # ── Class abilities ───────────────────────────────────────

    def _load_class_abilities(self, class_name: str | None) -> list[dict]:
        """
        Enemies don't have classes — returns empty list.
        Ability list for enemies comes from their inline ai: block,
        resolved by EnemyAI in Phase 4 follow-up.
        """
        return []   # stub — Phase 4

    # ── Registry query ────────────────────────────────────────

    @property
    def known_ids(self) -> list[str]:
        return list(self._index.keys())
