from __future__ import annotations
import random
import pygame
from core.text import get_font
from config import settings as S
from ship.ship import PlayerShip


class HUD:
    """
    Diegetic HUD — its visual fidelity is directly tied to hull integrity.

    > 60 HP : full color, stable
    40–60   : flickering, occasional frame drop
    20–40   : desaturated, color drains
    < 20    : vector tracking scrambled, elements randomly offset
    """

    def __init__(self, ship: PlayerShip):
        self.ship       = ship
        self._font      = None   # lazy init after pygame.init()
        self._glitch_t  = 0.0
        self._offset    = (0, 0)

    def _get_font(self) -> pygame.font.Font:
        if self._font is None:
            self._font = get_font(14)
        return self._font

    # ------------------------------------------------------------------
    def update(self, dt: float):
        self._glitch_t += dt
        hp = self.ship.hull

        if hp < S.HUD_SCRAMBLE_HP:
            if random.random() < 0.3:
                self._offset = (random.randint(-4, 4), random.randint(-4, 4))
        else:
            self._offset = (0, 0)

    def draw(self, surface: pygame.Surface, snap_charge: float | None = None):
        hp  = self.ship.hull
        font = self._get_font()

        # Flicker: skip drawing occasionally when hull is low
        if hp < S.HUD_FLICKER_HP and random.random() < 0.08:
            return

        ox, oy = self._offset

        # Hull bar
        self._draw_hull_bar(surface, ox, oy)

        # Velocity readout
        speed = self.ship.body.speed()
        vel_text = font.render(f"VEL  {speed:>6.1f} m/s", True, self._tint(S.GREEN_TERM))
        surface.blit(vel_text, (20 + ox, 60 + oy))

        # Angle readout
        angle_text = font.render(f"HDG  {self.ship.angle:>5.1f}°", True, self._tint(S.GREEN_TERM))
        surface.blit(angle_text, (20 + ox, 80 + oy))

        # Cargo status
        cargo = self.ship.cargo
        cargo_label = cargo.name if cargo else "NO CARGO"
        cargo_color = S.AMBER_TERM if cargo and cargo.is_damaged else S.GREEN_TERM
        cargo_text = font.render(f"CARGO  {cargo_label}", True, self._tint(cargo_color))
        surface.blit(cargo_text, (20 + ox, 100 + oy))

        self._draw_thruster_heat(surface, ox, oy)
        self._draw_snap_charge(surface, ox, oy, snap_charge)
        self._draw_fuel_bar(surface, ox, oy)

    def _draw_hull_bar(self, surface: pygame.Surface, ox: int, oy: int):
        font     = self._get_font()
        bar_w    = 200
        bar_h    = 12
        filled   = int(bar_w * self.ship.hull_pct)
        color    = self._hull_color()

        label = font.render(f"HULL  {self.ship.hull:>5.1f}", True, self._tint(color))
        surface.blit(label, (20 + ox, 20 + oy))

        bar_rect   = pygame.Rect(20 + ox, 38 + oy, bar_w, bar_h)
        fill_rect  = pygame.Rect(20 + ox, 38 + oy, filled, bar_h)
        pygame.draw.rect(surface, S.GREY_DEAD, bar_rect, 1)
        pygame.draw.rect(surface, color, fill_rect)

    def _draw_thruster_heat(self, surface: pygame.Surface, ox: int, oy: int):
        thruster = self._primary_thruster()
        if thruster is None:
            return
        font = self._get_font()
        heat = max(0.0, min(100.0, getattr(thruster, "heat", 0.0)))
        overheated = bool(getattr(thruster, "overheated", False))
        if overheated:
            color = S.RED_WARN
            status = "OVR"
        elif heat >= 70.0:
            color = S.AMBER_TERM
            status = "HOT"
        else:
            color = S.GREEN_TERM
            status = "OK "

        label = font.render(f"THRST {heat:>5.1f}C {status}", True, self._tint(color))
        surface.blit(label, (20 + ox, 124 + oy))

        bar_w, bar_h = 200, 8
        bar_rect = pygame.Rect(20 + ox, 142 + oy, bar_w, bar_h)
        fill_rect = pygame.Rect(20 + ox, 142 + oy, int(bar_w * heat / 100.0), bar_h)
        pygame.draw.rect(surface, S.GREY_DEAD, bar_rect, 1)
        pygame.draw.rect(surface, color, fill_rect)

    def _primary_thruster(self):
        chain = getattr(self.ship, "chain", None)
        slots = getattr(chain, "slots", [])
        for module in slots:
            if module is not None and "propulsion" in getattr(module, "tags", []):
                return module
        return None

    def _draw_snap_charge(self, surface: pygame.Surface, ox: int, oy: int,
                          snap_charge: float | None):
        if snap_charge is None:
            return
        pct = max(0.0, min(1.0, snap_charge))
        font = self._get_font()
        color = self._snap_color(pct)

        label = font.render(f"SNAP CHARGE {pct * 100:>3.0f}%", True, self._tint(color))
        surface.blit(label, (20 + ox, 156 + oy))

        bar_w, bar_h = 200, 8
        bar_rect = pygame.Rect(20 + ox, 174 + oy, bar_w, bar_h)
        fill_rect = pygame.Rect(20 + ox, 174 + oy, int(bar_w * pct), bar_h)
        pygame.draw.rect(surface, S.GREY_DEAD, bar_rect, 1)
        pygame.draw.rect(surface, self._tint(color), fill_rect)

    def _draw_fuel_bar(self, surface: pygame.Surface, ox: int, oy: int):
        fuel = getattr(self.ship, "fuel", None)
        if fuel is None:
            return
        font = self._get_font()
        pct = max(0.0, min(1.0, fuel / S.FUEL_MAX))
        if pct > 0.5:
            color = S.GREEN_TERM
        elif pct > 0.25:
            color = S.AMBER_TERM
        else:
            color = S.RED_WARN

        label = font.render(f"FUEL  {fuel:>5.1f}%", True, self._tint(color))
        surface.blit(label, (20 + ox, 188 + oy))

        bar_w, bar_h = 200, 8
        bar_rect  = pygame.Rect(20 + ox, 206 + oy, bar_w, bar_h)
        fill_rect = pygame.Rect(20 + ox, 206 + oy, int(bar_w * pct), bar_h)
        pygame.draw.rect(surface, S.GREY_DEAD, bar_rect, 1)
        pygame.draw.rect(surface, self._tint(color), fill_rect)

    def _snap_color(self, pct: float) -> tuple:
        if pct >= 0.95:
            return S.GREEN_TERM
        if pct >= 0.50:
            return S.AMBER_TERM
        return S.RED_WARN

    def _hull_color(self) -> tuple:
        hp = self.ship.hull
        if hp > S.HUD_FLICKER_HP:    return S.GREEN_TERM
        if hp > S.HUD_DESATURATE_HP: return S.AMBER_TERM
        return S.RED_WARN

    def _tint(self, color: tuple) -> tuple:
        """Desaturate color proportionally when hull is low."""
        hp = self.ship.hull
        if hp > S.HUD_DESATURATE_HP:
            return color
        t   = 1.0 - (hp / S.HUD_DESATURATE_HP)
        grey = int(0.299 * color[0] + 0.587 * color[1] + 0.114 * color[2])
        r   = int(color[0] + (grey - color[0]) * t)
        g   = int(color[1] + (grey - color[1]) * t)
        b   = int(color[2] + (grey - color[2]) * t)
        return (r, g, b)
