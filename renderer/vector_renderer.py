from __future__ import annotations
import math
import random
import pygame
from config import settings as S
from antagonists.repo_barge import BargeState
from antagonists.alien_ship import HULL_PTS as _ALIEN_HULL, INNER_PTS as _ALIEN_INNER
from renderer.visual_fx import VisualFX
from renderer.chromatic_corruption import ChromaticCorruption
from core.event_bus import (bus, EVT_SLINGSHOT, EVT_SCAN_PING,
                             EVT_TETHER_HIT, EVT_TETHER_SNAP,
                             EVT_MODULE_UNBOLTED, EVT_HULL_DAMAGE,
                             EVT_HULL_CRITICAL, EVT_WARP_JUMP, EVT_SECTOR_CLEAR,
                             EVT_SECTOR_START)


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
    _STAR_COUNT = 320

    def __init__(self, surface: pygame.Surface):
        self.surface     = surface
        self._vfx        = VisualFX()
        self._corruption = ChromaticCorruption(S.SCREEN_W, S.FLIGHT_H)
        self._glitch_burst_t = 0.0   # >0 = trigger glitch tear on next frame
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

        # Slingshot floater — list of (x, y, t) where t counts down from 1.0
        self._sling_floaters: list[list[float]] = []

        # Ember particles trailing exhaust — (x, y, vx, vy, age, lifetime, hue)
        self._embers: list[list[float]] = []

        # Explosion/hit particle system — [x, y, vx, vy, age, lifetime, hue, size]
        self._explosions: list[list[float]] = []
        self._was_alive = True
        self._last_ship_x = 640.0
        self._last_ship_y = 320.0

        # Screen shake state: trauma decays exponentially; offset is random per frame
        self._shake_trauma = 0.0   # 0.0 (none) → 1.0 (huge)

        # Soft lead-camera offset — the flight area glides slightly with the
        # ship's velocity. World still wraps in absolute coords; only the
        # display blit is offset. See _apply_camera_glide().
        self._cam_offset = pygame.Vector2(0.0, 0.0)

        # Per-sector background palette shift + intensity ramp
        self._sector_hue_shift = 0.0
        self._sector_intensity = 0.0   # 0.0 sector 1 → 1.0 sector SECTORS_PER_RUN

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
        bus.subscribe(EVT_SECTOR_START,     self._on_sector_start)

        # Sector intro card state
        self._intro_card_t     = 0.0
        self._intro_card_data: dict | None = None

    def _on_slingshot(self, **_):
        self._flash_t   = 0.45
        self._flash_col = (160, 210, 255)
        # Spawn "+800cr  FREE −5s" floater near the ship
        self._sling_floaters.append([self._last_ship_x, self._last_ship_y, 1.2])

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
            self._glitch_burst_t = 0.18   # tear the screen for a moment on impact

    def _on_hull_critical(self, **_):
        self._shake_trauma = min(1.0, self._shake_trauma + 0.4)

    def _on_warp_jump(self, **_):
        self._warp_t    = 0.55
        self._flash_t   = 0.35
        self._flash_col = (200, 220, 255)

    def _on_sector_clear(self, sector_num=0, **_):
        self._sector_hue_shift = (sector_num * 0.11) % 1.0
        # Intensity ramps with sector — escalates background density + brightness
        self._sector_intensity = min(1.0, sector_num / max(1, S.SECTORS_PER_RUN - 1))

    def _on_sector_start(self, sector_num=0, cargo_type=None,
                         theme="", sector_name="", formerly="", **_):
        self._intro_card_t    = 2.0
        self._intro_card_data = {
            "sector_num":  sector_num,
            "theme":       theme,
            "name":        sector_name,
            "formerly":    formerly,
        }

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
        self._draw_stars(t, ship)
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
        self._draw_sector_intro_card(dt)
        self._draw_sling_floaters(dt)
        self._draw_spore_effect(ship, t)
        self._draw_cargo_overlays(ship, t)
        self._draw_warp_streak(dt)
        self._apply_camera_glide(ship, dt)
        self._apply_screen_shake(dt)
        self._vfx.apply_flight_grade(
            self.surface, dt,
            hull_pct=ship.hull_pct if ship else 1.0,
            sector_intensity=self._sector_intensity,
        )

        # Layered chromatic corruption — only kicks in once hull is hurt.
        # iframe_active drives the cool blue shimmer (post-mercy-hit).
        hull_pct = ship.hull_pct if ship else 1.0
        burst = self._glitch_burst_t > 0
        if burst:
            self._glitch_burst_t = max(0.0, self._glitch_burst_t - dt)
        self._corruption.apply(
            self.surface, t, dt,
            intensity=max(0.0, (1.0 - hull_pct) - 0.18),
            iframe_active=bool(getattr(ship, "iframe_active", False)),
            glitch_burst=burst,
        )

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
        elif ctype == "SentientPaperwork":
            self._draw_form_popup(cargo, t)
        elif ctype == "SchrodingerVIP":
            self._draw_vip_effect(cargo, t)

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

        # ── Persistent audio waveform bar at top of screen ────────────────────
        wave_h = 20
        wave_surf = pygame.Surface((W, wave_h), pygame.SRCALPHA)
        # Background strip
        bg_a = int(60 + sl * 80)
        pygame.draw.rect(wave_surf, (4, 4, 8, bg_a), (0, 0, W, wave_h))
        pygame.draw.line(wave_surf, (80, 50, 20, 120), (0, wave_h - 1), (W, wave_h - 1), 1)
        # Waveform — sine + harmonics, distortion increases with sorrow
        wave_pts = []
        distort = sl * 3.8
        for wx in range(0, W, 2):
            phase = wx * 0.04 + t * 5.2
            base = math.sin(phase)
            # Add harmonics/noise as sorrow rises
            harm = (math.sin(phase * 2.3 + 1.1) * 0.45
                    + math.sin(phase * 5.7 + t * 2.1) * 0.2 * sl
                    + math.sin(phase * 11.3 + t * 3.7) * 0.15 * sl)
            noise = (random.random() - 0.5) * distort * 0.4
            amp = wave_h * 0.4 * (0.6 + 0.4 * sl)
            wy = int(wave_h / 2 + (base + harm + noise) * amp)
            wy = max(1, min(wave_h - 2, wy))
            wave_pts.append((wx, wy))
        if len(wave_pts) > 1:
            # Outer glow pass
            wave_col_glow = (int(200 * sl), int(60 * sl), int(20 * sl), int(sl * 120))
            pygame.draw.lines(wave_surf, wave_col_glow[:3], False, wave_pts, 3)
            # Core bright pass
            wave_col = (int(255 * sl), int(130 * sl), int(40 * sl), int(sl * 220))
            pygame.draw.lines(wave_surf, wave_col[:3], False, wave_pts, 1)
        self.surface.blit(wave_surf, (0, 0))

        # ── Ghost note symbols drifting upward (sl > 0.4) ─────────────────────
        if sl > 0.4:
            note_rng = random.Random(int(t * 0.5))   # slow seed = stable drift pattern
            n_notes = int((sl - 0.4) * 10)
            for ni in range(n_notes):
                note_x = note_rng.randint(40, W - 40)
                # Drift upward based on time + index
                note_y = int(((1.0 - ((t * 18 + ni * 57) % 120) / 120.0)) * (H - 40) + 20)
                note_a = int((sl - 0.4) / 0.6 * 150 * (1.0 - note_y / H))
                if note_a < 10:
                    continue
                # Draw a small musical note as lines
                note_col = (int(220 * sl), int(100 * sl), int(30 * sl))
                # Note head (small rectangle)
                pygame.draw.rect(self.surface, note_col, (note_x, note_y + 4, 5, 4))
                # Stem up
                pygame.draw.line(self.surface, note_col,
                                 (note_x + 4, note_y + 4), (note_x + 4, note_y - 4), 1)
                # Flag
                pygame.draw.line(self.surface, note_col,
                                 (note_x + 4, note_y - 4), (note_x + 8, note_y - 1), 1)

        # ── Sorrow meter HUD element — bolder ────────────────────────────────
        font_xs = pygame.font.SysFont("monospace", 13, bold=True)
        bars  = int(sl * 8)
        col_r = int(160 + sl * 95)
        col_g = int(80 * (1.0 - sl * 0.5))
        label = font_xs.render(
            f"SIGNAL  {'|' * bars}{'·' * (8 - bars)}",
            True, (col_r, col_g, int(30 * sl)))
        self.surface.blit(label, (8, H - 22))

    def _draw_form_popup(self, cargo, t: float):
        if not cargo.popup_active:
            return
        W, H  = S.SCREEN_W, S.FLIGHT_H
        frac  = cargo.popup_fraction   # 1.0→0.0 countdown
        pulse = 0.6 + 0.4 * abs(math.sin(t * 6.0))
        urgent = frac < 0.35

        # ── Floating form fragments behind main popup ─────────────────────────
        frag_rng = random.Random(42)
        n_frags = 5
        for fi in range(n_frags):
            # Each fragment has a fixed seed position + slow upward drift
            fbase_x = frag_rng.randint(80, W - 120)
            fbase_y = frag_rng.randint(H // 5, H * 3 // 4)
            # Drift upward slowly, cycling with time
            drift_speed = 12 + fi * 4
            fy = fbase_y - int((t * drift_speed + fi * 80) % (H - 40))
            fw, fh = frag_rng.randint(60, 100), frag_rng.randint(40, 65)
            # Skip if would overlap main popup area
            popup_bx = (W - 460) // 2
            popup_by = H // 4 - 60
            if (popup_bx - fw < fbase_x < popup_bx + 460 + fw and
                    popup_by - fh < fy < popup_by + 140):
                continue
            # Fade by height (fragments higher up are more faded)
            fade = max(20, int(120 * (1.0 - fy / H)))
            frag_surf = pygame.Surface((fw, fh), pygame.SRCALPHA)
            pygame.draw.rect(frag_surf, (28, 24, 10, min(fade, 90)), (0, 0, fw, fh))
            pygame.draw.rect(frag_surf, (90, 82, 38, fade), (0, 0, fw, fh), 1)
            # Simulated form fields as grey horizontal lines
            for line_i in range(0, fh - 6, 8):
                line_w = int(fw * (0.4 + 0.5 * frag_rng.random()))
                line_col_a = max(10, fade - 30)
                pygame.draw.line(frag_surf, (75, 70, 40, line_col_a),
                                 (5, line_i + 5), (5 + line_w, line_i + 5), 1)
                # Occasional label stub
                if frag_rng.random() < 0.4:
                    pygame.draw.rect(frag_surf, (50, 46, 22, line_col_a),
                                     (5, line_i + 6, int(fw * 0.25), 3))
            self.surface.blit(frag_surf, (fbase_x, fy))

        # ── Screen-shake border flash when urgent ─────────────────────────────
        if urgent:
            shake_a = int(60 * pulse)
            edge = pygame.Surface((W, H), pygame.SRCALPHA)
            edge.fill((0, 0, 0, 0))
            for thickness in (6, 3):
                r_col = (int(220 * pulse), 0, 0, shake_a)
                pygame.draw.rect(edge, r_col, (0, 0, W, H), thickness)
            self.surface.blit(edge, (0, 0))

        # ── Main popup box ────────────────────────────────────────────────────
        bw, bh = 580, 160
        bx     = (W - bw) // 2
        by     = H // 2 - bh // 2   # centred on screen for maximum interruption

        border_col = (230, 30, 30) if urgent else (200, 160, 0)
        bg_col     = (18, 4, 0) if urgent else (8, 14, 4)

        # Dark semi-transparent overlay behind box to block gameplay
        ov = pygame.Surface((W, H), pygame.SRCALPHA)
        ov.fill((0, 0, 0, int(130 * pulse) if urgent else 80))
        self.surface.blit(ov, (0, 0))

        pygame.draw.rect(self.surface, bg_col,    (bx, by, bw, bh))
        pygame.draw.rect(self.surface, border_col, (bx, by, bw, bh), 3)
        # Double-border for urgency
        if urgent:
            pulse_col = (int(255 * pulse), int(50 * pulse), 0)
            pygame.draw.rect(self.surface, pulse_col, (bx - 3, by - 3, bw + 6, bh + 6), 2)
            pygame.draw.rect(self.surface, pulse_col, (bx - 6, by - 6, bw + 12, bh + 12), 1)

        font_xl = pygame.font.SysFont("monospace", 20, bold=True)
        font_lg = pygame.font.SysFont("monospace", 16, bold=True)
        font_sm = pygame.font.SysFont("monospace", 12)

        # Header stripe
        hdr_col = (180, 30, 30) if urgent else (140, 110, 0)
        pygame.draw.rect(self.surface, hdr_col, (bx, by, bw, 28))

        title_txt = "⚠ UNION FORM 27-B — IMMEDIATE COMPLIANCE REQUIRED ⚠" if urgent \
                    else "UNION FORM 27-B — ADMINISTRATIVE INTERRUPT"
        title = font_lg.render(title_txt, True, (255, 200, 200) if urgent else (255, 220, 80))
        self.surface.blit(title, (bx + bw // 2 - title.get_width() // 2, by + 6))

        key_col = (255, 80, 80) if urgent else (0, 255, 120)
        key_s   = font_xl.render(f"PRESS  [ {cargo.popup_key_name} ]  NOW", True, key_col)
        self.surface.blit(key_s, (bx + bw // 2 - key_s.get_width() // 2, by + 42))

        # Countdown bar
        bar_w  = bw - 32
        filled = int(bar_w * frac)
        bar_col = (200, 30, 30) if urgent else (180, 140, 0)
        pygame.draw.rect(self.surface, (25, 10, 4), (bx + 16, by + 96, bar_w, 16))
        pygame.draw.rect(self.surface, bar_col,     (bx + 16, by + 96, filled, 16))
        pygame.draw.rect(self.surface, border_col,  (bx + 16, by + 96, bar_w, 16), 1)

        secs = cargo.popup_timer
        timer_s = font_lg.render(f"{secs:.1f}s", True,
                                  (255, 60, 60) if urgent else (180, 140, 60))
        self.surface.blit(timer_s, (bx + bw - timer_s.get_width() - 16, by + 126))

        sub = font_sm.render(
            "NON-COMPLIANCE: hull integrity penalty  |  Subsection 9, Union Charter  |  NON-NEGOTIABLE",
            True, (140, 80, 80) if urgent else (90, 80, 50))
        self.surface.blit(sub, (bx + bw // 2 - sub.get_width() // 2, by + 132))

    def _draw_vip_effect(self, cargo, t: float):
        """SchrodingerVIP — visual state overlay: alive/deceased/unobserved."""
        W, H = S.SCREEN_W, S.FLIGHT_H
        # Determine state string from cargo
        status = cargo.state_for_terminal()   # "alive", "deceased", or "unobserved"

        font_sm  = pygame.font.SysFont("monospace", 12, bold=True)
        font_xs  = pygame.font.SysFont("monospace", 10)

        if status == "alive":
            # ── Gentle green heartbeat pulse on screen edges ─────────────────
            # Beat: two rapid pulses followed by a long pause — simulating cardiac
            beat_phase = t % 1.2
            if beat_phase < 0.12:
                intensity = math.sin(beat_phase / 0.12 * math.pi)
            elif beat_phase < 0.28:
                intensity = math.sin((beat_phase - 0.16) / 0.12 * math.pi) * 0.6
            else:
                intensity = 0.0
            if intensity > 0.01:
                edge_a = int(intensity * 90)
                vignette = pygame.Surface((W, H), pygame.SRCALPHA)
                for i in range(3):
                    a = max(0, edge_a - i * 25)
                    pygame.draw.rect(vignette, (0, 200, 80, a),
                                     pygame.Rect(i*5, i*5, W - i*10, H - i*10), 8)
                self.surface.blit(vignette, (0, 0))
            # VIP status label
            vip_lbl = font_sm.render("VIP STATUS: ALIVE", True, (0, 200, 80))
            self.surface.blit(vip_lbl, (W - vip_lbl.get_width() - 10, H - 44))

        elif status == "deceased":
            # ── Red vignette pulse + EKG flatline ────────────────────────────
            dead_pulse = 0.45 + 0.25 * math.sin(t * 1.1)
            edge_a = int(dead_pulse * 80)
            vignette = pygame.Surface((W, H), pygame.SRCALPHA)
            for i in range(4):
                a = max(0, edge_a - i * 18)
                pygame.draw.rect(vignette, (200, 0, 0, a),
                                 pygame.Rect(i*5, i*5, W - i*10, H - i*10), 8)
            self.surface.blit(vignette, (0, 0))
            # EKG flatline at top centre
            ekl = W // 3
            eky = 22
            ekx = W // 2 - ekl // 2
            pygame.draw.line(self.surface, (200, 30, 30), (ekx, eky), (ekx + ekl, eky), 2)
            # Single blip (static dead spike at 1/3 of line)
            blip_x = ekx + ekl // 3
            pygame.draw.line(self.surface, (220, 50, 50),
                             (blip_x, eky), (blip_x + 2, eky - 6), 1)
            pygame.draw.line(self.surface, (220, 50, 50),
                             (blip_x + 2, eky - 6), (blip_x + 4, eky + 6), 1)
            pygame.draw.line(self.surface, (220, 50, 50),
                             (blip_x + 4, eky + 6), (blip_x + 6, eky), 1)
            # VIP status label
            vip_lbl = font_sm.render("VIP STATUS: DECEASED", True, (200, 30, 30))
            self.surface.blit(vip_lbl, (W - vip_lbl.get_width() - 10, H - 44))

        else:
            # ── Unobserved / superposition: overlapping ghost glow + ? symbols
            # Green edge glow + red edge glow simultaneously at half alpha
            sup_pulse = 0.4 + 0.3 * math.sin(t * 2.4)
            ea = int(sup_pulse * 50)
            sup_surf = pygame.Surface((W, H), pygame.SRCALPHA)
            for i in range(3):
                a = max(0, ea - i * 14)
                pygame.draw.rect(sup_surf, (0, 180, 70, a),
                                 pygame.Rect(i*5, i*5, W - i*10, H - i*10), 7)
                pygame.draw.rect(sup_surf, (180, 0, 0, a),
                                 pygame.Rect(i*6+2, i*6+2, W - i*12-4, H - i*12-4), 5)
            self.surface.blit(sup_surf, (0, 0))
            # Floating ? symbols that slowly rotate/drift
            q_font = pygame.font.SysFont("monospace", 18, bold=True)
            q_positions = [(W // 4, H // 3), (3 * W // 4, H // 4),
                           (W // 2, H * 2 // 3), (W // 5, H * 2 // 3)]
            for qi, (qx, qy) in enumerate(q_positions):
                rot_off = math.sin(t * 0.8 + qi * 1.57) * 10
                q_x = int(qx + rot_off)
                q_y = int(qy + math.cos(t * 0.6 + qi * 2.1) * 8)
                q_a = int(80 + 60 * math.sin(t * 1.2 + qi * 0.9))
                q_surf = pygame.Surface((22, 22), pygame.SRCALPHA)
                q_lbl = q_font.render("?", True, (200, 200, 50))
                q_surf.blit(q_lbl, (0, 0))
                q_surf.set_alpha(q_a)
                self.surface.blit(q_surf, (q_x - 11, q_y - 11))
            # VIP status label
            vip_lbl = font_sm.render("VIP STATUS: ???", True, (200, 180, 40))
            sub_lbl = font_xs.render("[UNOBSERVED]", True, (140, 120, 28))
            self.surface.blit(vip_lbl, (W - vip_lbl.get_width() - 10, H - 44))
            self.surface.blit(sub_lbl, (W - sub_lbl.get_width() - 10, H - 30))

    def _apply_camera_glide(self, ship, dt: float):
        """
        Tile-blit the flight area with an offset that follows the ship's
        velocity. Wraps via 4-quadrant blit so no black gap appears.
        Only affects the flight area (y < FLIGHT_H); cockpit is untouched.
        """
        if ship is None or not ship.is_alive:
            target_x = target_y = 0.0
        else:
            vx, vy = ship.body.vel.x, ship.body.vel.y
            target_x = max(-S.CAMERA_GLIDE_MAX,
                           min(S.CAMERA_GLIDE_MAX, vx * S.CAMERA_GLIDE_GAIN))
            target_y = max(-S.CAMERA_GLIDE_MAX,
                           min(S.CAMERA_GLIDE_MAX, vy * S.CAMERA_GLIDE_GAIN))
        step = min(1.0, S.CAMERA_GLIDE_RATE * dt)
        self._cam_offset.x += (target_x - self._cam_offset.x) * step
        self._cam_offset.y += (target_y - self._cam_offset.y) * step

        ox = int(round(-self._cam_offset.x))
        oy = int(round(-self._cam_offset.y))
        if ox == 0 and oy == 0:
            return

        W, H = S.SCREEN_W, S.FLIGHT_H
        snapshot = self.surface.subsurface(pygame.Rect(0, 0, W, H)).copy()
        self.surface.fill(S.BLACK, pygame.Rect(0, 0, W, H))
        # Tile in the four quadrants so the wrap-gap is filled regardless
        # of offset sign.
        dx_alt = W if ox < 0 else -W
        dy_alt = H if oy < 0 else -H
        for dx in (0, dx_alt):
            for dy in (0, dy_alt):
                self.surface.blit(snapshot, (ox + dx, oy + dy))

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
        self._draw_stars(t, None)
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
        # Nebulae get more saturated and brighter as the run progresses
        intensity_boost = 1.0 + self._sector_intensity * 0.55
        val_boost = 0.14 + self._sector_intensity * 0.10
        for x, y, r, base_hue, sat in self._nebulae:
            hue = (base_hue + self._sector_hue_shift + t * 0.0035) % 1.0
            col = _hsv(hue, sat * 0.60 * intensity_boost, val_boost)
            for scale, alpha_base in ((1.0, 20), (0.68, 32), (0.40, 44)):
                alpha = int(alpha_base * (1.0 + self._sector_intensity * 0.5))
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
        # Late-game sectors render more dust particles (every-other → every) and brighter
        skip = 1 if self._sector_intensity > 0.5 else 2
        bright_boost = 1.0 + self._sector_intensity * 0.6
        for i, (ox, oy, hue, freq, phase, rad) in enumerate(self._dust):
            if i % skip != 0:
                continue
            x = int((ox + math.cos(t * freq + phase) * rad) % S.SCREEN_W)
            y = int((oy + math.sin(t * freq * 0.7 + phase) * rad * 0.6) % S.SCREEN_H)
            brightness = (0.10 + 0.08 * abs(math.sin(t * freq * 1.3 + phase))) * bright_boost
            col = _hsv((hue + t * 0.015 + self._sector_hue_shift * 0.4) % 1.0,
                       0.65, min(0.95, brightness))
            surf.set_at((x, y), col)

    # ------------------------------------------------------------------  STARS
    def _gen_stars(self) -> list:
        rng = random.Random(self._STAR_SEED)
        stars = []
        for _ in range(self._STAR_COUNT):
            stars.append((
                rng.randint(0, S.SCREEN_W - 1),
                rng.randint(0, S.FLIGHT_H - 1),
                rng.random(),              # lum
                rng.random(),              # hue
                rng.uniform(0.6, 2.5),     # twinkle speed
                rng.random() * math.tau,   # twinkle phase
                rng.choice((0, 0, 0, 1, 1, 2)),  # depth layer (parallax)
            ))
        return stars

    def _draw_stars(self, t: float = 0.0, ship=None):
        surf = self.surface
        par_x = par_y = 0.0
        if ship is not None:
            par_x = -ship.pos.x * 0.018
            par_y = -ship.pos.y * 0.018
        for x, y, lum, hue, tw_speed, tw_phase, depth in self._stars:
            layer_scale = (0.35, 0.65, 1.0)[depth]
            sx = int((x + par_x * layer_scale)) % S.SCREEN_W
            sy = int((y + par_y * layer_scale)) % S.FLIGHT_H
            twinkle = 0.5 + 0.5 * math.sin(t * tw_speed + tw_phase)
            if lum < 0.48:
                v = int(lum * 55 * (0.7 + 0.3 * twinkle) * layer_scale)
                surf.set_at((sx, sy), (v, v, v + 12))
            elif lum < 0.80:
                v = int((50 + lum * 75) * (0.75 + 0.25 * twinkle) * layer_scale)
                surf.set_at((sx, sy), (v - 12, v - 12, v + 8))
            elif lum < 0.93:
                br = int(195 + 45 * twinkle)
                pygame.draw.circle(surf, (br - 10, br - 8, br),
                                   (sx, sy), 2 if twinkle > 0.85 else 1)
            else:
                shifted_hue = (hue + self._sector_hue_shift) % 1.0
                neon = _hsv(shifted_hue, 0.9, 1.0)
                r = 2 if twinkle > 0.7 else 1
                pygame.draw.circle(surf, neon, (sx, sy), r)
                if twinkle > 0.88:
                    pygame.draw.line(surf, neon, (sx - 5, sy), (sx + 5, sy), 1)
                    pygame.draw.line(surf, neon, (sx, sy - 5), (sx, sy + 5), 1)
                    glow = pygame.Surface((12, 12), pygame.SRCALPHA)
                    pygame.draw.circle(glow, (*neon, 60), (6, 6), 5)
                    surf.blit(glow, (sx - 6, sy - 6))

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

        # Soft core bloom
        bloom = pygame.Surface((r * 10, r * 10), pygame.SRCALPHA)
        for layer in range(5, 0, -1):
            br = int(r * (0.5 + layer * 0.35))
            hue = (drift + 0.35) % 1.0
            col = _hsv(hue, 0.6, 0.35)
            pygame.draw.circle(bloom, (*col, 12 + layer * 6), (r * 5, r * 5), br)
        self.surface.blit(bloom, (cx - r * 5, cy - r * 5))
        self._vfx.draw_pulsing_ring(self.surface, (cx, cy), int(r * 3.2), drift + 0.5, t)

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

        # Sector escalation: jagged distortion arcs around the event horizon
        # at high sectors — well looks angrier as the run progresses
        if self._sector_intensity > 0.25:
            n_arcs   = int(4 + self._sector_intensity * 8)
            arc_r    = core_r + 14 + int(self._sector_intensity * 8)
            arc_col  = _hsv((drift + 0.55) % 1.0,
                            0.85, 0.55 + 0.35 * self._sector_intensity)
            for i in range(n_arcs):
                base_ang = (i / n_arcs) * math.tau + t * 1.7
                # Random per-arc jitter scaled by intensity
                jitter   = math.sin(t * 8.0 + i * 0.7) * self._sector_intensity * 6
                r1 = arc_r + jitter
                r2 = arc_r + jitter + 3 + self._sector_intensity * 5
                x1 = cx + int(math.cos(base_ang) * r1)
                y1 = cy + int(math.sin(base_ang) * r1)
                x2 = cx + int(math.cos(base_ang) * r2)
                y2 = cy + int(math.sin(base_ang) * r2)
                pygame.draw.line(self.surface, arc_col, (x1, y1), (x2, y2), 1)

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
        # Mercy-window flicker — skip drawing on alternating fast frames so
        # the ship visibly strobes when invulnerable. Cheap and instantly readable.
        if getattr(ship, "iframe_active", False):
            if int(t * 18.0) % 2 == 0:
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

        # Aggressive halo when in chase/aim/clamp/torch
        if state in ("chase", "aim", "clamp", "torch"):
            halo_pulse = 0.6 + 0.4 * math.sin(t * 6.0)
            if state in ("clamp", "torch"):
                halo_col = (220, 60, 30)
            elif state == "aim":
                halo_col = (255, 220, 40)   # bright targeting yellow
            else:
                halo_col = (220, 130, 0)
            halo = pygame.Surface((100, 70), pygame.SRCALPHA)
            pygame.draw.ellipse(halo, (*halo_col, int(35 * halo_pulse)), (0, 0, 100, 70))
            pygame.draw.ellipse(halo, (*halo_col, int(60 * halo_pulse)), (8, 5, 84, 60))
            self.surface.blit(halo, (bx - 50, by - 35))

        # Hull body — filled dark with amber outline; white flash on bullet hit
        rect = pygame.Rect(bx-30, by-16, 60, 32)
        hit_flash = getattr(barge, 'hit_flash_t', 0.0)
        fill_col  = (180, 120, 40) if hit_flash > 0 else (16, 10, 0)
        rim_col   = (255, 255, 200) if hit_flash > 0 else S.AMBER_TERM
        pygame.draw.rect(self.surface, fill_col, rect)
        pygame.draw.rect(self.surface, (55, 35, 0), rect, 4)
        pygame.draw.rect(self.surface, rim_col, rect, 2)

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

        # Harpoon-arming warning — dashed targeting beam + reticle while in AIM
        if state == "aim" and ship and ship.is_alive:
            sx, sy = int(ship.pos.x), int(ship.pos.y)
            aim_t        = getattr(barge, "_aim_t", 0.0)
            aim_duration = getattr(barge, "AIM_DURATION", 1.6)
            progress     = max(0.0, min(1.0, 1.0 - aim_t / aim_duration))
            pulse        = 0.5 + 0.5 * math.sin(t * 28.0)
            # Yellow → red as the lock completes
            beam_r = 255
            beam_g = int(230 - 200 * progress)
            beam_b = 30
            # Dashed beam barge → ship
            dx, dy = sx - bx, sy - by
            L      = max(1.0, math.hypot(dx, dy))
            ux, uy = dx / L, dy / L
            dash_len = 14
            gap      = 8
            cur      = 0.0
            beam_col = (beam_r, beam_g, beam_b)
            while cur < L:
                seg_end = min(cur + dash_len, L)
                p1 = (int(bx + ux * cur), int(by + uy * cur))
                p2 = (int(bx + ux * seg_end), int(by + uy * seg_end))
                pygame.draw.line(self.surface, beam_col, p1, p2, 2)
                cur += dash_len + gap
            # Reticle on ship — pulsing crosshair circle
            ret_r = int(20 + 8 * pulse + 14 * progress)
            pygame.draw.circle(self.surface, beam_col, (sx, sy), ret_r, 2)
            pygame.draw.circle(self.surface, beam_col, (sx, sy), ret_r + 5, 1)
            tick = 6
            pygame.draw.line(self.surface, beam_col, (sx - ret_r - tick, sy), (sx - ret_r + 2, sy), 2)
            pygame.draw.line(self.surface, beam_col, (sx + ret_r - 2, sy), (sx + ret_r + tick, sy), 2)
            pygame.draw.line(self.surface, beam_col, (sx, sy - ret_r - tick), (sx, sy - ret_r + 2), 2)
            pygame.draw.line(self.surface, beam_col, (sx, sy + ret_r - 2), (sx, sy + ret_r + tick), 2)

        # Tether — double-layered crackling EM beam with snap-charge color
        tether = getattr(barge, "_tether", None)
        if tether and tether.is_active and ship and ship.is_alive:
            sx, sy  = int(ship.pos.x), int(ship.pos.y)
            dist    = math.hypot(sx - bx, sy - by)
            stretch = min(1.0, dist / S.TETHER_MAX_LENGTH)
            # Snap-charge: 0%=red  50%=amber  100%=bright green
            snap_pct = min(1.0, getattr(tether, "lateral_speed", 0.0) / S.SNAP_VELOCITY)
            if snap_pct < 0.5:
                # red → amber
                p2 = snap_pct * 2.0
                tr = int(200 + 55 * p2)
                tg = int(80  * p2)
            else:
                # amber → bright green
                p2 = (snap_pct - 0.5) * 2.0
                tr = int(255 - 255 * p2)
                tg = int(80  + 175 * p2)
            # At full snap-charge: pulse bright
            if snap_pct >= 0.95:
                tr, tg = 40, 255
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

    def _draw_sector_intro_card(self, dt: float):
        """2-second sector intro card in the top-left on sector load."""
        if self._intro_card_t <= 0 or self._intro_card_data is None:
            return
        self._intro_card_t -= dt
        from core.text import render_text
        from roguelite.procedural import THEME_DESCRIPTIONS
        d     = self._intro_card_data
        pct   = min(1.0, self._intro_card_t / 1.6)
        alpha = min(220, int(pct * 280))
        y     = 14

        def blit_line(text, size, color, bold=False):
            nonlocal y
            surf = render_text(text, size, color, bold=bold)
            surf.set_alpha(alpha)
            self.surface.blit(surf, (14, y))
            y += surf.get_height() + 3

        theme = d.get("theme", "")
        name  = d.get("name", "")
        form  = d.get("formerly", "")
        desc  = THEME_DESCRIPTIONS.get(theme, "")

        blit_line(theme or f"SECTOR {d.get('sector_num', '')}", 14, (255, 176, 0), bold=True)
        if name:
            blit_line(name, 11, (180, 180, 180))
        if form:
            blit_line(f"formerly: {form}", 10, (120, 120, 140))
        if desc:
            blit_line(desc, 10, (100, 180, 130))

    def _draw_sling_floaters(self, dt: float):
        """Slingshot reward UI floater: '+800cr  FREE −5s' drifting up from ship."""
        if not self._sling_floaters:
            return
        from core.text import render_text
        alive = []
        for f in self._sling_floaters:
            f[2] -= dt
            if f[2] <= 0:
                continue
            pct   = f[2] / 1.2
            alpha = min(255, int(pct * 340))
            y_off = int((1.2 - f[2]) * 60)
            surf  = render_text("+800cr  FREE −5s", 13, (255, 220, 60), bold=True, shadow=True)
            surf.set_alpha(alpha)
            self.surface.blit(surf, (int(f[0]) - surf.get_width() // 2,
                                     int(f[1]) - 20 - y_off))
            alive.append(f)
        self._sling_floaters = alive

    # ------------------------------------------------------------------
    def _draw_spore_effect(self, ship, t: float):
        """Psychedelic panic overlay when EpistemologicalShrooms inverts controls."""
        cargo = getattr(ship, "cargo", None)
        if cargo is None or not hasattr(cargo, "inversion_active"):
            return

        spore_level = getattr(cargo, "spore_level", 0.0)
        W, H = S.SCREEN_W, S.FLIGHT_H

        # ── Mandala background when spore_level > 0.2 (ambient build-up) ─────
        if spore_level > 0.2:
            mandala_surf = pygame.Surface((W, H), pygame.SRCALPHA)
            mcx, mcy = W // 2, H // 2
            mandala_a = int((spore_level - 0.2) / 0.8 * 90)
            # Hue cycles over time
            hue_m = (t * 0.07) % 1.0
            # Concentric triangles
            n_tri = int(3 + (spore_level - 0.2) * 8)
            for ti in range(n_tri):
                tri_r = 30 + ti * 22
                tri_ang = t * 0.35 * (1 if ti % 2 == 0 else -1)
                tri_pts = [
                    (int(mcx + tri_r * math.cos(tri_ang + math.tau * k / 3)),
                     int(mcy + tri_r * math.sin(tri_ang + math.tau * k / 3)))
                    for k in range(3)
                ]
                hue_t = (hue_m + ti * 0.08) % 1.0
                col_m = _hsv(hue_t, 0.9, 0.85)
                alpha_t = max(10, mandala_a - ti * 8)
                pygame.draw.polygon(mandala_surf, (*col_m, alpha_t), tri_pts, 1)
            # Concentric hexagons
            n_hex = int(2 + (spore_level - 0.2) * 5)
            for hi in range(n_hex):
                hex_r = 45 + hi * 30
                hex_ang = -t * 0.22 * (1 if hi % 2 == 0 else -1)
                hex_pts = [
                    (int(mcx + hex_r * math.cos(hex_ang + math.tau * k / 6)),
                     int(mcy + hex_r * math.sin(hex_ang + math.tau * k / 6)))
                    for k in range(6)
                ]
                hue_h = (hue_m + 0.33 + hi * 0.06) % 1.0
                col_h = _hsv(hue_h, 0.85, 0.80)
                alpha_h = max(10, mandala_a - hi * 10)
                pygame.draw.polygon(mandala_surf, (*col_h, alpha_h), hex_pts, 1)
            self.surface.blit(mandala_surf, (0, 0))

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

        # ── Radial rainbow spokes from screen centre when fully inverted ────
        if spore_level >= 0.9:
            spoke_surf = pygame.Surface((W, H), pygame.SRCALPHA)
            mcx, mcy = W // 2, H // 2
            n_spokes = 32
            for si in range(n_spokes):
                spoke_ang = math.tau * si / n_spokes + t * 0.5
                spoke_hue = (t * 0.12 + si / n_spokes) % 1.0
                scol = _hsv(spoke_hue, 1.0, 1.0)
                spoke_len = int(math.hypot(W, H) * 0.7)
                pygame.draw.line(spoke_surf, (*scol, 55),
                                 (mcx, mcy),
                                 (int(mcx + math.cos(spoke_ang) * spoke_len),
                                  int(mcy + math.sin(spoke_ang) * spoke_len)), 2)
            self.surface.blit(spoke_surf, (0, 0))

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
