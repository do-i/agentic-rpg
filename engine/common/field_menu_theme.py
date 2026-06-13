from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pygame


REPO_ROOT = Path(__file__).resolve().parents[2]
ASSET_ROOT = REPO_ROOT / "rusted_kingdoms" / "assets"
DEFAULT_BG = ASSET_ROOT / "images" / "battle_bg" / "zone4-sanctum-bg-1280x468.webp"

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
ROW_DIMMED = (38, 38, 48, 150)

_IMAGE_CACHE: dict[tuple[int, Path], pygame.Surface | None] = {}
_BG_CACHE: dict[tuple[int, int, int, Path], pygame.Surface] = {}
_ICON_CACHE: dict[tuple[int, str, int, bool], pygame.Surface] = {}

_ICON_COLORS: tuple[tuple[int, int, int], ...] = (
    GOLD,
    TEAL,
    VIOLET,
    EMBER,
    (118, 174, 95),
    (94, 139, 205),
    (196, 112, 151),
)


def load_image(path: Path) -> pygame.Surface | None:
    display_id = _display_cache_id()
    if display_id == 0:
        return _load_image_uncached(path)
    cache_key = (display_id, path)
    if cache_key not in _IMAGE_CACHE:
        _IMAGE_CACHE[cache_key] = _load_image_uncached(path)
    return _IMAGE_CACHE[cache_key]


def _load_image_uncached(path: Path) -> pygame.Surface | None:
    try:
        image = pygame.image.load(str(path))
        if pygame.display.get_surface() is not None:
            return image.convert_alpha()
        return image
    except (FileNotFoundError, pygame.error):
        return None


def _display_cache_id() -> int:
    display = pygame.display.get_surface() if pygame.display.get_init() else None
    return id(display) if display is not None else 0


def render_backdrop(screen: pygame.Surface, bg_path: Path = DEFAULT_BG) -> None:
    sw, sh = screen.get_size()
    display_id = _display_cache_id()
    cache_key = (display_id, sw, sh, bg_path)
    bg = _BG_CACHE.get(cache_key) if display_id else None
    if bg is None:
        bg = _build_backdrop(sw, sh, bg_path)
        if display_id:
            _BG_CACHE[cache_key] = bg
    screen.blit(bg, (0, 0))


def _build_backdrop(sw: int, sh: int, bg_path: Path) -> pygame.Surface:
    src = load_image(bg_path)
    if src is None:
        bg = pygame.Surface((sw, sh))
        bg.fill((12, 12, 18))
    else:
        scale = max(sw / src.get_width(), sh / src.get_height())
        size = (max(1, int(src.get_width() * scale)), max(1, int(src.get_height() * scale)))
        scaled = pygame.transform.smoothscale(src, size)
        bg = pygame.Surface((sw, sh))
        bg.blit(scaled, ((sw - size[0]) // 2, (sh - size[1]) // 2))
    veil = pygame.Surface((sw, sh), pygame.SRCALPHA)
    veil.fill((5, 7, 12, 168))
    bg.blit(veil, (0, 0))
    _draw_vignette(bg)
    return bg


def dim_screen(screen: pygame.Surface, alpha: int = 176) -> None:
    """Darken whatever is already drawn — backdrop for a centered modal."""
    veil = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
    veil.fill((4, 5, 9, alpha))
    screen.blit(veil, (0, 0))


def render_modal(
    screen: pygame.Surface,
    width: int,
    height: int,
    *,
    title: str | None = None,
    title_font: pygame.font.Font | None = None,
    dim: bool = True,
) -> pygame.Rect:
    """Dim the screen and draw a centered themed panel. Returns its rect."""
    if dim:
        dim_screen(screen)
    rect = pygame.Rect(
        (screen.get_width() - width) // 2,
        (screen.get_height() - height) // 2,
        width,
        height,
    )
    render_panel(screen, rect, active=True, title=title, title_font=title_font)
    return rect


def render_hint(
    screen: pygame.Surface,
    font: pygame.font.Font,
    text: str,
    x: int,
    y: int,
    *,
    color: tuple[int, int, int] = DIM,
) -> None:
    screen.blit(font.render(text, True, color), (x, y))


def render_header(
    screen: pygame.Surface,
    title_font: pygame.font.Font,
    sub_font: pygame.font.Font,
    title: str,
    subtitle: str,
    x: int,
    y: int,
) -> None:
    accent = pygame.Rect(x, y + 10, 7, 46)
    pygame.draw.rect(screen, EMBER, accent)
    pygame.draw.rect(screen, GOLD, (accent.x + 10, accent.y, 2, accent.h))
    title_s = title_font.render(title, True, INK)
    sub_s = sub_font.render(subtitle, True, MUTED)
    screen.blit(title_s, (x + 24, y))
    screen.blit(sub_s, (x + 26, y + title_s.get_height() - 2))


def render_panel(
    screen: pygame.Surface,
    rect: pygame.Rect,
    *,
    active: bool = False,
    title: str | None = None,
    title_font: pygame.font.Font | None = None,
) -> None:
    surf = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(surf, PANEL, surf.get_rect(), border_radius=6)
    pygame.draw.rect(surf, PANEL_DARK, (6, 6, rect.w - 12, rect.h - 12), border_radius=5)
    pygame.draw.rect(
        surf,
        BORDER_ACTIVE if active else BORDER,
        surf.get_rect().inflate(-1, -1),
        width=2 if active else 1,
        border_radius=6,
    )
    pygame.draw.line(surf, (255, 218, 126, 86), (14, 12), (rect.w - 14, 12), 1)
    pygame.draw.line(surf, (0, 0, 0, 95), (14, rect.h - 13), (rect.w - 14, rect.h - 13), 1)
    screen.blit(surf, rect.topleft)
    if title and title_font:
        label = title_font.render(title, True, GOLD)
        screen.blit(label, (rect.x + 18, rect.y + 14))


def render_icon_row(
    screen: pygame.Surface,
    font: pygame.font.Font,
    rect: pygame.Rect,
    text: str,
    *,
    icon_key: str,
    focused: bool,
    dimmed_sel: bool,
    color: tuple[int, int, int],
    image_path: Path | None = None,
    right_text: str = "",
    right_font: pygame.font.Font | None = None,
    subtext: str = "",
    sub_font: pygame.font.Font | None = None,
    badge: str = "",
) -> None:
    fill = ROW_ACTIVE if focused else ROW_DIMMED if dimmed_sel else ROW
    border = BORDER_ACTIVE if focused else BORDER if dimmed_sel else (82, 70, 50)
    row_surf = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(row_surf, fill, row_surf.get_rect(), border_radius=5)
    pygame.draw.rect(row_surf, border, row_surf.get_rect().inflate(-1, -1), 1, border_radius=5)
    if focused:
        pygame.draw.rect(row_surf, (255, 217, 117, 36), (3, 3, rect.w - 6, rect.h - 6), border_radius=4)
    screen.blit(row_surf, rect.topleft)

    icon_size = min(36, rect.h - 10)
    icon = icon_surface(icon_key, icon_size, dimmed=not focused and color == DIM, image_path=image_path)
    screen.blit(icon, (rect.x + 8, rect.y + (rect.h - icon_size) // 2))

    tx = rect.x + 18 + icon_size
    ty = rect.y + 8 if subtext else rect.y + (rect.h - font.get_height()) // 2
    max_w = rect.right - tx - 14
    if right_text:
        rf = right_font or font
        right = rf.render(right_text, True, MUTED if color != DIM else DIM)
        max_w -= right.get_width() + 12
        screen.blit(right, (rect.right - 10 - right.get_width(), rect.y + (rect.h - right.get_height()) // 2))
    label = fit_text(font, text, color, max_w)
    screen.blit(label, (tx, ty))
    if subtext and sub_font:
        sub = fit_text(sub_font, subtext, MUTED if color != DIM else DIM, max_w)
        screen.blit(sub, (tx, rect.y + rect.h - sub_font.get_height() - 7))
    if badge:
        badge_font = sub_font or font
        badge_s = badge_font.render(badge, True, (25, 18, 12))
        brect = pygame.Rect(rect.right - badge_s.get_width() - 16, rect.y + 7, badge_s.get_width() + 10, badge_s.get_height() + 4)
        pygame.draw.rect(screen, GOLD if focused else MUTED, brect, border_radius=4)
        screen.blit(badge_s, (brect.x + 5, brect.y + 2))


def icon_surface(
    key: str,
    size: int,
    *,
    dimmed: bool = False,
    image_path: Path | None = None,
) -> pygame.Surface:
    if image_path is not None:
        image = load_image(image_path)
        if image is not None:
            return _frame_icon(pygame.transform.smoothscale(image, (size, size)), size, dimmed)
    display_id = _display_cache_id()
    cache_key = (display_id, key, size, dimmed)
    if display_id:
        cached = _ICON_CACHE.get(cache_key)
        if cached is not None:
            return cached.copy()
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    color = _ICON_COLORS[sum(ord(c) for c in key) % len(_ICON_COLORS)]
    if dimmed:
        color = tuple(max(48, c // 2) for c in color)
    center = size // 2
    pygame.draw.circle(surf, (10, 10, 14, 218), (center, center), center)
    pygame.draw.circle(surf, color, (center, center), center - 2)
    pygame.draw.circle(surf, (255, 245, 190, 68), (center - size // 5, center - size // 5), max(2, size // 6))
    diamond = [
        (center, 5),
        (size - 5, center),
        (center, size - 5),
        (5, center),
    ]
    pygame.draw.polygon(surf, (20, 19, 23, 154), diamond, 2)
    letter = _icon_letter(key)
    font = pygame.font.SysFont("arial", max(10, int(size * 0.44)), bold=True)
    label = font.render(letter, True, (16, 13, 11))
    surf.blit(label, ((size - label.get_width()) // 2, (size - label.get_height()) // 2))
    if display_id:
        _ICON_CACHE[cache_key] = surf
    return surf.copy()


def member_icon_path(member_id: str) -> Path | None:
    path = ASSET_ROOT / "images" / f"{member_id}_profile.png"
    return path if path.exists() else None


def draw_stat_bar(
    screen: pygame.Surface,
    rect: pygame.Rect,
    value: int,
    maximum: int,
    color: tuple[int, int, int],
) -> None:
    pygame.draw.rect(screen, (17, 17, 22), rect, border_radius=4)
    pygame.draw.rect(screen, (75, 64, 45), rect, 1, border_radius=4)
    if maximum > 0:
        fill = rect.copy()
        fill.w = max(3, int(rect.w * max(0.0, min(1.0, value / maximum))))
        pygame.draw.rect(screen, color, fill.inflate(-2, -2), border_radius=3)


def fit_text(
    font: pygame.font.Font,
    text: str,
    color: tuple[int, int, int],
    max_w: int,
) -> pygame.Surface:
    if max_w <= 0 or font.size(text)[0] <= max_w:
        return font.render(text, True, color)
    ellipsis = "..."
    trimmed = text
    while trimmed and font.size(trimmed + ellipsis)[0] > max_w:
        trimmed = trimmed[:-1]
    return font.render((trimmed or text[:1]) + ellipsis, True, color)


def wrap_text(font: pygame.font.Font, text: str, max_w: int, limit: int = 3) -> list[str]:
    words = text.split()
    lines: list[str] = []
    line = ""
    for word in words:
        candidate = f"{line} {word}".strip()
        if line and font.size(candidate)[0] > max_w:
            lines.append(line)
            line = word
            if len(lines) >= limit:
                break
        else:
            line = candidate
    if line and len(lines) < limit:
        lines.append(line)
    return lines


def draw_divider(screen: pygame.Surface, x: int, y: int, w: int) -> None:
    pygame.draw.line(screen, (82, 66, 40), (x, y), (x + w, y), 1)
    pygame.draw.line(screen, (246, 208, 123), (x, y + 1), (x + w // 3, y + 1), 1)


def _frame_icon(image: pygame.Surface, size: int, dimmed: bool) -> pygame.Surface:
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    surf.blit(image, (0, 0))
    pygame.draw.rect(surf, (22, 18, 14, 180), surf.get_rect(), 2, border_radius=4)
    if dimmed:
        veil = pygame.Surface((size, size), pygame.SRCALPHA)
        veil.fill((12, 12, 16, 108))
        surf.blit(veil, (0, 0))
    return surf


def _icon_letter(key: str) -> str:
    for part in key.replace("-", "_").split("_"):
        if part:
            return part[0].upper()
    return "?"


def _draw_vignette(surface: pygame.Surface) -> None:
    sw, sh = surface.get_size()
    bands: Iterable[tuple[int, int]] = ((0, 78), (18, 48), (40, 30))
    for inset, alpha in bands:
        rect = pygame.Rect(inset, inset, sw - inset * 2, sh - inset * 2)
        veil = pygame.Surface((sw, sh), pygame.SRCALPHA)
        veil.fill((0, 0, 0, alpha))
        pygame.draw.rect(veil, (0, 0, 0, 0), rect, border_radius=18)
        surface.blit(veil, (0, 0))
