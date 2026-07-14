# tools/make_battle_sprites.py
#
# Generate pre-rendered battle spritesheets from world-map enemy sheets.
#
# Battle scenes draw enemies over painted backgrounds; the 64 px map
# sprites look blocky when nearest-scaled up. This tool re-renders the
# battle-relevant rows of a sheet at 4x with rounded edges (Scale2x), a
# painterly grade matched to the zone's battle background, and a soft
# contact shadow in place of the hard baked ellipse. Output:
# <id>_battle.png + <id>_battle.tsx next to the source sheet;
# BattleAssetCache picks them up automatically.
#
# Only the rows battle actually draws (idle/spellcast row 2, thrust
# row 6) are rendered — the other rows stay transparent so the PNGs
# compress well. Sheet geometry keeps all rows so frame indices line up.
#
# Usage:
#   python tools/make_battle_sprites.py --root rusted_kingdoms --all-encounters
#   python tools/make_battle_sprites.py --root rusted_kingdoms --encount zone_01_starting_forest
#   python tools/make_battle_sprites.py --root rusted_kingdoms --preset frost orc_raider_base
#
# Requires the dev extras (pillow, numpy): pip install -e ".[dev]"

from __future__ import annotations

import argparse
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree

import numpy as np
import yaml
from PIL import Image, ImageEnhance, ImageFilter

UPSCALE_PASSES = 2       # Scale2x applied twice: 64 -> 256
BATTLE_ROWS = (2, 6)     # idle/spellcast row, thrust row (Direction.DOWN based)


@dataclass(frozen=True)
class GradePreset:
    """Lighting parameters matched to one battle-background family."""
    light_top: float           # key-light gain at the head
    light_falloff: float       # how much the gain drops toward the feet
    tint_top: tuple[float, float, float]
    tint_bottom: tuple[float, float, float]
    rim_color: tuple[int, int, int]
    rim_strength: float
    occl_strength: float
    saturation: float
    shadow_rgb: tuple[int, int, int]
    shadow_alpha: int


PRESETS: dict[str, GradePreset] = {
    # warm midday sun on grass/stone (zones 1, 2, 4 gate/courtyard)
    "sunlit": GradePreset(
        light_top=1.10, light_falloff=0.18,
        tint_top=(1.04, 1.01, 0.94), tint_bottom=(0.97, 0.99, 1.05),
        rim_color=(255, 244, 214), rim_strength=0.35,
        occl_strength=0.30, saturation=1.12,
        shadow_rgb=(26, 30, 16), shadow_alpha=110,
    ),
    # foggy desaturated marsh light (zone 3)
    "overcast": GradePreset(
        light_top=1.02, light_falloff=0.10,
        tint_top=(0.99, 1.01, 1.00), tint_bottom=(0.96, 0.99, 1.02),
        rim_color=(214, 228, 222), rim_strength=0.22,
        occl_strength=0.25, saturation=0.95,
        shadow_rgb=(22, 26, 22), shadow_alpha=90,
    ),
    # dim interior with cold teal glow (zone 4 sanctum)
    "mystic": GradePreset(
        light_top=0.96, light_falloff=0.10,
        tint_top=(0.95, 1.00, 1.04), tint_bottom=(0.92, 0.98, 1.06),
        rim_color=(180, 235, 235), rim_strength=0.30,
        occl_strength=0.35, saturation=1.00,
        shadow_rgb=(12, 16, 20), shadow_alpha=120,
    ),
    # bright cold snowfield light (zones 5, 6)
    "frost": GradePreset(
        light_top=1.06, light_falloff=0.14,
        tint_top=(1.00, 1.01, 1.04), tint_bottom=(0.95, 0.98, 1.08),
        rim_color=(235, 242, 255), rim_strength=0.32,
        occl_strength=0.28, saturation=0.98,
        shadow_rgb=(24, 30, 44), shadow_alpha=100,
    ),
    # dark violet murk, faint cold glow (zone 8 corrupted forest, zone 10
    # stronghold approach)
    "gloom": GradePreset(
        light_top=0.94, light_falloff=0.08,
        tint_top=(0.97, 0.96, 1.03), tint_bottom=(0.94, 0.95, 1.05),
        rim_color=(200, 185, 225), rim_strength=0.26,
        occl_strength=0.32, saturation=0.92,
        shadow_rgb=(16, 14, 22), shadow_alpha=115,
    ),
    # hot lava light from below (zone 9 volcanic region)
    "ember": GradePreset(
        light_top=1.02, light_falloff=0.16,
        tint_top=(1.05, 0.96, 0.90), tint_bottom=(1.08, 0.94, 0.84),
        rim_color=(255, 160, 90), rim_strength=0.40,
        occl_strength=0.30, saturation=1.10,
        shadow_rgb=(40, 12, 8), shadow_alpha=110,
    ),
    # zones without a painted background yet (default dark floor)
    "neutral": GradePreset(
        light_top=1.04, light_falloff=0.12,
        tint_top=(1.00, 1.00, 1.00), tint_bottom=(0.97, 0.98, 1.02),
        rim_color=(240, 240, 235), rim_strength=0.25,
        occl_strength=0.28, saturation=1.05,
        shadow_rgb=(20, 20, 24), shadow_alpha=100,
    ),
}

# battle background id -> preset name ("none" = encounter file without one)
BACKGROUND_PRESETS: dict[str, str] = {
    "zone1-bg-1280x468": "sunlit",
    "zone2-bg-1280x468": "sunlit",
    "zone3-bg-1280x468": "overcast",
    "zone4-gate-bg-1280x468": "sunlit",
    "zone4-courtyard-bg-1280x468": "sunlit",
    "zone4-sanctum-bg-1280x468": "mystic",
    "zone5-bg-1280x468": "frost",
    "zone6-bg-1280x468": "frost",
    "zone7-bg-1280x468": "mystic",
    "zone8-bg-1280x468": "gloom",
    "zone9-bg-1280x468": "ember",
    "zone10-bg-1280x468": "gloom",
    "none": "neutral",
}


def scale2x(a: np.ndarray) -> np.ndarray:
    """Classic Scale2x: rounds staircase edges without blurring."""
    h, w, c = a.shape
    p = np.pad(a, ((1, 1), (1, 1), (0, 0)), mode="edge")
    C = p[1:-1, 1:-1]
    U = p[:-2, 1:-1]
    D = p[2:, 1:-1]
    L = p[1:-1, :-2]
    R = p[1:-1, 2:]

    def eq(x, y):
        return np.all(x == y, axis=-1, keepdims=True)

    keep = eq(U, D) | eq(L, R)
    e0 = np.where(~keep & eq(L, U), L, C)
    e1 = np.where(~keep & eq(U, R), R, C)
    e2 = np.where(~keep & eq(L, D), L, C)
    e3 = np.where(~keep & eq(D, R), R, C)

    out = np.empty((h * 2, w * 2, c), dtype=a.dtype)
    out[0::2, 0::2] = e0
    out[0::2, 1::2] = e1
    out[1::2, 0::2] = e2
    out[1::2, 1::2] = e3
    return out


def edge_masks(alpha: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return (rim, occlusion) float masks along the silhouette: pixels
    lit from above and pixels shaded from below."""
    solid = alpha > 128

    def shift(m: np.ndarray, dy: int, dx: int) -> np.ndarray:
        out = np.zeros_like(m)
        h, w = m.shape
        ys = slice(max(dy, 0), h + min(dy, 0))
        xs = slice(max(dx, 0), w + min(dx, 0))
        yd = slice(max(-dy, 0), h + min(-dy, 0))
        xd = slice(max(-dx, 0), w + min(-dx, 0))
        out[ys, xs] = m[yd, xd]
        return out

    rim = solid & ~shift(solid, 3, 1)
    occl = solid & ~shift(solid, -3, -1)
    rim_f = Image.fromarray((rim * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.6))
    occl_f = Image.fromarray((occl * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(2.2))
    return np.array(rim_f) / 255.0, np.array(occl_f) / 255.0


def grade(img: Image.Image, preset: GradePreset) -> Image.Image:
    """Painterly grade: directional key light, tint ramp, rim light and
    contact shading tuned to the zone's background."""
    img = img.filter(ImageFilter.GaussianBlur(0.8))
    img = ImageEnhance.Sharpness(img).enhance(1.15)
    a = np.array(img).astype(np.float32)
    rgb, alpha = a[..., :3], a[..., 3]

    h = a.shape[0]
    t = (np.arange(h, dtype=np.float32) / (h - 1))[:, None, None]
    light = preset.light_top - preset.light_falloff * t
    tint = (
        np.array(preset.tint_top, np.float32) * (1 - t * 0.5)
        + np.array(preset.tint_bottom, np.float32) * (t * 0.5)
    )
    rgb = rgb * light * tint

    rim, occl = edge_masks(alpha)
    rim_col = np.array(preset.rim_color, np.float32)
    rgb = rgb + rim[..., None] * preset.rim_strength * (rim_col - rgb)
    rgb = rgb * (1 - occl[..., None] * preset.occl_strength)

    a[..., :3] = np.clip(rgb, 0, 255)
    out = Image.fromarray(a.astype(np.uint8))
    return ImageEnhance.Color(out).enhance(preset.saturation)


def add_soft_shadow(img: Image.Image, preset: GradePreset) -> Image.Image:
    """Soft elliptical contact shadow anchored to the frame's feet."""
    a = np.array(img)
    alpha = a[..., 3]
    ys, xs = np.nonzero(alpha > 128)
    foot_y = ys.max()
    cx = (xs.min() + xs.max()) / 2
    body_w = xs.max() - xs.min()

    h, w = alpha.shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    rx, ry = body_w * 0.62, max(body_w * 0.16, 1.0)
    d = ((xx - cx) / rx) ** 2 + ((yy - (foot_y - ry * 0.2)) / ry) ** 2
    shade = np.clip(1.0 - d, 0, 1) ** 1.5 * preset.shadow_alpha

    canvas = np.zeros_like(a)
    canvas[..., 0:3] = preset.shadow_rgb
    canvas[..., 3] = shade.astype(np.uint8)
    base = Image.fromarray(canvas).filter(ImageFilter.GaussianBlur(3))
    base.alpha_composite(img)
    return base


def process_frame(frame: Image.Image, preset: GradePreset) -> Image.Image | None:
    """One map-sheet frame -> one graded battle frame at 4x. Returns None
    for empty frames."""
    a = np.array(frame)
    # Strip baked semi-transparent drop shadows; keep binary alpha.
    a[a[..., 3] < 255] = 0
    if not (a[..., 3] > 0).any():
        return None
    for _ in range(UPSCALE_PASSES):
        a = scale2x(a)
    return add_soft_shadow(grade(Image.fromarray(a), preset), preset)


def read_tsx_geometry(tsx_path: Path) -> tuple[int, int, int]:
    root = ElementTree.parse(tsx_path).getroot()
    values = []
    for name in ("tilewidth", "tileheight", "columns"):
        value = root.attrib.get(name)
        if value is None:
            raise ValueError(
                f'Missing "{name}" attribute on <tileset> in {tsx_path} '
                f'— e.g. <tileset ... {name}="64">'
            )
        values.append(int(value))
    return values[0], values[1], values[2]


def make_battle_sheet(sprites_dir: Path, sprite_id: str, preset: GradePreset) -> Path:
    src_tsx = sprites_dir / f"{sprite_id}.tsx"
    tile_w, tile_h, columns = read_tsx_geometry(src_tsx)
    sheet = Image.open(sprites_dir / f"{sprite_id}.png").convert("RGBA")
    rows = sheet.height // tile_h

    factor = 2 ** UPSCALE_PASSES
    out_w, out_h = tile_w * factor, tile_h * factor
    out = Image.new("RGBA", (columns * out_w, rows * out_h), (0, 0, 0, 0))
    for row in BATTLE_ROWS:
        if row >= rows:
            continue
        for col in range(columns):
            frame = sheet.crop(
                (col * tile_w, row * tile_h, (col + 1) * tile_w, (row + 1) * tile_h)
            )
            processed = process_frame(frame, preset)
            if processed is not None:
                out.paste(processed, (col * out_w, row * out_h))

    png_path = sprites_dir / f"{sprite_id}_battle.png"
    out.save(png_path)

    tsx_path = sprites_dir / f"{sprite_id}_battle.tsx"
    tsx_path.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<tileset version="1.10" tiledversion="1.12.1" name="{sprite_id}_battle" '
        f'tilewidth="{out_w}" tileheight="{out_h}" '
        f'tilecount="{rows * columns}" columns="{columns}">\n'
        f' <image source="{sprite_id}_battle.png" '
        f'width="{out.width}" height="{out.height}"/>\n'
        "</tileset>\n"
    )
    return png_path


def preset_for_background(bg_id: str) -> str:
    preset = BACKGROUND_PRESETS.get(bg_id)
    if preset is None:
        raise ValueError(
            f'No preset mapped for battle background "{bg_id}" '
            f"— add it to BACKGROUND_PRESETS in {__file__}"
        )
    return preset


def load_encounter(root: Path, encount_id: str) -> dict:
    return yaml.safe_load(
        (root / "data" / "encount" / f"{encount_id}.yaml").read_text()
    )


def encounter_sprite_ids(data: dict) -> list[str]:
    ids: list[str] = []
    for entry in data["entries"]:
        for enemy_id in entry["formation"]:
            if enemy_id not in ids:
                ids.append(enemy_id)
    boss = data.get("boss")
    if boss is not None and boss["id"] not in ids:
        ids.append(boss["id"])
    return ids


def all_encounter_assignments(root: Path) -> dict[str, str]:
    """Map every sprite id used by any encounter file to a preset name.
    Sprites fought on several backgrounds get the most common one."""
    seen: dict[str, Counter] = defaultdict(Counter)
    for path in sorted((root / "data" / "encount").glob("*.yaml")):
        data = yaml.safe_load(path.read_text())
        preset = preset_for_background(data.get("background", "none"))
        for sprite_id in encounter_sprite_ids(data):
            seen[sprite_id][preset] += 1
    return {sid: counts.most_common(1)[0][0] for sid, counts in seen.items()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, help="scenario root, e.g. rusted_kingdoms")
    parser.add_argument("--encount", help="encounter file id to pull sprite ids from")
    parser.add_argument("--all-encounters", action="store_true",
                        help="process every sprite used by any encounter file")
    parser.add_argument("--preset", choices=sorted(PRESETS),
                        help="grading preset for explicitly listed sprite ids "
                             "(--encount/--all-encounters derive it from the background)")
    parser.add_argument("sprite_ids", nargs="*", help="explicit sprite ids")
    args = parser.parse_args()

    root = Path(args.root)
    sprites_dir = root / "assets" / "sprites" / "enemies"

    jobs: dict[str, str] = {}
    if args.sprite_ids:
        if not args.preset:
            parser.error("explicit sprite ids need --preset")
        jobs.update({sid: args.preset for sid in args.sprite_ids})
    if args.encount:
        data = load_encounter(root, args.encount)
        preset = preset_for_background(data.get("background", "none"))
        for sid in encounter_sprite_ids(data):
            jobs.setdefault(sid, preset)
    if args.all_encounters:
        for sid, preset in all_encounter_assignments(root).items():
            jobs.setdefault(sid, preset)
    if not jobs:
        parser.error("no sprite ids given (pass ids, --encount or --all-encounters)")

    for sprite_id, preset_name in jobs.items():
        if not (sprites_dir / f"{sprite_id}.tsx").exists():
            print(f"skip {sprite_id}: no {sprite_id}.tsx in {sprites_dir}", file=sys.stderr)
            continue
        path = make_battle_sheet(sprites_dir, sprite_id, PRESETS[preset_name])
        print(f"wrote {path} [{preset_name}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
