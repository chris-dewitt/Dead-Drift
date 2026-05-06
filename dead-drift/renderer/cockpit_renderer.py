from __future__ import annotations
import math
import pygame
from config import settings as S
from core.event_bus import bus, EVT_BAX_SPEAK

_STRIP_TOP  = S.SCREEN_H - S.COCKPIT_H   # y=640
_SEP_X      = S.SCREEN_W - 134           # vertical divider before portrait
_PORT_X     = S.SCREEN_W - 130           # portrait box left edge  (x=1150)
_PORT_W     = 128                        # portrait width
_PORT_H     = S.COCKPIT_H - 6           # portrait height (74px)

# Bax portrait centre — everything is drawn relative to this
_BCX = _PORT_X + _PORT_W // 2           # 1214
_BCY = _STRIP_TOP + S.COCKPIT_H // 2    # 680


class CockpitRenderer:
    """
    Bottom-strip cockpit: Bax portrait (right) + speech readout (centre-left).
    Subscribes to EVT_BAX_SPEAK; no direct ref to Bax needed.
    """

    def __init__(self, surface: pygame.Surface):
        self.surface   = surface
        self._font     = None

        self._text     = ""      # full target line
        self._shown    = ""      # chars revealed so far
        self._type_t   = 0.0    # elapsed since line started
        self._hold_t   = 0.0    # elapsed since typing finished
        self._state    = "idle"  # "typing" | "holding" | "idle"

        bus.subscribe(EVT_BAX_SPEAK, self._on_speak)

    # ------------------------------------------------------------------
    def _on_speak(self, line: str, **_):
        self._text   = line
        self._shown  = ""
        self._type_t = 0.0
        self._hold_t = 0.0
        self._state  = "typing"

    def _get_font(self) -> pygame.font.Font:
        if self._font is None:
            self._font = pygame.font.SysFont("monospace", 13)
        return self._font

    # ------------------------------------------------------------------
    def update(self, dt: float):
        if self._state == "typing":
            self._type_t += dt
            n = int(self._type_t * 30)
            self._shown = self._text[:n]
            if n >= len(self._text):
                self._state  = "holding"
                self._hold_t = 0.0

        elif self._state == "holding":
            self._hold_t += dt
            if self._hold_t >= 4.0:
                self._state = "idle"
                self._shown = ""

    def draw(self, t: float):
        self._draw_strip()
        self._draw_speech(t)
        self._draw_bax(t)

    # ------------------------------------------------------------------  STRIP
    def _draw_strip(self):
        surf = self.surface
        # Background
        pygame.draw.rect(surf, (5, 5, 13),
                         pygame.Rect(0, _STRIP_TOP, S.SCREEN_W, S.COCKPIT_H))
        # Top border — amber scanline
        pygame.draw.line(surf, S.AMBER_TERM,
                         (0, _STRIP_TOP), (S.SCREEN_W, _STRIP_TOP), 1)
        # Portrait separator
        pygame.draw.line(surf, S.GREY_DEAD,
                         (_SEP_X, _STRIP_TOP + 5), (_SEP_X, S.SCREEN_H - 5), 1)

    # ------------------------------------------------------------------  SPEECH
    def _draw_speech(self, t: float):
        if not self._shown:
            return

        font   = self._get_font()
        lh     = font.get_linesize()
        label  = font.render("BAX >", True, S.AMBER_TERM)
        lbl_x  = 16
        text_x = lbl_x + label.get_width() + 10
        max_w  = _SEP_X - text_x - 12

        # Word-wrap the revealed text
        lines   = []
        current = ""
        for word in self._shown.split(" "):
            test = (current + " " + word).strip()
            if font.size(test)[0] <= max_w:
                current = test
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)

        total_h = lh * len(lines)
        base_y  = _STRIP_TOP + (S.COCKPIT_H - total_h) // 2

        # "BAX >" label, vertically centred
        surf = self.surface
        surf.blit(label, (lbl_x, base_y))

        # Blinking cursor while typing
        cursor = "_" if (self._state == "typing" and int(t * 4) % 2 == 0) else ""

        for i, line in enumerate(lines):
            txt  = line + (cursor if i == len(lines) - 1 else "")
            rendered = font.render(txt, True, S.GREEN_TERM)
            surf.blit(rendered, (text_x, base_y + i * lh))

    # ------------------------------------------------------------------  BAX
    def _draw_bax(self, t: float):
        surf    = self.surface
        port_y  = _STRIP_TOP + 3

        # Portrait border box
        pygame.draw.rect(surf, (5, 5, 13),
                         pygame.Rect(_PORT_X, port_y, _PORT_W, _PORT_H))
        pygame.draw.rect(surf, S.AMBER_TERM,
                         pygame.Rect(_PORT_X, port_y, _PORT_W, _PORT_H), 1)

        speaking = self._state in ("typing", "holding")
        self._draw_bax_figure(t, speaking)

    def _draw_bax_figure(self, t: float, speaking: bool):
        surf = self.surface
        cx, cy = _BCX, _BCY

        # ---- Antenna (crooked, bent left) ----
        pygame.draw.line(surf, S.GREY_DEAD,
                         (cx - 2, cy - 19), (cx - 11, cy - 31), 1)
        pygame.draw.line(surf, S.GREY_DEAD,
                         (cx - 11, cy - 31), (cx - 6, cy - 38), 1)
        # Antenna tip glow
        tip_col = S.AMBER_TERM if speaking else (80, 55, 0)
        pygame.draw.circle(surf, tip_col, (cx - 6, cy - 39), 2)

        # ---- Head polygon (asymmetric, slight left dent) ----
        head = [
            (cx - 25, cy - 17),   # top-left
            (cx + 23, cy - 19),   # top-right (a touch higher)
            (cx + 27, cy + 14),   # bottom-right
            (cx - 27, cy + 16),   # bottom-left
            (cx - 30, cy +  1),   # left-side dent (battle damage)
        ]
        pygame.draw.polygon(surf, (12, 12, 20), head)      # fill
        pygame.draw.polygon(surf, S.AMBER_TERM, head, 1)   # outline

        # CRT scan lines across face
        for sy in range(cy - 16, cy + 14, 3):
            pygame.draw.line(surf, (18, 18, 28), (cx - 24, sy), (cx + 25, sy), 1)

        # ---- Eyes ----
        eye_l = (cx - 9,  cy - 5)
        eye_r = (cx + 11, cy - 7)   # right eye sits slightly higher (asymmetry)

        if speaking:
            # Soft amber glow ring behind each eye
            pygame.draw.circle(surf, (70, 44, 0), eye_l, 8)
            pygame.draw.circle(surf, (70, 44, 0), eye_r, 8)
            eye_col = (255, 200, 40)
        else:
            eye_col = (90, 58, 4)

        pygame.draw.circle(surf, eye_col, eye_l, 5)
        pygame.draw.circle(surf, eye_col, eye_r, 5)
        # Pupils
        pygame.draw.circle(surf, (0, 0, 0), eye_l, 2)
        pygame.draw.circle(surf, (0, 0, 0), eye_r, 2)

        # ---- Mouth ----
        mouth_y = cy + 10
        if speaking:
            # Ripple / talking wave
            for mx in range(cx - 13, cx + 14, 2):
                wave = int(math.sin(mx * 0.55 + t * 14) * 2)
                pygame.draw.circle(surf, S.AMBER_TERM, (mx, mouth_y + wave), 1)
        else:
            # Flat line — neutral expression
            pygame.draw.line(surf, S.GREY_DEAD,
                             (cx - 13, mouth_y), (cx + 13, mouth_y), 1)

        # ---- Neck ----
        pygame.draw.rect(surf, (30, 30, 40),
                         pygame.Rect(cx - 5, cy + 15, 10, 5))
        pygame.draw.rect(surf, S.GREY_DEAD,
                         pygame.Rect(cx - 5, cy + 15, 10, 5), 1)

        # ---- Shoulder mounts ----
        for sx, sw in ((cx - 34, 13), (cx + 21, 13)):
            pygame.draw.rect(surf, (20, 20, 30),
                             pygame.Rect(sx, cy + 15, sw, 7))
            pygame.draw.rect(surf, S.GREY_DEAD,
                             pygame.Rect(sx, cy + 15, sw, 7), 1)
