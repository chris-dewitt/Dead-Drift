from __future__ import annotations
import random
import pygame
from cargo.cargo_base import BaseCargo
from core.event_bus import bus, EVT_BAX_SPEAK
from config import settings as S

_POPUP_KEYS = [(pygame.K_f, "F"), (pygame.K_g, "G"), (pygame.K_h, "H")]

_POPUP_BAX = [
    "Form 27-B, subsection 9. By ORDER of the bloody Union, mate. Press [{k}]!",
    "ADMINISTRATIVE INTERRUPT. File it. Press [{k}]. Now.",
    "Regulatory compliance form. Union bylaws, section 7. Hit [{k}]!",
    "Paperwork! MANDATORY! Press [{k}] or face infrastructure penalties!",
    "It's another bloody form. They never end. Press [{k}]. Quickly.",
    "Union bylaw 12-F demands immediate compliance. Key [{k}]. Do it.",
]

_FILED_BAX = [
    "Form filed! In triplicate! The Union can choke on it.",
    "Compliance achieved. Bureaucracy satisfied. For now.",
    "Filed it. WELL within the deadline, I might add.",
    "27-B processed. Subsection 9 satisfied. God help us all.",
    "Got it. Filed it. I hate this cargo more every sector.",
]

_MISSED_BAX = [
    "You MISSED the form! They've docked your hull integrity!",
    "Non-compliance! Hull integrity FINED! By BUREAUCRATIC LAW!",
    "That form was legally binding, mate. Hull damage incoming.",
    "ADMINISTRATIVE PENALTY. I warned you about the forms.",
]


class SentientPaperwork(BaseCargo):
    """Ch.3: Cursed bureaucratic documents — random HUD popup form interrupts."""

    def __init__(self):
        super().__init__("SENTIENT TELEPATHIC PAPERWORK")
        self.popup_active    = False
        self.popup_key: int | None = None
        self.popup_key_name  = ""
        self.popup_timer     = 0.0
        self.popup_fraction  = 0.0   # 1.0→0.0, used by renderer countdown bar
        self._next_trigger   = random.uniform(S.FORM_TRIGGER_MIN, S.FORM_TRIGGER_MAX)
        self._forms_filed    = 0

    def update(self, dt: float, ship) -> None:
        if self.popup_active:
            self.popup_timer    -= dt
            self.popup_fraction  = max(0.0, self.popup_timer / S.FORM_TIMEOUT)
            if self.popup_timer <= 0.0:
                self.popup_active = False
                ship.take_damage(14.0, source="form_missed")
                bus.emit(EVT_BAX_SPEAK, line=random.choice(_MISSED_BAX))
                self._next_trigger = random.uniform(
                    S.FORM_TRIGGER_MIN * 0.5, S.FORM_TRIGGER_MAX * 0.5)
        else:
            self._next_trigger -= dt
            if self._next_trigger <= 0.0:
                self._trigger_form()

    def _trigger_form(self) -> None:
        self.popup_key, self.popup_key_name = random.choice(_POPUP_KEYS)
        self.popup_active   = True
        self.popup_timer    = S.FORM_TIMEOUT
        self.popup_fraction = 1.0
        bus.emit(EVT_BAX_SPEAK,
                 line=random.choice(_POPUP_BAX).format(k=self.popup_key_name))

    def handle_key(self, event: pygame.event.Event) -> bool:
        if not self.popup_active or self.popup_key is None:
            return False
        if event.key == self.popup_key:
            self.popup_active = False
            self._forms_filed += 1
            self._next_trigger = random.uniform(S.FORM_TRIGGER_MIN, S.FORM_TRIGGER_MAX)
            bus.emit(EVT_BAX_SPEAK, line=random.choice(_FILED_BAX))
            return True
        return False

    def _on_damage(self) -> None:
        if not self.popup_active:
            self._next_trigger = max(3.0, self._next_trigger - 8.0)

    def terminal_climax(self) -> str:
        # Ch.3 — file the forms with the dispatcher who hates forms
        return "union_dispatcher"
