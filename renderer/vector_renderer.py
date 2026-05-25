from __future__ import annotations
import math
import random
import pygame
from core.text import get_font
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
        # Epic 11 — player identity: brief "YOU" label on sector load
        self._you_label_t: float = 0.0

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
        self._you_label_t = 1.5   # Epic 11 — show "YOU" label at sector open
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
        self._draw_debris_cloud(run_mgr, t)
        self._draw_debris(run_mgr, t)
        self._draw_satellites(run_mgr, t)
        self._draw_canisters(run_mgr, t)
        self._draw_bullets(ship)
        self._draw_alien(run_mgr, t)
        self._draw_ai_ships(run_mgr, t)
        self._draw_barges(run_mgr, ship, t)
        self._draw_barge_radar(run_mgr, ship, t)
        self._draw_trail(ship, t)
        self._draw_velocity_indicator(ship)
        self._update_embers(dt)
        self._draw_embers()
        self._update_explosions(dt)
        self._draw_explosions()
        frame_name = getattr(run_mgr, '_frame_name', '')
        self._draw_ship(ship, t, frame_name)
        self._draw_player_identity(ship, t, dt)   # Epic 11 — cyan ring + YOU label
        self._draw_exhaust(ship, t, frame_name)
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
        font_xs = get_font(13, bold=True)
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

        font_xl = get_font(20, bold=True)
        font_lg = get_font(16, bold=True)
        font_sm = get_font(12)

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

        font_sm  = get_font(12, bold=True)
        font_xs  = get_font(10)

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
            q_font = get_font(18, bold=True)
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

    def _draw_debris_cloud(self, run_mgr, t: float):
        cloud = getattr(run_mgr, "debris_cloud", None)
        if cloud is None:
            return
        # Dim visibility overlay
        ov = pygame.Surface((S.SCREEN_W, S.FLIGHT_H), pygame.SRCALPHA)
        ov.fill((20, 16, 10, cloud.alpha_overlay))
        self.surface.blit(ov, (0, 0))
        # Particles
        for p in cloud.particles:
            col = (int(160 + 40 * math.sin(t * 1.1 + p.radius)), 130, 90)
            s = pygame.Surface((int(p.radius * 2 + 1), int(p.radius * 2 + 1)),
                               pygame.SRCALPHA)
            pygame.draw.circle(s, (*col, p.alpha), (int(p.radius), int(p.radius)),
                               int(p.radius))
            self.surface.blit(s, (int(p.pos.x - p.radius), int(p.pos.y - p.radius)))

    def _draw_well(self, well, t: float):
        cx, cy = int(well.pos.x), int(well.pos.y)
        r      = well.radius
        collapse = getattr(well, "collapsing_pct", 0.0)
        # Hue shifts from normal cycling → red (0.0) as well collapses.
        # At collapse_pct=1.0 the drift baseline locks at hue=0.05 (deep red).
        drift_speed = max(0.01, 0.07 * (1.0 - collapse * 0.85))
        drift  = (t * drift_speed + collapse * 0.5) % 1.0
        # Rotation slows as it collapses
        rot_speed = 9.0 * (1.0 - collapse * 0.7)
        pulse  = math.sin(t * max(0.3, 1.4 - collapse)) * (4.5 + collapse * 8.0)

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
            ang = math.radians(i * 45 + t * rot_speed)
            x1 = cx + int(math.cos(ang) * r * 1.7)
            y1 = cy + int(math.sin(ang) * r * 1.7)
            x2 = cx + int(math.cos(ang) * r * 0.90)
            y2 = cy + int(math.sin(ang) * r * 0.90)
            pygame.draw.line(self.surface, line_col, (x1, y1), (x2, y2), 2)

        # Counter-rotating secondary spokes (4-fold, width=2)
        sec_col = _hsv((drift + 0.22) % 1.0, 0.55, 0.28)
        for i in range(4):
            ang = math.radians(i * 90 + 22.5 - t * (rot_speed * 0.55))
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

    # ------------------------------------------------------------------  AI SHIPS
    def _draw_ai_ships(self, run_mgr, t: float):
        ai_ships = getattr(run_mgr, "ai_ships", None)
        if not ai_ships:
            return
        for ship in ai_ships:
            if not ship.alive:
                continue
            self._draw_ai_ship(ship, t)
            self._draw_ai_ship_status(ship, t)

    def _draw_ai_ship(self, aiship, t: float) -> None:
        from antagonists.ai_ship import (
            CLASS_FIGHTER, CLASS_FREIGHTER, CLASS_HAULER,
            CLASS_GUNBOAT, CLASS_DERELICT,
        )
        cls = aiship.ship_class
        if cls == CLASS_FIGHTER:
            self._draw_aiship_fighter(aiship, t)
        elif cls == CLASS_FREIGHTER:
            self._draw_aiship_freighter(aiship, t)
        elif cls == CLASS_HAULER:
            self._draw_aiship_hauler(aiship, t)
        elif cls == CLASS_GUNBOAT:
            self._draw_aiship_gunboat(aiship, t)
        elif cls == CLASS_DERELICT:
            self._draw_aiship_derelict(aiship, t)

    def _aiship_world_pts(self, aiship, raw_pts):
        rad = math.radians(aiship.heading)
        cos_a, sin_a = math.cos(rad), math.sin(rad)
        return [
            (int(lx * cos_a - ly * sin_a + aiship.pos.x),
             int(lx * sin_a + ly * cos_a + aiship.pos.y))
            for lx, ly in raw_pts
        ]

    def _aiship_hit_tint(self, aiship, base_col):
        if aiship._hit_t > 0:
            mix = aiship._hit_t / 0.18
            return (
                min(255, int(base_col[0] + (255 - base_col[0]) * mix)),
                min(255, int(base_col[1] + (60 - base_col[1]) * mix)),
                min(255, int(base_col[2] + (60 - base_col[2]) * mix)),
            )
        return base_col

    def _aiship_scorches(self, aiship, n_marks: int = 4) -> list[tuple[int, int, int]]:
        """Deterministic scorch points in local space for the wear overlay."""
        rng = random.Random(aiship._art_seed)
        out = []
        for _ in range(n_marks):
            lx = rng.uniform(-22, 18)
            ly = rng.uniform(-10, 10)
            r = rng.randint(1, 3)
            out.append((int(lx), int(ly), r))
        return out

    # ---- FIGHTER --------------------------------------------------------
    def _draw_aiship_fighter(self, aiship, t: float):
        # Angular fighter, asymmetric wings — mismatched panels (run down).
        hull_pts = [(20, 0), (8, -7), (-4, -10), (-14, -8),
                    (-18, -3), (-18, 3), (-14, 8), (-4, 10), (8, 7)]
        wing_l = [(2, -10), (6, -22), (-2, -22), (-10, -10)]
        wing_r = [(2,  10), (6,  22), (-2,  22), (-10,  10)]
        # Stub gun barrels
        gun = [(20, 0), (28, 0)]

        wpts = self._aiship_world_pts(aiship, hull_pts)
        wl   = self._aiship_world_pts(aiship, wing_l)
        wr   = self._aiship_world_pts(aiship, wing_r)
        gpts = self._aiship_world_pts(aiship, gun)

        hull_col = self._aiship_hit_tint(aiship, (60, 65, 70))
        edge_col = self._aiship_hit_tint(aiship, (170, 165, 140))
        # Asymmetric panel — left wing slightly bleached, right freshly scorched
        l_wing_col = (50, 80, 70) if int(aiship._art_seed) % 2 == 0 else (75, 60, 50)
        r_wing_col = (70, 55, 45) if int(aiship._art_seed) % 2 == 0 else (45, 75, 65)

        pygame.draw.polygon(self.surface, l_wing_col, wl)
        pygame.draw.polygon(self.surface, edge_col,  wl, 1)
        pygame.draw.polygon(self.surface, r_wing_col, wr)
        pygame.draw.polygon(self.surface, edge_col,  wr, 1)
        pygame.draw.polygon(self.surface, hull_col, wpts)
        pygame.draw.polygon(self.surface, edge_col, wpts, 1)
        pygame.draw.line(self.surface, edge_col, gpts[0], gpts[1], 2)

        # Cockpit — tiny amber slit
        cockpit_pts = self._aiship_world_pts(aiship, [(8, -2), (12, -2), (12, 2), (8, 2)])
        pygame.draw.polygon(self.surface, (220, 140, 30), cockpit_pts)

        # Engine flicker
        self._aiship_exhaust(aiship, dist=-20, side_off=0, flame_col=(255, 130, 40))

        # Wear scorches
        self._draw_aiship_wear(aiship, intensity=aiship.wear)

    # ---- FREIGHTER ------------------------------------------------------
    def _draw_aiship_freighter(self, aiship, t: float):
        # Boxy mid-size freighter. Big rectangular cargo pod, modular look.
        hull_pts = [(32, 0), (24, -10), (-26, -14), (-32, -8),
                    (-32, 8), (-26, 14), (24, 10)]
        pod = [(-18, -10), (10, -10), (10, 10), (-18, 10)]
        cockpit = [(20, -5), (28, -3), (28, 3), (20, 5)]
        # Antenna mast
        mast = [(-10, -14), (-10, -22)]

        wpts = self._aiship_world_pts(aiship, hull_pts)
        ppts = self._aiship_world_pts(aiship, pod)
        cpts = self._aiship_world_pts(aiship, cockpit)
        mpts = self._aiship_world_pts(aiship, mast)

        hull_col = self._aiship_hit_tint(aiship, (62, 56, 46))
        edge_col = self._aiship_hit_tint(aiship, (180, 160, 110))
        pod_col  = (40, 45, 50)

        pygame.draw.polygon(self.surface, hull_col, wpts)
        pygame.draw.polygon(self.surface, edge_col, wpts, 1)
        # Cargo pod strapped to the back
        pygame.draw.polygon(self.surface, pod_col, ppts)
        pygame.draw.polygon(self.surface, (130, 120, 100), ppts, 1)
        # Cargo straps
        for off in (-6, 0, 6):
            s1 = self._aiship_world_pts(aiship, [(-18, off), (10, off)])
            pygame.draw.line(self.surface, (90, 75, 50), s1[0], s1[1], 1)
        # Cockpit window
        pygame.draw.polygon(self.surface, (230, 195, 80), cpts)
        # Mast
        pygame.draw.line(self.surface, edge_col, mpts[0], mpts[1], 1)
        # Twin engines — back left and right
        self._aiship_exhaust(aiship, dist=-30, side_off=-8, flame_col=(255, 140, 50))
        self._aiship_exhaust(aiship, dist=-30, side_off=8,  flame_col=(255, 140, 50))

        self._draw_aiship_wear(aiship, intensity=aiship.wear)

    # ---- HAULER ---------------------------------------------------------
    def _draw_aiship_hauler(self, aiship, t: float):
        # Long industrial tug with a grappling arm — Mira Voss type.
        hull_pts = [(34, 0), (24, -8), (-22, -10), (-34, -6),
                    (-34, 6), (-22, 10), (24, 8)]
        # Grappling arm forward
        arm = [(34, -4), (50, -6), (50, 6), (34, 4)]
        # Tool sled on top
        sled = [(0, -12), (14, -12), (14, -16), (0, -16)]

        wpts = self._aiship_world_pts(aiship, hull_pts)
        apts = self._aiship_world_pts(aiship, arm)
        spts = self._aiship_world_pts(aiship, sled)

        hull_col = self._aiship_hit_tint(aiship, (78, 60, 40))
        edge_col = self._aiship_hit_tint(aiship, (220, 150, 50))

        pygame.draw.polygon(self.surface, hull_col, wpts)
        pygame.draw.polygon(self.surface, edge_col, wpts, 1)
        pygame.draw.polygon(self.surface, (60, 45, 30), apts)
        pygame.draw.polygon(self.surface, edge_col, apts, 1)
        pygame.draw.polygon(self.surface, (40, 40, 40), spts)
        pygame.draw.polygon(self.surface, (140, 130, 80), spts, 1)
        # Pulsing welding tip on grappling arm
        tip = self._aiship_world_pts(aiship, [(50, 0)])[0]
        pulse = int(180 + 60 * math.sin(t * 5.5 + aiship._art_seed))
        pygame.draw.circle(self.surface, (pulse, 100, 30), tip, 3)
        pygame.draw.circle(self.surface, (255, 200, 100), tip, 1)
        # Cockpit
        cockpit_pts = self._aiship_world_pts(aiship, [(20, -3), (28, -3), (28, 3), (20, 3)])
        pygame.draw.polygon(self.surface, (220, 200, 60), cockpit_pts)
        # Single heavy engine
        self._aiship_exhaust(aiship, dist=-32, side_off=0, flame_col=(255, 110, 30), scale=1.4)

        self._draw_aiship_wear(aiship, intensity=aiship.wear)

    # ---- GUNBOAT (pirate) ----------------------------------------------
    def _draw_aiship_gunboat(self, aiship, t: float):
        # Compact pirate gunboat — twin engines, two forward guns, jagged hull
        hull_pts = [(22, 0), (14, -8), (-4, -12), (-14, -10),
                    (-18, -4), (-18, 4), (-14, 10), (-4, 12), (14, 8)]
        # Twin gun pods extending forward
        gun_l = [(14, -8), (24, -10), (24, -6), (16, -4)]
        gun_r = [(14,  8), (24,  10), (24,  6), (16,  4)]
        # Bridge bulge
        bridge = [(2, -5), (10, -3), (10, 3), (2, 5)]

        wpts = self._aiship_world_pts(aiship, hull_pts)
        glpts = self._aiship_world_pts(aiship, gun_l)
        grpts = self._aiship_world_pts(aiship, gun_r)
        bpts = self._aiship_world_pts(aiship, bridge)

        hull_col = self._aiship_hit_tint(aiship, (40, 18, 18))
        edge_col = self._aiship_hit_tint(aiship, (220, 50, 50))

        pygame.draw.polygon(self.surface, hull_col, wpts)
        pygame.draw.polygon(self.surface, edge_col, wpts, 2)
        pygame.draw.polygon(self.surface, (28, 15, 15), glpts)
        pygame.draw.polygon(self.surface, edge_col, glpts, 1)
        pygame.draw.polygon(self.surface, (28, 15, 15), grpts)
        pygame.draw.polygon(self.surface, edge_col, grpts, 1)
        pygame.draw.polygon(self.surface, (80, 25, 25), bpts)
        # Hostile flash — bridge pulses crimson when in ATTACK
        from antagonists.ai_ship import ST_ATTACK
        if aiship.state == ST_ATTACK:
            pulse = int(120 + 100 * math.sin(t * 11.0))
            bridge_pulse = self._aiship_world_pts(aiship, [(6, 0)])[0]
            pygame.draw.circle(self.surface, (255, pulse // 2, pulse // 2), bridge_pulse, 4)
        # Twin engines, dirty red flame
        self._aiship_exhaust(aiship, dist=-22, side_off=-5, flame_col=(255, 70, 30))
        self._aiship_exhaust(aiship, dist=-22, side_off=5,  flame_col=(255, 70, 30))

        # Skull-paint scratch on bridge (deterministic)
        rng = random.Random(aiship._art_seed + 1)
        for _ in range(3):
            lx = rng.uniform(-8, 4)
            ly = rng.uniform(-2, 2)
            sp1 = self._aiship_world_pts(aiship, [(lx, ly)])[0]
            sp2 = self._aiship_world_pts(aiship, [(lx + 3, ly)])[0]
            pygame.draw.line(self.surface, (200, 200, 200), sp1, sp2, 1)

        self._draw_aiship_wear(aiship, intensity=aiship.wear)

    # ---- DERELICT -------------------------------------------------------
    def _draw_aiship_derelict(self, aiship, t: float):
        # Wrecked hulk — broken silhouette, sparking, drifting end-over-end slowly
        hull_pts = [(22, -2), (14, -10), (-8, -14), (-22, -8),
                    (-20, 4), (-10, 14), (8, 10), (18, 4)]
        wpts = self._aiship_world_pts(aiship, hull_pts)
        # Slowly tumbling — adjust heading visually
        # (use t-based wobble layered on existing heading by drawing torn panels)

        hull_col = (32, 30, 28)
        edge_col = (110, 100, 90)

        pygame.draw.polygon(self.surface, hull_col, wpts)
        pygame.draw.polygon(self.surface, edge_col, wpts, 1)

        # Torn hull plates — random gaps showing void
        rng = random.Random(aiship._art_seed + 2)
        for _ in range(3):
            lx = rng.uniform(-18, 10)
            ly = rng.uniform(-10, 10)
            torn = [(lx, ly), (lx + 6, ly - 1), (lx + 5, ly + 4), (lx - 1, ly + 3)]
            tp = self._aiship_world_pts(aiship, torn)
            pygame.draw.polygon(self.surface, (8, 6, 4), tp)

        # Random sparks from broken systems
        if random.random() < 0.30:
            spark_lx = rng.uniform(-16, 8)
            spark_ly = rng.uniform(-10, 10)
            sp = self._aiship_world_pts(aiship, [(spark_lx, spark_ly)])[0]
            pygame.draw.circle(self.surface, (255, 200, 80), sp, 2)
            pygame.draw.circle(self.surface, (255, 240, 200), sp, 1)

        # Distress beacon — slow red blink
        if int(t * 1.2 + aiship._art_seed) % 3 == 0:
            beacon = self._aiship_world_pts(aiship, [(-8, 0)])[0]
            pygame.draw.circle(self.surface, (220, 40, 40), beacon, 3)
            pygame.draw.circle(self.surface, (255, 120, 120), beacon, 1)

    # ---- Shared helpers ------------------------------------------------
    def _aiship_exhaust(self, aiship, dist: int, side_off: int,
                        flame_col: tuple[int, int, int], scale: float = 1.0):
        # Flame anchored at local (-dist, side_off), pointing astern
        rad = math.radians(aiship.heading)
        cos_a, sin_a = math.cos(rad), math.sin(rad)
        ex = aiship.pos.x + dist * cos_a - side_off * sin_a
        ey = aiship.pos.y + dist * sin_a + side_off * cos_a
        flame_len = (6 + 4 * random.random()) * scale
        bx = ex + (-cos_a) * flame_len
        by = ey + (-sin_a) * flame_len
        pygame.draw.line(self.surface, flame_col, (int(ex), int(ey)), (int(bx), int(by)),
                         max(1, int(2 * scale)))
        pygame.draw.circle(self.surface, flame_col, (int(ex), int(ey)),
                           max(1, int(2 * scale)))

    def _draw_aiship_wear(self, aiship, intensity: float):
        if intensity < 0.35:
            return
        # Scorch marks scaled by wear
        n = int(2 + intensity * 6)
        for lx, ly, r in self._aiship_scorches(aiship, n):
            wp = self._aiship_world_pts(aiship, [(lx, ly)])[0]
            scorch_alpha = int(80 + 100 * intensity)
            s = pygame.Surface((r * 2 + 2, r * 2 + 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (15, 10, 5, scorch_alpha), (r + 1, r + 1), r)
            self.surface.blit(s, (wp[0] - r - 1, wp[1] - r - 1))

    def _draw_ai_ship_status(self, aiship, t: float):
        # Small caption above hailers when in HAIL state
        from antagonists.ai_ship import ST_HAIL, ST_ATTACK
        if aiship.state == ST_HAIL:
            font = get_font(9, bold=True)
            pulse = 0.5 + 0.5 * math.sin(t * 4.0)
            col = (int(150 + 105 * pulse), int(220 + 35 * pulse), 80)
            lbl = font.render("HAIL ▸ PRESS E", True, col)
            self.surface.blit(lbl,
                              (int(aiship.pos.x) - lbl.get_width() // 2,
                               int(aiship.pos.y) - aiship.radius - 18))
        elif aiship.state == ST_ATTACK:
            font = get_font(9, bold=True)
            col = (255, 60, 60)
            lbl = font.render("! HOSTILE", True, col)
            self.surface.blit(lbl,
                              (int(aiship.pos.x) - lbl.get_width() // 2,
                               int(aiship.pos.y) - aiship.radius - 18))

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
        font = get_font(8)
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

    def _draw_player_identity(self, ship, t: float, dt: float):
        """Epic 11 — constant cyan identity ring + brief 'YOU' label on sector load."""
        if not ship.is_alive:
            return
        pos = ship.pos
        px, py = int(pos.x), int(pos.y)

        # Constant dim cyan ring at 24px — always on, very subtle
        ring_surf = pygame.Surface((52, 52), pygame.SRCALPHA)
        ring_col  = (60, 210, 220, 38)   # dim cyan, very low alpha
        pygame.draw.circle(ring_surf, ring_col, (26, 26), 24, 1)
        self.surface.blit(ring_surf, (px - 26, py - 26))

        # "YOU" amber label — visible for 1.5s after sector load, then gone
        self._you_label_t = max(0.0, self._you_label_t - dt)
        if self._you_label_t > 0:
            fade = min(1.0, self._you_label_t * 2.0)   # fast in, holds, fades last 0.5s
            alpha = int(210 * fade)
            lbl_font = get_font(11, bold=True)
            lbl = lbl_font.render("YOU", True, (240, 190, 60))
            lbl.set_alpha(alpha)
            self.surface.blit(lbl, (px - lbl.get_width() // 2, py - 36))

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

    def _draw_ship(self, ship, t: float = 0.0, frame_name: str = ""):
        if not ship.is_alive:
            return
        if getattr(ship, "iframe_active", False):
            if int(t * 18.0) % 2 == 0:
                return

        pos   = ship.pos
        angle = ship.angle
        hp    = ship.hull_pct

        if frame_name == "SCRAP DELTA-7":
            self._draw_ship_delta7(ship, pos, angle, hp, t)
        elif frame_name == "REINFORCED JUNK MK2":
            self._draw_ship_junk_mk2(ship, pos, angle, hp, t)
        else:
            self._draw_ship_rustbucket(ship, pos, angle, hp, t)

        # Shared: battle damage scars across all frames
        if hp < 0.6:
            n_scars = int((0.6 - hp) * 14)
            rng = random.Random(id(ship) & 0xFFFF)
            for _ in range(n_scars):
                sx = rng.uniform(-20, 14)
                sy = rng.uniform(-14, 14)
                slen = rng.uniform(2, 5)
                sang = rng.uniform(0, math.tau)
                p1 = self._rotate_pt((sx, sy), angle, pos)
                p2 = self._rotate_pt((sx + math.cos(sang)*slen,
                                      sy + math.sin(sang)*slen), angle, pos)
                pygame.draw.line(self.surface, (180, 60, 50), p1, p2, 1)
            if hp < 0.3 and int(t * 6) % 2 == 0:
                rng2 = random.Random(id(ship) & 0xFF00)
                spk = self._rotate_pt((rng2.uniform(-16, 10), rng2.uniform(-10, 10)), angle, pos)
                pygame.draw.circle(self.surface, (255, 220, 80), spk, 2)
                pygame.draw.circle(self.surface, (255, 80, 30), spk, 1)

    # ---- RUSTBUCKET ALPHA -----------------------------------------------
    def _draw_ship_rustbucket(self, ship, pos, angle, hp, t):
        """Standard courier hull — beat-up postal shuttle, balanced."""
        hull = [(20,0),(12,-9),(-3,-11),(-18,-8),(-18,8),(-3,11),(12,9)]
        wing_l = [(-2,-11),(4,-14),(-4,-14)]
        wing_r = [(-2, 11),(4, 14),(-4, 14)]
        pts = [self._rotate_pt(p, angle, pos) for p in hull]
        wl  = [self._rotate_pt(p, angle, pos) for p in wing_l]
        wr  = [self._rotate_pt(p, angle, pos) for p in wing_r]

        # Engine ambient glow halo
        glow_r = int(30 + 5 * (0.7 + 0.3 * math.sin(t * 8.0)))
        glow_surf = pygame.Surface((glow_r*2, glow_r*2), pygame.SRCALPHA)
        ag_col = _hsv(0.58 + (1.0-hp)*0.20, 0.5, 0.8)
        for layer in range(3):
            pygame.draw.circle(glow_surf, (*ag_col, max(0, 28-layer*9)),
                               (glow_r, glow_r), max(1, glow_r-layer*7))
        self.surface.blit(glow_surf, (int(pos.x)-glow_r, int(pos.y)-glow_r))

        # Damage glow outline
        dr = int((1.0-hp)*60)
        pygame.draw.polygon(self.surface,
                            (dr, max(0,55-int((1-hp)*42)), max(0,115-int((1-hp)*85))),
                            pts, 5)

        # Wing nubs (nav light mounts)
        pygame.draw.polygon(self.surface, (10, 16, 30), wl)
        pygame.draw.polygon(self.surface, (10, 16, 30), wr)
        ol = S.WHITE_VEC if hp > 0.4 else (200, 180, 180)
        pygame.draw.polygon(self.surface, ol, wl, 1)
        pygame.draw.polygon(self.surface, ol, wr, 1)

        # Hull fill + outline
        pygame.draw.polygon(self.surface, (8, 14, 28), pts)
        pygame.draw.polygon(self.surface, ol, pts, 2)

        # Cargo bay marking — centre rectangle
        bay_pts = [(-1,-8),(9,-8),(9,9),(-1,9)]
        bp = [self._rotate_pt(p, angle, pos) for p in bay_pts]
        pygame.draw.polygon(self.surface, (12, 18, 32), bp)
        pygame.draw.polygon(self.surface, (38, 44, 68), bp, 1)
        for x_off in (2, 5):
            p1 = self._rotate_pt((x_off, -8), angle, pos)
            p2 = self._rotate_pt((x_off,  9), angle, pos)
            pygame.draw.line(self.surface, (28, 32, 52), p1, p2, 1)

        # Panel seams
        seam_col = (55, 58, 90)
        for a, b in [((14,-7),(-6,-7)),((14,8),(-6,8)),((5,-10),(5,11)),((-5,-9),(-5,10))]:
            pygame.draw.line(self.surface, seam_col,
                             self._rotate_pt(a, angle, pos), self._rotate_pt(b, angle, pos), 1)

        # Cockpit visor — elongated hex on nose
        cockpit_pts = [(17,-3),(12,-6),(7,-5),(7,5),(12,6),(17,3)]
        cpt = [self._rotate_pt(p, angle, pos) for p in cockpit_pts]
        cp  = 0.6 + 0.4 * math.sin(t * 1.8)
        pygame.draw.polygon(self.surface, (4, 30, 60), cpt)
        pygame.draw.polygon(self.surface,
                            (int(20+80*cp), int(140+80*cp), int(180+60*cp)), cpt, 1)
        pygame.draw.circle(self.surface, (180, 240, 255),
                           self._rotate_pt((14,-2), angle, pos), 1)

        # Engine nozzle housing
        nz_pts = [(-18,-5),(-25,-4),(-25,4),(-18,5)]
        nz = [self._rotate_pt(p, angle, pos) for p in nz_pts]
        pygame.draw.polygon(self.surface, (0, 22, 50), nz)
        pygame.draw.polygon(self.surface, (75, 95, 130), nz, 1)
        np_ = 0.6 + 0.4 * math.sin(t * 14.0)
        pygame.draw.circle(self.surface,
                           (int(200*np_), int(140*np_), int(40*np_)),
                           self._rotate_pt((-21, 0), angle, pos), 2)

        # RCS ports
        rp = 0.4 + 0.4 * math.sin(t * 6.0)
        rc = (int(40+60*rp), int(40+60*rp), int(80+50*rp))
        for lx, ly in ((9,-8),(9,10),(-10,-6),(-10,8)):
            pygame.draw.circle(self.surface, rc, self._rotate_pt((lx,ly), angle, pos), 1)

        # Nav lights on wing nubs
        pygame.draw.circle(self.surface, (255, 60, 60), self._rotate_pt((-1,-14), angle, pos), 2)
        pygame.draw.circle(self.surface, (60, 255, 100), self._rotate_pt((-1, 14), angle, pos), 2)

        # Gun barrel
        self._draw_ship_gun(ship, pos, angle, t, tip=(26,0), base=(18,0))

    # ---- SCRAP DELTA-7 --------------------------------------------------
    def _draw_ship_delta7(self, ship, pos, angle, hp, t):
        """Light interceptor — swept delta wings, needle nose, tight single engine."""
        hull = [(26,0),(20,-5),(4,-9),(-8,-16),(-18,-10),(-18,10),(-8,16),(4,9),(20,5)]
        body = [(22,0),(16,-4),(0,-6),(-10,-4),(-16,-2),(-16,2),(-10,4),(0,6),(16,4)]
        pts  = [self._rotate_pt(p, angle, pos) for p in hull]
        bpts = [self._rotate_pt(p, angle, pos) for p in body]

        # Engine glow — tight, blue-white
        eg_col = _hsv(0.62 + (1.0-hp)*0.18, 0.6, 0.9)
        glow_surf = pygame.Surface((56, 56), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (*eg_col, 30), (28,28), 22)
        pygame.draw.circle(glow_surf, (*eg_col, 50), (28,28), 14)
        ep = self._rotate_pt((-16, 0), angle, pos)
        self.surface.blit(glow_surf, (ep[0]-28, ep[1]-28))

        # Damage glow outline
        dr = int((1.0-hp)*65)
        pygame.draw.polygon(self.surface,
                            (dr, max(0,55-int((1-hp)*42)), max(0,115-int((1-hp)*85))),
                            pts, 5)

        # Wing fill (dark blue-grey) + outline
        pygame.draw.polygon(self.surface, (6, 12, 24), pts)
        ol = S.WHITE_VEC if hp > 0.4 else (200, 180, 180)
        pygame.draw.polygon(self.surface, ol, pts, 2)

        # Fuselage body (brighter inset)
        pygame.draw.polygon(self.surface, (10, 18, 36), bpts)
        pygame.draw.polygon(self.surface, (80, 90, 120), bpts, 1)

        # Panel seams — swept delta lines
        seam_col = (50, 55, 88)
        for a, b in [((16,-3),(-6,-3)),((16,3),(-6,3)),((4,-8),(4,8)),((-4,-12),(-4,12))]:
            pygame.draw.line(self.surface, seam_col,
                             self._rotate_pt(a, angle, pos), self._rotate_pt(b, angle, pos), 1)

        # Cockpit — narrow fighter-pilot slit
        cockpit_pts = [(22,-2),(17,-4),(12,-3),(12,3),(17,4),(22,2)]
        cpt = [self._rotate_pt(p, angle, pos) for p in cockpit_pts]
        cp  = 0.7 + 0.3 * math.sin(t * 1.8)
        pygame.draw.polygon(self.surface, (4, 26, 52), cpt)
        pygame.draw.polygon(self.surface,
                            (int(20+80*cp), int(120+100*cp), int(160+75*cp)), cpt, 1)
        pygame.draw.circle(self.surface, (200, 240, 255),
                           self._rotate_pt((20,-1), angle, pos), 1)

        # Engine nozzle — tight single rear center
        nz_pts = [(-18,-3),(-23,-2),(-23,2),(-18,3)]
        nz = [self._rotate_pt(p, angle, pos) for p in nz_pts]
        pygame.draw.polygon(self.surface, (0, 18, 45), nz)
        pygame.draw.polygon(self.surface, (80, 100, 140), nz, 1)
        np_ = 0.6 + 0.4 * math.sin(t * 16.0)
        pygame.draw.circle(self.surface,
                           (int(160*np_), int(200*np_), int(255*np_)),
                           self._rotate_pt((-20, 0), angle, pos), 2)

        # RCS ports — at wing roots
        rp = 0.4 + 0.4 * math.sin(t * 7.5)
        rc = (int(40+60*rp), int(50+70*rp), int(90+60*rp))
        for lx, ly in ((-2,-10),(-2,10),(-10,-6),(-10,6)):
            pygame.draw.circle(self.surface, rc, self._rotate_pt((lx,ly), angle, pos), 1)

        # Nav lights at swept wing tips
        pygame.draw.circle(self.surface, (255, 60, 60), self._rotate_pt((-8,-16), angle, pos), 2)
        pygame.draw.circle(self.surface, (60, 255, 100), self._rotate_pt((-8, 16), angle, pos), 2)

        # Gun barrel — longer on lighter/faster ship
        self._draw_ship_gun(ship, pos, angle, t, tip=(32,0), base=(22,0))

    # ---- REINFORCED JUNK MK2 -------------------------------------------
    def _draw_ship_junk_mk2(self, ship, pos, angle, hp, t):
        """Heavy armored freighter — wide, blunt, twin engines, twin guns."""
        hull = [(16,0),(10,-12),(-4,-18),(-20,-16),(-28,-8),(-28,8),(-20,16),(-4,18),(10,12)]
        shoulder_l = [(0,-14),(0,-20),(-16,-20),(-16,-14)]
        shoulder_r = [(0, 14),(0, 20),(-16, 20),(-16, 14)]
        pts = [self._rotate_pt(p, angle, pos) for p in hull]
        sl  = [self._rotate_pt(p, angle, pos) for p in shoulder_l]
        sr  = [self._rotate_pt(p, angle, pos) for p in shoulder_r]

        # Twin engine glow halos
        ag_col = _hsv(0.55 + (1.0-hp)*0.22, 0.45, 0.75)
        for side_off in (-8, 8):
            glow_surf = pygame.Surface((52, 52), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, (*ag_col, 25), (26,26), 20)
            pygame.draw.circle(glow_surf, (*ag_col, 45), (26,26), 12)
            ep = self._rotate_pt((-24, side_off), angle, pos)
            self.surface.blit(glow_surf, (ep[0]-26, ep[1]-26))

        # Damage glow outline
        dr = int((1.0-hp)*70)
        pygame.draw.polygon(self.surface,
                            (dr, max(0,55-int((1-hp)*42)), max(0,115-int((1-hp)*85))),
                            pts, 6)

        # Shoulder armor fill
        pygame.draw.polygon(self.surface, (10, 16, 26), sl)
        pygame.draw.polygon(self.surface, (10, 16, 26), sr)
        shldr_col = (100, 110, 130) if hp > 0.4 else (150, 130, 130)
        pygame.draw.polygon(self.surface, shldr_col, sl, 1)
        pygame.draw.polygon(self.surface, shldr_col, sr, 1)

        # Hull fill + outline
        pygame.draw.polygon(self.surface, (8, 14, 28), pts)
        ol = S.WHITE_VEC if hp > 0.4 else (200, 180, 180)
        pygame.draw.polygon(self.surface, ol, pts, 2)

        # Armor rivets on shoulder plates
        rivet_col = (70, 75, 100)
        for lx, ly in [(-4,-16),(-10,-18),(-16,-16),(-4,16),(-10,18),(-16,16)]:
            pygame.draw.circle(self.surface, rivet_col, self._rotate_pt((lx,ly), angle, pos), 1)

        # Panel seams — heavy armored look
        seam_col = (55, 58, 90)
        for a, b in [((10,-10),(-10,-10)),((10,11),(-10,11)),
                     ((4,-16),(4,17)),((-8,-16),(-8,17)),((-16,-12),(-16,13))]:
            pygame.draw.line(self.surface, seam_col,
                             self._rotate_pt(a, angle, pos), self._rotate_pt(b, angle, pos), 1)

        # Cargo bay — large center rectangle
        bay_pts = [(-4,-10),(8,-10),(8,11),(-4,11)]
        bp = [self._rotate_pt(p, angle, pos) for p in bay_pts]
        pygame.draw.polygon(self.surface, (12, 16, 28), bp)
        pygame.draw.polygon(self.surface, (42, 46, 70), bp, 1)
        for x_off in (0, 4, 8):
            p1 = self._rotate_pt((x_off-2, -10), angle, pos)
            p2 = self._rotate_pt((x_off-2,  11), angle, pos)
            pygame.draw.line(self.surface, (30, 34, 55), p1, p2, 1)

        # Boxy cockpit dome at nose
        cockpit_pts = [(12,-6),(6,-10),(0,-8),(0,8),(6,10),(12,6)]
        cpt = [self._rotate_pt(p, angle, pos) for p in cockpit_pts]
        cp  = 0.5 + 0.5 * math.sin(t * 1.4)
        pygame.draw.polygon(self.surface, (6, 22, 44), cpt)
        pygame.draw.polygon(self.surface,
                            (int(20+60*cp), int(100+80*cp), int(140+80*cp)), cpt, 1)
        for gx, gy in ((10,-2),(8,-5)):
            pygame.draw.circle(self.surface, (160, 220, 255),
                               self._rotate_pt((gx, gy), angle, pos), 1)

        # Twin engine nozzles side by side
        for side_off in (-8, 8):
            y1, y2 = side_off-4, side_off+4
            nz_pts = [(-24,y1),(-30,y1),(-30,y2),(-24,y2)]
            nz = [self._rotate_pt(p, angle, pos) for p in nz_pts]
            pygame.draw.polygon(self.surface, (0, 18, 42), nz)
            pygame.draw.polygon(self.surface, (70, 90, 120), nz, 1)
            np_ = 0.5 + 0.5 * math.sin(t * 13.0 + side_off)
            pygame.draw.circle(self.surface,
                               (int(180*np_), int(110*np_), int(30*np_)),
                               self._rotate_pt((-27, side_off), angle, pos), 2)

        # RCS ports — 6 for the heavier ship
        rp = 0.4 + 0.4 * math.sin(t * 5.5)
        rc = (int(40+60*rp), int(40+60*rp), int(80+50*rp))
        for lx, ly in ((8,-10),(8,11),(-4,-14),(-4,15),(-14,-10),(-14,10)):
            pygame.draw.circle(self.surface, rc, self._rotate_pt((lx,ly), angle, pos), 1)

        # Nav lights at outer armor flanges
        pygame.draw.circle(self.surface, (255, 60, 60), self._rotate_pt((-4,-18), angle, pos), 2)
        pygame.draw.circle(self.surface, (60, 255, 100), self._rotate_pt((-4, 18), angle, pos), 2)

        # Twin gun pods — heavier ship, two barrels
        self._draw_ship_gun(ship, pos, angle, t, tip=(22,-5), base=(14,-5))
        self._draw_ship_gun(ship, pos, angle, t, tip=(22, 5), base=(14, 5))

    # ---- Shared gun helper ----------------------------------------------
    def _draw_ship_gun(self, ship, pos, angle, t, tip, base):
        if not hasattr(ship, "gun"):
            return
        if not ship.gun.is_jammed:
            tp = self._rotate_pt(tip, angle, pos)
            bp = self._rotate_pt(base, angle, pos)
            pygame.draw.line(self.surface, (130, 130, 160), bp, tp, 2)
            pygame.draw.line(self.surface, (100, 230, 130), bp, tp, 1)
            pygame.draw.circle(self.surface, (60, 180, 90), tp, 1)
        else:
            jp  = 0.5 + 0.5 * abs(math.sin(t * 8))
            jc  = (int(200*jp), 0, 0)
            tp  = self._rotate_pt(tip, angle, pos)
            bp  = self._rotate_pt(base, angle, pos)
            pygame.draw.line(self.surface, jc, bp, tp, 2)

    def _draw_exhaust(self, ship, t: float, frame_name: str = ""):
        keys      = pygame.key.get_pressed()
        thrusting = keys[pygame.K_UP] or keys[pygame.K_w]
        reversing = keys[pygame.K_DOWN] or keys[pygame.K_s]
        if not thrusting and not reversing:
            return
        pos    = ship.pos
        angle  = ship.angle
        hp_pct = ship.hull_pct
        flick  = 1.0 + math.sin(t * 53.7) * 0.13
        jitter = math.sin(t * 22.0) * 1.5
        rad    = math.radians(angle + 180)
        ship_vx = ship.body.vel.x if hasattr(ship, "body") else 0
        ship_vy = ship.body.vel.y if hasattr(ship, "body") else 0

        if thrusting:
            if frame_name == "REINFORCED JUNK MK2":
                # Twin heavy plumes — shorter, wider, orange-amber
                hue2    = 0.06 + (1.0-hp_pct)*0.05
                c_out2  = _hsv(hue2, 0.85, 0.38*flick)
                c_mid2  = _hsv(hue2, 0.95, 0.75*flick)
                c_core2 = _hsv(hue2-0.03, 0.20, 1.0)
                gp_col2 = _hsv(hue2, 0.8, 0.9)
                for so in (-8, 8):
                    outer = [self._rotate_pt(p, angle, pos) for p in
                             ((-26,so-6),(-54,so+jitter*0.7),(-26,so+6))]
                    mid   = [self._rotate_pt(p, angle, pos) for p in
                             ((-26,so-3),(-38,so+jitter*0.4),(-26,so+3))]
                    core  = [self._rotate_pt(p, angle, pos) for p in
                             ((-26,so-1),(-30,so+jitter*0.2),(-26,so+1))]
                    glow_surf = pygame.Surface((100, 70), pygame.SRCALPHA)
                    pygame.draw.circle(glow_surf, (*gp_col2, 28), (50,35), 28)
                    pygame.draw.circle(glow_surf, (*gp_col2, 45), (50,35), 16)
                    gp = self._rotate_pt((-34, so), angle, pos)
                    self.surface.blit(glow_surf, (gp[0]-50, gp[1]-35))
                    pygame.draw.polygon(self.surface, c_out2,  outer)
                    pygame.draw.polygon(self.surface, c_mid2,  mid)
                    pygame.draw.polygon(self.surface, c_core2, core)
                    pygame.draw.circle(self.surface, (240, 250, 255),
                                       self._rotate_pt((-26, so), angle, pos), 1)
                if random.random() < 0.55:
                    spawn = self._rotate_pt((-28, random.choice([-8,8]) + random.uniform(-3,3)), angle, pos)
                    sp = random.uniform(120, 220)
                    spr = math.radians(random.uniform(-18, 18))
                    self._spawn_ember(spawn[0], spawn[1],
                                      math.cos(rad+spr)*sp + ship_vx*0.5,
                                      math.sin(rad+spr)*sp + ship_vy*0.5,
                                      (hue2 + random.uniform(-0.05, 0.05)) % 1.0)

            elif frame_name == "SCRAP DELTA-7":
                # Tight single blue-white plume — high energy
                hue3    = 0.62 + (1.0-hp_pct)*0.20
                c_out3  = _hsv(hue3, 0.70, 0.35*flick)
                c_mid3  = _hsv(hue3, 0.90, 0.78*flick)
                c_core3 = _hsv(hue3-0.02, 0.15, 1.0)
                gp_col3 = _hsv(hue3, 0.8, 0.9)
                outer = [self._rotate_pt(p, angle, pos) for p in
                         ((-18,-7),(-62,jitter*0.8),(-18,7))]
                mid   = [self._rotate_pt(p, angle, pos) for p in
                         ((-18,-4),(-40,jitter*0.5),(-18,4))]
                core  = [self._rotate_pt(p, angle, pos) for p in
                         ((-18,-2),(-28,jitter*0.25),(-18,2))]
                glow_surf = pygame.Surface((120, 70), pygame.SRCALPHA)
                pygame.draw.circle(glow_surf, (*gp_col3, 30), (60,35), 30)
                pygame.draw.circle(glow_surf, (*gp_col3, 55), (60,35), 18)
                cg = self._rotate_pt((-34, 0), angle, pos)
                self.surface.blit(glow_surf, (cg[0]-60, cg[1]-35))
                pygame.draw.polygon(self.surface, c_out3,  outer)
                pygame.draw.polygon(self.surface, c_mid3,  mid)
                pygame.draw.polygon(self.surface, c_core3, core)
                pygame.draw.polygon(self.surface, (240, 250, 255),
                                    [self._rotate_pt(p, angle, pos) for p in ((-18,-1),(-21,0),(-18,1))])
                if random.random() < 0.50:
                    spawn = self._rotate_pt((-20, random.uniform(-2,2)), angle, pos)
                    sp = random.uniform(160, 260)
                    spr = math.radians(random.uniform(-12, 12))
                    self._spawn_ember(spawn[0], spawn[1],
                                      math.cos(rad+spr)*sp + ship_vx*0.5,
                                      math.sin(rad+spr)*sp + ship_vy*0.5,
                                      (hue3 + random.uniform(-0.04, 0.04)) % 1.0)

            else:  # RUSTBUCKET ALPHA
                hue     = 0.58 + (1.0-hp_pct)*0.26
                c_outer = _hsv(hue, 0.75, 0.32*flick)
                c_mid   = _hsv(hue, 0.92, 0.72*flick)
                c_core  = _hsv(hue-0.04, 0.25, 1.0)
                gp_col  = _hsv(hue, 0.8, 0.9)
                outer = [self._rotate_pt(p, angle, pos) for p in
                         ((-18,-9),(-60,jitter),(-18,11))]
                mid   = [self._rotate_pt(p, angle, pos) for p in
                         ((-18,-5),(-40,jitter*0.6),(-18,7))]
                core  = [self._rotate_pt(p, angle, pos) for p in
                         ((-18,-2),(-26,jitter*0.3),(-18,4))]
                glow_surf = pygame.Surface((120, 80), pygame.SRCALPHA)
                pygame.draw.circle(glow_surf, (*gp_col, 35), (60,40), 36)
                pygame.draw.circle(glow_surf, (*gp_col, 50), (60,40), 22)
                cg = self._rotate_pt((-34, 0), angle, pos)
                self.surface.blit(glow_surf, (cg[0]-60, cg[1]-40))
                pygame.draw.polygon(self.surface, c_outer, outer)
                pygame.draw.polygon(self.surface, c_mid,   mid)
                pygame.draw.polygon(self.surface, c_core,  core)
                pygame.draw.polygon(self.surface, (240, 250, 255),
                                    [self._rotate_pt(p, angle, pos) for p in ((-18,-1),(-22,0),(-18,2))])
                if random.random() < 0.45:
                    spawn = self._rotate_pt((-22, random.uniform(-3,3)), angle, pos)
                    sp = random.uniform(140, 240)
                    spr = math.radians(random.uniform(-15, 15))
                    self._spawn_ember(spawn[0], spawn[1],
                                      math.cos(rad+spr)*sp + ship_vx*0.5,
                                      math.sin(rad+spr)*sp + ship_vy*0.5,
                                      (hue + random.uniform(-0.05, 0.05)) % 1.0)

        if reversing:
            if frame_name == "REINFORCED JUNK MK2":
                for gy in (-6, 6):
                    retro = [self._rotate_pt(p, angle, pos) for p in
                             ((14,gy-2),(26,math.sin(t*20)*0.6+gy),(14,gy+2))]
                    pygame.draw.polygon(self.surface, (200, 80, 20), retro)
                pygame.draw.circle(self.surface, (255, 130, 40),
                                   self._rotate_pt((22, 0), angle, pos), 4)
            elif frame_name == "SCRAP DELTA-7":
                retro = [self._rotate_pt(p, angle, pos) for p in
                         ((24,-1),(36,math.sin(t*22)*0.5),(24,1))]
                pygame.draw.polygon(self.surface, (180, 70, 10), retro)
                pygame.draw.circle(self.surface, (255, 120, 30),
                                   self._rotate_pt((32, 0), angle, pos), 2)
            else:
                retro = [self._rotate_pt(p, angle, pos) for p in
                         ((20,-2),(30,math.sin(t*20)*0.8),(20,2))]
                pygame.draw.polygon(self.surface, (200, 80, 20), retro)
                pygame.draw.circle(self.surface, (255, 140, 40),
                                   self._rotate_pt((28, 0), angle, pos), 3)

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
        font = get_font(7)
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
            font_xs = get_font(13)
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
        font_big = get_font(30, bold=True)
        font_sm  = get_font(15)
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
