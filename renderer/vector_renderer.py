from __future__ import annotations
import math
import random
import pygame
from config import settings as S
from antagonists.repo_barge import BargeState
from antagonists.alien_ship import HULL_PTS as _ALIEN_HULL, INNER_PTS as _ALIEN_INNER
from core.event_bus import (bus, EVT_SLINGSHOT, EVT_SCAN_PING,
                             EVT_TETHER_HIT, EVT_TETHER_SNAP,
                             EVT_MODULE_UNBOLTED, EVT_HULL_DAMAGE,
                             EVT_HULL_CRITICAL, EVT_WARP_JUMP, EVT_SECTOR_CLEAR)


# ---------------------------------------------------------------------------
def _hsv(h: float, s: float = 1.0, v: float = 1.0) -> tuple:
    h = h % 1.0
    if s == 0:
        c = int(v * 255)
        return (c, c, c)
    i  = int(h * 6)
    f  = h * 6 - i
    p, q, t = v * (1 - s), v * (1 - s * f), v * (1 - s * (1 - f))
    r, g, b = [(v,t,p),(q,v,p),(p,v,t),(p,q,v),(t,p,v),(v,p,q)][i % 6]
    return (int(r * 255), int(g * 255), int(b * 255))


class VectorRenderer:
    """
    Draws the flight scene — all geometry procedural, no sprites.
    Aesthetic: psychedelic brutalist. Void black, heavy neon, color cycling.
    """

    _STAR_SEED  = 7
    _STAR_COUNT = 170

    def __init__(self, surface: pygame.Surface):
        self.surface     = surface
        self._stars      = self._gen_stars()
        self._nebulae    = self._gen_nebulae()
        self._dust       = self._gen_dust()
        self._planets    = self._gen_planets()
        self._stations   = self._gen_stations()
        self._flash_t    = 0.0
        self._flash_col  = (180, 220, 255)
        self._scan_pings: list[tuple[int, int, float]] = []

        # Shooting stars — (x, y, vx, vy, age, lifetime)
        self._shooting_stars: list[list[float]] = []
        self._next_shooting_star = random.uniform(4.0, 10.0)

        # Ember particles trailing exhaust — (x, y, vx, vy, age, lifetime, hue)
        self._embers: list[list[float]] = []

        # Explosion/hit particle system — [x, y, vx, vy, age, lifetime, hue, size]
        self._explosions: list[list[float]] = []
        self._was_alive = True
        self._last_ship_x = 640.0
        self._last_ship_y = 320.0

        # Screen shake state: trauma decays exponentially; offset is random per frame
        self._shake_trauma = 0.0   # 0.0 (none) → 1.0 (huge)

        # Per-sector background palette shift
        self._sector_hue_shift = 0.0

        # Warp streak effect
        self._warp_t = 0.0

        bus.subscribe(EVT_SLINGSHOT,        self._on_slingshot)
        bus.subscribe(EVT_SCAN_PING,        self._on_scan_ping)
        bus.subscribe(EVT_TETHER_HIT,       self._on_tether_hit)
        bus.subscribe(EVT_TETHER_SNAP,      self._on_tether_snap)
        bus.subscribe(EVT_MODULE_UNBOLTED,  self._on_module_unbolted)
        bus.subscribe(EVT_HULL_DAMAGE,      self._on_hull_damage)
        bus.subscribe(EVT_HULL_CRITICAL,    self._on_hull_critical)
        bus.subscribe(EVT_WARP_JUMP,        self._on_warp_jump)
        bus.subscribe(EVT_SECTOR_CLEAR,     self._on_sector_clear)

    def _on_slingshot(self, **_):
        self._flash_t   = 0.45
        self._flash_col = (160, 210, 255)

    def _on_scan_ping(self, pos_x, pos_y, **_):
        t = pygame.time.get_ticks() / 1000.0
        self._scan_pings.append((int(pos_x), int(pos_y), t))

    def _on_tether_hit(self, **_):
        self._shake_trauma = min(1.0, self._shake_trauma + 0.75)
        self._flash_t   = 0.25
        self._flash_col = (255, 140, 40)

    def _on_tether_snap(self, **_):
        self._shake_trauma = min(1.0, self._shake_trauma + 0.55)
        self._flash_t   = 0.5
        self._flash_col = (220, 255, 220)   # green relief flash

    def _on_module_unbolted(self, **_):
        self._shake_trauma = min(1.0, self._shake_trauma + 0.55)
        self._flash_t   = 0.3
        self._flash_col = (255, 60, 20)

    def _on_hull_damage(self, amount=0.0, **_):
        self._shake_trauma = min(1.0, self._shake_trauma + min(0.45, amount * 0.04))
        if amount >= 5.0:
            n = max(4, int(amount * 0.8))
            self._spawn_explosion(self._last_ship_x, self._last_ship_y, n, 0.28)

    def _on_hull_critical(self, **_):
        self._shake_trauma = min(1.0, self._shake_trauma + 0.4)

    def _on_warp_jump(self, **_):
        self._warp_t    = 0.55
        self._flash_t   = 0.35
        self._flash_col = (200, 220, 255)

    def _on_sector_clear(self, sector_num=0, **_):
        self._sector_hue_shift = (sector_num * 0.11) % 1.0

    # ------------------------------------------------------------------
    def draw(self, run_mgr, ship, dt: float = 0.016):
        t = pygame.time.get_ticks() / 1000.0
        # Track ship position for effects; detect ship death
        self._last_ship_x = ship.pos.x
        self._last_ship_y = ship.pos.y
        if self._was_alive and not ship.is_alive:
            self._spawn_explosion(self._last_ship_x, self._last_ship_y, 32, 1.4)
            self._flash_t   = 0.9
            self._flash_col = (255, 160, 40)
        self._was_alive = ship.is_alive
        self._draw_nebulae(t)
        self._draw_dust(t)
        self._draw_planets(t)
        self._draw_stations(t)
        self._draw_stars(t)
        self._update_shooting_stars(dt, t)
        self._draw_shooting_stars(t)
        self._draw_scan_pings(t)
        self._draw_gravity_wells(run_mgr, t)
        self._draw_debris(run_mgr, t)
        self._draw_satellites(run_mgr, t)
        self._draw_canisters(run_mgr, t)
        self._draw_bullets(ship)
        self._draw_alien(run_mgr, t)
        self._draw_barges(run_mgr, ship, t)
        self._draw_barge_radar(run_mgr, ship, t)
        self._draw_trail(ship, t)
        self._draw_velocity_indicator(ship)
        self._update_embers(dt)
        self._draw_embers()
        self._update_explosions(dt)
        self._draw_explosions()
        self._draw_ship(ship, t)
        self._draw_exhaust(ship, t)
        self._draw_proximity_alarm(run_mgr, ship, t)
        self._draw_flash(dt)
        self._draw_spore_effect(ship, t)
        self._draw_cargo_overlays(ship, t)
        self._draw_warp_streak(dt)
        self._apply_screen_shake(dt)

    # ------------------------------------------------------------------  WARP STREAK
    def _draw_warp_streak(self, dt: float):
        if self._warp_t <= 0:
            return
        W, H  = S.SCREEN_W, S.FLIGHT_H
        cx, cy = W // 2, H // 2
        frac   = self._warp_t / 0.55   # 1.0 → 0.0
        surf   = pygame.Surface((W, H), pygame.SRCALPHA)
        n_lines = 48
        for i in range(n_lines):
            ang   = math.tau * i / n_lines
            # Streaks grow outward as warp intensifies
            inner = int(frac * 30)
            outer = int(40 + (1.0 - frac) * 420)
            x1 = int(cx + math.cos(ang) * inner)
            y1 = int(cy + math.sin(ang) * inner)
            x2 = int(cx + math.cos(ang) * outer)
            y2 = int(cy + math.sin(ang) * outer)
            alpha = int(frac * 180)
            hue   = (0.58 + i / n_lines * 0.25) % 1.0
            col   = _hsv(hue, 0.7, 1.0)
            pygame.draw.line(surf, (*col, alpha), (x1, y1), (x2, y2), 1)
        # Bright core flash
        core_a = int(frac * 220)
        pygame.draw.circle(surf, (200, 220, 255, core_a), (cx, cy), int(frac * 55))
        self.surface.blit(surf, (0, 0))
        self._warp_t = max(0.0, self._warp_t - dt)

    # ------------------------------------------------------------------  CARGO OVERLAYS
    def _draw_cargo_overlays(self, ship, t: float):
        cargo = getattr(ship, "cargo", None)
        if cargo is None:
            return
        ctype = type(cargo).__name__
        if ctype == "AcousticArchive":
            self._draw_acoustic_static(cargo, t)
        elif ctype in ("SentientPaperwork", "TriplicateForm"):
            self._draw_form_popup(cargo, t)

    def _draw_acoustic_static(self, cargo, t: float):
        sl = cargo.sorrow_level
        if sl < 0.05:
            return
        W, H = S.SCREEN_W, S.FLIGHT_H
        surf  = pygame.Surface((W, H), pygame.SRCALPHA)
        n_pixels = int(sl * 900)
        for _ in range(n_pixels):
            px = random.randint(0, W - 1)
            py = random.randint(0, H - 1)
            brightness = random.randint(60, 180)
            a = int(sl * 200)
            surf.set_at((px, py), (brightness, brightness, brightness, a))
        # Desaturation vignette
        desat_a = int(sl * 55)
        pygame.draw.rect(surf, (0, 0, 0, desat_a), (0, 0, W, H))
        # Edge noise strips (scanline density increase near edges)
        for y in range(0, H, 2):
            if random.random() < sl * 0.18:
                alpha = int(sl * 90 * random.random())
                pygame.draw.line(surf, (80, 80, 80, alpha), (0, y), (W, y), 1)
        self.surface.blit(surf, (0, 0))
        # Sorrow meter HUD element
        font_xs = pygame.font.SysFont("monospace", 12)
        bars  = int(sl * 8)
        label = font_xs.render(
            f"SIGNAL  {'|' * bars}{'·' * (8 - bars)}",
            True, (int(160 * sl), int(80 * sl), int(30 * sl)))
        self.surface.blit(label, (8, H - 22))

    def _draw_form_popup(self, cargo, t: float):
        if not cargo.popup_active:
            return
        W, H  = S.SCREEN_W, S.FLIGHT_H
        frac  = cargo.popup_fraction   # 1.0→0.0 countdown
        pulse = 0.6 + 0.4 * abs(math.sin(t * 6.0))
        urgent = frac < 0.35

        # Popup box centred in upper-third of screen
        bw, bh = 460, 120
        bx     = (W - bw) // 2
        by     = H // 4 - bh // 2

        border_col = (220, 40, 40) if urgent else (200, 160, 0)
        bg_col     = (14, 8, 0) if urgent else (8, 12, 4)

        pygame.draw.rect(self.surface, bg_col,    (bx, by, bw, bh))
        pygame.draw.rect(self.surface, border_col, (bx, by, bw, bh), 2)
        if urgent:
            pulse_col = (int(220 * pulse), int(40 * pulse), 0)
            pygame.draw.rect(self.surface, pulse_col, (bx - 2, by - 2, bw + 4, bh + 4), 1)

        font_lg = pygame.font.SysFont("monospace", 16, bold=True)
        font_sm = pygame.font.SysFont("monospace", 13)

        title = font_lg.render("UNION FORM 27-B — IMMEDIATE COMPLIANCE REQUIRED",
                               True, (220, 160, 0) if not urgent else (255, 80, 80))
        self.surface.blit(title, (bx + 12, by + 10))

        key_col = (0, 220, 100) if not urgent else (255, 200, 50)
        key_s   = font_lg.render(f"[ PRESS  {cargo.popup_key_name} ]", True, key_col)
        self.surface.blit(key_s, (bx + bw // 2 - key_s.get_width() // 2, by + 36))

        # Countdown bar
        bar_w = bw - 24
        filled = int(bar_w * frac)
        bar_col = (180, 40, 40) if urgent else (180, 140, 0)
        pygame.draw.rect(self.surface, (20, 14, 4), (bx + 12, by + 72, bar_w, 12))
        pygame.draw.rect(self.surface, bar_col,     (bx + 12, by + 72, filled, 12))
        pygame.draw.rect(self.surface, border_col,  (bx + 12, by + 72, bar_w, 12), 1)

        secs = cargo.popup_timer
        timer_s = font_sm.render(f"{secs:.1f}s", True, (160, 130, 60))
        self.surface.blit(timer_s, (bx + bw - timer_s.get_width() - 12, by + 90))

        sub = font_sm.render("Penalty: hull damage.  Subsection 9, Union Charter.  Non-negotiable.",
                             True, (80, 70, 50))
        self.surface.blit(sub, (bx + 12, by + 92))

    def _apply_screen_shake(self, dt: float):
        if self._shake_trauma <= 0.01:
            self._shake_trauma = 0.0
            return
        # Quadratic curve: huge shake when trauma is high, gentle when low
        amplitude = (self._shake_trauma ** 2) * 16.0
        dx = random.uniform(-amplitude, amplitude)
        dy = random.uniform(-amplitude, amplitude)
        snapshot = self.surface.copy()
        self.surface.fill(S.BLACK)
        self.surface.blit(snapshot, (int(dx), int(dy)))
        # Trauma decays at ~1.6/sec — half-life ~0.4s
        self._shake_trauma = max(0.0, self._shake_trauma - 1.6 * dt)

    def draw_menu_background(self, t: float):
        self._draw_nebulae(t)
        self._draw_dust(t)
        self._draw_planets(t)
        self._draw_stations(t)
        self._draw_stars(t)
        # Single decorative well centred behind the title
        class _FW:
            pass
        fw = _FW()
        fw.pos  = type("P", (), {"x": S.SCREEN_W / 2, "y": S.SCREEN_H / 2 - 50})()
        fw.radius = 60
        self._draw_well(fw, t * 0.35)

    # ------------------------------------------------------------------  NEBULAE
    def _gen_nebulae(self) -> list:
        rng = random.Random(self._STAR_SEED + 99)
        configs = [
            (0.62, 0.50, 260),
            (0.33, 0.40, 210),
            (0.80, 0.45, 190),
            (0.50, 0.35, 230),
            (0.12, 0.40, 170),
        ]
        out = []
        for hue, sat, r in configs:
            x = rng.randint(int(S.SCREEN_W * 0.10), int(S.SCREEN_W * 0.90))
            y = rng.randint(int(S.SCREEN_H * 0.08), int(S.SCREEN_H * 0.85))
            out.append((x, y, r, hue, sat))
        return out

    def _draw_nebulae(self, t: float):
        surf = pygame.Surface((S.SCREEN_W, S.SCREEN_H), pygame.SRCALPHA)
        for x, y, r, base_hue, sat in self._nebulae:
            hue = (base_hue + self._sector_hue_shift + t * 0.0035) % 1.0
            col = _hsv(hue, sat * 0.60, 0.14)
            for scale, alpha in ((1.0, 20), (0.68, 32), (0.40, 44)):
                pygame.draw.circle(surf, (*col, alpha), (x, y), int(r * scale))
        self.surface.blit(surf, (0, 0))

    # ------------------------------------------------------------------  PLANETS (decorative background)
    def _gen_planets(self) -> list:
        rng = random.Random(self._STAR_SEED + 311)
        out = []
        # Two distant planets in different corners
        all_corners = [0, 1, 2, 3]
        rng.shuffle(all_corners)
        configs = [
            # (corner: 0=TL, 1=TR, 2=BL, 3=BR), radius, hue, sat, has_ring, ring_tilt
            (all_corners[0], rng.randint(80, 130), rng.random(),
             rng.uniform(0.55, 0.85), rng.random() < 0.5, rng.uniform(0.2, 0.6)),
            (all_corners[1], rng.randint(38, 68), rng.random(),
             rng.uniform(0.45, 0.80), False, 0.0),
        ]
        for corner, r, hue, sat, has_ring, ring_tilt in configs:
            if corner == 0:
                cx, cy = -int(r * 0.35), -int(r * 0.35)
            elif corner == 1:
                cx, cy = S.SCREEN_W + int(r * 0.35), -int(r * 0.35)
            elif corner == 2:
                cx, cy = -int(r * 0.35), S.FLIGHT_H + int(r * 0.35)
            else:
                cx, cy = S.SCREEN_W + int(r * 0.35), S.FLIGHT_H + int(r * 0.35)
            band_seed = rng.random()
            out.append((cx, cy, r, hue, sat, has_ring, ring_tilt, band_seed))
        return out

    def _draw_planets(self, t: float):
        for cx, cy, r, base_hue, sat, has_ring, ring_tilt, band_seed in self._planets:
            hue = (base_hue + t * 0.005) % 1.0
            # Soft outer glow
            glow = pygame.Surface((r * 3, r * 3), pygame.SRCALPHA)
            glow_col = _hsv(hue, sat * 0.5, 0.18)
            for ring in range(6):
                ra = int(r * (1.0 + ring * 0.08))
                a  = max(0, 14 - ring * 2)
                pygame.draw.circle(glow, (*glow_col, a), (r * 3 // 2, r * 3 // 2), ra)
            self.surface.blit(glow, (cx - r * 3 // 2, cy - r * 3 // 2))

            # Ring (if any) — behind planet
            if has_ring:
                ring_surf = pygame.Surface((r * 3, int(r * 2.4)), pygame.SRCALPHA)
                ring_col = _hsv((hue + 0.08) % 1.0, sat * 0.4, 0.35)
                for rw in range(int(r * 1.4), int(r * 1.8), 2):
                    rh = int(rw * ring_tilt)
                    pygame.draw.ellipse(ring_surf, (*ring_col, 80),
                                        (r * 3 // 2 - rw, ring_surf.get_height() // 2 - rh,
                                         rw * 2, rh * 2), 1)
                self.surface.blit(ring_surf, (cx - r * 3 // 2,
                                              cy - ring_surf.get_height() // 2))

            # Planet body — dark side gradient
            body_surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            for layer in range(6, 0, -1):
                lr = int(r * layer / 6)
                shade = 0.22 + 0.10 * (1 - layer / 6)
                col = _hsv(hue, sat, shade)
                pygame.draw.circle(body_surf, (*col, 245), (r, r), lr)
            # Surface band (cloud belt)
            for i in range(3):
                band_y = int(r * (0.4 + i * 0.3 + band_seed))
                if 0 < band_y < 2 * r:
                    band_col = _hsv((hue + 0.04) % 1.0, sat * 0.7, 0.35)
                    pygame.draw.line(body_surf, (*band_col, 120),
                                     (max(0, r - int(r * 0.8)), band_y),
                                     (min(2 * r, r + int(r * 0.8)), band_y), 2)
            # Terminator (day/night line)
            terminator = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            for px in range(int(r * 0.3)):
                a = int(120 * (1 - px / (r * 0.3)))
                pygame.draw.line(terminator, (0, 0, 0, a),
                                 (px, 0), (px, 2 * r), 1)
            body_surf.blit(terminator, (0, 0))

            self.surface.blit(body_surf, (cx - r, cy - r))

            # Atmosphere highlight (lit edge)
            atm_surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            atm_col = _hsv(hue, sat * 0.6, 1.0)
            pygame.draw.circle(atm_surf, (*atm_col, 28), (r, r), r, 3)
            self.surface.blit(atm_surf, (cx - r, cy - r))

            # Ring foreground arc
            if has_ring:
                ring_surf = pygame.Surface((r * 3, int(r * 2.4)), pygame.SRCALPHA)
                ring_col = _hsv((hue + 0.08) % 1.0, sat * 0.4, 0.5)
                for rw in range(int(r * 1.4), int(r * 1.8), 2):
                    rh = int(rw * ring_tilt)
                    pygame.draw.arc(ring_surf, (*ring_col, 120),
                                    (r * 3 // 2 - rw, ring_surf.get_height() // 2 - rh,
                                     rw * 2, rh * 2),
                                    0, math.pi, 2)
                self.surface.blit(ring_surf, (cx - r * 3 // 2,
                                              cy - ring_surf.get_height() // 2))

    # ------------------------------------------------------------------  SPACE STATIONS (distant silhouettes)
    def _gen_stations(self) -> list:
        """Generate 2-3 distant station silhouettes at mid-field positions."""
        rng = random.Random(self._STAR_SEED + 503)
        out = []
        count = rng.randint(2, 3)
        types = ["ring", "cross", "tower"]
        for i in range(count):
            x = int(S.SCREEN_W * (0.15 + i * 0.30 + rng.uniform(-0.08, 0.08)))
            y = int(S.FLIGHT_H * rng.uniform(0.10, 0.75))
            kind = rng.choice(types)
            scale = rng.uniform(0.55, 1.0)      # 1.0 = full template size
            spin_rate = rng.uniform(-0.04, 0.04) # rad/s, slow parallax spin
            spin_phase = rng.random() * math.tau
            # dim amber/grey palette index
            hue = rng.uniform(0.08, 0.14)
            out.append((x, y, kind, scale, spin_rate, spin_phase, hue))
        return out

    def _draw_stations(self, t: float):
        surf = pygame.Surface((S.SCREEN_W, S.FLIGHT_H), pygame.SRCALPHA)
        for x, y, kind, scale, spin_rate, spin_phase, hue in self._stations:
            angle = spin_phase + spin_rate * t
            # Dim amber silhouette
            col = _hsv(hue, 0.55, 0.28)
            lit = _hsv(hue, 0.40, 0.52)   # lit window dots
            s = scale

            if kind == "ring":
                # Torus station: outer ring, inner ring, 4 spokes, hub
                ro = int(38 * s)
                ri = int(22 * s)
                spoke_len = int(20 * s)
                for r_px, w in ((ro, 2), (ri, 1)):
                    pygame.draw.circle(surf, (*col, 180), (x, y), r_px, w)
                for a in (0, math.pi / 2, math.pi, 3 * math.pi / 2):
                    a2 = a + angle
                    sx = x + int(math.cos(a2) * spoke_len)
                    sy = y + int(math.sin(a2) * spoke_len)
                    pygame.draw.line(surf, (*col, 160), (x, y), (sx, sy), 1)
                pygame.draw.circle(surf, (*col, 200), (x, y), int(6 * s))
                # Blinking windows around the outer ring
                for i in range(8):
                    wa = angle + i * math.tau / 8
                    wx = x + int(math.cos(wa) * ro)
                    wy = y + int(math.sin(wa) * ro)
                    blink = 0.5 + 0.5 * math.sin(t * 1.1 + i * 1.3)
                    if blink > 0.6:
                        surf.set_at((wx, wy), (*lit, 255))

            elif kind == "cross":
                # Cross-shaped station: 4 arms + hab module squares at tips
                arm_len = int(44 * s)
                arm_w   = int(6 * s)
                for a in (0.0, math.pi / 2):
                    a2 = a + angle
                    ex = x + int(math.cos(a2) * arm_len)
                    ey = y + int(math.sin(a2) * arm_len)
                    pygame.draw.line(surf, (*col, 180),
                                     (x - int(math.cos(a2) * arm_len),
                                      y - int(math.sin(a2) * arm_len)),
                                     (ex, ey), arm_w)
                    # Hab box at tip
                    hw = int(9 * s)
                    pygame.draw.rect(surf, (*col, 200),
                                     (ex - hw, ey - hw, hw * 2, hw * 2))
                # Central hub ring
                pygame.draw.circle(surf, (*col, 210), (x, y), int(11 * s), 2)
                # Running light blink
                blink = 0.5 + 0.5 * math.sin(t * 0.8)
                if blink > 0.55:
                    surf.set_at((x, y), (*lit, 255))

            else:  # tower
                # Vertical tower: thin mast, 3 horizontal decks, antenna
                mast_h  = int(70 * s)
                deck_w  = [int(w * s) for w in (28, 20, 12)]
                deck_ys = [-int(mast_h * f) for f in (0.2, 0.5, 0.78)]
                ax = x + int(math.cos(angle) * 0)  # tower doesn't spin visibly — slight drift
                # Mast
                pygame.draw.line(surf, (*col, 170),
                                 (x, y), (x, y - mast_h), 1)
                # Decks
                for dw, dy_off in zip(deck_w, deck_ys):
                    dh = int(4 * s)
                    pygame.draw.rect(surf, (*col, 185),
                                     (x - dw, y + dy_off - dh, dw * 2, dh * 2))
                # Antenna tip blink
                tip_y = y - mast_h - int(8 * s)
                pygame.draw.line(surf, (*col, 140),
                                 (x, y - mast_h), (x, tip_y), 1)
                blink = 0.5 + 0.5 * math.sin(t * 2.3)
                if blink > 0.5:
                    surf.set_at((x, tip_y), (255, 60, 60, 220))  # red beacon

        self.surface.blit(surf, (0, 0))

    # ------------------------------------------------------------------  SHOOTING STARS
    def _update_shooting_stars(self, dt: float, t: float):
        # Maybe spawn
        self._next_shooting_star -= dt
        if self._next_shooting_star <= 0:
            self._next_shooting_star = random.uniform(5.0, 14.0)
            # Spawn from random edge
            edge = random.randint(0, 3)
            if edge == 0:    # top
                x, y = random.randint(0, S.SCREEN_W), -20
                vx, vy = random.uniform(-280, 280), random.uniform(180, 380)
            elif edge == 1:  # right
                x, y = S.SCREEN_W + 20, random.randint(0, S.FLIGHT_H)
                vx, vy = random.uniform(-380, -180), random.uniform(-180, 180)
            elif edge == 2:  # bottom (unusual but ok)
                x, y = random.randint(0, S.SCREEN_W), S.FLIGHT_H + 20
                vx, vy = random.uniform(-280, 280), random.uniform(-380, -180)
            else:            # left
                x, y = -20, random.randint(0, S.FLIGHT_H)
                vx, vy = random.uniform(180, 380), random.uniform(-180, 180)
            life = random.uniform(0.9, 1.6)
            self._shooting_stars.append([x, y, vx, vy, 0.0, life])

        # Update
        alive = []
        for s in self._shooting_stars:
            s[0] += s[2] * dt
            s[1] += s[3] * dt
            s[4] += dt
            if s[4] < s[5] and -40 < s[0] < S.SCREEN_W + 40 and -40 < s[1] < S.FLIGHT_H + 40:
                alive.append(s)
        self._shooting_stars = alive

    def _draw_shooting_stars(self, t: float):
        for x, y, vx, vy, age, life in self._shooting_stars:
            frac = age / life
            speed = math.hypot(vx, vy)
            if speed < 1:
                continue
            ux, uy = vx / speed, vy / speed
            # Tail length scales with life remaining
            tail_len = (1 - frac * 0.6) * 60
            tx, ty = x - ux * tail_len, y - uy * tail_len
            # Color: cyan-white head, fades
            brightness = (1 - frac) ** 1.3
            head_col = (int(220 * brightness), int(240 * brightness),
                        int(255 * brightness))
            tail_col = (int(20 * brightness), int(80 * brightness),
                        int(180 * brightness))
            pygame.draw.line(self.surface, tail_col, (tx, ty), (x, y), 2)
            pygame.draw.line(self.surface, head_col,
                             (x - ux * 8, y - uy * 8), (x, y), 2)
            pygame.draw.circle(self.surface, head_col, (int(x), int(y)), 2)

    # ------------------------------------------------------------------  EMBERS (exhaust particles)
    def _spawn_ember(self, x: float, y: float, vx: float, vy: float, hue: float):
        self._embers.append([x, y, vx, vy, 0.0, random.uniform(0.5, 1.1), hue])

    def _update_embers(self, dt: float):
        alive = []
        for e in self._embers:
            e[0] += e[2] * dt
            e[1] += e[3] * dt
            # Decelerate slightly (space drag-free, but visual decay)
            e[2] *= 0.97
            e[3] *= 0.97
            e[4] += dt
            if e[4] < e[5]:
                alive.append(e)
        self._embers = alive

    def _draw_embers(self):
        for x, y, vx, vy, age, life, hue in self._embers:
            if not (0 <= x < S.SCREEN_W and 0 <= y < S.FLIGHT_H):
                continue
            frac = 1.0 - age / life
            val  = 0.4 + 0.6 * frac
            col  = _hsv(hue, 0.85, val)
            size = 1 if frac < 0.5 else 2
            pygame.draw.circle(self.surface, col, (int(x), int(y)), size)

    # ------------------------------------------------------------------  DUST
    def _gen_dust(self) -> list:
        rng = random.Random(self._STAR_SEED + 777)
        return [
            (rng.randint(0, S.SCREEN_W),
             rng.randint(0, S.SCREEN_H),
             rng.random(),                     # base hue
             rng.uniform(0.4, 1.8),            # drift freq
             rng.random() * math.tau,          # phase
             rng.uniform(12, 28))              # drift radius px
            for _ in range(90)
        ]

    def _draw_dust(self, t: float):
        surf = self.surface
        for ox, oy, hue, freq, phase, rad in self._dust:
            x = int((ox + math.cos(t * freq + phase) * rad) % S.SCREEN_W)
            y = int((oy + math.sin(t * freq * 0.7 + phase) * rad * 0.6) % S.SCREEN_H)
            brightness = 0.10 + 0.08 * abs(math.sin(t * freq * 1.3 + phase))
            col = _hsv((hue + t * 0.015) % 1.0, 0.65, brightness)
            surf.set_at((x, y), col)

    # ------------------------------------------------------------------  STARS
    def _gen_stars(self) -> list:
        rng = random.Random(self._STAR_SEED)
        stars = []
        for _ in range(self._STAR_COUNT):
            stars.append((
                rng.randint(0, S.SCREEN_W - 1),
                rng.randint(0, S.SCREEN_H - 1),
                rng.random(),              # lum
                rng.random(),              # hue
                rng.uniform(0.6, 2.5),     # twinkle speed
                rng.random() * math.tau,   # twinkle phase
            ))
        return stars

    def _draw_stars(self, t: float = 0.0):
        surf = self.surface
        for x, y, lum, hue, tw_speed, tw_phase in self._stars:
            twinkle = 0.5 + 0.5 * math.sin(t * tw_speed + tw_phase)
            if lum < 0.48:
                v = int(lum * 40 * (0.7 + 0.3 * twinkle))
                surf.set_at((x, y), (v, v, v + 9))
            elif lum < 0.80:
                v = int((50 + lum * 65) * (0.75 + 0.25 * twinkle))
                surf.set_at((x, y), (v - 12, v - 12, v))
            elif lum < 0.93:
                br = int(185 + 35 * twinkle)
                pygame.draw.circle(surf, (br - 10, br - 10, br),
                                   (x, y), 2 if twinkle > 0.85 else 1)
            else:
                shifted_hue = (hue + self._sector_hue_shift) % 1.0
                neon = _hsv(shifted_hue, 0.9, 1.0)
                r = 2 if twinkle > 0.7 else 1
                pygame.draw.circle(surf, neon, (x, y), r)
                if twinkle > 0.88:
                    pygame.draw.line(surf, neon, (x - 4, y), (x + 4, y), 1)
                    pygame.draw.line(surf, neon, (x, y - 4), (x, y + 4), 1)

    # ------------------------------------------------------------------  SCAN PINGS
    def _draw_scan_pings(self, t: float):
        PING_DUR = 3.2
        alive = []
        for cx, cy, start_t in self._scan_pings:
            age  = t - start_t
            if age > PING_DUR:
                continue
            alive.append((cx, cy, start_t))
            frac   = age / PING_DUR
            radius = int(frac * 560)
            col    = (0, int(200 * (1 - frac)), int(255 * (1 - frac)))
            if radius > 0:
                pygame.draw.circle(self.surface, col, (cx, cy), radius, 2)
            if radius > 30:
                pygame.draw.circle(self.surface, (0, int(130 * (1-frac)), int(175 * (1-frac))),
                                   (cx, cy), radius // 2, 1)
        self._scan_pings = alive

    # ------------------------------------------------------------------  GRAVITY WELLS
    def _draw_gravity_wells(self, run_mgr, t: float):
        if run_mgr.sector is None:
            return
        for well in run_mgr.sector.gravity.wells:
            self._draw_well(well, t)

    def _draw_well(self, well, t: float):
        cx, cy = int(well.pos.x), int(well.pos.y)
        r      = well.radius
        drift  = (t * 0.07) % 1.0
        pulse  = math.sin(t * 1.4) * 4.5

        # 7 concentric rings, hue spread across 0.45 of wheel, width=2
        rings = [
            (r * 4.8 + pulse * 1.6, 0.00, 0.16, 2),
            (r * 3.6 + pulse * 1.3, 0.06, 0.24, 2),
            (r * 2.7 + pulse * 1.0, 0.12, 0.40, 2),
            (r * 2.0 + pulse * 0.7, 0.20, 0.58, 2),
            (r * 1.4 + pulse * 0.4, 0.28, 0.74, 3),
            (r * 1.0 + pulse * 0.2, 0.36, 0.88, 3),
            (r * 0.62,              0.45, 0.98, 3),
        ]
        for radius, hue_off, val, width in rings:
            ir    = max(2, int(radius))
            hue   = (drift + hue_off) % 1.0
            color = _hsv(hue, 0.95, val)
            pygame.draw.circle(self.surface, color, (cx, cy), ir, width)
            if val > 0.50:
                glow = _hsv(hue, 0.72, val * 0.20)
                pygame.draw.circle(self.surface, glow, (cx, cy), ir + 5, 2)

        # Primary rotating radial lines (8-fold, width=2)
        line_hue = (drift + 0.12) % 1.0
        line_col = _hsv(line_hue, 0.80, 0.38)
        for i in range(8):
            ang = math.radians(i * 45 + t * 9)
            x1 = cx + int(math.cos(ang) * r * 1.7)
            y1 = cy + int(math.sin(ang) * r * 1.7)
            x2 = cx + int(math.cos(ang) * r * 0.90)
            y2 = cy + int(math.sin(ang) * r * 0.90)
            pygame.draw.line(self.surface, line_col, (x1, y1), (x2, y2), 2)

        # Counter-rotating secondary spokes (4-fold, width=2)
        sec_col = _hsv((drift + 0.22) % 1.0, 0.55, 0.28)
        for i in range(4):
            ang = math.radians(i * 90 + 22.5 - t * 5)
            x1 = cx + int(math.cos(ang) * r * 2.4)
            y1 = cy + int(math.sin(ang) * r * 2.4)
            x2 = cx + int(math.cos(ang) * r * 1.2)
            y2 = cy + int(math.sin(ang) * r * 1.2)
            pygame.draw.line(self.surface, sec_col, (x1, y1), (x2, y2), 2)

        # Tertiary fine spokes (16-fold, very dim)
        fine_col = _hsv((drift + 0.35) % 1.0, 0.40, 0.14)
        for i in range(16):
            ang = math.radians(i * 22.5 + t * 3)
            x1 = cx + int(math.cos(ang) * r * 3.0)
            y1 = cy + int(math.sin(ang) * r * 3.0)
            x2 = cx + int(math.cos(ang) * r * 1.5)
            y2 = cy + int(math.sin(ang) * r * 1.5)
            pygame.draw.line(self.surface, fine_col, (x1, y1), (x2, y2), 1)

        # Accretion disc — orbiting particles
        n_particles = 28
        for i in range(n_particles):
            base_ang = (i / n_particles) * math.tau
            # Particle has its own orbital radius and speed
            seed = (cx * 17 + cy * 31 + i * 53) % 100
            orbit_r = r * (1.5 + (seed / 100) * 0.8)
            orbit_speed = 0.7 + (seed % 7) * 0.12
            ang = base_ang + t * orbit_speed
            px = cx + math.cos(ang) * orbit_r
            py = cy + math.sin(ang) * orbit_r * 0.42   # squashed = inclined disc
            phue = (drift + 0.15 + (seed / 100) * 0.2) % 1.0
            # Brightness pulses as particle orbits
            bright = 0.5 + 0.5 * math.sin(ang * 2 + t * 1.4)
            pcol = _hsv(phue, 0.85, 0.5 + 0.4 * bright)
            pygame.draw.circle(self.surface, pcol, (int(px), int(py)),
                               2 if bright > 0.5 else 1)

        # Pulsing core
        core_r   = max(5, int(r * 0.24))
        core_hue = (drift + 0.5) % 1.0
        pygame.draw.circle(self.surface, _hsv(core_hue, 0.60, 0.88),
                           (cx, cy), core_r + 6)
        pygame.draw.circle(self.surface, _hsv(core_hue, 0.20, 1.0),
                           (cx, cy), core_r)
        pygame.draw.circle(self.surface, (255, 255, 255), (cx, cy),
                           max(2, core_r // 3))

        # Lensing distortion — bright ring around event horizon
        lens_pulse = 0.7 + 0.3 * math.sin(t * 2.5)
        lens_col = (int(255 * lens_pulse), int(255 * lens_pulse),
                    int(220 * lens_pulse))
        pygame.draw.circle(self.surface, lens_col, (cx, cy),
                           core_r + 9, 1)

    # ------------------------------------------------------------------  DEBRIS
    def _draw_debris(self, run_mgr, t: float):
        for rock in getattr(run_mgr, "debris", []):
            self._draw_rock(rock, t, False)
        for rock in getattr(run_mgr, "shower_rocks", []):
            self._draw_rock(rock, t, True)

    def _draw_rock(self, rock, t: float, tint_hot: bool):
        pts = rock.world_pts()
        if len(pts) < 3:
            return
        # HP-based tint: brighter as damage accumulates
        if rock.is_hit:
            fill, edge = (70, 45, 90), (230, 175, 255)
        elif tint_hot:
            fill, edge = (38, 20, 24), (190, 80, 55)
        else:
            # Slightly lighter fill for rocks with low HP
            hp_frac = rock.hp / (3 if rock.radius >= 13 else 2)
            dim = int(22 * (1 - hp_frac) * 0.5)
            fill = (20 + dim, 16 + dim, 32 + dim)
            edge = (65, 52, 88)
        pygame.draw.polygon(self.surface, fill, pts)
        pygame.draw.polygon(self.surface, edge, pts, 2)
        # Glint on first vertex
        cx = sum(p[0] for p in pts) // len(pts)
        cy = sum(p[1] for p in pts) // len(pts)
        glint_phase = (t * 1.1 + cx * 0.01) % math.tau
        if math.sin(glint_phase) > 0.82:
            glint_col = (140, 115, 165) if not tint_hot else (210, 125, 80)
            pygame.draw.circle(self.surface, glint_col, pts[0], 2)

    # ------------------------------------------------------------------  CANISTERS
    def _draw_canisters(self, run_mgr, t: float):
        for can in getattr(run_mgr, "canisters", []):
            if not can.picked_up:
                self._draw_canister(can, t)

    def _draw_canister(self, can, t: float):
        cx, cy = int(can.pos.x), int(can.pos.y)
        pulse  = math.sin(t * 3.2 + can.pulse) * 2.5
        size   = int(10 + pulse)
        hue    = (0.33 + can.hue_offset * 0.15 + math.sin(t * 0.6) * 0.08) % 1.0
        c_bright = _hsv(hue, 0.9, 1.0)
        c_mid    = _hsv(hue, 0.7, 0.55)
        c_glow   = _hsv(hue, 0.7, 0.30)
        c_dim    = _hsv(hue, 0.5, 0.18)

        # Outer halo
        halo_surf = pygame.Surface((size * 4, size * 4), pygame.SRCALPHA)
        pygame.draw.circle(halo_surf, (*c_dim, 70),
                           (size * 2, size * 2), size + 8)
        pygame.draw.circle(halo_surf, (*c_glow, 40),
                           (size * 2, size * 2), size + 14)
        self.surface.blit(halo_surf, (cx - size * 2, cy - size * 2))

        # Diamond layers
        pygame.draw.polygon(self.surface, c_glow,
                            [(cx, cy-size-5),(cx+size+5,cy),(cx,cy+size+5),(cx-size-5,cy)])
        pygame.draw.polygon(self.surface, c_mid,
                            [(cx, cy-size-1),(cx+size+1,cy),(cx,cy+size+1),(cx-size-1,cy)])
        pygame.draw.polygon(self.surface, c_bright,
                            [(cx, cy-size),(cx+size,cy),(cx,cy+size),(cx-size,cy)], 2)

        # Rotating tick marks
        ang_off = t * 1.2
        for i in range(4):
            ang = ang_off + i * math.pi / 2
            tx1 = int(cx + math.cos(ang) * (size - 5))
            ty1 = int(cy + math.sin(ang) * (size - 5))
            tx2 = int(cx + math.cos(ang) * (size - 2))
            ty2 = int(cy + math.sin(ang) * (size - 2))
            pygame.draw.line(self.surface, c_bright, (tx1, ty1), (tx2, ty2), 1)

        # Inner cross + dot
        pygame.draw.line(self.surface, c_bright, (cx-3,cy), (cx+3,cy), 1)
        pygame.draw.line(self.surface, c_bright, (cx,cy-3), (cx,cy+3), 1)
        # Centre fuel-marker dot
        center_pulse = 0.6 + 0.4 * math.sin(t * 6.0 + can.pulse)
        center_col = (int(220 * center_pulse), int(255 * center_pulse), int(180 * center_pulse))
        pygame.draw.circle(self.surface, center_col, (cx, cy), 2)

        # Orbiting sparkles
        for spk in range(2):
            sang = t * 2.0 + spk * math.pi + can.pulse
            sr   = size + 6 + 2 * math.sin(t * 3.0 + spk)
            sx   = int(cx + math.cos(sang) * sr)
            sy   = int(cy + math.sin(sang) * sr)
            pygame.draw.circle(self.surface, c_bright, (sx, sy), 1)

    # ------------------------------------------------------------------  SATELLITES
    def _draw_satellites(self, run_mgr, t: float):
        surf = self.surface
        for sat in getattr(run_mgr, "satellites", []):
            if not sat.alive:
                continue
            cx, cy = int(sat.pos.x), int(sat.pos.y)
            ang    = math.radians(sat.angle)

            # Hit flash
            if sat._hit_t > 0:
                col = (255, 210, 80)
                dim = (180, 140, 40)
            else:
                col = (120, 105, 75)
                dim = (52, 46, 33)

            # Four solar panel arms at 0°, 90°, 180°, 270°
            for arm_angle in (ang, ang + math.pi / 2, ang + math.pi, ang + 3 * math.pi / 2):
                cos_a, sin_a = math.cos(arm_angle), math.sin(arm_angle)
                # Arm strut
                ix = int(cx + cos_a * 7)
                iy = int(cy + sin_a * 7)
                ox = int(cx + cos_a * sat.arm_len)
                oy = int(cy + sin_a * sat.arm_len)
                pygame.draw.line(surf, col, (ix, iy), (ox, oy), 1)
                # Panel (perpendicular bar at tip)
                pa = arm_angle + math.pi / 2
                pcos, psin = math.cos(pa), math.sin(pa)
                p1 = (int(ox + pcos * 8), int(oy + psin * 8))
                p2 = (int(ox - pcos * 8), int(oy - psin * 8))
                pygame.draw.line(surf, dim, p1, p2, 3)
                pygame.draw.line(surf, col, p1, p2, 1)

            # Central hub
            pygame.draw.circle(surf, dim,  (cx, cy), 6)
            pygame.draw.circle(surf, col,  (cx, cy), 6, 1)

            # Fuel beacon — pulsing green dot at hub centre
            if sat.has_fuel:
                pulse = 0.55 + 0.45 * math.sin(sat._fuel_t * 3.2)
                beacon_col = (0, int(140 + 115 * pulse), int(60 + 68 * pulse))
                pygame.draw.circle(surf, beacon_col, (cx, cy), 3)

    # ------------------------------------------------------------------  ALIEN SHIP
    def _draw_alien(self, run_mgr, t: float):
        alien = getattr(run_mgr, "alien", None)
        if alien is None or not alien.alive:
            return
        surf = self.surface

        # Trail — dots fading from cyan to nothing
        n = len(alien._trail)
        for i, (tx, ty) in enumerate(alien._trail):
            frac = (i + 1) / max(1, n)
            r = int(frac * 20)
            g = int(frac * 220)
            b = int(frac * 200)
            size = max(1, int(frac * 4))
            if 0 <= int(tx) < S.SCREEN_W and 0 <= int(ty) < S.FLIGHT_H:
                pygame.draw.circle(surf, (r, g, b), (int(tx), int(ty)), size)

        # Hull fill + outline
        hull  = alien.world_pts(_ALIEN_HULL)
        inner = alien.world_pts(_ALIEN_INNER)
        if len(hull) >= 3:
            pygame.draw.polygon(surf, (0, 16, 12), hull)
            pygame.draw.polygon(surf, (0, 235, 200), hull, 2)
        if len(inner) >= 3:
            pygame.draw.polygon(surf, (0, 50, 38), inner)

        # Pulsing glow behind hull
        glow_surf = pygame.Surface((160, 160), pygame.SRCALPHA)
        ga = int(35 + 20 * math.sin(t * 5.0))
        pygame.draw.circle(glow_surf, (0, 235, 200, ga), (80, 80), 58)
        surf.blit(glow_surf, (int(alien.pos.x) - 80, int(alien.pos.y) - 80))

    # ------------------------------------------------------------------  BARGE RADAR
    def _draw_barge_radar(self, run_mgr, ship, t: float):
        barges = getattr(run_mgr, "barges", [])
        if not barges:
            return
        surf = self.surface
        R    = 36    # radar circle radius px
        cx   = S.SCREEN_W - R - 14
        cy   = R + 14

        # Background circle
        bg = pygame.Surface((R * 2 + 4, R * 2 + 4), pygame.SRCALPHA)
        pygame.draw.circle(bg, (6, 6, 10, 200), (R + 2, R + 2), R)
        pygame.draw.circle(bg, (60, 60, 80, 120), (R + 2, R + 2), R, 1)
        surf.blit(bg, (cx - R - 2, cy - R - 2))

        # Dim crosshair
        pygame.draw.line(surf, (30, 30, 40), (cx - R, cy), (cx + R, cy), 1)
        pygame.draw.line(surf, (30, 30, 40), (cx, cy - R), (cx, cy + R), 1)

        # Ship dot (always centre)
        pygame.draw.circle(surf, (0, 200, 80), (cx, cy), 2)

        # Map scale: radar covers the full screen
        scale_x = R / (S.SCREEN_W / 2)
        scale_y = R / (S.FLIGHT_H / 2)
        scx = ship.body.pos.x if hasattr(ship, "body") else ship.pos.x
        scy = ship.body.pos.y if hasattr(ship, "body") else ship.pos.y

        for barge in barges:
            bx = barge.body.pos.x
            by = barge.body.pos.y
            dx = (bx - scx) * scale_x
            dy = (by - scy) * scale_y
            # Clamp blip to radar circle edge if off range
            dist2d = math.hypot(dx, dy)
            if dist2d > R - 3:
                dx = dx / dist2d * (R - 3)
                dy = dy / dist2d * (R - 3)
            bx_r = int(cx + dx)
            by_r = int(cy + dy)

            # Color by state
            state = barge.state
            if state in ("torch", "clamp"):
                pulse = 0.5 + 0.5 * math.sin(t * 8.0)
                blip_col = (int(220 + 35 * pulse), int(30 + 20 * pulse), 20)
            elif state == "chase":
                blip_col = (255, 140, 0)
            else:
                blip_col = (120, 85, 0)

            pygame.draw.circle(surf, blip_col, (bx_r, by_r), 3)
            pygame.draw.circle(surf, blip_col, (bx_r, by_r), 3, 1)

        # Label
        font = pygame.font.SysFont("monospace", 8)
        label = font.render("RADAR", True, (40, 40, 55))
        surf.blit(label, (cx - label.get_width() // 2, cy + R + 2))

    # ------------------------------------------------------------------  BULLETS
    def _draw_bullets(self, ship):
        if not hasattr(ship, "gun"):
            return
        for bullet in ship.gun.bullets:
            bx, by = int(bullet.pos.x), int(bullet.pos.y)
            # Direction line — bright green bolt
            dx = int(bullet.vel.x * 0.022)
            dy = int(bullet.vel.y * 0.022)
            age_frac = 1.0 - bullet.lifetime / S.BULLET_LIFETIME
            hue = 0.33 - age_frac * 0.18   # green → cyan as it ages
            col_core  = _hsv(hue, 0.8, 1.0)
            col_glow  = _hsv(hue, 0.6, 0.45)
            pygame.draw.line(self.surface, col_glow,
                             (bx - dx*2, by - dy*2), (bx + dx, by + dy), 3)
            pygame.draw.line(self.surface, col_core,
                             (bx - dx,   by - dy),   (bx + dx, by + dy), 1)
            pygame.draw.circle(self.surface, (220, 255, 220), (bx, by), 2)

    # ------------------------------------------------------------------  SHIP
    def _draw_trail(self, ship, t: float):
        if not ship.is_alive:
            return
        vel   = ship.body.vel
        speed = vel.length()
        if speed < 30:
            return
        pos       = ship.pos
        trail_len = min(12, 4 + int(speed / 60))
        for i in range(1, trail_len + 1):
            frac = i / (trail_len + 1.0)
            gx = int(pos.x - vel.x * 0.013 * i)
            gy = int(pos.y - vel.y * 0.013 * i)
            if 0 <= gx < S.SCREEN_W and 0 <= gy < S.SCREEN_H:
                hue   = 0.60 - frac * 0.48
                val   = max(0.0, 0.72 - frac * 0.06)
                color = _hsv(hue, 0.95, val)
                pygame.draw.circle(self.surface, color, (gx, gy),
                                   max(1, 4 - i // 3))

    def _draw_velocity_indicator(self, ship):
        if not ship.is_alive:
            return
        vel   = ship.body.vel
        speed = vel.length()
        if speed < 20:
            return
        pos = ship.pos
        nx, ny   = vel.x / speed, vel.y / speed
        px_, py_ = -ny, nx
        dist = 30
        tip  = (int(pos.x + nx * (dist + 5)), int(pos.y + ny * (dist + 5)))
        arm1 = (int(pos.x + nx * (dist-4) + px_*5), int(pos.y + ny * (dist-4) + py_*5))
        arm2 = (int(pos.x + nx * (dist-4) - px_*5), int(pos.y + ny * (dist-4) - py_*5))
        pygame.draw.line(self.surface, (50, 60, 95), arm1, tip, 1)
        pygame.draw.line(self.surface, (50, 60, 95), arm2, tip, 1)
        rx = int(pos.x - nx * dist)
        ry = int(pos.y - ny * dist)
        pygame.draw.circle(self.surface, (70, 28, 28), (rx, ry), 4, 1)
        pygame.draw.line(self.surface, (70, 28, 28),
                         (rx - int(px_*3), ry - int(py_*3)),
                         (rx + int(px_*3), ry + int(py_*3)), 1)

    def _draw_ship(self, ship, t: float = 0.0):
        if not ship.is_alive:
            return
        pos   = ship.pos
        angle = ship.angle
        raw   = [(18,0),(5,-9),(-14,-7),(-14,9),(5,10)]
        pts   = [self._rotate_pt(p, angle, pos) for p in raw]

        hp = ship.hull_pct

        # Engine ambient glow halo (below ship outline)
        thrust_pulse = 0.7 + 0.3 * math.sin(t * 8.0)
        ambient_glow_r = int(28 + 6 * thrust_pulse)
        glow_surf = pygame.Surface((ambient_glow_r * 2, ambient_glow_r * 2), pygame.SRCALPHA)
        glow_hue = 0.58 + (1.0 - hp) * 0.20
        ag_col = _hsv(glow_hue, 0.5, 0.8)
        for layer in range(3):
            la = max(0, 28 - layer * 9)
            pygame.draw.circle(glow_surf, (*ag_col, la),
                               (ambient_glow_r, ambient_glow_r),
                               ambient_glow_r - layer * 6)
        self.surface.blit(glow_surf,
                          (int(pos.x) - ambient_glow_r, int(pos.y) - ambient_glow_r))

        # Damage glow (red halo when low HP)
        glow_r   = int((1.0 - hp) * 60)
        glow_col = (glow_r, max(0, 55 - int((1-hp)*42)), max(0, 115 - int((1-hp)*85)))
        pygame.draw.polygon(self.surface, glow_col, pts, 4)

        # Hull fill — darker blue interior, like ship is solid
        hull_fill = (8, 14, 28)
        pygame.draw.polygon(self.surface, hull_fill, pts)

        # Hull outline — slightly thicker, brighter on intact ship
        outline_col = S.WHITE_VEC if hp > 0.4 else (200, 180, 180)
        pygame.draw.polygon(self.surface, outline_col, pts, 2)

        # Panel/plate seams — subdivide hull
        seam_col = (60, 60, 90)
        seam_pts = [
            ((10, -5), (-8, -5)),    # top panel seam
            ((10, 6),  (-8, 6)),     # bottom panel seam
            ((5, -9),  (5, 10)),     # mid vertical seam
            ((-2, -7), (-2, 9)),     # rear vertical seam
        ]
        for a, b in seam_pts:
            pa = self._rotate_pt(a, angle, pos)
            pb = self._rotate_pt(b, angle, pos)
            pygame.draw.line(self.surface, seam_col, pa, pb, 1)

        # Cockpit window — cyan glow on the nose
        cockpit_pts = [(15, -2), (10, -4), (5, -3), (5, 4), (10, 5), (15, 3)]
        cpt = [self._rotate_pt(p, angle, pos) for p in cockpit_pts]
        cockpit_pulse = 0.6 + 0.4 * math.sin(t * 1.8)
        cockpit_col = (int(20 + 80 * cockpit_pulse),
                       int(140 + 80 * cockpit_pulse),
                       int(180 + 60 * cockpit_pulse))
        pygame.draw.polygon(self.surface, (4, 30, 60), cpt)
        pygame.draw.polygon(self.surface, cockpit_col, cpt, 1)
        # Cockpit glint
        glint_pt = self._rotate_pt((12, -1), angle, pos)
        pygame.draw.circle(self.surface, (180, 240, 255), glint_pt, 1)

        # Engine nozzle (rear) — darker housing with hot core
        nozzle = [self._rotate_pt(p, angle, pos) for p in
                  ((-14,-5),(-20,-3),(-20,5),(-14,7))]
        pygame.draw.polygon(self.surface, (0, 22, 50), nozzle)
        pygame.draw.polygon(self.surface, (75, 95, 130), nozzle, 1)
        # Inner nozzle heat ring
        nozzle_inner_pulse = 0.6 + 0.4 * math.sin(t * 14.0)
        nz_inner = self._rotate_pt((-17, 0), angle, pos)
        nz_col = (int(200 * nozzle_inner_pulse),
                  int(140 * nozzle_inner_pulse),
                  int(40 * nozzle_inner_pulse))
        pygame.draw.circle(self.surface, nz_col, nz_inner, 2)

        # RCS port dots — slight pulse
        rcs_pulse = 0.4 + 0.4 * math.sin(t * 6.0)
        rcs_col = (int(40 + 60 * rcs_pulse), int(40 + 60 * rcs_pulse), int(80 + 50 * rcs_pulse))
        for lx, ly in ((8,-8),(8,10),(-10,-6),(-10,8)):
            rpt = self._rotate_pt((lx, ly), angle, pos)
            pygame.draw.circle(self.surface, rcs_col, rpt, 1)

        # Wing tip nav lights — red left, green right (constant)
        nav_l = self._rotate_pt((-14, -7), angle, pos)
        nav_r = self._rotate_pt((-14, 9), angle, pos)
        pygame.draw.circle(self.surface, (255, 60, 60), nav_l, 2)
        pygame.draw.circle(self.surface, (60, 255, 100), nav_r, 2)

        # Battle damage scars — appear on low HP
        if hp < 0.6:
            # Deterministic scar positions based on ship's "scar seed"
            n_scars = int((0.6 - hp) * 10)
            rng = random.Random(id(ship) & 0xFFFF)
            for i in range(n_scars):
                sx = rng.uniform(-12, 14)
                sy = rng.uniform(-7, 8)
                slen = rng.uniform(2, 4)
                sang = rng.uniform(0, math.tau)
                p1 = self._rotate_pt((sx, sy), angle, pos)
                p2 = self._rotate_pt((sx + math.cos(sang) * slen,
                                     sy + math.sin(sang) * slen), angle, pos)
                pygame.draw.line(self.surface, (180, 60, 50), p1, p2, 1)

            # Sparking scar — flickers
            if hp < 0.3 and int(t * 6) % 2 == 0:
                spk = self._rotate_pt((rng.uniform(-10, 8), rng.uniform(-5, 5)), angle, pos)
                pygame.draw.circle(self.surface, (255, 220, 80), spk, 2)
                pygame.draw.circle(self.surface, (255, 80, 30), spk, 1)

        # Gun barrel indicator
        if hasattr(ship, "gun") and not ship.gun.is_jammed:
            barrel_tip  = self._rotate_pt((24, 0), angle, pos)
            barrel_base = self._rotate_pt((16, 0), angle, pos)
            pygame.draw.line(self.surface, (130, 130, 160), barrel_base, barrel_tip, 2)
            pygame.draw.line(self.surface, (100, 230, 130), barrel_base, barrel_tip, 1)
            # Muzzle dot
            pygame.draw.circle(self.surface, (60, 180, 90), barrel_tip, 1)
        elif hasattr(ship, "gun") and ship.gun.is_jammed:
            jam_pulse = 0.5 + 0.5 * abs(math.sin(t * 8))
            jam_col   = (int(200 * jam_pulse), 0, 0)
            barrel_tip  = self._rotate_pt((24, 0), angle, pos)
            barrel_base = self._rotate_pt((16, 0), angle, pos)
            pygame.draw.line(self.surface, jam_col, barrel_base, barrel_tip, 2)

    def _draw_exhaust(self, ship, t: float):
        keys      = pygame.key.get_pressed()
        thrusting = keys[pygame.K_UP] or keys[pygame.K_w]
        reversing = keys[pygame.K_DOWN] or keys[pygame.K_s]
        if not thrusting and not reversing:
            return
        pos    = ship.pos
        angle  = ship.angle
        hp_pct = ship.hull_pct
        flick  = 1.0 + math.sin(t * 53.7) * 0.13

        if thrusting:
            hue     = 0.58 + (1.0 - hp_pct) * 0.26
            c_outer = _hsv(hue, 0.75, 0.32 * flick)
            c_mid   = _hsv(hue, 0.92, 0.72 * flick)
            c_core  = _hsv(hue - 0.04, 0.25, 1.0)
            # Wavering plume — slight perpendicular jitter
            jitter = math.sin(t * 22.0) * 1.5
            outer = [self._rotate_pt(p, angle, pos) for p in
                     ((-14,-9),(-58, jitter),(-14,11))]
            mid   = [self._rotate_pt(p, angle, pos) for p in
                     ((-14,-5),(-38, jitter * 0.6),(-14,7))]
            core  = [self._rotate_pt(p, angle, pos) for p in
                     ((-14,-2),(-26, jitter * 0.3),(-14,4))]

            # Soft glow under plume
            glow_surf = pygame.Surface((120, 80), pygame.SRCALPHA)
            gp_col = _hsv(hue, 0.8, 0.9)
            pygame.draw.circle(glow_surf, (*gp_col, 35), (60, 40), 36)
            pygame.draw.circle(glow_surf, (*gp_col, 50), (60, 40), 22)
            cx_glow = self._rotate_pt((-30, 0), angle, pos)
            self.surface.blit(glow_surf, (cx_glow[0] - 60, cx_glow[1] - 40))

            pygame.draw.polygon(self.surface, c_outer, outer)
            pygame.draw.polygon(self.surface, c_mid,   mid)
            pygame.draw.polygon(self.surface, c_core,  core)

            # White hot inner flame
            inner_core = [self._rotate_pt(p, angle, pos) for p in
                          ((-14,-1),(-18,0),(-14,2))]
            pygame.draw.polygon(self.surface, (240, 250, 255), inner_core)

            # Spawn embers — small chance each frame to add particles
            if random.random() < 0.45:
                # Particle exits the nozzle in the opposite direction of facing
                rad = math.radians(angle + 180)
                spawn = self._rotate_pt((-18, random.uniform(-3, 3)), angle, pos)
                base_speed = random.uniform(140, 240)
                spread = math.radians(random.uniform(-15, 15))
                # Inherit ship velocity for natural look
                ship_vx = ship.body.vel.x if hasattr(ship, "body") else 0
                ship_vy = ship.body.vel.y if hasattr(ship, "body") else 0
                evx = math.cos(rad + spread) * base_speed + ship_vx * 0.5
                evy = math.sin(rad + spread) * base_speed + ship_vy * 0.5
                ember_hue = (hue + random.uniform(-0.05, 0.05)) % 1.0
                self._spawn_ember(spawn[0], spawn[1], evx, evy, ember_hue)

        if reversing:
            retro = [self._rotate_pt(p, angle, pos) for p in ((18,-2),(30, math.sin(t*20)*0.8),(18,2))]
            pygame.draw.polygon(self.surface, (200, 80, 20), retro)
            # Forward glow
            fwd_glow = self._rotate_pt((28, 0), angle, pos)
            pygame.draw.circle(self.surface, (255, 140, 40), fwd_glow, 3)

    # ------------------------------------------------------------------  BARGES
    def _draw_barges(self, run_mgr, ship, t: float = 0.0):
        for barge in run_mgr.barges:
            self._draw_barge(barge, ship, t)

    def _draw_barge(self, barge, ship, t: float = 0.0):
        pos    = barge.pos
        ticks  = pygame.time.get_ticks()
        bx, by = int(pos.x), int(pos.y)
        state  = barge.state

        # Aggressive halo when in chase/clamp/torch
        if state in ("chase", "clamp", "torch"):
            halo_pulse = 0.6 + 0.4 * math.sin(t * 6.0)
            halo_col = (220, 60, 30) if state in ("clamp", "torch") else (220, 130, 0)
            halo = pygame.Surface((100, 70), pygame.SRCALPHA)
            pygame.draw.ellipse(halo, (*halo_col, int(35 * halo_pulse)), (0, 0, 100, 70))
            pygame.draw.ellipse(halo, (*halo_col, int(60 * halo_pulse)), (8, 5, 84, 60))
            self.surface.blit(halo, (bx - 50, by - 35))

        # Hull body — filled dark with amber outline
        rect = pygame.Rect(bx-30, by-16, 60, 32)
        pygame.draw.rect(self.surface, (16, 10, 0), rect)
        pygame.draw.rect(self.surface, (55, 35, 0), rect, 4)
        pygame.draw.rect(self.surface, S.AMBER_TERM, rect, 2)

        # Hazard stripes — angled diagonal warning bars on top
        for stripe_x in range(bx - 26, bx + 26, 6):
            pygame.draw.line(self.surface, (80, 50, 0),
                             (stripe_x, by - 14), (stripe_x + 4, by - 10), 2)

        # Cargo hold dividers
        for dx in (-14, 0, 14):
            pygame.draw.line(self.surface, (45, 28, 0), (bx+dx, by-14), (bx+dx, by+14), 1)
        pygame.draw.line(self.surface, (70, 44, 0), (bx-22, by), (bx+22, by), 1)

        # Top-mounted harpoon turret
        turret_y = by - 22
        pygame.draw.rect(self.surface, (50, 30, 0), (bx - 5, turret_y, 10, 8))
        pygame.draw.rect(self.surface, S.AMBER_TERM, (bx - 5, turret_y, 10, 8), 1)
        # Turret barrel — aimed at ship if in chase
        if state in ("chase", "clamp", "torch") and ship is not None:
            aim_dx = ship.pos.x - bx
            aim_dy = ship.pos.y - by
            aim_len = math.hypot(aim_dx, aim_dy) or 1
            barrel_end = (int(bx + aim_dx / aim_len * 14),
                          int(turret_y - 2 + aim_dy / aim_len * 6))
            pygame.draw.line(self.surface, (200, 150, 50),
                             (bx, turret_y), barrel_end, 2)

        # Engine pods (rear) — bigger, brighter when in chase
        engine_pulse_speed = 8.0 if state in ("chase", "clamp", "torch") else 4.1
        engine_pulse = 0.55 + 0.45 * abs(math.sin(t * engine_pulse_speed))
        pod_col  = _hsv(0.09, 0.9, engine_pulse)
        pod_glow = _hsv(0.09, 0.6, engine_pulse * 0.25)
        for py_off in (-10, 10):
            pcx, pcy = bx - 32, by + py_off
            pygame.draw.circle(self.surface, pod_glow, (pcx, pcy), 9)
            pygame.draw.circle(self.surface, pod_col,  (pcx, pcy), 5)
            pygame.draw.circle(self.surface, (255, 240, 200), (pcx, pcy), 2)
            # Exhaust trail
            if state in ("chase", "clamp", "torch"):
                pygame.draw.line(self.surface, pod_col,
                                 (pcx, pcy), (pcx - 18, pcy), 2)
                pygame.draw.line(self.surface, (255, 200, 100),
                                 (pcx, pcy), (pcx - 10, pcy), 1)

        # Plasma torch arcs when actively cutting hull
        if state == BargeState.TORCH and ship is not None:
            sx_t = int(ship.pos.x)
            sy_t = int(ship.pos.y)
            torch_pulse = 0.5 + 0.5 * abs(math.sin(t * 14.0))
            for arc_i in range(3):
                ang_off = t * 7.0 + arc_i * math.tau / 3
                arc_len = int(22 + 12 * math.sin(t * 5.0 + arc_i))
                ax = int(bx + math.cos(ang_off) * arc_len)
                ay = int(by + math.sin(ang_off) * arc_len)
                arc_col = (int(255 * torch_pulse), int(120 * torch_pulse), 0)
                pygame.draw.line(self.surface, arc_col, (bx, by), (ax, ay), 2)
                pygame.draw.circle(self.surface, (255, 200, 50), (ax, ay), 2)

        # Forward sensor dome — eye-like, glows red when hunting
        dome_col_outer = (60, 14, 14) if state in ("chase", "clamp", "torch") else (30, 30, 50)
        dome_col_iris  = (220, 50, 30) if state in ("chase", "clamp", "torch") else (80, 80, 120)
        dome_col_pupil = (255, 230, 230) if state in ("chase", "clamp", "torch") else (150, 150, 200)
        pygame.draw.circle(self.surface, dome_col_outer, (bx+32, by), 7)
        pygame.draw.circle(self.surface, dome_col_iris,  (bx+32, by), 4, 1)
        pygame.draw.circle(self.surface, dome_col_pupil, (bx+32, by), 2)

        # Side running lights (always on, slow blink)
        run_blink = (ticks // 800) % 2 == 0
        side_col = (200, 0, 0) if run_blink else (60, 0, 0)
        pygame.draw.circle(self.surface, side_col, (bx - 28, by - 16), 1)
        pygame.draw.circle(self.surface, side_col, (bx + 28, by - 16), 1)

        # Hazard lights — corner amber pulse
        blink = (ticks // 380) % 2 == 0
        for (lx, ly), on in (((bx-24, by-11), blink), ((bx+24, by+11), not blink)):
            if on:
                pygame.draw.circle(self.surface, (100, 62, 0), (lx, ly), 7)
                pygame.draw.circle(self.surface, S.AMBER_TERM,  (lx, ly), 4)
            else:
                pygame.draw.circle(self.surface, (50, 32, 0), (lx, ly), 4)

        # Local 404 badge
        badge_rect = pygame.Rect(bx - 8, by - 4, 16, 8)
        pygame.draw.rect(self.surface, (8, 4, 0), badge_rect)
        pygame.draw.rect(self.surface, (140, 90, 0), badge_rect, 1)
        font = pygame.font.SysFont("monospace", 7)
        surface_404 = font.render("404", True, (200, 140, 0))
        self.surface.blit(surface_404, (bx - surface_404.get_width() // 2,
                                        by - surface_404.get_height() // 2))

        # Tether — double-layered crackling EM beam
        tether = getattr(barge, "_tether", None)
        if tether and tether.is_active and ship and ship.is_alive:
            sx, sy  = int(ship.pos.x), int(ship.pos.y)
            dist    = math.hypot(sx - bx, sy - by)
            stretch = min(1.0, dist / S.TETHER_MAX_LENGTH)
            # Color shifts orange → red as stretch increases
            tr = int(40  + 215 * stretch)
            tg = int(180 - 150 * stretch)
            jitter_max = int((1 - abs(0.5 - 0.5) * 2) * 10 * (0.4 + stretch))

            # Glow pass (thick, dim)
            glow_pts = [(bx, by)]
            for k in range(1, 9):
                frac = k / 9
                mx = int(bx + (sx - bx) * frac)
                my = int(by + (sy - by) * frac)
                jit = int((1 - abs(frac - 0.5) * 2) * 8 * (0.4 + stretch))
                glow_pts.append((mx + random.randint(-jit, jit),
                                 my + random.randint(-jit, jit)))
            glow_pts.append((sx, sy))
            glow_col = (min(255, tr // 2), max(0, tg // 3), 0)
            if len(glow_pts) >= 2:
                pygame.draw.lines(self.surface, glow_col, False, glow_pts, 5)

            # Core pass (thin, bright, fresh jitter)
            core_pts = [(bx, by)]
            for k in range(1, 9):
                frac = k / 9
                mx = int(bx + (sx - bx) * frac)
                my = int(by + (sy - by) * frac)
                jit = int((1 - abs(frac - 0.5) * 2) * 5 * stretch)
                core_pts.append((mx + random.randint(-jit, jit),
                                 my + random.randint(-jit, jit)))
            core_pts.append((sx, sy))
            core_col = (min(255, tr), max(0, tg), 60)
            if len(core_pts) >= 2:
                pygame.draw.lines(self.surface, core_col, False, core_pts, 2)

            # Crackle spark nodes
            for k in range(1, 4):
                frac = k / 4
                nx = int(bx + (sx - bx) * frac + random.randint(-4, 4))
                ny = int(by + (sy - by) * frac + random.randint(-4, 4))
                pygame.draw.circle(self.surface, (255, min(255, tg + 80), 80), (nx, ny), 2)

    # ------------------------------------------------------------------  EXPLOSIONS
    def _spawn_explosion(self, cx: float, cy: float, n: int, intensity: float):
        """Burst of n particles from (cx, cy).  intensity scales lifetime+size."""
        import math as _math
        for _ in range(n):
            ang  = random.uniform(0.0, _math.tau)
            spd  = random.uniform(18.0, 140.0) * intensity
            life = random.uniform(0.35, 0.9) * intensity
            hue  = random.uniform(0.02, 0.14)  # orange/yellow/red range
            size = random.uniform(1.5, 4.5) * intensity
            self._explosions.append([
                cx, cy,
                _math.cos(ang) * spd, _math.sin(ang) * spd,
                0.0, life, hue, size
            ])

    def _update_explosions(self, dt: float):
        for p in self._explosions:
            p[0] += p[2] * dt   # x
            p[1] += p[3] * dt   # y
            p[4] += dt           # age
            p[3] += 12.0 * dt   # slight gravity pull downward
            p[2] *= 0.92         # drag
        self._explosions = [p for p in self._explosions if p[4] < p[5]]

    def _draw_explosions(self):
        for x, y, _, __, age, life, hue, size in self._explosions:
            if not (0 <= int(x) < S.SCREEN_W and 0 <= int(y) < S.FLIGHT_H + S.COCKPIT_H):
                continue
            frac = 1.0 - age / life          # 1→0 as it dies
            # Shift hue orange→yellow→white as it cools
            draw_hue = (hue + (1 - frac) * 0.06) % 1.0
            bright   = max(0.0, frac)
            sat      = max(0.0, frac * 0.8)
            col = _hsv(draw_hue, sat, bright)
            r = max(1, int(size * frac))
            pygame.draw.circle(self.surface, col, (int(x), int(y)), r)
            # Glow halo on fresh particles
            if frac > 0.6:
                glow_col = _hsv(draw_hue, sat * 0.4, bright * 0.4)
                pygame.draw.circle(self.surface, glow_col, (int(x), int(y)), r + 2)

    # ------------------------------------------------------------------  EFFECTS
    def _draw_proximity_alarm(self, run_mgr, ship, t: float):
        if not ship.is_alive or not run_mgr.barges:
            return
        min_dist = min((barge.pos - ship.pos).length() for barge in run_mgr.barges)
        if min_dist > 340:
            return
        intensity = (1.0 - min_dist / 340.0) * abs(math.sin(t * 5.5))
        if intensity < 0.04:
            return
        r   = min(255, int(intensity * 240))
        col = (r, 0, 0)
        ew  = max(1, int(intensity * 42))
        fh  = S.FLIGHT_H
        pygame.draw.rect(self.surface, col, pygame.Rect(0,               0,       S.SCREEN_W, ew))
        pygame.draw.rect(self.surface, col, pygame.Rect(0,               fh - ew, S.SCREEN_W, ew))
        pygame.draw.rect(self.surface, col, pygame.Rect(0,               0,       ew,         fh))
        pygame.draw.rect(self.surface, col, pygame.Rect(S.SCREEN_W - ew, 0,       ew,         fh))

    def _draw_flash(self, dt: float):
        if self._flash_t <= 0:
            return
        alpha   = min(210, int(self._flash_t * 520))
        overlay = pygame.Surface((S.SCREEN_W, S.FLIGHT_H), pygame.SRCALPHA)
        overlay.fill((*self._flash_col, alpha))
        self.surface.blit(overlay, (0, 0))
        self._flash_t -= dt

    # ------------------------------------------------------------------
    def _draw_spore_effect(self, ship, t: float):
        """Psychedelic panic overlay when EpistemologicalShrooms inverts controls."""
        cargo = getattr(ship, "cargo", None)
        if cargo is None or not hasattr(cargo, "inversion_active"):
            return

        spore_level = getattr(cargo, "spore_level", 0.0)
        W, H = S.SCREEN_W, S.FLIGHT_H

        # Ambient pre-warning: spore meter pulses on screen edge when cargo is agitated
        if spore_level > 0.0 and not cargo.inversion_active:
            pulse = 0.4 + 0.6 * abs(math.sin(t * (2.0 + spore_level * 4.0)))
            edge_a = int(spore_level * 60 * pulse)
            if edge_a > 0:
                vignette = pygame.Surface((W, H), pygame.SRCALPHA)
                for i in range(4):
                    a = max(0, edge_a - i * 14)
                    pygame.draw.rect(vignette, (140, 0, 200, a),
                                     pygame.Rect(i*4, i*4, W - i*8, H - i*8), 8)
                self.surface.blit(vignette, (0, 0))
            # Tiny spore level readout bottom-left
            font_xs = pygame.font.SysFont("monospace", 13)
            bars = int(spore_level * 8)
            spore_txt = font_xs.render(
                f"SPORE {'|' * bars}{'.' * (8 - bars)}", True, (160, 0, 220))
            self.surface.blit(spore_txt, (8, H - 22))
            return

        if not cargo.inversion_active:
            return

        pct = cargo.invert_pct          # 1.0→0.0 as inversion wears off
        pulse = abs(math.sin(t * 7.0))

        # Chromatic split: R left, B right, G centre — gives cheap aberration feel
        shift = int(3 + spore_level * 5)
        for dx, col in [(-shift, (200, 0, 0, 20)), (shift, (0, 0, 200, 20))]:
            layer = pygame.Surface((W, H), pygame.SRCALPHA)
            layer.fill(col)
            self.surface.blit(layer, (dx, 0))

        # Full-screen magenta/purple breathing overlay
        base_a = int(35 + 45 * pulse)
        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        r = int(120 + 80 * pulse)
        overlay.fill((r, 0, 255, base_a))
        self.surface.blit(overlay, (0, 0))

        # Pulsing purple vignette border
        vignette = pygame.Surface((W, H), pygame.SRCALPHA)
        border_a = int(100 + 80 * pulse)
        for i in range(5):
            a = max(0, border_a - i * 18)
            pygame.draw.rect(vignette, (180, 0, 255, a),
                             pygame.Rect(i*5, i*5, W - i*10, H - i*10), 10)
        self.surface.blit(vignette, (0, 0))

        # Main warning — alternates cyan/magenta, large and bold
        font_big = pygame.font.SysFont("monospace", 30, bold=True)
        font_sm  = pygame.font.SysFont("monospace", 15)
        col_a = (0, 255, 255) if int(t * 5) % 2 == 0 else (255, 0, 255)
        col_b = (255, 0, 255) if int(t * 5) % 2 == 0 else (0, 255, 255)

        warn = font_big.render("!! CONTROLS INVERTED !!", True, col_a)
        self.surface.blit(warn, (W // 2 - warn.get_width() // 2, H // 2 - 54))

        # Spore level bar
        bars   = int(spore_level * 10)
        spore_line = font_sm.render(
            f"SPORE LEVEL  {'|' * bars}{'.' * (10 - bars)}  {'HOT' if spore_level > 0.6 else 'ACTIVE'}",
            True, col_b)
        self.surface.blit(spore_line, (W // 2 - spore_line.get_width() // 2, H // 2 - 16))

        # Countdown
        secs_left = pct * S.SPORE_DURATION
        timer = font_sm.render(f"NORMALIZING IN  {secs_left:.1f}s", True, col_a)
        self.surface.blit(timer, (W // 2 - timer.get_width() // 2, H // 2 + 10))

    @staticmethod
    def _rotate_pt(pt: tuple, angle_deg: float, origin) -> tuple:
        rad = math.radians(angle_deg)
        cos_a, sin_a = math.cos(rad), math.sin(rad)
        x, y = pt
        return (int(x * cos_a - y * sin_a + origin.x),
                int(x * sin_a + y * cos_a + origin.y))
