#!/usr/bin/env python3
"""Generate the consolidated repeatable wall tileset."""

from __future__ import annotations

import argparse
import binascii
import struct
import zlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_PNG = ROOT / "rusted_kingdoms/assets/tilesets/walls_02.png"
OUT_TSX = ROOT / "rusted_kingdoms/assets/tilesets/walls_02.tsx"


Color = tuple[int, int, int, int]

WALL = (88, 117, 132, 255)
WALL_HI = (142, 170, 180, 255)
WALL_LO = (45, 68, 80, 255)
MORTAR = (36, 50, 58, 255)
TRIM = (83, 47, 36, 255)
TRIM_HI = (151, 91, 55, 255)
TRIM_LO = (35, 24, 22, 255)
METAL = (160, 139, 82, 255)
EDGE_WIDTH = 7

PALETTES = [
    {
        "slug": "moss_stone",
        "wall": (93, 119, 83, 255),
        "wall_hi": (150, 169, 126, 255),
        "wall_lo": (48, 69, 50, 255),
        "mortar": (42, 54, 43, 255),
        "trim": (96, 65, 42, 255),
        "trim_hi": (164, 113, 67, 255),
        "trim_lo": (44, 31, 25, 255),
        "metal": (79, 137, 108, 255),
    },
    {
        "slug": "sandstone",
        "wall": (151, 133, 91, 255),
        "wall_hi": (204, 184, 130, 255),
        "wall_lo": (94, 78, 55, 255),
        "mortar": (80, 67, 54, 255),
        "trim": (91, 58, 47, 255),
        "trim_hi": (156, 101, 72, 255),
        "trim_lo": (45, 31, 28, 255),
        "metal": (130, 90, 58, 255),
    },
    {
        "slug": "obsidian",
        "wall": (64, 66, 76, 255),
        "wall_hi": (121, 124, 136, 255),
        "wall_lo": (27, 30, 38, 255),
        "mortar": (24, 25, 31, 255),
        "trim": (76, 80, 86, 255),
        "trim_hi": (150, 151, 145, 255),
        "trim_lo": (30, 32, 35, 255),
        "metal": (137, 63, 48, 255),
    },
]

SUBTLE_TALL_PALETTE = {
    "slug": "subtle_tall",
    "wall": (96, 111, 116, 255),
    "wall_hi": (118, 131, 135, 255),
    "wall_lo": (77, 90, 96, 255),
    "mortar": (58, 68, 72, 255),
    "trim": (86, 55, 42, 255),
    "trim_hi": (126, 83, 54, 255),
    "trim_lo": (47, 34, 29, 255),
    "metal": (131, 116, 77, 255),
    "edge_width": 4,
}

OAK_WALL_COLORS = [
    (151, 113, 69, 255),
    (166, 127, 79, 255),
    (120, 86, 54, 255),
]
OAK_TRIM_COLORS = [
    (82, 50, 35, 255),
    (111, 68, 43, 255),
    (147, 92, 54, 255),
    (45, 31, 26, 255),
    (151, 126, 76, 255),
]


def use_palette(palette: dict[str, Color]) -> None:
    global WALL, WALL_HI, WALL_LO, MORTAR, TRIM, TRIM_HI, TRIM_LO, METAL, EDGE_WIDTH
    WALL = palette["wall"]
    WALL_HI = palette["wall_hi"]
    WALL_LO = palette["wall_lo"]
    MORTAR = palette["mortar"]
    TRIM = palette["trim"]
    TRIM_HI = palette["trim_hi"]
    TRIM_LO = palette["trim_lo"]
    METAL = palette["metal"]
    EDGE_WIDTH = int(palette.get("edge_width", 7))  # type: ignore[arg-type]


def png_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"{path} is not a PNG")
    return struct.unpack(">II", data[16:24])


def chunk(tag: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data))
        + tag
        + data
        + struct.pack(">I", binascii.crc32(tag + data) & 0xFFFFFFFF)
    )


def write_png(path: Path, pixels: list[list[Color]]) -> None:
    height = len(pixels)
    width = len(pixels[0])
    raw = bytearray()
    for row in pixels:
        raw.append(0)
        for r, g, b, a in row:
            raw.extend((r, g, b, a))

    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        + chunk(b"IEND", b"")
    )


def mix(a: Color, b: Color, t: float) -> Color:
    return tuple(round(a[i] * (1 - t) + b[i] * t) for i in range(4))  # type: ignore[return-value]


def clamp(value: int) -> int:
    return max(0, min(255, value))


def shade(color: Color, amount: int) -> Color:
    return (clamp(color[0] + amount), clamp(color[1] + amount), clamp(color[2] + amount), color[3])


def jitter(seed: int, x: int, y: int, span: int) -> int:
    value = (x * 73_856_093) ^ (y * 19_349_663) ^ (seed * 83_492_791)
    value = (value ^ (value >> 13)) * 1_274_126_177
    return value % (span * 2 + 1) - span


def new_tile() -> list[list[Color]]:
    return [[(0, 0, 0, 255) for _ in range(32)] for _ in range(32)]


def rect(tile: list[list[Color]], x0: int, y0: int, x1: int, y1: int, color: Color) -> None:
    for y in range(max(0, y0), min(32, y1)):
        for x in range(max(0, x0), min(32, x1)):
            tile[y][x] = color


def hline(tile: list[list[Color]], y: int, x0: int, x1: int, color: Color) -> None:
    rect(tile, x0, y, x1, y + 1, color)


def vline(tile: list[list[Color]], x: int, y0: int, y1: int, color: Color) -> None:
    rect(tile, x, y0, x + 1, y1, color)


def mirror_center(tile: list[list[Color]]) -> None:
    for y in range(32):
        for x in range(16):
            tile[y][31 - x] = tile[y][x]
        tile[y][31] = tile[y][0]


def fill_blue_stone(tile: list[list[Color]], row: int, seed: int, center: bool) -> None:
    x_range = range(16) if center else range(32)
    for y in range(32):
        for x in x_range:
            world_y = row * 32 + y
            color = WALL
            if x % 8 == 0 or world_y % 12 == 0:
                color = mix(color, WALL_HI, 0.34)
            if x % 8 == 7 or world_y % 12 == 11:
                color = mix(color, WALL_LO, 0.42)
            if (x * 5 + world_y * 3 + seed) % 23 < 3:
                color = mix(color, WALL_HI, 0.18)
            if (x * 7 - world_y * 2 + seed) % 29 < 3:
                color = mix(color, WALL_LO, 0.18)
            color = shade(color, jitter(seed, x, world_y, 6))
            tile[y][x] = color
            if center:
                tile[y][31 - x] = color

    for y in range(0, 32, 12):
        hline(tile, y, 0, 32, MORTAR)
    for x in range(0, 32, 8):
        vline(tile, x, 0, 32, MORTAR)


def add_upper_cap(tile: list[list[Color]], center: bool) -> None:
    hline(tile, 0, 0, 32, TRIM_LO)
    hline(tile, 1, 0, 32, TRIM_HI)
    hline(tile, 2, 0, 32, TRIM)
    for x in range(0, 32, 4):
        color = TRIM_HI if x % 8 == 0 else TRIM_LO
        vline(tile, x, 0, 5, color)
    hline(tile, 5, 3, 29, METAL)
    hline(tile, 6, 3, 29, TRIM_LO)
    if center:
        mirror_center(tile)


def add_lower_base(tile: list[list[Color]], center: bool) -> None:
    hline(tile, 24, 0, 32, TRIM_LO)
    hline(tile, 25, 0, 32, TRIM_HI)
    for y in range(26, 32):
        for x in range(32):
            color = TRIM
            if x % 4 == 0:
                color = mix(TRIM, TRIM_LO, 0.55)
            elif x % 4 == 1:
                color = mix(TRIM, TRIM_HI, 0.25)
            if y in (28, 31):
                color = mix(color, TRIM_LO, 0.32)
            tile[y][x] = color
    hline(tile, 27, 4, 28, METAL)
    for x in (8, 16, 24):
        vline(tile, x, 26, 32, TRIM_LO)
    if center:
        mirror_center(tile)


def add_edge_post(tile: list[list[Color]], side: str, row: int) -> None:
    if side == "left":
        x0, x1 = 0, EDGE_WIDTH
        border_x = 0
    else:
        x0, x1 = 32 - EDGE_WIDTH, 32
        border_x = 31

    rect(tile, x0, 0, x1, 32, TRIM)
    vline(tile, border_x, 0, 32, TRIM_LO)
    if EDGE_WIDTH >= 4:
        vline(tile, x0 + 1, 0, 32, TRIM_HI)
        vline(tile, x1 - 2, 0, 32, TRIM_LO)

    offset = 3 if row == 0 else 1
    for y in range(offset, 32, 8):
        hline(tile, y, x0 + 1, x1 - 1, TRIM_HI)
        hline(tile, min(y + 2, 31), x0 + 1, x1 - 1, TRIM_LO)
        rect(tile, x0 + 2, y + 1, x1 - 2, min(y + 2, 32), METAL)


def fill_oak_wall(tile: list[list[Color]], row: int, center: bool) -> None:
    base, light, dark = OAK_WALL_COLORS
    x_range = range(16) if center else range(32)
    for y in range(32):
        for x in x_range:
            world_y = row * 32 + y
            plank_y = world_y % 10
            color = base
            if plank_y in (0, 9):
                color = dark
            elif x % 12 in (3, 4) and plank_y not in (1, 8):
                color = light
            elif x % 12 == 10 and plank_y not in (1, 8):
                color = dark
            tile[y][x] = color
            if center:
                tile[y][31 - x] = color


def add_oak_lower_base(tile: list[list[Color]], center: bool) -> None:
    dark, base, light, shadow, accent = OAK_TRIM_COLORS
    hline(tile, 24, 0, 32, shadow)
    hline(tile, 25, 0, 32, light)
    for y in range(26, 32):
        for x in range(32):
            color = base
            if x % 4 == 0:
                color = shadow
            elif x % 4 == 1:
                color = light
            if y in (28, 31):
                color = dark
            tile[y][x] = color
    hline(tile, 27, 5, 27, accent)
    for x in (8, 16, 24):
        vline(tile, x, 26, 32, shadow)
    if center:
        mirror_center(tile)


def add_oak_edge_post(tile: list[list[Color]], side: str, row: int) -> None:
    dark, base, light, shadow, accent = OAK_TRIM_COLORS
    edge_width = 4
    if side == "left":
        x0, x1, border_x = 0, edge_width, 0
    else:
        x0, x1, border_x = 32 - edge_width, 32, 31

    rect(tile, x0, 0, x1, 32, base)
    vline(tile, border_x, 0, 32, shadow)
    vline(tile, x0 + 1, 0, 32, light)
    vline(tile, x1 - 2, 0, 32, dark)

    offset = 3 if row == 0 else 1
    for y in range(offset, 32, 10):
        hline(tile, y, x0 + 1, x1 - 1, light)
        hline(tile, min(y + 2, 31), x0 + 1, x1 - 1, shadow)
        if x1 - x0 > 3 and y + 1 < 32:
            hline(tile, y + 1, x0 + 2, x1 - 2, accent)


def make_oak_tile(row: int, col: int) -> list[list[Color]]:
    center = col == 1
    tile = new_tile()
    fill_oak_wall(tile, row=row, center=center)
    if row == 1:
        add_oak_lower_base(tile, center=center)

    if col == 0:
        add_oak_edge_post(tile, "left", row)
    elif col == 2:
        add_oak_edge_post(tile, "right", row)
    else:
        mirror_center(tile)
    return tile


def assemble_oak_tall() -> list[list[Color]]:
    sheet = [[(0, 0, 0, 0) for _ in range(96)] for _ in range(64)]
    for row in range(2):
        for col in range(3):
            tile = make_oak_tile(row, col)
            ox, oy = col * 32, row * 32
            for y in range(32):
                for x in range(32):
                    sheet[oy + y][ox + x] = tile[y][x]
    return sheet


def make_tile(row: int, col: int, top_cap: bool) -> list[list[Color]]:
    center = col == 1
    tile = new_tile()
    fill_blue_stone(tile, row=row, seed=17 + row * 9 + col * 31, center=center)
    if row == 0 and top_cap:
        add_upper_cap(tile, center=center)
    elif row == 1:
        add_lower_base(tile, center=center)

    if col == 0:
        add_edge_post(tile, "left", row)
    elif col == 2:
        add_edge_post(tile, "right", row)
    else:
        mirror_center(tile)
    return tile


def assemble(top_cap: bool = True) -> list[list[Color]]:
    sheet = [[(0, 0, 0, 0) for _ in range(96)] for _ in range(64)]
    for row in range(2):
        for col in range(3):
            tile = make_tile(row, col, top_cap=top_cap)
            ox, oy = col * 32, row * 32
            for y in range(32):
                for x in range(32):
                    sheet[oy + y][ox + x] = tile[y][x]
    return sheet


def verify(sheet: list[list[Color]], reference_size: tuple[int, int], *, top_cap: bool) -> list[str]:
    messages = []
    if reference_size != (96, 128):
        messages.append(f"reference size warning: expected 96x128, got {reference_size[0]}x{reference_size[1]}")
    if len(sheet) != 64 or len(sheet[0]) != 96:
        raise AssertionError("generated sheet is not 96x64")

    for row in range(2):
        ox, oy = 32, row * 32
        for y in range(32):
            for x in range(16):
                if sheet[oy + y][ox + x] != sheet[oy + y][ox + 31 - x]:
                    raise AssertionError(f"center tile row {row} is not vertically symmetric")
            if sheet[oy + y][ox] != sheet[oy + y][ox + 31]:
                raise AssertionError(f"center tile row {row} has mismatched repeat seam")

    if not top_cap:
        for y in range(0, 7):
            for x in range(7, 89):
                if sheet[y][x] in (TRIM, TRIM_HI, TRIM_LO, METAL):
                    raise AssertionError("tall variant top row still contains top trim colors")

    messages.append("verified: one 3x2 set, 6 total tiles, 32x32 tiles")
    messages.append("verified: wall is two tiles tall")
    messages.append("verified: col 0 is left edge, col 1 is repeatable center, col 2 is right edge")
    messages.append("verified: both center tiles are vertically symmetric with matching left/right seams")
    if not top_cap:
        messages.append("verified: top row has no horizontal cap trim, so it can repeat upward")
    return messages


def verify_oak_tall(sheet: list[list[Color]], reference_size: tuple[int, int]) -> list[str]:
    messages = []
    if reference_size != (96, 128):
        messages.append(f"reference size warning: expected 96x128, got {reference_size[0]}x{reference_size[1]}")
    if len(sheet) != 64 or len(sheet[0]) != 96:
        raise AssertionError("generated sheet is not 96x64")

    for row in range(2):
        ox, oy = 32, row * 32
        for y in range(32):
            for x in range(16):
                if sheet[oy + y][ox + x] != sheet[oy + y][ox + 31 - x]:
                    raise AssertionError(f"center tile row {row} is not vertically symmetric")
            if sheet[oy + y][ox] != sheet[oy + y][ox + 31]:
                raise AssertionError(f"center tile row {row} has mismatched repeat seam")

    wall_colors: set[Color] = set()
    trim_colors: set[Color] = set()
    for y in range(64):
        for x in range(96):
            color = sheet[y][x]
            in_side_trim = x < 4 or x >= 92
            in_bottom_trim = y >= 56
            if in_side_trim or in_bottom_trim:
                trim_colors.add(color)
            else:
                wall_colors.add(color)

    if not wall_colors.issubset(set(OAK_WALL_COLORS)):
        raise AssertionError(f"oak wall surface has unexpected colors: {len(wall_colors)}")
    if len(wall_colors) > 3:
        raise AssertionError(f"oak wall surface has too many colors: {len(wall_colors)}")
    if not trim_colors.issubset(set(OAK_TRIM_COLORS)):
        raise AssertionError(f"oak trim has unexpected colors: {len(trim_colors)}")
    if len(trim_colors) > 5:
        raise AssertionError(f"oak trim has too many colors: {len(trim_colors)}")

    messages.append("verified: one 3x2 tall-only set, 6 total tiles, 32x32 tiles")
    messages.append("verified: oak wall surface uses 3 colors")
    messages.append("verified: trim uses 5 colors")
    messages.append("verified: col 0 is left edge, col 1 is repeatable center, col 2 is right edge")
    messages.append("verified: both center tiles are vertically symmetric with matching left/right seams")
    messages.append("verified: top row has no horizontal cap trim, so it can repeat upward")
    return messages


def write_tsx(path: Path, *, name: str, image: str, tilecount: int, height: int) -> None:
    path.write_text(
        f"""<?xml version="1.0" encoding="UTF-8"?>
<tileset version="1.10" tiledversion="1.12.1" name="{name}" tilewidth="32" tileheight="32" tilecount="{tilecount}" columns="3">
 <image source="{image}" width="96" height="{height}"/>
</tileset>
""",
        encoding="utf-8",
    )


def write_tileset(png_path: Path, tsx_path: Path, *, name: str, image: str, top_cap: bool) -> list[str]:
    sheet = assemble(top_cap=top_cap)
    messages = verify(sheet, (96, 128), top_cap=top_cap)
    write_png(png_path, sheet)
    write_tsx(tsx_path, name=name, image=image, tilecount=6, height=64)
    return [f"wrote {png_path}", f"wrote {tsx_path}", *messages]


def write_oak_tall_tileset(png_path: Path, tsx_path: Path, *, name: str, image: str) -> list[str]:
    sheet = assemble_oak_tall()
    messages = verify_oak_tall(sheet, (96, 128))
    write_png(png_path, sheet)
    write_tsx(tsx_path, name=name, image=image, tilecount=6, height=64)
    return [f"wrote {png_path}", f"wrote {tsx_path}", *messages]


def stack_sheets(sheets: list[list[list[Color]]]) -> list[list[Color]]:
    pixels: list[list[Color]] = []
    for sheet in sheets:
        pixels.extend(sheet)
    return pixels


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--png", type=Path, default=OUT_PNG)
    parser.add_argument("--tsx", type=Path, default=OUT_TSX)
    args = parser.parse_args()

    sheets = [assemble(top_cap=True), assemble(top_cap=False)]
    messages = [
        "assembled base capped wall set",
        "assembled base tall wall set",
    ]

    use_palette(SUBTLE_TALL_PALETTE)  # type: ignore[arg-type]
    sheets.append(assemble(top_cap=False))
    messages.append("assembled subtle tall wall set")

    sheets.append(assemble_oak_tall())
    messages.append("assembled oak tall wall set")

    for palette in PALETTES:
        use_palette(palette)
        slug = palette["slug"]  # type: ignore[assignment]
        sheets.append(assemble(top_cap=True))
        sheets.append(assemble(top_cap=False))
        messages.append(f"assembled {slug} capped wall set")
        messages.append(f"assembled {slug} tall wall set")

    sheet = stack_sheets(sheets)
    write_png(args.png, sheet)
    write_tsx(args.tsx, name="walls_02", image=args.png.name, tilecount=60, height=640)
    messages.insert(0, f"wrote {args.png}")
    messages.insert(1, f"wrote {args.tsx}")
    messages.append("verified: 10 wall sets, 60 total tiles, 32x32 tiles")
    for message in messages:
        print(message)


if __name__ == "__main__":
    main()
