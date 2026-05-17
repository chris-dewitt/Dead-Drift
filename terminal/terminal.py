from __future__ import annotations
import pygame
from terminal.npcs.base_npc import BaseNPC, NPCOutcome
from terminal.nlp_parser import NLPParser
from core.event_bus import bus, EVT_TERMINAL_OPEN, EVT_TERMINAL_CLOSE
from config import settings as S


class Terminal:
    """
    Fallout-style NLP terminal.
    Left panel: NPC vector portrait + status bars.
    Right panel: scrolling dialogue history with typewriter reveal.
    Bottom strip: patience meter + free-text input.
    """


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
            self._font = pygame.font.SysFont("monospace", 19)
        return self._font

    def _get_font_sm(self) -> pygame.font.Font:
        if self._font_sm is None:
            self._font_sm = pygame.font.SysFont("monospace", 15)
        return self._font_sm

    def _get_font_hd(self) -> pygame.font.Font:
        if self._font_hd is None:
            self._font_hd = pygame.font.SysFont("monospace", 17, bold=True)
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
        W, H = surface.get_size()
        t    = pygame.time.get_ticks() / 1000.0
        M    = 22       # side margin
        HDR_H = 60      # header bar
        BTM_H = 100     # input area at bottom
        GAP   = 12      # vertical gap between message blocks

        font    = self._get_font()
        font_sm = self._get_font_sm()
        font_hd = self._get_font_hd()
        lh = font.get_linesize()

        # Scanline overlay — built once, reused every frame
        if not hasattr(self, '_scan_surf') or self._scan_surf.get_size() != (W, H):
            self._scan_surf = pygame.Surface((W, H), pygame.SRCALPHA)
            for sy in range(0, H, 3):
                pygame.draw.line(self._scan_surf, (0, 0, 0, 32), (0, sy), (W, sy))

        # ── Background + border ───────────────────────────────────────
        surface.fill((2, 7, 2))
        pygame.draw.rect(surface, (0, 118, 48), (2, 2, W - 4, H - 4), 1)

        # ── Header bar ───────────────────────────────────────────────
        pygame.draw.rect(surface, (4, 20, 7), (0, 0, W, HDR_H))
        pygame.draw.line(surface, (0, 140, 58), (0, HDR_H), (W, HDR_H), 1)

        fn_title = pygame.font.SysFont("monospace", 21, bold=True)
        nm = fn_title.render(f"  {self.npc.name.upper()}", True, (255, 186, 34))
        surface.blit(nm, (M, HDR_H // 2 - nm.get_height() // 2))

        # Disposition bar (centre)
        disp  = self.npc.disposition
        cx_d  = W // 2 - 90
        d_lbl = font_sm.render("DISP", True, (72, 105, 72))
        surface.blit(d_lbl, (cx_d, HDR_H // 2 - 8))
        bx = cx_d + d_lbl.get_width() + 8
        bw, bh2, by = 112, 14, HDR_H // 2 - 6
        pygame.draw.rect(surface, (14, 26, 14), (bx, by, bw, bh2))
        dpct = max(0.0, min(1.0, (disp + 10) / 20.0))
        dcol = (0, 195, 80) if disp >= 0 else (195, 46, 46)
        pygame.draw.rect(surface, dcol, (bx, by, int(bw * dpct), bh2))
        pygame.draw.rect(surface, (48, 76, 48), (bx, by, bw, bh2), 1)

        # Patience pips (right side)
        total_p = self.npc.patience
        curr_p  = self.npc._patience
        p_lbl   = font_sm.render("PATIENCE", True, (72, 105, 72))
        pip_w   = 13
        pip_gap = 3
        pip_block_w = total_p * (pip_w + pip_gap) - pip_gap
        right_x = W - M - pip_block_w - p_lbl.get_width() - 14
        surface.blit(p_lbl, (right_x, HDR_H // 2 - 8))
        px0 = right_x + p_lbl.get_width() + 10
        for i in range(total_p):
            col = (255, 145, 0) if i < curr_p else (24, 36, 24)
            rx = px0 + i * (pip_w + pip_gap)
            pygame.draw.rect(surface, col,   (rx, HDR_H // 2 - 6, pip_w, 14))
            pygame.draw.rect(surface, (52, 76, 52), (rx, HDR_H // 2 - 6, pip_w, 14), 1)

        # ── Dialogue area ─────────────────────────────────────────────
        DIAG_Y0 = HDR_H + 8
        DIAG_Y1 = H - BTM_H
        char_w    = max(1, font.size("A")[0])
        wrap_cols = max(30, (W - 2 * M - 20) // char_w)

        fn_sp = pygame.font.SysFont("monospace", 17, bold=True)

        # Build message blocks
        blocks: list[tuple[str, bool, bool, list[str]]] = []
        for i, (speaker, text) in enumerate(self._history):
            disp_text = text[:int(self._tw_chars)] if i == self._tw_pos else text
            is_npc = speaker not in ("YOU", "SYSTEM")
            is_sys = speaker == "SYSTEM"
            blocks.append((speaker, is_npc, is_sys, self._wrap(disp_text, wrap_cols)))

        def _block_h(bl: tuple) -> int:
            _, _, is_sys, wrapped = bl
            return (0 if is_sys else lh) + len(wrapped) * lh + GAP

        total_px = sum(_block_h(bl) for bl in blocks)
        avail    = DIAG_Y1 - DIAG_Y0 - 10
        y = DIAG_Y0 + 6 + max(0, avail - total_px)

        for speaker, is_npc, is_sys, wrapped in blocks:
            b_h = _block_h((speaker, is_npc, is_sys, wrapped))
            if y + b_h < DIAG_Y0:
                y += b_h
                continue
            if y >= DIAG_Y1:
                break

            if is_npc:
                # Amber left accent bar
                bar_end = min(y + b_h - GAP - 2, DIAG_Y1)
                if y < DIAG_Y1:
                    pygame.draw.line(surface, (195, 122, 0),
                                     (M + 2, max(y, DIAG_Y0)),
                                     (M + 2, bar_end), 2)
                sp = fn_sp.render(f"  [{speaker}]", True, (255, 180, 34))
                if DIAG_Y0 <= y < DIAG_Y1:
                    surface.blit(sp, (M + 8, y))
                y += lh
                for line in wrapped:
                    if DIAG_Y0 <= y < DIAG_Y1:
                        surface.blit(
                            font.render(f"    {line}", True, (205, 152, 36)),
                            (M + 8, y))
                    y += lh

            elif is_sys:
                for line in wrapped:
                    if DIAG_Y0 <= y < DIAG_Y1:
                        surface.blit(
                            font_sm.render(f"  // {line}", True, (68, 86, 68)),
                            (M, y))
                    y += lh

            else:  # YOU
                sp = fn_sp.render("[YOU]  »", True, (62, 212, 98))
                if DIAG_Y0 <= y < DIAG_Y1:
                    surface.blit(sp, (W - M - sp.get_width(), y))
                y += lh
                for line in wrapped:
                    if DIAG_Y0 <= y < DIAG_Y1:
                        surface.blit(
                            font.render(f"    {line}", True, (84, 200, 104)),
                            (M + 52, y))
                    y += lh

            y += GAP

        # ── Bottom divider ────────────────────────────────────────────
        pygame.draw.line(surface, (0, 138, 56), (0, H - BTM_H), (W, H - BTM_H), 1)

        # ── Input box ─────────────────────────────────────────────────
        inp_y    = H - BTM_H + 12
        inp_rect = pygame.Rect(M, inp_y, W - 2 * M, 36)
        pygame.draw.rect(surface, (0, 14, 4), inp_rect)
        pygame.draw.rect(surface, (0, 172, 70), inp_rect, 1)
        cursor = "█" if self._cursor_visible else " "
        surface.blit(
            font.render(f"  > {self._input}{cursor}", True, (0, 236, 94)),
            (M + 8, inp_y + 8))

        # Hints
        surface.blit(
            font_sm.render(
                "deal · bribe · threaten · negotiate · complain · [ESC] abort",
                True, (50, 98, 60)),
            (M, inp_y + 46))

        # ── Outcome banner ────────────────────────────────────────────
        if self._done:
            _OCOL = {
                NPCOutcome.RELEASE: (28, 225, 106),
                NPCOutcome.IMPOUND: (215, 38, 38),
                NPCOutcome.EXPLOIT: (28, 196, 255),
            }
            _OLBL = {
                NPCOutcome.RELEASE: "[ CONNECTION CLOSED — VESSEL RELEASED ]",
                NPCOutcome.IMPOUND: "[ IMPOUND AUTHORIZED — DO NOT RESIST ]",
                NPCOutcome.EXPLOIT: "[ SYSTEM COMPROMISED — FORCED RELEASE ]",
            }
            ocol  = _OCOL.get(self._outcome, S.AMBER_TERM)
            olbl  = _OLBL.get(self._outcome, "[ DISCONNECTED ]")
            ofont = pygame.font.SysFont("monospace", 20, bold=True)
            osurf = ofont.render(olbl, True, ocol)
            ox = W // 2 - osurf.get_width() // 2
            oy = H - BTM_H // 2 - osurf.get_height() // 2
            pygame.draw.rect(surface, (0, 0, 0),
                (ox - 14, oy - 7, osurf.get_width() + 28, osurf.get_height() + 14))
            pygame.draw.rect(surface, ocol,
                (ox - 14, oy - 7, osurf.get_width() + 28, osurf.get_height() + 14), 1)
            surface.blit(osurf, (ox, oy))

        # ── Scanlines on top ─────────────────────────────────────────
        surface.blit(self._scan_surf, (0, 0))

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
