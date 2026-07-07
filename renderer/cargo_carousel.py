"""
Cargo Dossier Carousel — Epic 8.2.

Main-menu replay screen. Shows six chapter cargo cards, each with:
  * vector silhouette of the cargo
  * chapter title + cargo brief + flight quirk
  * "✓ DELIVERED" stamp (or "??? — UNCOVERED" stamp for incomplete chapters)
  * best-run stats (deepest sector, best single-run credits, secrets found)
  * HARDCORE indicator + best HARDCORE clear time when the chapter has
    been cleared at least once (Epic 8.4)

The cards live in a horizontal carousel — `←` / `→` cycle the focused
card, `ENTER` starts a fresh run targeted at that chapter. `H` toggles
the HARDCORE flag for the next run when the chapter qualifies.

Pure draw + input intent — the screen never mutates state directly.
The Game loop reads `selection_chapter` / `wants_hardcore` after a key
event to decide whether to start the run.
"""
from __future__ import annotations
import math

import pygame

from config import settings as S
from core.text import get_font


_CARDS: tuple[tuple[int, str, str, str, str, tuple, tuple], ...] = (
    (1, "ACOUSTIC ARCHIVE",  "archive",
     "Illegal music library.",
     "Proximity → signal static.",
     (160,  80,  30), (240, 140, 50)),
    (2, "MYCORRHIZAL PAYLOAD", "shroom",
     "Psychoactive fungal spores.",
     "Spore leak → controls invert.",
     ( 40, 120, 200), ( 90, 220, 170)),
    (3, "THE PAPERWORK",     "forms",
     "Sentient bureaucratic forms.",
     "Filing popups under fire.",
     (140, 160,  80), (200, 220, 110)),
    (4, "SCHRÖDINGER VIP",   "vip",
     "Passenger: alive or deceased.",
     "Observation collapses payout.",
     (200, 160,  40), (255, 220,  90)),
    (5, "MERCY",             "drive",
     "Chen's zero-write exploit drive.",
     "One plug-in ends the debt.",
     (180, 100,  40), (255, 160,  70)),
    (6, "THE UPLOAD",        "keycard",
     "Deploy MERCY. Hold the line.",
     "90 seconds. Alarms. No exit.",
     ( 60, 130, 180), (140, 210, 240)),
)


def card_count() -> int:
    return len(_CARDS)


def card_chapter(idx: int) -> int:
    return _CARDS[idx % len(_CARDS)][0]


# ---------------------------------------------------------------------------
# Cargo silhouette renderer — mirrors the corridor cargo silhouettes so the
# dossier card visually echoes what the courier hauls.
# ---------------------------------------------------------------------------
def _draw_cargo_silhouette(surf: pygame.Surface, cx: int, cy: int,
                           kind: str, t: float, dim: float):
    if kind == "archive":
        # Vinyl + crate corner
        col_lp = (int(220 * dim), int(80 * dim), int(20 * dim))
        col_lb = (int(255 * dim), int(120 * dim), int(40 * dim))
        col_in = (int(40 * dim), int(15 * dim), 0)
        pygame.draw.circle(surf, col_lp, (cx, cy), 32)
        pygame.draw.circle(surf, col_lb, (cx, cy), 32, 1)
        for r in (24, 18, 12):
            pygame.draw.circle(surf, col_lb, (cx, cy), r, 1)
        pygame.draw.circle(surf, col_in, (cx, cy), 5)
        return
    if kind == "shroom":
        # Bioluminescent jar
        glow = 0.55 + 0.45 * math.sin(t * 3.2)
        c_jar = (int(80 * dim), int(220 * dim), int(160 * dim))
        c_lid = (int(60 * dim), int(160 * dim), int(110 * dim))
        c_spore = (int(180 * dim), int(255 * dim), int(80 * dim * (0.55 + 0.45 * glow)))
        pygame.draw.rect(surf, (int(20 * dim), int(40 * dim), int(30 * dim)),
                         pygame.Rect(cx - 22, cy - 20, 44, 48))
        pygame.draw.rect(surf, c_jar,
                         pygame.Rect(cx - 22, cy - 20, 44, 48), 2)
        pygame.draw.rect(surf, c_lid,
                         pygame.Rect(cx - 24, cy - 26, 48, 8))
        for i, dy in enumerate((-4, 6, 16)):
            pygame.draw.circle(surf, c_spore,
                               (cx - 8 + i * 8, cy + dy), 4)
        return
    if kind == "forms":
        # Stack of forms
        for i in range(4):
            shade = max(0.45, 0.95 - i * 0.15)
            col = (int(220 * shade * dim),
                   int(210 * shade * dim),
                   int(180 * shade * dim))
            edge = (int(255 * dim), int(240 * dim), int(200 * dim))
            rect = pygame.Rect(cx - 24 + i, cy - 20 + i * 5, 48, 14)
            pygame.draw.rect(surf, col, rect)
            pygame.draw.rect(surf, edge, rect, 1)
            # Two text lines
            for ly in (3, 8):
                pygame.draw.line(surf, edge,
                                 (rect.left + 4, rect.top + ly),
                                 (rect.right - 4, rect.top + ly), 1)
        return
    if kind == "vip":
        # Sealed box with question mark
        pulse = 0.65 + 0.35 * math.sin(t * 2.5)
        col_b = (int(60 * dim), int(20 * dim), int(80 * dim))
        col_e = (int(140 * dim), int(70 * dim), int(180 * dim))
        col_q = (int(220 * dim * pulse), int(140 * dim * pulse), int(255 * dim * pulse))
        pygame.draw.rect(surf, col_b, pygame.Rect(cx - 24, cy - 22, 48, 44))
        pygame.draw.rect(surf, col_e, pygame.Rect(cx - 24, cy - 22, 48, 44), 2)
        f = get_font(22, bold=True)
        s = f.render("?", True, col_q)
        surf.blit(s, (cx - s.get_width() // 2, cy - s.get_height() // 2))
        return
    if kind == "drive":
        # MERCY drive — a data stick with a small amber LED
        col_b = (int(40 * dim), int(26 * dim), int(14 * dim))
        col_e = (int(200 * dim), int(130 * dim), int(60 * dim))
        col_l = (int(255 * dim), int(160 * dim), int(40 * dim))
        # Body of the drive
        pygame.draw.rect(surf, col_b, pygame.Rect(cx - 10, cy - 28, 20, 44))
        pygame.draw.rect(surf, col_e, pygame.Rect(cx - 10, cy - 28, 20, 44), 2)
        # USB connector nub at the bottom
        pygame.draw.rect(surf, col_e, pygame.Rect(cx - 6, cy + 16, 12, 8))
        pygame.draw.rect(surf, col_b, pygame.Rect(cx - 4, cy + 18, 8, 4))
        # Pulsing LED indicator on the face
        led_pulse = 0.5 + 0.5 * abs(math.sin(t * 2.8))
        led_col = tuple(int(c * led_pulse) for c in col_l)
        pygame.draw.circle(surf, led_col, (cx, cy - 16), 4)
        # Label etched on the body
        f8 = get_font(7, bold=True)
        lbl = f8.render("MERCY", True, col_e)
        surf.blit(lbl, (cx - lbl.get_width() // 2, cy - 4))
        return
    if kind == "keycard":
        # Nova Soma access keycard — flat, corporate, cold
        pulse = 0.6 + 0.4 * abs(math.sin(t * 1.4))
        col_b = (int(20 * dim), int(34 * dim), int(46 * dim))
        col_e = (int(100 * dim), int(180 * dim), int(220 * dim))
        col_s = (int(140 * dim * pulse), int(210 * dim * pulse), int(240 * dim * pulse))
        # Card body — landscape orientation
        pygame.draw.rect(surf, col_b, pygame.Rect(cx - 30, cy - 20, 60, 38))
        pygame.draw.rect(surf, col_e, pygame.Rect(cx - 30, cy - 20, 60, 38), 2)
        # Magnetic stripe
        pygame.draw.rect(surf, (int(30 * dim), int(40 * dim), int(50 * dim)),
                         pygame.Rect(cx - 28, cy - 14, 56, 8))
        # Nova Soma logo — a cold rectangle with "NS" in it
        pygame.draw.rect(surf, col_e, pygame.Rect(cx - 22, cy - 2, 18, 14))
        f7 = get_font(7, bold=True)
        ns = f7.render("NS", True, col_b)
        surf.blit(ns, (cx - 22 + (18 - ns.get_width()) // 2,
                       cy - 2 + (14 - ns.get_height()) // 2))
        # Pulsing "UPLOAD" status indicator on the right side
        st = f7.render("UPLOAD", True, col_s)
        surf.blit(st, (cx + 2, cy + 2))
        return


# ---------------------------------------------------------------------------
# Public render entry — called by Game when _menu_mode == "dossiers".
# ---------------------------------------------------------------------------

def draw_carousel(
    screen: pygame.Surface,
    *,
    meta,
    stats,
    cursor: int,
    t: float,
) -> None:
    """Draw the cargo carousel with the selected card centre-stage."""
    overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 220))
    screen.blit(overlay, (0, 0))

    cx = S.SCREEN_W // 2
    cy = S.SCREEN_H // 2 - 28

    # Title
    fh = get_font(15, bold=True)
    title = fh.render("CARGO DOSSIERS — REPLAY ANY CHAPTER",
                      True, (220, 200, 90))
    screen.blit(title, (cx - title.get_width() // 2, 70))

    # Sub-line
    fsm = get_font(11)
    sub_lines = [
        "Pick a card to dispatch your courier on a fresh run of that chapter.",
        "↑ ↓ navigate fields    ←  →  cycle cards    ENTER deploy    H toggle HARDCORE    ESC back",
    ]
    for i, line in enumerate(sub_lines):
        ts = fsm.render(line, True, (140, 130, 100))
        screen.blit(ts, (cx - ts.get_width() // 2, 92 + i * 14))

    # Layout: 5 visible cards at most, focused card centred + larger.
    n = len(_CARDS)
    cursor = cursor % n
    card_w = 220
    card_h = 270
    gap = 32
    # Render two side cards on each flank.
    for offset in (-2, -1, 0, 1, 2):
        idx = (cursor + offset) % n
        card = _CARDS[idx]
        x = cx + offset * (card_w + gap) - card_w // 2
        y = cy - card_h // 2 + 30
        # Side cards shrink and fade.
        if offset == 0:
            scale = 1.0
            alpha = 1.0
        elif abs(offset) == 1:
            scale = 0.85
            alpha = 0.78
        else:
            scale = 0.7
            alpha = 0.45
        sw = int(card_w * scale)
        sh = int(card_h * scale)
        sx = x + (card_w - sw) // 2
        sy = y + (card_h - sh) // 2
        _draw_card(screen, sx, sy, sw, sh, card, t,
                   meta=meta, stats=stats,
                   focused=(offset == 0), alpha=alpha)

    # Bottom hint shows hardcore opt-in state for the selected card.
    sel_card = _CARDS[cursor]
    chapter = sel_card[0]
    completed = chapter in (meta.chapters_completed if meta else [])
    hc_unlocked = bool(meta and meta.is_hardcore_unlocked(chapter))
    hc_active   = bool(meta and meta.is_hardcore)
    fsm2 = get_font(11, bold=True)
    if hc_unlocked:
        if hc_active:
            tag = f"HARDCORE ARMED — Ch.{chapter}: tighter timers, no shops, +1 barge per sector, 1 checkpoint."
            col = (255, 70, 70)
        else:
            tag = f"HARDCORE available for Ch.{chapter}.   Press H to arm."
            col = (200, 140, 60)
        fs = fsm2.render(tag, True, col)
        screen.blit(fs, (cx - fs.get_width() // 2, S.SCREEN_H - 90))
    elif completed:
        tag = "Clear this chapter once on STANDARD to unlock HARDCORE."
        fs = fsm2.render(tag, True, (110, 110, 130))
        screen.blit(fs, (cx - fs.get_width() // 2, S.SCREEN_H - 90))


def _draw_card(surf, x, y, w, h, card, t, *,
               meta, stats, focused: bool, alpha: float):
    chapter, title, kind, desc, quirk, base_col, accent_col = card
    completed = bool(meta and chapter in meta.chapters_completed)
    pulse = 0.8 + 0.2 * abs(math.sin(t * 2.2 + chapter))
    dim   = (1.0 if completed else 0.45) * alpha

    bg = tuple(int(c * dim * 0.30) for c in base_col)
    bd = tuple(int(c * dim * pulse) for c in accent_col)

    pygame.draw.rect(surf, bg, pygame.Rect(x, y, w, h))
    pygame.draw.rect(surf, bd, pygame.Rect(x, y, w, h), 2 if focused else 1)

    # Header bar
    hdr_h = 28
    hdr_bg = tuple(int(c * dim * 0.55) for c in base_col)
    pygame.draw.rect(surf, hdr_bg, pygame.Rect(x, y, w, hdr_h))
    pygame.draw.line(surf, bd, (x, y + hdr_h), (x + w, y + hdr_h), 1)

    fh = get_font(11, bold=True)
    fb = get_font(10)
    fsm = get_font(9)

    chapter_lbl = fh.render(f"CH.{chapter}", True,
                            tuple(int(c * dim) for c in accent_col))
    surf.blit(chapter_lbl, (x + 8, y + 8))
    title_col = tuple(int(c * dim) for c in accent_col)
    title_s = fh.render(title, True, title_col)
    surf.blit(title_s, (x + w - title_s.get_width() - 8, y + 8))

    # Cargo silhouette region — top-half of the card.
    sil_cy = y + hdr_h + 56
    sil_cx = x + w // 2
    _draw_cargo_silhouette(surf, sil_cx, sil_cy, kind, t, dim)

    # Stamp: ✓ DELIVERED for completed, ??? UNCOVERED for incomplete.
    stamp_y = y + hdr_h + 100
    if completed:
        stamp_col = tuple(int(c * dim * pulse) for c in accent_col)
        st = fh.render("✓ DELIVERED", True, stamp_col)
    else:
        stamp_col = (int(160 * alpha), int(140 * alpha), int(110 * alpha))
        st = fh.render("???   UNCOVERED", True, stamp_col)
    surf.blit(st, (x + (w - st.get_width()) // 2, stamp_y))

    # Delivery v2 I.2.5 — COURIER'S PRIDE ribbon: perfect corridor sweep
    # (every chip + every secret). Permanent, gold, earned not given.
    if completed and meta is not None \
            and getattr(meta, "has_courier_pride", None) \
            and meta.has_courier_pride(chapter):
        gold = (int(255 * dim), int(210 * dim), int(60 * dim))
        pr = fsm.render("★ COURIER'S PRIDE ★", True, gold)
        surf.blit(pr, (x + (w - pr.get_width()) // 2, stamp_y - 14))

    # Description + quirk
    desc_y = stamp_y + 22
    for j, line in enumerate((desc, quirk)):
        col = tuple(int(c * dim * 0.85) for c in accent_col)
        ds = fsm.render(line, True, col)
        surf.blit(ds, (x + (w - ds.get_width()) // 2, desc_y + j * 12))

    # Best-run stats from career ledger (only if completed and stats exists).
    stats_y = desc_y + 32
    if stats is not None and completed:
        c = stats.career
        deep = (c.get("deepest_sector_per_chapter", {}) or {}).get(str(chapter), 0)
        best_credits = c.get("best_single_run_credits", 0)
        rows = [
            (f"DEEPEST SECTOR  {deep}/{S.SECTORS_PER_RUN}"
             if deep else "DEEPEST SECTOR  —"),
            f"BEST CREDITS    {best_credits:,} cr",
        ]
        for j, line in enumerate(rows):
            col = (int(160 * dim), int(180 * dim), int(150 * dim))
            ls = fsm.render(line, True, col)
            surf.blit(ls, (x + 10, stats_y + j * 12))

    # HARDCORE row — only if unlocked.
    if meta and meta.is_hardcore_unlocked(chapter):
        hc_y = stats_y + 30
        hc_t = meta.hardcore_best_time(chapter)
        hc_text = (f"HARDCORE BEST  {hc_t // 60}m {hc_t % 60:02d}s"
                   if hc_t > 0 else "HARDCORE BEST  —")
        col = (int(220 * dim), int(80 * dim), int(60 * dim))
        hs = fsm.render(hc_text, True, col)
        surf.blit(hs, (x + 10, hc_y))
        if meta.is_hardcore:
            tag = fsm.render("[HARDCORE ARMED]", True,
                             (int(255 * dim), int(80 * dim), int(80 * dim)))
            surf.blit(tag, (x + 10, hc_y + 12))


def visible_chapters(meta) -> list[int]:
    """Chapters the player can currently launch via the carousel.
    Ch.1 is always available. Each subsequent chapter unlocks once the
    previous chapter has been completed (or if it has already been cleared).
    """
    completed = set(meta.chapters_completed) if meta else set()
    out = [1]
    for ch in (2, 3, 4, 5, 6):
        if (ch - 1) in completed or ch in completed:
            out.append(ch)
    return out
