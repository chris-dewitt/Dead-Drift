"""
Delivery sequence — fires at the end of a successful 5-sector run.
Three chained phases:
  1. APPROACH  — steer ship into station docking bay
  2. LAND      — descend to landing pad (resist gravity with thrust)
  3. RUN       — on-foot platformer through the station corridor
  4. RESULT    — payout card + debt adjustment + Bax wrap-up
"""
from __future__ import annotations
import math
import random
import pygame

from delivery.corridor import make_corridor
from delivery.corridor.elements import CORRIDOR_W, CORRIDOR_H
from config import settings as S
from renderer.sci_fi_ui import draw_space_crawl
from core.text import get_font

_APPROACH_CRAWL = [
    "Episode MCLXIV: THE DEBT STRIKES BACK (AT YOUR WALLET)",
    "A reckless courier. A rusted ship. Crushing compound interest.",
    "The Union of Repo Men demands satisfaction. Again.",
]
from core.event_bus import bus, EVT_BAX_SPEAK, EVT_DOCK_APPROACH, EVT_DOCK_PERFECT, EVT_DOCK_ROUGH

# ── Payout config ──────────────────────────────────────────────────────────
_DELIVERY_BONUS   = {3: 8000, 2: 4000, 1: 1000}   # credits added
_DELIVERY_FEE_CUT = {3: 0,    2: 0,    1: 2000}    # credits docked from meta.debt

_BAX_APPROACH = [
    "Station on sensors. Bay Three, apparently. Sounds made up.",
    "Right, line her up nice. I'll pretend I'm not nervous.",
    "Union station. All smiles, yeah? We're just a PERFECTLY NORMAL courier.",
]
_BAX_LAND = [
    "Easy does it. EASY. That's a landing pad, not a crash mat.",
    "Descent rate's a bit spicy. Less spicy would be ideal.",
    "Set her down gently and I'll buy you a metaphorical pint.",
]
_BAX_APPROACH_MISS = [
    "...You missed the bay a little. A lot. We're going round again.",
    "Classic. Bay's QUITE WIDE and we still grazed the edge.",
]
_BAX_LAND_ROUGH = [
    "That was ROUGH, mate. I've got rattled in me chassis.",
    "Gentle. GENTLE. Do you know that word? Look it up.",
]
_BAX_LAND_SMOOTH = [
    "Silk. Pure SILK. I'm actually impressed.",
    "Textbook. If the textbook was written by someone good.",
]


# ── Phase constants ─────────────────────────────────────────────────────────
_APPROACH_DURATION = 5.0    # seconds to fly into the bay (Beat 1)
_BEAT2_DURATION    = 4.0    # seconds for gauge + burn (Beat 2)
_BEAT3_DURATION    = 6.0    # seconds for cutscene     (Beat 3)
_RESULT_HOLD       = 4.0    # seconds to show result card

# Chapter station themes: (primary_col, accent_col, name)
_STATION_THEMES = {
    1: ((160, 80, 30),  (220, 120, 40), "DEPOT NINE / RECORD EXCHANGE"),
    2: ((40, 120, 200), (80, 200, 160), "BIOLAB STATION RAYA-7"),
    3: ((140, 160, 80), (180, 200, 100), "NOVA SOMA COMPLIANCE HUB 3"),
    4: ((200, 160, 40), (255, 210, 80), "THE MERIDIAN HOTEL — ORBITAL"),
}


def _scaled_rect(cx: int, cy: int, ox: float, oy: float,
                 w: float, h: float, scale: float) -> pygame.Rect:
    return pygame.Rect(
        int(cx + ox * scale - w * scale / 2),
        int(cy + oy * scale - h * scale / 2),
        max(1, int(w * scale)),
        max(1, int(h * scale)),
    )


def _draw_chapter_station_exterior(surface: pygame.Surface, cx: int, cy: int,
                                   scale: float, t: float, chapter: int) -> None:
    hull, trim, _name = _STATION_THEMES.get(chapter, _STATION_THEMES[1])
    dark = tuple(max(0, c // 4) for c in hull)
    glow = 0.45 + 0.55 * abs(math.sin(t * 2.2))
    glow_col = tuple(min(255, int(c * glow)) for c in trim)

    if chapter == 2:
        ring_w = max(20, int(310 * scale))
        ring_h = max(12, int(142 * scale))
        pygame.draw.ellipse(surface, dark, (cx - ring_w // 2, cy - ring_h // 2, ring_w, ring_h), 4)
        pygame.draw.ellipse(surface, trim, (cx - ring_w // 2, cy - ring_h // 2, ring_w, ring_h),
                            max(1, int(3 * scale)))
        pygame.draw.rect(surface, hull, _scaled_rect(cx, cy, 0, 0, 150, 54, scale))
        pygame.draw.rect(surface, trim, _scaled_rect(cx, cy, 0, 0, 150, 54, scale),
                         max(1, int(2 * scale)))
        for ox in (-92, -46, 46, 92):
            pod = _scaled_rect(cx, cy, ox, 0, 28, 76, scale)
            pygame.draw.ellipse(surface, (12, 30, 38), pod)
            pygame.draw.ellipse(surface, glow_col, pod, max(1, int(2 * scale)))
        for ox in (-120, 120):
            wing = [
                (cx + int(ox * scale), cy),
                (cx + int((ox + (38 if ox > 0 else -38)) * scale), cy - int(54 * scale)),
                (cx + int((ox + (38 if ox > 0 else -38)) * scale), cy + int(54 * scale)),
            ]
            pygame.draw.polygon(surface, (18, 48, 60), wing)
            pygame.draw.polygon(surface, trim, wing, max(1, int(2 * scale)))
    elif chapter == 3:
        body = _scaled_rect(cx, cy, 0, 0, 160, 220, scale)
        pygame.draw.rect(surface, hull, body)
        pygame.draw.rect(surface, trim, body, max(1, int(3 * scale)))
        for ox in (-88, 88):
            tower = _scaled_rect(cx, cy, ox, 8, 54, 170, scale)
            pygame.draw.rect(surface, dark, tower)
            pygame.draw.rect(surface, trim, tower, max(1, int(2 * scale)))
        for row in range(-4, 5):
            for col in range(-2, 3):
                if (row + col) % 2 == 0:
                    win = _scaled_rect(cx, cy, col * 23, row * 22, 9, 7, scale)
                    pygame.draw.rect(surface, glow_col, win)
        logo = _scaled_rect(cx, cy, 0, -82, 70, 28, scale)
        pygame.draw.rect(surface, (8, 16, 8), logo)
        pygame.draw.rect(surface, trim, logo, 1)
        if scale > 0.35:
            font = get_font(max(8, int(13 * scale)), bold=True)
            ns = font.render("NS", True, trim)
            surface.blit(ns, (logo.centerx - ns.get_width() // 2,
                              logo.centery - ns.get_height() // 2))
    elif chapter == 4:
        for r_i, rr in enumerate((150, 112, 76)):
            rect = pygame.Rect(cx - int(rr * scale), cy - int((rr * 0.42) * scale),
                               max(2, int(rr * 2 * scale)), max(2, int(rr * 0.84 * scale)))
            col = trim if r_i == 0 else glow_col
            pygame.draw.ellipse(surface, dark, rect, max(1, int(3 * scale)))
            pygame.draw.ellipse(surface, col, rect, max(1, int(2 * scale)))
        spine = _scaled_rect(cx, cy, 18, 0, 54, 210, scale)
        pygame.draw.rect(surface, hull, spine)
        pygame.draw.rect(surface, trim, spine, max(1, int(2 * scale)))
        for k in range(8):
            yy = cy - int(86 * scale) + int(k * 24 * scale)
            wx = cx + int((18 + math.sin(t * 0.8 + k) * 18) * scale)
            pygame.draw.circle(surface, glow_col, (wx, yy), max(1, int(3 * scale)))
        crown = [
            (cx + int(18 * scale), cy - int(128 * scale)),
            (cx - int(36 * scale), cy - int(82 * scale)),
            (cx + int(72 * scale), cy - int(82 * scale)),
        ]
        pygame.draw.polygon(surface, (40, 30, 8), crown)
        pygame.draw.polygon(surface, trim, crown, max(1, int(2 * scale)))
    else:
        pier = _scaled_rect(cx, cy, 0, 20, 250, 72, scale)
        pygame.draw.rect(surface, hull, pier)
        pygame.draw.rect(surface, trim, pier, max(1, int(3 * scale)))
        for i, ox in enumerate((-92, -46, 0, 46, 92)):
            cont = _scaled_rect(cx, cy, ox, -42 - (i % 2) * 28, 42, 26, scale)
            shade = (max(10, hull[0] - i * 12), max(10, hull[1] - i * 5), max(8, hull[2]))
            pygame.draw.rect(surface, shade, cont)
            pygame.draw.rect(surface, trim, cont, 1)
        for ox, flip in ((-126, 1), (118, -1)):
            mast_x = cx + int(ox * scale)
            mast_y = cy - int(74 * scale)
            pygame.draw.line(surface, trim, (mast_x, mast_y), (mast_x, cy + int(28 * scale)),
                             max(1, int(2 * scale)))
            arm_end = (mast_x + flip * int(64 * scale), mast_y + int(10 * scale))
            pygame.draw.line(surface, trim, (mast_x, mast_y), arm_end, max(1, int(2 * scale)))
            pygame.draw.line(surface, glow_col, arm_end, (arm_end[0], arm_end[1] + int(24 * scale)), 1)
        under = _scaled_rect(cx, cy, 0, 72, 280, 22, scale)
        pygame.draw.rect(surface, (32, 18, 8), under)
        pygame.draw.rect(surface, trim, under, 1)

    if scale > 0.4:
        font = get_font(max(8, int(9 * scale)), bold=True)
        label = font.render(_STATION_THEMES.get(chapter, _STATION_THEMES[1])[2].split(" / ")[0],
                            True, trim)
        surface.blit(label, (cx - label.get_width() // 2, cy + int(116 * scale)))


def _draw_chapter_bay_dressing(surface: pygame.Surface, W: int, H: int,
                               t: float, chapter: int) -> None:
    hull, trim, name = _STATION_THEMES.get(chapter, _STATION_THEMES[1])
    low = tuple(max(3, c // 5) for c in hull)
    mid = tuple(max(10, c // 2) for c in hull)
    pulse = 0.45 + 0.55 * abs(math.sin(t * 2.0))
    lit = tuple(min(255, int(c * pulse)) for c in trim)

    if chapter == 2:
        for x in (132, W - 172):
            tank = pygame.Rect(x, 118, 54, 126)
            pygame.draw.ellipse(surface, low, (tank.x, tank.y - 12, tank.w, 24))
            pygame.draw.rect(surface, low, tank)
            pygame.draw.ellipse(surface, mid, (tank.x, tank.bottom - 12, tank.w, 24))
            pygame.draw.rect(surface, trim, tank, 1)
            for y in range(tank.y + 20, tank.bottom - 10, 24):
                pygame.draw.line(surface, lit, (tank.x + 8, y), (tank.right - 8, y), 1)
        pygame.draw.arc(surface, lit, (W // 2 - 250, 74, 500, 90), 0, math.pi, 2)
    elif chapter == 3:
        logo = pygame.Rect(W // 2 - 82, 112, 164, 62)
        pygame.draw.rect(surface, (8, 12, 8), logo)
        pygame.draw.rect(surface, trim, logo, 2)
        font = get_font(24, bold=True)
        txt = font.render("NOVA SOMA", True, lit)
        surface.blit(txt, (logo.centerx - txt.get_width() // 2, logo.y + 9))
        for x in range(116, W - 116, 42):
            for y in range(198, H - 168, 32):
                pygame.draw.rect(surface, mid, (x, y, 18, 9))
    elif chapter == 4:
        for x in range(116, W - 116, 78):
            pygame.draw.arc(surface, lit, (x - 18, 92, 58, 150), math.pi, math.tau, 2)
            pygame.draw.circle(surface, lit, (x + 11, 102), 3)
        carpet = pygame.Rect(W // 2 - 74, 184, 148, H - 264)
        pygame.draw.polygon(surface, (38, 22, 8), [
            (carpet.centerx - 18, carpet.y), (carpet.centerx + 18, carpet.y),
            (carpet.right, carpet.bottom), (carpet.left, carpet.bottom),
        ])
        pygame.draw.line(surface, trim, (carpet.centerx, carpet.y), (carpet.centerx, carpet.bottom), 1)
    else:
        for i, x in enumerate((116, 168, W - 198, W - 146)):
            h = 54 + (i % 2) * 18
            crate = pygame.Rect(x, H - 228 - h, 44, h)
            pygame.draw.rect(surface, low, crate)
            pygame.draw.rect(surface, trim, crate, 1)
            pygame.draw.line(surface, mid, crate.midleft, crate.midright, 1)
        for x in (142, W - 154):
            pygame.draw.line(surface, trim, (x, 88), (x, 204), 2)
            pygame.draw.line(surface, trim, (x, 88), (x + (46 if x < W // 2 else -46), 124), 2)

    placard = pygame.Rect(W // 2 - 164, 48, 328, 28)
    pygame.draw.rect(surface, (5, 8, 7), placard)
    pygame.draw.rect(surface, trim, placard, 1)
    font = get_font(10, bold=True)
    txt = font.render(name.upper(), True, lit)
    surface.blit(txt, (placard.centerx - txt.get_width() // 2,
                       placard.centery - txt.get_height() // 2))


class DeliverySequence:
    PHASE_APPROACH = "approach"   # Beat 1: nose alignment
    PHASE_LAND     = "land"       # Beat 2: J-gauge + SPACE burn
    PHASE_BEAT3    = "beat3"      # Beat 3: docking cutscene
    PHASE_RUN      = "run"
    PHASE_RESULT   = "result"

    def __init__(self, meta, chapter: int = 1):
        self.meta    = meta
        self.chapter = chapter
        self._phase  = self.PHASE_APPROACH
        self._t      = 0.0

        # Approach state (Beat 1)
        self._ship_screen_x = float(S.SCREEN_W // 4)
        self._ship_screen_y = float(S.SCREEN_H // 2)
        self._bay_cx        = S.SCREEN_W * 0.72   # world centre of bay opening
        self._approach_offset = 0.0
        self._ship_angle    = -15.0  # degrees; 0 = nose pointing right toward bay
        self._aligned       = False
        self._align_held_t  = 0.0
        self._lock_flash_t  = 0.0

        # Landing state (Beat 2) — Epic 14.2: continuous speed-dock gauge.
        # Legacy fields kept so Beat 3 scoring display stays compatible.
        self._land_sub        = "speed_dock"   # always 'speed_dock' in new design
        self._land_sub_t      = 0.0
        self._j_hit           = False     # set by _finish_dock for Beat 3 display
        self._burn_done       = False     # set by _finish_dock for Beat 3 display
        self._burn_overshoot  = False     # set by _finish_dock for Beat 3 display
        self._land_y          = 60.0
        self._land_score      = 0
        self._beat2_sub_t     = 0.0
        # Epic 14.2 — speed-dock minigame state
        self._dock_speed         = 0.55     # current displayed speed 0..1
        self._dock_speed_target  = 0.55     # player-driven target
        self._dock_distance      = 1.0      # 1=far, 0=docked
        self._dock_in_zone_t     = 0.0      # accumulated time in green band
        self._dock_total_t       = 0.0      # total Beat 2 time elapsed
        self._dock_overshoots    = 0        # count of overshoot events
        self._dock_idle_t        = 0.0      # accumulated idle time
        self._dock_over_held_t   = 0.0      # held-over-zone timer
        self._dock_angle         = 0.0      # ship pitch (auto-corrected ±20°)
        self._dock_abort_t       = 0.0      # extreme-angle abort accumulator

        # Beat 3: cutscene
        self._clamp_anim_t  = 0.0
        self._dock_bonus_cr = 0      # +500 perfect, -200 both missed

        # Run state
        self._run = None
        self._run_stars = 0

        # Result
        self._result_t = 0.0
        self._bonus    = 0
        self._fee_cut  = 0
        self._done     = False

        # Approach stars track
        self._approach_score = 0   # 0=miss, 1=ok, 2=centred

        bus.emit(EVT_DOCK_APPROACH)

    # ── Public interface ──────────────────────────────────────────────────
    def handle_key(self, event: pygame.event.Event):
        if self._phase == self.PHASE_APPROACH:
            pass   # A/D rotation via held keys in update
        elif self._phase == self.PHASE_LAND:
            # Epic 14.2 — all input is held-key (W/S/A/D); no discrete triggers
            pass
        elif self._phase == self.PHASE_RUN:
            if self._run is not None:
                self._run.handle_key(event)

    def handle_keyup(self, event: pygame.event.Event):
        pass  # Beat 2 no longer needs key-release tracking

    def update(self, dt: float):
        self._t += dt
        if self._phase == self.PHASE_APPROACH:
            self._update_approach(dt)
        elif self._phase == self.PHASE_LAND:
            self._update_land(dt)
        elif self._phase == self.PHASE_BEAT3:
            self._update_beat3(dt)
        elif self._phase == self.PHASE_RUN:
            self._update_run(dt)
        elif self._phase == self.PHASE_RESULT:
            self._result_t -= dt
            if self._result_t <= 0:
                self._done = True

    def draw(self, surface: pygame.Surface):
        W, H = surface.get_size()
        if self._phase == self.PHASE_APPROACH:
            self._draw_approach(surface, W, H)
        elif self._phase == self.PHASE_LAND:
            self._draw_land(surface, W, H)
        elif self._phase == self.PHASE_BEAT3:
            self._draw_beat3(surface, W, H)
        elif self._phase == self.PHASE_RUN:
            self._draw_run(surface, W, H)
        elif self._phase == self.PHASE_RESULT:
            self._draw_result(surface, W, H)

    @property
    def is_done(self) -> bool:
        return self._done

    # ── Phase: Approach (Beat 1 — nose alignment) ────────────────────────
    def _update_approach(self, dt: float):
        keys = pygame.key.get_pressed()
        # A/D rotate nose angle; W/S translate vertically for positioning
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            self._ship_angle -= 80.0 * dt
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            self._ship_angle += 80.0 * dt
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            self._ship_screen_y -= 100.0 * dt
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            self._ship_screen_y += 100.0 * dt
        self._ship_angle = max(-60.0, min(60.0, self._ship_angle))

        # Ship auto-advances toward station
        self._ship_screen_x += 60.0 * dt

        # Alignment detection: nose within ±30° of straight-ahead (0°)
        if abs(self._ship_angle) < 30.0:
            self._aligned      = True
            self._align_held_t += dt
            self._lock_flash_t  = 0.3
        else:
            self._aligned      = False
            self._align_held_t = 0.0

        self._lock_flash_t = max(0.0, self._lock_flash_t - dt)

        # Advance: magnetic lock after 0.5s aligned, or timeout
        should_advance = self._align_held_t >= 0.5 or self._t >= _APPROACH_DURATION
        if should_advance:
            if self._aligned:
                self._approach_score = 2
            elif self._t < _APPROACH_DURATION:
                self._approach_score = 1
            else:
                self._approach_score = 0
                bus.emit(EVT_BAX_SPEAK, line=random.choice(_BAX_APPROACH_MISS))
            self._t             = 0.0
            self._phase         = self.PHASE_LAND
            self._land_sub      = "j_align"
            self._land_sub_t    = 0.0
            self._j_marker_t    = 0.0
            self._j_hit         = False
            self._j_resolved    = False
            self._burn_fill     = 0.0
            self._burn_holding  = False
            self._burn_done     = False
            self._burn_overshoot = False
            self._beat2_sub_t   = 0.0
            self._land_y        = 60.0
            bus.emit(EVT_BAX_SPEAK, line=random.choice(_BAX_LAND))

    def _draw_approach(self, surface: pygame.Surface, W: int, H: int):
        t = self._t
        surface.fill((8, 4, 16))
        draw_space_crawl(surface, _APPROACH_CRAWL, t, y_start=H - 80, speed=22.0)
        approach_frac = min(1.0, t / _APPROACH_DURATION)

        # ── Background nebula wash ───────────────────────────────────────
        neb = pygame.Surface((W, H), pygame.SRCALPHA)
        neb.fill((0, 8, 24, 16))
        surface.blit(neb, (0, 0))

        # ── Starfield: dim base + neon accents ───────────────────────────
        rng = random.Random(42)
        for _ in range(140):
            sx = rng.randint(0, W)
            sy = rng.randint(0, H)
            br = rng.randint(50, 180)
            pygame.draw.circle(surface, (br, br, br), (sx, sy), 1)
        rng2 = random.Random(99)
        for _ in range(16):
            sx2 = rng2.randint(0, W)
            sy2 = rng2.randint(0, H)
            nc  = [(0, 255, 200), (255, 0, 220), (255, 176, 0)][rng2.randint(0, 2)]
            pygame.draw.circle(surface, nc, (sx2, sy2), 1)

        # ── Background traffic: distant ships crossing the frame ─────────
        for i, (base_y_frac, spd, seed) in enumerate(
                [(0.18, 14.0, 71), (0.82, 9.0, 83)]):
            tx = int((W * 0.95 - t * spd) % (W * 1.4)) - int(W * 0.2)
            ty = int(H * base_y_frac)
            pygame.draw.polygon(surface, (28, 55, 75),
                                [(tx + 13, ty), (tx - 9, ty - 4), (tx - 9, ty + 4)])
            rl_p = 0.5 + 0.5 * math.sin(t * 2.0 + i * 1.3)
            pygame.draw.circle(surface, (int(180 * rl_p), 0, 0), (tx - 8, ty - 3), 1)
            pygame.draw.circle(surface, (0, int(180 * rl_p), 0), (tx - 8, ty + 3), 1)

        # ── Station structure ─────────────────────────────────────────────
        station_scale = 0.15 + approach_frac * 0.85
        st_cx = int(S.SCREEN_W * 0.78)
        st_cy = H // 2
        sw    = int(340 * station_scale)
        sh    = int(460 * station_scale)

        # Docking arms extending left
        for arm_y_frac in (-0.32, 0.32):
            ay    = int(st_cy + sh * arm_y_frac)
            a_len = int(90 * station_scale)
            a_h   = max(4, int(16 * station_scale))
            pygame.draw.rect(surface, (16, 28, 18),
                             (st_cx - sw // 2 - a_len, ay - a_h // 2, a_len, a_h))
            pygame.draw.rect(surface, (30, 60, 35),
                             (st_cx - sw // 2 - a_len, ay - a_h // 2, a_len, a_h), 1)
            tip_p = 0.3 + 0.7 * abs(math.sin(t * 1.8 + arm_y_frac * 10))
            pygame.draw.circle(surface, (int(255 * tip_p), int(60 * tip_p), 0),
                               (st_cx - sw // 2 - a_len, ay),
                               max(2, int(3 * station_scale)))

        # Radiator fins on far side
        for fi in range(3):
            fy   = int(st_cy - sh * 0.3 + fi * sh * 0.3)
            f_h  = max(4, int(sh * 0.18))
            f_w  = max(3, int(20 * station_scale))
            pygame.draw.rect(surface, (10, 24, 12),
                             (st_cx + sw // 2 + 2, fy - f_h // 2, f_w, f_h))
            pygame.draw.rect(surface, (0, 70, 35),
                             (st_cx + sw // 2 + 2, fy - f_h // 2, f_w, f_h), 1)

        # Antenna cluster on top
        ant_base_y = st_cy - sh // 2
        for ox, a_len2 in [(0, 24), (-12, 14), (12, 18), (-6, 10)]:
            ax2 = st_cx + int(ox * station_scale)
            pygame.draw.line(surface, (40, 80, 50),
                             (ax2, ant_base_y),
                             (ax2, ant_base_y - int(a_len2 * station_scale)), 1)
        if abs(math.sin(t * 2.5)) > 0.7:
            pygame.draw.circle(surface, (255, 80, 80),
                               (st_cx, ant_base_y - int(24 * station_scale)), 2)

        # Chapter-specific station silhouette.
        theme = _STATION_THEMES.get(self.chapter, _STATION_THEMES[1])
        _draw_chapter_station_exterior(surface, st_cx, st_cy, station_scale,
                                       t, self.chapter)

        # Signage panels
        if station_scale > 0.35:
            f_sign = get_font(max(8, int(9 * station_scale)), bold=True)
            for sign_text, sy_frac, s_col in [
                ("BAY 3",        -0.42, (200, 140,  0)),
                ("LOCAL 404",     0.38, (  0, 160, 60)),
                ("AUTHORIZED",   -0.15, ( 80, 120, 80)),
            ]:
                sy3 = int(st_cy + sh * sy_frac)
                sx3 = st_cx - sw // 2 + max(4, int(6 * station_scale))
                ss2 = f_sign.render(sign_text, True, s_col)
                surface.blit(ss2, (sx3, sy3 - ss2.get_height() // 2))

        # Running lights: red port (left), green starboard (right), white strobes
        for rl_y_frac in (-0.45, -0.15, 0.15, 0.45):
            rl_y2 = int(st_cy + sh * rl_y_frac)
            pygame.draw.circle(surface, (180, 40, 40),
                               (st_cx - sw // 2 - 4, rl_y2),
                               max(2, int(3 * station_scale)))
            pygame.draw.circle(surface, (40, 180, 40),
                               (st_cx + sw // 2 + 4, rl_y2),
                               max(2, int(3 * station_scale)))
        strobe = 0.3 + 0.7 * abs(math.sin(t * 4.0))
        sc2 = int(255 * strobe)
        for sy4 in (st_cy - sh // 2, st_cy + sh // 2):
            pygame.draw.circle(surface, (sc2, sc2, sc2),
                               (st_cx, sy4), max(2, int(3 * station_scale)))

        # Windows (scaled, hue-animated)
        for row in range(-2, 3):
            for col_i in (1, -1):
                wx  = st_cx + col_i * int(sw * 0.28)
                wy  = st_cy + row * int(sh * 0.14)
                wf  = 0.5 + 0.5 * math.sin(t * 0.7 + row * 1.3 + col_i)
                wc  = (0, int(140 * wf), int(80 * wf))
                ww2 = max(4, int(10 * station_scale))
                wh2 = max(3, int(8  * station_scale))
                pygame.draw.rect(surface, wc, (wx - ww2 // 2, wy - wh2 // 2, ww2, wh2))

        # ── Bay opening ───────────────────────────────────────────────────
        bay_top  = int(st_cy - sh * 0.22)
        bay_bot  = int(st_cy + sh * 0.22)
        bay_left = st_cx - sw // 2 - 2
        bay_w    = int(sw * 0.32)
        pygame.draw.rect(surface, (2, 4, 8),
                         (bay_left, bay_top, bay_w, bay_bot - bay_top))
        pulse = 0.7 + 0.3 * math.sin(t * 3.0)
        gcol  = (int(200 * pulse), int(140 * pulse), 0)
        pygame.draw.rect(surface, gcol,
                         (bay_left, bay_top, bay_w, bay_bot - bay_top), 2)
        # Bay guide-rail LEDs
        if bay_w > 18:
            step = max(8, (bay_bot - bay_top) // 6)
            for led_y in range(bay_top + 8, bay_bot, step):
                lp  = 0.4 + 0.6 * abs(math.sin(t * 2.0 + led_y * 0.05))
                lc  = (int(80 * lp), int(200 * lp), int(120 * lp))
                pygame.draw.circle(surface, lc,
                                   (bay_left + max(2, int(4 * station_scale)), led_y), 2)
        if bay_w > 4 and bay_bot > bay_top:
            gi = pygame.Surface((max(1, bay_w), max(1, bay_bot - bay_top)), pygame.SRCALPHA)
            gi.fill((80, 60, 0, int(45 * pulse)))
            # Atmosphere shimmer: horizontal density streaks
            for sk in range(0, bay_bot - bay_top, max(3, int(5 * station_scale))):
                sa = int(18 + 22 * abs(math.sin(t * 3.4 + sk * 0.15)))
                pygame.draw.line(gi, (140, 110, 20, sa), (0, sk), (bay_w - 1, sk), 1)
            surface.blit(gi, (bay_left, bay_top))

        # PAPI glideslope lights visible when close
        if station_scale > 0.5:
            papi_y2 = bay_top - max(4, int(12 * station_scale))
            on_gs   = self._ship_screen_y < (bay_top + bay_bot) / 2
            for pi in range(4):
                pc = (200, 0, 0) if (pi < 2 or not on_gs) else (200, 200, 200)
                pygame.draw.circle(surface, pc,
                                   (bay_left + int((pi + 1) * bay_w // 5), papi_y2),
                                   max(2, int(3 * station_scale)))

        # ── Bay docking status lights — 3-state panel (red/amber/green) ────
        if bay_w > 8:
            sl_x  = bay_left - max(6, int(18 * station_scale))
            sl_cy = int((bay_top + bay_bot) / 2)
            sl_h  = max(10, int(38 * station_scale))
            sl_w  = max(4, int(14 * station_scale))
            pygame.draw.rect(surface, (8, 14, 10),
                             (sl_x - sl_w // 2 - 2, sl_cy - sl_h // 2 - 2,
                              sl_w + 4, sl_h + 4), border_radius=2)
            pygame.draw.rect(surface, (30, 52, 34),
                             (sl_x - sl_w // 2 - 2, sl_cy - sl_h // 2 - 2,
                              sl_w + 4, sl_h + 4), border_radius=2, width=1)
            angle_abs = abs(self._ship_angle)
            for li, (lo_c, hi_c, on) in enumerate([
                ((60, 0, 0),   (220, 40, 40), angle_abs >= 35.0),      # red: off-axis
                ((50, 35, 0),  (200, 150, 0), 10.0 < angle_abs < 35.0),# amber: aligning
                ((0, 50, 0),   (0, 220, 80),  angle_abs <= 10.0),       # green: clear
            ]):
                ly = sl_cy - sl_h // 3 + li * (sl_h // 3)
                pygame.draw.circle(surface, hi_c if on else lo_c,
                                   (sl_x, ly), max(2, int(4 * station_scale)))

        # ── Alignment cone guide (target ±30°) ──────────────────────────
        cone_cx = bay_left - 40
        cone_cy = int((bay_top + bay_bot) / 2)
        cone_len = 120
        is_locked = self._lock_flash_t > 0
        cone_col = (0, 255, 100) if is_locked else (80, 160, 80)
        for sign in (-1, 1):
            ang_r = math.radians(sign * 30)
            ex_c  = cone_cx - int(cone_len * math.cos(ang_r))
            ey_c  = cone_cy + int(cone_len * math.sin(ang_r))
            pygame.draw.line(surface, cone_col, (cone_cx, cone_cy), (ex_c, ey_c), 1)
        if is_locked:
            lk = pygame.Surface((80, 22), pygame.SRCALPHA)
            lk.fill((0, 255, 100, 160))
            surface.blit(lk, (cone_cx - 40, cone_cy - 11))
            fl = get_font(14, bold=True)
            ls = fl.render("LOCKED", True, (0, 0, 0))
            surface.blit(ls, (cone_cx - ls.get_width() // 2, cone_cy - 8))

        # ── Player ship (rotated by angle) ──────────────────────────────
        px5  = int(self._ship_screen_x)
        py5  = int(self._ship_screen_y)
        ang_r2 = math.radians(self._ship_angle)
        nose_len, tail_len = 22, 14
        nose   = (px5 + int(nose_len * math.cos(ang_r2)),
                  py5 + int(nose_len * math.sin(ang_r2)))
        perp   = ang_r2 + math.pi / 2
        tail_t = (px5 - int(tail_len * math.cos(ang_r2)) + int(11 * math.cos(perp)),
                  py5 - int(tail_len * math.sin(ang_r2)) + int(11 * math.sin(perp)))
        tail_b = (px5 - int(tail_len * math.cos(ang_r2)) - int(11 * math.cos(perp)),
                  py5 - int(tail_len * math.sin(ang_r2)) - int(11 * math.sin(perp)))
        halo = pygame.Surface((54, 44), pygame.SRCALPHA)
        pygame.draw.ellipse(halo, (0, 220, 200, 28), (0, 0, 54, 44))
        surface.blit(halo, (px5 - 12, py5 - 22))
        pygame.draw.polygon(surface, (20, 200, 200), [nose, tail_t, tail_b])
        pygame.draw.polygon(surface, (0, 255, 240), [nose, tail_t, tail_b], 1)
        # Exhaust
        for k in range(5):
            ex2  = px5 - int((14 + k * 7) * math.cos(ang_r2))
            ey2  = py5 - int((14 + k * 7) * math.sin(ang_r2))
            ecol = (0, max(0, int(180 - k * 35)), max(0, int(100 - k * 18)))
            pygame.draw.line(surface, ecol,
                             (px5 - int(14 * math.cos(ang_r2)),
                              py5 - int(14 * math.sin(ang_r2))),
                             (ex2, ey2), 1)

        # ── Chapter station label ────────────────────────────────────────
        theme = _STATION_THEMES.get(self.chapter, _STATION_THEMES[1])
        f_stn = get_font(11)
        stn_s = f_stn.render(theme[2], True, theme[1])
        surface.blit(stn_s, (st_cx - stn_s.get_width() // 2, st_cy - sh // 2 - 18))

        # ── HUD ───────────────────────────────────────────────────────────
        f = get_font(14)
        surface.blit(f.render("BEAT 1  ·  ALIGN NOSE TO BAY  (A/D rotate  W/S nudge)",
                               True, (140, 100, 0)), (W // 2 - 260, 12))
        remain = max(0.0, _APPROACH_DURATION - t)
        tc = (0, 255, 100) if self._aligned else ((0, 200, 80) if remain > 2 else (255, 120, 0))
        label = "ALIGNED  ·  LOCK IMMINENT" if self._aligned else f"ALIGN IN  {remain:.1f}s"
        surface.blit(f.render(label, True, tc), (W - 260, 12))
        # Angle indicator bar
        bar_cx = W // 2
        bar_w  = 200
        pygame.draw.rect(surface, (20, 40, 20), (bar_cx - bar_w // 2, H - 32, bar_w, 12))
        # Target zone (green)
        zone_frac = 30 / 60
        zone_pix  = int(bar_w * zone_frac)
        pygame.draw.rect(surface, (0, 80, 40),
                         (bar_cx - zone_pix, H - 32, zone_pix * 2, 12))
        # Needle
        needle_x = bar_cx + int((self._ship_angle / 60) * bar_w // 2)
        needle_c  = (0, 255, 100) if self._aligned else (255, 180, 0)
        pygame.draw.rect(surface, needle_c, (needle_x - 2, H - 35, 4, 18))

    # ── Phase: Land (Beat 2 — Epic 14.2: continuous speed-dock gauge) ─────
    # Replaces the old J-tap + SPACE-hold QTE with a held-W/S minigame that
    # plays out as a single ~8s approach. Same scoring envelope.
    _DOCK_DURATION       = 8.0     # nominal time to dock at sweet-spot speed
    _DOCK_ZONE_LO        = 0.42    # gauge value: bottom of green band
    _DOCK_ZONE_HI        = 0.62    # gauge value: top of green band
    _DOCK_OVERSHOOT_LIM  = 0.85    # speed above which an "overshoot timer" runs
    _DOCK_OVERSHOOT_HOLD = 0.40    # seconds held above threshold = overshoot event
    _DOCK_IDLE_LIM       = 0.18    # speed below which "idle fee" accumulates
    _DOCK_TIME_CAP       = 14.0    # safety cap — never let Beat 2 run forever

    # ── Epic 14.2 — Continuous speed-dock approach ──────────────────────────
    def _finish_dock(self):
        """End Beat 2: compute score from time-in-zone + overshoots + idle."""
        accuracy = self._dock_in_zone_t / max(0.1, self._dock_total_t)
        perfect  = (accuracy >= 0.65 and self._dock_overshoots == 0
                    and self._dock_idle_t < 1.5)
        rough    = (accuracy < 0.30 or self._dock_overshoots >= 2
                    or self._dock_idle_t >= 3.0)
        if perfect:
            self._land_score = 2
            self._dock_bonus_cr = 500
            self._j_hit = True
            self._burn_done = True
            bus.emit(EVT_DOCK_PERFECT)
            bus.emit(EVT_BAX_SPEAK, line=random.choice(_BAX_LAND_SMOOTH))
        elif rough:
            self._land_score = 0
            self._dock_bonus_cr = -200
            self._j_hit = False
            self._burn_done = False
            self._burn_overshoot = self._dock_overshoots >= 2
            bus.emit(EVT_DOCK_ROUGH)
            bus.emit(EVT_BAX_SPEAK, line=random.choice(_BAX_LAND_ROUGH))
        else:
            self._land_score = 1
            self._dock_bonus_cr = 0
            self._j_hit = True
            self._burn_done = False
        self._t     = 0.0
        self._phase = self.PHASE_BEAT3

    def _update_land(self, dt: float):
        self._beat2_sub_t += dt
        self._land_sub_t  += dt
        self._dock_total_t += dt

        # Held-key input: W/UP increases target speed, S/DOWN decreases.
        # A/D nudge angle; auto-correct toward 0 if within ±20°.
        keys = pygame.key.get_pressed()
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            self._dock_speed_target = min(1.0, self._dock_speed_target + 0.95 * dt)
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            self._dock_speed_target = max(0.0, self._dock_speed_target - 0.95 * dt)
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            self._dock_angle = max(-35.0, self._dock_angle - 26.0 * dt)
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            self._dock_angle = min(35.0, self._dock_angle + 26.0 * dt)
        # Auto-correct angle while inside the dock-master tolerance (±20°).
        if abs(self._dock_angle) <= 20.0:
            ease = min(1.0, dt * 0.9)
            self._dock_angle -= self._dock_angle * ease
        else:
            # Outside tolerance: accumulate abort timer, bail at 1.0s.
            self._dock_abort_t += dt
            if self._dock_abort_t >= 1.0:
                bus.emit(EVT_BAX_SPEAK, line=random.choice([
                    "ABORT, mate, abort — we're way out of line. Resetting.",
                    "Pitch too steep! Dock master's furious. Recovering.",
                ]))
                self._dock_overshoots += 1
                self._dock_angle      = 0.0
                self._dock_abort_t    = 0.0
                self._dock_distance   = min(1.0, self._dock_distance + 0.18)

        # Speed converges to target
        ease = min(1.0, dt * 2.6)
        self._dock_speed += (self._dock_speed_target - self._dock_speed) * ease
        self._dock_speed = max(0.0, min(1.0, self._dock_speed))

        # Track sweet-spot residency
        if self._DOCK_ZONE_LO <= self._dock_speed <= self._DOCK_ZONE_HI:
            self._dock_in_zone_t += dt
            self._dock_over_held_t = 0.0
        elif self._dock_speed > self._DOCK_OVERSHOOT_LIM:
            self._dock_over_held_t += dt
            if self._dock_over_held_t >= self._DOCK_OVERSHOOT_HOLD:
                # Overshoot event — hull damage + speed reset + Bax shout
                self._dock_over_held_t = 0.0
                self._dock_overshoots += 1
                self._dock_speed = 0.35
                self._dock_speed_target = 0.50
                # Pushed back a bit on the approach
                self._dock_distance = min(1.0, self._dock_distance + 0.12)
                bus.emit(EVT_BAX_SPEAK, line=random.choice([
                    "OVERSHOOT! You're cooking the retros, ease off!",
                    "Too HOT, mate, too HOT! Bringing us round.",
                ]))
        elif self._dock_speed < self._DOCK_IDLE_LIM:
            self._dock_over_held_t = 0.0
            self._dock_idle_t += dt
        else:
            self._dock_over_held_t = 0.0

        # Descent — speed maps to distance-per-second
        descend_rate = 0.045 + self._dock_speed * 0.18
        self._dock_distance -= dt * descend_rate
        self._dock_distance = max(0.0, self._dock_distance)

        # Visual Y position (kept for legacy ship rendering in _draw_land)
        H_local   = S.SCREEN_H
        pad_top_y = H_local - 140
        contact_y = pad_top_y - 22
        start_y   = 60.0
        self._land_y = start_y + (contact_y - start_y) * (1.0 - self._dock_distance)

        if self._dock_distance <= 0.0 or self._dock_total_t >= self._DOCK_TIME_CAP:
            self._finish_dock()

    def _update_beat3(self, dt: float):
        self._clamp_anim_t += dt
        if self._clamp_anim_t >= 1.8 and self._run is None:
            # Fire Bax landing line once
            bus.emit(EVT_BAX_SPEAK, line=random.choice(_BAX_LAND_SMOOTH
                     if self._land_score == 2 else _BAX_LAND_ROUGH))
            self._run = make_corridor(
                self.chapter,
                hardcore=bool(getattr(self.meta, "is_hardcore", False)),
            )
        if self._clamp_anim_t >= _BEAT3_DURATION:
            self._t     = 0.0
            self._phase = self.PHASE_RUN

    def _draw_land(self, surface: pygame.Surface, W: int, H: int):
        t = self._t
        surface.fill((12, 22, 14))

        # ── Chamber walls and grid ────────────────────────────────────────
        pygame.draw.rect(surface, (20, 38, 22), (0,       0, 80, H))
        pygame.draw.rect(surface, (0, 100, 45), (80,      0,  2, H), 1)
        pygame.draw.rect(surface, (20, 38, 22), (W - 80,  0, 80, H))
        pygame.draw.rect(surface, (0, 100, 45), (W - 82,  0,  2, H), 1)
        for gx in range(80, W - 80, 60):
            pygame.draw.line(surface, (14, 26, 16), (gx, 0), (gx, H), 1)
        for gy in range(0, H, 60):
            pygame.draw.line(surface, (14, 26, 16), (80, gy), (W - 80, gy), 1)
        _draw_chapter_bay_dressing(surface, W, H, t, self.chapter)

        # ── Overhead gantry crane ─────────────────────────────────────────
        gantry_y = 88
        pygame.draw.rect(surface, (18, 34, 20), (80, gantry_y - 10, W - 160, 10))
        pygame.draw.rect(surface, (0, 80, 40),  (80, gantry_y - 10, W - 160, 10), 1)
        crane_x = int(W // 2 + 60 * math.sin(t * 0.38))
        pygame.draw.rect(surface, (28, 56, 30), (crane_x - 18, gantry_y - 8, 36, 14))
        pygame.draw.rect(surface, (0, 120, 50), (crane_x - 18, gantry_y - 8, 36, 14), 1)
        pygame.draw.line(surface, (0, 80, 40), (crane_x, gantry_y + 6), (crane_x, gantry_y + 48), 1)
        pygame.draw.circle(surface, (40, 80, 45), (crane_x, gantry_y + 52), 4)
        pygame.draw.circle(surface, (0, 120, 55), (crane_x, gantry_y + 52), 4, 1)

        # ── Emergency lighting strips near ceiling ────────────────────────
        for ex2 in range(100, W - 100, 90):
            ep = 0.4 + 0.6 * abs(math.sin(t * 1.2 + ex2 * 0.022))
            pygame.draw.rect(surface, (int(200 * ep), int(40 * ep), 0), (ex2, 0, 28, 7))

        # ── Equipment crates along left wall ─────────────────────────────
        pad_y  = H - 140
        pad_cx = W // 2
        pad_w  = 220
        f_sm   = get_font(9)
        for ci, (cxc, cyc, cwc, chc) in enumerate([
            (84,  H - 210, 44, 54), (84,  H - 148, 36, 44),
            (132, H - 164, 30, 38), (84,  H -  88, 52, 36),
        ]):
            shade = (16 + ci * 2, 30 + ci * 2, 18)
            pygame.draw.rect(surface, shade,   (cxc, cyc, cwc, chc))
            pygame.draw.rect(surface, (0, 80, 40), (cxc, cyc, cwc, chc), 1)
            lbl = f_sm.render(["L404", "FUEL", "MAINT", "PARTS"][ci], True, (0, 60, 30))
            surface.blit(lbl, (cxc + 3, cyc + 3))
        for cxc, cyc, cwc, chc in [(W - 128, H - 198, 44, 50), (W - 82, H - 134, 40, 40)]:
            pygame.draw.rect(surface, (16, 30, 18), (cxc, cyc, cwc, chc))
            pygame.draw.rect(surface, (0, 80, 40),  (cxc, cyc, cwc, chc), 1)

        # ── Magnetic clamp housing brackets on bay walls ──────────────────
        for wx, w_sign in ((58, 1), (W - 58, -1)):
            for cy_brk in (H // 2 - 50, H // 2 + 10):
                bw = 22 * w_sign
                bx = wx - (bw if w_sign < 0 else 0)
                pygame.draw.rect(surface, (12, 26, 14), (bx, cy_brk - 14, abs(bw), 28))
                pygame.draw.rect(surface, (0, 90, 40),  (bx, cy_brk - 14, abs(bw), 28), 1)
                # Clamp arm recess
                arm_x = wx + (w_sign * 2)
                pygame.draw.rect(surface, (6, 16, 8),
                                 (arm_x - 5 * (1 if w_sign < 0 else 0),
                                  cy_brk - 8, 10, 16))
                # Status indicator
                cl_p = 0.4 + 0.6 * abs(math.sin(t * 1.5 + cy_brk * 0.02))
                pygame.draw.circle(surface, (int(180 * cl_p), int(90 * cl_p), 0),
                                   (wx + w_sign * 8, cy_brk), 2)

        # ── Maintenance drone hovering near ceiling ───────────────────────
        drone_x = int(W * 0.7 + 42 * math.sin(t * 0.58))
        drone_y = int(160 + 14 * math.sin(t * 0.87))
        pygame.draw.ellipse(surface, (16, 36, 20),
                            (drone_x - 24, drone_y - 8, 48, 16))
        pygame.draw.ellipse(surface, (0, 100, 50),
                            (drone_x - 24, drone_y - 8, 48, 16), 1)
        for ang in (0, 90, 180, 270):
            ar2 = math.radians(ang)
            ax3 = drone_x + int(24 * math.cos(ar2))
            ay3 = drone_y + int(8  * math.sin(ar2))
            pygame.draw.circle(surface, (0, 80, 40),  (ax3, ay3), 4)
            pygame.draw.circle(surface, (0, 140, 60), (ax3, ay3), 4, 1)
        if abs(math.sin(t * 3.0)) > 0.7:
            pygame.draw.circle(surface, (200, 40, 40), (drone_x, drone_y - 6), 3)
        ds_label = f_sm.render("MAINT-BOT", True, (0, 60, 30))
        surface.blit(ds_label, (drone_x - ds_label.get_width() // 2, drone_y + 10))

        # ── Ground crew technicians ───────────────────────────────────────
        for tech_i, (tx2, facing) in enumerate([
            (pad_cx - 180, 1), (pad_cx + 162, -1), (pad_cx - 140, 1),
        ]):
            ty2 = pad_y - 2
            pygame.draw.rect(surface, (0, 60, 30),
                             (tx2 - 7, ty2 - 28, 14, 20))
            pygame.draw.rect(surface, (0, 100, 50),
                             (tx2 - 7, ty2 - 28, 14, 20), 1)
            pygame.draw.circle(surface, (0, 80, 40),  (tx2, ty2 - 34), 8)
            pygame.draw.circle(surface, (0, 130, 60), (tx2, ty2 - 34), 8, 1)
            pygame.draw.arc(surface, (0, 180, 220),
                            (tx2 - 5, ty2 - 40, 10, 12), 0, math.pi, 2)
            pygame.draw.line(surface, (0, 50, 25), (tx2 - 3, ty2 - 8), (tx2 - 3, ty2 + 8), 2)
            pygame.draw.line(surface, (0, 50, 25), (tx2 + 3, ty2 - 8), (tx2 + 3, ty2 + 8), 2)
            w_ang = math.sin(t * 1.4 + tech_i) * 0.4
            wax2  = tx2 + facing * int(18 * math.cos(w_ang + 0.3))
            way2  = ty2 - 18 + int(8 * math.sin(w_ang + 0.3))
            pygame.draw.line(surface, (0, 80, 40),
                             (tx2 + facing * 7, ty2 - 18), (wax2, way2), 2)
            wp2 = 0.4 + 0.6 * abs(math.sin(t * 2.0 + tech_i * 2.1))
            pygame.draw.circle(surface, (int(255 * wp2), int(140 * wp2), 0),
                               (wax2, way2), 3)

        # ── Station placard on far wall ───────────────────────────────────
        pw2, ph2 = 240, 46
        px_pl = W // 2 - pw2 // 2
        py_pl = 138
        pygame.draw.rect(surface, (10, 24, 12), (px_pl, py_pl, pw2, ph2))
        pygame.draw.rect(surface, (0, 120, 50), (px_pl, py_pl, pw2, ph2), 2)
        fp2  = get_font(12, bold=True)
        fp2s = get_font(10)
        ps1  = fp2.render("UNION LOCAL 404", True, (0, 180, 80))
        ps2  = fp2s.render("CERTIFIED DOCKING FACILITY — BAY 3", True, (0, 100, 50))
        surface.blit(ps1, (W // 2 - ps1.get_width() // 2, py_pl + 6))
        surface.blit(ps2, (W // 2 - ps2.get_width() // 2, py_pl + 26))

        # ── Hazard stripes flanking the pad ───────────────────────────────
        for hx in range(pad_cx - pad_w // 2 - 32, pad_cx - pad_w // 2, 12):
            pygame.draw.rect(surface, (160, 110, 0), (hx, pad_y - 22, 6, 22))
        for hx in range(pad_cx + pad_w // 2, pad_cx + pad_w // 2 + 32, 12):
            pygame.draw.rect(surface, (160, 110, 0), (hx, pad_y - 22, 6, 22))

        # ── Landing pad ───────────────────────────────────────────────────
        pulse = 0.6 + 0.4 * math.sin(t * 4.0)
        pcol  = (int(200 * pulse), int(140 * pulse), 0)
        pygame.draw.rect(surface, (15, 25, 12),
                         (pad_cx - pad_w // 2 - 4, pad_y, pad_w + 8, 14))
        pygame.draw.rect(surface, pcol,
                         (pad_cx - pad_w // 2, pad_y, pad_w, 10))
        for mk in range(pad_cx - pad_w // 2, pad_cx + pad_w // 2, 30):
            pygame.draw.rect(surface, (0, 0, 0), (mk, pad_y, 14, 10))
        pygame.draw.line(surface, (255, 200, 0),
                         (pad_cx - 20, pad_y + 5), (pad_cx + 20, pad_y + 5), 2)
        pygame.draw.line(surface, (255, 200, 0),
                         (pad_cx, pad_y - 2), (pad_cx, pad_y + 12), 2)
        for bx_off in (-90, 90):
            for gy2 in range(0, pad_y, 24):
                c = int(80 * pulse) if gy2 % 48 == 0 else int(40 * pulse)
                pygame.draw.line(surface, (0, c, 0),
                                 (pad_cx + bx_off, gy2), (pad_cx + bx_off, gy2 + 12), 1)

        # ── Ship descending ───────────────────────────────────────────────
        ship_cx = W // 2
        ship_y  = int(self._land_y)
        ship_pts = [
            (ship_cx,      ship_y + 22),
            (ship_cx - 18, ship_y),
            (ship_cx + 18, ship_y),
        ]
        pygame.draw.polygon(surface, (20, 200, 200), ship_pts)
        pygame.draw.polygon(surface, (0, 255, 240), ship_pts, 1)
        # Epic 14.2 — retro flames length is proportional to current dock speed.
        # Brighter / longer when throttle is high (overshoot zone), short/dim idle.
        if self._dock_speed > 0.08:
            nose_y = ship_y + 22
            flame_len = int(2 + 7 * self._dock_speed)
            flame_warm = self._dock_speed > self._DOCK_OVERSHOOT_LIM
            for k in range(flame_len):
                cy3 = nose_y + k * 6 + 4
                if flame_warm:
                    bc = (max(0, int(255 - k * 20)), max(0, int(60 - k * 8)), 0)
                else:
                    bc = (max(0, int(255 - k * 28)),
                          max(0, int(180 - k * 24)), 0)
                pygame.draw.line(surface, bc, (ship_cx - 5, nose_y), (ship_cx - 5, cy3), 2)
                pygame.draw.line(surface, bc, (ship_cx + 5, nose_y), (ship_cx + 5, cy3), 2)
                pygame.draw.line(surface, bc, (ship_cx,     nose_y), (ship_cx,     cy3 + 4), 2)

        # ── Beat 2 interactive overlay ────────────────────────────────────
        f    = get_font(14)
        fsm2 = get_font(11)
        cx   = W // 2

        # ── Epic 14.2 — Cockpit instrument panel (continuous speed-dock) ──
        inst_w, inst_h = 440, 120
        inst_x = cx - inst_w // 2
        inst_y = H // 2 - 70
        # Outer bezel
        pygame.draw.rect(surface, (4, 10, 6),
                         (inst_x - 10, inst_y - 10, inst_w + 20, inst_h + 20),
                         border_radius=6)
        pygame.draw.rect(surface, (0, 100, 45),
                         (inst_x - 10, inst_y - 10, inst_w + 20, inst_h + 20),
                         border_radius=6, width=2)
        # Inner face
        pygame.draw.rect(surface, (6, 16, 8),
                         (inst_x, inst_y, inst_w, inst_h),
                         border_radius=4)
        pygame.draw.rect(surface, (0, 70, 32),
                         (inst_x, inst_y, inst_w, inst_h),
                         border_radius=4, width=1)
        fp7  = get_font(7, bold=True)
        fp8  = get_font(8, bold=True)
        fp10 = get_font(10)

        # Header
        hdr = fp8.render("DOCK APPROACH COMPUTER  ·  W/S throttle  ·  A/D pitch",
                          True, (0, 140, 60))
        surface.blit(hdr, (cx - hdr.get_width() // 2, inst_y + 6))

        # ── Speed gauge ────────────────────────────────────────────────────
        gauge_w = inst_w - 40
        gx = inst_x + 20
        gy = inst_y + 26
        gh = 28
        pygame.draw.rect(surface, (8, 22, 10), (gx, gy, gauge_w, gh),
                         border_radius=2)
        pygame.draw.rect(surface, (0, 100, 50), (gx, gy, gauge_w, gh),
                         border_radius=2, width=1)
        # Green sweet-spot band
        z_x0 = gx + int(gauge_w * self._DOCK_ZONE_LO)
        z_x1 = gx + int(gauge_w * self._DOCK_ZONE_HI)
        pygame.draw.rect(surface, (0, 70, 35), (z_x0, gy + 2, z_x1 - z_x0, gh - 4))
        pygame.draw.rect(surface, (0, 200, 90), (z_x0, gy + 2, z_x1 - z_x0, gh - 4), 1)
        # Red overshoot zone
        ov_x = gx + int(gauge_w * self._DOCK_OVERSHOOT_LIM)
        pygame.draw.rect(surface, (50, 12, 12), (ov_x, gy + 2, gx + gauge_w - ov_x, gh - 4))
        pygame.draw.rect(surface, (210, 60, 40), (ov_x, gy + 2, gx + gauge_w - ov_x, gh - 4), 1)
        # Amber idle zone (left)
        id_x = gx + int(gauge_w * self._DOCK_IDLE_LIM)
        pygame.draw.rect(surface, (40, 30, 8), (gx + 1, gy + 2, id_x - gx, gh - 4))
        pygame.draw.rect(surface, (200, 150, 30), (gx + 1, gy + 2, id_x - gx, gh - 4), 1)
        # Current speed marker
        m_x = gx + int(self._dock_speed * gauge_w)
        in_zone = self._DOCK_ZONE_LO <= self._dock_speed <= self._DOCK_ZONE_HI
        m_col = (0, 240, 120) if in_zone else (
            (240, 70, 50) if self._dock_speed >= self._DOCK_OVERSHOOT_LIM
            else (240, 200, 60))
        pygame.draw.rect(surface, m_col, (m_x - 3, gy - 6, 6, gh + 12))
        # Target marker (slim ghost above the gauge)
        tgt_x = gx + int(self._dock_speed_target * gauge_w)
        pygame.draw.polygon(surface, (160, 200, 160),
                            [(tgt_x, gy - 10), (tgt_x - 4, gy - 4), (tgt_x + 4, gy - 4)])
        # Tick marks
        for tf in (0.0, 0.25, 0.5, 0.75, 1.0):
            tx = gx + int(tf * gauge_w)
            pygame.draw.line(surface, (0, 110, 55), (tx, gy + gh - 1), (tx, gy + gh + 3), 1)

        # ── Status row ────────────────────────────────────────────────────
        row_y = inst_y + 62
        # Distance bar
        dist_w = 120
        dist_x = inst_x + 14
        pygame.draw.rect(surface, (8, 22, 10), (dist_x, row_y, dist_w, 10))
        pygame.draw.rect(surface, (0, 90, 45), (dist_x, row_y, dist_w, 10), 1)
        d_fill = int(dist_w * (1.0 - self._dock_distance))
        pygame.draw.rect(surface, (0, 200, 120),
                         (dist_x + 1, row_y + 1, max(0, d_fill - 2), 8))
        dl = fp7.render("DIST TO PAD", True, (90, 150, 110))
        surface.blit(dl, (dist_x, row_y - 8))

        # Accuracy
        acc_pct = int(100 * self._dock_in_zone_t / max(0.1, self._dock_total_t))
        acc_col = (0, 220, 110) if acc_pct >= 65 else (
            (210, 80, 60) if acc_pct < 30 else (210, 170, 40))
        acc_s = fp10.render(f"ACCURACY  {acc_pct}%", True, acc_col)
        surface.blit(acc_s, (inst_x + 150, row_y - 1))

        # Overshoots tally
        ov_lbl = fp10.render(
            f"OVERSHOOT  {self._dock_overshoots}",
            True, (210, 70, 50) if self._dock_overshoots else (90, 130, 100))
        surface.blit(ov_lbl, (inst_x + inst_w - ov_lbl.get_width() - 14, row_y - 1))

        # ── Pitch indicator (artificial horizon strip) ────────────────────
        ph_y = inst_y + inst_h - 28
        ph_w = inst_w - 40
        ph_x = inst_x + 20
        pygame.draw.rect(surface, (8, 22, 10), (ph_x, ph_y, ph_w, 18))
        pygame.draw.rect(surface, (0, 90, 45), (ph_x, ph_y, ph_w, 18), 1)
        # Horizon scrolls with pitch
        center_x = ph_x + ph_w // 2
        pitch_norm = max(-1.0, min(1.0, self._dock_angle / 35.0))
        h_x = center_x - int(pitch_norm * (ph_w // 2 - 6))
        pygame.draw.line(surface, (0, 200, 110), (ph_x + 4, ph_y + 9),
                         (ph_x + ph_w - 4, ph_y + 9), 1)
        pygame.draw.rect(surface, (240, 200, 60), (h_x - 2, ph_y + 4, 4, 10))
        # Tolerance bands ±20°
        tol = int(ph_w / 2 * (20.0 / 35.0))
        pygame.draw.line(surface, (60, 160, 80),
                         (center_x - tol, ph_y + 1), (center_x - tol, ph_y + 17), 1)
        pygame.draw.line(surface, (60, 160, 80),
                         (center_x + tol, ph_y + 1), (center_x + tol, ph_y + 17), 1)
        ph_lbl = fp7.render("PITCH  ±20°  AUTOTRIM ACTIVE" if abs(self._dock_angle) <= 20.0
                            else "PITCH OUT OF LIMIT  —  ABORT IMMINENT",
                            True, (90, 150, 110) if abs(self._dock_angle) <= 20.0
                            else (220, 80, 60))
        surface.blit(ph_lbl, (ph_x, ph_y - 8))

    def _draw_beat3(self, surface: pygame.Surface, W: int, H: int):
        """Beat 3: dock-clamp cutscene + fade to corridor."""
        t    = self._clamp_anim_t
        surface.fill((4, 12, 6))
        _draw_chapter_bay_dressing(surface, W, H, t, self.chapter)
        f    = get_font(14)
        fsm2 = get_font(12)
        cx   = W // 2
        pad_y = H - 140

        # Ship settled on pad
        ship_pts = [(cx, pad_y + 22), (cx - 18, pad_y), (cx + 18, pad_y)]
        pygame.draw.polygon(surface, (20, 200, 200), ship_pts)
        pygame.draw.polygon(surface, (0, 255, 240), ship_pts, 1)

        # Vapor burst at hull contact points — fires first 1.5s of beat3
        if t < 1.5:
            contact_y = pad_y + 1
            burst_fade = max(0.0, 1.0 - t / 1.5)
            for vbx, vb_dir in ((cx - 18, -1), (cx + 18, 1), (cx, 0)):
                for vk in range(7):
                    va = (t * 2.2 + vk * 0.18) % 1.0
                    vx3 = vbx + int(vb_dir * (vk + 1) * 5 * va)
                    vy3 = contact_y + int(va * 14)
                    vr  = max(1, int(3 * (1 - va)))
                    vsurf = pygame.Surface((vr * 2 + 2, vr * 2 + 2), pygame.SRCALPHA)
                    va_out = int(burst_fade * 180 * (1 - va))
                    pygame.draw.circle(vsurf, (190, 215, 230, va_out),
                                       (vr + 1, vr + 1), vr)
                    surface.blit(vsurf, (vx3 - vr - 1, vy3 - vr - 1))

        # Dock clamps animating in
        clamp_prog = min(1.0, t / 1.5)
        for side, sign in [("L", -1), ("R", 1)]:
            cx2 = cx + sign * int(80 * (1.0 - clamp_prog))
            pygame.draw.rect(surface, (0, 120, 60),
                             (cx + sign * 20, pad_y - 8, sign * int(60 * clamp_prog), 6))
            pygame.draw.circle(surface, (0, 200, 100),
                               (cx + sign * int(20 + 60 * clamp_prog), pad_y - 5), 4)

        # "DOCKED" flash after clamps close
        if t > 1.5:
            pul = int(180 + 75 * math.sin(t * 4.0))
            ds  = f.render("DOCKED", True, (0, pul, int(pul * 0.4)))
            surface.blit(ds, (cx - ds.get_width() // 2, H // 2 - 20))

        # Scoring hint
        if self._dock_bonus_cr > 0:
            bs = fsm2.render(f"PERFECT DOCK  +{self._dock_bonus_cr} cr", True, (0, 240, 100))
            surface.blit(bs, (cx - bs.get_width() // 2, H // 2 + 10))
        elif self._dock_bonus_cr < 0:
            bs = fsm2.render(f"ROUGH DOCK  {self._dock_bonus_cr} cr", True, (220, 60, 60))
            surface.blit(bs, (cx - bs.get_width() // 2, H // 2 + 10))

        # Fade to black near end
        if t > _BEAT3_DURATION - 1.5:
            alpha = int(255 * (t - (_BEAT3_DURATION - 1.5)) / 1.5)
            fade  = pygame.Surface((W, H))
            fade.fill((0, 0, 0))
            fade.set_alpha(min(255, alpha))
            surface.blit(fade, (0, 0))

    # ── Phase: Run ────────────────────────────────────────────────────────
    def _update_run(self, dt: float):
        if self._run is not None:
            self._run.update(dt)
            if self._run.is_done:
                self._run_stars = self._run.stars
                self._compute_result()
                self._phase = self.PHASE_RESULT
                self._result_t = _RESULT_HOLD

    def _draw_run(self, surface: pygame.Surface, W: int, H: int):
        surface.fill((2, 4, 3))
        if self._run is None:
            return
        # Scale corridor to fill most of the screen (maintain aspect ratio)
        scale_x = W / CORRIDOR_W
        scale_y = H / CORRIDOR_H
        scale   = min(scale_x, scale_y) * 0.96   # slight margin
        disp_w  = int(CORRIDOR_W * scale)
        disp_h  = int(CORRIDOR_H * scale)
        cx      = (W - disp_w) // 2
        cy      = (H - disp_h) // 2

        # Render corridor into its internal surface (pass screen=None to skip blit)
        self._run.draw(None, 0, 0)
        corridor_surf = self._run.get_surface()
        scaled = pygame.transform.scale(corridor_surf, (disp_w, disp_h))
        # Border frame
        pygame.draw.rect(surface, (0, 60, 30),
                         (cx - 2, cy - 2, disp_w + 4, disp_h + 4), 2)
        surface.blit(scaled, (cx, cy))
        # Bax mini-portrait in corner
        self._draw_bax_corner(surface, W, H)

    def _draw_bax_corner(self, surface: pygame.Surface, W: int, H: int):
        t  = pygame.time.get_ticks() / 1000.0
        px = W - 80
        py = H - 70
        # Tiny Bax portrait
        head = [(px - 10, py - 16), (px + 10, py - 16),
                (px + 14, py - 4), (px - 14, py - 4)]
        pygame.draw.polygon(surface, (14, 14, 22), head)
        pygame.draw.polygon(surface, (40, 32, 0), head, 1)
        glow = 0.4 + 0.3 * abs(math.sin(t * 1.2))
        ec   = (int(160 * glow), int(100 * glow), 0)
        pygame.draw.circle(surface, ec, (px - 4, py - 11), 3)
        pygame.draw.circle(surface, ec, (px + 4, py - 11), 3)
        pygame.draw.line(surface, (40, 32, 0), (px + 8, py - 16), (px + 11, py - 24), 1)
        pygame.draw.circle(surface, (60, 44, 0), (px + 12, py - 25), 2)
        body = [(px - 12, py - 4), (px + 12, py - 4),
                (px + 10, py + 16), (px - 10, py + 16)]
        pygame.draw.polygon(surface, (12, 12, 20), body)
        pygame.draw.polygon(surface, (40, 32, 0), body, 1)
        f = get_font(9)
        surface.blit(f.render("BAX", True, (60, 50, 0)), (px - 12, py + 18))

    # ── Phase: Result ─────────────────────────────────────────────────────
    def _compute_result(self):
        stars = self._run_stars
        self._bonus   = _DELIVERY_BONUS.get(stars, 0)
        self._fee_cut = _DELIVERY_FEE_CUT.get(stars, 0)
        # Add dock bonus (from corridor credits_earned too)
        run_credits  = getattr(self._run, "credits_earned", 0)
        self._bonus += run_credits + max(0, self._dock_bonus_cr)
        if self._dock_bonus_cr < 0:
            self._fee_cut += abs(self._dock_bonus_cr)
        net_reduction = self._bonus - self._fee_cut
        if net_reduction > 0:
            self.meta.pay_off(net_reduction, source="DELIVERY PAYOUT")
        elif net_reduction < 0:
            self.meta.add_debt(-net_reduction, source="DOCK FEES")
        # Epic 8.4 — record HARDCORE best time + unlock check before
        # complete_chapter (it persists immediately).
        was_hardcore = bool(getattr(self.meta, "is_hardcore", False))
        if was_hardcore:
            total_time = float(getattr(self, "_total_time_for_hardcore", 0.0))
            if total_time > 0:
                try:
                    self.meta.record_hardcore_clear(self.chapter, total_time)
                except Exception:
                    pass
        self.meta.complete_chapter(self.chapter)
        # First clear of a chapter (any difficulty) unlocks HARDCORE for it.
        try:
            self.meta.unlock_hardcore_for_chapter(self.chapter)
        except Exception:
            pass
        # Reset the run-scoped hardcore flag now that the run is over.
        try:
            self.meta.clear_hardcore_flag()
        except Exception:
            pass
        self.meta.save()

    def _draw_result(self, surface: pygame.Surface, W: int, H: int):
        t = pygame.time.get_ticks() / 1000.0
        surface.fill((2, 6, 4))

        # Background scanlines
        sl = pygame.Surface((W, H), pygame.SRCALPHA)
        for y in range(0, H, 3):
            pygame.draw.line(sl, (0, 0, 0, 25), (0, y), (W, y))
        surface.blit(sl, (0, 0))

        # Panel
        pw, ph = 540, 320
        px_l = W // 2 - pw // 2
        py_t = H // 2 - ph // 2
        pygame.draw.rect(surface, (6, 14, 8),  (px_l, py_t, pw, ph))
        pygame.draw.rect(surface, (0, 160, 70), (px_l, py_t, pw, ph), 2)
        pygame.draw.rect(surface, (0, 80, 35),
                         (px_l + 4, py_t + 4, pw - 8, ph - 8), 1)

        # Stars row
        stars = self._run_stars
        star_label = ["☆☆☆  POOR DELIVERY", "★☆☆  ACCEPTABLE", "★★☆  GOOD RUN", "★★★  FLAWLESS"][stars]
        star_col   = [(80, 80, 80), (220, 60, 60), (255, 180, 0), (0, 220, 100)][stars]

        fh  = get_font(22, bold=True)
        fmd = get_font(16)
        fsm = get_font(13)

        hs = fh.render(star_label, True, star_col)
        surface.blit(hs, (W // 2 - hs.get_width() // 2, py_t + 24))
        pygame.draw.line(surface, (0, 100, 50),
                         (px_l + 20, py_t + 58), (px_l + pw - 20, py_t + 58), 1)

        # Stats
        dock_score_lbl  = ["MISSED ALL", "PARTIAL", "PERFECT"][min(2, self._approach_score)]
        dock_score_col  = [(180, 60, 60), (200, 160, 0), (0, 200, 90)][min(2, self._approach_score)]
        dock_bonus_lbl  = f"+{self._dock_bonus_cr} cr" if self._dock_bonus_cr >= 0 \
                          else f"{self._dock_bonus_cr} cr"
        dock_bonus_col  = (0, 220, 100) if self._dock_bonus_cr > 0 else \
                          (200, 160, 0) if self._dock_bonus_cr == 0 else (220, 60, 60)
        rows = [
            ("BEAT 1  NOSE ALIGN",
             ["MISSED", "OK", "LOCKED"][self._approach_score],
             [(180, 60, 60), (200, 160, 0), (0, 200, 90)][self._approach_score]),
            ("BEAT 2  DOCKING",
             f"J:{'HIT' if self._j_hit else 'MISS'}  BURN:{'HIT' if self._burn_done else 'MISS'}  {dock_bonus_lbl}",
             dock_bonus_col),
            ("DELIVERY RUN",
             f"{self._run_stars} ★  ·  run complete",
             (0, 190, 80) if self._run_stars == 3 else
             (200, 160, 0) if self._run_stars == 2 else (180, 60, 60)),
        ]

        y = py_t + 72
        for label, val, vcol in rows:
            ls = fmd.render(label, True, (80, 120, 80))
            vs = fmd.render(val,   True, vcol)
            surface.blit(ls, (px_l + 24, y))
            surface.blit(vs, (px_l + pw - 24 - vs.get_width(), y))
            y += 28

        pygame.draw.line(surface, (0, 100, 50),
                         (px_l + 20, y + 4), (px_l + pw - 20, y + 4), 1)
        y += 14

        # Payout line
        if self._bonus > 0:
            bs = fmd.render(f"DELIVERY BONUS   +{self._bonus:,} cr  OFF DEBT",
                            True, (0, 220, 100))
            surface.blit(bs, (W // 2 - bs.get_width() // 2, y))
            y += 28
        if self._fee_cut > 0:
            fs2 = fmd.render(f"LATE FEE   +{self._fee_cut:,} cr  ADDED TO DEBT",
                             True, (220, 60, 60))
            surface.blit(fs2, (W // 2 - fs2.get_width() // 2, y))
            y += 28

        # New debt total
        ds = fh.render(f"BALANCE   {self.meta.debt:,} cr", True, (200, 140, 0))
        surface.blit(ds, (W // 2 - ds.get_width() // 2, y + 6))

        # Continue prompt
        pulse = 0.5 + 0.5 * math.sin(t * 3.0)
        cs = fsm.render("continuing…", True, (int(40 * pulse), int(100 * pulse), int(50 * pulse)))
        surface.blit(cs, (W // 2 - cs.get_width() // 2, py_t + ph - 26))
