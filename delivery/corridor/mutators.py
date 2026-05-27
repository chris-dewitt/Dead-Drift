"""
Aliveness G.9 / G.10 — Cargo-affects-corridor mutators + time-pressure variant.

Each mutator is a corridor overlay that activates based on ``cargo.tag``.
The shared ``CorridorMutator`` ABC is the integration point:

    mutator = get_corridor_mutator(cargo)
    ...
    mutator.update(dt, t)
    mutator.draw_overlay(surf, t, cam_x, player_x, player_y)

G.9 ships three cargo-based overlays:
  - ShroomsMutator    — walls breathe and warp; per-room shader pulse
  - BiohazardMutator  — periodic decon flash every 12-18s, visibility loss
  - PaperworkMutator  — misleading exit signs + dead-end door markings

G.10 ships one difficulty overlay:
  - TimePressureMutator — visible gas/countdown, forces speed over exploration
"""
from __future__ import annotations
import math
import random
import pygame

from core.text import get_font
from core.event_bus import bus, EVT_BAX_SPEAK
from delivery.corridor.elements import CORRIDOR_W, CORRIDOR_H, FLOOR_Y, CEIL_Y


class CorridorMutator:
    """ABC for corridor overlays. All methods have safe no-op defaults."""

    def update(self, dt: float, t: float) -> None:
        pass

    def draw_overlay(self, surf: pygame.Surface, t: float,
                     cam_x: float, player_x: float, player_y: float) -> None:
        pass

    def danger_active(self) -> bool:
        """True when the player should take damage from the mutator effect."""
        return False


# ── G.9a — Shrooms mutator ───────────────────────────────────────────────────

class ShroomsMutator(CorridorMutator):
    """Walls breathe; per-room warp pulse. Cosmetic only — no damage."""

    def __init__(self):
        self._pulse = 0.0

    def update(self, dt: float, t: float) -> None:
        self._pulse = t  # just alias time for sinusoidal effects

    def draw_overlay(self, surf: pygame.Surface, t: float,
                     cam_x: float, player_x: float, player_y: float) -> None:
        # Wall-breathe overlay: SRCALPHA green shimmer that pulses in scale
        w_pulse = 0.5 + 0.5 * math.sin(t * 1.4)
        c_pulse = 0.5 + 0.5 * math.sin(t * 0.9 + 1.1)

        # Ceiling shimmer
        ceil_surf = pygame.Surface((CORRIDOR_W, 14), pygame.SRCALPHA)
        ceil_surf.fill((0, int(80 * w_pulse), int(40 * w_pulse), int(38 * w_pulse)))
        surf.blit(ceil_surf, (0, CEIL_Y))

        # Floor shimmer
        floor_surf = pygame.Surface((CORRIDOR_W, 14), pygame.SRCALPHA)
        floor_surf.fill((int(20 * c_pulse), int(60 * c_pulse), 0, int(32 * c_pulse)))
        surf.blit(floor_surf, (0, FLOOR_Y - 2))

        # Spore particles drifting upward
        rng = random.Random(int(t * 4))
        for _ in range(8):
            px = rng.randint(0, CORRIDOR_W)
            py = FLOOR_Y - int((t * 22 + rng.randint(0, CORRIDOR_H)) % (FLOOR_Y - CEIL_Y))
            r  = rng.randint(1, 3)
            a  = rng.randint(40, 120)
            sp = pygame.Surface((r * 2 + 2, r * 2 + 2), pygame.SRCALPHA)
            pygame.draw.circle(sp, (80, 200, 60, a), (r + 1, r + 1), r)
            surf.blit(sp, (px - r, py - r))

        # Warp distortion band — horizontal shear of a thin strip
        warp_y = int(CEIL_Y + (FLOOR_Y - CEIL_Y) * (0.4 + 0.3 * math.sin(t * 0.7)))
        warp_h = 6
        if 0 <= warp_y < CORRIDOR_H - warp_h:
            strip = surf.subsurface((0, warp_y, CORRIDOR_W, warp_h)).copy()
            offset = int(4 * math.sin(t * 2.3))
            surf.blit(strip, (offset, warp_y))


# ── G.9b — Biohazard mutator ─────────────────────────────────────────────────

class BiohazardMutator(CorridorMutator):
    """Periodic decon flash every 12-18s. Brief white-out + siren-style lines."""

    _DECON_WARN  = 1.2   # warning phase (amber pulse)
    _DECON_FLASH = 0.4   # white flash
    _DECON_CLEAR = 0.8   # fade out

    def __init__(self):
        self._next_decon = random.uniform(8.0, 14.0)
        self._decon_t    = -1.0   # -1 = not active
        self._bax_fired  = False

    def update(self, dt: float, t: float) -> None:
        if self._decon_t >= 0:
            self._decon_t += dt
            if self._decon_t >= self._DECON_WARN + self._DECON_FLASH + self._DECON_CLEAR:
                self._decon_t    = -1.0
                self._bax_fired  = False
        else:
            self._next_decon -= dt
            if self._next_decon <= 0:
                self._decon_t    = 0.0
                self._next_decon = random.uniform(12.0, 18.0)
                self._bax_fired  = False

    def danger_active(self) -> bool:
        return (0 <= self._decon_t < self._DECON_WARN + self._DECON_FLASH)

    def draw_overlay(self, surf: pygame.Surface, t: float,
                     cam_x: float, player_x: float, player_y: float) -> None:
        if self._decon_t < 0:
            # Ambient: faint biohazard stripe on ceiling every 120px
            f = get_font(7, bold=True)
            strip_off = int(cam_x * 0.6) % 120
            for bx in range(-strip_off, CORRIDOR_W + 120, 120):
                lbl = f.render("☣ BIOHAZARD", True, (60, 0, 0))
                surf.blit(lbl, (bx, CEIL_Y + 2))
            return

        dt_phase = self._decon_t

        if dt_phase < self._DECON_WARN:
            # Warning: amber pulsing stripes
            frac    = dt_phase / self._DECON_WARN
            alpha   = int(80 + 120 * math.sin(frac * math.pi * 6))
            warn    = pygame.Surface((CORRIDOR_W, CORRIDOR_H), pygame.SRCALPHA)
            warn.fill((180, 120, 0, max(0, min(220, alpha))))
            surf.blit(warn, (0, 0))
            f = get_font(18, bold=True)
            lbl = f.render("AUTOMATED DECON  —  BRACE", True, (255, 200, 0))
            surf.blit(lbl, (CORRIDOR_W // 2 - lbl.get_width() // 2, CORRIDOR_H // 2 - 12))
            if not self._bax_fired and frac > 0.3:
                self._bax_fired = True
                bus.emit(EVT_BAX_SPEAK,
                         line="Brace — automated decon cycle. Eyes down, courier.")

        elif dt_phase < self._DECON_WARN + self._DECON_FLASH:
            # Flash: full white
            fade = min(1.0, (dt_phase - self._DECON_WARN) / self._DECON_FLASH)
            alpha = int(255 * (1.0 - fade))
            fl = pygame.Surface((CORRIDOR_W, CORRIDOR_H), pygame.SRCALPHA)
            fl.fill((255, 255, 255, alpha))
            surf.blit(fl, (0, 0))

        else:
            # Clear: fading green mist
            frac  = (dt_phase - self._DECON_WARN - self._DECON_FLASH) / self._DECON_CLEAR
            alpha = int(90 * (1.0 - frac))
            mist  = pygame.Surface((CORRIDOR_W, CORRIDOR_H), pygame.SRCALPHA)
            mist.fill((0, 180, 60, alpha))
            surf.blit(mist, (0, 0))


# ── G.9c — Paperwork mutator ─────────────────────────────────────────────────

class PaperworkMutator(CorridorMutator):
    """Misleading exit signs and dead-end door markings."""

    _SIGNS = [
        ("EXIT →",    True),   # points wrong way
        ("EXIT ←",    False),
        ("NO EXIT",   None),
        ("→ SECURE",  True),
        ("AUTHORISED ONLY →", True),
        ("← CLEARANCE REQUIRED", False),
        ("PROCESSING →", True),
        ("← RECORDS", False),
    ]

    def __init__(self):
        rng = random.Random(42)
        self._sign_positions = [
            (rng.randint(80, CORRIDOR_W - 80), rng.choice(self._SIGNS))
            for _ in range(6)
        ]

    def draw_overlay(self, surf: pygame.Surface, t: float,
                     cam_x: float, player_x: float, player_y: float) -> None:
        f = get_font(8, bold=True)
        for world_x, (text, flipped) in self._sign_positions:
            sx = int(world_x - cam_x)
            if abs(sx) > CORRIDOR_W:
                continue
            # Sign panel
            lbl  = f.render(text, True, (160, 160, 80))
            pw   = lbl.get_width() + 12
            ph   = 14
            sign = pygame.Surface((pw, ph), pygame.SRCALPHA)
            sign.fill((20, 20, 8, 200))
            pygame.draw.rect(sign, (120, 120, 40), (0, 0, pw, ph), 1)
            sign.blit(lbl, (6, 2))
            surf.blit(sign, (sx - pw // 2, CEIL_Y + 20))

        # Bureaucratic stamp overlay on walls — faint "VOID" / "REJECTED"
        rng2 = random.Random(int(cam_x / 60))
        for _ in range(3):
            stamp_x = rng2.randint(0, CORRIDOR_W - 60)
            stamp_y = rng2.randint(CEIL_Y + 30, FLOOR_Y - 30)
            ang     = rng2.choice([-15, 15, -8, 8])
            words   = ["VOID", "REJECTED", "REFER TO FORM 12", "PENDING REVIEW"]
            word    = words[rng2.randint(0, len(words) - 1)]
            f_stamp = get_font(10, bold=True)
            st      = f_stamp.render(word, True, (80, 80, 20))
            rot     = pygame.transform.rotate(st, ang)
            ro      = pygame.Surface(rot.get_size(), pygame.SRCALPHA)
            ro.blit(rot, (0, 0))
            ro.set_alpha(55)
            surf.blit(ro, (stamp_x, stamp_y))


# ── G.10 — Time pressure mutator ─────────────────────────────────────────────

class TimePressureMutator(CorridorMutator):
    """Visible countdown + gas-seep effect. Forces speed over exploration.

    ``time_limit`` seconds before the corridor is considered failed.
    The corridor checks ``self.is_expired()`` to trigger a death/restart.
    """

    _GAS_START_AT   = 0.60   # fraction of time remaining when gas begins visually
    _DAMAGE_START   = 0.30   # fraction remaining when gas starts dealing damage

    def __init__(self, time_limit: float = 45.0):
        self._time_limit = time_limit
        self._elapsed    = 0.0
        self._bax_warned = False

    def update(self, dt: float, t: float) -> None:
        self._elapsed += dt
        remaining_frac = 1.0 - (self._elapsed / self._time_limit)
        if not self._bax_warned and remaining_frac < 0.40:
            self._bax_warned = True
            bus.emit(EVT_BAX_SPEAK,
                     line="Corridor's sealing. "
                          "Whatever they're flooding in — you don't want to breathe it. GO.")

    def danger_active(self) -> bool:
        return (1.0 - (self._elapsed / self._time_limit)) < self._DAMAGE_START

    def is_expired(self) -> bool:
        return self._elapsed >= self._time_limit

    def time_remaining(self) -> float:
        return max(0.0, self._time_limit - self._elapsed)

    def draw_overlay(self, surf: pygame.Surface, t: float,
                     cam_x: float, player_x: float, player_y: float) -> None:
        remaining_frac = 1.0 - (self._elapsed / self._time_limit)

        # Gas seep from floor once below threshold
        if remaining_frac < self._GAS_START_AT:
            gas_depth = int((self._GAS_START_AT - remaining_frac)
                           / self._GAS_START_AT * 80)
            gas_depth = min(80, gas_depth)
            gas_alpha = min(160, gas_depth * 2)
            gas_col   = (0, 180, 40, gas_alpha) if remaining_frac > self._DAMAGE_START \
                        else (180, 60, 0, gas_alpha)
            gas = pygame.Surface((CORRIDOR_W, gas_depth + 10), pygame.SRCALPHA)
            for gy in range(gas_depth + 10):
                row_a = int(gas_alpha * (1.0 - gy / (gas_depth + 10)))
                row_a += int(20 * math.sin(t * 2.1 + gy * 0.3))
                row_a = max(0, min(255, row_a))
                pygame.draw.line(gas, (*gas_col[:3], row_a),
                                 (0, gy), (CORRIDOR_W, gy))
            surf.blit(gas, (0, FLOOR_Y - gas_depth - 10))

        # HUD countdown in corner
        secs  = self.time_remaining()
        f_hud = get_font(14, bold=True)
        col   = (0, 220, 80) if secs > 20 else \
                (255, 180, 0) if secs > 10 else (220, 40, 40)
        lbl   = f_hud.render(f"SEAL IN  {secs:.0f}s", True, col)
        hud   = pygame.Surface((lbl.get_width() + 16, lbl.get_height() + 8),
                               pygame.SRCALPHA)
        hud.fill((0, 0, 0, 160))
        pygame.draw.rect(hud, col, (0, 0, hud.get_width(), hud.get_height()), 1)
        hud.blit(lbl, (8, 4))
        surf.blit(hud, (8, CEIL_Y + 8))

        # Flicker warning at low time
        if secs < 8.0 and int(t * 4) % 2 == 0:
            warn = pygame.Surface((CORRIDOR_W, CORRIDOR_H), pygame.SRCALPHA)
            warn.fill((180, 30, 0, 30))
            surf.blit(warn, (0, 0))


# ── Factory ───────────────────────────────────────────────────────────────────

def get_corridor_mutator(cargo, force_time_pressure: bool = False) -> CorridorMutator:
    """Return the appropriate mutator for the current cargo, or a no-op."""
    if force_time_pressure:
        return TimePressureMutator()
    if cargo is None:
        return CorridorMutator()
    tag = type(cargo).__name__
    if tag == "EpistemologicalShrooms":
        return ShroomsMutator()
    if tag in ("BiohazardCrate", "BiohazardSample"):
        return BiohazardMutator()
    if tag == "SentientPaperwork":
        return PaperworkMutator()
    return CorridorMutator()
