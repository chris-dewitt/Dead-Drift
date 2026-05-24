from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")


class _ScriptedNPC:
    def __init__(self, outcome: str = "continue", path: str = ""):
        from terminal.npcs.base_npc import BaseNPC

        class Scripted(BaseNPC):
            def __init__(self, scripted_outcome: str, scripted_path: str):
                super().__init__("TK-9", patience=3)
                self._scripted_outcome = scripted_outcome
                self._scripted_path = scripted_path

            def _intro_line(self) -> str:
                return "unit online"

            def _evaluate(self, parsed):
                self._current_path = self._scripted_path
                if parsed.intent == "sympathy":
                    self.disposition += 2
                elif parsed.intent == "threaten":
                    self.disposition -= 2
                return self._scripted_outcome, "scripted response"

            def exploits(self) -> dict[str, str]:
                return {}

        self.instance = Scripted(outcome, path)


def test_terminal_keystrokes_emit_audio_events_and_shake():
    import pygame
    from core.event_bus import EVT_TERMINAL_KEY, bus
    from terminal.terminal import Terminal

    pygame.init()
    events = []

    def _capture(kind: str, **_):
        events.append(kind)

    bus.subscribe(EVT_TERMINAL_KEY, _capture)
    try:
        terminal = Terminal(_ScriptedNPC().instance)
        terminal.handle_key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_a, unicode="a"))
        terminal.handle_key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_BACKSPACE, unicode=""))
        terminal._input = "go"
        terminal.handle_key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, unicode="\r"))
    finally:
        bus.unsubscribe(EVT_TERMINAL_KEY, _capture)

    assert events == ["normal", "backspace", "enter"]
    assert terminal._input_shake_t > 0


def test_terminal_paradox_outcome_freezes_portrait_and_payload():
    import pygame
    from core.event_bus import EVT_TERMINAL_CLOSE, bus
    from terminal.npcs.base_npc import NPCOutcome
    from terminal.terminal import Terminal

    pygame.init()
    payloads = []

    def _capture(**payload):
        payloads.append(payload)

    bus.subscribe(EVT_TERMINAL_CLOSE, _capture)
    try:
        terminal = Terminal(_ScriptedNPC(NPCOutcome.EXPLOIT, "PARADOX CRASH").instance)
        terminal._input = "paradox"
        terminal._submit()
    finally:
        bus.unsubscribe(EVT_TERMINAL_CLOSE, _capture)

    assert terminal._portrait_outcome == "paradox"
    assert terminal._portrait_freeze_t is not None
    assert payloads[-1]["reaction"] == "paradox"
    assert payloads[-1]["path"] == "PARADOX CRASH"


def test_reaction_portraits_render_for_terminal_roster():
    import pygame
    from terminal import npc_portraits

    pygame.font.init()
    names = [
        "GARY",
        "TK-9",
        "DISPATCHER",
        "KRESS",
        "MORWENNA",
        "SANDRA",
        "KRELLBORN",
        "MARROW",
        "TOLL AUTHORITY",
        "RELAY-7 FELIX",
        "INSPECTOR HOLT",
    ]
    for name in names:
        surface = pygame.Surface((190, 245), pygame.SRCALPHA)
        npc_portraits.draw_portrait(
            surface,
            name,
            pygame.Rect(0, 0, 190, 245),
            -2,
            1.25,
            reaction="furious",
            reaction_age=0.1,
        )
        assert pygame.mask.from_surface(surface).count() > 0


def test_terminal_outcome_sfx_key_distinguishes_paradox():
    from audio.audio_manager import _terminal_outcome_sfx_key

    assert _terminal_outcome_sfx_key("release") == "term_outcome_release"
    assert _terminal_outcome_sfx_key("exploit", "SQL INJECT") == "term_outcome_exploit"
    assert _terminal_outcome_sfx_key("exploit", "PARADOX CRASH") == "term_outcome_paradox"
    assert _terminal_outcome_sfx_key("impound") == "term_outcome_impound"
