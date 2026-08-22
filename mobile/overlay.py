"""Touch HUD: drag-thrust pad, fire, and a dashboard of scene buttons."""
from __future__ import annotations

from dataclasses import dataclass

import pygame

from config import settings as S
from core.state_manager import GameState
from core.text import get_font
from mobile import virtual_input as V

_JOY_R = 118
_FIRE_R = 72
_BTN_W, _BTN_H = 132, 52
_DASH_Y = S.SCREEN_H - S.COCKPIT_H + 18


@dataclass
class DashButton:
    action: str
    label: str
    rect: pygame.Rect
    hold_key: int | None = None
    pulse_key: int | None = None
    enabled: bool = True


def _circle_hit(cx: float, cy: float, r: float, x: float, y: float) -> bool:
    dx, dy = x - cx, y - cy
    return dx * dx + dy * dy <= r * r


class TouchOverlay:
    """Maps fingers / mouse to analog thrust + dashboard pulses."""

    def __init__(self):
        self.using_fingers = False
        self._joy_finger: int | None = None
        self._joy_origin = (180.0, float(S.FLIGHT_H - 150))
        self._fire_finger: int | None = None
        self._held: dict[int, DashButton] = {}
        self._layout: str = "menu"
        self.joy_center = (180, S.FLIGHT_H - 150)
        self.fire_center = (S.SCREEN_W - 150, S.FLIGHT_H - 150)
        self.buttons: list[DashButton] = []

    # ── layout ─────────────────────────────────────────────────────────
    def sync(self, game) -> None:
        state = game._effective_state()
        self._layout = self._layout_name(game, state)
        self.buttons = self._build_buttons(game, state)

    def _layout_name(self, game, state: GameState) -> str:
        if state == GameState.FLIGHT:
            return "flight"
        if state == GameState.DELIVERY:
            delivery = game._delivery
            if delivery is None:
                return "dock"
            if getattr(delivery, "_phase", None) == getattr(delivery, "PHASE_RUN", "run"):
                return "corridor"
            return "dock"
        if state == GameState.PAUSED:
            return "paused"
        return "menu"

    def _build_buttons(self, game, state: GameState) -> list[DashButton]:
        buttons: list[DashButton] = []
        y = _DASH_Y
        if self._layout == "flight":
            ready = bool(getattr(game.run_mgr, "jump_ready", False))
            buttons.append(DashButton("pause", "PAUSE", pygame.Rect(24, y, _BTN_W, _BTN_H),
                                      pulse_key=pygame.K_ESCAPE))
            buttons.append(DashButton("jump", "JUMP" if ready else "WAIT",
                                      pygame.Rect(S.SCREEN_W // 2 - 80, y, 160, _BTN_H),
                                      pulse_key=pygame.K_j, enabled=ready))
            cargo = getattr(game.ship, "cargo", None)
            if cargo is not None and getattr(cargo, "popup_active", False):
                key = getattr(cargo, "popup_key", pygame.K_f) or pygame.K_f
                name = getattr(cargo, "popup_key_name", "FILE")
                buttons.append(DashButton("file", f"FILE {name}",
                                          pygame.Rect(S.SCREEN_W - 280, y, 150, _BTN_H),
                                          pulse_key=key))
            return buttons
        if self._layout == "corridor":
            buttons.append(DashButton("pause", "PAUSE", pygame.Rect(24, y, _BTN_W, _BTN_H),
                                      pulse_key=pygame.K_ESCAPE))
            buttons.append(DashButton("talk", "TALK", pygame.Rect(170, y, _BTN_W, _BTN_H),
                                      pulse_key=pygame.K_e))
            buttons.append(DashButton("pipe", "DOWN", pygame.Rect(316, y, _BTN_W, _BTN_H),
                                      pulse_key=pygame.K_DOWN))
            buttons.append(DashButton("jump", "JUMP",
                                      pygame.Rect(S.SCREEN_W - 320, S.FLIGHT_H - 210, 140, 64),
                                      hold_key=pygame.K_SPACE, pulse_key=pygame.K_SPACE))
            buttons.append(DashButton("sprint", "SPRINT",
                                      pygame.Rect(S.SCREEN_W - 168, S.FLIGHT_H - 210, 140, 64),
                                      hold_key=pygame.K_LSHIFT))
            return buttons
        if self._layout == "dock":
            buttons.append(DashButton("pause", "PAUSE", pygame.Rect(24, y, _BTN_W, _BTN_H),
                                      pulse_key=pygame.K_ESCAPE))
            return buttons
        if self._layout == "paused":
            return buttons
        # menus / loadout / difficulty / decant / interstitial
        buttons.append(DashButton("back", "BACK", pygame.Rect(24, y, _BTN_W, _BTN_H),
                                  pulse_key=pygame.K_ESCAPE))
        buttons.append(DashButton("confirm", "CONFIRM",
                                  pygame.Rect(S.SCREEN_W - 176, y, 152, _BTN_H),
                                  pulse_key=pygame.K_RETURN))
        if state == GameState.LOADOUT_DRAFT:
            buttons.append(DashButton("left", "<", pygame.Rect(S.SCREEN_W // 2 - 150, y, 64, _BTN_H),
                                      pulse_key=pygame.K_LEFT))
            buttons.append(DashButton("right", ">", pygame.Rect(S.SCREEN_W // 2 + 86, y, 64, _BTN_H),
                                      pulse_key=pygame.K_RIGHT))
        return buttons

    def uses_stick(self) -> bool:
        return self._layout in ("flight", "corridor", "dock")

    def uses_fire(self) -> bool:
        return self._layout == "flight"

    # ── events ─────────────────────────────────────────────────────────
    def handle_event(self, event: pygame.event.Event, display, game) -> bool:
        fdown = getattr(pygame, "FINGERDOWN", -1)
        fup = getattr(pygame, "FINGERUP", -2)
        fmove = getattr(pygame, "FINGERMOTION", -3)
        if event.type in (fdown, fup, fmove):
            self.using_fingers = True
            lx, ly = display.norm_to_logical(event.x, event.y)
            fid = int(getattr(event, "finger_id", 0))
            if event.type == fdown:
                return self._down(fid, lx, ly, game)
            if event.type == fmove:
                return self._move(fid, lx, ly)
            return self._up(fid)
        if self.using_fingers:
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            lx, ly = display.to_logical(*event.pos)
            return self._down(0, lx, ly, game)
        if event.type == pygame.MOUSEMOTION and event.buttons[0]:
            lx, ly = display.to_logical(*event.pos)
            return self._move(0, lx, ly)
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            return self._up(0)
        return False

    def _down(self, fid: int, lx: float, ly: float, game) -> bool:
        if self._hit_menu_row(lx, ly, game):
            return True
        for btn in self.buttons:
            if btn.enabled and btn.rect.collidepoint(int(lx), int(ly)):
                self._held[fid] = btn
                if btn.hold_key is not None:
                    V.hold(btn.hold_key)
                if btn.pulse_key is not None:
                    V.pulse(btn.pulse_key)
                return True
        if self.uses_fire() and _circle_hit(*self.fire_center, _FIRE_R, lx, ly):
            self._fire_finger = fid
            V.hold(pygame.K_SPACE)
            return True
        if self.uses_stick() and self._in_stick_zone(lx, ly):
            self._joy_finger = fid
            self._joy_origin = (lx, ly)
            V.set_analog(0.0, 0.0)
            return True
        return False

    def _move(self, fid: int, lx: float, ly: float) -> bool:
        if fid != self._joy_finger:
            return False
        ox, oy = self._joy_origin
        dx = (lx - ox) / _JOY_R
        dy = (oy - ly) / _JOY_R
        mag = (dx * dx + dy * dy) ** 0.5
        if mag > 1.0:
            dx, dy = dx / mag, dy / mag
        if mag < V.DEADZONE:
            dx, dy = 0.0, 0.0
        V.set_analog(dx, dy)
        return True

    def _up(self, fid: int) -> bool:
        consumed = False
        if fid == self._joy_finger:
            self._joy_finger = None
            V.set_analog(0.0, 0.0)
            consumed = True
        if fid == self._fire_finger:
            self._fire_finger = None
            V.release(pygame.K_SPACE)
            consumed = True
        btn = self._held.pop(fid, None)
        if btn is not None and btn.hold_key is not None:
            V.release(btn.hold_key)
            consumed = True
        return consumed

    def _in_stick_zone(self, lx: float, ly: float) -> bool:
        # Left half of the flight area — drag anywhere here to thrust.
        return lx < S.SCREEN_W * 0.48 and ly < S.SCREEN_H - 20

    def _hit_menu_row(self, lx: float, ly: float, game) -> bool:
        state = game.states.state
        if state == GameState.PAUSED:
            cy = S.SCREEN_H // 2 - 40
            for i in range(2):
                ry = cy + 50 + i * 36
                if abs(lx - S.SCREEN_W / 2) < 280 and ry - 4 <= ly <= ry + 32:
                    game._pause_menu_cursor = i
                    V.pulse(pygame.K_RETURN)
                    return True
            return False
        if state == GameState.DIFFICULTY_SELECT:
            cx, cy = S.SCREEN_W // 2, S.SCREEN_H // 2
            y0 = cy - 120 - 20 + 52
            for i in range(3):
                ry = y0 + i * 58
                if abs(lx - cx) < 260 and ry - 8 <= ly <= ry + 48:
                    game._diff_cursor = i
                    V.pulse(pygame.K_RETURN)
                    return True
            return False
        if state != GameState.MAIN_MENU:
            return False
        py = int(S.SCREEN_H * 0.54)
        if game._menu_mode in ("pick_new", "pick_load"):
            for i in range(S.MAX_SAVE_SLOTS):
                ry = py + 22 + i * 30
                if abs(lx - S.SCREEN_W / 2) < 320 and ry <= ly <= ry + 28:
                    game._slot_cursor = i
                    V.pulse(pygame.K_RETURN)
                    return True
            return False
        if game._menu_mode in ("confirm_overwrite", "confirm_delete_run"):
            if ly > py + 40:
                V.pulse(pygame.K_RETURN if lx < S.SCREEN_W / 2 else pygame.K_ESCAPE)
                return True
            return False
        if game._menu_mode != "main":
            return False
        rows = game._main_menu_rows()
        row_y0 = py + 20
        for i, (_label, enabled, _action) in enumerate(rows):
            ry = row_y0 + i * 32
            if abs(lx - S.SCREEN_W / 2) < 280 and ry <= ly <= ry + 30:
                game._menu_cursor = i
                if enabled:
                    V.pulse(pygame.K_RETURN)
                return True
        return False

    # ── draw ───────────────────────────────────────────────────────────
    def draw(self, surface: pygame.Surface) -> None:
        if self.uses_stick():
            self._draw_stick(surface)
        if self.uses_fire():
            self._draw_fire(surface)
        font = get_font(14, bold=True)
        for btn in self.buttons:
            self._draw_button(surface, btn, font)

    def _draw_stick(self, surface: pygame.Surface) -> None:
        cx, cy = self.joy_center
        ring = pygame.Surface((_JOY_R * 2 + 8, _JOY_R * 2 + 8), pygame.SRCALPHA)
        pygame.draw.circle(ring, (20, 40, 28, 90), (_JOY_R + 4, _JOY_R + 4), _JOY_R)
        pygame.draw.circle(ring, (0, 180, 80, 160), (_JOY_R + 4, _JOY_R + 4), _JOY_R, 2)
        pygame.draw.circle(ring, (0, 90, 50, 120), (_JOY_R + 4, _JOY_R + 4), 18, 1)
        surface.blit(ring, (cx - _JOY_R - 4, cy - _JOY_R - 4))
        ax, ay = V.get_analog()
        kx = int(cx + ax * (_JOY_R - 22))
        ky = int(cy - ay * (_JOY_R - 22))
        pygame.draw.circle(surface, (0, 220, 90), (kx, ky), 16, 2)
        hint = get_font(11).render("DRAG THRUST", True, (70, 110, 80))
        surface.blit(hint, (cx - hint.get_width() // 2, cy + _JOY_R + 6))

    def _draw_fire(self, surface: pygame.Surface) -> None:
        cx, cy = self.fire_center
        hot = self._fire_finger is not None
        col = (220, 70, 50) if hot else (180, 40, 36)
        pygame.draw.circle(surface, (40, 10, 10), (cx, cy), _FIRE_R)
        pygame.draw.circle(surface, col, (cx, cy), _FIRE_R, 3)
        label = get_font(16, bold=True).render("FIRE", True, col)
        surface.blit(label, (cx - label.get_width() // 2, cy - 10))

    def _draw_button(self, surface: pygame.Surface, btn: DashButton, font) -> None:
        r = btn.rect
        fill = (18, 28, 16, 210) if btn.enabled else (10, 10, 14, 180)
        edge = (0, 200, 80) if btn.enabled else (60, 60, 70)
        if btn.action == "jump" and btn.enabled:
            edge = (220, 200, 60)
        bg = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
        bg.fill(fill)
        surface.blit(bg, r.topleft)
        pygame.draw.rect(surface, edge, r, 2)
        txt = font.render(btn.label, True, edge)
        surface.blit(txt, (r.centerx - txt.get_width() // 2,
                           r.centery - txt.get_height() // 2))
