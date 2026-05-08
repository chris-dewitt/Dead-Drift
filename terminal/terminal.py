from __future__ import annotations
import math
import pygame
from terminal.npcs.base_npc import BaseNPC, NPCOutcome
from terminal.nlp_parser import NLPParser
from terminal.npc_portraits import draw_portrait
from core.event_bus import bus, EVT_TERMINAL_OPEN, EVT_TERMINAL_CLOSE
from config import settings as S


class Terminal:
    """
    Fallout-style NLP terminal.
    Left panel: NPC vector portrait + status bars.
    Right panel: scrolling dialogue history with typewriter reveal.
    Bottom strip: patience meter + free-text input.
    """

    _PORTRAIT_W = 360   # px wide for left panel
    _MARGIN     = 16
    _BOTTOM_H   = 82

    def __init__(self, npc: BaseNPC):
        self.npc      = npc
        self._history: list[tuple[str, str]] = []
        self._input   = ""
        self._done    = False
        self._outcome = NPCOutcome.CONTINUE

        self._cursor_visible = True
        self._cursor_timer   = 0.0

        # Typewriter — tracks the latest NPC entry being revealed
        self._tw_pos   = -1
        self._tw_chars = 0.0

        self._font:    pygame.font.Font | None = None   # 16px dialogue
        self._font_sm: pygame.font.Font | None = None   # 13px labels
        self._font_hd: pygame.font.Font | None = None   # 14px bold name tag

        bus.emit(EVT_TERMINAL_OPEN, npc=npc)
        self._push(npc.name.upper(), npc.intro())

    # ------------------------------------------------------------------
    def _get_font(self) -> pygame.font.Font:
        if self._font is None:
            self._font = pygame.font.SysFont("monospace", 17)
        return self._font

    def _get_font_sm(self) -> pygame.font.Font:
        if self._font_sm is None:
            self._font_sm = pygame.font.SysFont("monospace", 14)
        return self._font_sm

    def _get_font_hd(self) -> pygame.font.Font:
        if self._font_hd is None:
            self._font_hd = pygame.font.SysFont("monospace", 15, bold=True)
        return self._font_hd

    # ------------------------------------------------------------------
    def handle_key(self, event: pygame.event.Event):
        if self._done:
            return
        if event.key == pygame.K_ESCAPE:
            self._push("SYSTEM", "[connection terminated by user]")
            self._done    = True
            self._outcome = NPCOutcome.RELEASE
            bus.emit(EVT_TERMINAL_CLOSE, outcome=self._outcome)
        elif event.key == pygame.K_RETURN and self._input.strip():
            self._submit()
        elif event.key == pygame.K_BACKSPACE:
            self._input = self._input[:-1]
        elif event.unicode and event.unicode.isprintable():
            if len(self._input) < 78:
                self._input += event.unicode

    def _submit(self):
        player_text = self._input.strip()
        self._push("YOU", player_text)
        self._input = ""

        outcome, response = self.npc.respond(player_text)
        self._push(self.npc.name.upper(), response)
        self._outcome = outcome

        if outcome != NPCOutcome.CONTINUE:
            self._done = True
            bus.emit(EVT_TERMINAL_CLOSE, outcome=outcome)

    # ------------------------------------------------------------------
    def update(self, dt: float):
        # Cursor blink
        self._cursor_timer += dt
        if self._cursor_timer >= S.CURSOR_BLINK_MS / 1000.0:
            self._cursor_visible = not self._cursor_visible
            self._cursor_timer   = 0.0

        # Typewriter advance on latest NPC message
        if 0 <= self._tw_pos < len(self._history):
            _, text = self._history[self._tw_pos]
            self._tw_chars = min(float(len(text)),
                                 self._tw_chars + S.TYPEWRITER_SPEED * dt)

    # ------------------------------------------------------------------
    def draw(self, surface: pygame.Surface):
        surface.fill(S.BLACK)
        t      = pygame.time.get_ticks() / 1000.0
        W, H   = surface.get_size()
        M      = self._MARGIN
        PW     = self._PORTRAIT_W
        BH     = self._BOTTOM_H
        font   = self._get_font()
        font_sm = self._get_font_sm()
        font_hd = self._get_font_hd()
        lh     = font.get_linesize()

        # ── outer border ───────────────────────────────────────────────
        pygame.draw.rect(surface, S.GREEN_TERM, pygame.Rect(4, 4, W-8, H-8), 1)

        # ── portrait panel ─────────────────────────────────────────────
        p_rect = pygame.Rect(M, M, PW - M, H - BH - M * 2)
        pygame.draw.rect(surface, (6, 10, 6), p_rect)
        pygame.draw.rect(surface, (0, 80, 30), p_rect, 1)

        draw_portrait(surface, self.npc.name, p_rect, self.npc.disposition, t)

        # NPC name tag
        name_y = p_rect.bottom - 58
        surface.blit(font_hd.render(self.npc.name.upper(), True, S.AMBER_TERM),
                     (p_rect.left + 8, name_y))

        # Disposition bar
        surface.blit(font_sm.render("DISPOSITION", True, (110, 110, 110)),
                     (p_rect.left + 8, name_y + 18))
        bx = p_rect.left + 8
        bw = PW - M - 18
        by = name_y + 32
        pygame.draw.rect(surface, (28, 28, 28), pygame.Rect(bx, by, bw, 8))
        dpct = (self.npc.disposition + 10) / 20.0
        dcol = (0, 190, 70) if self.npc.disposition >= 0 else (200, 38, 38)
        pygame.draw.rect(surface, dcol, pygame.Rect(bx, by, int(bw * dpct), 8))
        pygame.draw.rect(surface, (110, 110, 110), pygame.Rect(bx, by, bw, 8), 1)

        # ── vertical divider ──────────────────────────────────────────
        div_x = PW + 6
        pygame.draw.line(surface, (0, 100, 40), (div_x, M), (div_x, H - BH - M), 1)

        # ── dialogue panel ─────────────────────────────────────────────
        dl_x  = div_x + 10
        dl_w  = W - dl_x - M
        dl_y0 = M + 6
        dl_y1 = H - BH - M

        char_w    = font.size("A")[0]
        wrap_cols = max(20, dl_w // char_w)

        all_lines: list[tuple[str, tuple]] = []
        for i, (speaker, text) in enumerate(self._history):
            display = text[:int(self._tw_chars)] if i == self._tw_pos else text
            prefix  = f"{speaker}> "
            if speaker == "YOU":
                col = S.GREEN_TERM
            elif speaker == "SYSTEM":
                col = (90, 90, 90)
            else:
                col = S.AMBER_TERM
            for line in self._wrap(prefix + display, wrap_cols):
                all_lines.append((line, col))

        max_lines = (dl_y1 - dl_y0) // lh
        visible   = all_lines[-max_lines:]
        y = dl_y0
        for line_text, col in visible:
            surface.blit(font.render(line_text, True, col), (dl_x, y))
            y += lh

        # ── bottom strip ──────────────────────────────────────────────
        strip_y = H - BH
        pygame.draw.line(surface, (0, 100, 40), (M, strip_y), (W - M, strip_y), 1)

        # Patience bar
        surface.blit(font_sm.render("PATIENCE", True, (110, 110, 110)), (M, strip_y + 7))
        pb_x = M + 76
        pb_w = 200
        pb_y = strip_y + 8
        pygame.draw.rect(surface, (28, 28, 28), pygame.Rect(pb_x, pb_y, pb_w, 10))
        ppct = self.npc._patience / max(1, self.npc.patience)
        pcol = (210, 38, 38) if ppct < 0.35 else S.AMBER_TERM
        pygame.draw.rect(surface, pcol, pygame.Rect(pb_x, pb_y, int(pb_w * ppct), 10))
        pygame.draw.rect(surface, (70, 70, 70), pygame.Rect(pb_x, pb_y, pb_w, 10), 1)

        # Hint text
        surface.blit(
            font_sm.render("try: bribe · complain · negotiate · threaten · [ESC] bail out",
                           True, (120, 120, 120)),
            (pb_x + pb_w + 14, strip_y + 9))

        # Input line
        inp_y = strip_y + 32
        pygame.draw.line(surface, (0, 60, 20), (M, inp_y - 4), (W - M, inp_y - 4), 1)
        cursor   = "_" if self._cursor_visible else " "
        inp_surf = font.render(f"> {self._input}{cursor}", True, S.GREEN_TERM)
        surface.blit(inp_surf, (M, inp_y))

        # Outcome banner when done
        if self._done:
            _OCOL = {
                NPCOutcome.RELEASE: S.GREEN_TERM,
                NPCOutcome.IMPOUND: (210, 38, 38),
                NPCOutcome.EXPLOIT: (0, 210, 255),
            }
            _OLBL = {
                NPCOutcome.RELEASE: "[ CONNECTION CLOSED — VESSEL RELEASED ]",
                NPCOutcome.IMPOUND: "[ CONNECTION CLOSED — IMPOUND AUTHORIZED ]",
                NPCOutcome.EXPLOIT: "[ SYSTEM EXPLOITED — FORCED RELEASE ]",
            }
            ocol  = _OCOL.get(self._outcome, S.AMBER_TERM)
            olbl  = _OLBL.get(self._outcome, "[ DISCONNECTED ]")
            ofont = pygame.font.SysFont("monospace", 17, bold=True)
            osurf = ofont.render(olbl, True, ocol)
            ox = W // 2 - osurf.get_width() // 2
            oy = inp_y + 4
            pygame.draw.rect(surface, S.BLACK,
                pygame.Rect(ox-8, oy-4, osurf.get_width()+16, osurf.get_height()+8))
            pygame.draw.rect(surface, ocol,
                pygame.Rect(ox-8, oy-4, osurf.get_width()+16, osurf.get_height()+8), 1)
            surface.blit(osurf, (ox, oy))

    # ------------------------------------------------------------------
    def _push(self, speaker: str, text: str):
        self._history.append((speaker, text))
        if speaker != "YOU":
            self._tw_pos   = len(self._history) - 1
            self._tw_chars = 0.0

    @staticmethod
    def _wrap(text: str, width: int) -> list[str]:
        words   = text.split()
        lines   = []
        current = ""
        for word in words:
            if len(current) + len(word) + (1 if current else 0) <= width:
                current += ("" if not current else " ") + word
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines or [""]

    @property
    def is_done(self) -> bool:
        return self._done

    @property
    def outcome(self) -> str:
        return self._outcome
