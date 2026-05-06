from __future__ import annotations
import pygame
from terminal.npcs.base_npc import BaseNPC, NPCOutcome
from terminal.nlp_parser import NLPParser
from core.event_bus import bus, EVT_TERMINAL_OPEN, EVT_TERMINAL_CLOSE
from config import settings as S


class Terminal:
    """
    The claustrophobic, brutalist text terminal.
    Manages input buffer, display history, and drives NPC dialogue.
    """

    MAX_HISTORY = S.TERMINAL_ROWS - 4

    def __init__(self, npc: BaseNPC):
        self.npc      = npc
        self._history: list[tuple[str, str]] = []   # (speaker, text)
        self._input   = ""
        self._done    = False
        self._outcome = NPCOutcome.CONTINUE
        self._cursor_visible = True
        self._cursor_timer   = 0.0
        self._font    = None

        bus.emit(EVT_TERMINAL_OPEN, npc=npc)
        self._push(npc.name.upper(), npc.intro())

    def _get_font(self) -> pygame.font.Font:
        if self._font is None:
            self._font = pygame.font.SysFont("monospace", 16)
        return self._font

    # ------------------------------------------------------------------
    def handle_key(self, event: pygame.event.Event):
        if self._done:
            return

        if event.key == pygame.K_RETURN and self._input.strip():
            self._submit()
        elif event.key == pygame.K_BACKSPACE:
            self._input = self._input[:-1]
        elif event.unicode and event.unicode.isprintable():
            if len(self._input) < S.TERMINAL_COLS - 4:
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
        self._cursor_timer += dt
        if self._cursor_timer >= S.CURSOR_BLINK_MS / 1000.0:
            self._cursor_visible = not self._cursor_visible
            self._cursor_timer   = 0.0

    def draw(self, surface: pygame.Surface):
        surface.fill(S.BLACK)
        font   = self._get_font()
        line_h = font.get_linesize()
        margin = 24

        # CRT glow border
        pygame.draw.rect(surface, S.GREEN_TERM,
                         pygame.Rect(8, 8, S.SCREEN_W - 16, S.SCREEN_H - 16), 1)

        # History
        visible = self._history[-self.MAX_HISTORY:]
        y = margin
        for speaker, text in visible:
            color = S.AMBER_TERM if speaker != "YOU" else S.GREEN_TERM
            prefix = f"{speaker}> "
            # Word-wrap at TERMINAL_COLS
            for line in self._wrap(prefix + text, S.TERMINAL_COLS):
                surf = font.render(line, True, color)
                surface.blit(surf, (margin, y))
                y += line_h

        # Input line
        y = S.SCREEN_H - margin - line_h * 2
        pygame.draw.line(surface, S.GREEN_TERM,
                         (margin, y - 4), (S.SCREEN_W - margin, y - 4), 1)
        cursor = "_" if self._cursor_visible else " "
        input_surf = font.render(f"> {self._input}{cursor}", True, S.GREEN_TERM)
        surface.blit(input_surf, (margin, y))

        # Patience meter
        pat_text = f"PATIENCE: {'|' * self.npc._patience}{'.' * (self.npc.patience - self.npc._patience)}"
        pat_surf = font.render(pat_text, True, S.AMBER_TERM)
        surface.blit(pat_surf, (S.SCREEN_W - pat_surf.get_width() - margin, margin))

    def _push(self, speaker: str, text: str):
        self._history.append((speaker, text))

    @staticmethod
    def _wrap(text: str, width: int) -> list[str]:
        words  = text.split()
        lines  = []
        current = ""
        for word in words:
            if len(current) + len(word) + 1 <= width:
                current += ("" if not current else " ") + word
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines or [""]

    # ------------------------------------------------------------------
    @property
    def is_done(self) -> bool:
        return self._done

    @property
    def outcome(self) -> str:
        return self._outcome
