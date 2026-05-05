from __future__ import annotations
from abc import ABC, abstractmethod
from terminal.nlp_parser import NLPParser, ParsedInput


class NPCOutcome:
    CONTINUE  = "continue"    # keep interrogating
    RELEASE   = "release"     # player wins, ship released
    IMPOUND   = "impound"     # player loses, ship towed
    EXPLOIT   = "exploit"     # player found a logic flaw


class BaseNPC(ABC):
    """
    Abstract NPC for Terminal interrogations.

    Each NPC has:
    - A set of exploit triggers (linguistic weaknesses)
    - A patience meter (runs out → impound)
    - A disposition that shifts based on player input
    """

    def __init__(self, name: str, patience: int = 5):
        self.name       = name
        self.patience   = patience
        self._patience  = patience
        self.disposition = 0      # -10 hostile .. +10 friendly
        self._parser    = NLPParser()
        self._turn      = 0
        self._log: list[tuple[str, str]] = []   # (speaker, text)

    # ------------------------------------------------------------------
    @abstractmethod
    def _intro_line(self) -> str:
        ...

    @abstractmethod
    def _evaluate(self, parsed: ParsedInput) -> tuple[str, str]:
        """Return (outcome, npc_response_text)."""
        ...

    @abstractmethod
    def exploits(self) -> dict[str, str]:
        """Map of exploit_key -> description."""
        ...

    # ------------------------------------------------------------------
    def respond(self, player_input: str) -> tuple[str, str]:
        """
        Parse input, evaluate against NPC logic, return (outcome, npc_line).
        Patience ticks down every turn.
        """
        parsed   = self._parser.parse(player_input)
        self._turn += 1
        self._log.append(("PLAYER", player_input))

        if self._patience <= 0:
            return NPCOutcome.IMPOUND, self._out_of_patience_line()

        outcome, response = self._evaluate(parsed)

        if outcome == NPCOutcome.CONTINUE:
            self._patience -= 1
            self._shift_disposition(parsed)

        self._log.append((self.name.upper(), response))
        return outcome, response

    def intro(self) -> str:
        line = self._intro_line()
        self._log.append((self.name.upper(), line))
        return line

    # ------------------------------------------------------------------
    def _shift_disposition(self, parsed: ParsedInput):
        if parsed.sentiment["compound"] > 0.4:
            self.disposition += 1
        elif parsed.sentiment["compound"] < -0.4:
            self.disposition -= 1
        self.disposition = max(-10, min(10, self.disposition))

    def _out_of_patience_line(self) -> str:
        return "Alright, that's it. Harpoon's locked. You're getting towed."

    @property
    def transcript(self) -> list[tuple[str, str]]:
        return list(self._log)
