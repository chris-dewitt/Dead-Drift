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
                             EVT_SATELLITE_HIT, EVT_ALIEN_SIGHTING, EVT_TORCH_ACTIVE,
                             EVT_HARPOON_ARMING,
                             EVT_SHIP_DESTROYED, EVT_RUN_START,
                             EVT_SHOP_ENTER, EVT_SHOP_BUY, EVT_SHOP_SKIP,
                             EVT_FINAL_SECTOR, EVT_SECTOR_START)

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
    "Debt interest just ticked. I felt it spiritually.",
    "Fun fact: my memory banks hold every previous pilot's last words. "
    "I don't share them. That would be weird.",
    "You know the Union pays their droids hazard pay? I don't get hazard pay. "
    "I am the hazard.",
    "I've cross-referenced your current velocity against every good decision "
    "I've ever witnessed. Still cross-referencing.",
    "Nova Soma classifies me as 'non-essential equipment'. I classify them as "
    "'the entire reason we're out here'. Different perspectives.",
    "I've been in worse sectors. Don't ask me to describe them. "
    "Actually — just keep your eyes forward.",
    "The stars don't care about our debt. I find that either comforting or "
    "horrifying depending on the sector.",
    "My diagnostic ran this morning. Everything nominal except the part "
    "where I'm bolted to a courier ship with seventeen outstanding warrants.",
    "Three things keep us going: thrust, spite, and an unreasonably optimistic "
    "read on our survival odds. Mostly the spite.",
    "I miss radio. Real radio. Not Union dispatch, not MediCorp invoices. "
    "Just someone playin' music because they felt like it.",
    "This sector is particularly hostile, even by the standards of sectors "
    "that are TRYING to be hostile.",
    "I've calculated our ideal escape vector seventeen times. "
    "It's still 'forward and fast'. Very sophisticated maths.",
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
    "She's pushing three-fifty! Nav computer is singing!",
    "Go on then! Show 'em what a rusted hull CAN do!",
    "The tether can't reach what it can't track! KEEP. MOVING.",
    "My velocity alerts are firing on all cylinders. PERFECT.",
    "I love this part. I hate every other part. I love THIS PART.",
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
    "Union drones move faster than this. Just so you're aware.",
    "I've seen decommissioned satellites with more urgency.",
    "We're generating less momentum than the debt interest. Reflective.",
    "Barge IFF is offline this slow. Lucky break. Use it.",
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

# Per-cargo idle commentary — drawn during flight when no urgent condition fires
_CARGO_IDLE: dict[str, list[str]] = {
    "AcousticArchive": [
        "That archive's worth a decade of suppressed music. Nova Soma's been buying "
        "everything — burying it. We might be the only copy left out here.",
        "Illegal sound library in the hold. The Union's gonna be absolutely incandescent "
        "about this. Good.",
        "That archive's got music that predates the creditors. Someone made it because "
        "they WANTED to. Mad, that. Beautiful.",
        "I can feel the archive humming through the hull. Old frequencies. "
        "Whatever's on it, Nova Soma doesn't want anyone to hear it.",
        "The archive pulses a bit when we hit high speed. "
        "I didn't know I could miss music until I heard what's in there.",
        "Carrying the archive feels different from other cargo. "
        "Like it matters more. Which is embarrassing to say. But there it is.",
    ],
    "EpistemologicalShrooms": [
        "Psychoactive spores in the hold. Completely routine courier work. "
        "I've filed a pre-emptive incident report with meself.",
        "The shrooms have opinions. I don't know how I know that. "
        "Cargo hold reading nominal. Very normal. No concerns whatsoever.",
        "Mycorrhizal payload intact. I can confirm this because I am still "
        "experiencing conventional physics. For now.",
        "I'm detecting trace fungal particles through the ventilation. "
        "Totally fine. The walls look completely normal.",
        "The cargo's breathin' a bit. Rhythmically. I'm choosing not to think about that.",
        "We're carrying spores that rewrite your epistemological framework. "
        "Staying ahead of the paperwork. Barely.",
    ],
    "SentientPaperwork": [
        "The forms keep reorganizing themselves in the hold. Page order changes "
        "every time I scan. Normal. Fine. Don't ask.",
        "Sentient bureaucracy in the hold. The irony of carrying documents "
        "that file themselves has not escaped me.",
        "The paperwork is technically classified — even FROM the cargo. "
        "I genuinely don't know how that works legally.",
        "The documents are arguing with each other. Quietly. "
        "I'm choosing not to intervene. Union business.",
        "Form 27-B has apparently filed a complaint against Form 27-A. "
        "In triplicate. They're handling it internally.",
        "The cargo manifest rewrote itself again. Three new clauses. "
        "I don't know what they say. I don't WANT to know what they say.",
    ],
    "SchrodingerVIP": [
        "Our passenger is simultaneously the best and worst cargo I've ever "
        "facilitated. The wavefunction will decide which.",
        "The VIP hasn't been observed in a while. "
        "I'm choosing to interpret that as 'definitely alive'. Probably.",
        "Passenger manifest: one (1) person, alive OR deceased, to be confirmed. "
        "Insurance liability is absolutely someone else's problem.",
        "Don't look in the back. Whatever state they're in, "
        "observation locks it in. Keep it ambiguous.",
        "The VIP requested a blanket earlier. "
        "I have no way to verify if that request is still relevant. "
        "I've left the blanket. It's fine.",
        "Schrödinger was a physicist. The VIP is a person. "
        "Probably. We'll find out at the drop-off.",
    ],
}

# Sector-start briefings — one line when a new sector loads
_SECTOR_START_GENERIC = [
    "New sector. Watch the rocks.",
    "Jump confirmed. Fresh sector, same debt. Let's move.",
    "We're through. Keep her steady.",
    "Sector loaded. I'll tell you if something's trying to kill us.",
    "Clean jump. New sector. Eyes open.",
    "Through the gate. Stay sharp.",
]

_SECTOR_START_CARGO: dict[str, list[str]] = {
    "AcousticArchive": [
        "Sector {n}. Archive's still in the hold. Union doesn't know what "
        "they're after. Yet.",
        "Through the gate. The music's intact. Keep it that way.",
        "Sector {n}. Still carrying the archive. Still illegal in eight territories. "
        "Still worth it.",
        "New sector. The archive survives as long as we do. No pressure.",
    ],
    "EpistemologicalShrooms": [
        "Sector {n}. Spores are stable-ish. Keep the ventilation closed.",
        "Through the gate. Shrooms haven't done anything weird this sector. Yet.",
        "New sector. Mycorrhizal cargo intact. I can tell because "
        "I'm still experiencing conventional physics.",
        "Sector {n}. Fungal payload aboard. Pilot probably still sober. Let's go.",
    ],
    "SentientPaperwork": [
        "Sector {n}. The forms have reorganized themselves again. "
        "I'm letting them. They seem to prefer it.",
        "Through the gate. Papers intact. Still classified. "
        "We're fine until we're not.",
        "New sector. The cargo's still filing. Don't engage with it. Just fly.",
        "Sector {n}. Bureaucratic payload present. The irony hasn't diminished. Moving on.",
    ],
    "SchrodingerVIP": [
        "Sector {n}. Passenger unobserved. That's the ideal state. Keep it that way.",
        "Through the gate. VIP status: ambiguous. Which is CORRECT. Keep moving.",
        "New sector. Waveform uncollapsed. Passenger is everywhere and nowhere "
        "until we land. Textbook.",
        "Sector {n}. Don't look in the back. I mean it. "
        "Ambiguity is the only thing keeping the payout intact.",
    ],
}

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
        self._meta       = meta
        self.vault       = VocabularyVault()
        self.mixologist  = Mixologist()
        self._speak_cd   = 0.0
        self._radio_cd   = 0.0
        self._idle_cd    = random.uniform(self._IDLE_MIN, self._IDLE_MAX)
        self._ctx_cd     = self._GRACE
        self._grace_t    = self._GRACE

        # Run-stat tracking
        self._run_tether_hits  = 0
        self._run_hull_events  = 0
        self._run_slingshots   = 0
        self._alien_count      = 0   # alien sightings this session

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
        bus.subscribe(EVT_HARPOON_ARMING,   self._on_harpoon_arming)
        bus.subscribe(EVT_SHIP_DESTROYED,   self._on_ship_destroyed)
        bus.subscribe(EVT_RUN_START,        self._on_run_start)
        bus.subscribe(EVT_SHOP_ENTER,       self._on_shop_enter)
        bus.subscribe(EVT_SHOP_BUY,         self._on_shop_buy)
        bus.subscribe(EVT_SHOP_SKIP,        self._on_shop_skip)
        bus.subscribe(EVT_FINAL_SECTOR,     self._on_final_sector)
        bus.subscribe(EVT_SECTOR_START,     self._on_sector_start)

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
            # Cargo-aware commentary fires ~30% of the time over gravity-well quips
            cargo = getattr(self.ship, 'cargo', None)
            if cargo is not None:
                pool = _CARGO_IDLE.get(type(cargo).__name__)
                if pool and random.random() < 0.30:
                    self.speak(random.choice(pool))
                    self._ctx_cd = 18.0
                    return
            if random.random() < 0.18:
                self.speak(random.choice(_WELL_CLOSE))
                self._ctx_cd = 20.0
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
        self._run_hull_events += 1
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
        self._run_tether_hits += 1
        lines = [
            "They've got us tethered! DRIFT, go on, DRIFT!",
            "Harpoon's locked! Sideways, mate, SIDEWAYS!",
            "Oh lovely. Drift hard or lose the thruster!",
        ]
        if self._run_tether_hits >= 3:
            lines.append(f"That's {self._run_tether_hits} harpoons this run. "
                         "They REALLY want this cargo.")
        self.speak(random.choice(lines))

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
        self._run_slingshots += 1
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
        self._alien_count += 1
        if self._alien_count == 1:
            self.speak(random.choice([
                "OI OI OI. WHAT WAS THAT. That was NOT human. That was NOT Union. "
                "Did you SEE that thing? Did you — it's gone. It's GONE. Are you alright? I'm not alright.",
                "I'm reading a hull signature that is categorically NOT in any Union registry. "
                "That's — mate, that's an alien ship. ALIEN. And it didn't even LOOK at us. "
                "I don't know if that's good.",
                "CONTACT. Unknown origin. Moving fast. Won't respond to — "
                "...it's leaving. It just... left. Like we weren't worth stopping for. "
                "Which is probably fine. Probably.",
            ]))
        elif self._alien_count == 2:
            self.speak(random.choice([
                "AGAIN. They're back. Or a different one. I can't tell. They all look the same "
                "and I feel bad about that but they do. Still not filing paperwork. Still unsettling.",
                "Second alien contact. I've started a spreadsheet. Column one: 'did they care about us?'. "
                "Column two: 'no'. This is column two.",
                "Right so either they're following us or space is smaller than I thought. "
                "Either way: deeply weird. Keep moving.",
            ]))
        else:
            self.speak(random.choice([
                f"Alien sighting number {self._alien_count}. I've stopped being surprised. "
                "That worries me more than the aliens do.",
                "They're back. Fine. We have a working arrangement now, apparently. "
                "They fly past. We don't die. Everyone's happy.",
                "Another one. I've named this one Gerald. Gerald doesn't care about us. "
                "I find that oddly comforting.",
                "At this point I think they're just commuting. Past us. Every run. "
                "Gerald's got somewhere to be.",
            ]))

    def _on_harpoon_arming(self, countdown=1.5, **_):
        self.speak(random.choice([
            f"INCOMING HARPOON! BRACE — {countdown:.1f} seconds. BREAK THEIR LOCK!",
            "TARGETING LASER ON US. Cut sideways or eat the cable. MOVE.",
            "Harpoon's armin'! Get out of their cone — NOW!",
            "EM LOCK INCOMING. Boost, juke, ANYTHING — go!",
            "Their reticle's on you. Break the line of sight. FAST.",
        ]))

    def _on_torch_active(self, **_):
        self.speak(random.choice([
            "PLASMA TORCH IS HOT. SNAP THE TETHER. NOW. NOW. NOW.",
            "They're cuttin' into the hull! Snap that cable SIDEWAYS. GO!",
            "TORCH STATE. Drift HARD or lose a module. You've got seconds!",
            "OI. They are unbolting your ship. SNAP THE TETHER. Lateral velocity. DO IT.",
        ]))

    def _on_run_start(self, **_):
        self._run_tether_hits = 0
        self._run_hull_events = 0
        self._run_slingshots  = 0
        n = getattr(self._meta, "clone_count", 0)
        if n > 1:
            line = random.choice([
                f"Clone {n}. Same debt. Same ship. Same me, unfortunately. "
                "Let's try not to repeat last time.",
                f"Right. {n} bodies in. Good news: they kept your instincts. "
                "Bad news: same debt. Let's go.",
                f"Clone {n} reporting. Hull's fresh, wallet isn't. "
                "One more shot. Make it count.",
                f"That's {n} clones now. Each one slightly more annoyed to be 'ere. "
                "Use it.",
                f"Back again. Clone {n}. The debt grew while you were gone. "
                "Course it did. Thrusters are warm — let's move.",
            ])
            bus.emit(EVT_BAX_SPEAK, line=line)
            self._speak_cd = 3.2

    def _on_ship_destroyed(self, **_):
        self.speak(random.choice([
            "No no no no — MEDCORP INCOMING. Don't go towards the light. "
            "There IS no light. There's a clone tank. Which is worse.",
            "Right. That's us dead then. I'll see you on the other side of the fluid tank.",
            "Hull: zero. Pilot: deceased. Again. I'll have your clone warmed up.",
            "I've filed the incident report. Cause of death: 'the usual'. See you in the tank.",
            "That's a wrap on THIS body. Next one's slightly newer, allegedly.",
        ]))

    def _on_shop_enter(self, **_):
        self.speak(random.choice([
            "Black market stop. Don't tell the Union. Or do — they won't be surprised.",
            "Shady vendor ahead. Discretion is expensive. So is dying. Weigh it up.",
            "Right, the dodgy bloke with the crate. Budget's tight but so's our hull.",
            "It's the grey market. Everything works. Mostly. Sometimes. Buy something.",
            "Quick stop. What we need vs what we can afford. Classic dilemma.",
        ]))

    def _on_shop_buy(self, tag="", name="", **_):
        lines = {
            "hull_patch": [
                "Hull patch applied. We've got a little more margin for bad decisions.",
                "Good call. That's fifty hull integrity back. Grey market, but still.",
                "Patched. She's not pretty but she'll hold. Probably.",
            ],
            "thrust_boost": [
                "Catalyst in. Next forty seconds: considerably faster. Don't waste it.",
                "Fuel additive loaded. She's gonna SING. Ready when you are.",
                "Thrust catalyst in the mix. That's the good stuff. Illegal, but good.",
            ],
            "jammer": [
                "Jammer active. Barge harpoon locks are scrambled for ninety seconds. "
                "Local 404 is FURIOUS and can't legally prove it.",
                "EM jammer running. Their harpoon IFF is seeing static. Nice.",
                "Jammer in. They can see us but they can't grab us. For now.",
            ],
            "intel": [
                "Intel drop. I've cross-referenced with our terminal history. Useful.",
                "Black market data package. Could come in handy mid-negotiation.",
                "Intercepted dispatch logs. Their weak spots, highlighted. Cheers.",
            ],
        }
        fallback = [f"Got the {name}. Right. Let's make it count."]
        self.speak(random.choice(lines.get(tag, fallback)))

    def _on_shop_skip(self, **_):
        self.speak(random.choice([
            "Nothing? We walked away from the black market with nothing? Bold strategy.",
            "Alright. Saving the credits. I respect it. I also question it. Both.",
            "Didn't buy anything. The credits stay on the tally. That's fine. Probably fine.",
            "Window shopping at the grey market. Very dignified. Very broke.",
        ]))

    def _on_final_sector(self, **_):
        self.speak(random.choice([
            "Last sector. Everything they've got is coming for us. "
            "Everything we've got is going into this. Let's DO it.",
            "Final sector. Two barges, heavy rocks, all our worst options. "
            "Statistically we've survived worse. Once. Barely.",
            "This is sector five. Last one. After this: debt reduction, "
            "drop-off confirmed, and a very long time NOT being in space. MOVE.",
            "Sector five. The gauntlet. I've run the numbers. "
            "Our odds are 'possible'. That's the best I've got. GO.",
        ]))

    def _on_sector_start(self, sector_num=1, cargo_type=None, **_):
        pool = _SECTOR_START_CARGO.get(cargo_type) if cargo_type else None
        if pool:
            line = random.choice(pool).format(n=sector_num)
        else:
            line = random.choice(_SECTOR_START_GENERIC)
        bus.emit(EVT_BAX_SPEAK, line=line)
        self._speak_cd = 3.2

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
