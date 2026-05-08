"""
Procedural vector portraits for terminal NPCs.
All geometry uses pygame.draw — no sprites.
"""
from __future__ import annotations
import math
import random
import pygame
from config import settings as S

# Maps the NPC .name string to a portrait key
_NAME_TO_KEY = {
    "GARY":       "gary",
    "TK-9":       "synthetic_droid",
    "DISPATCHER": "union_dispatcher",
}


def draw_portrait(surface: pygame.Surface, npc_name: str,
                  rect: pygame.Rect, disposition: int = 0, t: float = 0.0):
    key = _NAME_TO_KEY.get(npc_name.upper(), "unknown")
    fn  = _DISPATCH.get(key, _unknown)
    # Centre portrait in top 2/3 of rect
    cx = rect.centerx
    cy = rect.top + int(rect.height * 0.40)
    scale = min(rect.width, rect.height * 0.65) / 200.0
    fn(surface, cx, cy, scale, disposition, t)


# ---------------------------------------------------------------------------
# Gary — tired Local 404 field agent

def _gary(surface, cx, cy, s, disposition, t):
    amb = S.AMBER_TERM
    dim = (92, 66, 0)
    bg  = (22, 16, 0)

    # Head
    pygame.draw.ellipse(surface, bg,
        pygame.Rect(int(cx-56*s), int(cy-68*s), int(112*s), int(128*s)))
    pygame.draw.ellipse(surface, dim,
        pygame.Rect(int(cx-56*s), int(cy-68*s), int(112*s), int(128*s)), 2)

    # Under-eye shadow
    for gx in (-38, 8):
        pygame.draw.ellipse(surface, (52, 36, 0),
            pygame.Rect(int(cx+gx*s), int(cy-22*s), int(30*s), int(10*s)))

    # Eyes — open wider when friendly, squint when hostile
    eh = max(2, int((4 + max(0, disposition) * 0.6) * s))
    for gx in (-38, 10):
        pygame.draw.ellipse(surface, amb,
            pygame.Rect(int(cx+gx*s), int(cy-28*s), int(26*s), eh))

    # Pupils
    for gx in (-25, 23):
        pygame.draw.circle(surface, (0, 0, 0),
            (int(cx+gx*s), int(cy-26*s)), max(2, int(4*s)))

    # Nose bridge
    for dx, x2 in ((-4, -9), (4, 9)):
        pygame.draw.line(surface, dim,
            (int(cx+dx*s), int(cy-4*s)), (int(cx+x2*s), int(cy+12*s)), 2)

    # Mouth — frown neutral, smile when disposition high
    mouth_y = int(cy + 28*s)
    if disposition >= 3:
        pygame.draw.arc(surface, dim,
            pygame.Rect(int(cx-20*s), mouth_y-8, int(40*s), int(10*s)),
            math.pi, 2*math.pi, 2)
    else:
        pygame.draw.arc(surface, dim,
            pygame.Rect(int(cx-20*s), mouth_y, int(40*s), int(8*s)),
            0, math.pi, 2)

    # Stubble (deterministic random)
    rng = random.Random(42)
    for _ in range(20):
        sx = int(cx + rng.uniform(-46, 46) * s)
        sy = int(cy + rng.uniform(6, 46) * s)
        pygame.draw.circle(surface, (100, 72, 0), (sx, sy), max(1, int(1.5*s)))

    # Collar
    pygame.draw.line(surface, dim,
        (int(cx-34*s), int(cy+64*s)), (int(cx-10*s), int(cy+52*s)), 2)
    pygame.draw.line(surface, dim,
        (int(cx+34*s), int(cy+64*s)), (int(cx+10*s), int(cy+52*s)), 2)

    # Union badge
    badge = pygame.Rect(int(cx-18*s), int(cy+52*s), int(16*s), int(11*s))
    pygame.draw.rect(surface, (18, 13, 0), badge)
    pygame.draw.rect(surface, amb, badge, 1)
    font = pygame.font.SysFont("monospace", max(7, int(7*s)))
    surface.blit(font.render("404", True, amb), badge.topleft)


# ---------------------------------------------------------------------------
# TK-9 — compliance droid

def _synthetic_droid(surface, cx, cy, s, disposition, t):
    if disposition >= 3:
        eye_col = (0, 220, 210)
    elif disposition <= -3:
        eye_col = (220, 40, 40)
    else:
        eye_col = S.AMBER_TERM

    bg   = (12, 18, 22)
    edge = (70, 90, 105)
    pan  = (36, 46, 56)

    # Hexagonal head
    pts = [
        (int(cx-46*s), int(cy-54*s)),
        (int(cx+46*s), int(cy-54*s)),
        (int(cx+62*s), int(cy-18*s)),
        (int(cx+62*s), int(cy+42*s)),
        (int(cx-62*s), int(cy+42*s)),
        (int(cx-62*s), int(cy-18*s)),
    ]
    pygame.draw.polygon(surface, bg, pts)
    pygame.draw.polygon(surface, edge, pts, 2)

    # Horizontal panel seams
    for dy in (-28, -2, 22):
        pygame.draw.line(surface, pan,
            (int(cx-56*s), int(cy+dy*s)), (int(cx+56*s), int(cy+dy*s)), 1)

    # LED eye bars
    ey = int(cy - 30*s)
    eh = max(3, int(9*s))
    pygame.draw.rect(surface, (0, 0, 0),
        pygame.Rect(int(cx-50*s), ey-2, int(100*s), eh+4))
    pygame.draw.rect(surface, eye_col,
        pygame.Rect(int(cx-48*s), ey, int(38*s), eh))
    pygame.draw.rect(surface, eye_col,
        pygame.Rect(int(cx+10*s), ey, int(38*s), eh))

    # Pulsing glow overlay on eyes
    ga = int(55 + 35 * math.sin(t * 2.0))
    gs = pygame.Surface((int(100*s), eh+10), pygame.SRCALPHA)
    pygame.draw.rect(gs, (*eye_col, ga), pygame.Rect(0, 0, int(100*s), eh+10))
    surface.blit(gs, (int(cx-50*s), ey-5))

    # Mouth ventilation grille
    for i in range(4):
        gy = int(cy + 10*s + i*5*s)
        pygame.draw.line(surface, pan, (int(cx-28*s), gy), (int(cx+28*s), gy), 1)

    # Antenna
    pygame.draw.line(surface, edge,
        (int(cx+22*s), int(cy-54*s)), (int(cx+34*s), int(cy-82*s)), 2)
    pygame.draw.circle(surface, eye_col,
        (int(cx+34*s), int(cy-84*s)), max(2, int(3*s)))

    # Neck bolts
    for bx in (-44, 44):
        pygame.draw.circle(surface, edge,
            (int(cx+bx*s), int(cy+44*s)), max(3, int(5*s)))
        pygame.draw.circle(surface, pan,
            (int(cx+bx*s), int(cy+44*s)), max(1, int(2*s)))


# ---------------------------------------------------------------------------
# Dispatcher — union bureaucrat

def _union_dispatcher(surface, cx, cy, s, disposition, t):
    amb = S.AMBER_TERM
    dim = (92, 66, 0)
    bg  = (22, 16, 0)

    # Round head
    pygame.draw.ellipse(surface, bg,
        pygame.Rect(int(cx-58*s), int(cy-64*s), int(116*s), int(114*s)))
    pygame.draw.ellipse(surface, dim,
        pygame.Rect(int(cx-58*s), int(cy-64*s), int(116*s), int(114*s)), 2)

    # Glasses
    for gx in (-22, 22):
        pygame.draw.circle(surface, dim, (int(cx+gx*s), int(cy-18*s)), int(18*s), 2)
        ls = pygame.Surface((int(36*s), int(36*s)), pygame.SRCALPHA)
        pygame.draw.circle(ls, (255, 176, 0, 18), (int(18*s), int(18*s)), int(18*s))
        surface.blit(ls, (int(cx+gx*s-18*s), int(cy-18*s-18*s)))
    pygame.draw.line(surface, dim,
        (int(cx-4*s), int(cy-18*s)), (int(cx+4*s), int(cy-18*s)), 2)

    # Eyes
    for gx in (-22, 22):
        pygame.draw.ellipse(surface, amb,
            pygame.Rect(int(cx+gx*s-8*s), int(cy-22*s), int(16*s), int(7*s)))

    # Nose
    for dx, x2 in ((-0, -6), (0, 6)):
        pygame.draw.line(surface, dim,
            (int(cx+dx*s), int(cy-4*s)), (int(cx+x2*s), int(cy+12*s)), 2)

    # Mouth
    mx = int(cy + 22*s)
    if disposition >= 2:
        pygame.draw.arc(surface, dim,
            pygame.Rect(int(cx-18*s), mx-6, int(36*s), int(8*s)),
            math.pi, 2*math.pi, 2)
    else:
        pygame.draw.line(surface, dim,
            (int(cx-18*s), mx), (int(cx+18*s), mx), 2)

    # Headset arc
    pygame.draw.arc(surface, dim,
        pygame.Rect(int(cx-62*s), int(cy-80*s), int(124*s), int(52*s)),
        0, math.pi, 3)
    pygame.draw.circle(surface, dim,
        (int(cx-62*s), int(cy-54*s)), max(4, int(8*s)), 2)
    pygame.draw.line(surface, dim,
        (int(cx-62*s), int(cy-46*s)), (int(cx-46*s), int(cy-8*s)), 2)
    pygame.draw.circle(surface, amb,
        (int(cx-46*s), int(cy-6*s)), max(3, int(4*s)))

    # Collar and tie
    pygame.draw.line(surface, dim,
        (int(cx-36*s), int(cy+56*s)), (int(cx-9*s), int(cy+44*s)), 2)
    pygame.draw.line(surface, dim,
        (int(cx+36*s), int(cy+56*s)), (int(cx+9*s), int(cy+44*s)), 2)
    tie = [(int(cx), int(cy+42*s)), (int(cx-8*s), int(cy+52*s)),
           (int(cx), int(cy+72*s)), (int(cx+8*s), int(cy+52*s))]
    pygame.draw.polygon(surface, (38, 28, 0), tie)
    pygame.draw.polygon(surface, dim, tie, 1)


# ---------------------------------------------------------------------------
def _unknown(surface, cx, cy, s, disposition, t):
    pygame.draw.circle(surface, (35, 35, 35), (int(cx), int(cy)), int(60*s), 2)
    font = pygame.font.SysFont("monospace", max(12, int(38*s)))
    surf = font.render("?", True, S.AMBER_TERM)
    surface.blit(surf, (int(cx - surf.get_width()//2), int(cy - surf.get_height()//2)))


_DISPATCH = {
    "gary":             _gary,
    "synthetic_droid":  _synthetic_droid,
    "union_dispatcher": _union_dispatcher,
    "unknown":          _unknown,
}
