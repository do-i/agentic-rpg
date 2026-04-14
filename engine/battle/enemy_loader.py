# engine/io/enemy_loader.py
#
# Phase 4 — Battle system

from __future__ import annotations
from pathlib import Path
import yaml

from engine.battle.combatant import Combatant


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
        ai_data = self._load_ai_data(data)

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
            sprite_scale=data.get("sprite_scale", 100),
            exp_yield=data.get("exp", 0),
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
                    with open(ref_path, "r") as f:
                        ref_data = yaml.safe_load(f)
                    return {
                        "ai": ref_data.get("ai", {}),
                        "targeting": ref_data.get("targeting", {}),
                    }
                except Exception:
                    pass

        return {
            "ai": data.get("ai", {}),
            "targeting": data.get("targeting", {}),
        }

    def load_world_sprite_path(self, enemy_id: str) -> str | None:
        """Return the world_sprite path string from the enemy YAML, or None."""
        path = self._index.get(enemy_id)
        if not path:
            return None
        try:
            with open(path, "r") as f:
                for doc in yaml.safe_load_all(f):
                    if isinstance(doc, dict) and doc.get("id") == enemy_id:
                        return doc.get("world_sprite")
        except Exception:
            pass
        return None

    # ── Registry query ────────────────────────────────────────

    @property
    def known_ids(self) -> list[str]:
        return list(self._index.keys())
