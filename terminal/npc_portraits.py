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

    # ── Back wall: heavy horizontal hull-plate seams ───────────────────────
    for i in range(5):
        y = inner.top + 10 + i * 14
        col = (38, 26, 6) if i % 2 == 0 else (22, 14, 2)
        pygame.draw.line(surface, col, (inner.left, y), (inner.right, y), 2)
    # Vertical wall ribs full-height
    for x_off in (18, 36, inner.width - 36, inner.width - 18):
        xr = inner.left + x_off
        pygame.draw.line(surface, (32, 22, 4), (xr, inner.top), (xr, inner.bottom), 1)

    # ── Viewport window (top-centre) — debris outside ──────────────────────
    vp = pygame.Rect(cx - 44, inner.top + 5, 88, 50)
    pygame.draw.rect(surface, (2, 6, 12), vp)
    pygame.draw.rect(surface, (80, 58, 14), vp, 3)
    # Window frame: thick cross-bar
    pygame.draw.line(surface, (65, 46, 12), (vp.left, vp.centery), (vp.right, vp.centery), 2)
    pygame.draw.line(surface, (65, 46, 12), (vp.centerx, vp.top), (vp.centerx, vp.bottom), 2)
    # Stars in window
    rng_vp = random.Random(17)
    for _ in range(18):
        sx = rng_vp.randint(vp.left + 3, vp.right - 3)
        sy = rng_vp.randint(vp.top + 3, vp.bottom - 3)
        sc = rng_vp.choice([(80, 80, 100), (100, 90, 60), (60, 110, 80)])
        pygame.draw.circle(surface, sc, (sx, sy), 1)
    # Drifting debris rock in window
    drift_off = int(4 * math.sin(t * 0.18))
    drx, dry = cx - 8 + drift_off, inner.top + 22
    drock = [(drx, dry-5), (drx+7, dry-7), (drx+12, dry-2), (drx+10, dry+5),
             (drx+3, dry+6), (drx-3, dry+3)]
    pygame.draw.polygon(surface, (28, 22, 38), drock)
    pygame.draw.polygon(surface, (60, 50, 75), drock, 1)
    # Second smaller rock
    drx2, dry2 = cx + 18 - drift_off, inner.top + 32
    drock2 = [(drx2, dry2-3), (drx2+4, dry2-4), (drx2+6, dry2), (drx2+4, dry2+3), (drx2-1, dry2+2)]
    pygame.draw.polygon(surface, (24, 20, 34), drock2)
    pygame.draw.polygon(surface, (50, 44, 62), drock2, 1)

    # ── Hazard stripe panels left and right of viewport ─────────────────────
    for side_x, w in ((inner.left, 40), (inner.right - 40, 40)):
        stripe_rect = pygame.Rect(side_x, inner.top + 5, w, 50)
        pygame.draw.rect(surface, (16, 12, 0), stripe_rect)
        pygame.draw.rect(surface, (55, 38, 0), stripe_rect, 1)
        for k in range(0, w + 50, 10):
            x1 = side_x + k
            y1 = inner.top + 5
            x2 = side_x + k - 50
            y2 = inner.top + 55
            pygame.draw.line(surface, (85, 58, 0),
                             (max(side_x, min(side_x+w, x1)), y1),
                             (max(side_x, min(side_x+w, x2)), y2), 2)

    # ── CAUTION blink lights ─────────────────────────────────────────────────
    pulse = 0.5 + 0.5 * math.sin(t * 3.1)
    blink_fast = (int(t * 2.6) % 2 == 0)
    caution_col = (int(210 * pulse), int(115 * pulse), 0) if blink_fast else (38, 20, 0)
    for lx in (inner.left + 12, inner.right - 12):
        pygame.draw.circle(surface, (28, 16, 0), (lx, inner.top + 14), 8)
        pygame.draw.circle(surface, caution_col, (lx, inner.top + 14), 6)
        pygame.draw.circle(surface, (70, 42, 0), (lx, inner.top + 14), 8, 1)
    caut = font6.render("!! CAUTION !!", True, (int(165*pulse), int(85*pulse), 0))
    surface.blit(caut, (cx - caut.get_width()//2, inner.top + 9))

    # ── Side wall ribs mid-section ────────────────────────────────────────────
    for i in range(5):
        x_l = inner.left + 4 + i * 6
        x_r = inner.right - 4 - i * 6
        pygame.draw.line(surface, (30, 20, 4), (x_l, inner.top + 58),
                         (x_l, inner.bottom - 38), 1)
        pygame.draw.line(surface, (30, 20, 4), (x_r, inner.top + 58),
                         (x_r, inner.bottom - 38), 1)

    # ── Four monitor screens: STATUS, MANIFEST, COMMS, ROUTE ─────────────────
    screen_defs = [
        (inner.left + 4,   inner.top + 60, 42, 30, "STATUS"),
        (inner.left + 50,  inner.top + 60, 42, 30, "MANIFEST"),
        (cx - 18,          inner.top + 60, 42, 30, "COMMS"),
        (inner.right - 46, inner.top + 60, 42, 30, "ROUTE"),
    ]
    mon_blink_frame = int(t * 4)
    for mx, my, mw, mh, label in screen_defs:
        pygame.draw.rect(surface, (5, 7, 2), (mx, my, mw, mh))
        pygame.draw.rect(surface, (85, 62, 12), (mx, my, mw, mh), 1)
        for sl in range(my + 3, my + mh - 1, 3):
            pygame.draw.line(surface, (8, 10, 2), (mx+1, sl), (mx+mw-2, sl), 1)
        pygame.draw.rect(surface, (22, 16, 0), (mx, my, mw, 8))
        lbl = font6.render(label, True, (145, 104, 22))
        surface.blit(lbl, (mx + mw//2 - lbl.get_width()//2, my + 1))
        for row in range(3):
            scroll_idx = (mon_blink_frame + row * 3 + hash(label) % 7) % 8
            line_col = (55, 185, 55) if scroll_idx < 6 else (185, 55, 18)
            blen = int(mw * 0.25 + (scroll_idx / 8.0) * mw * 0.60)
            pygame.draw.rect(surface, line_col, (mx + 3, my + 10 + row * 6, blen, 3))
    # STATUS: blinking ONLINE dot
    st_mx, st_my = screen_defs[0][0], screen_defs[0][1]
    stat_blink = (int(t * 1.9) % 2 == 0)
    pygame.draw.circle(surface, (0, 220, 80) if stat_blink else (0, 55, 20),
                       (st_mx + 36, st_my + 25), 3)

    # ── Union logo panel (wall-mounted plaque) ────────────────────────────────
    logo_rect = pygame.Rect(cx + 32, inner.top + 60, 28, 34)
    pygame.draw.rect(surface, (12, 8, 0), logo_rect)
    pygame.draw.rect(surface, (108, 72, 0), logo_rect, 2)
    # Hex shape embossed
    lhx, lhy = logo_rect.centerx, logo_rect.top + 10
    hex_pts = [(lhx + int(8*math.cos(math.pi/3*i)), lhy + int(8*math.sin(math.pi/3*i)))
               for i in range(6)]
    pygame.draw.polygon(surface, (24, 16, 0), hex_pts)
    pygame.draw.polygon(surface, (180, 128, 24), hex_pts, 1)
    lbl404 = font8.render("404", True, (220, 160, 30))
    surface.blit(lbl404, (logo_rect.centerx - lbl404.get_width()//2, logo_rect.top + 20))

    # ── Coffee mug on console desk ─────────────────────────────────────────────
    mug_x, mug_y = inner.left + 10, inner.bottom - 38
    pygame.draw.rect(surface, (32, 20, 6), (mug_x, mug_y, 12, 14))
    pygame.draw.rect(surface, (75, 52, 16), (mug_x, mug_y, 12, 14), 1)
    pygame.draw.arc(surface, (75, 52, 16),
                    pygame.Rect(mug_x + 11, mug_y + 4, 6, 7), -math.pi/2, math.pi/2, 1)
    for si in range(3):
        steam_x = mug_x + 2 + si * 4
        steam_y = mug_y - 4 - int(4 * math.sin(t * 1.8 + si * 1.2))
        pygame.draw.circle(surface, (55, 50, 44), (steam_x, steam_y), 1)

    # ── Maintenance manuals stacked left ──────────────────────────────────────
    book_defs = [
        (inner.left + 4, inner.bottom - 32, 16, 8, (80, 28, 14)),
        (inner.left + 4, inner.bottom - 24, 18, 8, (28, 58, 18)),
        (inner.left + 4, inner.bottom - 16, 20, 8, (14, 28, 80)),
        (inner.left + 4, inner.bottom - 8,  22, 8, (60, 48, 10)),
    ]
    for bx2, by2, bw2, bh2, bc in book_defs:
        pygame.draw.rect(surface, bc, (bx2, by2, bw2, bh2))
        pygame.draw.rect(surface, (105, 85, 42), (bx2, by2, bw2, bh2), 1)
        # Spine line
        pygame.draw.line(surface, (50, 40, 20), (bx2+2, by2), (bx2+2, by2+bh2), 1)

    # ── Radio handset ─────────────────────────────────────────────────────────
    rx, ry = cx + 46, inner.bottom - 30
    pygame.draw.rect(surface, (22, 14, 4), (rx, ry, 8, 18))
    pygame.draw.rect(surface, (85, 58, 12), (rx, ry, 8, 18), 1)
    pygame.draw.circle(surface, (65, 44, 8), (rx + 4, ry + 4), 2)
    pygame.draw.circle(surface, (65, 44, 8), (rx + 4, ry + 14), 2)
    pygame.draw.arc(surface, (65, 44, 8),
                    pygame.Rect(rx + 7, ry + 7, 8, 5), -math.pi/2, math.pi/2, 1)

    # ── Main control console panel ────────────────────────────────────────────
    panel = pygame.Rect(inner.left + 4, inner.bottom - 36, inner.width - 8, 28)
    pygame.draw.rect(surface, (14, 10, 0), panel)
    pygame.draw.line(surface, (70, 46, 10), (panel.left, panel.top), (panel.right, panel.top), 2)
    pygame.draw.line(surface, (40, 26, 6), (panel.left, panel.top+1), (panel.right, panel.top+1), 1)
    # Toggle switches — varied colours and sizes
    for i in range(12):
        bx3 = panel.left + 6 + i * 16
        if bx3 + 8 > panel.right - 4:
            break
        lit = (int(t * 0.55) + i * 4) % 11 == 0
        sw_col = (200, 120, 0) if lit else (38, 24, 4)
        pygame.draw.rect(surface, sw_col, (bx3, panel.top + 5, 7, 5))
        pygame.draw.rect(surface, (65, 44, 10), (bx3, panel.top + 5, 7, 5), 1)
        # Toggle stem
        pygame.draw.line(surface, (55, 36, 8),
                         (bx3 + 3, panel.top + 5), (bx3 + 3, panel.top + 3), 1)
    # BARGE STATUS readout
    stat_col = (0, 185, 82) if (int(t * 0.55) % 2 == 0) else (0, 75, 28)
    stat_txt = font7.render("BARGE STATUS: NOMINAL  CH.7 CLEAR", True, stat_col)
    surface.blit(stat_txt, (panel.left + 6, panel.top + 14))
    # Small blinking LED cluster
    for li in range(4):
        lled = (int(t * 3 + li * 2.1) % 5 == 0)
        lcol = [(0, 200, 70), (200, 120, 0), (200, 40, 40), (0, 140, 200)][li]
        pygame.draw.circle(surface, lcol if lled else (18, 12, 4),
                           (panel.right - 20 + li * 6, panel.top + 8), 2)


def _backdrop_synthetic_droid(surface, inner, t):
    """Nova Soma sterile processing room — white-green clinical tech horror."""
    cx = inner.centerx
    font6 = pygame.font.SysFont("monospace", 6, bold=True)
    font7 = pygame.font.SysFont("monospace", 7)

    # ── Grid floor — perspective lines converging at horizon ──────────────────
    floor_y  = inner.bottom - 10
    horizon  = inner.top + inner.height * 2 // 5
    vp_x     = cx
    for gx in range(inner.left, inner.right + 2, 16):
        pygame.draw.line(surface, (10, 24, 12), (gx, floor_y), (vp_x, horizon), 1)
    for gy_frac in (0.55, 0.65, 0.74, 0.82, 0.90, 0.97, 1.0):
        gy = inner.top + int(inner.height * gy_frac) - 10
        if horizon <= gy <= floor_y:
            pygame.draw.line(surface, (10, 24, 12), (inner.left, gy), (inner.right, gy), 1)

    # ── Grid ceiling ──────────────────────────────────────────────────────────
    ceil_y = inner.top + 12
    for gx in range(inner.left, inner.right + 2, 16):
        pygame.draw.line(surface, (8, 18, 10), (gx, ceil_y), (vp_x, horizon), 1)
    for gy_frac in (0.0, 0.05, 0.11, 0.17, 0.23):
        gy = inner.top + int(inner.height * gy_frac) + 4
        if inner.top <= gy <= ceil_y + 30:
            pygame.draw.line(surface, (8, 18, 10), (inner.left, gy), (inner.right, gy), 1)

    # ── Overhead LED lighting strips ──────────────────────────────────────────
    for lx_off in (inner.width // 4, inner.width // 2, 3 * inner.width // 4):
        lx = inner.left + lx_off
        pulse_l = 0.75 + 0.25 * math.sin(t * 0.9 + lx_off * 0.02)
        pygame.draw.line(surface, (int(12 * pulse_l), int(28 * pulse_l), int(14 * pulse_l)),
                         (lx - 18, inner.top + 6), (lx + 18, inner.top + 6), 2)
        # Glow underneath
        glow_l = pygame.Surface((40, 14), pygame.SRCALPHA)
        pygame.draw.rect(glow_l, (0, int(180 * pulse_l), int(60 * pulse_l), 28),
                         (0, 0, 40, 14))
        surface.blit(glow_l, (lx - 20, inner.top + 7))

    # ── Server rack towers — left and right walls ─────────────────────────────
    rack_specs = [
        (inner.left + 2,  inner.top + 12, 28, inner.height - 24),
        (inner.left + 32, inner.top + 18, 20, inner.height - 34),
        (inner.right - 30, inner.top + 12, 28, inner.height - 24),
        (inner.right - 52, inner.top + 18, 20, inner.height - 34),
    ]
    for rx, ry, rw, rh in rack_specs:
        pygame.draw.rect(surface, (5, 14, 8), (rx, ry, rw, rh))
        pygame.draw.rect(surface, (22, 52, 28), (rx, ry, rw, rh), 1)
        # Rack unit dividers
        for unit in range(0, rh, 5):
            pygame.draw.line(surface, (12, 30, 16),
                             (rx + 1, ry + unit), (rx + rw - 2, ry + unit), 1)
        # LED column (right side of rack)
        for row in range(0, rh - 4, 5):
            phase = (row // 5 + int(t * 6) + rx) % 8
            if phase < 5:
                led_col = (0, 220, 80)
            elif phase == 5:
                led_col = (220, 180, 0)
            elif phase == 6:
                led_col = (180, 30, 30)
            else:
                led_col = (0, 100, 200)
            pygame.draw.rect(surface, led_col, (rx + rw - 5, ry + row + 1, 3, 3))
        # Drive bay slots
        for slot in range(ry + 4, min(ry + rh - 4, ry + 50), 8):
            pygame.draw.rect(surface, (8, 20, 12), (rx + 3, slot, rw - 10, 5))
            pygame.draw.rect(surface, (16, 40, 22), (rx + 3, slot, rw - 10, 5), 1)

    # ── Cable conduits running across walls ───────────────────────────────────
    for cy_off in (0.18, 0.36, 0.54, 0.72):
        cy2 = inner.top + int(inner.height * cy_off)
        # Main conduit (thick)
        pygame.draw.line(surface, (14, 30, 16), (inner.left + 30, cy2), (inner.right - 30, cy2), 3)
        pygame.draw.line(surface, (0, 55, 22), (inner.left + 30, cy2), (inner.right - 30, cy2), 1)
        # Thinner side conduit
        pygame.draw.line(surface, (8, 20, 10),
                         (inner.left + 30, cy2 + 4), (inner.right - 30, cy2 + 4), 1)
        # Connector clips
        for cx3 in (inner.left + 50, cx - 20, cx + 20, inner.right - 50):
            pygame.draw.rect(surface, (22, 62, 32), (cx3 - 3, cy2 - 4, 6, 10))
            pygame.draw.rect(surface, (0, 105, 52), (cx3 - 3, cy2 - 4, 6, 10), 1)

    # ── Overhead cable tray ───────────────────────────────────────────────────
    tray_y = inner.top + 8
    pygame.draw.rect(surface, (8, 22, 11), (inner.left + 4, tray_y, inner.width - 8, 5))
    pygame.draw.rect(surface, (32, 65, 38), (inner.left + 4, tray_y, inner.width - 8, 5), 1)
    # Cable drops from tray
    for hx in range(inner.left + 16, inner.right - 4, 12):
        drop = 8 + int(4 * math.sin(t * 0.4 + hx * 0.1))
        pygame.draw.line(surface, (16, 38, 20), (hx, tray_y + 5), (hx + 2, tray_y + drop), 1)

    # ── Nova Soma logo — abstract diamond geometry on back wall ───────────────
    logo_cx = cx
    logo_cy = inner.top + int(inner.height * 0.36)
    logo_r  = 16
    pulse_a = 0.5 + 0.5 * math.sin(t * 2.8)
    # Outer diamond (glowing)
    ns_pts = [(logo_cx, logo_cy - logo_r), (logo_cx + logo_r, logo_cy),
              (logo_cx, logo_cy + logo_r), (logo_cx - logo_r, logo_cy)]
    pygame.draw.polygon(surface, (4, 20, 10), ns_pts)
    pygame.draw.polygon(surface, (0, int(210 * pulse_a), int(85 * pulse_a)), ns_pts, 2)
    # Inner nested diamond
    ir = logo_r * 2 // 3
    ns_in = [(logo_cx, logo_cy - ir), (logo_cx + ir, logo_cy),
             (logo_cx, logo_cy + ir), (logo_cx - ir, logo_cy)]
    pygame.draw.polygon(surface, (0, int(145 * pulse_a), int(55 * pulse_a)), ns_in, 1)
    # Centre cross
    pygame.draw.line(surface, (0, int(200 * pulse_a), int(70 * pulse_a)),
                     (logo_cx - logo_r//2, logo_cy), (logo_cx + logo_r//2, logo_cy), 1)
    pygame.draw.line(surface, (0, int(200 * pulse_a), int(70 * pulse_a)),
                     (logo_cx, logo_cy - logo_r//2), (logo_cx, logo_cy + logo_r//2), 1)
    pygame.draw.circle(surface, (0, int(230 * pulse_a), int(90 * pulse_a)),
                       (logo_cx, logo_cy), 3)
    ns_lbl = font6.render("NOVA  SOMA", True, (0, int(145 * pulse_a), int(55 * pulse_a)))
    surface.blit(ns_lbl, (logo_cx - ns_lbl.get_width()//2, logo_cy + logo_r + 4))

    # ── Status monitor array — top centre ─────────────────────────────────────
    mon_x = cx - 38
    mon_y = inner.top + 14
    for mi in range(4):
        msx = mon_x + mi * 22
        pygame.draw.rect(surface, (2, 11, 5), (msx, mon_y, 19, 15))
        pygame.draw.rect(surface, (22, 64, 28), (msx, mon_y, 19, 15), 1)
        bar_w = int(4 + 11 * ((math.sin(t * 2.6 + mi * 1.2) * 0.5 + 0.5)))
        pygame.draw.rect(surface, (0, 185, 62), (msx + 2, mon_y + 5, bar_w, 4))
        blink2 = (int(t * 3.2 + mi) % 5 == 0)
        pygame.draw.circle(surface, (0, 225, 85) if blink2 else (0, 48, 18),
                           (msx + 16, mon_y + 3), 2)
        # Scanlines
        for sl in range(mon_y + 2, mon_y + 13, 2):
            pygame.draw.line(surface, (4, 14, 6), (msx+1, sl), (msx+17, sl), 1)

    # ── Analysis / dissection table lower-centre ──────────────────────────────
    tbl_rect = pygame.Rect(cx - 36, inner.bottom - 22, 72, 12)
    pygame.draw.rect(surface, (8, 22, 12), tbl_rect)
    pygame.draw.rect(surface, (0, 128, 55), tbl_rect, 1)
    # Table surface detail line
    pygame.draw.line(surface, (0, 80, 38), (tbl_rect.left + 4, tbl_rect.centery),
                     (tbl_rect.right - 4, tbl_rect.centery), 1)
    # Legs
    for lx in (tbl_rect.left + 8, tbl_rect.right - 8):
        pygame.draw.line(surface, (0, 85, 38), (lx, tbl_rect.bottom), (lx, tbl_rect.bottom + 5), 1)
    # Specimen container on table
    pygame.draw.rect(surface, (4, 30, 16), (cx - 12, inner.bottom - 28, 24, 9))
    pygame.draw.rect(surface, (0, 168, 74), (cx - 12, inner.bottom - 28, 24, 9), 1)
    # Analyzing blink
    an_col = (0, 205, 82) if (int(t * 2.2) % 2 == 0) else (0, 62, 26)
    an_lbl = font6.render("ANALYZING", True, an_col)
    surface.blit(an_lbl, (cx - an_lbl.get_width()//2, inner.bottom - 34))

    # ── Cooling vent strip at bottom ───────────────────────────────────────────
    for vx in range(inner.left + 4, inner.right - 4, 13):
        pygame.draw.rect(surface, (7, 18, 10), (vx, inner.bottom - 9, 10, 6))
        pygame.draw.rect(surface, (18, 46, 24), (vx, inner.bottom - 9, 10, 6), 1)
        for vy in range(inner.bottom - 8, inner.bottom - 3, 2):
            pygame.draw.line(surface, (12, 32, 15), (vx + 1, vy), (vx + 9, vy), 1)
    # Vent flow animation — tiny drifting particle
    vent_drift = int((t * 22) % (inner.width - 8))
    pygame.draw.circle(surface, (0, 85, 35),
                       (inner.left + 4 + vent_drift, inner.bottom - 12), 1)


def _backdrop_union_dispatcher(surface, inner, t):
    """Massive union dispatch centre — rows of terminals receding in perspective."""
    cx = inner.centerx
    font6 = pygame.font.SysFont("monospace", 6, bold=True)
    font7 = pygame.font.SysFont("monospace", 7)

    # ── Ceiling: fluorescent light strips with flicker ────────────────────────
    flick = 0.82 + 0.18 * (math.sin(t * 7.1) > 0.55)
    for lx_frac in (0.20, 0.50, 0.80):
        lx = inner.left + int(inner.width * lx_frac)
        pygame.draw.line(surface, (int(180 * flick), int(172 * flick), int(88 * flick)),
                         (lx - 22, inner.top + 4), (lx + 22, inner.top + 4), 2)
        glow_strip = pygame.Surface((50, 16), pygame.SRCALPHA)
        pygame.draw.rect(glow_strip, (220, 210, 130, int(30 * flick)), (0, 0, 50, 16))
        surface.blit(glow_strip, (lx - 25, inner.top + 5))

    # ── Back wall: perspective receding rows of desks/terminals ──────────────
    # Draw 4 rows, each row smaller and higher (vanishing point at cx, horizon)
    horizon_y = inner.top + inner.height // 3
    row_defs = [
        # (y, row_h, desk_w, desk_h, label_size)
        (inner.bottom - 36, 10, inner.width - 8, 8),
        (inner.bottom - 60, 8,  inner.width * 3//4, 7),
        (inner.bottom - 78, 6,  inner.width // 2, 6),
        (inner.bottom - 90, 5,  inner.width // 3, 5),
    ]
    for ry, rh, row_w, desk_h in row_defs:
        row_x = cx - row_w // 2
        # Desk surface
        pygame.draw.rect(surface, (30, 24, 8), (row_x, ry, row_w, desk_h))
        pygame.draw.line(surface, (70, 56, 18), (row_x, ry), (row_x + row_w, ry), 1)
        # Individual terminal monitors on each desk row
        n_terms = max(2, row_w // 28)
        term_w = max(14, row_w // n_terms - 4)
        term_h = max(8, desk_h + 4)
        for ti in range(n_terms):
            tx = row_x + 4 + ti * (term_w + 4)
            ty = ry - term_h
            pygame.draw.rect(surface, (4, 10, 4), (tx, ty, term_w, term_h))
            pygame.draw.rect(surface, (55, 80, 20), (tx, ty, term_w, term_h), 1)
            # Scrolling data on screen
            scroll = (int(t * 3 + ti * 7 + ry) % 6)
            bar_w2 = int(term_w * (0.3 + scroll / 10.0))
            bar_col = (50, 170, 50) if scroll < 4 else (170, 130, 30)
            pygame.draw.rect(surface, bar_col, (tx + 1, ty + term_h//2, bar_w2, 2))
        # Chair backs below desk
        for ti in range(n_terms):
            chx = row_x + 10 + ti * (row_w // n_terms)
            pygame.draw.rect(surface, (20, 16, 6), (chx, ry + desk_h, 10, 5))
            pygame.draw.rect(surface, (45, 36, 12), (chx, ry + desk_h, 10, 5), 1)

    # ── Perspective floor lines ────────────────────────────────────────────────
    for fx_frac in range(0, inner.width, 18):
        fx = inner.left + fx_frac
        pygame.draw.line(surface, (22, 18, 4), (fx, inner.bottom), (cx, horizon_y), 1)

    # ── Overhead informational boards — tally counters ────────────────────────
    board_y = inner.top + 12
    boards = [
        (inner.left + 10, 60, 18, "FORMS"),
        (cx - 28,         56, 16, "QUEUE"),
        (inner.right - 70, 56, 16, "DESKS"),
    ]
    for bx2, bw2, bh2, blabel in boards:
        pygame.draw.rect(surface, (10, 8, 0), (bx2, board_y, bw2, bh2))
        pygame.draw.rect(surface, (120, 90, 18), (bx2, board_y, bw2, bh2), 1)
        bl = font6.render(blabel, True, (200, 155, 28))
        surface.blit(bl, (bx2 + bw2//2 - bl.get_width()//2, board_y + 2))
        # Scrolling 4-digit counter
        cval = (int(t * 1.4 + hash(blabel)) % 9999)
        cv_lbl = font6.render(f"{cval:04d}", True, (255, 176, 0))
        surface.blit(cv_lbl, (bx2 + bw2//2 - cv_lbl.get_width()//2, board_y + 10))
        # Row of tiny horizontal bars (tally)
        for bi in range(5):
            b_on = (int(t * 2 + bi) % 6 != 0)
            bc = (180, 140, 0) if b_on else (40, 30, 4)
            pygame.draw.rect(surface, bc, (bx2 + 3 + bi * 10, board_y + bh2 - 5, 8, 3))

    # ── Union seal badge on back wall ─────────────────────────────────────────
    seal_x, seal_y = inner.right - 34, inner.top + 8
    pygame.draw.circle(surface, (18, 12, 0), (seal_x, seal_y + 14), 14)
    pygame.draw.circle(surface, (130, 95, 18), (seal_x, seal_y + 14), 14, 2)
    # Inner ring
    pygame.draw.circle(surface, (90, 65, 12), (seal_x, seal_y + 14), 9, 1)
    # "404" at centre
    s4 = font6.render("404", True, (200, 152, 24))
    surface.blit(s4, (seal_x - s4.get_width()//2, seal_y + 14 - s4.get_height()//2))
    # Radial spokes of seal
    for si in range(8):
        sa = si * math.pi / 4
        sx1 = int(seal_x + math.cos(sa) * 9)
        sy1 = int(seal_y + 14 + math.sin(sa) * 9)
        sx2 = int(seal_x + math.cos(sa) * 13)
        sy2 = int(seal_y + 14 + math.sin(sa) * 13)
        pygame.draw.line(surface, (110, 80, 14), (sx1, sy1), (sx2, sy2), 1)

    # ── Radio tower antenna visible through top-right window ──────────────────
    win_rect = pygame.Rect(inner.right - 50, inner.top + 4, 40, 36)
    pygame.draw.rect(surface, (2, 4, 8), win_rect)
    pygame.draw.rect(surface, (65, 50, 12), win_rect, 1)
    # Antenna
    ant_x, ant_y = win_rect.centerx, win_rect.bottom - 2
    pygame.draw.line(surface, (55, 85, 45), (ant_x, ant_y), (ant_x, win_rect.top + 6), 1)
    for cross_y in (win_rect.top + 10, win_rect.top + 18, win_rect.top + 26):
        pygame.draw.line(surface, (45, 70, 38), (ant_x - 5, cross_y), (ant_x + 5, cross_y), 1)
    ant_blink = (int(t * 1.6) % 2 == 0)
    pygame.draw.circle(surface, (200, 40, 40) if ant_blink else (55, 10, 10),
                       (ant_x, win_rect.top + 7), 2)

    # ── FORM BACKLOG counter — large panel ────────────────────────────────────
    bl_rect = pygame.Rect(inner.left + 6, inner.top + 4, 68, 22)
    pygame.draw.rect(surface, (14, 8, 0), bl_rect)
    pygame.draw.rect(surface, (170, 50, 50), bl_rect, 2)
    bl_title = font6.render("FORM BACKLOG", True, (200, 80, 60))
    surface.blit(bl_title, (bl_rect.left + 4, bl_rect.top + 2))
    backlog_n = 4728 + int(t * 0.3)
    bl_num = font7.render(str(backlog_n), True, (255, 80, 60))
    surface.blit(bl_num, (bl_rect.centerx - bl_num.get_width()//2, bl_rect.top + 11))

    # ── Paper stacks at bottom left/right ─────────────────────────────────────
    for pstack_x, count, step in ((inner.left + 4, 10, 4), (inner.right - 32, 12, 3)):
        for i in range(count):
            py2 = inner.bottom - 14 - i * step
            off2 = ((i * 7) % 5) - 2
            shade = 55 + (i % 3) * 8
            pygame.draw.rect(surface, (shade, shade - 5, shade // 2),
                             (pstack_x + off2, py2, 28, step))
            pygame.draw.rect(surface, (110, 102, 52),
                             (pstack_x + off2, py2, 28, step), 1)
    # IN-TRAY label
    tray_lbl = font6.render("IN-TRAY: 47 BEHIND", True, (185, 55, 55))
    surface.blit(tray_lbl, (inner.left + 5, inner.bottom - 22))


def _backdrop_kress(surface, inner, t):
    """Dimly lit black-market stall — contraband airlock junction."""
    cx = inner.centerx
    font6 = pygame.font.SysFont("monospace", 6, bold=True)
    font7 = pygame.font.SysFont("monospace", 7)

    # ── Corrugated metal wall — vertical corrugation stripes ─────────────────
    for i in range(0, inner.width, 7):
        x = inner.left + i
        col = (30, 28, 35) if (i // 7) % 2 == 0 else (18, 17, 24)
        pygame.draw.line(surface, col, (x, inner.top), (x, inner.bottom), 1)
    # Horizontal rust bands
    for ry_off in (0.28, 0.55, 0.78):
        ry2 = inner.top + int(inner.height * ry_off)
        pygame.draw.line(surface, (38, 22, 14), (inner.left, ry2), (inner.right, ry2), 1)

    # ── Piped conduit running along ceiling ───────────────────────────────────
    pipe_y = inner.top + 8
    pygame.draw.line(surface, (45, 38, 50), (inner.left + 2, pipe_y), (inner.right - 2, pipe_y), 4)
    pygame.draw.line(surface, (70, 55, 75), (inner.left + 2, pipe_y), (inner.right - 2, pipe_y), 1)
    # Pipe clamps
    for pcx in range(inner.left + 20, inner.right - 10, 28):
        pygame.draw.rect(surface, (60, 50, 65), (pcx - 3, pipe_y - 3, 6, 8))
        pygame.draw.rect(surface, (90, 75, 95), (pcx - 3, pipe_y - 3, 6, 8), 1)

    # ── Flickering overhead light ─────────────────────────────────────────────
    flicker_phase = math.sin(t * 13.7)
    flicker_on = flicker_phase > -0.85
    light_col = (180, 155, 80) if flicker_on else (30, 24, 12)
    light_x = cx - 10
    pygame.draw.rect(surface, light_col, (light_x, inner.top + 10, 20, 5))
    pygame.draw.rect(surface, (120, 100, 40), (light_x, inner.top + 10, 20, 5), 1)
    if flicker_on:
        glow_l = pygame.Surface((60, 40), pygame.SRCALPHA)
        pygame.draw.rect(glow_l, (180, 150, 70, 25), (0, 0, 60, 40))
        surface.blit(glow_l, (cx - 30, inner.top + 14))

    # ── Porthole/viewport with stars ──────────────────────────────────────────
    port_x, port_y = inner.right - 28, inner.top + 16
    pygame.draw.circle(surface, (4, 4, 8), (port_x, port_y), 18)
    pygame.draw.circle(surface, (65, 50, 30), (port_x, port_y), 18, 3)
    pygame.draw.circle(surface, (45, 35, 18), (port_x, port_y), 14, 1)
    rng_port = random.Random(42)
    for _ in range(10):
        sx = rng_port.randint(port_x - 14, port_x + 14)
        sy = rng_port.randint(port_y - 14, port_y + 14)
        if (sx - port_x)**2 + (sy - port_y)**2 < 14**2:
            pygame.draw.circle(surface, (85, 85, 110), (sx, sy), 1)
    # Porthole bolt holes
    for ba in range(0, 360, 60):
        bpx = int(port_x + math.cos(math.radians(ba)) * 18)
        bpy = int(port_y + math.sin(math.radians(ba)) * 18)
        pygame.draw.circle(surface, (55, 42, 22), (bpx, bpy), 2)

    # ── Stacked cargo crates left side ────────────────────────────────────────
    crate_defs = [
        (inner.left + 4, inner.bottom - 30, 30, 20),
        (inner.left + 4, inner.bottom - 52, 26, 20),
        (inner.left + 8, inner.bottom - 70, 22, 16),
        (inner.left + 36, inner.bottom - 36, 24, 26),
    ]
    stencils = ["HC-4", "OUT", "BLK", "V-7"]
    for (cx2, cy2, cw, ch), stencil in zip(crate_defs, stencils):
        pygame.draw.rect(surface, (28, 24, 32), (cx2, cy2, cw, ch))
        pygame.draw.rect(surface, (75, 60, 42), (cx2, cy2, cw, ch), 1)
        # Corner brackets
        for brx, bry in ((cx2, cy2), (cx2+cw-4, cy2), (cx2, cy2+ch-4), (cx2+cw-4, cy2+ch-4)):
            pygame.draw.rect(surface, (100, 80, 45), (brx, bry, 4, 4), 1)
        # Stencil text
        st_lbl = font6.render(stencil, True, (100, 85, 48))
        surface.blit(st_lbl, (cx2 + cw//2 - st_lbl.get_width()//2,
                               cy2 + ch//2 - st_lbl.get_height()//2))

    # ── Contraband items on shelves (right side) ──────────────────────────────
    shelf_defs = [(inner.right - 50, inner.top + 32, 44, 5),
                  (inner.right - 50, inner.top + 58, 44, 5),
                  (inner.right - 50, inner.top + 84, 44, 5)]
    for sx2, sy2, sw2, sh2 in shelf_defs:
        pygame.draw.rect(surface, (40, 34, 14), (sx2, sy2, sw2, sh2))
        pygame.draw.rect(surface, (80, 65, 28), (sx2, sy2, sw2, sh2), 1)
        # Items on shelf
        ix = sx2 + 4
        # Item 1: small box
        pygame.draw.rect(surface, (32, 44, 30), (ix, sy2 - 10, 10, 10))
        pygame.draw.rect(surface, (60, 80, 56), (ix, sy2 - 10, 10, 10), 1)
        # Item 2: cylinder (fuel cell)
        pygame.draw.rect(surface, (34, 28, 38), (ix + 14, sy2 - 12, 8, 12))
        pygame.draw.circle(surface, (65, 52, 72), (ix + 18, sy2 - 12), 4)
        # Item 3: abstract weapon shape
        weapon_pts = [(ix + 26, sy2 - 8), (ix + 36, sy2 - 4),
                      (ix + 38, sy2), (ix + 24, sy2 - 2)]
        pygame.draw.polygon(surface, (50, 50, 55), weapon_pts)
        pygame.draw.polygon(surface, (120, 100, 60), weapon_pts, 1)

    # ── Hand-written price list board ─────────────────────────────────────────
    board_x, board_y = inner.left + 4, inner.top + 4
    board_w, board_h = 54, 26
    pygame.draw.rect(surface, (22, 18, 8), (board_x, board_y, board_w, board_h))
    pygame.draw.rect(surface, (85, 65, 22), (board_x, board_y, board_w, board_h), 1)
    price_lines = ["HC-4   800cr", "FUEL   200cr", "PARTS  450cr"]
    for pi, pl in enumerate(price_lines):
        pl_lbl = font6.render(pl, True, (140, 120, 45))
        surface.blit(pl_lbl, (board_x + 3, board_y + 3 + pi * 8))

    # ── Shadow figures in background (distant customers) ──────────────────────
    for fig_x, fig_y_off in ((cx - 18, 0), (cx + 24, 4)):
        fy = inner.bottom - 40 + fig_y_off
        # Head
        pygame.draw.circle(surface, (22, 18, 22), (fig_x, fy - 12), 5)
        # Body
        pygame.draw.line(surface, (22, 18, 22), (fig_x, fy - 7), (fig_x, fy + 8), 3)
        # Arms
        pygame.draw.line(surface, (22, 18, 22), (fig_x - 5, fy - 2), (fig_x + 5, fy - 2), 2)

    # ── Fog wisps at bottom ────────────────────────────────────────────────────
    for k in range(4):
        fy2 = inner.bottom - 16 + k * 3
        for fx2 in range(inner.left + 4, inner.right - 4, 5):
            wob = int(2 * math.sin(t * 0.7 + fx2 * 0.08 + k * 0.6))
            pygame.draw.line(surface, (38, 36, 46), (fx2, fy2 + wob), (fx2 + 4, fy2 + wob), 1)

    # ── Neon sign ─────────────────────────────────────────────────────────────
    sign_flicker = (int(t * 11) % 10) != 0
    sign = pygame.Rect(cx - 28, inner.top + 12, 52, 16)
    pygame.draw.rect(surface, (12, 8, 18), sign)
    pygame.draw.rect(surface, (190, 0, 230) if sign_flicker else (40, 0, 65), sign, 1)
    nf = font7.render("DOCK-7 EXCHANGE", True,
                       (225, 65, 225) if sign_flicker else (60, 20, 55))
    surface.blit(nf, (sign.centerx - nf.get_width()//2, sign.centery - nf.get_height()//2))


def _backdrop_insurance_adjuster(surface, inner, t):
    """Sterile Nova Soma claims office — cubicle hell, ancient terminal, dead plant."""
    cx = inner.centerx
    font6 = pygame.font.SysFont("monospace", 6, bold=True)
    font7 = pygame.font.SysFont("monospace", 7)

    # ── Ceiling tile grid (fluorescent office look) ───────────────────────────
    flick_off = 0.90 + 0.10 * math.sin(t * 4.8)
    for x in range(inner.left + 4, inner.right - 4, 18):
        pygame.draw.line(surface, (int(18 * flick_off), int(20 * flick_off), int(22 * flick_off)),
                         (x, inner.top + 2), (x, inner.top + 30), 1)
    for y in range(inner.top + 2, inner.top + 30, 14):
        pygame.draw.line(surface, (int(18 * flick_off), int(20 * flick_off), int(22 * flick_off)),
                         (inner.left + 4, y), (inner.right - 4, y), 1)
    # Fluorescent tube
    pygame.draw.rect(surface, (int(170 * flick_off), int(165 * flick_off), int(90 * flick_off)),
                     (cx - 30, inner.top + 2, 60, 3))

    # ── Cubicle partition divider left ────────────────────────────────────────
    part_x = inner.left + 22
    pygame.draw.rect(surface, (34, 32, 28), (inner.left, inner.top + 30, part_x - inner.left, inner.height - 30))
    pygame.draw.line(surface, (65, 60, 40), (part_x, inner.top + 30), (part_x, inner.bottom), 2)
    # Cubicle fabric texture — horizontal lines
    for hy in range(inner.top + 34, inner.bottom - 2, 4):
        pygame.draw.line(surface, (40, 37, 32), (inner.left, hy), (part_x - 2, hy), 1)

    # ── Desk buried under stacked form papers ─────────────────────────────────
    desk_y = inner.bottom - 30
    pygame.draw.rect(surface, (38, 34, 18), (part_x + 2, desk_y, inner.width - part_x + inner.left - 4, 8))
    pygame.draw.line(surface, (75, 68, 32),
                     (part_x + 2, desk_y), (inner.right - 2, desk_y), 1)
    # Stacks of form paper (many layers)
    for stack_i in range(18):
        py_stack = desk_y - 4 - stack_i * 3
        off_stack = ((stack_i * 9) % 7) - 3
        shade_s = 52 + (stack_i % 5) * 5
        pygame.draw.rect(surface, (shade_s, shade_s - 4, shade_s // 2),
                         (part_x + 6 + off_stack, py_stack, 48, 3))
        pygame.draw.rect(surface, (100, 95, 50),
                         (part_x + 6 + off_stack, py_stack, 48, 3), 1)
        # Some sheets have visible text lines
        if stack_i % 4 == 0:
            for li in range(2):
                pygame.draw.line(surface, (80, 76, 40),
                                 (part_x + 9 + off_stack, py_stack + li + 1),
                                 (part_x + 42 + off_stack, py_stack + li + 1), 1)

    # ── CLAIM-7 ancient green-screen terminal ─────────────────────────────────
    term_x = part_x + 6
    term_y = inner.top + 32
    term_w, term_h = 50, 36
    pygame.draw.rect(surface, (4, 14, 5), (term_x, term_y, term_w, term_h))
    pygame.draw.rect(surface, (30, 70, 35), (term_x, term_y, term_w, term_h), 2)
    # CRT scanlines
    for sl in range(term_y + 2, term_y + term_h - 2, 3):
        pygame.draw.line(surface, (6, 18, 7), (term_x + 2, sl), (term_x + term_w - 2, sl), 1)
    # Green screen text lines
    term_lines = ["CLAIM-7 v2.1", "> CASE#47821", "STATUS: PEND",
                  "ADJUSTER: MW", "OUTCOME: TBD"]
    for li, ll in enumerate(term_lines):
        lc = (0, 200, 70) if li < 2 else (0, 130, 45)
        ll_surf = font6.render(ll, True, lc)
        surface.blit(ll_surf, (term_x + 3, term_y + 3 + li * 6))
    # Blinking cursor
    if (int(t * 2) % 2 == 0):
        pygame.draw.rect(surface, (0, 200, 70), (term_x + 3, term_y + 3 + 5 * 6, 5, 5))

    # ── Motivational poster on cubicle wall ───────────────────────────────────
    post_x, post_y = inner.right - 54, inner.top + 32
    pygame.draw.rect(surface, (28, 26, 18), (post_x, post_y, 48, 30))
    pygame.draw.rect(surface, (80, 74, 40), (post_x, post_y, 48, 30), 1)
    # Poster content
    p1 = font6.render("EVERY CLAIM", True, (90, 85, 45))
    p2 = font6.render("IS A NEW", True, (90, 85, 45))
    p3 = font6.render("BEGINNING", True, (90, 85, 45))
    surface.blit(p1, (post_x + 24 - p1.get_width()//2, post_y + 4))
    surface.blit(p2, (post_x + 24 - p2.get_width()//2, post_y + 12))
    surface.blit(p3, (post_x + 24 - p3.get_width()//2, post_y + 20))

    # ── Gerald's door in background with nameplate ────────────────────────────
    door_x, door_y = inner.right - 26, inner.top + 34
    pygame.draw.rect(surface, (32, 28, 16), (door_x, door_y, 18, 40))
    pygame.draw.rect(surface, (62, 54, 28), (door_x, door_y, 18, 40), 1)
    # Door knob
    pygame.draw.circle(surface, (100, 80, 30), (door_x + 3, door_y + 22), 2)
    # Nameplate
    np_rect = pygame.Rect(door_x, door_y + 2, 18, 8)
    pygame.draw.rect(surface, (70, 60, 22), np_rect)
    pygame.draw.rect(surface, (120, 100, 38), np_rect, 1)
    gn = font6.render("GRTLD", True, (100, 85, 28))
    surface.blit(gn, (np_rect.centerx - gn.get_width()//2, np_rect.top + 1))

    # ── Sad potted plant, corner ──────────────────────────────────────────────
    plant_x = inner.left + 6
    plant_y = inner.bottom - 28
    pot = pygame.Rect(plant_x - 8, plant_y + 10, 16, 12)
    pygame.draw.rect(surface, (55, 28, 8), pot)
    pygame.draw.rect(surface, (28, 12, 0), pot, 1)
    # Drooping yellowed leaves
    pygame.draw.line(surface, (55, 80, 22), (plant_x - 3, plant_y + 10), (plant_x - 14, plant_y + 18), 2)
    pygame.draw.line(surface, (55, 80, 22), (plant_x + 3, plant_y + 10), (plant_x + 14, plant_y + 18), 2)
    pygame.draw.line(surface, (68, 88, 30), (plant_x, plant_y + 10), (plant_x, plant_y + 2), 2)
    # One dead leaf (brown)
    pygame.draw.line(surface, (80, 50, 10), (plant_x - 2, plant_y + 10), (plant_x - 10, plant_y + 22), 2)

    # ── Office floor / baseboard ───────────────────────────────────────────────
    pygame.draw.rect(surface, (28, 26, 20), (inner.left, inner.bottom - 6, inner.width, 6))
    pygame.draw.line(surface, (55, 50, 32), (inner.left, inner.bottom - 6), (inner.right, inner.bottom - 6), 1)


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
