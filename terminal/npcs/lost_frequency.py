from __future__ import annotations

from terminal.npcs.base_npc import BaseNPC, NPCOutcome
from terminal.nlp_parser import ParsedInput


class LostFrequency(BaseNPC):
    """Aftermath slot for Marrow's station once the Roost is gone."""

    def __init__(self, run_context: dict | None = None, **_):
        super().__init__("FREQUENCY LOST", patience=2)
        self._heard_static = False
        self._ctx = run_context or {}

    def _intro_line(self) -> str:
        return (
            "*carrier hiss* The Roost frequency returns only a seizure loop: "
            "LOCAL 404 ASSET RECOVERY NOTICE. UNLICENSED RELAY SILENCED. "
            "BROADCASTER AT LARGE: NO LONGER AT LARGE. *static*"
        )

    def exploits(self) -> dict[str, str]:
        return {
            "aftermath": "Hear the raid notice where Marrow used to broadcast",
        }

    def _evaluate(self, parsed: ParsedInput) -> tuple[str, str]:
        raw = parsed.raw.lower()
        self._current_path = "FREQUENCY LOST"
        if any(w in raw for w in ("marrow", "roost", "radio", "broadcast", "hello")):
            self._heard_static = True
            return NPCOutcome.RELEASE, (
                "No answer. Just Local 404 legal boilerplate, a burst of old music "
                "too damaged to name, and the hollow click of a channel nobody "
                "is allowed to use anymore."
            )
        return NPCOutcome.RELEASE, (
            "The frequency does not answer. The gate logs the dead channel as "
            "acknowledged and clears you through."
        )

    def get_path_progress(self) -> list[tuple[str, int, int]]:
        return [("FREQUENCY LOST", int(self._heard_static), 1)]
