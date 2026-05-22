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

from delivery.platformer import DeliveryRun, CORRIDOR_W, CORRIDOR_H
from config import settings as S
from core.event_bus import bus, EVT_BAX_SPEAK

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
_APPROACH_DURATION = 12.0   # seconds to fly into the bay
_LAND_DURATION     = 10.0   # seconds to descend to pad
_RESULT_HOLD       = 4.0    # seconds to show result card


class DeliverySequence:
    PHASE_APPROACH = "approach"
    PHASE_LAND     = "land"
    PHASE_RUN      = "run"
    PHASE_RESULT   = "result"

    def __init__(self, meta, chapter: int = 1):
        self.meta    = meta
        self.chapter = chapter
        self._phase  = self.PHASE_APPROACH
        self._t      = 0.0

        # Approach state
        self._ship_screen_x = float(S.SCREEN_W // 4)
        self._ship_screen_y = float(S.SCREEN_H // 2)
        self._bay_cx        = S.SCREEN_W * 0.72   # world centre of bay opening
        self._approach_offset = 0.0   # horizontal miss at bay entry (-1..+1 normalised)

        # Landing state
        self._land_y        = 60.0    # ship y during landing
        self._land_vy       = 0.0
        self._land_throttle = False
        self._land_score    = 0       # 0=rough, 1=ok, 2=smooth

        # Run state
        self._run: DeliveryRun | None = None
        self._run_stars = 0

        # Result
        self._result_t = 0.0
        self._bonus    = 0
        self._fee_cut  = 0
        self._done     = False

        # Approach stars track
        self._approach_score = 0   # 0=miss, 1=ok, 2=centred

        bus.emit(EVT_BAX_SPEAK, line=random.choice(_BAX_APPROACH))

    # ── Public interface ──────────────────────────────────────────────────
    def handle_key(self, event: pygame.event.Event):
        if self._phase == self.PHASE_APPROACH:
            pass   # steering via held keys in update()
        elif self._phase == self.PHASE_LAND:
            if event.key in (pygame.K_w, pygame.K_UP):
                self._land_throttle = True
        elif self._phase == self.PHASE_RUN:
            if self._run is not None:
                self._run.handle_key(event)

    def handle_keyup(self, event: pygame.event.Event):
        if self._phase == self.PHASE_LAND:
            if event.key in (pygame.K_w, pygame.K_UP):
                self._land_throttle = False

    def update(self, dt: float):
        self._t += dt
        if self._phase == self.PHASE_APPROACH:
            self._update_approach(dt)
        elif self._phase == self.PHASE_LAND:
            self._update_land(dt)
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
        elif self._phase == self.PHASE_RUN:
            self._draw_run(surface, W, H)
        elif self._phase == self.PHASE_RESULT:
            self._draw_result(surface, W, H)

    @property
    def is_done(self) -> bool:
        return self._done

    # ── Phase: Approach ───────────────────────────────────────────────────
    def _update_approach(self, dt: float):
        keys = pygame.key.get_pressed()
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            self._ship_screen_x -= 190.0 * dt
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            self._ship_screen_x += 190.0 * dt
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            self._ship_screen_y -= 140.0 * dt
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            self._ship_screen_y += 140.0 * dt

        # Ship auto-advances toward station
        self._ship_screen_x += 60.0 * dt

        if self._t >= _APPROACH_DURATION:
            bay_top     = S.SCREEN_H * 0.28
            bay_bot     = S.SCREEN_H * 0.72
            bay_mid_y   = (bay_top + bay_bot) / 2
            miss_x      = abs(self._ship_screen_x - self._bay_cx) / 80.0
            miss_y      = abs(self._ship_screen_y - bay_mid_y) / 80.0
            miss        = max(miss_x, miss_y)
            self._approach_offset = miss
            if miss < 0.25:
                self._approach_score = 2
            elif miss < 0.7:
                self._approach_score = 1
                bus.emit(EVT_BAX_SPEAK, line=random.choice(_BAX_APPROACH_MISS))
            else:
                self._approach_score = 0
                bus.emit(EVT_BAX_SPEAK, line=random.choice(_BAX_APPROACH_MISS))
            self._t     = 0.0
            self._phase = self.PHASE_LAND
            self._ship_screen_x = float(S.SCREEN_W // 2)
            self._land_y = 60.0
            self._land_vy = 30.0
            bus.emit(EVT_BAX_SPEAK, line=random.choice(_BAX_LAND))

    def _draw_approach(self, surface: pygame.Surface, W: int, H: int):
        t = self._t
        surface.fill((2, 4, 8))

        # Stars
        rng = random.Random(42)
        for _ in range(140):
            sx = rng.randint(0, W)
            sy = rng.randint(0, H)
            br = rng.randint(60, 180)
            pygame.draw.circle(surface, (br, br, br), (sx, sy), 1)

        # Station — grows as we approach
        approach_frac = min(1.0, t / _APPROACH_DURATION)
        station_scale = 0.15 + approach_frac * 0.85   # grows from 15% to 100% of final
        st_cx = int(S.SCREEN_W * 0.78)
        st_cy = H // 2

        # Station hull
        sw = int(340 * station_scale)
        sh = int(460 * station_scale)
        pygame.draw.rect(surface, (20, 30, 20),
                         (st_cx - sw // 2, st_cy - sh // 2, sw, sh))
        pygame.draw.rect(surface, (40, 80, 50),
                         (st_cx - sw // 2, st_cy - sh // 2, sw, sh), 2)

        # Bay opening (gap in the hull)
        bay_top    = int(st_cy - sh * 0.22)
        bay_bot    = int(st_cy + sh * 0.22)
        bay_left   = st_cx - sw // 2 - 2
        bay_w      = int(sw * 0.32)
        # Black out the bay opening
        pygame.draw.rect(surface, (2, 4, 8),
                         (bay_left, bay_top, bay_w, bay_bot - bay_top))
        # Glowing bay frame
        pulse = 0.7 + 0.3 * math.sin(t * 3.0)
        gcol  = (int(200 * pulse), int(140 * pulse), 0)
        pygame.draw.rect(surface, gcol,
                         (bay_left, bay_top, bay_w, bay_bot - bay_top), 2)
        # Bay interior glow
        gi = pygame.Surface((bay_w, bay_bot - bay_top), pygame.SRCALPHA)
        gi.fill((80, 60, 0, int(60 * pulse)))
        surface.blit(gi, (bay_left, bay_top))

        # Windows on station
        for row in range(-2, 3):
            for col_i in (1, -1):
                wx = st_cx + col_i * int(sw * 0.28)
                wy = st_cy + row * int(sh * 0.14)
                wf = 0.5 + 0.5 * math.sin(t * 0.7 + row * 1.3 + col_i)
                wc = (0, int(140 * wf), int(80 * wf))
                pygame.draw.rect(surface, wc, (wx - 5, wy - 4, 10, 8))

        # Player ship
        sx = int(self._ship_screen_x)
        sy = int(self._ship_screen_y)
        angle = math.radians(15)
        nose  = (sx + 22, sy)
        tail_t = (sx - 14, sy - 11)
        tail_b = (sx - 14, sy + 11)
        pygame.draw.polygon(surface, (20, 200, 200), [nose, tail_t, tail_b])
        pygame.draw.polygon(surface, (0, 255, 240), [nose, tail_t, tail_b], 1)
        # Exhaust
        for k in range(4):
            ex = sx - 14 - k * 7
            ecol = (0, int(180 - k * 40), int(100 - k * 20))
            pygame.draw.line(surface, ecol, (sx - 14, sy - 4 + k), (ex, sy), 1)

        # HUD
        f = pygame.font.SysFont("monospace", 14)
        surface.blit(f.render("APPROACH STATION  ·  STEER INTO BAY", True, (140, 100, 0)),
                     (W // 2 - 170, 12))
        surface.blit(f.render("A/D  ←→   W/S  ↑↓", True, (60, 90, 60)), (W // 2 - 90, 30))
        # Timer
        remain = max(0.0, _APPROACH_DURATION - t)
        tc = (0, 200, 80) if remain > 4 else (255, 120, 0)
        surface.blit(f.render(f"ENTRY IN  {remain:.0f}s", True, tc), (W - 150, 12))

    # ── Phase: Land ───────────────────────────────────────────────────────
    def _update_land(self, dt: float):
        grav  = 160.0 + self._t * 28.0   # gravity grows over time
        thrust = 310.0 if self._land_throttle else 0.0
        self._land_vy += (grav - thrust) * dt
        self._land_y  += self._land_vy * dt

        pad_y = S.SCREEN_H - 140
        if self._land_y >= pad_y:
            self._land_y = float(pad_y)
            spd = abs(self._land_vy)
            if spd < 55:
                self._land_score = 2
                bus.emit(EVT_BAX_SPEAK, line=random.choice(_BAX_LAND_SMOOTH))
            elif spd < 130:
                self._land_score = 1
            else:
                self._land_score = 0
                bus.emit(EVT_BAX_SPEAK, line=random.choice(_BAX_LAND_ROUGH))
            self._land_vy = 0.0
            self._t       = 0.0
            self._phase   = self.PHASE_RUN
            self._run     = DeliveryRun()

    def _draw_land(self, surface: pygame.Surface, W: int, H: int):
        t = self._t
        surface.fill((8, 14, 10))

        # Station interior — large chamber
        chamber_col = (12, 22, 14)
        surface.fill(chamber_col)
        # Side walls
        pygame.draw.rect(surface, (20, 38, 22), (0, 0, 80, H))
        pygame.draw.rect(surface, (0, 100, 45), (80, 0, 2, H), 1)
        pygame.draw.rect(surface, (20, 38, 22), (W - 80, 0, 80, H))
        pygame.draw.rect(surface, (0, 100, 45), (W - 82, 0, 2, H), 1)
        # Grid lines
        for gx in range(80, W - 80, 60):
            pygame.draw.line(surface, (14, 26, 16), (gx, 0), (gx, H), 1)
        for gy in range(0, H, 60):
            pygame.draw.line(surface, (14, 26, 16), (80, gy), (W - 80, gy), 1)

        # Landing pad
        pad_y = H - 140
        pad_w = 220
        pad_cx = W // 2
        pulse  = 0.6 + 0.4 * math.sin(t * 4.0)
        pcol   = (int(200 * pulse), int(140 * pulse), 0)
        pygame.draw.rect(surface, (15, 25, 12),
                         (pad_cx - pad_w // 2 - 4, pad_y, pad_w + 8, 14))
        pygame.draw.rect(surface, pcol,
                         (pad_cx - pad_w // 2, pad_y, pad_w, 10))
        # Pad markers
        for mk in range(pad_cx - pad_w // 2, pad_cx + pad_w // 2, 30):
            pygame.draw.rect(surface, (0, 0, 0), (mk, pad_y, 14, 10))
        # Centre X
        pygame.draw.line(surface, (255, 200, 0),
                         (pad_cx - 20, pad_y + 5), (pad_cx + 20, pad_y + 5), 2)
        pygame.draw.line(surface, (255, 200, 0),
                         (pad_cx, pad_y - 2), (pad_cx, pad_y + 12), 2)
        # Approach guides — vertical beams
        for bx_off in (-90, 90):
            for gy2 in range(0, pad_y, 24):
                c = int(80 * pulse) if gy2 % 48 == 0 else int(40 * pulse)
                pygame.draw.line(surface, (0, c, 0),
                                 (pad_cx + bx_off, gy2), (pad_cx + bx_off, gy2 + 12), 1)

        # Ship
        ship_cx = W // 2
        ship_y  = int(self._land_y)
        ship_pts = [
            (ship_cx, ship_y + 22),    # nose (pointing down)
            (ship_cx - 18, ship_y),
            (ship_cx + 18, ship_y),
        ]
        pygame.draw.polygon(surface, (20, 200, 200), ship_pts)
        pygame.draw.polygon(surface, (0, 255, 240), ship_pts, 1)
        # Thruster glow
        if self._land_throttle:
            for k in range(5):
                cy  = ship_y - k * 8 - 6
                bc  = (0, int(180 - k * 30), int(255 - k * 40))
                pygame.draw.line(surface, bc,
                                 (ship_cx - 6, ship_y), (ship_cx - 6, cy), 2)
                pygame.draw.line(surface, bc,
                                 (ship_cx + 6, ship_y), (ship_cx + 6, cy), 2)

        # HUD
        f     = pygame.font.SysFont("monospace", 14)
        fsm   = pygame.font.SysFont("monospace", 12)
        spd   = abs(self._land_vy)
        sc    = (0, 220, 80) if spd < 55 else (255, 180, 0) if spd < 130 else (220, 50, 50)
        surface.blit(f.render("STATION INTERIOR  ·  LAND ON PAD", True, (100, 140, 80)),
                     (W // 2 - 160, 12))
        surface.blit(f.render("HOLD  W  TO THRUST", True, (60, 90, 60)), (W // 2 - 90, 30))
        surface.blit(f.render(f"DESCENT  {spd:>5.0f} px/s", True, sc),
                     (W - 220, 12))
        surface.blit(fsm.render("<55 SMOOTH · <130 OK · ABOVE = ROUGH", True, (50, 70, 50)),
                     (W - 290, 30))

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
        rows = [
            ("APPROACH SCORE",
             ["WIDE MISS", "CLOSE ENOUGH", "DEAD CENTRE"][self._approach_score],
             [(180, 60, 60), (200, 160, 0), (0, 200, 90)][self._approach_score]),
            ("LANDING",
             ["ROUGH  (hull stressed)", "ACCEPTABLE", "SMOOTH  (textbook)"][self._land_score],
             [(180, 60, 60), (200, 160, 0), (0, 200, 90)][self._land_score]),
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
