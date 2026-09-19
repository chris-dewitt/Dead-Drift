"""
Bax's Records — Epic 8.3.

Main-menu screen with four manila-folder tabs:

    1. CLONE LOG               — clones spun up, deaths, debt totals, deepest sector
                                 reached per chapter.
    2. RUN HIGHLIGHTS          — career stats from StatsTracker.
    3. VULNERABILITY DATABASE  — per-NPC discovered exploit keys from VocabularyVault.
    4. LORE FRAGMENTS          — text scraps collected from corridor secrets.

Aesthetic: file-cabinet metaphor — a faint manila-paper card with tabs
across the top, low-fi serif-ish caption type, mono body. Pure draw —
all data is read from `meta`, `vault`, and `stats`; this screen never
mutates state.
"""
from __future__ import annotations
import math
from typing import Iterable

import pygame

from config import settings as S
from core.text import get_font
from terminal.vault_keys import aliases_for_key


# ---------------------------------------------------------------------------
# NPC display order + human-readable labels for the Vulnerability Database.
# Matches the registry in `terminal/npc_logic.py`.
# ---------------------------------------------------------------------------
_NPC_LABEL: tuple[tuple[str, str], ...] = (
    ("gary",                  "GARY"),
    ("synthetic_droid",       "TK-9"),
    ("union_dispatcher",      "DISPATCHER"),
    ("kress",                 "KRESS"),
    ("insurance_adjuster",    "MORWENNA"),
    ("sandra",                "SANDRA"),
    ("pirate",                "KRELLBORN"),
    ("underground_dj",        "MARROW"),
    ("toll_authority",        "TOLL AUTHORITY"),
    ("nervous_fence",         "RELAY-7 FELIX"),
    ("cargo_inspector",       "INSPECTOR HOLT"),
    ("dray",                  "DRAY"),
    ("nova_soma_collections", "NOVA SOMA AI"),
    ("mira_voss",             "MIRA VOSS"),
    ("idealist_rep",          "EDMUND (IDEALIST)"),
    ("corrupt_rep",           "VINCE (CORRUPT)"),
    ("chen",                  "CHEN"),
    ("bowen",                 "BOWEN"),
    ("lost_frequency",        "LOST FREQUENCY"),
)


_TABS: tuple[str, ...] = (
    "CLONE LOG",
    "RUN HIGHLIGHTS",
    "VULNERABILITY DB",
    "LORE FRAGMENTS",
)


# ---------------------------------------------------------------------------
# Public render entry — called by Game when _menu_mode == "records".
# ---------------------------------------------------------------------------

def draw_records(
    screen: pygame.Surface,
    *,
    meta,
    vault,
    stats,
    tab_idx: int,
    scroll: int,
    t: float,
) -> None:
    """Render Bax's Records over a dim backdrop. Pure draw — no state changes."""
    overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 220))
    screen.blit(overlay, (0, 0))

    panel_w = min(820, S.SCREEN_W - 120)
    panel_h = min(500, S.SCREEN_H - 140)
    panel_x = (S.SCREEN_W - panel_w) // 2
    panel_y = (S.SCREEN_H - panel_h) // 2

    _draw_folder_panel(screen, panel_x, panel_y, panel_w, panel_h, t)
    _draw_tabs(screen, panel_x, panel_y, panel_w, tab_idx, t)
    _draw_header(screen, panel_x, panel_y, panel_w, meta)

    body_x = panel_x + 24
    body_y = panel_y + 86
    body_w = panel_w - 48
    body_h = panel_h - 132

    if tab_idx == 0:
        _draw_clone_log(screen, body_x, body_y, body_w, body_h,
                        meta=meta, stats=stats)
    elif tab_idx == 1:
        _draw_run_highlights(screen, body_x, body_y, body_w, body_h,
                             stats=stats, scroll=scroll)
    elif tab_idx == 2:
        _draw_vuln_db(screen, body_x, body_y, body_w, body_h,
                      vault=vault, scroll=scroll)
    else:
        _draw_lore(screen, body_x, body_y, body_w, body_h,
                   meta=meta, scroll=scroll)

    _draw_footer(screen, panel_x, panel_y + panel_h - 24, panel_w)


# ---------------------------------------------------------------------------
# Frame chrome
# ---------------------------------------------------------------------------

def _draw_folder_panel(surf, x, y, w, h, t):
    # Manila-paper card, slightly warm. Faint scuff lines so it feels handled.
    pygame.draw.rect(surf, (28, 24, 14), pygame.Rect(x - 4, y + 6, w + 8, h))
    pygame.draw.rect(surf, (210, 188, 132), pygame.Rect(x, y, w, h))
    pygame.draw.rect(surf, (130, 110, 60),  pygame.Rect(x, y, w, h), 1)
    # Top tab seam
    pygame.draw.line(surf, (130, 110, 60), (x, y + 36), (x + w, y + 36), 1)
    # Subtle brass corner brackets
    for cx, cy, sx, sy in (
        (x, y, 1, 1), (x + w, y, -1, 1),
        (x, y + h, 1, -1), (x + w, y + h, -1, -1),
    ):
        pygame.draw.line(surf, (160, 130, 70), (cx, cy), (cx + sx * 14, cy), 2)
        pygame.draw.line(surf, (160, 130, 70), (cx, cy), (cx, cy + sy * 14), 2)
    # Light hand-written stamp in the corner — gently breathing alpha
    breath = 0.5 + 0.5 * math.sin(t * 1.6)
    stamp = get_font(10, bold=True).render("PROPERTY OF B.A.X. // L-404",
                                           True, (140, 60, 50))
    stamp.set_alpha(int(150 + 60 * breath))
    surf.blit(stamp, (x + w - stamp.get_width() - 12, y + h - 16))


def _draw_tabs(surf, x, y, w, active_idx, t):
    fnt = get_font(11, bold=True)
    tab_w = (w - 16) // len(_TABS)
    for i, label in enumerate(_TABS):
        tx = x + 8 + i * tab_w
        ty = y - 18
        active = (i == active_idx)
        col_bg = (210, 188, 132) if active else (155, 135, 80)
        col_bd = (130, 110, 60)
        col_tx = (40, 30, 8)  if active else (90, 75, 40)
        rect = pygame.Rect(tx, ty, tab_w - 4, 26)
        pygame.draw.rect(surf, col_bg, rect)
        pygame.draw.rect(surf, col_bd, rect, 1)
        if active:
            pygame.draw.line(surf, col_bg,
                             (rect.left + 1, rect.bottom),
                             (rect.right - 2, rect.bottom), 2)
        ts = fnt.render(label, True, col_tx)
        surf.blit(ts, (rect.centerx - ts.get_width() // 2, rect.top + 6))


def _draw_header(surf, x, y, w, meta):
    title = get_font(15, bold=True).render(
        "BAX'S RECORDS", True, (60, 38, 12))
    surf.blit(title, (x + 18, y + 46))

    sub = get_font(10).render(
        f"Cross-referenced from clone-tank ledger, vault entries, and "
        f"corridor scraps. Clone #{getattr(meta, 'clone_count', 1)}.",
        True, (95, 70, 30))
    surf.blit(sub, (x + 18, y + 66))


def _draw_footer(surf, x, y, w):
    hint = get_font(10).render(
        "TAB / ←→ switch tab     ↑↓ / PGUP PGDN scroll     ESC back",
        True, (80, 60, 28))
    surf.blit(hint, (x + (w - hint.get_width()) // 2, y))


# ---------------------------------------------------------------------------
# Tab 1 — CLONE LOG
# ---------------------------------------------------------------------------

def _draw_clone_log(surf, x, y, w, h, *, meta, stats):
    fh   = get_font(12, bold=True)
    fb   = get_font(11)
    fsm  = get_font(10)
    cur_y = y

    surf.blit(fh.render("CLONE-TANK LEDGER", True, (60, 38, 12)),
              (x, cur_y))
    cur_y += 22

    runs_started   = 0
    runs_completed = 0
    debt_paid      = 0
    debt_accrued   = 0
    deep_per_chap  = {}
    if stats is not None and getattr(stats, "career", None):
        c = stats.career
        runs_started   = int(c.get("runs_started", 0))
        runs_completed = int(c.get("runs_completed", 0))
        debt_accrued   = int(c.get("total_debt_accrued", 0))
        debt_paid      = int(c.get("total_debt_paid", 0))
        deep_per_chap  = c.get("deepest_sector_per_chapter", {}) or {}

    deaths = max(0, runs_started - runs_completed)
    rows: list[tuple[str, str]] = [
        ("CLONE COUNT",         f"#{getattr(meta, 'clone_count', 1)}"),
        ("OUTSTANDING DEBT",    f"{getattr(meta, 'debt', 0):,} cr"),
        ("RUNS STARTED",        f"{runs_started:,}"),
        ("RUNS COMPLETED",      f"{runs_completed:,}"),
        ("DEATHS (estimated)",  f"{deaths:,}"),
        ("DEBT ACCRUED LIFETIME", f"{debt_accrued:,} cr"),
        ("DEBT PAID OFF",       f"{debt_paid:,} cr"),
    ]
    for k, v in rows:
        ks = fb.render(k, True, (75, 55, 22))
        vs = fb.render(v, True, (40, 28, 6))
        surf.blit(ks, (x + 4, cur_y))
        surf.blit(vs, (x + 280, cur_y))
        cur_y += 18

    cur_y += 8
    pygame.draw.line(surf, (130, 110, 60),
                     (x, cur_y), (x + w, cur_y), 1)
    cur_y += 10

    surf.blit(fh.render("DEEPEST SECTOR — PER CHAPTER", True, (60, 38, 12)),
              (x, cur_y))
    cur_y += 22
    chap_names = {
        1: "CH.1  ACOUSTIC ARCHIVE",
        2: "CH.2  MYCORRHIZAL PAYLOAD",
        3: "CH.3  THE PAPERWORK",
        4: "CH.4  SCHRÖDINGER VIP",
    }
    for ch, name in chap_names.items():
        depth = int(deep_per_chap.get(str(ch), 0))
        bar_w = 220
        fill_w = int(bar_w * (depth / S.SECTORS_PER_RUN)) if depth else 0
        pygame.draw.rect(surf, (160, 140, 90),
                         pygame.Rect(x + 280, cur_y + 4, bar_w, 8))
        pygame.draw.rect(surf, (130, 110, 60),
                         pygame.Rect(x + 280, cur_y + 4, bar_w, 8), 1)
        if fill_w > 0:
            pygame.draw.rect(surf, (180, 80, 40),
                             pygame.Rect(x + 280, cur_y + 4, fill_w, 8))
        ks = fb.render(name, True, (75, 55, 22))
        surf.blit(ks, (x + 4, cur_y))
        depth_lbl = "—" if depth == 0 else f"{depth} / {S.SECTORS_PER_RUN}"
        ds = fsm.render(depth_lbl, True, (40, 28, 6))
        surf.blit(ds, (x + 280 + bar_w + 8, cur_y + 1))
        cur_y += 18

    if cur_y < y + h - 28:
        cur_y = y + h - 28
    foot = fsm.render(
        "BAX: \"You've paid for your own body more times than I'd like to count, mate.\"",
        True, (110, 80, 30))
    surf.blit(foot, (x, cur_y))


# ---------------------------------------------------------------------------
# Tab 2 — RUN HIGHLIGHTS
# ---------------------------------------------------------------------------

def _draw_run_highlights(surf, x, y, w, h, *, stats, scroll):
    fh   = get_font(12, bold=True)
    fb   = get_font(11)
    fsm  = get_font(10)
    cur_y = y

    surf.blit(fh.render("RUN HIGHLIGHTS — CAREER LEDGER", True, (60, 38, 12)),
              (x, cur_y))
    cur_y += 22

    if stats is None:
        surf.blit(fb.render("No career data yet — finish a sector to file the first record.",
                            True, (95, 70, 30)),
                  (x, cur_y))
        return

    c = stats.career
    rows: list[tuple[str, str]] = [
        ("LIFETIME SLINGSHOTS",      f"{c.get('lifetime_slingshots', 0):,}"),
        ("LIFETIME TETHER SNAPS",    f"{c.get('lifetime_snaps', 0):,}"),
        ("LIFETIME KILLS",           f"{c.get('lifetime_kills', 0):,}"),
        ("BEST SINGLE-RUN CREDITS",  f"{c.get('best_single_run_credits', 0):,} cr"),
        ("BEST SLINGSHOT SPEED",     f"{c.get('best_slingshot_speed', 0)} px/s"),
        ("FASTEST SECTOR-1 CLEAR",   _fmt_seconds(c.get('fastest_sector_1_s', 0))),
        ("LONGEST NO-DAMAGE STREAK", _fmt_seconds(c.get('longest_no_damage_run_s', 0))),
    ]
    for k, v in rows:
        ks = fb.render(k, True, (75, 55, 22))
        vs = fb.render(v, True, (40, 28, 6))
        surf.blit(ks, (x + 4, cur_y))
        surf.blit(vs, (x + 320, cur_y))
        cur_y += 18

    cur_y += 8
    pygame.draw.line(surf, (130, 110, 60),
                     (x, cur_y), (x + w, cur_y), 1)
    cur_y += 10

    surf.blit(fh.render("THIS RUN", True, (60, 38, 12)),
              (x, cur_y))
    cur_y += 22
    r = stats.run
    rrows: list[tuple[str, str]] = [
        ("Slingshots",      f"{r.get('slingshots', 0)}"),
        ("Tether snaps",    f"{r.get('snaps', 0)}"),
        ("Kills",           f"{r.get('kills', 0)}"),
        ("Credits earned",  f"{r.get('credits_earned', 0):,} cr"),
        ("Debt added",      f"{r.get('debt_added', 0):,} cr"),
        ("Best slingshot",  f"{r.get('best_slingshot_speed', 0)} px/s"),
    ]
    for k, v in rrows:
        ks = fb.render(k, True, (90, 70, 30))
        vs = fb.render(v, True, (50, 36, 8))
        surf.blit(ks, (x + 4, cur_y))
        surf.blit(vs, (x + 320, cur_y))
        cur_y += 16


def _fmt_seconds(s) -> str:
    s = int(s or 0)
    if s <= 0:
        return "—"
    if s < 60:
        return f"{s}s"
    return f"{s // 60}m {s % 60:02d}s"


# ---------------------------------------------------------------------------
# Tab 3 — VULNERABILITY DATABASE
# ---------------------------------------------------------------------------

def _backdoors_for(vault, npc_key: str) -> list[str]:
    if vault is None or not hasattr(vault, "get_backdoors"):
        return []
    backdoors: list[str] = []
    seen: set[str] = set()
    try:
        for key in aliases_for_key(npc_key):
            for item in vault.get_backdoors(key):
                if item not in seen:
                    seen.add(item)
                    backdoors.append(item)
    except Exception:
        return []
    return backdoors


def _draw_vuln_db(surf, x, y, w, h, *, vault, scroll):
    fh   = get_font(12, bold=True)
    fb   = get_font(11)
    fsm  = get_font(10)

    surf.blit(fh.render("VULNERABILITY DATABASE — DISCOVERED EXPLOITS",
                        True, (60, 38, 12)),
              (x, y))

    legend = fsm.render(
        "★ filed in vault     ??? not yet discovered",
        True, (95, 70, 30))
    surf.blit(legend, (x + 4, y + 22))

    rows: list[tuple[str, list[str]]] = []
    for npc_key, label in _NPC_LABEL:
        rows.append((label, _backdoors_for(vault, npc_key)))

    line_h = 18
    visible = max(1, (h - 50) // line_h)
    scroll = max(0, min(scroll, max(0, len(rows) - visible)))

    cur_y = y + 44
    for label, backdoors in rows[scroll:scroll + visible]:
        col_label = (40, 28, 6) if backdoors else (130, 110, 70)
        ks = fb.render(label, True, col_label)
        surf.blit(ks, (x + 4, cur_y))

        if not backdoors:
            ms = fsm.render("???", True, (140, 110, 70))
            surf.blit(ms, (x + 200, cur_y + 1))
        else:
            entries = ", ".join(_format_backdoor(b) for b in backdoors[:5])
            if len(backdoors) > 5:
                entries += f"  (+{len(backdoors) - 5} more)"
            es = fsm.render(f"★ {entries}", True, (180, 70, 30))
            surf.blit(es, (x + 200, cur_y + 1))
        cur_y += line_h

    if len(rows) > visible:
        bar_x = x + w - 6
        bar_y = y + 44
        bar_h = visible * line_h
        pygame.draw.rect(surf, (160, 140, 90),
                         pygame.Rect(bar_x, bar_y, 4, bar_h))
        knob_h = max(20, int(bar_h * (visible / len(rows))))
        knob_y = bar_y + int((bar_h - knob_h) * (scroll / max(1, len(rows) - visible)))
        pygame.draw.rect(surf, (130, 60, 30),
                         pygame.Rect(bar_x, knob_y, 4, knob_h))


def _format_backdoor(name: str) -> str:
    return str(name).replace("_", " ").title()


# ---------------------------------------------------------------------------
# Tab 4 — LORE FRAGMENTS
# ---------------------------------------------------------------------------

def _draw_lore(surf, x, y, w, h, *, meta, scroll):
    fh   = get_font(12, bold=True)
    fb   = get_font(11)
    fsm  = get_font(10)

    fragments = list(getattr(meta, "lore_fragments", []) or [])
    surf.blit(fh.render(
        f"LORE FRAGMENTS  —  {len(fragments)} on file",
        True, (60, 38, 12)),
              (x, y))

    if not fragments:
        body = fsm.render(
            "Nothing filed yet. Off-path corridor secrets surface here.",
            True, (95, 70, 30))
        surf.blit(body, (x + 4, y + 28))
        return

    # Per-fragment card with chapter pill.
    cur_y = y + 28
    line_h = 14
    card_pad = 6

    cards: list[tuple[str, int, list[str]]] = []
    for entry in fragments:
        text = str(entry.get("text", ""))
        ch   = int(entry.get("chapter", 0) or 0)
        wrapped = _wrap_lines(text, fsm, w - 100)
        cards.append((text, ch, wrapped))

    # Compute card heights for scroll math.
    card_heights = [card_pad * 2 + line_h * max(1, len(c[2])) for c in cards]
    total_h = sum(card_heights) + (len(cards) - 1) * 4
    visible_h = h - 32
    max_scroll = max(0, total_h - visible_h)
    scroll_px = max(0, min(scroll * line_h, max_scroll))

    cur_y -= scroll_px
    clip = surf.get_clip()
    surf.set_clip(pygame.Rect(x, y + 28, w, visible_h))
    for (text, ch, wrapped), card_h in zip(cards, card_heights):
        if cur_y + card_h < y + 28:
            cur_y += card_h + 4
            continue
        if cur_y > y + 28 + visible_h:
            break
        rect = pygame.Rect(x, cur_y, w - 8, card_h)
        pygame.draw.rect(surf, (228, 210, 165), rect)
        pygame.draw.rect(surf, (140, 110, 60),  rect, 1)
        pill_label = f"CH.{ch}" if ch else "CORRIDOR"
        pill_col = {1: (180, 90, 30), 2: (40, 130, 90),
                    3: (130, 130, 60), 4: (170, 140, 40)}.get(ch, (90, 70, 30))
        ps = fsm.render(pill_label, True, pill_col)
        surf.blit(ps, (rect.left + 8, rect.top + card_pad))
        ty = rect.top + card_pad
        for line in wrapped:
            ts = fb.render(line, True, (40, 28, 6))
            surf.blit(ts, (rect.left + 80, ty))
            ty += line_h
        cur_y += card_h + 4
    surf.set_clip(clip)


def _wrap_lines(text: str, font: pygame.font.Font, max_w: int) -> list[str]:
    words = (text or "").split()
    if not words:
        return [""]
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = (current + " " + word).strip()
        if font.size(candidate)[0] <= max_w:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


# ---------------------------------------------------------------------------
# Public helper: how many scroll rows the current tab supports.
# Game uses this to clamp the scroll cursor before drawing.
# ---------------------------------------------------------------------------

def max_scroll(tab_idx: int, *, meta, vault, stats) -> int:
    if tab_idx == 2:
        return max(0, len(_NPC_LABEL) - 8)
    if tab_idx == 3:
        frags = list(getattr(meta, "lore_fragments", []) or [])
        return max(0, len(frags) * 4)
    return 0


def tab_count() -> int:
    return len(_TABS)
