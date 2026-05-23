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

        # Landing state (Beat 2)
        self._land_y        = 60.0
        self._land_vy       = 0.0
        self._land_throttle = False
        self._land_score    = 0       # 0=rough, 1=ok, 2=smooth
        self._beat2_sub     = 0       # 0=j_gauge, 1=burn
        self._gauge_angle   = 0.0     # 0-100
        self._gauge_dir     = 1
        self._gauge_t       = 0.0
        self._j_hit         = False
        self._j_window_open = False
        self._j_window_t    = 0.0
        self._burn_held     = False
        self._burn_held_t   = 0.0
        self._burn_done     = False
        self._beat2_sub_t   = 0.0    # time in current sub-phase

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
            if self._beat2_sub == 0 and event.key == pygame.K_j:
                # J-tap: check if gauge is in the green zone
                in_zone = abs(self._gauge_angle - 50) < 15
                self._j_hit = in_zone
                self._j_window_open = True
                self._j_window_t = 0.4
            elif self._beat2_sub == 1:
                if event.key == pygame.K_SPACE:
                    self._burn_held = True
        elif self._phase == self.PHASE_RUN:
            if self._run is not None:
                self._run.handle_key(event)

    def handle_keyup(self, event: pygame.event.Event):
        if self._phase == self.PHASE_LAND:
            if event.key == pygame.K_SPACE:
                self._burn_held = False

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
            self._t        = 0.0
            self._phase    = self.PHASE_LAND
            self._beat2_sub = 0
            self._beat2_sub_t = 0.0
            bus.emit(EVT_BAX_SPEAK, line=random.choice(_BAX_LAND))

    def _draw_approach(self, surface: pygame.Surface, W: int, H: int):
        t = self._t
        surface.fill((2, 4, 8))
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

        # Main hull
        pygame.draw.rect(surface, (20, 30, 20),
                         (st_cx - sw // 2, st_cy - sh // 2, sw, sh))
        pygame.draw.rect(surface, (40, 80, 50),
                         (st_cx - sw // 2, st_cy - sh // 2, sw, sh), 2)

        # Structural ribs
        for ri in range(1, 4):
            ry2 = int(st_cy - sh // 2 + ri * sh // 4)
            pygame.draw.line(surface, (28, 50, 30),
                             (st_cx - sw // 2, ry2), (st_cx + sw // 2, ry2), 1)

        # Signage panels
        if station_scale > 0.35:
            f_sign = pygame.font.SysFont("monospace", max(8, int(9 * station_scale)), bold=True)
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
        gi = pygame.Surface((max(1, bay_w), max(1, bay_bot - bay_top)), pygame.SRCALPHA)
        gi.fill((80, 60, 0, int(60 * pulse)))
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
            fl = pygame.font.SysFont("monospace", 14, bold=True)
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
        f_stn = pygame.font.SysFont("monospace", 11)
        stn_s = f_stn.render(theme[2], True, theme[1])
        surface.blit(stn_s, (st_cx - stn_s.get_width() // 2, st_cy - sh // 2 - 18))

        # ── HUD ───────────────────────────────────────────────────────────
        f = pygame.font.SysFont("monospace", 14)
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

    # ── Phase: Land (Beat 2 — thruster gauge + retro burn) ───────────────
    def _update_land(self, dt: float):
        self._beat2_sub_t += dt
        self._j_window_t   = max(0.0, self._j_window_t - dt)
        if self._j_window_t <= 0:
            self._j_window_open = False

        if self._beat2_sub == 0:
            # J-gauge: needle swings sinusoidally between 0-100
            self._gauge_t     += dt * 60.0  # degrees/s
            self._gauge_angle  = 50 + 48 * math.sin(math.radians(self._gauge_t))
            # Auto-advance after 2.5s
            if self._beat2_sub_t >= 2.5 or self._j_hit:
                if self._j_hit:
                    self._land_score = max(self._land_score, 1)
                self._beat2_sub    = 1
                self._beat2_sub_t  = 0.0
                self._burn_held_t  = 0.0

        elif self._beat2_sub == 1:
            # SPACE burn: hold for 1.2s
            if self._burn_held:
                self._burn_held_t += dt
            # Auto-advance after 2.5s
            if self._beat2_sub_t >= 2.5 or self._burn_held_t >= 1.2:
                if self._burn_held_t >= 1.0:
                    self._burn_done    = True
                    self._land_score   = 2
                    bus.emit(EVT_BAX_SPEAK, line=random.choice(_BAX_LAND_SMOOTH))
                elif not self._j_hit:
                    self._land_score = 0
                    bus.emit(EVT_BAX_SPEAK, line=random.choice(_BAX_LAND_ROUGH))
                # Compute docking bonus
                hits = (1 if self._approach_score >= 1 else 0) + \
                       (1 if self._j_hit else 0) + \
                       (1 if self._burn_done else 0)
                if hits >= 2:
                    self._dock_bonus_cr = 500
                    bus.emit(EVT_DOCK_PERFECT)
                elif hits == 0:
                    self._dock_bonus_cr = -200
                    bus.emit(EVT_DOCK_ROUGH)
                # Transition to Beat 3
                self._t     = 0.0
                self._phase = self.PHASE_BEAT3

    def _update_beat3(self, dt: float):
        self._clamp_anim_t += dt
        if self._clamp_anim_t >= 1.8 and self._run is None:
            # Fire Bax landing line once
            bus.emit(EVT_BAX_SPEAK, line=random.choice(_BAX_LAND_SMOOTH
                     if self._land_score == 2 else _BAX_LAND_ROUGH))
            self._run = make_corridor(self.chapter)
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
        f_sm   = pygame.font.SysFont("monospace", 9)
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
        fp2  = pygame.font.SysFont("monospace", 12, bold=True)
        fp2s = pygame.font.SysFont("monospace", 10)
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
        if self._land_throttle:
            for k in range(5):
                cy3 = ship_y - k * 8 - 6
                bc  = (0, max(0, int(180 - k * 30)), max(0, int(255 - k * 40)))
                pygame.draw.line(surface, bc, (ship_cx - 6, ship_y), (ship_cx - 6, cy3), 2)
                pygame.draw.line(surface, bc, (ship_cx + 6, ship_y), (ship_cx + 6, cy3), 2)

        # ── Beat 2 interactive overlay ────────────────────────────────────
        f    = pygame.font.SysFont("monospace", 14)
        fsm2 = pygame.font.SysFont("monospace", 11)
        overlay_x = W // 2 - 160
        overlay_y = H // 2 - 80

        if self._beat2_sub == 0:
            # J-Gauge
            surface.blit(f.render("BEAT 2  ·  ALIGN THRUSTERS  ·  TAP  J",
                                   True, (200, 160, 0)), (W // 2 - 200, 14))
            # Gauge background
            g_x, g_y, g_w, g_h = overlay_x, overlay_y + 30, 320, 40
            pygame.draw.rect(surface, (12, 24, 14), (g_x, g_y, g_w, g_h))
            pygame.draw.rect(surface, (0, 120, 60),  (g_x, g_y, g_w, g_h), 2)
            # Green zone (center ±15%)
            zone_x = g_x + int(g_w * 0.35)
            zone_w = int(g_w * 0.30)
            z_col  = (0, 100, 40) if not self._j_hit else (0, 180, 80)
            pygame.draw.rect(surface, z_col, (zone_x, g_y + 4, zone_w, g_h - 8))
            # Needle
            needle_px = g_x + int(g_w * self._gauge_angle / 100)
            n_col = (0, 255, 100) if self._j_hit else (255, 200, 0)
            pygame.draw.rect(surface, n_col, (needle_px - 3, g_y - 4, 6, g_h + 8))
            hit_s = fsm2.render("HIT!" if self._j_hit else "TAP J IN GREEN ZONE",
                                 True, (0, 220, 100) if self._j_hit else (160, 140, 60))
            surface.blit(hit_s, (g_x, g_y + g_h + 6))

        elif self._beat2_sub == 1:
            # SPACE burn bar
            surface.blit(f.render("BEAT 2  ·  RETRO BURN  ·  HOLD  SPACE",
                                   True, (200, 160, 0)), (W // 2 - 210, 14))
            b_x, b_y, b_w, b_h = overlay_x, overlay_y + 30, 320, 40
            pygame.draw.rect(surface, (12, 24, 14), (b_x, b_y, b_w, b_h))
            pygame.draw.rect(surface, (0, 120, 60),  (b_x, b_y, b_w, b_h), 2)
            fill_w = int(b_w * min(1.0, self._burn_held_t / 1.2))
            burn_col = (0, 200, 80) if fill_w < b_w else (0, 255, 120)
            pygame.draw.rect(surface, burn_col, (b_x, b_y + 4, fill_w, b_h - 8))
            done_s = fsm2.render("BURN COMPLETE!" if self._burn_done else "HOLD SPACE  1.2s",
                                  True, (0, 255, 120) if self._burn_done else (160, 140, 60))
            surface.blit(done_s, (b_x, b_y + b_h + 6))

    def _draw_beat3(self, surface: pygame.Surface, W: int, H: int):
        """Beat 3: dock-clamp cutscene + fade to corridor."""
        t    = self._clamp_anim_t
        surface.fill((4, 12, 6))
        f    = pygame.font.SysFont("monospace", 14)
        fsm2 = pygame.font.SysFont("monospace", 12)
        cx   = W // 2
        pad_y = H - 140

        # Ship settled on pad
        ship_pts = [(cx, pad_y + 22), (cx - 18, pad_y), (cx + 18, pad_y)]
        pygame.draw.polygon(surface, (20, 200, 200), ship_pts)
        pygame.draw.polygon(surface, (0, 255, 240), ship_pts, 1)

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
        surface.fill((4, 8, 6))
        if self._run is None:
            return
        # Draw corridor centred in window
        cx = (W - CORRIDOR_W) // 2
        cy = (H - CORRIDOR_H) // 2
        # Frame
        pygame.draw.rect(surface, (0, 80, 40),
                         (cx - 3, cy - 3, CORRIDOR_W + 6, CORRIDOR_H + 6), 2)
        self._run.draw(surface, cx, cy)
        # Bax mini-portrait in corner
        self._draw_bax_corner(surface, W, H)
        # Phase label
        f = pygame.font.SysFont("monospace", 12)
        surface.blit(f.render("DELIVERY RUN  ·  REACH THE DROP-OFF", True, (50, 80, 50)),
                     ((W - CORRIDOR_W) // 2, cy - 20))

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
        f = pygame.font.SysFont("monospace", 9)
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
            self.meta.pay_off(net_reduction)
        elif net_reduction < 0:
            self.meta.add_debt(-net_reduction)
        self.meta.complete_chapter(self.chapter)
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

        fh  = pygame.font.SysFont("monospace", 22, bold=True)
        fmd = pygame.font.SysFont("monospace", 16)
        fsm = pygame.font.SysFont("monospace", 13)

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
