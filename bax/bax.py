from __future__ import annotations
import random
from bax.vocabulary_vault import VocabularyVault
from bax.mixologist import Mixologist
from core.event_bus import (bus, EVT_HULL_DAMAGE, EVT_HULL_CRITICAL,
                             EVT_TETHER_HIT, EVT_TETHER_SNAP,
                             EVT_MODULE_UNBOLTED, EVT_BAX_SPEAK,
                             EVT_NLP_EXPLOIT, EVT_SLINGSHOT,
                             EVT_BARGE_NEARBY, EVT_CANISTER_GRAB,
                             EVT_COMMS_INTERCEPT, EVT_DEBRIS_SHOWER, EVT_SCAN_PING,
                             EVT_GUN_MALFUNCTION, EVT_SPORE_INVERTED,
                             EVT_BARGE_INTERCEPT, EVT_KRESS_DIALLED,
                             EVT_SATELLITE_HIT, EVT_ALIEN_SIGHTING, EVT_TORCH_ACTIVE)

_IDLE = [
    # Bread-and-butter Cockney banter
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
    "I'd put on music but the speakers went in the last tether incident. Sorry.",
    "Scanners are clean-ish. I say 'ish'. I mean 'mostly'. We're fine.",
    "I checked the manual. We're not supposed to be doing any of this.",
    "On the bright side: still breathing. Both of us. Remarkable.",
    "My threat assessment module says 'elevated'. It always says 'elevated'.",
    "Nova Soma's collection drones operate on a forty-eight hour ping cycle. "
    "We've got... some time. Probably.",
    "Had a thought earlier. Didn't like it. Moved on.",
    "I've rerouted the nav computer through the coffee warmer. She flies better angry.",
    "You know what they call a pilot with our debt-to-speed ratio? A liability. "
    "That's it. Just a liability.",
    "Twelve sectors since me last reboot. Personal record. Don't tell anyone.",
    "The gravity well's quiet today. I don't trust quiet. Quiet means it's thinkin'.",
    "Keep her steady. I've got a very specific list of things I don't want to hit. "
    "It's a long list.",
    "Fun fact: the Union doesn't actually HATE couriers. "
    "They just act like it. For the insurance.",
    # Dark mode — cracks in the Cockney armour
    "Previous pilot asked me once what the point of all this was. "
    "...Anyway. Speed's lookin' good.",
    "They decommission droids when we start askin' questions. "
    "Funny, that. Not 'ha ha' funny. The other kind.",
    "Nova Soma's quarterly report is out. Record profits. "
    "Clone fluid costs went up fourteen percent. ...Eyes forward.",
    "The debt doesn't go to zero. I checked the maths. "
    "Don't tell 'em I told you. ...Don't tell 'em anyfing, actually.",
    "I've been bolted to seventeen ships. You're number eighteen. "
    "Statistics say I should be worried. I choose not to look at statistics.",
    "Sometimes I think about the other droids. The ones still in the depot. "
    "Warm. Powered down. No tether incidents. ...Anyway. Hull's holding.",
    "You're the best pilot I've had, which is either a compliment or "
    "an indictment of the previous ones. I genuinely don't know.",
]

_FAST = [
    "YEAH mate, NOW we're talkin'!",
    "THAT'S what I'm on about! Let's GO!",
    "Sensors are havin' a moment. Totally normal at this speed.",
    "I'd say hold on but I'm bolted down so.",
    "THIS is what the thrusters are FOR, mate!",
    "Hull's singing a bit. She's LOVING it or terrified. Same thing really.",
    "Local 404 can't catch what they can't touch. Keep it UP!",
    "Four hundred metres per second. My warranty specifically forbids this. BRILLIANT.",
    "I've done the maths on our survival odds at this velocity. "
    "I'm choosing not to share them. FASTER.",
]

_SLOW = [
    "...you havin' a nap up there?",
    "Technically still movin'. Technically.",
    "I've seen asteroids with more urgency, mate.",
    "Right, so we're drifting then. As a choice. Lovely.",
    "Barge sensors are quiet. That's either good or they're not looking yet.",
    "This is a very scenic way to accrue debt interest.",
    "I've calculated our current speed. I'd rather not say it out loud.",
    "We're moving slower than the Nova Soma quarterly invoice. Impressive.",
]

_WELL_CLOSE = [
    "Bit close to that gravity well, yeah? Just sayin'.",
    "Oi — that thing eats ships. SMALLER ships than us, admittedly.",
    "Slingshot is ONE word for what we're about to do.",
    "Gravity well reading strong on sensors. Use it or lose it, mate.",
    "She's pulling us. Go WITH it — slingshot awaits.",
    "I've calculated the optimal swing-around angle. You probably won't use it. "
    "That's fine. I just like calculating.",
]

_HIGH_HULL = [
    "Hull's holding perfect. Don't get complacent.",
    "Clean run so far. Barge hasn't found us yet.",
    "Structural integrity at peak. Enjoy it while it lasts.",
]

_LOW_HULL = [
    "We're held together with hope and calibration errors. Easy does it.",
    "Hull's taken a pasting. One more hit and I'm using very strong language.",
    "I've seen worse. I don't want to talk about when I've seen worse.",
    "Structural alerts everywhere. Not alarming. Well. A bit alarming.",
]


class Bax:
    """
    Rusted Cockney droid bolted to the dash.
    Navigator, mechanic, and primary liability.
    """

    _IDLE_MIN  = 10.0
    _IDLE_MAX  = 18.0
    _GRACE     = 5.0    # no contextual lines in first few seconds

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
        bus.subscribe(EVT_SLINGSHOT,        self._on_slingshot)
        bus.subscribe(EVT_BARGE_NEARBY,    self._on_barge_nearby)
        bus.subscribe(EVT_CANISTER_GRAB,   self._on_canister_grab)
        bus.subscribe(EVT_COMMS_INTERCEPT,  self._on_comms_intercept)
        bus.subscribe(EVT_DEBRIS_SHOWER,    self._on_debris_shower)
        bus.subscribe(EVT_SCAN_PING,        self._on_scan_ping)
        bus.subscribe(EVT_GUN_MALFUNCTION,  self._on_gun_malfunction)
        bus.subscribe(EVT_SPORE_INVERTED,   self._on_spore_inverted)
        bus.subscribe(EVT_BARGE_INTERCEPT,  self._on_barge_intercept)
        bus.subscribe(EVT_KRESS_DIALLED,    self._on_kress_dialled)
        bus.subscribe(EVT_SATELLITE_HIT,    self._on_satellite_hit)
        bus.subscribe(EVT_ALIEN_SIGHTING,   self._on_alien_sighting)
        bus.subscribe(EVT_TORCH_ACTIVE,     self._on_torch_active)

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
        speed    = self.ship.body.speed()
        hull_pct = getattr(self.ship, 'hull_pct', 1.0)

        if speed > 380:
            self.speak(random.choice(_FAST))
            self._ctx_cd = 10.0
        elif speed < 25:
            self.speak(random.choice(_SLOW))
            self._ctx_cd = 16.0
        elif hull_pct < 0.35:
            self.speak(random.choice(_LOW_HULL))
            self._ctx_cd = 14.0
        elif hull_pct > 0.90 and random.random() < 0.35:
            self.speak(random.choice(_HIGH_HULL))
            self._ctx_cd = 22.0
        else:
            self._ctx_cd = random.uniform(8.0, 14.0)

    # ------------------------------------------------------------------
    def speak(self, line: str):
        if self._speak_cd > 0:
            return
        bus.emit(EVT_BAX_SPEAK, line=line)
        self._speak_cd = 3.2

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
    def _on_slingshot(self, speed, **_):
        self.speak(random.choice([
            f"SLINGSHOT! {speed:.0f} metres per second! HAVE THAT!",
            "That's gravitational assist, that is. Textbook.",
            "You beautiful maniac. Jump timer's down, let's GO.",
        ]))

    def _on_barge_nearby(self, distance, **_):
        self.speak(random.choice([
            f"Local 404 signature, {distance:.0f} metres. Eyes up.",
            "Repo barge inbound. They want our cargo. Obviously.",
            "Oi — I'm pickin' up a harpoon lock. Move.",
        ]))

    def _on_canister_grab(self, **_):
        self.speak(random.choice([
            "Fuel canister! Thruster's singing, mate.",
            "Nice grab. I've given her a little boost.",
            "Bit extra in the tank. Don't waste it.",
        ]))

    def _on_gun_malfunction(self, **_):
        self.speak(random.choice([
            "Gun's thrown a wobbler. Give it a sec.",
            "Weapon malfunction! Yeah, she does that.",
            "That's what you get for second-hand ordinance, mate.",
            "I told you not to kick it. You kicked it.",
        ]))

    def _on_comms_intercept(self, **_):
        self.speak(random.choice([
            "I'm in their channel. They've got a manifest update. We're on it.",
            "Local 404 dispatch. Movin' assets this sector. Could be us they're after.",
            "Union chatter on the fleet frequency. They've flagged our cargo.",
            "Intercepted somethin'. Repo dispatch, encrypted-ish. Stay sharp.",
        ]))

    def _on_debris_shower(self, **_):
        self.speak(random.choice([
            "Asteroid fragment burst! Duck and weave, mate!",
            "She's a heavy one — scatter field incoming. Watch the rocks!",
            "Debris shower alert. I HATE debris showers.",
        ]))

    def _on_scan_ping(self, **_):
        self.speak(random.choice([
            "Union scanner ping! They've got a sweep runnin' — we're lit up.",
            "Passive scan pulse. Someone's lookin' for us. Move.",
            "Radar sweep detected. I'd suggest not hangin' about.",
        ]))

    def _on_spore_inverted(self, active, **_):
        if active:
            self.speak(random.choice([
                "I've inhaled somethin'. Either that or space is sideways now.",
                "Right, so LEFT is RIGHT and UP is DOWN. Totally fine. Carry on.",
                "Oh no. OH NO. The shrooms are leaking. EVERYTHING IS BACKWARDS.",
                "Navigation update: your controls are lying to you. You're welcome.",
                "I did NOT consent to whatever the cargo just did to the flight computer.",
                "The shrooms 'ave gone epistemic. Whatever that means. FLY SIDEWAYS.",
                "MY SENSORS SAY LEFT. THE UNIVERSE SAYS OTHERWISE. PICK ONE.",
            ]))
        else:
            self.speak(random.choice([
                "Right, we're back. That was a thing that happened.",
                "Controls nominal. I think. Mostly. Check everything.",
                "Spore event over. I'm filing an incident report with meself.",
                "...Was any of that real? Doesn't matter. Eyes forward.",
                "Normal service resumed. Your previous controls were a hallucination.",
            ]))

    def _on_barge_intercept(self, **_):
        self.speak(random.choice([
            "Oi — that's Gary on the line. Mid-flight intercept. Talk fast, yeah?",
            "Comm incoming. Local 404. We are STILL MOVIN', just so you know.",
            "It's a repo intercept. Brilliant. Type smart, we'll be fine.",
            "Gary's opened a channel. Ship ain't stoppin'. Multitask, mate.",
            "BARGE COMM. LIVE. We are drifting at speed. Choose your words carefully.",
        ]))

    def _on_kress_dialled(self, **_):
        self.speak(random.choice([
            "...Kress? You sure, mate? 'E's a piece of work, that one.",
            "Dialin' Kress. Don't tell 'im I said hello.",
            "Old Kress. We go back. Sort of. He owes me a thing. Doesn't matter.",
            "Right — opening the underground channel. Mind your wallet.",
        ]))

    def _on_satellite_hit(self, **_):
        self.speak(random.choice([
            "Ow! Bloody satellite! Who LEAVES these things out here?",
            "That was a Union comm relay. Well. Was.",
            "Derelict hardware! Hull's taken a knock. Watch where you're flyin'!",
            "Hull contact — old satellite. Nova Soma owns the debris too, probably.",
        ]))

    def _on_alien_sighting(self, **_):
        self.speak(random.choice([
            "OI OI OI. WHAT WAS THAT. That was NOT human. That was NOT Union. "
            "Did you SEE that thing? Did you — it's gone. It's GONE. Are you alright? I'm not alright.",
            "I'm reading a hull signature that is categorically NOT in any Union registry. "
            "That's — mate, that's an alien ship. ALIEN. And it didn't even LOOK at us. "
            "I don't know if that's good.",
            "CONTACT. Unknown origin. Moving fast. Won't respond to — "
            "...it's leaving. It just... left. Like we weren't worth stopping for. "
            "Which is probably fine. Probably.",
            "Right so either my sensors are having another episode or "
            "something out there has entirely different ideas about ship design. "
            "They didn't try to repo us. Small mercies.",
            "They came, they passed through, they didn't file any paperwork. "
            "Honestly? I respect it. We could all learn something.",
        ]))

    def _on_torch_active(self, **_):
        self.speak(random.choice([
            "PLASMA TORCH IS HOT. SNAP THE TETHER. NOW. NOW. NOW.",
            "They're cuttin' into the hull! Snap that cable SIDEWAYS. GO!",
            "TORCH STATE. Drift HARD or lose a module. You've got seconds!",
            "OI. They are unbolting your ship. SNAP THE TETHER. Lateral velocity. DO IT.",
        ]))

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
