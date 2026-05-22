"""
Procedural vector portraits for terminal NPCs.
All geometry uses pygame.draw — no sprites.
"""
from __future__ import annotations
import math
import random
import pygame
from config import settings as S

_NAME_TO_KEY = {
    "GARY":       "gary",
    "TK-9":       "synthetic_droid",
    "DISPATCHER": "union_dispatcher",
    "KRESS":      "kress",
    "MORWENNA":   "insurance_adjuster",
    "SANDRA":     "sandra",
    "KRELLBORN":  "pirate",
    "MARROW":     "underground_dj",
}


def draw_portrait(surface: pygame.Surface, npc_name: str,
                  rect: pygame.Rect, disposition: int = 0, t: float = 0.0):
    """
    Renders a CRT video-call portrait inside `rect`.

    Layers (back to front):
      1. CRT bezel hardware + signal strip
      2. Scene backdrop (environment behind the NPC)
      3. NPC vector portrait
      4. Disposition-driven glitch overlay
    """
    key   = _NAME_TO_KEY.get(npc_name.upper(), "unknown")
    inner = _draw_crt_bezel(surface, rect, npc_name, t, disposition)

    backdrop = _BACKDROPS.get(key)
    if backdrop is not None:
        prev_clip = surface.get_clip()
        surface.set_clip(inner)
        backdrop(surface, inner, t)
        surface.set_clip(prev_clip)

    fn    = _DISPATCH.get(key, _unknown)
    cx    = inner.centerx
    cy    = inner.top + int(inner.height * 0.46)
    scale = min(inner.width, inner.height * 0.65) / 200.0
    fn(surface, cx, cy, scale, disposition, t)

    _draw_signal_overlay(surface, inner, t, disposition)


# ---------------------------------------------------------------------------
# CRT bezel + signal overlay (universal hardware framing)
# ---------------------------------------------------------------------------

def _draw_crt_bezel(surface: pygame.Surface, rect: pygame.Rect,
                    npc_name: str, t: float, disposition: int) -> pygame.Rect:
    """Draws a chunky CRT bezel around `rect`, returns the inner usable area."""
    # Outer plastic frame
    pygame.draw.rect(surface, (12, 9, 4), rect)
    # Recessed bezel ring
    pygame.draw.rect(surface, (38, 26, 6), rect, 2)

    # Inner CRT face
    bezel = 6
    crt_outer = rect.inflate(-bezel*2, -bezel*2)
    pygame.draw.rect(surface, (2, 1, 0), crt_outer)
    pygame.draw.rect(surface, (140, 92, 0), crt_outer, 1)
    # Subtle curvature highlight
    pygame.draw.line(surface, (78, 52, 10),
                     (crt_outer.left+1, crt_outer.top+1),
                     (crt_outer.right-1, crt_outer.top+1), 1)

    # Corner screws — four of 'em, with a slot mark
    sc = (110, 84, 30)
    sd = (52, 38, 12)
    screw_pos = [(rect.left+5,  rect.top+5),
                 (rect.right-6, rect.top+5),
                 (rect.left+5,  rect.bottom-6),
                 (rect.right-6, rect.bottom-6)]
    for sx, sy in screw_pos:
        pygame.draw.circle(surface, sc, (sx, sy), 3)
        pygame.draw.circle(surface, sd, (sx, sy), 3, 1)
        pygame.draw.line(surface, sd, (sx-2, sy), (sx+2, sy), 1)

    # ── Top label strip — "LIVE COMM" + blinking record dot + callsign ──
    label_h = 14
    label_rect = pygame.Rect(crt_outer.left+1, crt_outer.top+1,
                             crt_outer.width-2, label_h)
    pygame.draw.rect(surface, (10, 7, 0), label_rect)
    pygame.draw.line(surface, (100, 64, 0),
                     (label_rect.left, label_rect.bottom),
                     (label_rect.right, label_rect.bottom), 1)
    font = pygame.font.SysFont("monospace", 8, bold=True)
    blink = (int(t * 2) % 2 == 0)
    dot_col = (230, 60, 30) if blink else (70, 20, 10)
    pygame.draw.circle(surface, dot_col,
                       (label_rect.left+8, label_rect.centery), 3)
    lbl = font.render("LIVE COMM // NOVA SOMA RELAY 7-B", True, (190, 130, 24))
    surface.blit(lbl, (label_rect.left+16,
                       label_rect.centery - lbl.get_height()//2))
    cs = font.render(npc_name.upper(), True, (255, 180, 44))
    surface.blit(cs, (label_rect.right - cs.get_width() - 6,
                      label_rect.centery - cs.get_height()//2))

    # ── Bottom hardware strip — signal bars + timecode ──
    bot_h = 12
    bot_rect = pygame.Rect(crt_outer.left+1, crt_outer.bottom - bot_h - 1,
                           crt_outer.width-2, bot_h)
    pygame.draw.rect(surface, (10, 7, 0), bot_rect)
    pygame.draw.line(surface, (100, 64, 0),
                     (bot_rect.left, bot_rect.top),
                     (bot_rect.right, bot_rect.top), 1)
    # Signal bars — degrade as disposition turns hostile
    if disposition >= 0:
        sig = 5
    elif disposition >= -3:
        sig = 4
    elif disposition >= -6:
        sig = 3
    else:
        sig = 1 + (int(t * 4) % 2)   # flickering between 1 and 2
    bw, bg = 4, 2
    sx0 = bot_rect.left + 8
    sy0 = bot_rect.centery
    for i in range(5):
        h = 3 + i * 2
        col = (40, 160, 40) if i < sig else (40, 30, 10)
        pygame.draw.rect(surface, col, (sx0 + i*(bw+bg), sy0 - h//2 + 1, bw, h))
    sig_lbl = font.render("SIG", True, (110, 74, 18))
    surface.blit(sig_lbl, (sx0 + 5*(bw+bg) + 4,
                           sy0 - sig_lbl.get_height()//2))
    tc = font.render(f"T+{int(t*10):05d}", True, (130, 92, 24))
    surface.blit(tc, (bot_rect.right - tc.get_width() - 6,
                      sy0 - tc.get_height()//2))

    return pygame.Rect(crt_outer.left+1, crt_outer.top + label_h + 3,
                       crt_outer.width-2,
                       crt_outer.height - label_h - bot_h - 6)


def _draw_signal_overlay(surface: pygame.Surface, inner: pygame.Rect,
                         t: float, disposition: int):
    """Disposition-tied glitch effect — clean when calm, broken when angry."""
    if disposition >= 0:
        return  # clean signal

    overlay = pygame.Surface((inner.w, inner.h), pygame.SRCALPHA)
    rng = random.Random(int(t * 6))

    if disposition <= -6:
        # Severe: rolling glitch bars + chromatic split
        for _ in range(3):
            sy = rng.randint(0, inner.h - 1)
            sh = rng.randint(2, 5)
            pygame.draw.rect(overlay, (255, 40, 40, 95),
                             (0, sy, inner.w, sh))
        # Static speckle
        for _ in range(40):
            spx = rng.randint(0, inner.w - 1)
            spy = rng.randint(0, inner.h - 1)
            pygame.draw.line(overlay, (180, 60, 60, 110),
                             (spx, spy), (spx+1, spy), 1)
    elif disposition <= -3:
        # Moderate: occasional horizontal interference
        for _ in range(2):
            sy = rng.randint(0, inner.h - 1)
            sh = rng.randint(1, 3)
            pygame.draw.rect(overlay, (220, 90, 50, 70),
                             (0, sy, inner.w, sh))
    else:
        # Mild
        sy = rng.randint(0, inner.h - 1)
        pygame.draw.rect(overlay, (200, 130, 60, 40),
                         (0, sy, inner.w, 1))

    surface.blit(overlay, inner.topleft)


# ---------------------------------------------------------------------------
# Shitty-3D wireframe helpers
# Orthographic (no perspective divide) = deliberate cheap aesthetic.

def _proj3(x: float, y: float, z: float,
           cx: int, cy: int, s: float, ry: float) -> tuple[int, int]:
    rx = x * math.cos(ry) - z * math.sin(ry)
    rz = x * math.sin(ry) + z * math.cos(ry)
    tilt = 0.18
    y2 = y * math.cos(tilt) - rz * math.sin(tilt)
    return int(cx + rx * s), int(cy + y2 * s)


def _wire_box(surface, cx, cy, s, t, hw, hh, hd, color, lw: int = 1):
    ry = t * 0.32 + 0.5
    rng = random.Random(int(t * 3))
    skip = set(rng.sample(range(12), 2)) if rng.random() < 0.06 else set()
    verts = [
        (-hw, -hh, -hd), ( hw, -hh, -hd), ( hw,  hh, -hd), (-hw,  hh, -hd),
        (-hw, -hh,  hd), ( hw, -hh,  hd), ( hw,  hh,  hd), (-hw,  hh,  hd),
    ]
    edges = [
        (0, 1), (1, 2), (2, 3), (3, 0),
        (4, 5), (5, 6), (6, 7), (7, 4),
        (0, 4), (1, 5), (2, 6), (3, 7),
    ]
    pts = [_proj3(*v, cx, cy, s, ry) for v in verts]
    for idx, (i, j) in enumerate(edges):
        if idx not in skip:
            pygame.draw.line(surface, color, pts[i], pts[j], lw)


def _wire_hex_prism(surface, cx, cy, s, t, r, hh, color, lw: int = 1):
    ry = t * 0.32 + 0.5
    rng = random.Random(int(t * 3))
    skip = set(rng.sample(range(6), 1)) if rng.random() < 0.06 else set()
    top = [(r * math.cos(math.pi / 3 * i), -hh, r * math.sin(math.pi / 3 * i))
           for i in range(6)]
    bot = [(r * math.cos(math.pi / 3 * i),  hh, r * math.sin(math.pi / 3 * i))
           for i in range(6)]
    tp = [_proj3(*v, cx, cy, s, ry) for v in top]
    bp = [_proj3(*v, cx, cy, s, ry) for v in bot]
    for i in range(6):
        n = (i + 1) % 6
        if i not in skip:
            pygame.draw.line(surface, color, tp[i], tp[n], lw)
            pygame.draw.line(surface, color, bp[i], bp[n], lw)
        pygame.draw.line(surface, color, tp[i], bp[i], lw)


# ---------------------------------------------------------------------------
# Gary — tired Local 404 field agent

def _gary(surface, cx, cy, s, disposition, t):
    amb = S.AMBER_TERM
    dim = (92, 66, 0)
    bg  = (22, 16, 0)

    _wire_box(surface, cx, int(cy - 8 * s), s, t, 68, 78, 46, (52, 37, 0), lw=1)

    # Head
    pygame.draw.ellipse(surface, bg,
        pygame.Rect(int(cx - 56 * s), int(cy - 68 * s), int(112 * s), int(128 * s)))
    pygame.draw.ellipse(surface, dim,
        pygame.Rect(int(cx - 56 * s), int(cy - 68 * s), int(112 * s), int(128 * s)), 2)

    # Under-eye shadow (heavier when hostile)
    shadow_alpha = max(0, 72 - disposition * 8)
    for gx in (-38, 8):
        pygame.draw.ellipse(surface, (shadow_alpha, int(shadow_alpha * 0.5), 0),
            pygame.Rect(int(cx + gx * s), int(cy - 22 * s), int(30 * s), int(10 * s)))

    # Eyes — wider when friendly, squint when hostile, narrowest when very hostile
    if disposition >= 4:
        eh = int(9 * s)
    elif disposition >= 0:
        eh = max(2, int((4 + disposition * 0.8) * s))
    else:
        eh = max(1, int((4 + disposition * 0.5) * s))

    for gx in (-38, 10):
        pygame.draw.ellipse(surface, amb,
            pygame.Rect(int(cx + gx * s), int(cy - 28 * s), int(26 * s), eh))

    # Pupils — shift slightly right when reading (friendly) vs glare
    pd = 2 if disposition > 0 else 0
    for gx in (-25, 23):
        pygame.draw.circle(surface, (0, 0, 0),
            (int(cx + gx * s + pd), int(cy - 26 * s)), max(2, int(4 * s)))

    # Nose bridge
    for dx, x2 in ((-4, -9), (4, 9)):
        pygame.draw.line(surface, dim,
            (int(cx + dx * s), int(cy - 4 * s)),
            (int(cx + x2 * s), int(cy + 12 * s)), 2)

    # Mouth
    mouth_y = int(cy + 28 * s)
    if disposition >= 3:
        pygame.draw.arc(surface, amb,
            pygame.Rect(int(cx - 22 * s), mouth_y - 10, int(44 * s), int(14 * s)),
            math.pi, 2 * math.pi, 2)
    elif disposition >= 0:
        pygame.draw.arc(surface, dim,
            pygame.Rect(int(cx - 20 * s), mouth_y, int(40 * s), int(8 * s)),
            0, math.pi, 2)
    else:
        # Deep frown
        pygame.draw.arc(surface, dim,
            pygame.Rect(int(cx - 22 * s), mouth_y + 2, int(44 * s), int(12 * s)),
            0, math.pi, 2)

    # Stubble
    rng = random.Random(42)
    for _ in range(22):
        sx = int(cx + rng.uniform(-46, 46) * s)
        sy = int(cy + rng.uniform(6, 46) * s)
        pygame.draw.circle(surface, (100, 72, 0), (sx, sy), max(1, int(1.5 * s)))

    # Collar
    pygame.draw.line(surface, dim,
        (int(cx - 34 * s), int(cy + 64 * s)),
        (int(cx - 10 * s), int(cy + 52 * s)), 2)
    pygame.draw.line(surface, dim,
        (int(cx + 34 * s), int(cy + 64 * s)),
        (int(cx + 10 * s), int(cy + 52 * s)), 2)

    # Union badge
    badge = pygame.Rect(int(cx - 18 * s), int(cy + 52 * s), int(16 * s), int(11 * s))
    pygame.draw.rect(surface, (18, 13, 0), badge)
    pygame.draw.rect(surface, amb, badge, 1)
    font = pygame.font.SysFont("monospace", max(7, int(7 * s)))
    surface.blit(font.render("404", True, amb), badge.topleft)


# ---------------------------------------------------------------------------
# TK-9 — compliance droid with loyalty subroutine

def _synthetic_droid(surface, cx, cy, s, disposition, t):
    # Eye color shifts dramatically with disposition
    if disposition >= 4:
        # Deep friendship mode — warm white/gold
        eye_col = (255, 240, 180)
        glitch_mode = True
    elif disposition >= 2:
        eye_col = (0, 220, 210)
        glitch_mode = False
    elif disposition >= 0:
        eye_col = S.AMBER_TERM
        glitch_mode = False
    elif disposition >= -3:
        eye_col = (200, 120, 0)
        glitch_mode = False
    else:
        eye_col = (220, 40, 40)
        glitch_mode = False

    bg   = (12, 18, 22)
    edge = (70, 90, 105)
    pan  = (36, 46, 56)

    _wire_hex_prism(surface, cx, int(cy - 8 * s), s, t, 70, 62, (0, 42, 40), lw=1)

    # Hexagonal head — glitch offset if hostile or friendship active
    glitch_x = 0
    if disposition <= -3 or glitch_mode:
        glitch_x = int(random.Random(int(t * 8)).uniform(-3, 3) * s)

    pts = [
        (int(cx - 46 * s + glitch_x), int(cy - 54 * s)),
        (int(cx + 46 * s + glitch_x), int(cy - 54 * s)),
        (int(cx + 62 * s), int(cy - 18 * s)),
        (int(cx + 62 * s), int(cy + 42 * s)),
        (int(cx - 62 * s), int(cy + 42 * s)),
        (int(cx - 62 * s), int(cy - 18 * s)),
    ]
    pygame.draw.polygon(surface, bg, pts)
    pygame.draw.polygon(surface, edge, pts, 2)

    # Extra glitch line on hostile
    if disposition <= -4:
        rng = random.Random(int(t * 5))
        for _ in range(3):
            gy = int(cy + rng.uniform(-30, 30) * s)
            pygame.draw.line(surface, (180, 20, 20),
                             (int(cx - 60 * s), gy), (int(cx + 60 * s), gy), 1)

    # Horizontal panel seams
    for dy in (-28, -2, 22):
        pygame.draw.line(surface, pan,
            (int(cx - 56 * s), int(cy + dy * s)),
            (int(cx + 56 * s), int(cy + dy * s)), 1)

    # LED eye bars
    ey = int(cy - 30 * s)
    eh = max(3, int(9 * s))
    pygame.draw.rect(surface, (0, 0, 0),
        pygame.Rect(int(cx - 50 * s), ey - 2, int(100 * s), eh + 4))

    # Eyes pulse faster in friendship mode
    pulse_speed = 4.0 if glitch_mode else 2.0
    pygame.draw.rect(surface, eye_col,
        pygame.Rect(int(cx - 48 * s), ey, int(38 * s), eh))
    pygame.draw.rect(surface, eye_col,
        pygame.Rect(int(cx + 10 * s), ey, int(38 * s), eh))

    ga = int(55 + 45 * math.sin(t * pulse_speed))
    gs = pygame.Surface((int(100 * s), eh + 10), pygame.SRCALPHA)
    pygame.draw.rect(gs, (*eye_col, ga), pygame.Rect(0, 0, int(100 * s), eh + 10))
    surface.blit(gs, (int(cx - 50 * s), ey - 5))

    # Mouth grille — in friendship mode, the slats angle up slightly (smile)
    for i in range(4):
        gy = int(cy + 10 * s + i * 5 * s)
        if glitch_mode:
            # Ascending slats = smile
            gx_off = int((i - 1.5) * 3 * s)
            pygame.draw.line(surface, (*eye_col, 180),
                (int(cx - 28 * s), gy - gx_off), (int(cx + 28 * s), gy - gx_off), 1)
        else:
            pygame.draw.line(surface, pan,
                (int(cx - 28 * s), gy), (int(cx + 28 * s), gy), 1)

    # Antenna
    pygame.draw.line(surface, edge,
        (int(cx + 22 * s), int(cy - 54 * s)),
        (int(cx + 34 * s), int(cy - 82 * s)), 2)
    ant_col = eye_col if glitch_mode else eye_col
    pygame.draw.circle(surface, ant_col,
        (int(cx + 34 * s), int(cy - 84 * s)), max(2, int(3 * s)))

    # Neck bolts
    for bx in (-44, 44):
        pygame.draw.circle(surface, edge,
            (int(cx + bx * s), int(cy + 44 * s)), max(3, int(5 * s)))
        pygame.draw.circle(surface, pan,
            (int(cx + bx * s), int(cy + 44 * s)), max(1, int(2 * s)))

    # "LOYALTY SUBROUTINE" label when in friendship mode
    if disposition >= 3:
        font = pygame.font.SysFont("monospace", max(8, int(8 * s)))
        pulse_a = int(180 + 75 * math.sin(t * 3.0))
        label_col = tuple(min(255, int(c * pulse_a / 255)) for c in eye_col)
        label = font.render("LOYALTY SUBROUTINE", True, label_col)
        surface.blit(label, (int(cx - label.get_width() // 2), int(cy + 56 * s)))


# ---------------------------------------------------------------------------
# Dispatcher — union bureaucrat drowning in paperwork

def _union_dispatcher(surface, cx, cy, s, disposition, t):
    amb = S.AMBER_TERM
    dim = (92, 66, 0)
    bg  = (22, 16, 0)

    _wire_box(surface, cx, int(cy - 8 * s), s, t, 74, 76, 50, (52, 37, 0), lw=1)

    # Head
    pygame.draw.ellipse(surface, bg,
        pygame.Rect(int(cx - 58 * s), int(cy - 64 * s), int(116 * s), int(114 * s)))
    pygame.draw.ellipse(surface, dim,
        pygame.Rect(int(cx - 58 * s), int(cy - 64 * s), int(116 * s), int(114 * s)), 2)

    # Glasses with slight tilt when stressed
    stress = max(0, -disposition) * 0.04
    for i, gx in enumerate((-22, 22)):
        tilt = (i * 2 - 1) * stress
        pygame.draw.circle(surface, dim,
            (int(cx + gx * s), int(cy - 18 * s + tilt * s * 10)), int(18 * s), 2)
        ls = pygame.Surface((int(36 * s), int(36 * s)), pygame.SRCALPHA)
        pygame.draw.circle(ls, (255, 176, 0, 18),
            (int(18 * s), int(18 * s)), int(18 * s))
        surface.blit(ls, (int(cx + gx * s - 18 * s), int(cy - 18 * s - 18 * s)))
    pygame.draw.line(surface, dim,
        (int(cx - 4 * s), int(cy - 18 * s)),
        (int(cx + 4 * s), int(cy - 18 * s)), 2)

    # Eyes — stressed/tired when hostile
    eye_h = max(3, int((7 - max(0, -disposition)) * s))
    for gx in (-22, 22):
        pygame.draw.ellipse(surface, amb,
            pygame.Rect(int(cx + gx * s - 8 * s), int(cy - 22 * s),
                        int(16 * s), eye_h))

    # Nose
    for dx, x2 in ((0, -6), (0, 6)):
        pygame.draw.line(surface, dim,
            (int(cx + dx * s), int(cy - 4 * s)),
            (int(cx + x2 * s), int(cy + 12 * s)), 2)

    # Mouth — flat line when neutral, slight downturn when overwhelmed
    mx = int(cy + 22 * s)
    if disposition >= 2:
        pygame.draw.arc(surface, dim,
            pygame.Rect(int(cx - 18 * s), mx - 6, int(36 * s), int(8 * s)),
            math.pi, 2 * math.pi, 2)
    elif disposition >= -2:
        pygame.draw.line(surface, dim,
            (int(cx - 18 * s), mx), (int(cx + 18 * s), mx), 2)
    else:
        # Overwhelmed frown
        pygame.draw.arc(surface, dim,
            pygame.Rect(int(cx - 18 * s), mx + 2, int(36 * s), int(10 * s)),
            0, math.pi, 2)

    # Floating papers when stress is high
    if disposition <= -2:
        rng = random.Random(int(t * 2))
        for _ in range(3):
            px = int(cx + rng.uniform(-70, 70) * s)
            py = int(cy + rng.uniform(-80, 20) * s)
            pw, ph = int(18 * s), int(12 * s)
            angle = rng.uniform(-0.4, 0.4)
            paper_pts = [
                (px + int((-pw // 2) * math.cos(angle) - (-ph // 2) * math.sin(angle)),
                 py + int((-pw // 2) * math.sin(angle) + (-ph // 2) * math.cos(angle))),
                (px + int((pw // 2) * math.cos(angle) - (-ph // 2) * math.sin(angle)),
                 py + int((pw // 2) * math.sin(angle) + (-ph // 2) * math.cos(angle))),
                (px + int((pw // 2) * math.cos(angle) - (ph // 2) * math.sin(angle)),
                 py + int((pw // 2) * math.sin(angle) + (ph // 2) * math.cos(angle))),
                (px + int((-pw // 2) * math.cos(angle) - (ph // 2) * math.sin(angle)),
                 py + int((-pw // 2) * math.sin(angle) + (ph // 2) * math.cos(angle))),
            ]
            pygame.draw.polygon(surface, (28, 20, 0), paper_pts)
            pygame.draw.polygon(surface, (60, 44, 0), paper_pts, 1)

    # Headset arc
    pygame.draw.arc(surface, dim,
        pygame.Rect(int(cx - 62 * s), int(cy - 80 * s), int(124 * s), int(52 * s)),
        0, math.pi, 3)
    pygame.draw.circle(surface, dim,
        (int(cx - 62 * s), int(cy - 54 * s)), max(4, int(8 * s)), 2)
    pygame.draw.line(surface, dim,
        (int(cx - 62 * s), int(cy - 46 * s)),
        (int(cx - 46 * s), int(cy - 8 * s)), 2)
    pygame.draw.circle(surface, amb,
        (int(cx - 46 * s), int(cy - 6 * s)), max(3, int(4 * s)))

    # Collar and tie
    pygame.draw.line(surface, dim,
        (int(cx - 36 * s), int(cy + 56 * s)),
        (int(cx - 9 * s),  int(cy + 44 * s)), 2)
    pygame.draw.line(surface, dim,
        (int(cx + 36 * s), int(cy + 56 * s)),
        (int(cx + 9 * s),  int(cy + 44 * s)), 2)
    tie = [
        (int(cx),           int(cy + 42 * s)),
        (int(cx - 8 * s),   int(cy + 52 * s)),
        (int(cx),           int(cy + 72 * s)),
        (int(cx + 8 * s),   int(cy + 52 * s)),
    ]
    pygame.draw.polygon(surface, (38, 28, 0), tie)
    pygame.draw.polygon(surface, dim, tie, 1)


# ---------------------------------------------------------------------------
# Kress — ex-asteroid miner, voice only, comm static aesthetic

def _kress(surface, cx, cy, s, disposition, t):
    # Static/noise field — it's a comm call, portrait is a signal waveform
    rng_static = random.Random(int(t * 12))

    # Background — dark with subtle green tinge
    bg_rect = pygame.Rect(int(cx - 90 * s), int(cy - 90 * s), int(180 * s), int(180 * s))

    # Static noise behind waveform
    for _ in range(60):
        sx = int(cx + rng_static.uniform(-88, 88) * s)
        sy = int(cy + rng_static.uniform(-88, 88) * s)
        alpha_val = rng_static.randint(20, 70)
        pygame.draw.circle(surface, (0, alpha_val, int(alpha_val * 0.4)), (sx, sy), 1)

    # "COMM LINK" label at top
    font = pygame.font.SysFont("monospace", max(9, int(10 * s)))
    lbl = font.render("COMM LINK · CHANNEL 7", True, (0, 120, 60))
    surface.blit(lbl, (int(cx - lbl.get_width() // 2), int(cy - 88 * s)))

    # Voice waveform — sinusoidal with noise
    wave_w = int(160 * s)
    wave_x0 = cx - wave_w // 2
    amp_base = max(4, int(28 * s))
    amp_mod  = 1.0 + 0.3 * abs(disposition) / 10.0
    pts = []
    steps = 80
    for i in range(steps + 1):
        x = wave_x0 + int(i * wave_w / steps)
        phase = t * 3.2 + i * 0.18
        noise = rng_static.uniform(-0.2, 0.2)
        y_off = int(amp_base * amp_mod * (math.sin(phase) + 0.4 * math.sin(phase * 2.3 + 1.1) + noise))
        pts.append((x, cy + y_off))

    if len(pts) > 1:
        wave_col = (0, 200, 120) if disposition >= 0 else (180, 100, 0)
        pygame.draw.lines(surface, wave_col, False, pts, 2)

    # Glow under waveform
    glow = pygame.Surface((wave_w + 10, int(amp_base * 2.5 * amp_mod) + 10), pygame.SRCALPHA)
    for i, pt in enumerate(pts):
        gx = pt[0] - wave_x0
        gy = pt[1] - cy + glow.get_height() // 2
        if 0 <= gx < glow.get_width() and 0 <= gy < glow.get_height():
            pygame.draw.circle(glow, (*wave_col, 30), (gx, gy), 3)
    surface.blit(glow, (wave_x0 - 5, cy - glow.get_height() // 2))

    # Horizontal scan bars (comm channel look)
    scan_y = int((t * 40) % (180 * s))
    for dy in range(0, int(180 * s), 24):
        line_y = int(cy - 90 * s) + (dy + scan_y) % int(180 * s)
        pygame.draw.line(surface, (0, 80, 40, 60), (int(cx - 88 * s), line_y), (int(cx + 88 * s), line_y), 1)

    # Signal strength meter (bottom)
    meter_y = int(cy + 62 * s)
    bars = 5
    active = max(1, min(bars, 2 + disposition // 2 + 3))
    for i in range(bars):
        bw = max(6, int(10 * s))
        bh = max(4, int((i + 1) * 6 * s))
        bx = int(cx - bars * (bw + 3) * 0.5 + i * (bw + 3))
        col = (0, 180, 90) if i < active else (30, 50, 35)
        pygame.draw.rect(surface, col, (bx, meter_y - bh, bw, bh))
        pygame.draw.rect(surface, (0, 80, 40), (bx, meter_y - bh, bw, bh), 1)

    sig = font.render("SIG", True, (0, 80, 50))
    surface.blit(sig, (int(cx - 88 * s), meter_y - sig.get_height()))

    # Kress "voice" label
    name_lbl = font.render("KRESS", True, (0, 160, 90))
    surface.blit(name_lbl, (int(cx - name_lbl.get_width() // 2), int(cy + 74 * s)))


# ---------------------------------------------------------------------------
def _unknown(surface, cx, cy, s, disposition, t):
    pygame.draw.circle(surface, (35, 35, 35), (int(cx), int(cy)), int(60 * s), 2)
    font = pygame.font.SysFont("monospace", max(12, int(38 * s)))
    surf = font.render("?", True, S.AMBER_TERM)
    surface.blit(surf, (int(cx - surf.get_width() // 2),
                        int(cy - surf.get_height() // 2)))


_DISPATCH = {
    "gary":               _gary,
    "synthetic_droid":    _synthetic_droid,
    "union_dispatcher":   _union_dispatcher,
    "kress":              _kress,
    "insurance_adjuster": None,   # set after definition below
    "sandra":             None,
    "pirate":             None,
    "underground_dj":     None,
    "unknown":            _unknown,
}


# ---------------------------------------------------------------------------
# Scene backdrops — one per NPC, drawn behind the bust
# ---------------------------------------------------------------------------

def _backdrop_gary(surface, inner, t):
    """Local 404 field barge cockpit — cramped, functional, overworked."""
    cx = inner.centerx
    font6  = pygame.font.SysFont("monospace", 6, bold=True)
    font7  = pygame.font.SysFont("monospace", 7)
    font8  = pygame.font.SysFont("monospace", 8, bold=True)

    # ── Back wall: horizontal hull-plate seams ──────────────────────────────
    for i in range(3):
        y = inner.top + 20 + i * 18
        pygame.draw.line(surface, (30, 20, 4), (inner.left, y), (inner.right, y), 1)

    # ── Viewport window (top-centre) — debris outside ──────────────────────
    vp = pygame.Rect(cx - 38, inner.top + 6, 76, 42)
    pygame.draw.rect(surface, (2, 6, 10), vp)
    pygame.draw.rect(surface, (70, 50, 12), vp, 2)
    # Window frame cross-bar
    pygame.draw.line(surface, (60, 42, 10), (vp.left, vp.centery), (vp.right, vp.centery), 1)
    pygame.draw.line(surface, (60, 42, 10), (vp.centerx, vp.top), (vp.centerx, vp.bottom), 1)
    # Stars / debris dots visible through window
    rng_vp = random.Random(17)
    for _ in range(12):
        sx = rng_vp.randint(vp.left + 3, vp.right - 3)
        sy = rng_vp.randint(vp.top + 3, vp.bottom - 3)
        pygame.draw.circle(surface, (80, 80, 100), (sx, sy), 1)
    # Floating debris rock silhouette
    drx, dry = cx - 12, inner.top + 18
    drock = [(drx, dry-4), (drx+6, dry-6), (drx+10, dry-2), (drx+8, dry+4),
             (drx+2, dry+5), (drx-2, dry+2)]
    pygame.draw.polygon(surface, (28, 22, 38), drock)
    pygame.draw.polygon(surface, (55, 45, 70), drock, 1)

    # ── Hazard stripe panels left and right of viewport ─────────────────────
    for side_x, w in ((inner.left, 34), (inner.right - 34, 34)):
        stripe_rect = pygame.Rect(side_x, inner.top + 6, w, 42)
        pygame.draw.rect(surface, (16, 12, 0), stripe_rect)
        pygame.draw.rect(surface, (50, 35, 0), stripe_rect, 1)
        # Diagonal hazard stripes
        for k in range(0, w + 42, 12):
            x1 = side_x + k
            y1 = inner.top + 6
            x2 = side_x + k - 42
            y2 = inner.top + 48
            pygame.draw.line(surface, (80, 55, 0),
                             (max(side_x, min(side_x+w, x1)), y1),
                             (max(side_x, min(side_x+w, x2)), y2), 2)

    # ── CAUTION blink lights — top-left / top-right ──────────────────────────
    pulse = 0.5 + 0.5 * math.sin(t * 3.0)
    blink_fast = (int(t * 2.4) % 2 == 0)
    caution_col = (int(200 * pulse), int(110 * pulse), 0) if blink_fast else (40, 22, 0)
    for lx in (inner.left + 10, inner.right - 10):
        pygame.draw.circle(surface, (30, 18, 0), (lx, inner.top + 11), 7)
        pygame.draw.circle(surface, caution_col, (lx, inner.top + 11), 5)
        pygame.draw.circle(surface, (60, 36, 0), (lx, inner.top + 11), 7, 1)
    # CAUTION label between the lights
    caut = font6.render("!! CAUTION !!", True, (int(160*pulse), int(80*pulse), 0))
    surface.blit(caut, (cx - caut.get_width()//2, inner.top + 7))

    # ── Side wall ribs ────────────────────────────────────────────────────────
    for side, xs in (("left", range(4)), ("right", range(4))):
        for i in xs:
            if side == "left":
                x = inner.left + 4 + i * 7
            else:
                x = inner.right - 4 - i * 7
            pygame.draw.line(surface, (28, 18, 4), (x, inner.top + 54),
                             (x, inner.bottom - 32), 1)

    # ── Three monitor screens — STATUS, MANIFEST, COMMS ─────────────────────
    screen_defs = [
        (inner.left + 6,  inner.top + 55, 50, 30, "STATUS"),
        (cx - 28,         inner.top + 55, 56, 30, "MANIFEST"),
        (inner.right - 56, inner.top + 55, 50, 30, "COMMS"),
    ]
    mon_blink_frame = int(t * 4)
    for mx, my, mw, mh, label in screen_defs:
        pygame.draw.rect(surface, (6, 8, 2), (mx, my, mw, mh))
        pygame.draw.rect(surface, (80, 60, 10), (mx, my, mw, mh), 1)
        # Scanline
        for sl in range(my + 3, my + mh - 2, 3):
            pygame.draw.line(surface, (8, 10, 2), (mx+1, sl), (mx+mw-2, sl), 1)
        # Label top strip
        pygame.draw.rect(surface, (20, 15, 0), (mx, my, mw, 8))
        lbl = font6.render(label, True, (140, 100, 20))
        surface.blit(lbl, (mx + mw//2 - lbl.get_width()//2, my + 1))
        # Scrolling data lines — offsets by time
        for row in range(3):
            scroll_idx = (mon_blink_frame + row * 3 + hash(label) % 7) % 8
            line_col = (60, 180, 60) if scroll_idx < 6 else (180, 60, 20)
            blen = int(mw * 0.3 + (scroll_idx / 8.0) * mw * 0.55)
            pygame.draw.rect(surface, line_col,
                             (mx + 3, my + 10 + row * 6, blen, 3))
    # STATUS screen has a blinking "ONLINE" indicator
    st_mx, st_my = screen_defs[0][0], screen_defs[0][1]
    stat_blink = (int(t * 1.8) % 2 == 0)
    sc2 = (0, 220, 80) if stat_blink else (0, 60, 20)
    pygame.draw.circle(surface, sc2, (st_mx + 44, st_my + 25), 3)

    # ── Union logo panel — right wall ─────────────────────────────────────────
    logo_rect = pygame.Rect(inner.right - 30, inner.top + 55, 22, 30)
    pygame.draw.rect(surface, (12, 8, 0), logo_rect)
    pygame.draw.rect(surface, (100, 68, 0), logo_rect, 1)
    lbl404 = font8.render("404", True, (220, 160, 30))
    surface.blit(lbl404, (logo_rect.centerx - lbl404.get_width()//2, logo_rect.top + 3))
    union_lbl = font6.render("LOCAL", True, (110, 80, 15))
    surface.blit(union_lbl, (logo_rect.centerx - union_lbl.get_width()//2, logo_rect.top + 14))
    union_lbl2 = font6.render("UNION", True, (110, 80, 15))
    surface.blit(union_lbl2, (logo_rect.centerx - union_lbl2.get_width()//2, logo_rect.top + 21))

    # ── Coffee mug outline on console ─────────────────────────────────────────
    mug_x, mug_y = inner.left + 9, inner.bottom - 34
    pygame.draw.rect(surface, (28, 18, 6), (mug_x, mug_y, 10, 12))
    pygame.draw.rect(surface, (70, 50, 15), (mug_x, mug_y, 10, 12), 1)
    pygame.draw.arc(surface, (70, 50, 15),
                    pygame.Rect(mug_x + 9, mug_y + 3, 5, 6), -math.pi/2, math.pi/2, 1)
    # Steam wisps
    for si in range(2):
        steam_x = mug_x + 3 + si * 4
        steam_y = mug_y - 4 - int(3 * math.sin(t * 2.0 + si * 1.5))
        pygame.draw.circle(surface, (50, 45, 40), (steam_x, steam_y), 1)

    # ── Maintenance manuals stacked left side ─────────────────────────────────
    book_defs = [(inner.left + 4, inner.bottom - 28, 14, 8, (80, 28, 14)),
                 (inner.left + 4, inner.bottom - 20, 16, 8, (30, 60, 20)),
                 (inner.left + 4, inner.bottom - 12, 18, 8, (14, 30, 80))]
    for bx2, by2, bw2, bh2, bc in book_defs:
        pygame.draw.rect(surface, bc, (bx2, by2, bw2, bh2))
        pygame.draw.rect(surface, (100, 80, 40), (bx2, by2, bw2, bh2), 1)

    # ── Radio handset outline ─────────────────────────────────────────────────
    rx, ry = cx + 40, inner.bottom - 26
    pygame.draw.rect(surface, (20, 14, 4), (rx, ry, 7, 16))
    pygame.draw.rect(surface, (80, 55, 10), (rx, ry, 7, 16), 1)
    pygame.draw.circle(surface, (60, 42, 8), (rx + 3, ry + 3), 2)
    pygame.draw.circle(surface, (60, 42, 8), (rx + 3, ry + 12), 2)
    # Coiled cord
    pygame.draw.arc(surface, (60, 42, 8),
                    pygame.Rect(rx + 6, ry + 6, 6, 4), -math.pi/2, math.pi/2, 1)

    # ── Main control panel at the bottom ─────────────────────────────────────
    panel = pygame.Rect(inner.left + 4, inner.bottom - 32, inner.width - 8, 24)
    pygame.draw.rect(surface, (14, 10, 0), panel)
    pygame.draw.line(surface, (60, 40, 8), (panel.left, panel.top), (panel.right, panel.top), 2)
    # Toggle switches
    for i in range(10):
        bx3 = panel.left + 8 + i * 18
        lit = (int(t * 0.6) + i * 3) % 9 == 0
        col2 = (200, 120, 0) if lit else (40, 26, 4)
        pygame.draw.rect(surface, col2, (bx3, panel.top + 6, 6, 4))
        pygame.draw.rect(surface, (60, 42, 8), (bx3, panel.top + 6, 6, 4), 1)
    # BARGE STATUS readout on panel
    stat_col = (0, 180, 80) if (int(t * 0.5) % 2 == 0) else (0, 80, 30)
    stat_txt = font7.render("BARGE STATUS: NOMINAL", True, stat_col)
    surface.blit(stat_txt, (panel.left + 4, panel.top + 13))


def _backdrop_synthetic_droid(surface, inner, t):
    """Nova Soma sterile processing room — white-green clinical tech horror."""
    cx = inner.centerx
    font6 = pygame.font.SysFont("monospace", 6, bold=True)
    font7 = pygame.font.SysFont("monospace", 7)

    # ── Grid floor — perspective lines converging at cx, bottom ──────────────
    floor_y = inner.bottom - 12
    vp_x    = cx
    for gx in range(inner.left, inner.right + 1, 18):
        pygame.draw.line(surface, (10, 22, 10),
                         (gx, floor_y), (vp_x, inner.top + inner.height // 2), 1)
    for gy_frac in (0.55, 0.70, 0.82, 0.92, 1.0):
        gy = inner.top + int(inner.height * gy_frac) - 12
        if inner.top <= gy <= floor_y:
            pygame.draw.line(surface, (10, 22, 10),
                             (inner.left, gy), (inner.right, gy), 1)

    # ── Grid ceiling ─────────────────────────────────────────────────────────
    ceil_y = inner.top + 12
    for gx in range(inner.left, inner.right + 1, 18):
        pygame.draw.line(surface, (8, 18, 8),
                         (gx, ceil_y), (vp_x, inner.top + inner.height // 2), 1)
    for gy_frac in (0.0, 0.06, 0.12, 0.18):
        gy = inner.top + int(inner.height * gy_frac) + 4
        if inner.top <= gy <= ceil_y + 20:
            pygame.draw.line(surface, (8, 18, 8),
                             (inner.left, gy), (inner.right, gy), 1)

    # ── Server rack towers on left and right ──────────────────────────────────
    rack_specs = [
        (inner.left + 2, inner.top + 14, 26, inner.height - 28),
        (inner.left + 30, inner.top + 20, 18, inner.height - 36),
        (inner.right - 28, inner.top + 14, 26, inner.height - 28),
        (inner.right - 48, inner.top + 20, 18, inner.height - 36),
    ]
    for rx, ry, rw, rh in rack_specs:
        pygame.draw.rect(surface, (6, 14, 8), (rx, ry, rw, rh))
        pygame.draw.rect(surface, (20, 50, 25), (rx, ry, rw, rh), 1)
        # Rack unit lines
        for unit in range(0, rh, 6):
            pygame.draw.line(surface, (12, 28, 14),
                             (rx + 1, ry + unit), (rx + rw - 2, ry + unit), 1)
        # LED indicators — scrolling pattern
        for row in range(0, rh - 4, 6):
            phase = (row // 6 + int(t * 5) + rx) % 7
            led_col = (0, 220, 80) if phase < 5 else (180, 30, 30)
            if phase == 6:
                led_col = (220, 180, 0)
            pygame.draw.rect(surface, led_col, (rx + rw - 5, ry + row + 1, 3, 3))

    # ── Cable conduits running walls ──────────────────────────────────────────
    for cy_off in (0.22, 0.42, 0.62):
        cy2 = inner.top + int(inner.height * cy_off)
        pygame.draw.line(surface, (12, 28, 14),
                         (inner.left + 28, cy2), (inner.right - 28, cy2), 3)
        pygame.draw.line(surface, (0, 50, 20),
                         (inner.left + 28, cy2), (inner.right - 28, cy2), 1)
        # Conduit connectors
        for cx3 in (inner.left + 42, cx, inner.right - 42):
            pygame.draw.circle(surface, (20, 60, 30), (cx3, cy2), 3)
            pygame.draw.circle(surface, (0, 100, 50), (cx3, cy2), 3, 1)

    # ── Overhead cable tray ───────────────────────────────────────────────────
    tray_y = inner.top + 10
    pygame.draw.rect(surface, (8, 20, 10),
                     (inner.left + 4, tray_y, inner.width - 8, 4))
    pygame.draw.rect(surface, (30, 60, 35),
                     (inner.left + 4, tray_y, inner.width - 8, 4), 1)
    for hx in range(inner.left + 14, inner.right - 4, 10):
        pygame.draw.line(surface, (15, 36, 18),
                         (hx, tray_y + 4), (hx + 4, tray_y + 12), 1)

    # ── Nova Soma logo — abstract diamond geometry centre wall ────────────────
    logo_cx = cx
    logo_cy = inner.top + int(inner.height * 0.38)
    logo_r  = 14
    # Outer diamond
    ns_pts = [(logo_cx, logo_cy - logo_r), (logo_cx + logo_r, logo_cy),
              (logo_cx, logo_cy + logo_r), (logo_cx - logo_r, logo_cy)]
    pygame.draw.polygon(surface, (4, 18, 8), ns_pts)
    pygame.draw.polygon(surface, (0, 200, 80), ns_pts, 1)
    # Inner cross
    inner_r = logo_r // 2
    ns_inner = [(logo_cx, logo_cy - inner_r), (logo_cx + inner_r, logo_cy),
                (logo_cx, logo_cy + inner_r), (logo_cx - inner_r, logo_cy)]
    pygame.draw.polygon(surface, (0, 140, 55), ns_inner, 1)
    # Centre pulse
    pulse_a = 0.5 + 0.5 * math.sin(t * 3.0)
    pygame.draw.circle(surface, (0, int(220 * pulse_a), int(80 * pulse_a)),
                       (logo_cx, logo_cy), 3)
    ns_lbl = font6.render("NOVA SOMA", True, (0, 140, 55))
    surface.blit(ns_lbl, (logo_cx - ns_lbl.get_width()//2, logo_cy + logo_r + 3))

    # ── Status monitor array — top-centre ─────────────────────────────────────
    mon_x = cx - 34
    mon_y = inner.top + 15
    for mi in range(3):
        msx = mon_x + mi * 24
        pygame.draw.rect(surface, (2, 10, 4), (msx, mon_y, 20, 14))
        pygame.draw.rect(surface, (20, 60, 25), (msx, mon_y, 20, 14), 1)
        # Scrolling green bar
        bar_w = int(4 + 12 * ((math.sin(t * 2.5 + mi * 1.1) * 0.5 + 0.5)))
        pygame.draw.rect(surface, (0, 180, 60), (msx + 2, mon_y + 4, bar_w, 4))
        blink2 = (int(t * 3 + mi) % 4 == 0)
        led2 = (0, 220, 80) if blink2 else (0, 50, 18)
        pygame.draw.circle(surface, led2, (msx + 17, mon_y + 2), 2)

    # ── Analysis / dissection table in lower-centre ───────────────────────────
    tbl_rect = pygame.Rect(cx - 32, inner.bottom - 20, 64, 10)
    pygame.draw.rect(surface, (8, 20, 10), tbl_rect)
    pygame.draw.rect(surface, (0, 120, 50), tbl_rect, 1)
    # Table legs
    for lx in (tbl_rect.left + 6, tbl_rect.right - 6):
        pygame.draw.line(surface, (0, 80, 35),
                         (lx, tbl_rect.bottom), (lx, tbl_rect.bottom + 4), 1)
    # Object on table — abstract specimen container
    pygame.draw.rect(surface, (4, 28, 14),
                     (cx - 10, inner.bottom - 25, 20, 8))
    pygame.draw.rect(surface, (0, 160, 70),
                     (cx - 10, inner.bottom - 25, 20, 8), 1)
    # Status: ANALYZING blink
    an_col = (0, 200, 80) if (int(t * 2) % 2 == 0) else (0, 60, 24)
    an_lbl = font6.render("ANALYZING", True, an_col)
    surface.blit(an_lbl, (cx - an_lbl.get_width()//2, inner.bottom - 31))

    # ── Cooling vents bottom ──────────────────────────────────────────────────
    for vx in range(inner.left + 4, inner.right - 4, 14):
        pygame.draw.rect(surface, (8, 18, 10),
                         (vx, inner.bottom - 10, 10, 6))
        pygame.draw.rect(surface, (20, 45, 22),
                         (vx, inner.bottom - 10, 10, 6), 1)
        for vy in range(inner.bottom - 9, inner.bottom - 4, 2):
            pygame.draw.line(surface, (12, 30, 14),
                             (vx + 1, vy), (vx + 9, vy), 1)


def _backdrop_union_dispatcher(surface, inner, t):
    # Paper-flooded office: stacked forms + fluorescent flicker + in-tray
    # Fluorescent flicker — slight vignette pulse at top
    flick = 0.85 + 0.15 * (math.sin(t * 6.5) > 0.6)
    glow = pygame.Surface((inner.w, 28), pygame.SRCALPHA)
    pygame.draw.rect(glow, (220, 215, 130, int(38 * flick)),
                     (0, 0, inner.w, 28))
    surface.blit(glow, (inner.left, inner.top))

    # Stacks of paper on left wall
    pstack_x = inner.left + 8
    for i in range(7):
        y = inner.bottom - 22 - i * 5
        off = ((i * 7) % 5) - 2
        pygame.draw.rect(surface, (60, 56, 28),
                         (pstack_x + off, y, 26, 4))
        pygame.draw.rect(surface, (110, 100, 50),
                         (pstack_x + off, y, 26, 4), 1)
    # Stacks on right
    pstack_x = inner.right - 34
    for i in range(9):
        y = inner.bottom - 22 - i * 4
        off = ((i * 11) % 6) - 3
        pygame.draw.rect(surface, (60, 56, 28),
                         (pstack_x + off, y, 26, 3))
        pygame.draw.rect(surface, (110, 100, 50),
                         (pstack_x + off, y, 26, 3), 1)
    # IN-TRAY label
    font = pygame.font.SysFont("monospace", 7, bold=True)
    tag = font.render("47 FORMS BEHIND", True, (180, 50, 50))
    surface.blit(tag, (inner.left + 6, inner.top + 4))


def _backdrop_kress(surface, inner, t):
    # Back-alley dock: corrugated metal + neon sign flicker + faint fog
    # Corrugated wall — vertical zigzag stripes
    for i in range(0, inner.width, 8):
        x = inner.left + i
        col = (28, 26, 32) if (i // 8) % 2 == 0 else (18, 18, 24)
        pygame.draw.line(surface, col,
                         (x, inner.top + 28), (x, inner.bottom - 8), 1)
    # Neon sign — random flicker
    flicker = (int(t * 12) % 11) != 0   # mostly on
    sign = pygame.Rect(inner.right - 60, inner.top + 22, 50, 14)
    pygame.draw.rect(surface, (10, 8, 16), sign)
    pygame.draw.rect(surface, (180, 0, 220) if flicker else (40, 0, 60),
                     sign, 1)
    font = pygame.font.SysFont("monospace", 7, bold=True)
    nf = font.render("DOCK-7", True, (220, 60, 220) if flicker else (60, 20, 50))
    surface.blit(nf, (sign.centerx - nf.get_width()//2,
                      sign.centery - nf.get_height()//2))
    # Fog wisps at bottom
    for k in range(3):
        fy = inner.bottom - 14 + k * 3
        for fx in range(inner.left + 4, inner.right - 4, 6):
            wob = int(2 * math.sin(t * 0.8 + fx * 0.1 + k))
            pygame.draw.line(surface, (40, 40, 48),
                             (fx, fy + wob), (fx + 4, fy + wob), 1)


def _backdrop_insurance_adjuster(surface, inner, t):
    # Corporate office: Nova Soma logo + ceiling tile grid + corner plant
    # Ceiling tile grid (top portion)
    for x in range(inner.left + 4, inner.right - 4, 22):
        pygame.draw.line(surface, (20, 22, 24),
                         (x, inner.top + 4), (x, inner.top + 32), 1)
    for y in range(inner.top + 4, inner.top + 32, 16):
        pygame.draw.line(surface, (20, 22, 24),
                         (inner.left + 4, y), (inner.right - 4, y), 1)
    # Nova Soma logo on the back wall
    cx = inner.centerx
    logo_y = inner.top + 38
    pygame.draw.rect(surface, (12, 8, 0), (cx - 36, logo_y, 72, 18))
    pygame.draw.rect(surface, (110, 84, 18), (cx - 36, logo_y, 72, 18), 1)
    font = pygame.font.SysFont("monospace", 8, bold=True)
    logo = font.render("NOVA SOMA", True, (220, 160, 30))
    surface.blit(logo, (cx - logo.get_width()//2,
                        logo_y + 9 - logo.get_height()//2))
    # Potted plant in corner — sad, drooping
    px, py = inner.right - 24, inner.bottom - 28
    pot = pygame.Rect(px - 8, py + 8, 16, 10)
    pygame.draw.rect(surface, (60, 30, 8), pot)
    pygame.draw.rect(surface, (30, 14, 0), pot, 1)
    # Drooping leaves
    pygame.draw.line(surface, (40, 80, 30), (px - 4, py + 8), (px - 12, py + 16), 2)
    pygame.draw.line(surface, (40, 80, 30), (px + 4, py + 8), (px + 12, py + 16), 2)
    pygame.draw.line(surface, (50, 90, 40), (px, py + 8), (px, py + 2), 2)


def _backdrop_sandra(surface, inner, t):
    # Dispatch center: multiple screens + Vega Curve quota chart
    # Three small screens at the top
    for i in range(3):
        sw, sh = 36, 22
        sx = inner.left + 10 + i * (sw + 6)
        sy = inner.top + 6
        pygame.draw.rect(surface, (4, 18, 4), (sx, sy, sw, sh))
        pygame.draw.rect(surface, (40, 130, 50), (sx, sy, sw, sh), 1)
        # Route map: small connected nodes
        nodes = [(sx + 6, sy + 6 + i * 2),
                 (sx + 18, sy + 14),
                 (sx + 28, sy + 8 + i)]
        pygame.draw.lines(surface, (60, 180, 80), False, nodes, 1)
        for n in nodes:
            pygame.draw.circle(surface, (120, 220, 130), n, 1)
    # Accolade plaque
    plaque = pygame.Rect(inner.right - 70, inner.top + 38, 62, 20)
    pygame.draw.rect(surface, (60, 50, 12), plaque)
    pygame.draw.rect(surface, (200, 160, 40), plaque, 1)
    font = pygame.font.SysFont("monospace", 6, bold=True)
    p1 = font.render("VEGA CURVE", True, (240, 200, 80))
    surface.blit(p1, (plaque.centerx - p1.get_width()//2, plaque.top + 4))
    p2 = font.render("BASELINE: 312", True, (220, 180, 60))
    surface.blit(p2, (plaque.centerx - p2.get_width()//2, plaque.top + 11))
    # Quota chart — ascending bar pattern on the lower wall
    chart_y0 = inner.bottom - 12
    bar_x = inner.left + 8
    for i in range(11):
        h = 4 + i * 1
        col = (40, 150, 60) if i < 9 else (240, 180, 50)
        pygame.draw.rect(surface, col, (bar_x + i * 5, chart_y0 - h, 3, h))


def _backdrop_pirate(surface, inner, t):
    # Pirate ship interior: exposed wiring + scavenged panels + defaced flag
    # Exposed wiring — sagging cables across the back
    for i in range(3):
        y0 = inner.top + 14 + i * 8
        ax = inner.left + 6
        bx = inner.right - 6
        col = (140, 60, 0) if i == 0 else (60, 80, 90) if i == 1 else (20, 30, 30)
        sag = 6
        mid = ((ax + bx) // 2, y0 + sag)
        pygame.draw.lines(surface, col, False, [(ax, y0), mid, (bx, y0)], 2)
    # Scavenged metal panels — irregular plates riveted on
    plates = [
        (inner.left + 6,  inner.top + 40, 38, 24),
        (inner.left + 46, inner.top + 56, 28, 18),
        (inner.right - 42, inner.top + 42, 30, 22),
        (inner.right - 64, inner.bottom - 24, 24, 14),
    ]
    for px, py, pw, ph in plates:
        pygame.draw.rect(surface, (38, 38, 44), (px, py, pw, ph))
        pygame.draw.rect(surface, (90, 70, 50), (px, py, pw, ph), 1)
        # Rivets
        for rx in (px+3, px+pw-4):
            for ry in (py+3, py+ph-4):
                pygame.draw.circle(surface, (140, 110, 60), (rx, ry), 1)
    # Defaced Union flag — black bar through the 404 emblem
    flag = pygame.Rect(inner.left + 8, inner.bottom - 30, 26, 18)
    pygame.draw.rect(surface, (16, 8, 0), flag)
    pygame.draw.rect(surface, (100, 60, 0), flag, 1)
    font = pygame.font.SysFont("monospace", 6, bold=True)
    ff = font.render("404", True, (160, 120, 30))
    surface.blit(ff, (flag.centerx - ff.get_width()//2, flag.centery - ff.get_height()//2))
    # X through it
    pygame.draw.line(surface, (230, 30, 30),
                     (flag.left, flag.top), (flag.right, flag.bottom), 2)
    pygame.draw.line(surface, (230, 30, 30),
                     (flag.left, flag.bottom), (flag.right, flag.top), 2)


def _backdrop_underground_dj(surface, inner, t):
    # Radio studio: turntables + ON-AIR sign + soundwave
    # ON AIR sign — chunky red glow
    sign = pygame.Rect(inner.left + 8, inner.top + 6, 56, 16)
    glow_pulse = 0.6 + 0.4 * math.sin(t * 2.0)
    pygame.draw.rect(surface, (12, 0, 0), sign)
    pygame.draw.rect(surface,
                     (int(220 * glow_pulse + 35), 30, 30), sign, 1)
    font = pygame.font.SysFont("monospace", 9, bold=True)
    oa = font.render("ON AIR", True, (255, 60, 40))
    surface.blit(oa, (sign.centerx - oa.get_width()//2,
                      sign.centery - oa.get_height()//2))
    # Soundwave visualization across the middle
    wave_y = inner.top + 36
    last_pt = None
    for x in range(inner.left + 6, inner.right - 6, 3):
        amp = 4 + 3 * math.sin(t * 6.0 + x * 0.2) + 2 * math.sin(t * 11.0 + x * 0.07)
        pt = (x, wave_y + int(amp))
        if last_pt is not None:
            pygame.draw.line(surface, (40, 200, 230), last_pt, pt, 1)
        last_pt = pt
    # Two turntables at the bottom (just the discs)
    for cx_off in (inner.left + 26, inner.right - 26):
        cy = inner.bottom - 22
        pygame.draw.circle(surface, (16, 16, 20), (cx_off, cy), 14)
        pygame.draw.circle(surface, (80, 80, 90), (cx_off, cy), 14, 1)
        # Grooves
        for gr in (4, 7, 10, 13):
            pygame.draw.circle(surface, (32, 32, 38), (cx_off, cy), gr, 1)
        # Centre label
        pygame.draw.circle(surface, (200, 100, 30), (cx_off, cy), 3)
        # Stylus arm
        ax = cx_off + 10
        ay = cy - 10
        pygame.draw.line(surface, (140, 140, 150),
                         (ax, ay), (cx_off + 3, cy - 1), 1)
        pygame.draw.circle(surface, (190, 50, 50), (cx_off + 3, cy - 1), 1)


_BACKDROPS = {
    "gary":               _backdrop_gary,
    "synthetic_droid":    _backdrop_synthetic_droid,
    "union_dispatcher":   _backdrop_union_dispatcher,
    "kress":              _backdrop_kress,
    "insurance_adjuster": _backdrop_insurance_adjuster,
    "sandra":             _backdrop_sandra,
    "pirate":             _backdrop_pirate,
    "underground_dj":     _backdrop_underground_dj,
}


# ---------------------------------------------------------------------------
# New portrait functions for the four NPCs that don't have one yet
# ---------------------------------------------------------------------------

def _insurance_adjuster(surface, cx, cy, s, disposition, t):
    """
    Morwenna — Nova Soma claims adjuster. Pinned-back hair, blazer,
    permanent thin-lipped smile that's actually annoyance.
    """
    # Color palette — corporate amber
    amb = (240, 195, 70)
    dim = (110, 78, 16)
    skin_l = (220, 180, 130)
    skin_d = (100, 70, 40)
    suit = (60, 50, 80)
    hair = (60, 40, 20)

    # Hair silhouette behind head — bun
    pygame.draw.circle(surface, hair, (int(cx + 26 * s), int(cy - 18 * s)), int(12 * s))
    pygame.draw.circle(surface, (28, 18, 6), (int(cx + 26 * s), int(cy - 18 * s)), int(12 * s), 1)

    # Neck
    neck = [(int(cx - 14 * s), int(cy + 26 * s)),
            (int(cx + 14 * s), int(cy + 26 * s)),
            (int(cx + 16 * s), int(cy + 46 * s)),
            (int(cx - 16 * s), int(cy + 46 * s))]
    pygame.draw.polygon(surface, skin_d, neck)
    pygame.draw.polygon(surface, dim, neck, 1)

    # Head
    head_pts = [
        (int(cx - 36 * s), int(cy - 12 * s)),
        (int(cx - 30 * s), int(cy - 30 * s)),
        (int(cx - 10 * s), int(cy - 38 * s)),
        (int(cx + 16 * s), int(cy - 36 * s)),
        (int(cx + 30 * s), int(cy - 24 * s)),
        (int(cx + 32 * s), int(cy - 4 * s)),
        (int(cx + 22 * s), int(cy + 18 * s)),
        (int(cx + 8 * s),  int(cy + 28 * s)),
        (int(cx - 12 * s), int(cy + 26 * s)),
        (int(cx - 28 * s), int(cy + 12 * s)),
        (int(cx - 36 * s), int(cy - 2 * s)),
    ]
    pygame.draw.polygon(surface, skin_l, head_pts)
    pygame.draw.polygon(surface, dim, head_pts, 1)
    # Hair on top
    hair_pts = [
        (int(cx - 30 * s), int(cy - 24 * s)),
        (int(cx - 10 * s), int(cy - 38 * s)),
        (int(cx + 16 * s), int(cy - 36 * s)),
        (int(cx + 30 * s), int(cy - 24 * s)),
        (int(cx + 22 * s), int(cy - 16 * s)),
        (int(cx - 18 * s), int(cy - 18 * s)),
    ]
    pygame.draw.polygon(surface, hair, hair_pts)
    pygame.draw.polygon(surface, (28, 18, 6), hair_pts, 1)
    # Hair part line
    pygame.draw.line(surface, (28, 18, 6),
                     (int(cx + 4 * s), int(cy - 36 * s)),
                     (int(cx + 16 * s), int(cy - 20 * s)), 1)

    # Eyes — narrow, calculating
    eye_y = int(cy - 8 * s)
    blink = (int(t * 0.5) % 7 == 0)
    if blink:
        pygame.draw.line(surface, dim,
                         (int(cx - 16 * s), eye_y),
                         (int(cx - 6 * s), eye_y), 1)
        pygame.draw.line(surface, dim,
                         (int(cx + 6 * s), eye_y),
                         (int(cx + 16 * s), eye_y), 1)
    else:
        # Expression: wary/angry narrows the eyes further
        narrow = 1 if disposition < -2 else 0
        pygame.draw.ellipse(surface, (40, 28, 4),
                            (int(cx - 16 * s), eye_y - 2 + narrow,
                             int(10 * s), 3 - narrow))
        pygame.draw.ellipse(surface, (40, 28, 4),
                            (int(cx + 6 * s), eye_y - 2 + narrow,
                             int(10 * s), 3 - narrow))
        # Pupils
        pygame.draw.circle(surface, (8, 4, 0),
                           (int(cx - 11 * s), eye_y), 1)
        pygame.draw.circle(surface, (8, 4, 0),
                           (int(cx + 11 * s), eye_y), 1)

    # Brows — angled down inward when wary/angry
    brow_y = int(cy - 14 * s)
    brow_tilt = max(0, -disposition) // 2
    pygame.draw.line(surface, hair,
                     (int(cx - 18 * s), brow_y),
                     (int(cx - 4 * s), brow_y + brow_tilt), 2)
    pygame.draw.line(surface, hair,
                     (int(cx + 4 * s), brow_y + brow_tilt),
                     (int(cx + 18 * s), brow_y), 2)

    # Nose
    pygame.draw.line(surface, dim,
                     (int(cx + 1 * s), int(cy - 6 * s)),
                     (int(cx - 2 * s), int(cy + 4 * s)), 1)

    # Mouth — thin pursed line, twists into a smirk
    mx0 = int(cx - 8 * s)
    mx1 = int(cx + 8 * s)
    my = int(cy + 14 * s)
    if disposition > 2:
        # Faint smile (still corporate)
        pygame.draw.line(surface, dim, (mx0, my + 1), (mx1, my + 1), 1)
    elif disposition < -3:
        # Tight, downturned
        pygame.draw.line(surface, dim, (mx0, my + 2), (mx1, my + 2), 1)
    else:
        pygame.draw.line(surface, dim, (mx0, my), (mx1, my), 1)

    # Blazer collar
    collar_pts = [
        (int(cx - 28 * s), int(cy + 46 * s)),
        (int(cx - 16 * s), int(cy + 36 * s)),
        (int(cx + 16 * s), int(cy + 36 * s)),
        (int(cx + 28 * s), int(cy + 46 * s)),
        (int(cx + 36 * s), int(cy + 70 * s)),
        (int(cx - 36 * s), int(cy + 70 * s)),
    ]
    pygame.draw.polygon(surface, suit, collar_pts)
    pygame.draw.polygon(surface, (140, 110, 30), collar_pts, 1)
    # Nova Soma lapel pin
    pygame.draw.circle(surface, amb,
                       (int(cx + 18 * s), int(cy + 50 * s)), int(2 * s) + 1)


def _sandra(surface, cx, cy, s, disposition, t):
    """
    Sandra Vega-Marsh — sharp jaw, courier jumpsuit, helmet hair,
    permanent half-smirk.
    """
    skin_l = (210, 175, 130)
    skin_d = (110, 70, 30)
    suit   = (40, 50, 100)
    accent = (210, 70, 60)
    hair   = (40, 28, 18)
    dim    = (100, 76, 24)

    # Helmet collar at neck
    helmet = [
        (int(cx - 28 * s), int(cy + 30 * s)),
        (int(cx + 28 * s), int(cy + 30 * s)),
        (int(cx + 22 * s), int(cy + 24 * s)),
        (int(cx - 22 * s), int(cy + 24 * s)),
    ]
    pygame.draw.polygon(surface, suit, helmet)
    pygame.draw.polygon(surface, (90, 100, 150), helmet, 1)

    # Neck
    neck = [(int(cx - 12 * s), int(cy + 22 * s)),
            (int(cx + 12 * s), int(cy + 22 * s)),
            (int(cx + 14 * s), int(cy + 32 * s)),
            (int(cx - 14 * s), int(cy + 32 * s))]
    pygame.draw.polygon(surface, skin_d, neck)

    # Head — angular, sharp jaw
    head_pts = [
        (int(cx - 30 * s), int(cy - 18 * s)),
        (int(cx - 16 * s), int(cy - 34 * s)),
        (int(cx + 12 * s), int(cy - 36 * s)),
        (int(cx + 28 * s), int(cy - 22 * s)),
        (int(cx + 30 * s), int(cy - 2 * s)),
        (int(cx + 18 * s), int(cy + 18 * s)),
        (int(cx + 4 * s),  int(cy + 24 * s)),
        (int(cx - 12 * s), int(cy + 22 * s)),
        (int(cx - 24 * s), int(cy + 10 * s)),
        (int(cx - 30 * s), int(cy - 4 * s)),
    ]
    pygame.draw.polygon(surface, skin_l, head_pts)
    pygame.draw.polygon(surface, dim, head_pts, 1)

    # Helmet hair — slicked back, severe
    hair_pts = [
        (int(cx - 26 * s), int(cy - 22 * s)),
        (int(cx - 16 * s), int(cy - 34 * s)),
        (int(cx + 12 * s), int(cy - 36 * s)),
        (int(cx + 28 * s), int(cy - 22 * s)),
        (int(cx + 22 * s), int(cy - 14 * s)),
        (int(cx - 18 * s), int(cy - 12 * s)),
    ]
    pygame.draw.polygon(surface, hair, hair_pts)
    pygame.draw.polygon(surface, (12, 8, 0), hair_pts, 1)
    # Slick lines
    for i in range(3):
        pygame.draw.line(surface, (28, 18, 6),
                         (int(cx - 14 * s + i * 8), int(cy - 32 * s)),
                         (int(cx - 8 * s + i * 8), int(cy - 16 * s)), 1)

    # Eyes — judgemental, half-lidded
    eye_y = int(cy - 4 * s)
    pygame.draw.ellipse(surface, (40, 28, 4),
                        (int(cx - 16 * s), eye_y - 1, int(10 * s), 3))
    pygame.draw.ellipse(surface, (40, 28, 4),
                        (int(cx + 6 * s), eye_y - 1, int(10 * s), 3))
    # Pupils — slightly off-centre (looking past you)
    pygame.draw.circle(surface, (4, 4, 0),
                       (int(cx - 9 * s), eye_y), 1)
    pygame.draw.circle(surface, (4, 4, 0),
                       (int(cx + 13 * s), eye_y), 1)

    # Brows — perfectly arched
    brow_y = int(cy - 12 * s)
    arch = max(0, -disposition) // 2
    pygame.draw.line(surface, hair,
                     (int(cx - 18 * s), brow_y + 2),
                     (int(cx - 6 * s), brow_y - 1 - arch), 2)
    pygame.draw.line(surface, hair,
                     (int(cx + 6 * s), brow_y - 1 - arch),
                     (int(cx + 18 * s), brow_y + 2), 2)

    # Nose — pointed
    pygame.draw.line(surface, dim,
                     (int(cx + 1 * s), int(cy - 2 * s)),
                     (int(cx - 1 * s), int(cy + 10 * s)), 1)

    # Mouth — half-smirk (right side higher)
    if disposition < -2:
        # Frown
        pygame.draw.arc(surface, dim,
                        (int(cx - 10 * s), int(cy + 12 * s),
                         int(20 * s), int(10 * s)),
                        math.pi, 2 * math.pi, 1)
    else:
        # Smirk
        m_l = (int(cx - 10 * s), int(cy + 16 * s))
        m_r = (int(cx + 10 * s), int(cy + 12 * s))
        pygame.draw.line(surface, dim, m_l, m_r, 1)
        # Right corner upturn
        pygame.draw.line(surface, dim, m_r, (int(cx + 12 * s), int(cy + 10 * s)), 1)

    # Suit shoulders
    sh_pts = [
        (int(cx - 36 * s), int(cy + 32 * s)),
        (int(cx + 36 * s), int(cy + 32 * s)),
        (int(cx + 42 * s), int(cy + 70 * s)),
        (int(cx - 42 * s), int(cy + 70 * s)),
    ]
    pygame.draw.polygon(surface, suit, sh_pts)
    pygame.draw.polygon(surface, (90, 100, 150), sh_pts, 1)
    # Courier patch on shoulder
    patch_x, patch_y = int(cx - 28 * s), int(cy + 40 * s)
    pygame.draw.rect(surface, accent,
                     (patch_x, patch_y, int(14 * s), int(8 * s)))
    pygame.draw.rect(surface, (40, 8, 8),
                     (patch_x, patch_y, int(14 * s), int(8 * s)), 1)


def _pirate(surface, cx, cy, s, disposition, t):
    """
    "Krellborn" pirate — scarred face, breathing mask, wrapped scarf.
    Posture and silhouette read as a threat.
    """
    skin   = (170, 130, 90)
    skin_d = (90, 60, 30)
    scarf  = (60, 30, 30)
    mask   = (30, 30, 36)
    metal  = (170, 130, 50)
    accent = (220, 50, 30)
    dim    = (110, 70, 30)

    # Wrapped scarf around neck — irregular polygon
    scarf_pts = [
        (int(cx - 36 * s), int(cy + 16 * s)),
        (int(cx - 20 * s), int(cy + 10 * s)),
        (int(cx + 20 * s), int(cy + 10 * s)),
        (int(cx + 38 * s), int(cy + 18 * s)),
        (int(cx + 42 * s), int(cy + 38 * s)),
        (int(cx - 42 * s), int(cy + 38 * s)),
    ]
    pygame.draw.polygon(surface, scarf, scarf_pts)
    pygame.draw.polygon(surface, (24, 8, 8), scarf_pts, 1)
    # Frayed scarf edges
    for ex in (-32, -18, 4, 22, 36):
        pygame.draw.line(surface, (40, 20, 20),
                         (int(cx + ex * s), int(cy + 20 * s)),
                         (int(cx + ex * s + 2), int(cy + 28 * s)), 1)

    # Head silhouette
    head_pts = [
        (int(cx - 32 * s), int(cy - 16 * s)),
        (int(cx - 20 * s), int(cy - 36 * s)),
        (int(cx + 16 * s), int(cy - 38 * s)),
        (int(cx + 30 * s), int(cy - 24 * s)),
        (int(cx + 34 * s), int(cy - 4 * s)),
        (int(cx + 22 * s), int(cy + 14 * s)),
        (int(cx - 18 * s), int(cy + 12 * s)),
        (int(cx - 30 * s), int(cy - 2 * s)),
    ]
    pygame.draw.polygon(surface, skin, head_pts)
    pygame.draw.polygon(surface, dim, head_pts, 1)

    # Scar across left cheek
    pygame.draw.line(surface, (90, 30, 30),
                     (int(cx - 22 * s), int(cy - 18 * s)),
                     (int(cx - 10 * s), int(cy + 6 * s)), 2)
    pygame.draw.line(surface, (160, 80, 80),
                     (int(cx - 22 * s), int(cy - 18 * s)),
                     (int(cx - 10 * s), int(cy + 6 * s)), 1)

    # Breathing mask covering nose+mouth
    mask_pts = [
        (int(cx - 18 * s), int(cy - 2 * s)),
        (int(cx + 18 * s), int(cy - 2 * s)),
        (int(cx + 22 * s), int(cy + 14 * s)),
        (int(cx - 22 * s), int(cy + 14 * s)),
    ]
    pygame.draw.polygon(surface, mask, mask_pts)
    pygame.draw.polygon(surface, metal, mask_pts, 1)
    # Mask filters — two metal cylinders on the sides
    for fx_off in (-20, 18):
        pygame.draw.circle(surface, metal,
                           (int(cx + fx_off * s), int(cy + 6 * s)), int(3 * s) + 1)
        pygame.draw.circle(surface, (60, 40, 10),
                           (int(cx + fx_off * s), int(cy + 6 * s)), int(3 * s) + 1, 1)
    # Mask grid
    for gx in range(-10, 11, 4):
        pygame.draw.line(surface, (15, 15, 20),
                         (int(cx + gx * s), int(cy + 2 * s)),
                         (int(cx + gx * s), int(cy + 12 * s)), 1)

    # Eyes — only visible part of face
    eye_y = int(cy - 14 * s)
    eye_l = (int(cx - 12 * s), eye_y)
    eye_r = (int(cx + 10 * s), eye_y)
    # Pupil pulse — wider when hostile (intimidating stare)
    pupil_r = 2 if disposition >= 0 else 3
    pygame.draw.circle(surface, accent, eye_l, pupil_r + 1)
    pygame.draw.circle(surface, (255, 220, 200), eye_l, pupil_r)
    pygame.draw.circle(surface, (10, 0, 0), eye_l, 1)
    pygame.draw.circle(surface, accent, eye_r, pupil_r + 1)
    pygame.draw.circle(surface, (255, 220, 200), eye_r, pupil_r)
    pygame.draw.circle(surface, (10, 0, 0), eye_r, 1)

    # Brows — heavy, low — get heavier with hostility
    brow_y = int(cy - 22 * s)
    brow_drop = max(0, -disposition)
    pygame.draw.line(surface, (40, 20, 0),
                     (int(cx - 18 * s), brow_y + brow_drop),
                     (int(cx - 4 * s),  brow_y + 2 + brow_drop), 3)
    pygame.draw.line(surface, (40, 20, 0),
                     (int(cx + 4 * s),  brow_y + 2 + brow_drop),
                     (int(cx + 18 * s), brow_y + brow_drop), 3)

    # Hood / hair wrap on top
    hood_pts = [
        (int(cx - 34 * s), int(cy - 18 * s)),
        (int(cx - 20 * s), int(cy - 38 * s)),
        (int(cx + 16 * s), int(cy - 40 * s)),
        (int(cx + 32 * s), int(cy - 24 * s)),
        (int(cx + 24 * s), int(cy - 16 * s)),
        (int(cx - 26 * s), int(cy - 14 * s)),
    ]
    pygame.draw.polygon(surface, (32, 24, 16), hood_pts)
    pygame.draw.polygon(surface, (90, 60, 30), hood_pts, 1)

    # Shoulder armour — riveted plates
    shoulder_pts = [
        (int(cx - 42 * s), int(cy + 38 * s)),
        (int(cx + 42 * s), int(cy + 38 * s)),
        (int(cx + 50 * s), int(cy + 70 * s)),
        (int(cx - 50 * s), int(cy + 70 * s)),
    ]
    pygame.draw.polygon(surface, (44, 44, 50), shoulder_pts)
    pygame.draw.polygon(surface, metal, shoulder_pts, 1)
    # Rivets
    for rx_off in (-34, -10, 10, 34):
        pygame.draw.circle(surface, metal,
                           (int(cx + rx_off * s), int(cy + 50 * s)), 2)


def _underground_dj(surface, cx, cy, s, disposition, t):
    """
    Marrow — radio DJ. Beanie, headphones, kind eyes.
    Mouth animates when "broadcasting" (high disposition triggers
    a brief mic gesture).
    """
    skin_l = (200, 160, 110)
    skin_d = (90, 60, 30)
    beanie = (60, 40, 80)
    accent = (40, 200, 230)
    head_p = (40, 40, 50)
    dim    = (100, 76, 24)

    # Headphone strap behind head
    pygame.draw.arc(surface, head_p,
                    (int(cx - 38 * s), int(cy - 50 * s),
                     int(76 * s), int(40 * s)),
                    0, math.pi, 3)

    # Beanie
    beanie_pts = [
        (int(cx - 32 * s), int(cy - 22 * s)),
        (int(cx - 28 * s), int(cy - 38 * s)),
        (int(cx - 8 * s),  int(cy - 46 * s)),
        (int(cx + 18 * s), int(cy - 44 * s)),
        (int(cx + 30 * s), int(cy - 32 * s)),
        (int(cx + 32 * s), int(cy - 18 * s)),
    ]
    pygame.draw.polygon(surface, beanie, beanie_pts)
    pygame.draw.polygon(surface, (24, 14, 38), beanie_pts, 1)
    # Beanie ribs
    for rx in range(-22, 25, 8):
        pygame.draw.line(surface, (40, 22, 60),
                         (int(cx + rx * s), int(cy - 40 * s)),
                         (int(cx + rx * s), int(cy - 18 * s)), 1)
    # Beanie pom
    pygame.draw.circle(surface, accent,
                       (int(cx - 12 * s), int(cy - 46 * s)), int(4 * s) + 1)
    pygame.draw.circle(surface, (10, 90, 110),
                       (int(cx - 12 * s), int(cy - 46 * s)), int(4 * s) + 1, 1)

    # Head silhouette
    head_pts = [
        (int(cx - 32 * s), int(cy - 18 * s)),
        (int(cx - 22 * s), int(cy - 30 * s)),
        (int(cx + 22 * s), int(cy - 30 * s)),
        (int(cx + 32 * s), int(cy - 16 * s)),
        (int(cx + 30 * s), int(cy + 4 * s)),
        (int(cx + 18 * s), int(cy + 22 * s)),
        (int(cx - 16 * s), int(cy + 24 * s)),
        (int(cx - 30 * s), int(cy + 4 * s)),
    ]
    pygame.draw.polygon(surface, skin_l, head_pts)
    pygame.draw.polygon(surface, dim, head_pts, 1)

    # Sideburns
    pygame.draw.line(surface, (60, 40, 24),
                     (int(cx - 28 * s), int(cy - 14 * s)),
                     (int(cx - 26 * s), int(cy - 2 * s)), 2)
    pygame.draw.line(surface, (60, 40, 24),
                     (int(cx + 28 * s), int(cy - 14 * s)),
                     (int(cx + 26 * s), int(cy - 2 * s)), 2)

    # Headphone cups — bracket the head
    for cup_x_off in (-32, 32):
        cup_x = int(cx + cup_x_off * s)
        cup_y = int(cy - 10 * s)
        pygame.draw.ellipse(surface, head_p,
                            (cup_x - int(8 * s), cup_y - int(8 * s),
                             int(16 * s), int(16 * s)))
        pygame.draw.ellipse(surface, accent,
                            (cup_x - int(8 * s), cup_y - int(8 * s),
                             int(16 * s), int(16 * s)), 1)
        pygame.draw.circle(surface, (15, 110, 130), (cup_x, cup_y), int(4 * s))

    # Eyes — warm, attentive
    eye_y = int(cy - 6 * s)
    pygame.draw.circle(surface, (245, 245, 245),
                       (int(cx - 10 * s), eye_y), 3)
    pygame.draw.circle(surface, (245, 245, 245),
                       (int(cx + 10 * s), eye_y), 3)
    pygame.draw.circle(surface, (40, 80, 30),
                       (int(cx - 10 * s), eye_y), 2)
    pygame.draw.circle(surface, (40, 80, 30),
                       (int(cx + 10 * s), eye_y), 2)
    pygame.draw.circle(surface, (10, 20, 10),
                       (int(cx - 10 * s), eye_y), 1)
    pygame.draw.circle(surface, (10, 20, 10),
                       (int(cx + 10 * s), eye_y), 1)

    # Brows — friendly, relaxed
    pygame.draw.line(surface, (60, 40, 24),
                     (int(cx - 16 * s), int(cy - 14 * s)),
                     (int(cx - 4 * s),  int(cy - 16 * s)), 2)
    pygame.draw.line(surface, (60, 40, 24),
                     (int(cx + 4 * s),  int(cy - 16 * s)),
                     (int(cx + 16 * s), int(cy - 14 * s)), 2)

    # Nose
    pygame.draw.line(surface, dim,
                     (int(cx + 1 * s), int(cy - 4 * s)),
                     (int(cx - 1 * s), int(cy + 8 * s)), 1)

    # Mouth — animates when broadcasting (disp >= 1 = engaged)
    speaking = disposition >= 1
    if speaking:
        m_open = int(2 + 2 * abs(math.sin(t * 12.0)))
        pygame.draw.ellipse(surface, (60, 20, 20),
                            (int(cx - 6 * s), int(cy + 12 * s),
                             int(12 * s), m_open))
    else:
        pygame.draw.line(surface, dim,
                         (int(cx - 8 * s), int(cy + 14 * s)),
                         (int(cx + 8 * s), int(cy + 14 * s)), 1)

    # Microphone arm — boom from right cup to mouth
    pygame.draw.line(surface, head_p,
                     (int(cx + 32 * s), int(cy - 6 * s)),
                     (int(cx + 18 * s), int(cy + 14 * s)), 2)
    pygame.draw.circle(surface, accent,
                       (int(cx + 18 * s), int(cy + 14 * s)), 3)
    pygame.draw.circle(surface, (10, 80, 90),
                       (int(cx + 18 * s), int(cy + 14 * s)), 3, 1)

    # Shoulders + casual jacket
    sh_pts = [
        (int(cx - 36 * s), int(cy + 30 * s)),
        (int(cx + 36 * s), int(cy + 30 * s)),
        (int(cx + 42 * s), int(cy + 70 * s)),
        (int(cx - 42 * s), int(cy + 70 * s)),
    ]
    pygame.draw.polygon(surface, (50, 60, 70), sh_pts)
    pygame.draw.polygon(surface, (90, 110, 130), sh_pts, 1)


# Patch the dispatch table now that the new functions exist
_DISPATCH["insurance_adjuster"] = _insurance_adjuster
_DISPATCH["sandra"]             = _sandra
_DISPATCH["pirate"]             = _pirate
_DISPATCH["underground_dj"]     = _underground_dj
