"""
FREQUENCY LOST — the aftermath slot for Marrow's station once the Roost is gone.

There is no negotiation here. Marrow is dead; the Roost frequency returns only a
Local 404 seizure loop. Every path is a way of sitting with that silence: you
can hail the dead channel and hear what's left of him, say a quiet goodbye,
call in a dedication to nobody, swear at Local 404 for silencing him, or drop
into the dead relay's shell and `grep` the seizure log for the last thing
Marrow cached before they pulled the plug.

All roads clear you through — the gate logs the dead channel as acknowledged —
but they don't all feel the same, and the gate never impounds a courier for
grieving. Hailing gets one beat of static back before it lets you go; that beat
is the point of the whole encounter.
"""
from __future__ import annotations

import random

from core.event_bus import bus, EVT_NLP_EXPLOIT
from terminal.npcs.base_npc import BaseNPC, NPCOutcome
from terminal.npcs.keywords import hit
from terminal.nlp_parser import ParsedInput

# Ways of reaching for the broadcaster who used to answer here.
_HAIL_PHRASES = [
    "marrow", "roost", "pirate radio", "the frequency", "come in",
    "you there", "anyone there", "is anyone", "hello", "hey", "still there",
    "can you hear", "do you copy", "check the band", "who's broadcasting",
    "whos broadcasting",
]
_HAIL_WORDS = ("radio", "broadcast", "signal", "band", "channel", "static")
# Ways of grieving the channel — a courier paying respects.
_MOURN_PHRASES = [
    "goodbye", "sorry", "miss you", "thank you", "for marrow", "one last",
    "sign off", "farewell", "safe travels", "rest easy", "rest in",
    "he was", "he deserved", "i liked him", "he mattered", "godspeed",
    "see you around", "clear skies",
]
_MOURN_WORDS = ("rest", "sorry", "goodbye", "farewell", "dedication")
# A last request called in to a station that can't play it.
_DEDICATION_PHRASES = [
    "play it", "play something", "put it on", "request", "dedicate",
    "this one goes out", "spin it", "one more song", "last song",
    "b-side", "b side", "the slow one", "his set", "the old stuff",
]
_DEDICATION_WORDS = ("song", "track", "record", "vinyl", "tune", "music")
# Rage at Local 404 for silencing him.
_RAGE_PHRASES = [
    "local 404", "they killed", "asset recovery", "make them pay",
    "not forgotten", "they did this", "burn them", "i'll remember",
    "ill remember", "nova soma did", "someone should",
]
_RAGE_WORDS = ("bastards", "murderers", "seizure", "avenge", "revenge", "raid")


class LostFrequency(BaseNPC):
    """Aftermath slot for Marrow's station once the Roost is gone."""

    def __init__(self, vocabulary_vault=None, run_context: dict | None = None, **_):
        super().__init__("FREQUENCY LOST", patience=2)
        self._vault        = vocabulary_vault
        self._heard_static = False
        self._mourned      = False
        self._dedicated    = False
        self._raged        = False
        self._hails        = 0
        self._ctx = run_context or {}

    # ------------------------------------------------------------------
    def _win(self, key: str, path: str) -> None:
        """File a path as discovered so it reaches Bax's vault and Records."""
        self._current_path = path
        bus.emit(EVT_NLP_EXPLOIT, npc="lost_frequency", exploit_key=key)
        if self._vault:
            self._vault.record("lost_frequency", key.upper())

    def _intro_line(self) -> str:
        return random.choice([
            "*carrier hiss* The Roost frequency returns only a seizure loop: "
            "LOCAL 404 ASSET RECOVERY NOTICE. UNLICENSED RELAY SILENCED. "
            "BROADCASTER AT LARGE: NO LONGER AT LARGE. *static*",

            "*the band is still there. that's the worst of it — the band is "
            "still there, and it's carrying nothing but a recovery notice on "
            "an eleven-second loop* LOCAL 404 ASSET RECOVERY NOTICE. "
            "UNLICENSED RELAY SILENCED. *static*",

            "*Bax finds the frequency out of habit before either of you "
            "remembers why you shouldn't* ...LOCAL 404 ASSET RECOVERY NOTICE. "
            "UNLICENSED RELAY SILENCED. *she doesn't turn it off* *static*",
        ])

    def _universal_escape_line(self) -> str:
        return (
            "*you say it to a dead channel and the dead channel takes it, "
            "the way he would have* Eleven-second loop. Local 404 boilerplate. "
            "Nothing answers. The gate logs the frequency as acknowledged and "
            "clears you through the quiet."
        )

    def exploits(self) -> dict[str, str]:
        return {
            "aftermath":    "Hail the dead channel — hear what's left where Marrow was",
            "dedication":   "Say a quiet goodbye — the gate logs it and lets you pass",
            "request":      "Call in one last dedication to a station that can't play it",
            "reprisal":     "Name Local 404 out loud — the boilerplate answers instead",
            "relay_shell":  "Type `shell`, then `grep marrow raid seizure.log` — his last cache",
        }

    def _evaluate(self, parsed: ParsedInput) -> tuple[str, str]:
        raw = parsed.raw.lower()

        if hit(raw, _MOURN_PHRASES, _MOURN_WORDS):
            self._mourned = True
            self._win("dedication", "DEDICATION")
            return NPCOutcome.RELEASE, random.choice([
                "You say it to a channel nobody is allowed to use. "
                "Bax keeps the comm open a second longer than she has to. "
                "Then the gate logs the dead frequency as acknowledged and clears you.",

                "*no answer, obviously* Bax logs the transmission anyway — "
                "outgoing, unacknowledged, eleven seconds. She files it under "
                "the Roost's old call sign instead of the seizure notice. "
                "The gate clears you through.",

                "Somewhere out past the belt a relay you'll never see repeats "
                "your words once into empty sky, because that's what relays do "
                "and nobody has told this one to stop. "
                "The gate logs the dead channel as acknowledged and clears you.",
            ])

        if hit(raw, _DEDICATION_PHRASES, _DEDICATION_WORDS):
            self._dedicated = True
            self._win("request", "REQUEST")
            return NPCOutcome.RELEASE, random.choice([
                "You call in a request to a station with nobody at the desk. "
                "The seizure loop doesn't skip. But Bax pulls something off her "
                "own storage — badly compressed, taped off the Roost two "
                "chapters ago — and plays it at you the whole way to the gate.",

                "*a request line that stopped being a request line* "
                "Eleven seconds of Local 404 boilerplate. Then eleven more. "
                "Bax says: 'He'd have played it, Boss. He played anything.' "
                "The gate clears you through.",

                "Marrow took requests from couriers who couldn't pay and "
                "corporates who could, and he charged the corporates. "
                "There's nobody left on the desk to charge you. "
                "The gate logs the dead channel as acknowledged and clears you.",
            ])

        if hit(raw, _RAGE_PHRASES, _RAGE_WORDS):
            self._raged = True
            self._win("reprisal", "AFTERMATH")
            return NPCOutcome.RELEASE, random.choice([
                "Local 404 boilerplate answers instead of Marrow — flat, legal, final. "
                "Nova Soma's name is in the fine print. Somewhere a courier writes it down. "
                "The gate clears you through the quiet.",

                "You swear at a legal notice. The legal notice repeats. "
                "*Bax, quiet* 'Felix says half the band's gone dark since the raid. "
                "Half. They didn't just take the Roost, Boss.' "
                "The gate logs the dead channel as acknowledged and clears you.",

                "ASSET RECOVERY COMPLETE. RELAY DECOMMISSIONED. "
                "NO FURTHER ACTION REQUIRED. "
                "*the loop is eleven seconds long and it does not care what you called it* "
                "The gate clears you through.",
            ])

        if hit(raw, _HAIL_PHRASES, _HAIL_WORDS):
            self._hails += 1
            self._heard_static = True
            # First hail gets a beat back. Hailing twice is how a courier
            # finds out nobody's coming — so the second one lets you go.
            if self._hails == 1:
                self._current_path = "AFTERMATH"
                return NPCOutcome.CONTINUE, random.choice([
                    "*for about a second and a half, under the loop, there is "
                    "music — too damaged to name, wrong speed, somebody's "
                    "mid-sentence* —and that one goes out to every clone on the "
                    "night shift, you beautif— *LOCAL 404 ASSET RECOVERY NOTICE.*",

                    "*carrier. carrier. carrier.* Nothing is going to answer this. "
                    "You know that. Bax knows that. The band stays open anyway.",

                    "*a fragment of a jingle he must have recorded himself, badly, "
                    "years ago* —the Roost, the Roost, the only station that "
                    "doesn't work for anyb— *LOCAL 404 ASSET RECOVERY NOTICE.*",
                ])
            self._win("aftermath", "AFTERMATH")
            return NPCOutcome.RELEASE, random.choice([
                "No answer. Just Local 404 legal boilerplate, a burst of old music "
                "too damaged to name, and the hollow click of a channel nobody "
                "is allowed to use anymore.",

                "Twice is how you find out. *Bax closes the band herself this time.* "
                "The gate logs the dead frequency as acknowledged and clears you through.",
            ])

        self._current_path = "AFTERMATH"
        return NPCOutcome.RELEASE, random.choice([
            "The frequency does not answer. The gate logs the dead channel as "
            "acknowledged and clears you through.",

            "Eleven seconds of notice, then eleven more. Nothing you say is "
            "going anywhere. The gate logs the dead channel as acknowledged "
            "and clears you through.",
        ])

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
                    "/var/log/requests.log": "sandra vega-marsh — something with a horn in it\n"
                               "felix (relay-7) — 'anything, just leave it on'\n"
                               "unknown courier, sector four — for a pilot called Connie",
                },
                loot={"/var/log/seizure.log": "relay_shell"},
                denied=set(),
            )
        return self._shell

    def get_path_progress(self) -> list[tuple[str, int, int]]:
        return [
            ("AFTERMATH",   int(self._heard_static), 1),
            ("DEDICATION",  int(self._mourned),      1),
            ("REQUEST",     int(self._dedicated),    1),
            ("REPRISAL",    int(self._raged),        1),
            ("RELAY SHELL", int(getattr(self, "_systems_hit", False)), 1),
        ]
