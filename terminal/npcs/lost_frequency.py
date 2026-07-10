"""
FREQUENCY LOST — the aftermath slot for Marrow's station once the Roost is gone.

There is no negotiation here. Marrow is dead; the Roost frequency returns only a
Local 404 seizure loop. Every path is a way of sitting with that silence: you
can listen to the raid notice, say a quiet goodbye, or drop into the dead
relay's shell and `grep` the seizure log for the last thing Marrow cached before
Local 404 pulled the plug. All roads clear you through — the gate logs the dead
channel as acknowledged — but they don't all feel the same.
"""
from __future__ import annotations

from terminal.npcs.base_npc import BaseNPC, NPCOutcome
from terminal.nlp_parser import ParsedInput

# Ways of reaching for the broadcaster who used to answer here.
_HAIL_KEYWORDS = [
    "marrow", "roost", "radio", "broadcast", "hello", "come in",
    "you there", "anyone", "pirate radio", "the frequency", "signal",
]
# Ways of grieving the channel — a courier paying respects.
_MOURN_KEYWORDS = [
    "goodbye", "rest", "sorry", "miss you", "thank you", "dedication",
    "for marrow", "one last", "sign off", "farewell", "safe travels",
]
# Rage at Local 404 for silencing him.
_RAGE_KEYWORDS = [
    "local 404", "bastards", "murderers", "they killed", "seizure",
    "asset recovery", "avenge", "make them pay", "not forgotten",
]


class LostFrequency(BaseNPC):
    """Aftermath slot for Marrow's station once the Roost is gone."""

    def __init__(self, run_context: dict | None = None, **_):
        super().__init__("FREQUENCY LOST", patience=2)
        self._heard_static = False
        self._mourned      = False
        self._raged        = False
        self._ctx = run_context or {}

    def _intro_line(self) -> str:
        return (
            "*carrier hiss* The Roost frequency returns only a seizure loop: "
            "LOCAL 404 ASSET RECOVERY NOTICE. UNLICENSED RELAY SILENCED. "
            "BROADCASTER AT LARGE: NO LONGER AT LARGE. *static*"
        )

    def exploits(self) -> dict[str, str]:
        return {
            "aftermath":    "Hail the dead channel — hear the raid notice where Marrow was",
            "dedication":   "Say a quiet goodbye — the gate logs it and lets you pass",
            "relay_shell":  "Type `shell`, then `grep marrow raid seizure.log` — his last cache",
        }

    def _evaluate(self, parsed: ParsedInput) -> tuple[str, str]:
        raw = parsed.raw.lower()

        if any(w in raw for w in _MOURN_KEYWORDS):
            self._mourned      = True
            self._current_path = "DEDICATION"
            return NPCOutcome.RELEASE, (
                "You say it to a channel nobody is allowed to use. "
                "Bax keeps the comm open a second longer than she has to. "
                "Then the gate logs the dead frequency as acknowledged and clears you."
            )

        if any(w in raw for w in _RAGE_KEYWORDS):
            self._raged        = True
            self._current_path = "AFTERMATH"
            return NPCOutcome.RELEASE, (
                "Local 404 boilerplate answers instead of Marrow — flat, legal, final. "
                "Nova Soma's name is in the fine print. Somewhere a courier writes it down. "
                "The gate clears you through the quiet."
            )

        if any(w in raw for w in _HAIL_KEYWORDS):
            self._heard_static = True
            self._current_path = "AFTERMATH"
            return NPCOutcome.RELEASE, (
                "No answer. Just Local 404 legal boilerplate, a burst of old music "
                "too damaged to name, and the hollow click of a channel nobody "
                "is allowed to use anymore."
            )

        self._current_path = "AFTERMATH"
        return NPCOutcome.RELEASE, (
            "The frequency does not answer. The gate logs the dead channel as "
            "acknowledged and clears you through."
        )

    # J.3.1 — the dead relay still has a shell. `grep marrow raid` (or reading
    # the seizure log) surfaces the last thing Marrow cached before Local 404
    # silenced the Roost: a routing note that ties him to Chen's cipher.
    def shell_session(self):
        if getattr(self, "_shell", None) is None:
            from terminal.shell_session import ShellSession
            self._shell = ShellSession(
                host="roost-relay", user="ghost",
                motd="ROOST RELAY // last packet cached before seizure",
                files={
                    "/README": "if you are reading this the Roost is gone.\n"
                               "the music is in the log. so am I. — M.",
                    "/var/log/seizure.log": "LOCAL 404 ASSET RECOVERY: relay silenced.\n"
                               "marrow: routed the cipher for Chen. raid could not un-route it.\n"
                               "marrow: tell the couriers the frequency was real.",
                },
                loot={"/var/log/seizure.log": "relay_shell"},
                denied=set(),
            )
        return self._shell

    def get_path_progress(self) -> list[tuple[str, int, int]]:
        return [
            ("AFTERMATH",   int(self._heard_static), 1),
            ("DEDICATION",  int(self._mourned),      1),
            ("RELAY SHELL", int(getattr(self, "_systems_hit", False)), 1),
        ]
