"""
Procedural vector portraits for terminal NPCs.
All geometry uses pygame.draw — no sprites.
"""
from __future__ import annotations
import math
import random
import pygame
from config import settings as S
from core.text import get_font

_NAME_TO_KEY = {
    "GARY":                    "gary",
    "TK-9":                    "synthetic_droid",
    "DISPATCHER":              "union_dispatcher",
    "KRESS":                   "kress",
    "MORWENNA":                "insurance_adjuster",
    "SANDRA":                  "sandra",
    "KRELLBORN":               "pirate",
    "MARROW":                  "underground_dj",
    "TOLL AUTHORITY":          "toll_authority",
    "RELAY-7 FELIX":           "nervous_fence",
    "INSPECTOR HOLT":          "cargo_inspector",
    "DRAY":                    "dray",
    "NOVA SOMA COLLECTIONS":   "nova_soma_collections",
    "MIRA VOSS":               "mira_voss",
    "EDMUND":                  "idealist_rep",
    "VINCE":                   "corrupt_rep",
    # J.3.1 — Ch5/6 climax + Marrow aftermath. Use the generic face geometry
    # (no bespoke portrait yet) but give each a distinct CRT accent + named bezel.
    "CHEN":                    "chen",
    "BOWEN":                   "bowen",
    "FREQUENCY LOST":          "lost_frequency",
}

_REACTION_ACCENTS = {
    "gary": (255, 170, 34),
    "synthetic_droid": (0, 230, 210),
    "union_dispatcher": (210, 165, 55),
    "kress": (0, 190, 110),
    "insurance_adjuster": (230, 210, 120),
    "sandra": (90, 235, 130),
    "pirate": (230, 70, 50),
    "underground_dj": (180, 80, 235),
    "toll_authority": (220, 170, 40),
    "nervous_fence": (0, 210, 135),
    "cargo_inspector": (0, 190, 125),
    "dray": (160, 210, 130),
    "nova_soma_collections": (100, 230, 215),
    "mira_voss": (240, 140, 50),
    "idealist_rep": (200, 220, 80),    # earnest gold-green
    "corrupt_rep":  (220, 90, 60),     # opportunistic rust-orange
    "chen":         (150, 130, 235),   # architect — cold violet
    "bowen":        (120, 210, 225),   # sterile corporate cyan
    "lost_frequency": (120, 110, 140), # dead-static grey-violet
    "unknown": S.AMBER_TERM,
}

_FREEZE_REACTIONS = {"exploit", "paradox", "impound", "abort"}


def draw_portrait(surface: pygame.Surface, npc_name: str,
                  rect: pygame.Rect, disposition: int = 0, t: float = 0.0,
                  reaction: str = "", reaction_age: float = 0.0,
                  frozen_t: float | None = None, outcome: str = ""):
    """
    Renders a CRT video-call portrait inside `rect`.

    Layers (back to front):
      1. CRT bezel hardware + signal strip
      2. Scene backdrop (environment behind the NPC)
      3. NPC vector portrait
      4. Disposition-driven glitch overlay
    """
    key = _NAME_TO_KEY.get(npc_name.upper(), "unknown")
    reaction = reaction or outcome or ""
    draw_disp = _reaction_disposition(disposition, reaction)
    inner = _draw_crt_bezel(surface, rect, npc_name, t, draw_disp)

    backdrop = _BACKDROPS.get(key)
    if backdrop is not None:
        prev_clip = surface.get_clip()
        surface.set_clip(inner)
        layer = pygame.Surface((inner.w, inner.h), pygame.SRCALPHA)
        local = pygame.Rect(0, 0, inner.w, inner.h)
        layer.fill((4, 10, 6, 255))
        backdrop(layer, local, t)
        _draw_ambient_backdrop_life(layer, local, key, t)
        sway_x = int(math.sin(t * 0.41 + len(key)) * 1.3)
        sway_y = int(math.sin(t * 0.33 + len(key) * 0.7) * 1.1)
        surface.blit(layer, (inner.left + sway_x, inner.top + sway_y))
        surface.set_clip(prev_clip)

    fn    = _DISPATCH.get(key, _unknown)
    shake_x, shake_y = _portrait_shake(reaction, reaction_age, t)
    cx    = inner.centerx + shake_x
    cy    = inner.top + int(inner.height * 0.46) + shake_y
    scale = min(inner.width, inner.height * 0.65) / 200.0
    portrait_t = frozen_t if (frozen_t is not None and reaction in _FREEZE_REACTIONS) else t
    fn(surface, cx, cy, scale, draw_disp, portrait_t)

    _draw_reaction_overlay(surface, inner, key, reaction, reaction_age, t)
    _draw_signal_overlay(surface, inner, t, draw_disp)


def _reaction_disposition(disposition: int, reaction: str) -> int:
    if reaction in ("friendly", "release"):
        return max(4, disposition + 3)
    if reaction == "annoyed":
        return min(-3, disposition - 2)
    if reaction in ("furious", "impound", "abort"):
        return min(-7, disposition - 5)
    if reaction == "exploit":
        return min(-6, disposition - 4)
    if reaction == "paradox":
        return -10
    return disposition


def _portrait_shake(reaction: str, age: float, t: float) -> tuple[int, int]:
    if reaction == "furious" and age < 0.30:
        return int(math.sin(t * 90.0) * 3), int(math.cos(t * 84.0) * 2)
    if reaction in ("impound", "abort") and age < 0.70:
        return int(math.sin(t * 70.0) * 4), int(math.sin(t * 57.0) * 2)
    if reaction == "paradox":
        return int(math.sin(t * 31.0) * 2), int(math.cos(t * 29.0) * 2)
    return 0, 0


def _draw_ambient_backdrop_life(surface: pygame.Surface, inner: pygame.Rect,
                                key: str, t: float) -> None:
    accent = _REACTION_ACCENTS.get(key, S.AMBER_TERM)
    rng = random.Random(key)

    # Two distant passersby, low-alpha and behind the bust.
    for idx in range(2):
        speed = 11 + idx * 7 + (len(key) % 5)
        phase = (t * speed + rng.randint(0, inner.w)) % (inner.w + 44)
        x = inner.left - 22 + int(phase)
        y = inner.bottom - 38 - idx * 12
        col = (18 + idx * 8, 22 + idx * 6, 18 + idx * 5)
        pygame.draw.circle(surface, col, (x, y - 9), 4)
        pygame.draw.line(surface, col, (x, y - 5), (x, y + 8), 3)
        pygame.draw.line(surface, col, (x - 5, y), (x + 5, y + 2), 2)

    # Dust/data motes drifting upward. Stable seed per NPC keeps it calm.
    for idx in range(18):
        base_x = rng.randint(inner.left + 2, inner.right - 3)
        base_y = rng.randint(inner.top + 10, inner.bottom - 10)
        x = inner.left + ((base_x - inner.left + int(t * (idx % 5 + 1))) % inner.w)
        y = inner.top + ((base_y - inner.top - int(t * (idx % 4 + 1) * 0.6)) % inner.h)
        a = 45 + int(25 * math.sin(t * 1.5 + idx))
        pygame.draw.circle(surface, (*accent, max(12, a)), (x, y), 1)

    # Small live readout flicker, different position from the main face.
    readout = pygame.Rect(inner.right - 44, inner.bottom - 24, 36, 12)
    pulse = 0.55 + 0.45 * math.sin(t * 3.7 + len(key))
    pygame.draw.rect(surface, (3, 12, 8, 150), readout)
    pygame.draw.rect(surface, (*accent, int(45 + 70 * pulse)), readout, 1)
    for row in range(2):
        width = int(8 + ((t * 9 + row * 13 + len(key)) % 20))
        pygame.draw.line(surface, (*accent, 90),
                         (readout.left + 4, readout.top + 4 + row * 5),
                         (readout.left + 4 + width, readout.top + 4 + row * 5), 1)


def _draw_reaction_overlay(surface: pygame.Surface, inner: pygame.Rect,
                           key: str, reaction: str, age: float, t: float) -> None:
    if not reaction:
        return
    accent = _REACTION_ACCENTS.get(key, S.AMBER_TERM)
    layer = pygame.Surface((inner.w, inner.h), pygame.SRCALPHA)

    if reaction in ("friendly", "release"):
        strength = max(0.0, 1.0 - age / 1.2) if reaction == "friendly" else 0.7
        pygame.draw.rect(layer, (*accent, int(35 + 45 * strength)), layer.get_rect(), 2)
        pygame.draw.ellipse(layer, (*accent, int(28 * strength)),
                            pygame.Rect(18, 22, inner.w - 36, inner.h - 48), 2)
    elif reaction == "annoyed":
        layer.fill((0, 0, 0, 38))
        for y in range(0, inner.h, 7):
            pygame.draw.line(layer, (255, 80, 30, 28), (0, y), (inner.w, y), 1)
    elif reaction in ("furious", "impound", "abort"):
        layer.fill((45, 0, 0, 74))
        for y in range(0, inner.h, 9):
            off = int(math.sin(t * 16.0 + y) * 5)
            pygame.draw.line(layer, (255, 35, 35, 88), (off, y), (inner.w + off, y), 2)
    elif reaction == "exploit":
        layer.fill((0, 38, 50, 44))
        rng = random.Random(int(t * 10))
        for _ in range(7):
            y = rng.randrange(0, max(1, inner.h - 4))
            x = rng.randrange(-16, 17)
            pygame.draw.rect(layer, (0, 230, 255, 95), (x, y, inner.w, rng.randrange(2, 5)))
    elif reaction == "paradox":
        layer.fill((35, 0, 45, 58))
        rng = random.Random(int(t * 22))
        for _ in range(12):
            y = rng.randrange(0, max(1, inner.h - 3))
            h = rng.randrange(1, 6)
            x = rng.randrange(-24, 25)
            col = rng.choice([(255, 40, 220, 120), (0, 240, 255, 105), (255, 255, 255, 80)])
            pygame.draw.rect(layer, col, (x, y, inner.w, h))

    surface.blit(layer, inner.topleft)


# ---------------------------------------------------------------------------
# CRT bezel + signal overlay (universal hardware framing)
# ---------------------------------------------------------------------------

def _draw_crt_bezel(surface: pygame.Surface, rect: pygame.Rect,
                    npc_name: str, t: float, disposition: int) -> pygame.Rect:
    """Draws a chunky CRT bezel around `rect`, returns the inner usable area."""
    pulse = 0.5 + 0.5 * math.sin(t * 2.1)
    # Outer plastic — warm industrial
    pygame.draw.rect(surface, (28, 18, 8), rect)
    pygame.draw.rect(surface, (int(200 + 55 * pulse), int(120 + 40 * pulse), 20), rect, 3)
    # Recessed bezel ring
    pygame.draw.rect(surface, (60, 40, 12), rect.inflate(-2, -2), 2)

    # Inner CRT face — green phosphor glow
    bezel = 6
    crt_outer = rect.inflate(-bezel * 2, -bezel * 2)
    pygame.draw.rect(surface, (4, 12, 6), crt_outer)
    glow = pygame.Surface((crt_outer.w, crt_outer.h), pygame.SRCALPHA)
    glow.fill((0, 80, 40, int(30 + 25 * pulse)))
    surface.blit(glow, crt_outer.topleft)
    pygame.draw.rect(surface, (0, 255, 140), crt_outer, 1)
    pygame.draw.rect(surface, (255, 180, 60), crt_outer.inflate(-2, -2), 1)
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
    font = get_font(8, bold=True)
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
    """Disposition-tied glitch effect — alive phosphor when calm, broken when angry."""
    if disposition >= 0:
        shimmer = pygame.Surface((inner.w, inner.h), pygame.SRCALPHA)
        for y in range(0, inner.h, 6):
            a = int(12 + 10 * abs(math.sin(t * 2.5 + y * 0.08)))
            pygame.draw.line(shimmer, (0, 255, 140, a), (0, y), (inner.w, y))
        surface.blit(shimmer, inner.topleft)
        if disposition < 3:
            return

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
    font = get_font(max(7, int(7 * s)))
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
        font = get_font(max(8, int(8 * s)))
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
    font = get_font(max(9, int(10 * s)))
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
    font = get_font(max(12, int(38 * s)))
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
    font6  = get_font(6, bold=True)
    font7  = get_font(7)
    font8  = get_font(8, bold=True)

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
    pygame.draw.rect(surface, (12, 4, 28), vp)
    pygame.draw.rect(surface, (255, 160, 40), vp, 2)
    pygame.draw.rect(surface, (0, 255, 180), vp.inflate(-6, -6), 1)
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
    font6 = get_font(6, bold=True)
    font7 = get_font(7)

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
    font6 = get_font(6, bold=True)
    font7 = get_font(7)

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
    font6 = get_font(6, bold=True)
    font7 = get_font(7)

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
    font6 = get_font(6, bold=True)
    font7 = get_font(7)

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
    """High-spec courier cockpit — clean, green, perfect. Annoyingly good."""
    cx = inner.centerx
    font6 = get_font(6, bold=True)
    font7 = get_font(7)

    # ── Clean hull panelling — tight seams ────────────────────────────────────
    for i in range(4):
        y = inner.top + 8 + i * 12
        pygame.draw.line(surface, (20, 24, 18), (inner.left, y), (inner.right, y), 1)
    for x_off in (20, 40, inner.width - 40, inner.width - 20):
        pygame.draw.line(surface, (16, 20, 14), (inner.left + x_off, inner.top),
                         (inner.left + x_off, inner.bottom), 1)

    # ── Clean viewport — bright clean stars ───────────────────────────────────
    vp = pygame.Rect(cx - 40, inner.top + 4, 80, 44)
    pygame.draw.rect(surface, (3, 5, 8), vp)
    pygame.draw.rect(surface, (55, 110, 65), vp, 2)
    # Frame cross-bars (clean lines, green tint)
    pygame.draw.line(surface, (35, 75, 45), (vp.left, vp.centery), (vp.right, vp.centery), 1)
    pygame.draw.line(surface, (35, 75, 45), (vp.centerx, vp.top), (vp.centerx, vp.bottom), 1)
    rng_s = random.Random(55)
    for _ in range(20):
        sx = rng_s.randint(vp.left + 3, vp.right - 3)
        sy = rng_s.randint(vp.top + 3, vp.bottom - 3)
        sc = rng_s.choice([(100, 140, 120), (80, 120, 100), (140, 180, 150)])
        pygame.draw.circle(surface, sc, (sx, sy), 1)
    # A distant clean waypoint marker in view
    pygame.draw.rect(surface, (40, 200, 80), (vp.centerx + 8, vp.centery - 5, 6, 6), 1)
    pygame.draw.line(surface, (40, 200, 80),
                     (vp.centerx + 12, vp.centery - 9), (vp.centerx + 12, vp.centery - 14), 1)

    # ── Multiple HUD monitor panels — all showing green (nominal) ─────────────
    screen_defs = [
        (inner.left + 4,  inner.top + 52, 44, 28, "NAV",    True),
        (inner.left + 52, inner.top + 52, 44, 28, "HULL",   True),
        (cx - 18,         inner.top + 52, 44, 28, "THRUST", True),
        (inner.right - 48, inner.top + 52, 44, 28, "COMMS",  True),
    ]
    for mx, my, mw, mh, label, nominal in screen_defs:
        pygame.draw.rect(surface, (4, 14, 5), (mx, my, mw, mh))
        pygame.draw.rect(surface, (40, 130, 52), (mx, my, mw, mh), 1)
        for sl in range(my + 2, my + mh - 1, 3):
            pygame.draw.line(surface, (6, 18, 7), (mx+1, sl), (mx+mw-2, sl), 1)
        # Header strip
        pygame.draw.rect(surface, (8, 30, 12), (mx, my, mw, 8))
        lbl = font6.render(label, True, (55, 190, 75))
        surface.blit(lbl, (mx + mw//2 - lbl.get_width()//2, my + 1))
        # Green bar — all full (nominal)
        pygame.draw.rect(surface, (0, 190, 65), (mx + 3, my + 10, mw - 6, 4))
        # "OK" or metric
        ok_lbl = font6.render("100%  OK", True, (0, 200, 70))
        surface.blit(ok_lbl, (mx + mw//2 - ok_lbl.get_width()//2, my + 18))

    # ── VEGA-MARSH callsign — bright amber ────────────────────────────────────
    cs_lbl = font7.render("VEGA-MARSH", True, (255, 176, 0))
    surface.blit(cs_lbl, (cx - cs_lbl.get_width()//2, inner.top + 84))

    # ── Trophy/plaque on right wall ───────────────────────────────────────────
    plaque = pygame.Rect(inner.right - 54, inner.top + 4, 50, 44)
    pygame.draw.rect(surface, (55, 46, 12), plaque)
    pygame.draw.rect(surface, (210, 170, 42), plaque, 2)
    # Trophy chevron shape
    tphx = plaque.centerx
    tphy = plaque.top + 10
    trophy_pts = [(tphx - 8, tphy + 18), (tphx - 5, tphy + 8), (tphx, tphy + 2),
                  (tphx + 5, tphy + 8), (tphx + 8, tphy + 18)]
    pygame.draw.lines(surface, (220, 180, 50), False, trophy_pts, 2)
    pygame.draw.line(surface, (210, 170, 42), (tphx - 5, tphy + 18), (tphx + 5, tphy + 18), 2)
    # Plaque text
    p1 = font6.render("ELITE COURIER", True, (220, 175, 40))
    surface.blit(p1, (plaque.centerx - p1.get_width()//2, plaque.top + 30))
    p2 = font6.render("ZERO FAILS", True, (180, 140, 28))
    surface.blit(p2, (plaque.centerx - p2.get_width()//2, plaque.top + 38))

    # ── Run statistics panel ──────────────────────────────────────────────────
    stat_x, stat_y = inner.left + 4, inner.top + 4
    stat_w, stat_h = 58, 44
    pygame.draw.rect(surface, (5, 18, 8), (stat_x, stat_y, stat_w, stat_h))
    pygame.draw.rect(surface, (40, 130, 52), (stat_x, stat_y, stat_w, stat_h), 1)
    stat_hdr = font6.render("RUN STATS", True, (55, 190, 75))
    surface.blit(stat_hdr, (stat_x + stat_w//2 - stat_hdr.get_width()//2, stat_y + 2))
    stat_lines = ["SECTORS:5/5", "CARGO:INTACT", "DEBT:CLEAR", "RATING: A+"]
    for si, sl in enumerate(stat_lines):
        slbl = font6.render(sl, True, (0, 190, 65))
        surface.blit(slbl, (stat_x + 4, stat_y + 10 + si * 8))

    # ── Comms array — antennas in corner ──────────────────────────────────────
    ant_base_x, ant_base_y = inner.right - 12, inner.bottom - 6
    for i, (adx, ady) in enumerate(((0, -40), (-8, -35), (-16, -28))):
        pygame.draw.line(surface, (40, 80, 50),
                         (ant_base_x + adx, ant_base_y),
                         (ant_base_x + adx, ant_base_y + ady), 1)
        blink_a = (int(t * (1.4 + i * 0.5) + i) % 2 == 0)
        pygame.draw.circle(surface, (0, 220, 80) if blink_a else (0, 60, 22),
                           (ant_base_x + adx, ant_base_y + ady), 2)

    # ── Quota/performance ascending bar chart ─────────────────────────────────
    chart_y0 = inner.bottom - 8
    bar_x = inner.left + 4
    for bi in range(14):
        bh = 3 + bi
        bc = (0, 160, 55) if bi < 12 else (240, 190, 50)
        pygame.draw.rect(surface, bc, (bar_x + bi * 6, chart_y0 - bh, 4, bh))
    # Chart label
    ch_lbl = font6.render("DELIVERIES", True, (0, 120, 45))
    surface.blit(ch_lbl, (bar_x, chart_y0 - 26))


def _backdrop_pirate(surface, inner, t):
    """Battered outer-belt pirate vessel — scavenged, cracked, hostile."""
    cx = inner.centerx
    font6 = get_font(6, bold=True)
    font7 = get_font(7)

    # ── Exposed hull plating — irregular dark metal ───────────────────────────
    for i in range(0, inner.width, 9):
        x = inner.left + i
        col = (32, 30, 36) if (i // 9) % 2 == 0 else (22, 20, 28)
        pygame.draw.line(surface, col, (x, inner.top), (x, inner.bottom), 1)
    # Diagonal weld marks
    for wx in range(inner.left + 10, inner.right - 5, 22):
        pygame.draw.line(surface, (48, 38, 26), (wx, inner.top + 2), (wx + 8, inner.top + 14), 1)

    # ── Cracked viewport with hand-patched welds ──────────────────────────────
    vp = pygame.Rect(cx - 36, inner.top + 4, 72, 42)
    pygame.draw.rect(surface, (3, 4, 7), vp)
    pygame.draw.rect(surface, (55, 38, 20), vp, 3)
    # Crack lines on viewport glass
    crack_pts = [(vp.left + 12, vp.top + 8), (vp.left + 22, vp.top + 20),
                 (vp.left + 18, vp.top + 36)]
    pygame.draw.lines(surface, (80, 65, 45), False, crack_pts, 1)
    crack2 = [(vp.left + 22, vp.top + 20), (vp.left + 35, vp.top + 28)]
    pygame.draw.lines(surface, (70, 55, 35), False, crack2, 1)
    # Weld patch over crack — rough blobs
    for wpx, wpy in ((vp.left + 14, vp.top + 10), (vp.left + 24, vp.top + 22)):
        pygame.draw.circle(surface, (65, 40, 18), (wpx, wpy), 3)
        pygame.draw.circle(surface, (90, 58, 24), (wpx, wpy), 3, 1)
    # Stars through viewport
    rng_pv = random.Random(77)
    for _ in range(14):
        sx = rng_pv.randint(vp.left + 3, vp.right - 3)
        sy = rng_pv.randint(vp.top + 3, vp.bottom - 3)
        pygame.draw.circle(surface, (75, 68, 88), (sx, sy), 1)
    # Outer belt asteroid visible
    ax_a, ay_a = vp.left + 48, vp.top + 22
    ast_pts = [(ax_a, ay_a - 5), (ax_a + 7, ay_a - 7), (ax_a + 11, ay_a - 2),
               (ax_a + 9, ay_a + 5), (ax_a + 2, ay_a + 6), (ax_a - 2, ay_a + 2)]
    pygame.draw.polygon(surface, (28, 24, 34), ast_pts)
    pygame.draw.polygon(surface, (58, 48, 64), ast_pts, 1)

    # ── Exposed sagging wiring — multiple cables ──────────────────────────────
    for i in range(5):
        y0 = inner.top + 50 + i * 6
        ax_w = inner.left + 4
        bx_w = inner.right - 4
        sag = 4 + (i % 3) * 3
        col_w = [(140, 55, 0), (55, 75, 85), (18, 28, 28),
                 (100, 35, 20), (40, 55, 40)][i]
        mid_w = ((ax_w + bx_w) // 2, y0 + sag)
        pygame.draw.lines(surface, col_w, False, [(ax_w, y0), mid_w, (bx_w, y0)], 2)
        # Wire fraying end
        pygame.draw.circle(surface, col_w, (bx_w, y0), 2)

    # ── Scavenged screen showing corrupt/static data ──────────────────────────
    scr_x, scr_y = inner.left + 4, inner.top + 54
    scr_w, scr_h = 52, 32
    pygame.draw.rect(surface, (8, 6, 8), (scr_x, scr_y, scr_w, scr_h))
    pygame.draw.rect(surface, (75, 55, 40), (scr_x, scr_y, scr_w, scr_h), 1)
    # Corrupt/static data lines
    rng_scr = random.Random(int(t * 3))
    for row in range(5):
        line_w = rng_scr.randint(12, scr_w - 8)
        col_c = (rng_scr.randint(40, 120), rng_scr.randint(10, 50), rng_scr.randint(0, 30))
        pygame.draw.rect(surface, col_c, (scr_x + 3, scr_y + 4 + row * 5, line_w, 3))
    # Glitch horizontal bar
    if (int(t * 4) % 7 == 0):
        glitch_y = scr_y + rng_scr.randint(2, scr_h - 4)
        pygame.draw.rect(surface, (200, 100, 40), (scr_x, glitch_y, scr_w, 3))
    # "NO SIGNAL" flicker
    if (int(t * 2.5) % 3 == 0):
        ns_lbl = font6.render("NO SIG", True, (130, 80, 30))
        surface.blit(ns_lbl, (scr_x + scr_w//2 - ns_lbl.get_width()//2, scr_y + scr_h//2 - 3))

    # ── Weapon rack — abstract tool/weapon shapes ─────────────────────────────
    rack_x, rack_y = inner.right - 48, inner.top + 50
    pygame.draw.rect(surface, (30, 26, 20), (rack_x, rack_y, 44, 54))
    pygame.draw.rect(surface, (68, 52, 32), (rack_x, rack_y, 44, 54), 1)
    # Hook bar
    pygame.draw.line(surface, (85, 65, 40), (rack_x + 4, rack_y + 8), (rack_x + 40, rack_y + 8), 1)
    # Weapon 1: long tube (plasma torch)
    pygame.draw.rect(surface, (55, 50, 58), (rack_x + 6, rack_y + 12, 32, 5))
    pygame.draw.circle(surface, (90, 80, 95), (rack_x + 38, rack_y + 14), 3)
    # Weapon 2: chunky tool
    wp2_pts = [(rack_x + 8, rack_y + 22), (rack_x + 30, rack_y + 22),
               (rack_x + 32, rack_y + 28), (rack_x + 8, rack_y + 28)]
    pygame.draw.polygon(surface, (55, 48, 52), wp2_pts)
    pygame.draw.polygon(surface, (95, 78, 62), wp2_pts, 1)
    # Weapon 3: short stocky shape
    pygame.draw.rect(surface, (46, 42, 48), (rack_x + 10, rack_y + 34, 22, 10))
    pygame.draw.rect(surface, (80, 68, 55), (rack_x + 10, rack_y + 34, 22, 10), 1)

    # ── Crude skull-and-bones geometric marker (defaced union badge) ──────────
    skull_x, skull_y = inner.left + 8, inner.bottom - 32
    # Skull outline: hexagon
    skpts = [(skull_x + int(10*math.cos(math.pi/3*i)), skull_y + int(8*math.sin(math.pi/3*i)))
             for i in range(6)]
    pygame.draw.polygon(surface, (18, 14, 14), skpts)
    pygame.draw.polygon(surface, (180, 35, 35), skpts, 1)
    # Eye holes
    pygame.draw.circle(surface, (180, 35, 35), (skull_x - 3, skull_y - 1), 2)
    pygame.draw.circle(surface, (180, 35, 35), (skull_x + 3, skull_y - 1), 2)
    # Cross-bones beneath
    pygame.draw.line(surface, (160, 28, 28), (skull_x - 8, skull_y + 9), (skull_x + 8, skull_y + 18), 2)
    pygame.draw.line(surface, (160, 28, 28), (skull_x + 8, skull_y + 9), (skull_x - 8, skull_y + 18), 2)

    # ── Torn/patched hull section left wall ───────────────────────────────────
    torn_pts = [(inner.left + 2, inner.top + 88),
                (inner.left + 14, inner.top + 80),
                (inner.left + 18, inner.top + 92),
                (inner.left + 10, inner.top + 98),
                (inner.left + 2, inner.top + 95)]
    pygame.draw.polygon(surface, (42, 36, 46), torn_pts)
    pygame.draw.polygon(surface, (80, 60, 35), torn_pts, 1)
    # Patch
    pygame.draw.rect(surface, (50, 44, 30), (inner.left + 2, inner.top + 86, 16, 12))
    pygame.draw.rect(surface, (95, 72, 42), (inner.left + 2, inner.top + 86, 16, 12), 1)
    # Rivets on patch
    for rpx, rpy in ((inner.left + 4, inner.top + 88), (inner.left + 16, inner.top + 88),
                     (inner.left + 4, inner.top + 96), (inner.left + 16, inner.top + 96)):
        pygame.draw.circle(surface, (130, 105, 60), (rpx, rpy), 1)

    # ── Defaced union flag ────────────────────────────────────────────────────
    flag = pygame.Rect(cx - 14, inner.bottom - 28, 28, 18)
    pygame.draw.rect(surface, (16, 8, 0), flag)
    pygame.draw.rect(surface, (100, 60, 0), flag, 1)
    ff = font6.render("404", True, (160, 120, 30))
    surface.blit(ff, (flag.centerx - ff.get_width()//2, flag.centery - ff.get_height()//2))
    pygame.draw.line(surface, (230, 30, 30), (flag.left, flag.top), (flag.right, flag.bottom), 2)
    pygame.draw.line(surface, (230, 30, 30), (flag.left, flag.bottom), (flag.right, flag.top), 2)


def _backdrop_underground_dj(surface, inner, t):
    """Cramped pirate radio broadcast booth — reel-to-reel, vinyl, contraband freq."""
    cx = inner.centerx
    font6 = get_font(6, bold=True)
    font7 = get_font(7)

    # ── Acoustic foam panels on walls — grid of small squares ────────────────
    foam_col = (22, 20, 24)
    foam_edge = (34, 30, 38)
    for fy in range(inner.top, inner.bottom, 9):
        for fx in range(inner.left, inner.right, 9):
            pygame.draw.rect(surface, foam_col, (fx, fy, 8, 8))
            pygame.draw.rect(surface, foam_edge, (fx, fy, 8, 8), 1)

    # ── ON AIR sign — pulsing red ─────────────────────────────────────────────
    glow_pulse = 0.55 + 0.45 * math.sin(t * 2.2)
    sign = pygame.Rect(cx - 30, inner.top + 4, 60, 18)
    pygame.draw.rect(surface, (18, 0, 0), sign)
    pygame.draw.rect(surface, (int(230 * glow_pulse + 25), 28, 28), sign, 2)
    # Glow halo
    glow_s = pygame.Surface((70, 26), pygame.SRCALPHA)
    pygame.draw.rect(glow_s, (220, 30, 30, int(50 * glow_pulse)), (0, 0, 70, 26))
    surface.blit(glow_s, (cx - 35, inner.top + 1))
    font8b = get_font(9, bold=True)
    oa = font8b.render("ON AIR", True, (255, 55, 38))
    surface.blit(oa, (sign.centerx - oa.get_width()//2, sign.centery - oa.get_height()//2))

    # ── BROADCASTING LIVE indicator ────────────────────────────────────────────
    bl_blink = (int(t * 1.8) % 2 == 0)
    bl_col = (55, 220, 80) if bl_blink else (12, 55, 18)
    pygame.draw.circle(surface, bl_col, (cx + 38, inner.top + 13), 3)
    bl_lbl = font6.render("LIVE TX", True, (45, 185, 68))
    surface.blit(bl_lbl, (cx + 42, inner.top + 8))

    # ── Waveform display — animated oscilloscope ──────────────────────────────
    wave_y = inner.top + 28
    wave_pts = []
    for x in range(inner.left + 6, inner.right - 6, 2):
        amp = (5 + 4 * math.sin(t * 6.2 + x * 0.18)
               + 2 * math.sin(t * 11.4 + x * 0.07)
               + 1 * math.sin(t * 17.8 + x * 0.03))
        wave_pts.append((x, wave_y + int(amp)))
    if len(wave_pts) > 1:
        pygame.draw.lines(surface, (40, 205, 235), False, wave_pts, 1)
    # Mirror wave (ghost)
    ghost_pts = [(x, wave_y + int((wave_y - y) * 0.3 + wave_y * 0.7) - wave_y)
                 for x, y in wave_pts]
    ghost_pts2 = [(x, wave_y - int(abs(y - wave_y) * 0.5)) for x, y in wave_pts]
    if len(ghost_pts2) > 1:
        pygame.draw.lines(surface, (20, 90, 105), False, ghost_pts2, 1)

    # ── Mixing board — horizontal slider panel ────────────────────────────────
    mix_x, mix_y = inner.left + 4, inner.top + 44
    mix_w, mix_h = inner.width - 8, 24
    pygame.draw.rect(surface, (18, 14, 20), (mix_x, mix_y, mix_w, mix_h))
    pygame.draw.rect(surface, (70, 55, 80), (mix_x, mix_y, mix_w, mix_h), 1)
    # Slider channels
    n_sliders = 10
    slider_w = (mix_w - 8) // n_sliders
    for si in range(n_sliders):
        sx = mix_x + 4 + si * slider_w
        # Track
        pygame.draw.line(surface, (40, 32, 48), (sx + slider_w//2, mix_y + 3),
                         (sx + slider_w//2, mix_y + mix_h - 5), 1)
        # Fader position (animated)
        fpos = int(mix_y + 4 + 14 * (0.4 + 0.4 * math.sin(t * 0.8 + si * 0.7)))
        pygame.draw.rect(surface, (100, 80, 120), (sx + slider_w//2 - 3, fpos, 6, 4))
        pygame.draw.rect(surface, (160, 130, 180), (sx + slider_w//2 - 3, fpos, 6, 4), 1)
        # Level LED
        led_on = (fpos - (mix_y + 4)) < 9
        pygame.draw.circle(surface, (0, 200, 80) if led_on else (0, 50, 18),
                           (sx + slider_w//2, mix_y + mix_h - 3), 2)

    # ── Reel-to-reel tape machine ──────────────────────────────────────────────
    rtr_x, rtr_y = inner.right - 56, inner.top + 44
    pygame.draw.rect(surface, (20, 16, 24), (rtr_x, rtr_y, 52, 40))
    pygame.draw.rect(surface, (75, 58, 88), (rtr_x, rtr_y, 52, 40), 1)
    # Two reels
    for reel_cx_off, spin_dir in ((rtr_x + 14, 1), (rtr_x + 38, -1)):
        reel_cy = rtr_y + 18
        reel_ang = t * spin_dir * 1.8
        pygame.draw.circle(surface, (35, 28, 42), (reel_cx_off, reel_cy), 10)
        pygame.draw.circle(surface, (95, 75, 110), (reel_cx_off, reel_cy), 10, 1)
        pygame.draw.circle(surface, (60, 48, 70), (reel_cx_off, reel_cy), 5)
        # Reel spokes
        for sp in range(3):
            spang = reel_ang + sp * math.tau / 3
            pygame.draw.line(surface, (80, 62, 92),
                             (int(reel_cx_off + math.cos(spang) * 3),
                              int(reel_cy + math.sin(spang) * 3)),
                             (int(reel_cx_off + math.cos(spang) * 9),
                              int(reel_cy + math.sin(spang) * 9)), 1)
    # Tape path between reels
    pygame.draw.line(surface, (45, 35, 25), (rtr_x + 14, rtr_y + 24), (rtr_x + 38, rtr_y + 24), 1)
    # PLAY button
    play_col = (0, 200, 70) if (int(t * 0.5) % 2 == 0) else (0, 100, 35)
    pygame.draw.polygon(surface, play_col,
                        [(rtr_x + 18, rtr_y + 30), (rtr_x + 24, rtr_y + 34),
                         (rtr_x + 18, rtr_y + 38)])

    # ── Stacked vinyl record shapes ────────────────────────────────────────────
    for vi, vx_off in enumerate((inner.left + 4, inner.left + 20)):
        vy = inner.bottom - 14 - vi * 4
        pygame.draw.ellipse(surface, (22, 20, 28), (vx_off, vy - 14, 22, 4))
        pygame.draw.ellipse(surface, (65, 56, 75), (vx_off, vy - 14, 22, 4), 1)
        pygame.draw.circle(surface, (180, 100, 40), (vx_off + 11, vy - 12), 3)

    # ── Transmission antenna outside porthole ──────────────────────────────────
    port_x = inner.left + 14
    port_y = inner.top + 10
    pygame.draw.circle(surface, (4, 4, 8), (port_x, port_y), 10)
    pygame.draw.circle(surface, (70, 55, 80), (port_x, port_y), 10, 2)
    # Antenna mast
    pygame.draw.line(surface, (55, 85, 62), (port_x, port_y - 10), (port_x, port_y - 24), 1)
    for ca in (6, 14, 22):
        pygame.draw.line(surface, (42, 68, 48), (port_x - 4, port_y - ca), (port_x + 4, port_y - ca), 1)
    ant_blink2 = (int(t * 1.9) % 2 == 0)
    pygame.draw.circle(surface, (200, 55, 55) if ant_blink2 else (60, 14, 14),
                       (port_x, port_y - 24), 2)

    # ── Nova Soma frequency list — pinned paper (crossed out) ──────────────────
    freq_x, freq_y = inner.right - 44, inner.top + 68
    pygame.draw.rect(surface, (32, 30, 22), (freq_x, freq_y, 40, 30))
    pygame.draw.rect(surface, (80, 75, 45), (freq_x, freq_y, 40, 30), 1)
    # Thumb tack
    pygame.draw.circle(surface, (180, 50, 50), (freq_x + 20, freq_y), 2)
    freq_lines = ["107.4 MHz", "98.6 MHz", "112.0 MHz"]
    for fi, fl in enumerate(freq_lines):
        fl_lbl = font6.render(fl, True, (95, 90, 52))
        surface.blit(fl_lbl, (freq_x + 3, freq_y + 4 + fi * 8))
        # Strike-through all entries
        ly = freq_y + 4 + fi * 8 + 3
        pygame.draw.line(surface, (200, 35, 35),
                         (freq_x + 2, ly), (freq_x + 38, ly), 1)

    # ── Tangled cables at bottom ───────────────────────────────────────────────
    for ci in range(4):
        csx = inner.left + 8 + ci * 24
        csy = inner.bottom - 10
        cex = csx + 16 + ci * 3
        cey = inner.bottom - 4
        mid_c = ((csx + cex) // 2, csy + 6 + ci * 2)
        pygame.draw.lines(surface, [(80, 40, 80), (40, 60, 80), (80, 80, 40), (40, 80, 60)][ci],
                          False, [(csx, csy), mid_c, (cex, cey)], 2)


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


# ---------------------------------------------------------------------------
# Toll Authority — Gate Seven Checkpoint Attendant
# ---------------------------------------------------------------------------

def _backdrop_toll_authority(surface, inner, t):
    """Cramped checkpoint booth interior — harsh fluorescent strips, form stacks."""
    cx = inner.centerx
    # Back wall — grey booth panelling
    for i in range(4):
        y = inner.top + 8 + i * 15
        col = (28, 30, 28) if i % 2 == 0 else (20, 22, 20)
        pygame.draw.rect(surface, col, (inner.left, y, inner.width, 15))
    # Fluorescent strip light — flickers
    flicker = 1.0 if int(t * 7) % 17 != 0 else 0.55
    strip_col = (int(200 * flicker), int(210 * flicker), int(180 * flicker))
    pygame.draw.rect(surface, strip_col, (cx - 32, inner.top + 5, 64, 4))
    # Stack of forms on left
    for i in range(5):
        fy = inner.top + 32 + i * 3
        pygame.draw.rect(surface, (160, 148, 110), (inner.left + 6, fy, 28, 2))
    # Terminal screen glow (right side)
    scr_rect = pygame.Rect(inner.right - 40, inner.top + 20, 30, 22)
    pygame.draw.rect(surface, (20, 60, 20), scr_rect)
    pygame.draw.rect(surface, (0, 90, 40), scr_rect, 1)
    font7 = get_font(6)
    for row, txt in enumerate(["LEVY:1500", "STATUS:OK", "QUEUE:18"]):
        s = font7.render(txt, True, (0, 200, 80))
        surface.blit(s, (scr_rect.left + 2, scr_rect.top + 2 + row * 7))
    # Booth window frame
    pygame.draw.rect(surface, (60, 55, 40),
                     (inner.left, inner.top, inner.width, inner.height), 2)


def _toll_authority(surface, cx, cy, s, disposition, t):
    """
    Gate Seven attendant — bored, tired, slightly resentful.
    Uniform cap, slight bags under eyes, headset, clipboard held up.
    """
    skin  = (210, 175, 140)
    skin_d = (130, 100, 75)
    suit  = (55, 60, 50)      # grey-green Transit Authority uniform
    cap   = (40, 45, 35)
    cap_b = (70, 80, 60)
    white = (230, 230, 220)
    amber = (220, 170, 40)

    # Torso / uniform
    torso_pts = [
        (int(cx - 38 * s), int(cy + 80 * s)),
        (int(cx + 38 * s), int(cy + 80 * s)),
        (int(cx + 30 * s), int(cy + 20 * s)),
        (int(cx - 30 * s), int(cy + 20 * s)),
    ]
    pygame.draw.polygon(surface, suit, torso_pts)
    # Shoulder insignia stripe
    for side in (-1, 1):
        sx = cx + side * int(26 * s)
        pygame.draw.rect(surface, amber,
                         (sx - int(4 * s), int(cy + 25 * s), int(8 * s), int(4 * s)))

    # Neck
    pygame.draw.rect(surface, skin,
                     (cx - int(8 * s), int(cy + 10 * s), int(16 * s), int(14 * s)))

    # Head — slightly round, tired
    head_rect = pygame.Rect(cx - int(26 * s), int(cy - 42 * s),
                            int(52 * s), int(54 * s))
    pygame.draw.ellipse(surface, skin, head_rect)
    pygame.draw.ellipse(surface, skin_d, head_rect, 1)

    # Cap
    brim_y = int(cy - 42 * s)
    pygame.draw.rect(surface, cap,
                     (cx - int(30 * s), brim_y - int(18 * s),
                      int(60 * s), int(20 * s)))
    pygame.draw.rect(surface, cap_b,
                     (cx - int(32 * s), brim_y - int(3 * s),
                      int(64 * s), int(5 * s)))
    # Cap badge — small amber rectangle
    pygame.draw.rect(surface, amber,
                     (cx - int(8 * s), brim_y - int(14 * s), int(16 * s), int(8 * s)))

    # Tired eyes — slightly drooped lids
    for ex_off in (-13, 13):
        ex = cx + int(ex_off * s)
        ey = int(cy - 20 * s)
        pygame.draw.ellipse(surface, white,
                            pygame.Rect(ex - int(7 * s), ey - int(4 * s),
                                        int(14 * s), int(8 * s)))
        # Pupil — slightly unfocused, looking sideways
        pygame.draw.circle(surface, (50, 55, 45),
                           (ex + int(1 * s), ey), max(1, int(3 * s)))
        # Drooped upper lid
        pygame.draw.arc(surface, skin_d,
                        pygame.Rect(ex - int(7 * s), ey - int(4 * s),
                                    int(14 * s), int(8 * s)),
                        0, math.pi, max(1, int(2 * s)))

    # Bags under eyes
    for ex_off in (-13, 13):
        ex = cx + int(ex_off * s)
        ey = int(cy - 15 * s)
        pygame.draw.arc(surface, skin_d,
                        pygame.Rect(ex - int(8 * s), ey, int(16 * s), int(6 * s)),
                        math.pi, math.tau, 1)

    # Nose
    pygame.draw.line(surface, skin_d,
                     (cx, int(cy - 10 * s)), (cx - int(4 * s), int(cy - 2 * s)), 1)

    # Thin line of a mouth — slightly disapproving
    mouth_y = int(cy + 5 * s)
    pygame.draw.line(surface, skin_d,
                     (cx - int(10 * s), mouth_y), (cx + int(10 * s), mouth_y), 1)
    # Slight downturn at corners
    pygame.draw.line(surface, skin_d,
                     (cx - int(10 * s), mouth_y),
                     (cx - int(13 * s), mouth_y + int(3 * s)), 1)
    pygame.draw.line(surface, skin_d,
                     (cx + int(10 * s), mouth_y),
                     (cx + int(13 * s), mouth_y + int(3 * s)), 1)

    # Headset
    pygame.draw.arc(surface, (80, 85, 75),
                    pygame.Rect(cx - int(28 * s), int(cy - 40 * s),
                                int(56 * s), int(30 * s)),
                    0, math.pi, max(1, int(3 * s)))
    # Earpiece right
    pygame.draw.circle(surface, (60, 65, 55),
                       (cx + int(28 * s), int(cy - 25 * s)), max(2, int(5 * s)))
    # Mic boom
    pygame.draw.line(surface, (80, 85, 75),
                     (cx - int(28 * s), int(cy - 25 * s)),
                     (cx - int(34 * s), int(cy - 8 * s)), 1)
    pygame.draw.circle(surface, (50, 55, 45),
                       (cx - int(34 * s), int(cy - 8 * s)), max(1, int(2 * s)))

    # Clipboard held up (right arm)
    clip_x = cx + int(32 * s)
    clip_y = int(cy + 5 * s)
    pygame.draw.rect(surface, (180, 165, 120),
                     (clip_x, clip_y, int(22 * s), int(28 * s)))
    pygame.draw.rect(surface, (100, 90, 60),
                     (clip_x, clip_y, int(22 * s), int(28 * s)), 1)
    pygame.draw.rect(surface, (100, 90, 60),
                     (clip_x + int(4 * s), clip_y - int(4 * s),
                      int(14 * s), int(5 * s)))
    for row in range(4):
        pygame.draw.line(surface, (60, 55, 40),
                         (clip_x + int(3 * s), clip_y + int(4 + row * 5) * s),
                         (clip_x + int(19 * s), clip_y + int(4 + row * 5) * s), 1)

    # Disposition tint — high disp = slight smile; low = scowl
    if disposition >= 3:
        pygame.draw.arc(surface, (160, 130, 100),
                        pygame.Rect(cx - int(10 * s), mouth_y - int(4 * s),
                                    int(20 * s), int(10 * s)),
                        math.pi, math.tau, 1)
    elif disposition <= -3:
        for dx in (-14, 14):
            pygame.draw.line(surface, skin_d,
                             (cx + int(dx * s), mouth_y - int(2 * s)),
                             (cx + int((dx + 2 if dx > 0 else dx - 2) * s),
                              mouth_y + int(5 * s)), 1)


_DISPATCH["toll_authority"] = _toll_authority
_BACKDROPS["toll_authority"] = _backdrop_toll_authority


# ---------------------------------------------------------------------------
# Relay-7 Felix -- grey-market relay contact
# ---------------------------------------------------------------------------

def _backdrop_nervous_fence(surface, inner, t):
    """Bootleg relay closet: stolen route maps, cables, and half-legal gear."""
    font6 = get_font(6, bold=True)
    font7 = get_font(7)
    cx = inner.centerx

    # Patchwork wall panels
    for i in range(6):
        y = inner.top + i * 18
        col = (18, 18, 24) if i % 2 else (24, 20, 28)
        pygame.draw.rect(surface, col, (inner.left, y, inner.width, 18))
        pygame.draw.line(surface, (52, 42, 26), (inner.left, y), (inner.right, y), 1)

    # Left monitor: barge route map
    mon = pygame.Rect(inner.left + 8, inner.top + 12, 54, 42)
    pygame.draw.rect(surface, (4, 18, 14), mon)
    pygame.draw.rect(surface, (0, 180, 100), mon, 1)
    for i in range(4):
        y = mon.top + 8 + i * 8
        pygame.draw.line(surface, (0, 80, 55), (mon.left + 4, y), (mon.right - 4, y), 1)
    route = [
        (mon.left + 6, mon.bottom - 7),
        (mon.left + 19, mon.top + 26),
        (mon.left + 34, mon.top + 18),
        (mon.right - 7, mon.top + 9),
    ]
    pygame.draw.lines(surface, (0, 245, 150), False, route, 1)
    blip_x = route[1][0] + int(math.sin(t * 4.0) * 3)
    pygame.draw.circle(surface, (255, 190, 40), (blip_x, route[1][1]), 2)
    tag = font6.render("404 ROUTES", True, (0, 210, 120))
    surface.blit(tag, (mon.left + 3, mon.top + 2))

    # Right monitor: legitimacy plan
    plan = pygame.Rect(inner.right - 58, inner.top + 16, 48, 48)
    pygame.draw.rect(surface, (22, 14, 8), plan)
    pygame.draw.rect(surface, (170, 110, 35), plan, 1)
    for row, txt in enumerate(["LLC?", "TAX ID", "NO CRIME", "LOGO"]):
        line = font7.render(txt, True, (210, 155, 70))
        surface.blit(line, (plan.left + 4, plan.top + 5 + row * 9))
    pygame.draw.line(surface, (210, 45, 45),
                     (plan.left + 4, plan.top + 24),
                     (plan.right - 4, plan.top + 24), 1)

    # Cable mess and signal lights
    for i in range(7):
        x0 = inner.left + 6 + i * 18
        y0 = inner.bottom - 12
        x1 = inner.left + 20 + i * 15
        y1 = inner.bottom - 3
        mid = ((x0 + x1) // 2, y0 - 6 + int(math.sin(t * 1.4 + i) * 2))
        col = [(80, 40, 120), (30, 95, 90), (130, 90, 30)][i % 3]
        pygame.draw.lines(surface, col, False, [(x0, y0), mid, (x1, y1)], 1)
    for i in range(5):
        lx = cx - 28 + i * 14
        ly = inner.top + 72
        on = int(t * (2 + i)) % 3 != 0
        pygame.draw.circle(surface, (0, 220, 120) if on else (25, 55, 40), (lx, ly), 2)

    # Handwritten sign
    sign = pygame.Rect(cx - 34, inner.top + 4, 68, 10)
    pygame.draw.rect(surface, (80, 62, 36), sign)
    pygame.draw.rect(surface, (140, 110, 64), sign, 1)
    lbl = font6.render("LEGIT SOON", True, (235, 210, 140))
    surface.blit(lbl, (sign.centerx - lbl.get_width() // 2, sign.top + 2))


def _nervous_fence(surface, cx, cy, s, disposition, t):
    """Felix: anxious relay broker, oversized headset, always almost caught."""
    skin = (205, 168, 125)
    skin_d = (110, 76, 42)
    hair = (50, 35, 22)
    jacket = (44, 52, 60)
    accent = (0, 210, 135)
    amber = (230, 165, 45)

    # Hunched shoulders and patched vest
    shoulders = [
        (int(cx - 44 * s), int(cy + 68 * s)),
        (int(cx + 44 * s), int(cy + 68 * s)),
        (int(cx + 34 * s), int(cy + 28 * s)),
        (int(cx - 34 * s), int(cy + 28 * s)),
    ]
    pygame.draw.polygon(surface, jacket, shoulders)
    pygame.draw.polygon(surface, (95, 115, 115), shoulders, 1)
    pygame.draw.rect(surface, (70, 40, 30),
                     (int(cx - 30 * s), int(cy + 42 * s), int(18 * s), int(14 * s)))
    pygame.draw.rect(surface, amber,
                     (int(cx + 14 * s), int(cy + 38 * s), int(18 * s), int(8 * s)), 1)

    # Neck
    pygame.draw.rect(surface, skin_d,
                     (int(cx - 9 * s), int(cy + 18 * s), int(18 * s), int(17 * s)))

    # Head: narrow, nervous
    head = [
        (int(cx - 26 * s), int(cy - 30 * s)),
        (int(cx - 12 * s), int(cy - 43 * s)),
        (int(cx + 14 * s), int(cy - 40 * s)),
        (int(cx + 27 * s), int(cy - 24 * s)),
        (int(cx + 24 * s), int(cy + 5 * s)),
        (int(cx + 10 * s), int(cy + 24 * s)),
        (int(cx - 10 * s), int(cy + 24 * s)),
        (int(cx - 24 * s), int(cy + 8 * s)),
    ]
    pygame.draw.polygon(surface, skin, head)
    pygame.draw.polygon(surface, skin_d, head, 1)

    # Messy hair
    hair_pts = [
        (int(cx - 24 * s), int(cy - 29 * s)),
        (int(cx - 10 * s), int(cy - 44 * s)),
        (int(cx + 10 * s), int(cy - 42 * s)),
        (int(cx + 25 * s), int(cy - 25 * s)),
        (int(cx + 12 * s), int(cy - 31 * s)),
        (int(cx + 3 * s), int(cy - 24 * s)),
        (int(cx - 7 * s), int(cy - 32 * s)),
    ]
    pygame.draw.polygon(surface, hair, hair_pts)
    pygame.draw.polygon(surface, (20, 12, 8), hair_pts, 1)
    for spike in (-17, -5, 8):
        pygame.draw.line(surface, hair,
                         (int(cx + spike * s), int(cy - 36 * s)),
                         (int(cx + (spike - 5) * s), int(cy - 48 * s)), 2)

    # Oversized headset
    pygame.draw.arc(surface, (80, 95, 100),
                    pygame.Rect(int(cx - 34 * s), int(cy - 48 * s),
                                int(68 * s), int(44 * s)),
                    0, math.pi, max(1, int(3 * s)))
    for side in (-1, 1):
        cup = (int(cx + side * 27 * s), int(cy - 12 * s))
        pygame.draw.circle(surface, (20, 34, 34), cup, max(4, int(8 * s)))
        pygame.draw.circle(surface, accent, cup, max(4, int(8 * s)), 1)
    pygame.draw.line(surface, (80, 95, 100),
                     (int(cx + 27 * s), int(cy - 10 * s)),
                     (int(cx + 18 * s), int(cy + 8 * s)), 2)
    pygame.draw.circle(surface, accent, (int(cx + 18 * s), int(cy + 8 * s)), 2)

    # Wide anxious eyes
    eye_y = int(cy - 12 * s)
    for ex in (-10, 12):
        pygame.draw.ellipse(surface, (232, 240, 225),
                            pygame.Rect(int(cx + ex * s - 6 * s), eye_y - int(5 * s),
                                        int(12 * s), int(9 * s)))
        pygame.draw.circle(surface, (15, 45, 35),
                           (int(cx + ex * s + math.sin(t * 3.0) * 1), eye_y), 2)
    # Brows lifted in panic
    pygame.draw.line(surface, hair,
                     (int(cx - 18 * s), int(cy - 24 * s)),
                     (int(cx - 5 * s), int(cy - 28 * s)), 2)
    pygame.draw.line(surface, hair,
                     (int(cx + 5 * s), int(cy - 27 * s)),
                     (int(cx + 20 * s), int(cy - 22 * s)), 2)

    # Nose and mouth
    pygame.draw.line(surface, skin_d,
                     (int(cx + 2 * s), int(cy - 6 * s)),
                     (int(cx - 2 * s), int(cy + 5 * s)), 1)
    mouth_y = int(cy + 15 * s)
    if disposition >= 2:
        pygame.draw.arc(surface, skin_d,
                        pygame.Rect(int(cx - 9 * s), mouth_y - int(7 * s),
                                    int(18 * s), int(12 * s)),
                        0, math.pi, 1)
    else:
        pygame.draw.line(surface, skin_d,
                         (int(cx - 8 * s), mouth_y),
                         (int(cx + 8 * s), mouth_y + int(2 * s)), 1)

    # Sweat bead / relay badge
    if disposition <= 0 or int(t * 2.0) % 2 == 0:
        pygame.draw.circle(surface, (90, 210, 235),
                           (int(cx + 22 * s), int(cy - 4 * s)), max(1, int(2 * s)))
    badge = pygame.Rect(int(cx - 7 * s), int(cy + 45 * s), int(14 * s), int(10 * s))
    pygame.draw.rect(surface, (10, 30, 24), badge)
    pygame.draw.rect(surface, accent, badge, 1)


# ---------------------------------------------------------------------------
# Inspector Holt -- Sector Transit Authority manifest checker
# ---------------------------------------------------------------------------

def _backdrop_cargo_inspector(surface, inner, t):
    """Sterile STA checkpoint office: scanner arch, forms, and manifest board."""
    font6 = get_font(6, bold=True)
    font7 = get_font(7)
    cx = inner.centerx

    # Office wall and harsh light
    pygame.draw.rect(surface, (20, 26, 28), inner)
    for y in range(inner.top + 10, inner.bottom, 16):
        pygame.draw.line(surface, (32, 40, 42), (inner.left, y), (inner.right, y), 1)
    flicker = 0.7 + 0.3 * (int(t * 11) % 5 != 0)
    light_col = (int(180 * flicker), int(205 * flicker), int(190 * flicker))
    pygame.draw.rect(surface, light_col, (cx - 36, inner.top + 5, 72, 4))

    # Cargo scanner arch behind Holt
    arch = pygame.Rect(cx - 42, inner.top + 28, 84, 82)
    pygame.draw.arc(surface, (80, 120, 110), arch, math.pi, math.tau, 3)
    pygame.draw.line(surface, (80, 120, 110), (arch.left, arch.centery), (arch.left, arch.bottom), 3)
    pygame.draw.line(surface, (80, 120, 110), (arch.right, arch.centery), (arch.right, arch.bottom), 3)
    scan_y = arch.top + 20 + int((math.sin(t * 2.6) + 1.0) * 24)
    pygame.draw.line(surface, (0, 230, 140), (arch.left + 8, scan_y), (arch.right - 8, scan_y), 1)

    # Manifest board
    board = pygame.Rect(inner.left + 7, inner.top + 18, 48, 58)
    pygame.draw.rect(surface, (8, 18, 16), board)
    pygame.draw.rect(surface, (0, 160, 100), board, 1)
    title = font6.render("MANIFEST", True, (0, 220, 130))
    surface.blit(title, (board.left + 3, board.top + 3))
    for row, txt in enumerate(["STD FR", "GEN GOODS", "REG-14", "OK"]):
        col = (0, 185, 110) if row != 3 else (220, 180, 60)
        surface.blit(font7.render(txt, True, col),
                     (board.left + 4, board.top + 13 + row * 9))

    # Stacks of forms and stamp pad
    for i in range(6):
        fy = inner.bottom - 20 + i * 2
        pygame.draw.rect(surface, (170, 160, 130),
                         (inner.right - 48 + i, fy, 34, 2))
    stamp = pygame.Rect(inner.right - 46, inner.bottom - 12, 18, 8)
    pygame.draw.rect(surface, (90, 20, 20), stamp)
    pygame.draw.rect(surface, (160, 70, 40), stamp, 1)

    # Filing cabinet
    cab = pygame.Rect(inner.right - 54, inner.top + 22, 44, 44)
    pygame.draw.rect(surface, (42, 48, 52), cab)
    pygame.draw.rect(surface, (90, 105, 105), cab, 1)
    for i in range(3):
        drawer = pygame.Rect(cab.left + 4, cab.top + 5 + i * 12, cab.w - 8, 9)
        pygame.draw.rect(surface, (30, 36, 40), drawer)
        pygame.draw.line(surface, (120, 135, 130), drawer.midtop, drawer.midbottom, 1)


def _cargo_inspector(surface, cx, cy, s, disposition, t):
    """Inspector Holt: precise, dry, and weaponized by forms."""
    skin = (216, 182, 140)
    skin_d = (120, 84, 50)
    hair = (55, 42, 32)
    uniform = (34, 54, 66)
    trim = (0, 190, 125)
    paper = (198, 190, 158)

    # Torso and tie
    torso = [
        (int(cx - 39 * s), int(cy + 72 * s)),
        (int(cx + 39 * s), int(cy + 72 * s)),
        (int(cx + 29 * s), int(cy + 28 * s)),
        (int(cx - 29 * s), int(cy + 28 * s)),
    ]
    pygame.draw.polygon(surface, uniform, torso)
    pygame.draw.polygon(surface, (85, 120, 120), torso, 1)
    tie = [
        (int(cx - 5 * s), int(cy + 30 * s)),
        (int(cx + 5 * s), int(cy + 30 * s)),
        (int(cx + 3 * s), int(cy + 60 * s)),
        (int(cx), int(cy + 67 * s)),
        (int(cx - 3 * s), int(cy + 60 * s)),
    ]
    pygame.draw.polygon(surface, (90, 26, 22), tie)
    pygame.draw.polygon(surface, (160, 60, 45), tie, 1)
    pygame.draw.rect(surface, trim,
                     (int(cx - 26 * s), int(cy + 39 * s), int(18 * s), int(6 * s)), 1)

    # Neck and head
    pygame.draw.rect(surface, skin_d,
                     (int(cx - 10 * s), int(cy + 15 * s), int(20 * s), int(18 * s)))
    head_rect = pygame.Rect(int(cx - 28 * s), int(cy - 39 * s),
                            int(56 * s), int(58 * s))
    pygame.draw.ellipse(surface, skin, head_rect)
    pygame.draw.ellipse(surface, skin_d, head_rect, 1)

    # Neat side-part hair
    hair_pts = [
        (int(cx - 27 * s), int(cy - 24 * s)),
        (int(cx - 17 * s), int(cy - 41 * s)),
        (int(cx + 15 * s), int(cy - 40 * s)),
        (int(cx + 28 * s), int(cy - 24 * s)),
        (int(cx + 18 * s), int(cy - 28 * s)),
        (int(cx - 2 * s), int(cy - 23 * s)),
    ]
    pygame.draw.polygon(surface, hair, hair_pts)
    pygame.draw.polygon(surface, (24, 18, 12), hair_pts, 1)
    pygame.draw.line(surface, (24, 18, 12),
                     (int(cx - 4 * s), int(cy - 39 * s)),
                     (int(cx - 10 * s), int(cy - 24 * s)), 1)

    # Glasses and careful eyes
    eye_y = int(cy - 12 * s)
    for ex in (-12, 12):
        lens = pygame.Rect(int(cx + ex * s - 9 * s), eye_y - int(6 * s),
                           int(18 * s), int(10 * s))
        pygame.draw.rect(surface, (170, 210, 195), lens, 1)
        pygame.draw.circle(surface, (20, 34, 30), (int(cx + ex * s), eye_y), 2)
    pygame.draw.line(surface, (170, 210, 195),
                     (int(cx - 3 * s), eye_y - int(2 * s)),
                     (int(cx + 3 * s), eye_y - int(2 * s)), 1)
    brow_drop = max(0, -disposition)
    pygame.draw.line(surface, hair,
                     (int(cx - 21 * s), int(cy - 24 * s + brow_drop)),
                     (int(cx - 5 * s), int(cy - 23 * s)), 2)
    pygame.draw.line(surface, hair,
                     (int(cx + 5 * s), int(cy - 23 * s)),
                     (int(cx + 21 * s), int(cy - 24 * s + brow_drop)), 2)

    # Nose, mouth, and bureaucratic stillness
    pygame.draw.line(surface, skin_d,
                     (int(cx + 1 * s), int(cy - 7 * s)),
                     (int(cx - 2 * s), int(cy + 6 * s)), 1)
    mouth_y = int(cy + 13 * s)
    if disposition >= 3:
        pygame.draw.line(surface, skin_d,
                         (int(cx - 8 * s), mouth_y),
                         (int(cx + 8 * s), mouth_y + int(1 * s)), 1)
    elif disposition <= -3:
        pygame.draw.arc(surface, skin_d,
                        pygame.Rect(int(cx - 10 * s), mouth_y - int(2 * s),
                                    int(20 * s), int(9 * s)),
                        math.pi, math.tau, 1)
    else:
        pygame.draw.line(surface, skin_d,
                         (int(cx - 9 * s), mouth_y),
                         (int(cx + 9 * s), mouth_y), 1)

    # Clipboard and pen
    clip = pygame.Rect(int(cx + 24 * s), int(cy + 8 * s), int(26 * s), int(34 * s))
    pygame.draw.rect(surface, paper, clip)
    pygame.draw.rect(surface, (105, 94, 65), clip, 1)
    pygame.draw.rect(surface, (85, 85, 82),
                     (clip.left + int(7 * s), clip.top - int(4 * s),
                      int(12 * s), int(5 * s)))
    for row in range(5):
        line_y = clip.top + int((6 + row * 5) * s)
        pygame.draw.line(surface, (80, 75, 60),
                         (clip.left + int(4 * s), line_y),
                         (clip.right - int(4 * s), line_y), 1)
    pygame.draw.line(surface, trim,
                     (int(cx - 26 * s), int(cy + 24 * s)),
                     (int(cx - 42 * s), int(cy + 4 * s)), 2)


_DISPATCH["nervous_fence"] = _nervous_fence
_BACKDROPS["nervous_fence"] = _backdrop_nervous_fence
_DISPATCH["cargo_inspector"] = _cargo_inspector
_BACKDROPS["cargo_inspector"] = _backdrop_cargo_inspector


# ---------------------------------------------------------------------------
# DRAY — slacker off-channel courier
# ---------------------------------------------------------------------------

def _backdrop_dray(surface, inner, t):
    """Cramped relay bunk: ratty bunk wall, discarded ration wrappers, bored ambience."""
    font6 = get_font(6, bold=True)
    cx = inner.centerx

    # Bunk wall — dented, sticker-covered metal panels
    for i in range(5):
        y = inner.top + i * 22
        col = (28, 22, 18) if i % 2 == 0 else (22, 18, 14)
        pygame.draw.rect(surface, col, (inner.left, y, inner.width, 22))
        pygame.draw.line(surface, (50, 38, 28), (inner.left, y), (inner.right, y), 1)

    # Random stickers on the wall — tiny colored blobs
    rng = random.Random(77)
    for i in range(6):
        sx = inner.left + rng.randint(8, inner.width - 14)
        sy = inner.top + rng.randint(6, inner.height // 2)
        scol = rng.choice([(180, 40, 40), (40, 160, 120), (200, 160, 40), (100, 80, 200)])
        pygame.draw.rect(surface, scol, (sx, sy, rng.randint(6, 12), rng.randint(5, 9)))
        pygame.draw.rect(surface, (255, 255, 255, 60), (sx, sy, rng.randint(6, 12), rng.randint(5, 9)), 1)

    # Relay screen top-right — static-y, mostly ignored
    scr = pygame.Rect(inner.right - 48, inner.top + 8, 38, 26)
    pygame.draw.rect(surface, (12, 18, 14), scr)
    pygame.draw.rect(surface, (0, 170, 90), scr, 1)
    # Static noise on screen
    rng2 = random.Random(int(t * 4))
    for _ in range(20):
        px = rng2.randint(scr.left + 1, scr.right - 2)
        py = rng2.randint(scr.top + 1, scr.bottom - 2)
        pygame.draw.circle(surface, (0, 100 + rng2.randint(0, 80), 60), (px, py), 1)
    tag = font6.render("RELAY OFF", True, (0, 200, 100))
    surface.blit(tag, (scr.left + 2, scr.top + 2))

    # Ration wrapper on bottom-left — crumpled foil
    wr_pts = [
        (inner.left + 4,  inner.bottom - 8),
        (inner.left + 18, inner.bottom - 14),
        (inner.left + 26, inner.bottom - 10),
        (inner.left + 22, inner.bottom - 4),
        (inner.left + 6,  inner.bottom - 3),
    ]
    pygame.draw.polygon(surface, (120, 110, 90), wr_pts)
    pygame.draw.polygon(surface, (180, 170, 130), wr_pts, 1)
    wrap_lbl = font6.render("NUTRI-PASTE", True, (90, 80, 60))
    surface.blit(wrap_lbl, (inner.left + 5, inner.bottom - 12))

    # Signal status light — blinking amber (always borderline signal)
    blink_on = int(t * 1.8) % 3 != 2
    sig_col = (220, 160, 30) if blink_on else (60, 44, 8)
    pygame.draw.circle(surface, sig_col, (cx - 28, inner.top + 10), 3)
    sig_lbl = font6.render("WEAK SIG", True, (120, 95, 30))
    surface.blit(sig_lbl, (cx - 22, inner.top + 7))


def _dray(surface, cx, cy, s, disposition, t):
    """Dray: visor PUSHED UP on his helmet, sleepy eyes visible, a stim
    cigarette dangling off his lip, courier jacket open over a faded
    band shirt. Reads as 'this guy is on his break and you're bothering
    him' from across the room.

    Aliveness B.5 rework — earlier portrait hid Dray entirely behind a
    tinted visor; players couldn't read his disposition or remember him.
    The new portrait commits to the slacker energy: bored eyes, lazy
    smile / smirk, smoke trail, visible band-shirt slogan."""
    skin   = (210, 175, 135)
    skin_d = (130, 95, 60)
    skin_s = (90, 65, 38)
    helm   = (58, 68, 72)
    helm_l = (110, 130, 138)
    visor  = (40, 110, 130)      # raised visor — daylight side
    accent = (160, 210, 130)
    jacket = (54, 48, 38)
    jacket_hi = (90, 78, 56)
    shirt  = (40, 30, 80)        # faded band shirt
    hair   = (60, 45, 30)

    cx_i = int(cx)
    cy_i = int(cy)

    # ── Slouched torso: jacket open over a faded band shirt ──────────
    torso_pts = [
        (cx_i - int(44 * s), cy_i + int(80 * s)),
        (cx_i + int(48 * s), cy_i + int(80 * s)),
        (cx_i + int(36 * s), cy_i + int(22 * s)),
        (cx_i - int(34 * s), cy_i + int(22 * s)),
    ]
    pygame.draw.polygon(surface, jacket, torso_pts)
    pygame.draw.polygon(surface, jacket_hi, torso_pts, 1)
    # Band shirt triangle showing through open jacket
    shirt_pts = [
        (cx_i, cy_i + int(28 * s)),
        (cx_i - int(18 * s), cy_i + int(80 * s)),
        (cx_i + int(18 * s), cy_i + int(80 * s)),
    ]
    pygame.draw.polygon(surface, shirt, shirt_pts)
    # Band logo  small triangle inside the shirt area
    pygame.draw.polygon(surface, (200, 180, 120),
                        [(cx_i - int(8 * s), cy_i + int(56 * s)),
                         (cx_i,              cy_i + int(46 * s)),
                         (cx_i + int(8 * s), cy_i + int(56 * s))], 1)

    # Jacket collar lapel  asymmetric, popped on one side
    pygame.draw.polygon(surface, jacket_hi,
                        [(cx_i - int(34 * s), cy_i + int(22 * s)),
                         (cx_i - int(10 * s), cy_i + int(34 * s)),
                         (cx_i - int(34 * s), cy_i + int(40 * s))])

    # ── Neck ─────────────────────────────────────────────────────────
    pygame.draw.rect(surface, skin_d, pygame.Rect(
        cx_i - int(12 * s), cy_i + int(10 * s),
        int(24 * s), int(16 * s)))

    # ── Helmet shell  battered grey-blue, visor RAISED ───────────────
    helm_rect = pygame.Rect(cx_i - int(48 * s), cy_i - int(60 * s),
                             int(96 * s), int(76 * s))
    pygame.draw.ellipse(surface, helm, helm_rect)
    pygame.draw.ellipse(surface, helm_l, helm_rect, 2)
    # Scuff marks (deterministic for the seed)
    rng = random.Random(13)
    for _ in range(5):
        scx = cx_i + int(rng.uniform(-34, 34) * s)
        scy = cy_i + int(rng.uniform(-52, -16) * s)
        pygame.draw.line(surface, (38, 46, 50),
                         (scx, scy),
                         (scx + rng.randint(3, 9),
                          scy + rng.randint(-2, 2)), 1)

    # Visor PUSHED UP onto the crown of the helmet  flipped lid look
    visor_rect = pygame.Rect(cx_i - int(40 * s), cy_i - int(74 * s),
                              int(80 * s), int(22 * s))
    pygame.draw.ellipse(surface, visor, visor_rect)
    pygame.draw.ellipse(surface, (90, 180, 200), visor_rect, 2)
    # Crack in raised visor  partial line
    pygame.draw.line(surface, (180, 220, 230),
                     (cx_i + int(8 * s), cy_i - int(66 * s)),
                     (cx_i + int(30 * s), cy_i - int(60 * s)), 1)

    # A few strands of hair flopping out below helmet brim
    pygame.draw.line(surface, hair,
                     (cx_i - int(28 * s), cy_i - int(22 * s)),
                     (cx_i - int(22 * s), cy_i - int(12 * s)),
                     max(2, int(3 * s)))
    pygame.draw.line(surface, hair,
                     (cx_i + int(26 * s), cy_i - int(22 * s)),
                     (cx_i + int(20 * s), cy_i - int(8 * s)),
                     max(2, int(3 * s)))

    # ── Face: eyebrows + sleepy eyes (visor is up, we can SEE him) ───
    # Eyebrows  one raised slightly higher than the other (cocky)
    pygame.draw.line(surface, hair,
                     (cx_i - int(22 * s), cy_i - int(24 * s)),
                     (cx_i - int(8 * s),  cy_i - int(28 * s)),
                     max(2, int(3 * s)))   # left brow raised
    pygame.draw.line(surface, hair,
                     (cx_i + int(8 * s),  cy_i - int(24 * s)),
                     (cx_i + int(22 * s), cy_i - int(24 * s)),
                     max(2, int(3 * s)))   # right brow flat

    # Sleepy eyes  half-lidded, depending on disposition
    blink_phase = abs(math.sin(t * 0.9 + 1.2))
    half_lid = blink_phase < 0.55 or disposition < 0
    for ex_off in (-13, 13):
        eye_cx = cx_i + int(ex_off * s)
        eye_cy = cy_i - int(14 * s)
        if half_lid:
            pygame.draw.line(surface, skin_s,
                             (eye_cx - int(5 * s), eye_cy),
                             (eye_cx + int(5 * s), eye_cy),
                             max(2, int(3 * s)))
        else:
            pygame.draw.circle(surface, (240, 230, 200),
                               (eye_cx, eye_cy), max(2, int(4 * s)))
            pygame.draw.circle(surface, (10, 22, 12),
                               (eye_cx, eye_cy), max(1, int(2 * s)))
            # Pupil drifts slightly  reads as 'looking through you'
            drift = int(2 * math.sin(t * 0.3 + ex_off))
            pygame.draw.circle(surface, (10, 22, 12),
                               (eye_cx + drift, eye_cy), 1)

    # Nose  short line for definition
    pygame.draw.line(surface, skin_s,
                     (cx_i, cy_i - int(8 * s)),
                     (cx_i + int(2 * s), cy_i + int(2 * s)),
                     max(1, int(2 * s)))

    # Stubble — diagonal hatching across jaw
    for i in range(-4, 5):
        sx = cx_i + i * int(4 * s)
        sy = cy_i + int(10 * s)
        pygame.draw.line(surface, skin_s,
                         (sx - 1, sy),
                         (sx + 2, sy + 3), 1)

    # Mouth  lopsided smirk (or flat line when annoyed)
    mouth_y = cy_i + int(6 * s)
    if disposition >= 2:
        # Smirk
        pygame.draw.line(surface, skin_s,
                         (cx_i - int(8 * s), mouth_y + 1),
                         (cx_i + int(8 * s), mouth_y - 2),
                         max(2, int(2 * s)))
    elif disposition <= -2:
        # Flat line
        pygame.draw.line(surface, skin_s,
                         (cx_i - int(8 * s), mouth_y),
                         (cx_i + int(8 * s), mouth_y),
                         max(2, int(2 * s)))
    else:
        # Default  slight smirk, lips parted
        pygame.draw.line(surface, skin_s,
                         (cx_i - int(9 * s), mouth_y),
                         (cx_i + int(7 * s), mouth_y - 1),
                         max(2, int(2 * s)))

    # ── Stim cig dangling from the right corner of his mouth ─────────
    cig_x = cx_i + int(10 * s)
    cig_y = mouth_y
    pygame.draw.line(surface, (240, 235, 200),
                     (cig_x, cig_y),
                     (cig_x + int(12 * s), cig_y + int(2 * s)),
                     max(2, int(2 * s)))
    # Lit tip — orange ember that pulses
    ember = 0.55 + 0.45 * math.sin(t * 4.2)
    pygame.draw.circle(surface, (int(255 * ember), int(110 * ember), 30),
                       (cig_x + int(12 * s), cig_y + int(2 * s)),
                       max(1, int(2 * s)))
    # Smoke trail  drifting up-right
    for k in range(4):
        sk_t = (t * 1.3 + k * 0.25) % 1.0
        sk_x = cig_x + int(12 * s + sk_t * 14)
        sk_y = cig_y + int(2 * s - sk_t * 22)
        sk_a = int(160 * (1 - sk_t))
        sk_r = max(1, int((1 + sk_t * 3) * s))
        smoke = pygame.Surface((sk_r * 2 + 2, sk_r * 2 + 2),
                               pygame.SRCALPHA)
        pygame.draw.circle(smoke, (180, 180, 200, sk_a),
                           (sk_r + 1, sk_r + 1), sk_r)
        surface.blit(smoke, (sk_x - sk_r - 1, sk_y - sk_r - 1))

    # ── Relay badge on helmet side  blinks softly ───────────────────
    pygame.draw.circle(surface, accent,
                       (cx_i + int(36 * s), cy_i - int(40 * s)),
                       max(3, int(4 * s)))
    pygame.draw.circle(surface, (10, 60, 40),
                       (cx_i + int(36 * s), cy_i - int(40 * s)),
                       max(3, int(4 * s)), 1)
    if int(t * 1.4) % 2 == 0:
        pygame.draw.circle(surface, (*accent, 180),
                           (cx_i + int(36 * s), cy_i - int(40 * s)),
                           max(5, int(6 * s)), 1)

    # Comm speaker grille on chin guard
    for grille_x in range(-12, 14, 5):
        pygame.draw.line(surface, (40, 55, 60),
                         (int(cx + grille_x * s), int(cy + 6 * s)),
                         (int(cx + grille_x * s), int(cy + 12 * s)), 1)

    # Disposition — hostile: visor flickers red tint
    if disposition <= -3:
        red_surf = pygame.Surface((int(76 * s), int(38 * s)), pygame.SRCALPHA)
        pygame.draw.ellipse(red_surf, (200, 30, 30, 60), pygame.Rect(0, 0, int(76 * s), int(38 * s)))
        surface.blit(red_surf, visor_rect.topleft)


# ---------------------------------------------------------------------------
# NOVA SOMA COLLECTIONS — automated wellness-debt AI
# ---------------------------------------------------------------------------

def _backdrop_nova_soma_collections(surface, inner, t):
    """Corporate wellness UI: clean gradients, progress rings, soft pastel branding."""
    cx = inner.centerx
    font6 = get_font(6, bold=True)
    font7 = get_font(7)

    # Background: clean dark blue-grey with subtle grid
    pygame.draw.rect(surface, (14, 18, 26), inner)
    for i in range(0, inner.height, 12):
        alpha = 18 + int(6 * math.sin(t * 0.5 + i * 0.1))
        line_surf = pygame.Surface((inner.width, 1), pygame.SRCALPHA)
        line_surf.fill((100, 230, 215, alpha))
        surface.blit(line_surf, (inner.left, inner.top + i))
    for i in range(0, inner.width, 16):
        alpha = 12 + int(5 * math.sin(t * 0.4 + i * 0.08))
        col_surf = pygame.Surface((1, inner.height), pygame.SRCALPHA)
        col_surf.fill((100, 230, 215, alpha))
        surface.blit(col_surf, (inner.left + i, inner.top))

    # Wellness score ring (top-right)
    ring_cx = inner.right - 28
    ring_cy = inner.top + 30
    ring_r = 18
    pygame.draw.circle(surface, (20, 28, 38), (ring_cx, ring_cy), ring_r)
    pygame.draw.circle(surface, (40, 55, 65), (ring_cx, ring_cy), ring_r, 2)
    score_frac = 0.72 + 0.08 * math.sin(t * 0.7)
    arc_rect = pygame.Rect(ring_cx - ring_r, ring_cy - ring_r, ring_r * 2, ring_r * 2)
    pygame.draw.arc(surface, (100, 230, 215), arc_rect,
                    math.pi / 2, math.pi / 2 + score_frac * math.tau, 2)
    score_lbl = font6.render(f"{int(score_frac * 100)}%", True, (100, 230, 215))
    surface.blit(score_lbl, (ring_cx - score_lbl.get_width() // 2, ring_cy - 3))
    wellness_tag = font6.render("WELLNESS", True, (60, 130, 125))
    surface.blit(wellness_tag, (ring_cx - wellness_tag.get_width() // 2, ring_cy + ring_r + 2))

    # Debt bar (left side)
    bar_rect = pygame.Rect(inner.left + 8, inner.top + 20, 10, inner.height - 40)
    pygame.draw.rect(surface, (20, 28, 38), bar_rect)
    pygame.draw.rect(surface, (40, 55, 65), bar_rect, 1)
    fill_h = int(bar_rect.height * (0.61 + 0.05 * math.sin(t * 1.2)))
    fill_rect = pygame.Rect(bar_rect.left + 1, bar_rect.bottom - fill_h - 1,
                             bar_rect.width - 2, fill_h)
    pygame.draw.rect(surface, (255, 120, 160), fill_rect)
    debt_lbl = font6.render("DEBT", True, (200, 90, 130))
    surface.blit(debt_lbl, (inner.left + 4, inner.bottom - 14))

    # Scrolling marquee at the bottom
    marquee_txt = "NOVA SOMA COLLECTIONS • YOUR WELLNESS IS OUR PRIORITY • "
    marquee_font = get_font(6)
    msurf = marquee_font.render(marquee_txt, True, (80, 200, 190))
    scroll_x = inner.left + inner.width - int((t * 28) % (inner.width + msurf.get_width()))
    prev_clip = surface.get_clip()
    surface.set_clip(pygame.Rect(inner.left, inner.bottom - 12, inner.width, 10))
    pygame.draw.rect(surface, (10, 16, 22), pygame.Rect(inner.left, inner.bottom - 12, inner.width, 10))
    surface.blit(msurf, (scroll_x, inner.bottom - 11))
    surface.set_clip(prev_clip)

    # "CALL IN PROGRESS" tag
    tag = font7.render("SESSION ACTIVE", True, (100, 230, 215))
    surface.blit(tag, (cx - tag.get_width() // 2, inner.top + 4))


def _nova_soma_collections(surface, cx, cy, s, disposition, t):
    """
    Nova Soma Collections AI — a corporate sensor platform, not a humanoid face.
    Asymmetric elliptical sensor array. Emotion shown through readout state changes.
    """
    bg_col  = (14, 20, 30)
    shell   = (38, 58, 72)
    shell_l = (70, 110, 125)
    cyan    = (100, 230, 215)
    pink    = (255, 130, 170)
    amber   = (215, 160, 40)
    dim     = (25, 55, 60)

    hostile  = disposition <= -3
    friendly = disposition >= 3

    # Platform / neck stub
    plat_pts = [
        (int(cx - 28 * s), int(cy + 80 * s)),
        (int(cx + 28 * s), int(cy + 80 * s)),
        (int(cx + 22 * s), int(cy + 40 * s)),
        (int(cx - 22 * s), int(cy + 40 * s)),
    ]
    pygame.draw.polygon(surface, (24, 36, 46), plat_pts)
    pygame.draw.polygon(surface, shell_l, plat_pts, 1)

    # Elliptical head casing
    head_rect = pygame.Rect(int(cx - 52 * s), int(cy - 60 * s),
                             int(104 * s), int(108 * s))
    pygame.draw.ellipse(surface, shell, head_rect)
    pygame.draw.ellipse(surface, shell_l, head_rect, 2)

    # Sensor display panel — slightly flatter ellipse than the casing
    face_rect = pygame.Rect(int(cx - 40 * s), int(cy - 46 * s),
                             int(80 * s), int(84 * s))
    pygame.draw.ellipse(surface, bg_col, face_rect)
    pygame.draw.ellipse(surface, (40, 65, 80), face_rect, 1)

    # ── PRIMARY SENSOR NODE ──────────────────────────────────────────────────
    # Large horizontal bar, offset LEFT of centre — breaks bilateral symmetry
    p_pulse = 0.5 + 0.5 * math.sin(t * (5.5 if hostile else 2.1))
    p_col   = pink if hostile else (amber if friendly else cyan)
    p_lit   = tuple(min(255, int(c * (0.55 + 0.45 * p_pulse))) for c in p_col)

    pw, ph = max(4, int(26 * s)), max(3, int(9 * s))
    px_s, py_s = int(cx - 11 * s), int(cy - 16 * s)
    pygame.draw.rect(surface, dim,
                     pygame.Rect(px_s - pw // 2, py_s - ph // 2, pw, ph),
                     border_radius=max(2, int(ph // 2)))
    pygame.draw.rect(surface, p_lit,
                     pygame.Rect(px_s - pw // 2 + 1, py_s - ph // 2 + 1,
                                 pw - 2, max(1, ph - 2)),
                     border_radius=max(1, max(1, ph // 2 - 1)))
    if ph >= 4:
        g_s = pygame.Surface((pw + 14, ph + 14), pygame.SRCALPHA)
        pygame.draw.rect(g_s, (*p_lit, int(30 + 45 * p_pulse)),
                         pygame.Rect(5, 5, pw + 4, ph + 4),
                         border_radius=max(2, int(ph // 2)))
        surface.blit(g_s, (px_s - pw // 2 - 7, py_s - ph // 2 - 7))

    # ── SECONDARY SENSOR — small vertical rectangle, upper RIGHT ────────────
    s2_p  = 0.5 + 0.5 * math.sin(t * 1.6 + 1.5)
    s2w   = max(3, int(11 * s))
    s2h   = max(4, int(16 * s))
    s2x   = int(cx + 20 * s)
    s2y   = int(cy - 18 * s)
    s2col = pink if hostile else (dim if s2_p < 0.4 else cyan)
    pygame.draw.rect(surface, (8, 20, 24),
                     pygame.Rect(s2x - s2w // 2, s2y - s2h // 2, s2w, s2h),
                     border_radius=max(1, int(2 * s)))
    pygame.draw.rect(surface, s2col,
                     pygame.Rect(s2x - s2w // 2, s2y - s2h // 2, s2w, s2h),
                     border_radius=max(1, int(2 * s)), width=1)
    pygame.draw.circle(surface, s2col, (s2x, s2y), max(1, int(2 * s)))

    # ── TERTIARY CLUSTER — 3 micro-dots, lower LEFT, irregular spacing ───────
    for di, (dox, doy, dp_off) in enumerate([(-19, 7, 0.0), (-24, 15, 1.1), (-13, 19, 2.3)]):
        dp = abs(math.sin(t * (3.2 if hostile else 1.2) + dp_off))
        dc = pink if (hostile and dp > 0.5) else (cyan if dp > 0.5 else dim)
        pygame.draw.circle(surface, dc,
                           (int(cx + dox * s), int(cy + doy * s)),
                           max(1, int(2 * s)))

    # ── QUATERNARY STRIP — 4 micro-nodes on right edge, vertical ────────────
    for qi in range(4):
        q_p  = abs(math.sin(t * (2.8 if hostile else 0.9) + qi * 0.9))
        q_on = q_p > (0.25 if hostile else 0.55)
        qc   = pink if (hostile and q_on) else (cyan if q_on else dim)
        pygame.draw.circle(surface, qc,
                           (int(cx + 27 * s), int(cy + (-12 + qi * 7) * s)),
                           max(1, int(2 * s)))

    # ── SWEEP ARC from primary sensor ───────────────────────────────────────
    sweep_a = (t * 0.85) % (2 * math.pi)
    arc_c   = tuple(min(255, int(c * 0.26)) for c in p_col)
    for step in range(3):
        r_off = max(8, int((14 + step * 8) * s))
        ax = px_s + int(r_off * math.cos(sweep_a))
        ay = py_s + int(r_off * math.sin(sweep_a))
        if face_rect.collidepoint(ax, ay):
            pygame.draw.circle(surface, arc_c, (ax, ay), 1)

    # ── READOUT PANEL — replaces "mouth"; state changes with disposition ─────
    rdp_y = int(cy + 10 * s)
    rdp_w = max(14, int(64 * s))
    rdp_h = max(5, int(26 * s))
    rdp_x = cx - rdp_w // 2
    pygame.draw.rect(surface, (6, 12, 18),
                     pygame.Rect(rdp_x, rdp_y, rdp_w, rdp_h),
                     border_radius=max(1, int(2 * s)))
    pygame.draw.rect(surface, (30, 50, 65),
                     pygame.Rect(rdp_x, rdp_y, rdp_w, rdp_h),
                     border_radius=max(1, int(2 * s)), width=1)

    if s >= 0.55 and rdp_h >= 12:
        rd_font = get_font(max(5, int(6 * s)))
        tick    = int(t * (5.0 if hostile else 1.8))

        def _hx(seed, n=3):
            v = (seed * 2654435761) & 0xFFFFFFFF
            chars = "0123456789ABCDEF"
            return "".join(chars[(v >> (i * 4)) & 0xF] for i in range(n))

        if hostile:
            rows = [f"ERR:{_hx(tick)}", f"ALM:{'!!!' if tick % 2 else '---'}"]
            rc   = pink
        elif friendly:
            rows = [f"SYN:{_hx(tick // 3, 2)}h", "OK:100"]
            rc   = amber
        else:
            rows = [f"{_hx(tick, 4)}", f"{_hx(tick+5,2)}.{_hx(tick+9,2)}"]
            rc   = (60, 160, 150)

        row_h = max(4, (rdp_h - 4) // max(1, len(rows)))
        for li, row in enumerate(rows):
            ry = rdp_y + 2 + li * row_h
            if ry + 5 < rdp_y + rdp_h:
                rtxt = rd_font.render(row, True, rc)
                surface.blit(rtxt, (rdp_x + max(2, int(3 * s)), ry))

    # ── LOGOTYPE ──────────────────────────────────────────────────────────────
    font_lbl = get_font(max(6, int(6 * s)), bold=True)
    la  = int(80 + 40 * math.sin(t * 0.75))
    lc  = (int(cyan[0] * la // 120), int(cyan[1] * la // 120), int(cyan[2] * la // 120))
    ls  = font_lbl.render("NOVA SOMA", True, lc)
    surface.blit(ls, (cx - ls.get_width() // 2, int(cy + 36 * s)))

    # Corner accent dots on casing (structural detail only)
    for dx, dy in [(-1, -1), (1, -1), (-1, 1), (1, 1)]:
        acx = int(cx + dx * 44 * s)
        acy = int(cy + dy * 46 * s)
        pygame.draw.circle(surface, shell_l, (acx, acy), max(2, int(3 * s)))
        pygame.draw.circle(surface, cyan,    (acx, acy), max(2, int(3 * s)), 1)


# ---------------------------------------------------------------------------
# MIRA VOSS — back-alley hull medic
# ---------------------------------------------------------------------------

def _backdrop_mira_voss(surface, inner, t):
    """Industrial repair bay: exposed conduit, tool wall, welding sparks."""
    font6 = get_font(6, bold=True)
    font7 = get_font(7)
    cx = inner.centerx

    # Grimy workshop walls — alternating dark metal plates
    for i in range(6):
        y = inner.top + i * 18
        col = (20, 16, 14) if i % 2 == 0 else (28, 22, 18)
        pygame.draw.rect(surface, col, (inner.left, y, inner.width, 18))
        pygame.draw.line(surface, (55, 42, 30), (inner.left, y), (inner.right, y), 1)

    # Tool wall on the right side
    tool_x = inner.right - 36
    tool_rect = pygame.Rect(tool_x, inner.top + 8, 28, inner.height - 16)
    pygame.draw.rect(surface, (24, 20, 16), tool_rect)
    pygame.draw.rect(surface, (70, 55, 38), tool_rect, 1)
    # Hanging tools — silhouettes
    tool_shapes = [(4, 8, 4, 18), (12, 6, 4, 22), (20, 10, 4, 14)]
    for tx, ty, tw, th in tool_shapes:
        pygame.draw.rect(surface, (60, 50, 38),
                         (tool_rect.left + tx, tool_rect.top + ty, tw, th))
        pygame.draw.line(surface, (90, 72, 50),
                         (tool_rect.left + tx + tw // 2, tool_rect.top + ty - 3),
                         (tool_rect.left + tx + tw // 2, tool_rect.top + ty), 1)

    # Hull plate being worked on (left side)
    plate = pygame.Rect(inner.left + 4, inner.top + 24, 36, 50)
    pygame.draw.rect(surface, (30, 26, 22), plate)
    pygame.draw.rect(surface, (80, 65, 46), plate, 1)
    # Weld seams on the plate
    for row in range(3):
        wy = plate.top + 10 + row * 14
        pygame.draw.line(surface, (110, 80, 40),
                         (plate.left + 4, wy), (plate.right - 4, wy), 1)
    # Repair patch — bright spot
    pygame.draw.circle(surface, (160, 120, 60),
                       (plate.left + 18, plate.top + 30), 5)
    pygame.draw.circle(surface, (220, 180, 80),
                       (plate.left + 18, plate.top + 30), 5, 1)

    # Welding sparks — animated
    rng = random.Random(int(t * 7))
    for _ in range(8):
        spx = plate.left + rng.randint(4, plate.width - 4)
        spy = plate.top + rng.randint(20, plate.height - 6)
        spark_r = rng.random()
        if spark_r > 0.5:
            scol = (255, int(160 + rng.randint(0, 80)), 20)
            pygame.draw.circle(surface, scol, (spx, spy), 1)

    # Industrial ceiling pipe
    pygame.draw.line(surface, (50, 40, 30),
                     (inner.left, inner.top + 12),
                     (inner.right, inner.top + 12), 3)
    for px in range(inner.left + 12, inner.right - 8, 18):
        pygame.draw.line(surface, (70, 55, 38),
                         (px, inner.top + 12), (px, inner.top + 20), 2)

    # Status board
    board = pygame.Rect(cx - 18, inner.top + 4, 36, 10)
    pygame.draw.rect(surface, (60, 46, 30), board)
    pygame.draw.rect(surface, (120, 95, 60), board, 1)
    lbl = font6.render("HULL MEDIC", True, (220, 170, 90))
    surface.blit(lbl, (board.centerx - lbl.get_width() // 2, board.top + 2))


def _mira_voss(surface, cx, cy, s, disposition, t):
    """Mira Voss: tough hull medic. Welding visor pushed up, grease-marked face, work-hardened."""
    skin   = (195, 158, 118)
    skin_d = (105, 75, 48)
    hair   = (38, 28, 18)      # dark, short and practical
    suit   = (58, 52, 44)      # worn work coveralls
    suit_l = (90, 80, 65)
    visor  = (62, 100, 110)    # welding visor pushed up on forehead
    visor_l = (100, 150, 160)
    accent = (240, 140, 50)    # orange-yellow industrial

    # Torso — coveralls with utility pouches
    torso_pts = [
        (int(cx - 44 * s), int(cy + 82 * s)),
        (int(cx + 44 * s), int(cy + 82 * s)),
        (int(cx + 36 * s), int(cy + 22 * s)),
        (int(cx - 36 * s), int(cy + 22 * s)),
    ]
    pygame.draw.polygon(surface, suit, torso_pts)
    pygame.draw.polygon(surface, suit_l, torso_pts, 1)
    # Utility pouch on left chest
    pouch = pygame.Rect(int(cx - 30 * s), int(cy + 34 * s), int(16 * s), int(12 * s))
    pygame.draw.rect(surface, (72, 64, 52), pouch)
    pygame.draw.rect(surface, suit_l, pouch, 1)
    # Welding badge / certification patch on right
    badge = pygame.Rect(int(cx + 14 * s), int(cy + 30 * s), int(18 * s), int(12 * s))
    pygame.draw.rect(surface, (30, 22, 12), badge)
    pygame.draw.rect(surface, accent, badge, 1)
    font = get_font(max(6, int(6 * s)))
    badge_lbl = font.render("CERT", True, accent)
    surface.blit(badge_lbl, (badge.left + 3, badge.top + 2))

    # Neck
    pygame.draw.rect(surface, skin_d,
                     (int(cx - 10 * s), int(cy + 12 * s),
                      int(20 * s), int(14 * s)))

    # Head — practical, strong jaw
    head_pts = [
        (int(cx - 36 * s), int(cy - 14 * s)),
        (int(cx - 28 * s), int(cy - 36 * s)),
        (int(cx - 8 * s),  int(cy - 46 * s)),
        (int(cx + 14 * s), int(cy - 44 * s)),
        (int(cx + 30 * s), int(cy - 28 * s)),
        (int(cx + 34 * s), int(cy - 8 * s)),
        (int(cx + 28 * s), int(cy + 14 * s)),
        (int(cx + 8 * s),  int(cy + 22 * s)),
        (int(cx - 12 * s), int(cy + 20 * s)),
        (int(cx - 32 * s), int(cy + 8 * s)),
    ]
    pygame.draw.polygon(surface, skin, head_pts)
    pygame.draw.polygon(surface, skin_d, head_pts, 1)

    # Hair — short, practical cut
    hair_pts = [
        (int(cx - 34 * s), int(cy - 14 * s)),
        (int(cx - 26 * s), int(cy - 38 * s)),
        (int(cx - 6 * s),  int(cy - 48 * s)),
        (int(cx + 16 * s), int(cy - 46 * s)),
        (int(cx + 30 * s), int(cy - 30 * s)),
        (int(cx + 22 * s), int(cy - 22 * s)),
        (int(cx - 4 * s),  int(cy - 28 * s)),
        (int(cx - 22 * s), int(cy - 20 * s)),
    ]
    pygame.draw.polygon(surface, hair, hair_pts)
    pygame.draw.polygon(surface, (18, 14, 8), hair_pts, 1)

    # Welding visor pushed up on forehead — distinctive feature
    visor_pts = [
        (int(cx - 34 * s), int(cy - 28 * s)),
        (int(cx + 28 * s), int(cy - 32 * s)),
        (int(cx + 26 * s), int(cy - 46 * s)),
        (int(cx - 30 * s), int(cy - 44 * s)),
    ]
    pygame.draw.polygon(surface, visor, visor_pts)
    pygame.draw.polygon(surface, visor_l, visor_pts, 1)
    # Visor lens strip — tinted orange
    lens_pts = [
        (int(cx - 28 * s), int(cy - 32 * s)),
        (int(cx + 22 * s), int(cy - 35 * s)),
        (int(cx + 20 * s), int(cy - 42 * s)),
        (int(cx - 25 * s), int(cy - 40 * s)),
    ]
    pygame.draw.polygon(surface, (60, 36, 12), lens_pts)
    pygame.draw.polygon(surface, (130, 80, 30), lens_pts, 1)

    # Eyes — focused, no-nonsense
    eye_y = int(cy - 12 * s)
    if disposition >= 3:
        ecol = (200, 240, 200)   # slightly warmer when pleased
    elif disposition <= -4:
        ecol = (255, 180, 160)   # hard stare when hostile
    else:
        ecol = (220, 215, 205)

    for ex_off in (-12, 14):
        pygame.draw.ellipse(surface, ecol,
                            pygame.Rect(int(cx + ex_off * s - int(7 * s)), eye_y - int(4 * s),
                                        int(14 * s), max(3, int(7 * s))))
        pygame.draw.circle(surface, (30, 60, 50),
                           (int(cx + ex_off * s), eye_y), max(2, int(3 * s)))

    # Brows — flat, direct (angle steeper when hostile)
    brow_angle = max(0, -disposition) * 0.8
    for side, ex_off in [(-1, -12), (1, 14)]:
        pygame.draw.line(surface, hair,
                         (int(cx + ex_off * s - int(8 * s)),
                          int(cy - 22 * s + side * brow_angle * s)),
                         (int(cx + ex_off * s + int(8 * s)),
                          int(cy - 24 * s - side * brow_angle * s)), 2)

    # Grease marks — random soot smears on face
    rng = random.Random(99)
    for _ in range(4):
        gx = int(cx + rng.uniform(-28, 28) * s)
        gy = int(cy + rng.uniform(-8, 18) * s)
        grease_surf = pygame.Surface((max(3, int(8 * s)), max(2, int(4 * s))), pygame.SRCALPHA)
        grease_surf.fill((28, 20, 14, 65))
        surface.blit(grease_surf, (gx, gy))

    # Nose
    pygame.draw.line(surface, skin_d,
                     (int(cx + 2 * s), int(cy - 4 * s)),
                     (int(cx - 2 * s), int(cy + 8 * s)), 1)

    # Mouth — set, determined
    mouth_y = int(cy + 14 * s)
    if disposition >= 3:
        pygame.draw.arc(surface, skin_d,
                        pygame.Rect(int(cx - 11 * s), mouth_y - int(8 * s),
                                    int(22 * s), int(12 * s)),
                        math.pi, math.tau, 1)
    elif disposition <= -3:
        pygame.draw.arc(surface, skin_d,
                        pygame.Rect(int(cx - 12 * s), mouth_y,
                                    int(24 * s), int(10 * s)),
                        0, math.pi, 1)
    else:
        pygame.draw.line(surface, skin_d,
                         (int(cx - 10 * s), mouth_y),
                         (int(cx + 10 * s), mouth_y), 1)

    # Welding tool holstered at hip — visible bottom of frame
    pygame.draw.line(surface, accent,
                     (int(cx - 32 * s), int(cy + 48 * s)),
                     (int(cx - 24 * s), int(cy + 76 * s)), max(2, int(3 * s)))
    pygame.draw.circle(surface, (200, 110, 30),
                       (int(cx - 24 * s), int(cy + 76 * s)), max(3, int(4 * s)))


_DISPATCH["dray"]                   = _dray
_BACKDROPS["dray"]                  = _backdrop_dray
_DISPATCH["nova_soma_collections"]  = _nova_soma_collections
_BACKDROPS["nova_soma_collections"] = _backdrop_nova_soma_collections
_DISPATCH["mira_voss"]              = _mira_voss
_BACKDROPS["mira_voss"]             = _backdrop_mira_voss


# ---------------------------------------------------------------------------
# Idealist Union Rep — Edmund "Eddie" Marlowe
# ---------------------------------------------------------------------------

def _idealist_rep(surface, cx, cy, s, disposition, t):
    """Edmund Marlowe — Local 404 true believer.

    Visual signature: high collar with charter pin, neat side-parted hair,
    earnest open expression. Same Local 404 hi-vis sash as Gary, but pressed.
    """
    skin     = (220, 195, 165)
    skin_d   = (170, 140, 110)
    hair     = (110, 70,  35)
    hi_vis   = (220, 200, 70)   # gold-yellow union sash
    pin      = (200, 80,  80)   # red charter pin
    eye_col  = (15, 20, 30)
    cy = int(cy)
    cx = int(cx)

    # Collar / shoulders — high formal collar, pressed
    pygame.draw.polygon(surface, hi_vis, [
        (int(cx - 50 * s), int(cy + 78 * s)),
        (int(cx + 50 * s), int(cy + 78 * s)),
        (int(cx + 38 * s), int(cy + 22 * s)),
        (int(cx - 38 * s), int(cy + 22 * s)),
    ])
    # Sash diagonal line
    pygame.draw.line(surface, (180, 160, 50),
                     (int(cx - 32 * s), int(cy + 38 * s)),
                     (int(cx + 32 * s), int(cy + 70 * s)),
                     max(2, int(3 * s)))
    # Charter pin
    pygame.draw.circle(surface, pin,
                       (int(cx + 22 * s), int(cy + 50 * s)),
                       max(3, int(5 * s)))
    pygame.draw.circle(surface, (255, 255, 255),
                       (int(cx + 22 * s), int(cy + 50 * s)),
                       max(1, int(2 * s)))

    # Neck
    pygame.draw.rect(surface, skin, pygame.Rect(
        int(cx - 12 * s), int(cy + 12 * s),
        int(24 * s), int(20 * s)))
    pygame.draw.line(surface, skin_d,
                     (int(cx - 12 * s), int(cy + 32 * s)),
                     (int(cx + 12 * s), int(cy + 32 * s)), 1)

    # Head — slightly narrow, eager
    head_rect = pygame.Rect(
        int(cx - 38 * s), int(cy - 50 * s),
        int(76 * s), int(72 * s))
    pygame.draw.ellipse(surface, skin, head_rect)
    pygame.draw.ellipse(surface, skin_d, head_rect, 1)

    # Hair — neat side part, glossy
    pygame.draw.polygon(surface, hair, [
        (int(cx - 38 * s), int(cy - 32 * s)),
        (int(cx + 38 * s), int(cy - 36 * s)),
        (int(cx + 36 * s), int(cy - 50 * s)),
        (int(cx - 36 * s), int(cy - 50 * s)),
    ])
    # Side part highlight
    pygame.draw.line(surface, (160, 110, 50),
                     (int(cx - 16 * s), int(cy - 50 * s)),
                     (int(cx - 6 * s), int(cy - 32 * s)),
                     max(1, int(2 * s)))

    # Eyes — wide, sincere
    blink = abs(math.sin(t * 1.4)) < 0.96
    for ex in (-14, 14):
        eye_x = int(cx + ex * s)
        eye_y = int(cy - 8 * s)
        if blink:
            pygame.draw.circle(surface, (255, 255, 255), (eye_x, eye_y),
                               max(2, int(4 * s)))
            pygame.draw.circle(surface, eye_col, (eye_x, eye_y),
                               max(1, int(2 * s)))
        else:
            pygame.draw.line(surface, eye_col,
                             (eye_x - 3, eye_y), (eye_x + 3, eye_y), 1)
    # Eyebrows — slightly raised, hopeful
    for ex in (-14, 14):
        pygame.draw.line(surface, hair,
                         (int(cx + ex * s - 5), int(cy - 18 * s)),
                         (int(cx + ex * s + 5), int(cy - 16 * s)),
                         max(1, int(2 * s)))

    # Nose
    pygame.draw.line(surface, skin_d,
                     (int(cx), int(cy - 4 * s)),
                     (int(cx + 2 * s), int(cy + 6 * s)), 1)

    # Mouth — open, mid-quote, depending on disposition
    mouth_y = int(cy + 16 * s)
    if disposition >= 2:
        # Mid-grin, charter just made his day
        pygame.draw.arc(surface, skin_d, pygame.Rect(
            int(cx - 14 * s), int(mouth_y - 6),
            int(28 * s), int(12 * s)), 3.4, 6.0, 2)
    elif disposition <= -2:
        # Pained — your bribe offer wounded him
        pygame.draw.arc(surface, skin_d, pygame.Rect(
            int(cx - 12 * s), int(mouth_y - 2),
            int(24 * s), int(10 * s)), 0.4, 2.7, 2)
    else:
        # Default: lips parted, mid-sentence
        pygame.draw.line(surface, skin_d,
                         (int(cx - 10 * s), mouth_y),
                         (int(cx + 10 * s), mouth_y), 2)


# ---------------------------------------------------------------------------
# Corrupt Union Rep — Vince "Two-Tap" Brogan
# ---------------------------------------------------------------------------

def _corrupt_rep(surface, cx, cy, s, disposition, t):
    """Vince Brogan — opportunistic Local 404 with side hustles.

    Visual signature: grimy hi-vis (faded, stained), missed-shave,
    droopy mustache, side-mounted earpiece, slight smirk. Same shape
    as Gary but visibly less professional.
    """
    skin     = (200, 160, 130)
    skin_d   = (140, 100, 70)
    hair     = (40,  35, 30)
    stubble  = (70, 55, 40)
    hi_vis   = (165, 130, 35)   # faded/dirty union sash
    sash_dim = (110, 85, 25)
    earpiece = (40, 40, 50)
    cy = int(cy)
    cx = int(cx)

    # Collar / shoulders — slumped, lapel undone
    pygame.draw.polygon(surface, hi_vis, [
        (int(cx - 50 * s), int(cy + 78 * s)),
        (int(cx + 50 * s), int(cy + 78 * s)),
        (int(cx + 36 * s), int(cy + 24 * s)),
        (int(cx - 36 * s), int(cy + 24 * s)),
    ])
    # Stains
    pygame.draw.circle(surface, (90, 60, 30),
                       (int(cx - 18 * s), int(cy + 50 * s)),
                       max(3, int(5 * s)))
    pygame.draw.circle(surface, (90, 60, 30),
                       (int(cx + 14 * s), int(cy + 64 * s)),
                       max(2, int(3 * s)))
    # Lapel notch — undone
    pygame.draw.line(surface, sash_dim,
                     (int(cx - 6 * s), int(cy + 26 * s)),
                     (int(cx - 14 * s), int(cy + 60 * s)),
                     max(2, int(3 * s)))

    # Neck — wider, more hunched
    pygame.draw.rect(surface, skin, pygame.Rect(
        int(cx - 14 * s), int(cy + 12 * s),
        int(28 * s), int(20 * s)))

    # Head — slightly wider/heavier than Eddie
    head_rect = pygame.Rect(
        int(cx - 42 * s), int(cy - 52 * s),
        int(84 * s), int(76 * s))
    pygame.draw.ellipse(surface, skin, head_rect)
    pygame.draw.ellipse(surface, skin_d, head_rect, 1)

    # Stubble across jaw — diagonal hatching
    for i in range(-3, 4):
        sx = int(cx + i * 6 * s)
        sy = int(cy + 8 * s)
        pygame.draw.line(surface, stubble,
                         (sx - 1, sy),
                         (sx + 2, sy + 4), 1)

    # Hair — receding, messy
    pygame.draw.polygon(surface, hair, [
        (int(cx - 34 * s), int(cy - 36 * s)),
        (int(cx + 34 * s), int(cy - 38 * s)),
        (int(cx + 28 * s), int(cy - 50 * s)),
        (int(cx - 26 * s), int(cy - 52 * s)),
    ])
    # Hairline tooth (receding)
    pygame.draw.polygon(surface, skin, [
        (int(cx - 4 * s), int(cy - 36 * s)),
        (int(cx + 4 * s), int(cy - 36 * s)),
        (int(cx),         int(cy - 26 * s)),
    ])

    # Earpiece — black bud + dangling wire
    pygame.draw.circle(surface, earpiece,
                       (int(cx + 38 * s), int(cy - 10 * s)),
                       max(2, int(4 * s)))
    pygame.draw.line(surface, (60, 60, 70),
                     (int(cx + 38 * s), int(cy - 6 * s)),
                     (int(cx + 44 * s), int(cy + 12 * s)), 1)

    # Eyes — narrow, calculating
    blink = abs(math.sin(t * 1.1 + 0.4)) < 0.93
    for ex in (-14, 14):
        eye_x = int(cx + ex * s)
        eye_y = int(cy - 6 * s)
        if blink:
            pygame.draw.line(surface, (15, 15, 20),
                             (eye_x - 4, eye_y), (eye_x + 4, eye_y), 2)
            pygame.draw.circle(surface, (15, 15, 20), (eye_x, eye_y - 1),
                               max(1, int(2 * s)))
        else:
            pygame.draw.line(surface, (15, 15, 20),
                             (eye_x - 4, eye_y), (eye_x + 4, eye_y), 1)
    # Eyebrows — heavy, slightly raised
    for ex in (-14, 14):
        pygame.draw.line(surface, hair,
                         (int(cx + ex * s - 7), int(cy - 16 * s)),
                         (int(cx + ex * s + 5), int(cy - 14 * s)),
                         max(2, int(3 * s)))

    # Mustache — droopy
    pygame.draw.arc(surface, hair, pygame.Rect(
        int(cx - 14 * s), int(cy + 6 * s),
        int(28 * s), int(10 * s)), 3.4, 6.0, max(2, int(3 * s)))

    # Mouth — smirk lopsided to the right
    mouth_y = int(cy + 18 * s)
    if disposition >= 2:
        # Real grin, bribe taken
        pygame.draw.arc(surface, skin_d, pygame.Rect(
            int(cx - 14 * s), int(mouth_y - 4),
            int(28 * s), int(14 * s)), 3.5, 6.1, 2)
    else:
        pygame.draw.line(surface, skin_d,
                         (int(cx - 10 * s), mouth_y + 1),
                         (int(cx + 10 * s), mouth_y - 2), 2)


def _backdrop_idealist_rep(surface, inner, t):
    """Eddie's barge cockpit — pinned charter poster, neatly stowed clipboard,
    framed photo of his union induction class."""
    cx = inner.centerx
    cy = inner.centery
    fnt = get_font(6, bold=True)
    fnt2 = get_font(5)

    # Charter poster — mounted, pristine
    poster = pygame.Rect(inner.left + 18, inner.top + 18, 60, 80)
    pygame.draw.rect(surface, (245, 235, 200), poster)
    pygame.draw.rect(surface, (130, 90, 30), poster, 1)
    title = fnt.render("LOCAL 404", True, (180, 50, 50))
    surface.blit(title, (poster.left + 4, poster.top + 4))
    sub = fnt2.render("CHARTER", True, (60, 50, 30))
    surface.blit(sub, (poster.left + 4, poster.top + 12))
    # Article rows
    for i in range(6):
        y = poster.top + 22 + i * 8
        pygame.draw.line(surface, (140, 110, 70),
                         (poster.left + 4, y), (poster.right - 4, y), 1)

    # Framed photo (dim back wall)
    frame = pygame.Rect(inner.right - 70, inner.top + 22, 50, 36)
    pygame.draw.rect(surface, (140, 100, 50), frame)
    pygame.draw.rect(surface, (240, 220, 170), frame, 1)
    # Three silhouette heads
    for i, off in enumerate((-12, 0, 12)):
        pygame.draw.circle(surface, (60, 60, 80),
                           (frame.centerx + off, frame.centery - 4), 4)
        pygame.draw.rect(surface, (60, 60, 80),
                         pygame.Rect(frame.centerx + off - 6,
                                     frame.centery, 12, 14))

    # Clipboard hung neatly
    clip = pygame.Rect(inner.left + 12, inner.bottom - 60, 38, 50)
    pygame.draw.rect(surface, (220, 215, 180), clip)
    pygame.draw.rect(surface, (90, 70, 40), clip, 1)
    pygame.draw.rect(surface, (160, 130, 60),
                     pygame.Rect(clip.centerx - 6, clip.top - 4, 12, 6))

    # Scroll text along bottom — drifting charter quote
    scroll_t = (t * 14) % 240
    line = "ARTICLE 7 :: SOLIDARITY :: SHARED PROSPERITY :: SECTION 4.2  "
    txt = fnt.render(line * 3, True, (110, 130, 70))
    band_y = inner.bottom - 12
    surface.set_clip(pygame.Rect(inner.left + 80, band_y - 2,
                                  inner.width - 100, 12))
    surface.blit(txt, (inner.left + 80 - int(scroll_t), band_y))
    surface.set_clip(None)


def _backdrop_corrupt_rep(surface, inner, t):
    """Vinny's barge cockpit — second-hand chair, cigarette burns,
    a half-empty bottle, dim red running lights."""
    cx = inner.centerx
    cy = inner.centery
    fnt = get_font(6, bold=True)

    # Hazy red light bath across the back wall
    hazy = pygame.Surface((inner.width, inner.height), pygame.SRCALPHA)
    hazy.fill((90, 30, 30, 38))
    surface.blit(hazy, (inner.left, inner.top))

    # Bare bulb — flickers
    bulb_pulse = 0.55 + 0.45 * abs(math.sin(t * 6.3))
    pygame.draw.circle(surface, (int(220 * bulb_pulse), int(80 * bulb_pulse), 30),
                       (inner.centerx + 30, inner.top + 14),
                       int(6 + 3 * bulb_pulse))
    pygame.draw.line(surface, (60, 60, 70),
                     (inner.centerx + 30, inner.top),
                     (inner.centerx + 30, inner.top + 8), 1)

    # Half-empty bottle on the dash
    bx = inner.left + 22
    by = inner.bottom - 56
    pygame.draw.rect(surface, (50, 80, 50),
                     pygame.Rect(bx, by, 12, 38))
    pygame.draw.rect(surface, (110, 160, 110),
                     pygame.Rect(bx, by, 12, 38), 1)
    pygame.draw.rect(surface, (40, 60, 30),
                     pygame.Rect(bx + 1, by + 16, 10, 20))
    pygame.draw.rect(surface, (200, 160, 80),
                     pygame.Rect(bx + 2, by + 4, 8, 6))   # label

    # Cigarette burns — three small dots across the dash
    for i, dx in enumerate((40, 70, 100)):
        pygame.draw.circle(surface, (40, 20, 10),
                           (bx + dx, by + 30 + (i % 2) * 4), 2)

    # Cracked dispatch screen — broken with static
    scr = pygame.Rect(inner.right - 78, inner.top + 18, 60, 44)
    pygame.draw.rect(surface, (8, 16, 16), scr)
    pygame.draw.rect(surface, (60, 80, 80), scr, 1)
    # Crack — diagonal lines
    pygame.draw.line(surface, (160, 160, 160),
                     (scr.left + 10, scr.top + 6),
                     (scr.right - 12, scr.bottom - 8), 1)
    pygame.draw.line(surface, (160, 160, 160),
                     (scr.right - 18, scr.top + 4),
                     (scr.left + 14, scr.bottom - 4), 1)
    static_y = scr.top + int((t * 60) % scr.height)
    pygame.draw.line(surface, (140, 140, 140),
                     (scr.left + 2, static_y),
                     (scr.right - 2, static_y), 1)

    # Hand-written sticky note
    note = pygame.Rect(inner.right - 60, inner.bottom - 42, 44, 28)
    pygame.draw.rect(surface, (220, 200, 80), note)
    pygame.draw.rect(surface, (140, 110, 30), note, 1)
    nt = fnt.render("PAY DAY", True, (90, 50, 20))
    surface.blit(nt, (note.left + 6, note.top + 4))
    nt2 = fnt.render("KRELLBORN", True, (60, 30, 10))
    surface.blit(nt2, (note.left + 6, note.top + 14))


_DISPATCH["idealist_rep"]  = _idealist_rep
_DISPATCH["corrupt_rep"]   = _corrupt_rep
_BACKDROPS["idealist_rep"] = _backdrop_idealist_rep
_BACKDROPS["corrupt_rep"]  = _backdrop_corrupt_rep
