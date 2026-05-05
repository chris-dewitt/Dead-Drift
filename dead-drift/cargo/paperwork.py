from cargo.cargo_base import BaseCargo
from core.event_bus import bus, EVT_CARGO_DAMAGED


class SentientPaperwork(BaseCargo):
    """
    Ch.3: 500 pages of living bureaucratic red tape in a titanium briefcase.
    Damage effect: brutalist HUD pop-ups demand signatures before afterburners fire.
    Terminal climax: audit the Repo Union's contracts in real-time.
    """

    def __init__(self):
        super().__init__("SENTIENT TELEPATHIC PAPERWORK")
        self.forms_pending: list[str] = []
        self._form_pool = [
            "FORM 7B: Cargo Provenance Declaration",
            "FORM 12: Afterburner Ignition Consent",
            "FORM 3C: Gravitational Hazard Liability Waiver",
            "FORM 99: Clone Identity Continuity Acknowledgement",
            "FORM 404: Intent to Exist in This Sector",
        ]

    def _on_damage(self):
        import random
        if self._form_pool:
            form = random.choice(self._form_pool)
            if form not in self.forms_pending:
                self.forms_pending.append(form)
        bus.emit(EVT_CARGO_DAMAGED, cargo=self, severity=len(self.forms_pending))

    def sign_form(self) -> str | None:
        if self.forms_pending:
            return self.forms_pending.pop(0)
        return None

    @property
    def afterburner_blocked(self) -> bool:
        return len(self.forms_pending) > 0

    def terminal_climax(self) -> str:
        return "union_dispatcher"
