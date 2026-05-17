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
}


def draw_portrait(surface: pygame.Surface, npc_name: str,
                  rect: pygame.Rect, disposition: int = 0, t: float = 0.0):
    key = _NAME_TO_KEY.get(npc_name.upper(), "unknown")
    fn  = _DISPATCH.get(key, _unknown)
    cx  = rect.centerx
    cy  = rect.top + int(rect.height * 0.40)
    scale = min(rect.width, rect.height * 0.65) / 200.0
    fn(surface, cx, cy, scale, disposition, t)


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
    "gary":             _gary,
    "synthetic_droid":  _synthetic_droid,
    "union_dispatcher": _union_dispatcher,
    "kress":            _kress,
    "unknown":          _unknown,
}
