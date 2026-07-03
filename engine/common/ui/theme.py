# engine/common/ui/theme.py
#
# App-wide UI palette and scenario-owned theme assets. Split out of the
# former field_menu_theme.py: this module holds colors and asset paths;
# drawing helpers live in chrome.py, surface caching in image_cache.py.

from __future__ import annotations

from pathlib import Path

from engine.io.yaml_require import require


# Scenario-owned theme assets, configured once at DI time (AppModule) from
# the manifest — the engine never hardcodes a scenario path. Same pattern
# as font_provider.init_fonts()/get_fonts().
_ASSET_ROOT: Path | None = None
_MENU_BACKDROP: Path | None = None


def init_theme_assets(scenario_path: Path, manifest: dict) -> None:
    """Resolve the menu backdrop and asset root from the scenario manifest."""
    global _ASSET_ROOT, _MENU_BACKDROP
    backdrop_rel = require(
        manifest, "ui.menu_backdrop", scenario_path / "manifest.yaml",
        "ui:\n  menu_backdrop: assets/images/battle_bg/zone4-sanctum-bg-1280x468.webp",
    )
    backdrop = scenario_path / backdrop_rel
    if not backdrop.exists():
        raise ValueError(
            f'"ui.menu_backdrop" in {scenario_path / "manifest.yaml"} points to '
            f"a missing file: {backdrop}"
        )
    _ASSET_ROOT = scenario_path / "assets"
    _MENU_BACKDROP = backdrop


def theme_asset_root() -> Path:
    if _ASSET_ROOT is None:
        raise RuntimeError(
            "Theme assets not configured — init_theme_assets() must run "
            "before rendering (wired in AppModule.provide_scene_registry)."
        )
    return _ASSET_ROOT


def menu_backdrop_path() -> Path:
    if _MENU_BACKDROP is None:
        raise RuntimeError(
            "Theme assets not configured — init_theme_assets() must run "
            "before rendering (wired in AppModule.provide_scene_registry)."
        )
    return _MENU_BACKDROP


def member_icon_path(member_id: str) -> Path | None:
    path = theme_asset_root() / "images" / f"{member_id}_profile.png"
    return path if path.exists() else None


# ── Palette ───────────────────────────────────────────────────

INK = (242, 236, 211)
MUTED = (184, 174, 142)
DIM = (101, 96, 88)
GOLD = (231, 184, 86)
EMBER = (203, 82, 47)
TEAL = (67, 166, 160)
VIOLET = (126, 101, 204)
PANEL = (22, 22, 28, 228)
PANEL_DARK = (10, 10, 14, 188)
BORDER = (126, 98, 55)
BORDER_ACTIVE = (235, 190, 89)
ROW = (30, 30, 38, 164)
ROW_ACTIVE = (79, 51, 38, 214)
