from __future__ import annotations
import math
import pygame
from terminal.npcs.base_npc import BaseNPC, NPCOutcome
from terminal.nlp_parser import NLPParser
from terminal.npc_portraits import draw_portrait
from core.event_bus import bus, EVT_TERMINAL_OPEN, EVT_TERMINAL_CLOSE
from config import settings as S


# NPC-specific hint tables — shown at bottom of terminal
_NPC_HINTS = {
    "GARY":       "deal · bribe ≥3k · sympathy · blevins · article 7 · [ESC] abort",
    "TK-9":       "paradox×2 · sql inject · formal statute · override · friendship · emp.month · [ESC] abort",
    "DISPATCHER": "coffee/break · forms×3 · 42 · quantum+legal · grievance×3 · bribe ≥10k · [ESC] abort",
    "KRESS":      "intel · contraband · volkov · connie · be friendly×3 · [ESC] abort",
}

_OUTCOME_COLOR = {
    NPCOutcome.RELEASE: (28, 225, 106),
    NPCOutcome.IMPOUND: (215, 38, 38),
    NPCOutcome.EXPLOIT: (0, 210, 255),
}
_OUTCOME_LABEL = {
    NPCOutcome.RELEASE: "NEGOTIATION SUCCESSFUL — VESSEL RELEASED",
    NPCOutcome.IMPOUND: "IMPOUND AUTHORIZED — DO NOT RESIST",
    NPCOutcome.EXPLOIT: "EXPLOIT CONFIRMED — SYSTEM COMPROMISED",
}


class Terminal:
    """
    NLP terminal — left panel portrait, right panel dialogue, bottom input.

    Visual features:
    - Disposition delta flash (+N / -N) appears at the bar when disposition changes
    - Patience pips go red when 2 or fewer remain
    - EXPLOIT outcome gets a special cyan banner vs green for RELEASE
    - NPC-specific hint text in the input strip
    - "MOMENTUM POSITIVE" label when disposition ≥ 3
    """

    def __init__(self, npc: BaseNPC):
        self.npc      = npc
        self._history: list[tuple[str, str]] = []
        self._input   = ""
        self._done    = False
        self._outcome = NPCOutcome.CONTINUE

        self._cursor_visible = True
        self._cursor_timer   = 0.0

        # Typewriter
        self._tw_pos   = -1
        self._tw_chars = 0.0

        # Disposition delta flash
        self._disp_flash: tuple[int, float] | None = None   # (delta, timestamp)

        # Exploit flash (timestamp or None)
        self._exploit_flash: float | None = None

        self._font:    pygame.font.Font | None = None
        self._font_sm: pygame.font.Font | None = None
        self._font_hd: pygame.font.Font | None = None

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

        disp_before = self.npc.disposition
        outcome, response = self.npc.respond(player_text)
        disp_after  = self.npc.disposition

        delta = disp_after - disp_before
        if delta != 0:
            now = pygame.time.get_ticks() / 1000.0
            self._disp_flash = (delta, now)

        if outcome in (NPCOutcome.EXPLOIT, NPCOutcome.RELEASE):
            self._exploit_flash = pygame.time.get_ticks() / 1000.0

        self._push(self.npc.name.upper(), response)
        self._outcome = outcome

        if outcome != NPCOutcome.CONTINUE:
            self._done = True
            bus.emit(EVT_TERMINAL_CLOSE, outcome=outcome)

    # ------------------------------------------------------------------
    def update(self, dt: float):
        self._cursor_timer += dt
        if self._cursor_timer >= S.CURSOR_BLINK_MS / 1000.0:
            self._cursor_visible = not self._cursor_visible
            self._cursor_timer   = 0.0

        if 0 <= self._tw_pos < len(self._history):
            _, text = self._history[self._tw_pos]
            self._tw_chars = min(float(len(text)),
                                 self._tw_chars + S.TYPEWRITER_SPEED * dt)

    # ------------------------------------------------------------------
    def draw(self, surface: pygame.Surface):
        W, H = surface.get_size()
        t    = pygame.time.get_ticks() / 1000.0
        M    = 18
        HDR_H = 74        # taller header for delta-flash row
        BTM_H = 108
        PNL_W = 290
        GAP   = 12

        font    = self._get_font()
        font_sm = self._get_font_sm()
        font_hd = self._get_font_hd()
        lh = font.get_linesize()

        # Scanline overlay
        if not hasattr(self, '_scan_surf') or self._scan_surf.get_size() != (W, H):
            self._scan_surf = pygame.Surface((W, H), pygame.SRCALPHA)
            for sy in range(0, H, 3):
                pygame.draw.line(self._scan_surf, (0, 0, 0, 30), (0, sy), (W, sy))

        # ── Background + outer border ─────────────────────────────────
        surface.fill((2, 7, 2))
        pygame.draw.rect(surface, (0, 118, 48), (2, 2, W - 4, H - 4), 1)

        # ── Header bar ────────────────────────────────────────────────
        pygame.draw.rect(surface, (4, 20, 7), (0, 0, W, HDR_H))
        pygame.draw.line(surface, (0, 140, 58), (0, HDR_H), (W, HDR_H), 1)

        # Header has two rows: top = name/disposition/patience, bottom = delta/warnings
        ROW1_Y = 18
        ROW2_Y = 50

        fn_title = pygame.font.SysFont("monospace", 19, bold=True)
        nm = fn_title.render(self.npc.name.upper(), True, (255, 186, 34))
        surface.blit(nm, (M, ROW1_Y - nm.get_height() // 2 + 7))

        # ── Disposition bar (centred) ─────────────────────────────────
        disp  = self.npc.disposition
        d_lbl = font_sm.render("DISP", True, (72, 105, 72))
        bw, bh2 = 130, 12
        bar_total_w = d_lbl.get_width() + 8 + bw
        bar_left = (W - bar_total_w) // 2
        surface.blit(d_lbl, (bar_left, ROW1_Y - 8))
        bx = bar_left + d_lbl.get_width() + 8
        by = ROW1_Y - bh2 // 2

        pygame.draw.rect(surface, (14, 26, 14), (bx, by, bw, bh2))
        dpct = max(0.0, min(1.0, (disp + 10) / 20.0))

        if disp >= 4:
            dcol = (0, 235, 100)
        elif disp >= 1:
            dcol = (0, 195, 80)
        elif disp == 0:
            dcol = (180, 140, 0)
        elif disp >= -3:
            dcol = (195, 100, 0)
        else:
            dcol = (195, 46, 46)

        pygame.draw.rect(surface, dcol, (bx, by, int(bw * dpct), bh2))
        pygame.draw.rect(surface, (48, 76, 48), (bx, by, bw, bh2), 1)
        # Centre tick
        cx_tick = bx + bw // 2
        pygame.draw.line(surface, (90, 110, 90), (cx_tick, by - 2), (cx_tick, by + bh2 + 2), 1)

        # ── Patience pips (right) ─────────────────────────────────────
        total_p = self.npc.patience
        curr_p  = self.npc._patience
        p_lbl   = font_sm.render("PATIENCE", True, (72, 105, 72))
        pip_w, pip_gap = 10, 3
        pip_block_w = total_p * (pip_w + pip_gap) - pip_gap
        right_x = W - M - pip_block_w - p_lbl.get_width() - 12
        surface.blit(p_lbl, (right_x, ROW1_Y - 8))
        px0 = right_x + p_lbl.get_width() + 10
        for i in range(total_p):
            active = i < curr_p
            if active:
                if curr_p <= 2:
                    pulse = int(180 + 75 * math.sin(t * 4.0))
                    col = (pulse, max(0, pulse - 140), 0)
                else:
                    col = (255, 145, 0)
            else:
                col = (22, 34, 22)
            rx = px0 + i * (pip_w + pip_gap)
            pygame.draw.rect(surface, col, (rx, ROW1_Y - 6, pip_w, 12))
            pygame.draw.rect(surface, (50, 76, 50), (rx, ROW1_Y - 6, pip_w, 12), 1)

        # ── ROW 2 — momentum / delta / patience warning ───────────────
        # MOMENTUM (left of disp bar)
        if disp >= 3:
            pulse = int(200 + 55 * math.sin(t * 3.0))
            mom_col = (0, pulse, int(pulse * 0.4))
            mom = font_sm.render("MOMENTUM +", True, mom_col)
            surface.blit(mom, (bar_left + bar_total_w + 12, ROW1_Y - 7))

        # Disposition delta flash — in row 2, directly under bar
        if self._disp_flash is not None:
            delta, flash_t = self._disp_flash
            age = t - flash_t
            if age < 1.8:
                sign = "+" if delta > 0 else ""
                col  = (0, 230, 100) if delta > 0 else (230, 60, 60)
                fs   = pygame.font.SysFont("monospace", 16, bold=True)
                ds   = fs.render(f"{sign}{delta} DISP", True, col)
                drift_y = int(age * 14)
                surface.blit(ds, (bx + bw // 2 - ds.get_width() // 2,
                                  ROW2_Y - 4 - drift_y))
            else:
                self._disp_flash = None

        # Low patience warning — under patience pips
        if 0 < curr_p <= 2:
            warn = font_sm.render(
                f"!! {curr_p} TURN{'S' if curr_p > 1 else ''} LEFT !!",
                True, (220, 60, 60))
            surface.blit(warn, (right_x + (pip_block_w + p_lbl.get_width() + 10 - warn.get_width()) // 2,
                                ROW2_Y - 6))

        # ── Portrait panel ────────────────────────────────────────────
        p_rect = pygame.Rect(M, HDR_H + 4, PNL_W - M - 4, H - BTM_H - HDR_H - 8)
        pygame.draw.rect(surface, (4, 12, 4), p_rect)
        pygame.draw.rect(surface, (0, 80, 34), p_rect, 1)

        draw_portrait(surface, self.npc.name, p_rect, self.npc.disposition, t)

        if not hasattr(self, '_p_scan') or self._p_scan.get_size() != (p_rect.w, p_rect.h):
            self._p_scan = pygame.Surface((p_rect.w, p_rect.h), pygame.SRCALPHA)
            for sy in range(0, p_rect.h, 2):
                pygame.draw.line(self._p_scan, (0, 0, 0, 50), (0, sy), (p_rect.w, sy))
        surface.blit(self._p_scan, p_rect.topleft)

        sig_col = (50, 90, 50) if int(t * 2) % 3 != 0 else (80, 130, 80)
        sig_surf = font_sm.render("COMM  ·  SIGNAL: DEGRADED", True, sig_col)
        surface.blit(sig_surf, (p_rect.left + 4, p_rect.bottom - sig_surf.get_height() - 4))

        # ── Vertical divider ──────────────────────────────────────────
        div_x = PNL_W + 2
        pygame.draw.line(surface, (0, 100, 42), (div_x, HDR_H + 2), (div_x, H - BTM_H - 2), 1)

        # ── Dialogue panel ────────────────────────────────────────────
        dl_x  = PNL_W + 10
        dl_w  = W - dl_x - M
        DIAG_Y0 = HDR_H + 8
        DIAG_Y1 = H - BTM_H
        char_w    = max(1, font.size("A")[0])
        wrap_cols = max(30, dl_w // char_w)

        fn_sp = pygame.font.SysFont("monospace", 17, bold=True)

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
        # Anchor newest messages to BOTTOM. When content overflows, start y
        # negative so oldest messages clip off the top.
        y = DIAG_Y0 + 6 + (avail - total_px)

        # Set up clip rect so blocks crossing the top edge don't draw above
        prev_clip = surface.get_clip()
        clip_rect = pygame.Rect(0, DIAG_Y0, W, DIAG_Y1 - DIAG_Y0)
        surface.set_clip(clip_rect)

        for speaker, is_npc, is_sys, wrapped in blocks:
            b_h = _block_h((speaker, is_npc, is_sys, wrapped))
            if y + b_h < DIAG_Y0:
                y += b_h
                continue
            if y >= DIAG_Y1:
                break

            if is_npc:
                bar_end = y + b_h - GAP - 2
                pygame.draw.line(surface, (195, 122, 0),
                                 (dl_x, y), (dl_x, bar_end), 2)
                sp = fn_sp.render(f"  [{speaker}]", True, (255, 180, 34))
                surface.blit(sp, (dl_x + 6, y))
                y += lh
                for line in wrapped:
                    surface.blit(
                        font.render(f"    {line}", True, (205, 152, 36)),
                        (dl_x + 6, y))
                    y += lh

            elif is_sys:
                for line in wrapped:
                    surface.blit(
                        font_sm.render(f"  // {line}", True, (68, 86, 68)),
                        (dl_x, y))
                    y += lh

            else:  # YOU
                sp = fn_sp.render("[YOU]  »", True, (62, 212, 98))
                surface.blit(sp, (W - M - sp.get_width(), y))
                y += lh
                for line in wrapped:
                    surface.blit(
                        font.render(f"    {line}", True, (84, 200, 104)),
                        (dl_x + 48, y))
                    y += lh

            y += GAP

        surface.set_clip(prev_clip)

        # ── Bottom divider ─────────────────────────────────────────────
        pygame.draw.line(surface, (0, 138, 56), (0, H - BTM_H), (W, H - BTM_H), 1)

        # ── Input box ──────────────────────────────────────────────────
        inp_y    = H - BTM_H + 10
        inp_rect = pygame.Rect(M, inp_y, W - 2 * M, 36)
        pygame.draw.rect(surface, (0, 14, 4), inp_rect)
        pygame.draw.rect(surface, (0, 172, 70), inp_rect, 1)
        cursor = "█" if self._cursor_visible else " "
        surface.blit(
            font.render(f"  > {self._input}{cursor}", True, (0, 236, 94)),
            (M + 8, inp_y + 8))

        # NPC-specific hint
        hint = _NPC_HINTS.get(self.npc.name.upper(),
                              "deal · bribe · sympathy · threaten · [ESC] abort")
        surface.blit(
            font_sm.render(hint, True, (50, 98, 60)),
            (M, inp_y + 50))

        # Turn counter
        turn_s = font_sm.render(f"TURN {self.npc._turn}", True, (42, 72, 42))
        surface.blit(turn_s, (W - M - turn_s.get_width(), inp_y + 50))

        # ── Outcome banner ─────────────────────────────────────────────
        if self._done:
            self._draw_outcome_banner(surface, W, H, t)

        # ── Global scanlines ───────────────────────────────────────────
        surface.blit(self._scan_surf, (0, 0))

    def _draw_outcome_banner(self, surface: pygame.Surface, W: int, H: int, t: float):
        ocol = _OUTCOME_COLOR.get(self._outcome, S.AMBER_TERM)
        olbl = _OUTCOME_LABEL.get(self._outcome, "[ DISCONNECTED ]")

        # For EXPLOIT and RELEASE, add a flash aura
        is_win = self._outcome in (NPCOutcome.RELEASE, NPCOutcome.EXPLOIT)

        if is_win and self._exploit_flash is not None:
            age = t - self._exploit_flash
            if age < 3.0:
                # Expanding glow rect
                pulse = abs(math.sin(t * 6.0))
                aura = pygame.Surface((W, H), pygame.SRCALPHA)
                a = int(60 * pulse * max(0, 1.0 - age / 3.0))
                aura.fill((*ocol, a))
                surface.blit(aura, (0, 0))

        ofont = pygame.font.SysFont("monospace", 22, bold=True)
        osurf = ofont.render(olbl, True, ocol)
        ox = W // 2 - osurf.get_width() // 2
        oy = H // 2 - osurf.get_height() // 2

        # Dark backing with colored border
        pad = 16
        bg_rect = pygame.Rect(ox - pad, oy - pad // 2,
                              osurf.get_width() + pad * 2, osurf.get_height() + pad)
        pygame.draw.rect(surface, (0, 0, 0), bg_rect)
        pygame.draw.rect(surface, ocol, bg_rect, 2)

        # Pulsing second border for wins
        if is_win:
            pulse_a = int(180 + 75 * math.sin(t * 5.0))
            inner_col = tuple(min(255, int(c * 0.6)) for c in ocol)
            pygame.draw.rect(surface, inner_col,
                             bg_rect.inflate(-4, -4), 1)

        surface.blit(osurf, (ox, oy))

        # Sub-label
        sub_font = pygame.font.SysFont("monospace", 14)
        sub_lbl = "[ press any key ]" if is_win else "[ IMPOUND PROCEEDING — ESC TO VIEW FEES ]"
        sub_col = (int(ocol[0] * 0.7), int(ocol[1] * 0.7), int(ocol[2] * 0.7))
        sub = sub_font.render(sub_lbl, True, sub_col)
        surface.blit(sub, (W // 2 - sub.get_width() // 2, oy + osurf.get_height() + 8))

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
