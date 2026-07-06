"""Shared retro / satirical sci-fi UI drawing helpers (pygame)."""

from __future__ import annotations

import math
import random
import pygame


from core.text import get_font
def draw_space_crawl(surface: pygame.Surface, lines: list[str], t: float,
                     *, y_start: int = 72, speed: float = 28.0) -> None:
    """Star-Wars parody crawl — yellow italic-ish block drifting upward."""
    w, h = surface.get_size()
    ov = pygame.Surface((w, h), pygame.SRCALPHA)
    ov.fill((0, 0, 0, 140))
    surface.blit(ov, (0, 0))

    f_title = get_font(11, bold=True)
    f_body = get_font(10)
    block_h = 20 + len(lines) * 16
    scroll_y = y_start - int(t * speed) % (h + block_h + 80)

    title = f_title.render("A LONG TIME AGO IN A DEBT SYSTEM FAR, FAR OVERDUE", True, (255, 220, 80))
    ov.blit(title, (w // 2 - title.get_width() // 2, scroll_y))
    y = scroll_y + 22
    for line in lines:
        s = f_body.render(line, True, (255, 235, 120))
        ov.blit(s, (w // 2 - s.get_width() // 2, y))
        y += 16
    surface.blit(ov, (0, 0))


def draw_mario_brick_platform(surf: pygame.Surface, sx: int, y: int, w: int, h: int,
                            brick: tuple, hi: tuple, t: float = 0.0) -> None:
    """8-bit brick blocks with corporate hazard stripe."""
    tile = 14
    pygame.draw.rect(surf, brick, (sx - w // 2, y, w, h))
    for tx in range(sx - w // 2, sx - w // 2 + w, tile):
        for ty in range(y, y + h, tile // 2):
            pygame.draw.rect(surf, hi, (tx, ty, tile - 2, tile // 2 - 2), 1)
    # Mortar shadow
    pygame.draw.line(surf, (0, 0, 0), (sx - w // 2, y + h - 1), (sx + w // 2, y + h - 1), 1)
    # Blinking corporate bolt (question-block energy)
    if int(t * 3) % 2 == 0:
        cx = sx - w // 2 + w // 2
        pygame.draw.rect(surf, (255, 220, 60), (cx - 4, y + 2, 8, 4))
        pygame.draw.rect(surf, (200, 40, 40), (cx - 4, y + h - 6, 8, 3))


def draw_corporate_pipe(surf: pygame.Surface, sx: int, y: int, h: int,
                        body: tuple, hi: tuple) -> None:
    """Green pipe parody — Nova Soma drainage."""
    pw = 22
    pygame.draw.rect(surf, body, (sx - pw // 2, y, pw, h))
    lip_h = 10
    pygame.draw.rect(surf, hi, (sx - pw // 2 - 3, y - lip_h, pw + 6, lip_h))
    pygame.draw.rect(surf, (255, 80, 80), (sx - pw // 2 + 2, y + h // 3, pw - 4, 3))
    f = get_font(6)
    lbl = f.render("NS", True, (20, 20, 20))
    surf.blit(lbl, (sx - lbl.get_width() // 2, y + 4))


def draw_courier_sprite(surf: pygame.Surface, px: int, py: int, t: float, *,
                        inv: bool = False, grounded: bool = True,
                        pose: str | None = None,
                        walk_phase: float | None = None) -> None:
    """
    Detailed sci-fi courier sprite with walk animation.

    px = horizontal centre.  py = sprite top (caller passes self._py - 8 so the
    head clears the ceiling; total sprite height is ~40 px).

    Layout from py:
      py+0  ..  py+10  head / helmet
      py+10 ..  py+13  neck
      py+13 ..  py+25  torso  (shoulder pads extend ±4 px)
      py+25 ..  py+28  hips
      py+28 ..  py+40  legs + boots  (walk-animated)
    Arms hang from shoulders and swing with walk cycle.
    Backpack drawn behind torso (first, so suit overlaps it).
    """
    # ── Palette ───────────────────────────────────────────────────────────────
    if inv:
        c_suit  = (140, 28, 195)
        c_armor = (90, 18, 150)
        c_visor = (255, 80, 255)
        c_vis2  = (180, 30, 180)
        c_helm  = (55, 18, 75)
        c_trim  = (220, 160, 255)
        c_boot  = (38, 10, 55)
        c_pack  = (65, 18, 85)
        c_led   = (255, 100, 255)
        c_led2  = (100, 20, 100)
    else:
        c_suit  = (32, 78, 185)
        c_armor = (52, 60, 80)
        c_visor = (0, 215, 255)
        c_vis2  = (0, 110, 170)
        c_helm  = (42, 48, 62)
        c_trim  = (195, 215, 255)
        c_boot  = (26, 30, 42)
        c_pack  = (50, 56, 70)
        c_led   = (0, 255, 120)
        c_led2  = (10, 70, 35)

    c_badge = (255, 215, 0)
    c_glove = (28, 30, 36)
    c_knee  = (48, 54, 68)
    c_vent  = (255, 55, 30)
    c_white = (240, 245, 255)

    # ── Helpers ───────────────────────────────────────────────────────────────
    def r(x, y, w, h, col, bw=0, bc=None):
        pygame.draw.rect(surf, col, (int(x), int(y), int(w), int(h)))
        if bw:
            pygame.draw.rect(surf, bc or c_trim, (int(x), int(y), int(w), int(h)), bw)

    def ln(x1, y1, x2, y2, col, w=1):
        pygame.draw.line(surf, col, (int(x1), int(y1)), (int(x2), int(y2)), w)

    def circ(cx, cy, rad, col, bw=0, bc=None):
        pygame.draw.circle(surf, col, (int(cx), int(cy)), rad)
        if bw:
            pygame.draw.circle(surf, bc or c_trim, (int(cx), int(cy)), rad, bw)

    def poly(pts, col, bw=0, bc=None):
        ipts = [(int(x), int(y)) for x, y in pts]
        pygame.draw.polygon(surf, col, ipts)
        if bw:
            pygame.draw.polygon(surf, bc or c_trim, ipts, bw)

    # ── Animation state ───────────────────────────────────────────────────────
    # Delivery v2 I.1.3 — pose resolution. Explicit pose wins; legacy callers
    # keep the old grounded-flag behaviour (run when grounded, tuck in air).
    if pose is None:
        pose = "run" if grounded else "jump"
    # walk_phase lets the caller drive leg cadence from actual speed;
    # t keeps driving blinks/LEDs so idling never freezes the electronics.
    wp   = walk_phase if walk_phase is not None else t * 9.0
    blink = int(t * 3.5) % 2 == 0
    blink2 = int(t * 2.0) % 2 == 0

    if pose == "run":
        ll_sw = math.sin(wp)          * 5.5  # left  leg  swing
        lr_sw = math.sin(wp + math.pi) * 5.5  # right leg  swing
        al_sw = math.sin(wp + math.pi) * 4.5  # left  arm  (opposite leg)
        ar_sw = math.sin(wp)          * 4.5  # right arm
        bob   = int(abs(math.sin(wp * 2)) * 1.5)
    elif pose == "idle":
        sway = math.sin(t * 2.2)             # slow breathe, feet planted
        ll_sw = lr_sw = sway * 0.8
        al_sw = ar_sw = -sway * 1.2
        bob   = int(abs(math.sin(t * 2.2)) * 1.0)
    elif pose == "fall":
        ll_sw, lr_sw = -9.0,  8.0            # legs split wide
        al_sw, ar_sw =  9.0, -9.0            # arms flung out
        bob = 0
    elif pose == "skid":
        ll_sw, lr_sw =  9.0,  7.0            # both legs braced forward
        al_sw, ar_sw = -9.0, -7.0            # arms trail behind
        bob = 1
    elif pose == "victory":
        hop = abs(math.sin(t * 6.0))         # bouncing on the spot
        ll_sw = lr_sw = 0.0
        al_sw, ar_sw = -10.0, 10.0           # arms thrown wide
        bob = -int(hop * 3.0)
    else:
        # "jump" — tucked
        ll_sw, lr_sw = -7.0,  5.0
        al_sw, ar_sw = -8.0, -6.0
        bob = 0

    # All y-coords relative to this anchor
    hy = py + bob   # head top

    # ── BACKPACK (behind body) ─────────────────────────────────────────────────
    bpx, bpy = px + 8, hy + 15
    r(bpx,     bpy,     6, 12, c_pack, 1, c_armor)
    # Vent slats
    for vi in range(3):
        r(bpx + 1, bpy + 2 + vi * 3, 4, 2, c_armor)
    # Nozzle
    r(bpx + 1, bpy + 9, 4, 3, (38, 42, 52))
    # Status LED
    r(bpx + 2, bpy, 2, 2, c_vent if blink else (50, 18, 8))

    # ── LEGS ──────────────────────────────────────────────────────────────────
    hip_y = hy + 28

    for side, sw in ((-1, ll_sw), (1, lr_sw)):
        ox  = px + side * 4        # thigh root x
        # Knee position
        kx = ox + sw * 0.65
        ky = hip_y + 6
        # Ankle
        ax = kx + sw * 0.20
        ay = ky + 6
        # Thigh (fat line)
        ln(ox, hip_y, kx, ky, c_suit, 5)
        # Knee pad
        circ(kx, ky, 4, c_knee, 1, c_armor)
        # Shin
        ln(kx, ky, ax, ay, c_suit, 4)
        # Boot block
        blx = ax - 4 if side == -1 else ax - 3
        r(blx, ay, 9, 4, c_boot, 1, c_armor)
        r(blx, ay + 2, 9, 2, c_armor)  # sole stripe

    # ── TORSO ─────────────────────────────────────────────────────────────────
    tx, tyw  = px - 8, 16
    ty, twh  = hy + 13, 13

    # Body suit
    r(tx, ty, tyw, twh, c_suit, 1, c_trim)

    # Chest armour plate
    r(tx + 3, ty + 2, 10, 8, c_armor, 1, (75, 85, 105))

    # ID badge  (gold card, 2 data-line details)
    r(tx + 4, ty + 3, 6, 4, c_badge)
    ln(tx + 5, ty + 4, tx + 9, ty + 4, (90, 65, 0))
    ln(tx + 5, ty + 5, tx + 8, ty + 5, (90, 65, 0))

    # Chest indicator LED
    ci_col = c_led if blink2 else c_led2
    circ(tx + 12, ty + 3, 2, ci_col)

    # Belt
    r(tx + 3, ty + twh - 3, 10, 3, c_knee, 1, c_armor)
    r(tx + 6, ty + twh - 3, 4, 3, c_armor)   # buckle

    # Shoulder pads
    for side in (-1, 1):
        spx = (tx - 4) if side == -1 else (tx + tyw)
        r(spx, ty, 5, 7, c_armor, 1, c_trim)
        # Shoulder LED (left = green status, right = orange warning)
        sl_col = (c_led if blink else c_led2) if side == -1 else \
                 (c_vent if blink2 else (60, 18, 8))
        circ(spx + 2, ty + 2, 2, sl_col)

    # ── ARMS ──────────────────────────────────────────────────────────────────
    for side, sw in ((-1, al_sw), (1, ar_sw)):
        shx = px + side * 9
        shy = hy + 16
        # Elbow
        ex = shx + sw * 0.55 + side
        ey = shy + 7
        # Hand
        hx2 = ex + sw * 0.30
        hy2 = ey + 6
        ln(shx, shy, ex, ey, c_suit, 4)          # upper arm
        circ(ex, ey, 3, c_knee, 1, c_armor)       # elbow
        ln(ex, ey, hx2, hy2, c_suit, 3)           # forearm
        circ(hx2, hy2, 3, c_glove, 1, c_trim)     # glove

    # ── NECK / COLLAR ─────────────────────────────────────────────────────────
    r(px - 3, hy + 10, 6, 4, c_suit)
    r(px - 4, hy + 12, 8, 2, c_armor)

    # ── HELMET ────────────────────────────────────────────────────────────────
    hx0, hw0 = px - 8, 16
    hh0       = 11

    # Dome polygon (hexagonal crown)
    poly([(hx0 + 3,  hy),
          (hx0 + hw0 - 3, hy),
          (hx0 + hw0,     hy + 3),
          (hx0 + hw0,     hy + hh0),
          (hx0,           hy + hh0),
          (hx0,           hy + 3)], c_helm, 1, c_trim)

    # Visor slit
    vy = hy + 3
    r(hx0 + 2, vy, hw0 - 4, 5, c_vis2)
    r(hx0 + 2, vy, hw0 - 4, 2, c_visor)          # bright top strip
    ln(hx0 + 3, vy + 1, hx0 + 7, vy + 1, c_white) # reflection gleam

    # Chin seal
    r(hx0 + 2, hy + hh0 - 3, hw0 - 4, 3, c_armor, 1, c_helm)

    # Ear comm-units
    for side in (-1, 1):
        ex2 = (hx0 - 3) if side == -1 else (hx0 + hw0)
        r(ex2, hy + 3, 3, 6, c_armor, 1, c_trim)
        ec_col = c_led if (int(t * 2.0 + (0 if side == -1 else 1)) % 2 == 0) else c_led2
        circ(ex2 + 1, hy + 5, 2, ec_col)

    # Antenna (tilted right)
    ln(hx0 + hw0 - 3, hy, hx0 + hw0 + 2, hy - 7, c_trim)
    circ(hx0 + hw0 + 2, hy - 7, 2, c_led if blink else c_led2)

    # Centre-top ridge
    r(px - 1, hy, 2, 3, c_armor)

    # Helmet hazard stripe (thin amber band across front)
    r(hx0 + 2, hy + hh0 - 5, hw0 - 4, 2, (200, 130, 0))


def _rgba(r: int, g: int, b: int, a: int) -> tuple[int, int, int, int]:
    """Clamp channel values for pygame SRCALPHA fills."""
    return (
        max(0, min(255, int(r))),
        max(0, min(255, int(g))),
        max(0, min(255, int(b))),
        max(0, min(255, int(a))),
    )


def draw_terminal_backdrop(surface: pygame.Surface, t: float) -> None:
    """Subtle phosphor wash — no full-screen stripe overlays (terminal draws its own scanlines)."""
    w, h = surface.get_size()
    pulse = 0.5 + 0.5 * math.sin(t * 0.6)
    wash = pygame.Surface((w, h), pygame.SRCALPHA)
    wash.fill(_rgba(14, 48, 26, int(5 + 3 * pulse)))
    surface.blit(wash, (0, 0))
    # Corner status LEDs
    for i, (lx, ly) in enumerate([(12, 12), (w - 20, 12), (12, h - 20), (w - 20, h - 20)]):
        on = math.sin(t * 2.5 + i) > 0.2
        col = (0, 255, 120) if on else (30, 50, 30)
        pygame.draw.circle(surface, col, (lx, ly), 3)


def draw_landing_star_destroyer(surface: pygame.Surface, cx: int, cy: int,
                                scale: float, t: float, col_hull: tuple,
                                col_trim: tuple) -> None:
    """Oversized wedge station — Spaceballs scale joke."""
    sw = int(380 * scale)
    sh = int(120 * scale)
    pts = [
        (cx + sw // 2, cy),
        (cx - sw // 2, cy - sh // 3),
        (cx - sw // 2, cy + sh // 3),
    ]
    pygame.draw.polygon(surface, col_hull, pts)
    pygame.draw.polygon(surface, col_trim, pts, max(2, int(2 * scale)))
    # Ridiculous bridge tower
    tw = int(40 * scale)
    th = int(90 * scale)
    pygame.draw.rect(surface, col_trim,
                     (cx + sw // 4, cy - th // 2, tw, th))
    # Running gag label
    if scale > 0.4:
        f = get_font(max(8, int(10 * scale)), bold=True)
        s = f.render("DEFINITELY NOT A TRAP", True, (255, 80, 80))
        surface.blit(s, (cx - s.get_width() // 2, cy + sh // 3 + 6))
    # Engine glow
    pulse = 0.5 + 0.5 * math.sin(t * 5)
    pygame.draw.circle(surface, (int(255 * pulse), int(120 * pulse), 0),
                       (cx - sw // 2 - 8, cy), max(3, int(6 * scale)))
