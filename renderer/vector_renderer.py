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
                             EVT_HULL_CRITICAL)


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
        self._flash_t    = 0.0
        self._flash_col  = (180, 220, 255)
        self._scan_pings: list[tuple[int, int, float]] = []

        # Screen shake state: trauma decays exponentially; offset is random per frame
        self._shake_trauma = 0.0   # 0.0 (none) → 1.0 (huge)

        bus.subscribe(EVT_SLINGSHOT,        self._on_slingshot)
        bus.subscribe(EVT_SCAN_PING,        self._on_scan_ping)
        bus.subscribe(EVT_TETHER_HIT,       self._on_tether_hit)
        bus.subscribe(EVT_TETHER_SNAP,      self._on_tether_snap)
        bus.subscribe(EVT_MODULE_UNBOLTED,  self._on_module_unbolted)
        bus.subscribe(EVT_HULL_DAMAGE,      self._on_hull_damage)
        bus.subscribe(EVT_HULL_CRITICAL,    self._on_hull_critical)

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
        # Tiny shake on small hits, big shake on hard hits
        self._shake_trauma = min(1.0, self._shake_trauma + min(0.45, amount * 0.04))

    def _on_hull_critical(self, **_):
        self._shake_trauma = min(1.0, self._shake_trauma + 0.4)

    # ------------------------------------------------------------------
    def draw(self, run_mgr, ship, dt: float = 0.016):
        t = pygame.time.get_ticks() / 1000.0
        self._draw_nebulae(t)
        self._draw_dust(t)
        self._draw_stars(t)
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
        self._draw_ship(ship, t)
        self._draw_exhaust(ship, t)
        self._draw_proximity_alarm(run_mgr, ship, t)
        self._draw_flash(dt)
        self._draw_spore_effect(ship, t)
        self._apply_screen_shake(dt)

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
            hue = (base_hue + t * 0.0035) % 1.0
            col = _hsv(hue, sat * 0.60, 0.14)
            for scale, alpha in ((1.0, 20), (0.68, 32), (0.40, 44)):
                pygame.draw.circle(surf, (*col, alpha), (x, y), int(r * scale))
        self.surface.blit(surf, (0, 0))

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
                neon = [(0, 230, 255), (230, 0, 255), (255, 190, 0),
                        (0, 255, 128), (255, 60, 120)][int(hue * 5) % 5]
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

        # Pulsing core
        core_r   = max(5, int(r * 0.24))
        core_hue = (drift + 0.5) % 1.0
        pygame.draw.circle(self.surface, _hsv(core_hue, 0.60, 0.88),
                           (cx, cy), core_r + 6)
        pygame.draw.circle(self.surface, _hsv(core_hue, 0.20, 1.0),
                           (cx, cy), core_r)
        pygame.draw.circle(self.surface, (255, 255, 255), (cx, cy),
                           max(2, core_r // 3))

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

        pygame.draw.polygon(self.surface, c_glow,
                            [(cx, cy-size-5),(cx+size+5,cy),(cx,cy+size+5),(cx-size-5,cy)])
        pygame.draw.polygon(self.surface, c_mid,
                            [(cx, cy-size-1),(cx+size+1,cy),(cx,cy+size+1),(cx-size-1,cy)])
        pygame.draw.polygon(self.surface, c_bright,
                            [(cx, cy-size),(cx+size,cy),(cx,cy+size),(cx-size,cy)], 2)
        ang_off = t * 1.2
        for i in range(4):
            ang = ang_off + i * math.pi / 2
            tx1 = int(cx + math.cos(ang) * (size - 5))
            ty1 = int(cy + math.sin(ang) * (size - 5))
            tx2 = int(cx + math.cos(ang) * (size - 2))
            ty2 = int(cy + math.sin(ang) * (size - 2))
            pygame.draw.line(self.surface, c_bright, (tx1, ty1), (tx2, ty2), 1)
        pygame.draw.line(self.surface, c_bright, (cx-3,cy), (cx+3,cy), 1)
        pygame.draw.line(self.surface, c_bright, (cx,cy-3), (cx,cy+3), 1)

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
        glow_r = int((1.0 - hp) * 60)
        glow_col = (glow_r, max(0, 55 - int((1-hp)*42)), max(0, 115 - int((1-hp)*85)))

        pygame.draw.polygon(self.surface, glow_col, pts, 4)
        pygame.draw.polygon(self.surface, S.WHITE_VEC, pts, 2)

        # Interior spine
        nose  = self._rotate_pt((18, 0), angle, pos)
        belly = self._rotate_pt((-5, 0), angle, pos)
        pygame.draw.line(self.surface, (100, 100, 130), nose, belly, 1)

        nozzle = [self._rotate_pt(p, angle, pos) for p in
                  ((-14,-5),(-20,-3),(-20,5),(-14,7))]
        pygame.draw.polygon(self.surface, (0, 35, 75), nozzle, 3)
        pygame.draw.polygon(self.surface, S.GREY_DEAD, nozzle, 1)

        # RCS port dots
        for lx, ly in ((8,-8),(8,10),(-10,-6),(-10,8)):
            rpt = self._rotate_pt((lx, ly), angle, pos)
            pygame.draw.circle(self.surface, (40, 40, 60), rpt, 1)

        # Gun barrel indicator
        if hasattr(ship, "gun") and not ship.gun.is_jammed:
            barrel_tip  = self._rotate_pt((22, 0), angle, pos)
            barrel_base = self._rotate_pt((15, 0), angle, pos)
            pygame.draw.line(self.surface, (100, 220, 100), barrel_base, barrel_tip, 1)
        elif hasattr(ship, "gun") and ship.gun.is_jammed:
            jam_pulse = 0.5 + 0.5 * abs(math.sin(t * 8))
            jam_col   = (int(200 * jam_pulse), 0, 0)
            barrel_tip  = self._rotate_pt((22, 0), angle, pos)
            barrel_base = self._rotate_pt((15, 0), angle, pos)
            pygame.draw.line(self.surface, jam_col, barrel_base, barrel_tip, 1)

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
            outer = [self._rotate_pt(p, angle, pos) for p in ((-14,-9),(-58,0),(-14,11))]
            mid   = [self._rotate_pt(p, angle, pos) for p in ((-14,-5),(-38,0),(-14,7))]
            core  = [self._rotate_pt(p, angle, pos) for p in ((-14,-2),(-24,0),(-14,4))]
            pygame.draw.polygon(self.surface, c_outer, outer)
            pygame.draw.polygon(self.surface, c_mid,   mid)
            pygame.draw.polygon(self.surface, c_core,  core)

        if reversing:
            retro = [self._rotate_pt(p, angle, pos) for p in ((18,-2),(30,0),(18,2))]
            pygame.draw.polygon(self.surface, (200, 80, 20), retro)

    # ------------------------------------------------------------------  BARGES
    def _draw_barges(self, run_mgr, ship, t: float = 0.0):
        for barge in run_mgr.barges:
            self._draw_barge(barge, ship, t)

    def _draw_barge(self, barge, ship, t: float = 0.0):
        pos    = barge.pos
        ticks  = pygame.time.get_ticks()
        bx, by = int(pos.x), int(pos.y)

        rect = pygame.Rect(bx-30, by-16, 60, 32)
        pygame.draw.rect(self.surface, (55, 35, 0), rect, 4)
        pygame.draw.rect(self.surface, S.AMBER_TERM, rect, 2)

        # Cargo hold dividers
        for dx in (-14, 0, 14):
            pygame.draw.line(self.surface, (45, 28, 0), (bx+dx, by-14), (bx+dx, by+14), 1)
        pygame.draw.line(self.surface, (70, 44, 0), (bx-22, by), (bx+22, by), 1)

        # Engine pods (rear)
        engine_pulse = 0.55 + 0.45 * abs(math.sin(t * 4.1))
        pod_col  = _hsv(0.09, 0.9, engine_pulse)
        pod_glow = _hsv(0.09, 0.6, engine_pulse * 0.25)
        for py_off in (-10, 10):
            pcx, pcy = bx - 32, by + py_off
            pygame.draw.circle(self.surface, pod_glow, (pcx, pcy), 8)
            pygame.draw.circle(self.surface, pod_col,  (pcx, pcy), 4)
            pygame.draw.circle(self.surface, (255, 240, 200), (pcx, pcy), 2)

        # Forward sensor dome
        pygame.draw.circle(self.surface, (30, 30, 50),   (bx+32, by), 6)
        pygame.draw.circle(self.surface, (80, 80, 120),  (bx+32, by), 4, 1)
        pygame.draw.circle(self.surface, (150, 150, 200),(bx+32, by), 2)

        # Hazard lights
        blink = (ticks // 380) % 2 == 0
        for (lx, ly), on in (((bx-24, by-11), blink), ((bx+24, by+11), not blink)):
            if on:
                pygame.draw.circle(self.surface, (100, 62, 0), (lx, ly), 7)
                pygame.draw.circle(self.surface, S.AMBER_TERM,  (lx, ly), 4)
            else:
                pygame.draw.circle(self.surface, (50, 32, 0), (lx, ly), 4)

        # Tether — jagged lightning polyline
        tether = getattr(barge, "_tether", None)
        if tether and tether.is_active and ship and ship.is_alive:
            sx, sy  = int(ship.pos.x), int(ship.pos.y)
            stretch = min(1.0, math.hypot(sx-bx, sy-by) / S.TETHER_MAX_LENGTH)
            tr = int(40  + 195 * stretch)
            tg = int(200 - 165 * stretch)
            pts = [(bx, by)]
            for k in range(1, 7):
                frac = k / 7
                mx   = int(bx + (sx-bx) * frac)
                my   = int(by + (sy-by) * frac)
                jit  = int((1 - abs(frac - 0.5) * 2) * 6 * stretch)
                pts.append((mx + random.randint(-jit, jit),
                            my + random.randint(-jit, jit)))
            pts.append((sx, sy))
            pygame.draw.lines(self.surface, (min(255,tr), max(0,tg), 40), False, pts, 2)

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
