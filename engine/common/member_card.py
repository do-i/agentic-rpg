# engine/common/member_card.py
#
# Shared party-roster column used by the Status, Spells, and Equipment field
# screens. Each of those scenes shows the same left-hand list of member cards
# (portrait + name/level + class + HP/MP); factoring it here keeps the look
# identical across all three and gives them a single, consistent column width.

from __future__ import annotations

import pygame

from engine.common.color_constants import C_TEXT_DIM
from engine.common.ui.theme import GOLD, INK, MUTED, member_icon_path
from engine.common.ui.chrome import fit_text, icon_surface, render_row_frame
from engine.party.member_state import MemberState

# The roster cards are widened past the historical 300px base so that
# three-digit HP/MP values (e.g. "MP 100/100") no longer overflow the card
# frame. All three screens add the same amount so the column stays uniform.
CARD_COLUMN_EXTRA = 16


def member_column_width(screen_width: int) -> int:
    """Width of the party-roster column, shared across Status/Spells/Equipment."""
    base = min(300, max(260, int(screen_width * 0.24)))
    return base + CARD_COLUMN_EXTRA


def render_member_column(
    screen: pygame.Surface,
    panel: pygame.Rect,
    members: list[MemberState],
    *,
    selection: int,
    active_page: bool,
    font_head: pygame.font.Font,
    font_row: pygame.font.Font,
    font_meta: pygame.font.Font,
) -> None:
    """Render the list of member cards down the left panel.

    Cards are distributed down the full panel height so portraits can grow into
    the vertical space the shared icon rows leave empty. The currently selected
    card is highlighted when ``active_page`` is set, otherwise dimmed.
    """
    x = panel.x + 16
    top = panel.y + 52
    w = panel.w - 32
    if not members:
        msg = font_row.render("No members.", True, C_TEXT_DIM)
        screen.blit(msg, (x, top))
        return

    n = len(members)
    gap = 14
    avail = (panel.bottom - 16) - top
    row_h = min(118, (avail - gap * (n - 1)) // n)
    portrait = min(row_h - 16, 92)

    for i, m in enumerate(members):
        selected = (i == selection)
        row = pygame.Rect(x, top + i * (row_h + gap), w, row_h)
        _render_member_card(
            screen, row, m, portrait,
            focused=selected and active_page,
            dimmed=selected and not active_page,
            font_head=font_head, font_row=font_row, font_meta=font_meta,
        )


def _render_member_card(
    screen: pygame.Surface,
    rect: pygame.Rect,
    m: MemberState,
    portrait: int,
    *,
    focused: bool,
    dimmed: bool,
    font_head: pygame.font.Font,
    font_row: pygame.font.Font,
    font_meta: pygame.font.Font,
) -> None:
    render_row_frame(screen, rect, focused=focused, dimmed_sel=dimmed)
    icon = icon_surface(f"member_{m.id}", portrait, image_path=member_icon_path(m.id))
    screen.blit(icon, (rect.x + 12, rect.y + (rect.h - portrait) // 2))

    tx = rect.x + 24 + portrait
    max_w = rect.right - tx - 14
    name = fit_text(font_head, f"{m.name}  Lv{m.level}", INK, max_w)
    cls = fit_text(font_row, m.class_name.title(), GOLD, max_w)
    hp = font_meta.render(f"HP {m.hp}/{m.hp_max}", True, MUTED)
    mp = font_meta.render(f"MP {m.mp}/{m.mp_max}", True, MUTED)

    line_gap = 6
    block_h = (name.get_height() + line_gap + cls.get_height()
               + line_gap + max(hp.get_height(), mp.get_height()))
    ty = rect.y + (rect.h - block_h) // 2
    screen.blit(name, (tx, ty))
    ty += name.get_height() + line_gap
    screen.blit(cls, (tx, ty))
    ty += cls.get_height() + line_gap
    screen.blit(hp, (tx, ty))
    screen.blit(mp, (tx + max(hp.get_width() + 18, 96), ty))
