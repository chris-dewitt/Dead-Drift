from __future__ import annotations
import math
import pygame
from config import settings as S
from core.event_bus import bus, EVT_BAX_SPEAK, EVT_COMMS_SPEAK

_STRIP_TOP = S.SCREEN_H - S.COCKPIT_H   # y=640
_INFO_W    = 162                          # left info panel width
_SEP_X     = S.SCREEN_W - 136            # right separator before portrait
_PORT_X    = S.SCREEN_W - 132
_PORT_W    = 130
_PORT_H    = S.COCKPIT_H - 6
_BCX       = _PORT_X + _PORT_W // 2
_BCY       = _STRIP_TOP + S.COCKPIT_H // 2

# Per-speaker label + text colours
_SPEAKER_LABEL = {
    "BAX":        (255, 176,   0),   # amber
    "KRESS":      (255,  55,  30),   # angry red-orange
    "MEDI-CORP":  (  0, 185, 255),   # cold hospital blue
    "DOCK-7":     (255, 215,  40),   # invoice yellow
    "REP. LEGAL": (200,  40, 255),   # Union purple
}
_SPEAKER_TEXT = {
    "BAX":        (  0, 255,  70),
    "KRESS":      (255, 145, 110),
    "MEDI-CORP":  (155, 225, 255),
    "DOCK-7":     (255, 225, 115),
    "REP. LEGAL": (220, 155, 255),
}


def _hsv(h, s=1.0, v=1.0):
    h = h % 1.0
    if s == 0:
        c = int(v * 255); return (c, c, c)
    i = int(h * 6); f = h * 6 - i
    p, q, t = v*(1-s), v*(1-s*f), v*(1-s*(1-f))
    r, g, b = [(v,t,p),(q,v,p),(p,v,t),(p,q,v),(t,p,v),(v,p,q)][i % 6]
    return (int(r*255), int(g*255), int(b*255))


class CockpitRenderer:
    """
    Bottom strip — info panel (left) · speech (centre) · Bax portrait (right).
    Handles Bax speech and external comms (KRESS, bill collectors).
    Queues messages so nothing gets dropped.
    """

    def __init__(self, surface: pygame.Surface,
                 ship=None, run_mgr=None, meta=None):
        self.surface  = surface
        self._ship    = ship
        self._run_mgr = run_mgr
        self._meta    = meta
        self._font    = None

        # Speech state
        self._speaker = "BAX"
        self._text    = ""
        self._shown   = ""
        self._type_t  = 0.0
        self._hold_t  = 0.0
        self._state   = "idle"     # "typing" | "holding" | "idle"
        self._queue: list[tuple[str, str]] = []

        bus.subscribe(EVT_BAX_SPEAK,   self._on_bax_speak)
        bus.subscribe(EVT_COMMS_SPEAK, self._on_comms_speak)

    # ------------------------------------------------------------------
    def _on_bax_speak(self, line: str, **_):
        self._enqueue("BAX", line)

    def _on_comms_speak(self, speaker: str, line: str, **_):
        self._enqueue(speaker, line)

    def _enqueue(self, speaker: str, line: str):
        if self._state == "idle":
            self._start(speaker, line)
        else:
            self._queue.append((speaker, line))

    def _start(self, speaker: str, line: str):
        self._speaker = speaker
        self._text    = line
        self._shown   = ""
        self._type_t  = 0.0
        self._hold_t  = 0.0
        self._state   = "typing"

    def _get_font(self) -> pygame.font.Font:
        if self._font is None:
            self._font = pygame.font.SysFont("monospace", 13)
        return self._font

    # ------------------------------------------------------------------
    def update(self, dt: float):
        if self._state == "typing":
            self._type_t += dt
            n = int(self._type_t * 32)
            self._shown = self._text[:n]
            if n >= len(self._text):
                self._state  = "holding"
                self._hold_t = 0.0

        elif self._state == "holding":
            self._hold_t += dt
            if self._hold_t >= 4.0:
                self._state = "idle"
                self._shown = ""
                if self._queue:
                    spk, line = self._queue.pop(0)
                    self._start(spk, line)

    def draw(self, t: float):
        self._draw_strip()
        self._draw_info_panel()
        self._draw_speech(t)
        self._draw_bax(t)

    # ------------------------------------------------------------------  STRIP
    def _draw_strip(self):
        surf = self.surface
        pygame.draw.rect(surf, (5, 5, 13),
                         pygame.Rect(0, _STRIP_TOP, S.SCREEN_W, S.COCKPIT_H))
        pygame.draw.line(surf, S.AMBER_TERM,
                         (0, _STRIP_TOP), (S.SCREEN_W, _STRIP_TOP), 1)
        # Info panel separator
        pygame.draw.line(surf, (40, 35, 0),
                         (_INFO_W, _STRIP_TOP + 4), (_INFO_W, S.SCREEN_H - 4), 1)
        # Portrait separator
        pygame.draw.line(surf, S.GREY_DEAD,
                         (_SEP_X, _STRIP_TOP + 5), (_SEP_X, S.SCREEN_H - 5), 1)

    # ------------------------------------------------------------------  INFO PANEL
    def _draw_info_panel(self):
        surf = self.surface
        font = self._get_font()
        lh   = font.get_linesize()
        x    = 8
        y    = _STRIP_TOP + 7

        # Debt
        debt = self._meta.debt if self._meta else 0
        debt_col = (255, 55, 55) if debt > 40000 else S.AMBER_TERM
        surf.blit(font.render(f"DEBT  {debt:>9,} cr", True, debt_col), (x, y))
        y += lh + 1

        # Clone count
        clones = self._meta.clone_count if self._meta else 0
        surf.blit(font.render(f"CLONE #{clones:<3}", True, (85, 70, 10)), (x, y))
        y += lh + 1

        # Sector
        if self._run_mgr and self._run_mgr.sector is not None:
            sec = min(self._run_mgr.sector_num, S.SECTORS_PER_RUN)
            surf.blit(font.render(f"SECT  {sec}/{S.SECTORS_PER_RUN}", True, S.GREY_DEAD), (x, y))
        y += lh + 1

        # Gun status
        if self._ship and hasattr(self._ship, "gun"):
            gun = self._ship.gun
            if gun.is_jammed:
                pct = int(gun.jam_pct * 100)
                surf.blit(font.render(f"GUN   JAMMED {pct:>2}%", True, (220, 40, 40)), (x, y))
            else:
                surf.blit(font.render("GUN   READY", True, (0, 200, 60)), (x, y))

    # ------------------------------------------------------------------  SPEECH
    def _draw_speech(self, t: float):
        if not self._shown:
            return
        font    = self._get_font()
        lh      = font.get_linesize()
        lbl_col = _SPEAKER_LABEL.get(self._speaker, S.AMBER_TERM)
        txt_col = _SPEAKER_TEXT.get(self._speaker, S.GREEN_TERM)

        label   = font.render(f"{self._speaker} >", True, lbl_col)
        lbl_x   = _INFO_W + 10
        text_x  = lbl_x + label.get_width() + 8
        max_w   = _SEP_X - text_x - 10

        # Word-wrap
        lines, current = [], ""
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
        cursor  = "_" if (self._state == "typing" and int(t * 4) % 2 == 0) else ""

        surf = self.surface
        surf.blit(label, (lbl_x, base_y))
        for i, line in enumerate(lines):
            txt      = line + (cursor if i == len(lines) - 1 else "")
            rendered = font.render(txt, True, txt_col)
            surf.blit(rendered, (text_x, base_y + i * lh))

        # Subtle incoming-transmission indicator for non-Bax speakers
        if self._speaker != "BAX":
            ind_col = _SPEAKER_LABEL.get(self._speaker, S.AMBER_TERM)
            pygame.draw.rect(surf, ind_col,
                             pygame.Rect(_INFO_W + 3, _STRIP_TOP + 2, 4, S.COCKPIT_H - 4))

    # ------------------------------------------------------------------  BAX PORTRAIT
    def _draw_bax(self, t: float):
        surf   = self.surface
        port_y = _STRIP_TOP + 3
        pygame.draw.rect(surf, (5, 5, 13),
                         pygame.Rect(_PORT_X, port_y, _PORT_W, _PORT_H))
        pygame.draw.rect(surf, S.AMBER_TERM,
                         pygame.Rect(_PORT_X, port_y, _PORT_W, _PORT_H), 1)
        speaking = self._state in ("typing", "holding") and self._speaker == "BAX"
        self._draw_bax_figure(t, speaking)

    def _draw_bax_figure(self, t: float, speaking: bool):
        surf = self.surface
        cx, cy = _BCX, _BCY

        # ---- Antenna ----
        pygame.draw.line(surf, S.GREY_DEAD, (cx-2, cy-19), (cx-12, cy-32), 2)
        pygame.draw.line(surf, S.GREY_DEAD, (cx-12, cy-32), (cx-7,  cy-40), 1)
        tip_v   = 0.6 + 0.4 * abs(math.sin(t * 2.1)) if speaking else 0.25
        tip_col = _hsv(0.11, 0.9, tip_v)
        pygame.draw.circle(surf, tip_col, (cx-7, cy-41), 3)
        if speaking:
            pygame.draw.circle(surf, (255, 255, 160), (cx-7, cy-41), 1)

        # ---- Head polygon (asymmetric) ----
        head = [
            (cx-26, cy-18),   # top-left
            (cx+24, cy-20),   # top-right (raised)
            (cx+28, cy+15),   # bottom-right
            (cx-28, cy+17),   # bottom-left
            (cx-31, cy+  2),  # battle-damage dent
        ]
        pygame.draw.polygon(surf, (12, 12, 20), head)
        pygame.draw.polygon(surf, S.AMBER_TERM, head, 1)

        # ---- Ear ports ----
        for sign in (-1, 1):
            ex = cx + sign * 27
            ep = (ex - 3 if sign > 0 else ex - 3, cy - 4)
            pygame.draw.rect(surf, (25, 25, 40), (*ep, 7, 9))
            pygame.draw.rect(surf, (80, 60, 10), (*ep, 7, 9), 1)
            # Port slit detail
            pygame.draw.line(surf, (50, 38, 5),
                             (ep[0]+2, cy), (ep[0]+5, cy), 1)

        # ---- CRT scan lines ----
        for sy in range(cy-17, cy+15, 3):
            pygame.draw.line(surf, (18, 18, 28), (cx-25, sy), (cx+26, sy), 1)

        # ---- Brow ridge ----
        brow = [(cx-23, cy-12), (cx+22, cy-14), (cx+24, cy-9), (cx-21, cy-8)]
        pygame.draw.polygon(surf, (20, 18, 30), brow)
        pygame.draw.polygon(surf, (62, 48, 8),  brow, 1)

        # ---- LED forehead row ----
        led_states = [
            ((0, 210, 80)  if not speaking else (255, 200, 0)),  # status
            ((255, 110, 0)),                                       # power (always amber)
            ((0,  140, 255) if speaking else (0, 45, 95)),        # comms
        ]
        for i, led_col in enumerate(led_states):
            lx = cx - 9 + i * 10
            ly = cy - 17
            glow = tuple(max(0, c // 4) for c in led_col)
            pygame.draw.circle(surf, glow,    (lx, ly), 4)
            pygame.draw.circle(surf, led_col, (lx, ly), 2)

        # ---- Eyes ----
        eye_l = (cx-10, cy-5)
        eye_r = (cx+12, cy-7)
        if speaking:
            pygame.draw.circle(surf, (70, 44, 0), eye_l, 9)
            pygame.draw.circle(surf, (70, 44, 0), eye_r, 9)
            eye_col = (255, 205, 45)
        else:
            eye_col = (85, 55, 4)
        pygame.draw.circle(surf, eye_col, eye_l, 5)
        pygame.draw.circle(surf, eye_col, eye_r, 5)
        pygame.draw.circle(surf, (0, 0, 0), eye_l, 2)
        pygame.draw.circle(surf, (0, 0, 0), eye_r, 2)
        # Eye socket shadow ring
        pygame.draw.circle(surf, (30, 22, 4), eye_l, 7, 1)
        pygame.draw.circle(surf, (30, 22, 4), eye_r, 7, 1)

        # ---- Damage scratches ----
        pygame.draw.line(surf, (55, 42, 62), (cx+6, cy-9),  (cx+16, cy+3),  1)
        pygame.draw.line(surf, (55, 42, 62), (cx-19, cy+6), (cx-10, cy+11), 1)
        pygame.draw.line(surf, (45, 35, 52), (cx-5,  cy-2), (cx-2,  cy+5),  1)  # small chip

        # ---- Mouth ----
        mouth_y = cy + 11
        if speaking:
            for mx in range(cx-14, cx+15, 2):
                wave = int(math.sin(mx * 0.55 + t * 14) * 2)
                pygame.draw.circle(surf, S.AMBER_TERM, (mx, mouth_y + wave), 1)
        else:
            pygame.draw.line(surf, S.GREY_DEAD, (cx-14, mouth_y), (cx+14, mouth_y), 1)

        # ---- Neck ----
        pygame.draw.rect(surf, (30, 30, 40), pygame.Rect(cx-5, cy+16, 10, 5))
        pygame.draw.rect(surf, S.GREY_DEAD,  pygame.Rect(cx-5, cy+16, 10, 5), 1)

        # ---- Shoulder mounts ----
        for sx, sw, sign in ((cx-35, 14, -1), (cx+21, 14, 1)):
            pygame.draw.rect(surf, (20, 20, 30), pygame.Rect(sx, cy+16, sw, 8))
            pygame.draw.rect(surf, S.GREY_DEAD,  pygame.Rect(sx, cy+16, sw, 8), 1)
            # Connector wire from neck
            wire_x = cx + sign * 5
            pygame.draw.line(surf, (40, 40, 55),
                             (wire_x, cy+20),
                             (sx + (sw if sign > 0 else 0), cy+19), 1)
            # Shoulder indicator dot
            dot_col = (0, 160, 80) if not speaking else (200, 120, 0)
            pygame.draw.circle(surf, dot_col, (sx + sw//2, cy+20), 2)
