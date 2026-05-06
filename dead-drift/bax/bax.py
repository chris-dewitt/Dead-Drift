from __future__ import annotations
import random
from bax.vocabulary_vault import VocabularyVault
from bax.mixologist import Mixologist
from core.event_bus import (bus, EVT_HULL_DAMAGE, EVT_HULL_CRITICAL,
                             EVT_TETHER_HIT, EVT_TETHER_SNAP,
                             EVT_MODULE_UNBOLTED, EVT_BAX_SPEAK,
                             EVT_NLP_EXPLOIT)

_IDLE = [
    "Right then. No rush. I've only been bolted here since the third war.",
    "Velocity's lookin' good. Still alive. Gold standard, mate.",
    "Scanners say somethin's out there. Said that about me last crew too.",
    "A lesser droid would've quit. Lucky for you, I'm considerably worse.",
    "I've filed a formal complaint with meself. In triplicate.",
    "Beautiful view, innit. If you're into void. Which I am now, apparently.",
    "I did the maths. We're probably fine. Emphasis on probably.",
    "Still gettin' paid in credits, yeah? 'Cos I've got debts. Ironic, that.",
    "You ever think about how we're just two idiots in a can? No reason.",
    "Officially: I am THRIVING. Unofficially: please go faster.",
]

_FAST = [
    "YEAH mate, NOW we're talkin'!",
    "THAT'S what I'm on about! Let's GO!",
    "Sensors are havin' a moment. Totally normal at this speed.",
    "I'd say hold on but I'm bolted down so.",
]

_SLOW = [
    "...you havin' a nap up there?",
    "Technically still movin'. Technically.",
    "I've seen asteroids with more urgency, mate.",
    "Right, so we're drifting then. As a choice. Lovely.",
]

_WELL_CLOSE = [
    "Bit close to that gravity well, yeah? Just sayin'.",
    "Oi — that thing eats ships. SMALLER ships than us, admittedly.",
    "Slingshot is ONE word for what we're about to do.",
]


class Bax:
    """
    Rusted Cockney droid bolted to the dash.
    Navigator, mechanic, and primary liability.
    """

    _IDLE_MIN  = 18.0
    _IDLE_MAX  = 28.0
    _GRACE     = 6.0    # no contextual lines in first few seconds

    def __init__(self, ship, meta):
        self.ship        = ship
        self.vault       = VocabularyVault()
        self.mixologist  = Mixologist()
        self._speak_cd   = 0.0
        self._radio_cd   = 0.0
        self._idle_cd    = random.uniform(self._IDLE_MIN, self._IDLE_MAX)
        self._ctx_cd     = self._GRACE
        self._grace_t    = self._GRACE

        self._wire_events()

    # ------------------------------------------------------------------
    def _wire_events(self):
        bus.subscribe(EVT_HULL_DAMAGE,     self._on_hull_damage)
        bus.subscribe(EVT_HULL_CRITICAL,   self._on_hull_critical)
        bus.subscribe(EVT_TETHER_HIT,      self._on_tether_hit)
        bus.subscribe(EVT_TETHER_SNAP,     self._on_tether_snap)
        bus.subscribe(EVT_MODULE_UNBOLTED, self._on_module_unbolted)
        bus.subscribe(EVT_NLP_EXPLOIT,     self._on_exploit_found)

    def update(self, dt: float):
        self._speak_cd = max(0.0, self._speak_cd - dt)
        self._radio_cd = max(0.0, self._radio_cd - dt)
        self._idle_cd  = max(0.0, self._idle_cd  - dt)
        self._ctx_cd   = max(0.0, self._ctx_cd   - dt)
        self._grace_t  = max(0.0, self._grace_t  - dt)

        # Ambient idle chatter
        if self._idle_cd <= 0:
            self.speak(random.choice(_IDLE))
            self._idle_cd = random.uniform(self._IDLE_MIN, self._IDLE_MAX)

        # Contextual flight commentary
        if self._ctx_cd <= 0 and self._grace_t <= 0:
            self._contextual()

    def _contextual(self):
        speed = self.ship.body.speed()
        if speed > 380:
            self.speak(random.choice(_FAST))
            self._ctx_cd = 12.0
        elif speed < 25:
            self.speak(random.choice(_SLOW))
            self._ctx_cd = 20.0

    # ------------------------------------------------------------------
    def speak(self, line: str):
        if self._speak_cd > 0:
            return
        bus.emit(EVT_BAX_SPEAK, line=line)
        self._speak_cd = 4.5

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
            "Harpoon's locked! Sideways, mate, SIDEWAYS!",
            "Oh lovely. Drift hard or lose the thruster!",
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
        self.speak(f"FILED THAT. {exploit_key.upper()} works on their lot.")

    # ------------------------------------------------------------------
    def radio_blip(self):
        if self._radio_cd <= 0:
            self.speak("Pickin' up somethin' on the radio... quiet-like. Eyes open.")
            self._radio_cd = 10.0

    def inject_mix(self, ingredient_a: str, ingredient_b: str):
        mix = self.mixologist.brew(ingredient_a, ingredient_b)
        if mix is None:
            self.speak("Don't know that recipe yet. Stick to what we know.")
            return None
        self.speak(f"Injecting '{mix.name}'. {mix.description}")
        from ship.modules.thruster import Thruster
        for t in self.ship.chain.get_active("propulsion"):
            if isinstance(t, Thruster):
                t.inject_fuel_mix(mix.force_mult, mix.duration)
        return mix
