from __future__ import annotations
import random
from bax.vocabulary_vault import VocabularyVault
from bax.mixologist import Mixologist
from core.event_bus import (bus, EVT_HULL_DAMAGE, EVT_HULL_CRITICAL,
                             EVT_TETHER_HIT, EVT_TETHER_SNAP,
                             EVT_MODULE_UNBOLTED, EVT_BAX_SPEAK,
                             EVT_NLP_EXPLOIT)


class Bax:
    """
    Rusted Cockney droid bolted to the dash.
    Navigator, mechanic, and primary liability.

    Audio cues are emitted via EVT_BAX_SPEAK — the renderer/audio layer
    picks them up and plays through the distorted dashboard speaker.
    """

    def __init__(self, ship, meta):
        self.ship        = ship
        self.vault       = VocabularyVault()
        self.mixologist  = Mixologist()
        self._speak_cd   = 0.0    # cooldown so Bax doesn't spam
        self._radio_cd   = 0.0

        self._wire_events()

    # ------------------------------------------------------------------
    def _wire_events(self):
        bus.subscribe(EVT_HULL_DAMAGE,    self._on_hull_damage)
        bus.subscribe(EVT_HULL_CRITICAL,  self._on_hull_critical)
        bus.subscribe(EVT_TETHER_HIT,     self._on_tether_hit)
        bus.subscribe(EVT_TETHER_SNAP,    self._on_tether_snap)
        bus.subscribe(EVT_MODULE_UNBOLTED, self._on_module_unbolted)
        bus.subscribe(EVT_NLP_EXPLOIT,    self._on_exploit_found)

    def update(self, dt: float):
        self._speak_cd  = max(0.0, self._speak_cd - dt)
        self._radio_cd  = max(0.0, self._radio_cd - dt)

    # ------------------------------------------------------------------
    def speak(self, line: str):
        if self._speak_cd > 0:
            return
        bus.emit(EVT_BAX_SPEAK, line=line)
        self._speak_cd = 4.0    # 4s between Bax lines

    # ------------------------------------------------------------------
    def _on_hull_damage(self, amount, **_):
        if amount > 15:
            self.speak(random.choice([
                "OI! That's coming out of ME warranty, mate!",
                "Hull breach detected, yeah? Cheers for that.",
                "I felt that. I FELT that in me capacitors.",
            ]))

    def _on_hull_critical(self, hp, **_):
        self.speak(random.choice([
            f"Hull at {hp:.0f}! WE ARE ABSOLUTELY DYING MATE.",
            "I've seen scrap heaps in better nick than this!",
            "If we die again I'm filing a grievance.",
        ]))

    def _on_tether_hit(self, barge, **_):
        self.speak(random.choice([
            "They've got us tethered! DRIFT, go on, DRIFT!",
            "Harpoon's locked! You know what to do — sideways, mate, SIDEWAYS!",
            "Oh lovely, it's Gary again. Drift hard or lose the thruster!",
        ]))

    def _on_tether_snap(self, reason, **_):
        self.speak(random.choice([
            "Tether's snapped! Leg it!",
            "YEAH! Have that, Gary!",
            "That's what lateral velocity looks like, mate!",
        ]))

    def _on_module_unbolted(self, module, **_):
        status = "It's holding - barely!" if module.is_functional() else "IT'S GONE MATE."
        self.speak(f"They've torched the {module.name}! {status}")

    def _on_exploit_found(self, npc, exploit_key, **_):
        self.vault.add_backdoor(type(npc).__name__.lower(), exploit_key)
        self.speak(f"FILED THAT. {exploit_key.upper()} works on their lot. Good stuff.")

    # ------------------------------------------------------------------
    def radio_blip(self):
        """Called by renderer when static detected — stealth enemy nearby."""
        if self._radio_cd <= 0:
            self.speak("Pickin' up somethin' on the radio... quiet-like. Eyes open.")
            self._radio_cd = 10.0

    def inject_mix(self, ingredient_a: str, ingredient_b: str):
        """Brew a fuel mix and inject it into the thruster line."""
        mix = self.mixologist.brew(ingredient_a, ingredient_b)
        if mix is None:
            self.speak("Don't know that recipe yet, do I. Stick to what we know.")
            return None

        self.speak(f"Injecting '{mix.name}'. {mix.description}")
        from ship.modules.thruster import Thruster
        thrusters = self.ship.chain.get_active("propulsion")
        for t in thrusters:
            if isinstance(t, Thruster):
                t.inject_fuel_mix(mix.force_mult, mix.duration)

        return mix
