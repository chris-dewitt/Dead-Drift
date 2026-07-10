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
        self.last_parsed: ParsedInput | None = None
        self._current_path: str = ""            # set by subclass during _evaluate
        # J.1 — a priced line stages a transaction here; the Terminal applies
        # it against the run wallet after respond(). Only ever set when the
        # NPC has already confirmed the player can afford it (via _ctx credits),
        # so the Terminal never has to second-guess affordability.
        self._pending_txn: dict | None = None

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
    # Universal panic-escape easter egg (playtest backlog).
    # The phrase "fuck off" releases the player on every NPC. NOT
    # advertised in any keyword hint, dossier line, README, or in-game
    # text — players have to discover it organically. The carrier
    # registers it as path "ESCAPE" so the per-NPC dossier doesn't
    # show ★ ESCAPE on the chip strip.
    _UNIVERSAL_ESCAPE = "fuck off"

    def respond(self, player_input: str) -> tuple[str, str]:
        """
        Parse input, evaluate against NPC logic, return (outcome, npc_line).
        Patience ticks down every turn.
        """
        parsed   = self._parser.parse(player_input)
        self.last_parsed  = parsed
        self._current_path = ""
        self._turn += 1
        self._log.append(("PLAYER", player_input))

        # Universal easter egg — checked before evaluator so it works
        # even when patience is at zero.
        if self._UNIVERSAL_ESCAPE in player_input.lower():
            self._current_path = "ESCAPE"
            line = self._universal_escape_line()
            self._log.append((self.name.upper(), line))
            return NPCOutcome.RELEASE, line

        if self._patience <= 0:
            return NPCOutcome.IMPOUND, self._out_of_patience_line()

        outcome, response = self._evaluate(parsed)
        if outcome == NPCOutcome.CONTINUE:
            response = self._with_cargo_dialogue(response)

        if outcome == NPCOutcome.CONTINUE:
            self._patience -= 1
            self._shift_disposition(parsed)

        self._log.append((self.name.upper(), response))
        return outcome, response

    def _universal_escape_line(self) -> str:
        """Default flavour for the universal escape phrase. NPCs may
        override if they want a more in-character close-out."""
        return (
            "*long pause* ...Right. That's the rudest thing I've heard "
            "all shift. Channel closed. Don't come back through this "
            "sector this week."
        )

    def intro(self) -> str:
        line = self._with_cargo_dialogue(self._intro_line())
        self._log.append((self.name.upper(), line))
        return line

    # ------------------------------------------------------------------
    def _shift_disposition(self, parsed: ParsedInput):
        if parsed.sentiment["compound"] > 0.4:
            self.disposition += 1
        elif parsed.sentiment["compound"] < -0.4:
            self.disposition -= 1
        self.disposition = max(-10, min(10, self.disposition))

    def get_path_progress(self) -> list[tuple[str, int, int]]:
        """Return [(display_name, current, max), ...] for the dossier panel."""
        return []

    def _out_of_patience_line(self) -> str:
        return "Alright, that's it. Harpoon's locked. You're getting towed."

    def bribe_cost(self) -> int:
        """Credits the player owes for a successful bribe. Override in subclasses."""
        return 0

    # ------------------------------------------------------------------
    # J.1 — priced transactions (the terminal stops lying about money)
    def _credits(self) -> int:
        """Player's spendable run credits, injected into _ctx each turn."""
        return int(getattr(self, "_ctx", {}).get("credits", 0))

    def stage_transaction(self, amount: int, *, dual_ledger: bool = True,
                          effect: str | None = None,
                          label: str = "TERMINAL") -> None:
        """Record a charge the Terminal will apply after respond(). Call this
        only once you've confirmed affordability (see `_credits`)."""
        self._pending_txn = {
            "amount": int(amount), "dual_ledger": bool(dual_ledger),
            "effect": effect, "label": label,
        }

    def take_pending_transaction(self) -> dict | None:
        txn, self._pending_txn = self._pending_txn, None
        return txn

    def penalize_patience(self, n: int = 1) -> None:
        """Spend patience outside the normal per-turn tick (e.g. a broke
        counter-offer). Never lets patience go negative."""
        self._patience = max(0, self._patience - int(n))

    # ------------------------------------------------------------------
    # J.2 — coding-exploit hooks. Curated NPCs override shell_session /
    # repl_session to expose a real systems path (a fake shell or a Python
    # REPL); everyone else returns None, so typing `shell`/`python` at them
    # just reports "no system on this channel." The Terminal drives the
    # session and calls register_systems_exploit() when the player lands the
    # break-in, so the win flows through the normal EXPLOIT payout.
    def shell_session(self):
        return None

    def repl_session(self):
        return None

    def register_systems_exploit(self, kind: str, exploit_key: str) -> str:
        """Mark a shell/REPL break-in: set the winning path, emit the exploit
        event, best-effort vault record. Returns the dossier path label."""
        path = f"{kind} EXPLOIT"
        self._current_path = path
        self._systems_hit = True
        try:
            from core.event_bus import bus, EVT_NLP_EXPLOIT
            bus.emit(EVT_NLP_EXPLOIT, npc=self, exploit_key=exploit_key)
        except Exception:
            pass
        vault = getattr(self, "_vault", None)
        if vault is not None and hasattr(vault, "record"):
            try:
                vault.record(type(self).__name__.lower(), exploit_key.upper())
            except Exception:
                pass
        return path

    def _with_cargo_dialogue(self, line: str) -> str:
        """Append one cargo-aware flavor line per encounter when context allows."""
        if getattr(self, "_cargo_dialogue_used", False):
            return line
        try:
            from terminal.npcs.cargo_dialogue import cargo_line_for
            cargo_line = cargo_line_for(self.name, getattr(self, "_ctx", {}))
        except Exception:
            cargo_line = None
        if not cargo_line:
            return line
        self._cargo_dialogue_used = True
        return f"{line} {cargo_line}"

    @property
    def transcript(self) -> list[tuple[str, str]]:
        return list(self._log)
