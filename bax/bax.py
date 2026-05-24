from __future__ import annotations
import random
from collections import deque
from bax.vocabulary_vault import VocabularyVault
from bax.mixologist import Mixologist
from core.event_bus import (bus, EVT_HULL_DAMAGE, EVT_HULL_CRITICAL,
                             EVT_TETHER_HIT, EVT_TETHER_SNAP,
                             EVT_MODULE_UNBOLTED, EVT_BAX_SPEAK,
                             EVT_NLP_EXPLOIT, EVT_SLINGSHOT,
                             EVT_THRUSTER_OVERHEAT,
                             EVT_BARGE_NEARBY, EVT_CANISTER_GRAB,
                             EVT_COMMS_INTERCEPT, EVT_DEBRIS_SHOWER, EVT_SCAN_PING,
                             EVT_GUN_MALFUNCTION, EVT_SPORE_INVERTED,
                             EVT_BARGE_INTERCEPT, EVT_KRESS_DIALLED,
                             EVT_SATELLITE_HIT, EVT_ALIEN_SIGHTING, EVT_TORCH_ACTIVE,
                             EVT_HARPOON_ARMING, EVT_GUN_FIRE,
                             EVT_SHIP_DESTROYED, EVT_RUN_START,
                             EVT_SHOP_ENTER, EVT_SHOP_BUY, EVT_SHOP_SKIP,
                             EVT_FINAL_SECTOR, EVT_SECTOR_START,
                             EVT_BARGE_KILLED,
                             EVT_CORRIDOR_RUN, EVT_CORRIDOR_JUMP,
                             EVT_CORRIDOR_SECRET, EVT_CORRIDOR_DEATH,
                             EVT_DOCK_APPROACH, EVT_DOCK_PERFECT, EVT_DOCK_ROUGH)

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

# ── NEW LINE BANKS (Epic 7.2) ────────────────────────────────────────────────

_SUSTAINED_FIRE = [
    "YES MATE. GIVE 'EM EVERYTHING. THAT'S THE STUFF.",
    "OI OI OI — empty the magazine, courier, EMPTY IT!",
    "She's SINGING up there! Don't stop!",
    "I've been bolted to this dash for sixteen years and I have NEVER seen this much enthusiasm. Keep it goin'.",
    "Look at us! Just two units, expressing ourselves through ordnance!",
    "The Union's gonna file SO MUCH paperwork about this. KEEP FIRING.",
    "Yeah! YEAH! That's the spirit they decommissioned me for!",
    "Whoever told you to conserve ammo was a coward. KEEP. SHOOTING.",
    "Every bullet's a love letter to Local 404. Send another one!",
    "I'd fire too if I had hands. I'd be FIRING. KEEP GOING!",
    "This is what the trigger's FOR, mate! Don't you DARE stop!",
    "Sustained fire detected — internal review: I LOVE IT, KEEP FIRING.",
]

_FIRST_BARGE_KILL_OF_RUN = [
    "BARGE DOWN. BARGE. DOWN. Mate. MATE. We just decommissioned a Union asset.",
    "OI! That's a barge OFF the books! Local 404 just lost a vehicle and their dignity!",
    "First kill of the run. FIRST. And it's a barge. Outstanding work, courier. OUTSTANDING.",
    "I've waited SIXTEEN YEARS to see a Repo Barge eat dirt. I am EMOTIONAL.",
    "Barge eliminated. Filing report titled 'GOT 'EM.' That's the whole report. Closed it.",
    "OH that's gonna leave a mark on someone's quarterly review. Beautiful work, mate.",
    "Down she goes! Union's down a unit and we've still got our cargo. WHAT a day.",
    "Did you SEE that? Of COURSE you did, you did it. I saw it. WE saw it. Magnificent.",
    "Repo barge: destroyed. Pilot satisfaction: maximum. Bax morale: through the roof.",
    "That's the WAY, courier! THAT is how you start a run!",
    "BARGE. NEUTRALISED. The Union just took a tax write-off and they don't know it yet.",
    "First barge of the run goes BOOM. I'd buy you a drink if I had a stomach. Or money.",
]

_BARGE_DESTROYED = [
    "Another barge gone. Local 404's gonna run out at this rate. Wouldn't that be a tragedy.",
    "Down she goes. That's two. Or three. I've lost count. I love losing count this way.",
    "Repo barge: out of service. Permanently. By order of us.",
    "Filing's gonna be MENTAL for whoever survives this run on their end.",
    "Barge eliminated. I'm calling that 'cause of death: bad career choices.'",
    "Knocked another one out. The Union's pension fund is gonna feel that.",
    "Beautiful. Whatever you're doing, keep doing it. They keep dying.",
    "Barge down. I'd cheer but I don't want to seem unprofessional. ...Quietly cheering.",
    "That's another Union vehicle reduced to scrap. Job satisfaction: ELEVATED.",
    "Another one. They keep coming, we keep clearing 'em. This is the rhythm now.",
    "Barge ate it. Lovely. Whose round is this, mine or yours?",
    "Smashed it. Local 404's pulling their hair out at HQ right now. Picture it.",
]

_PANIC_UNDER_10_HULL = [
    "...hull's gone, mate. Almost. Please.",
    "We're at single digits. I don't usually beg. I'm begging.",
    "Listen — get us out. Wherever you can. Just get us out.",
    "Last time I was this damaged I had a different pilot. He didn't make it. You're going to make it.",
    "I'm not panicking. ...I'm panicking a bit.",
    "Mate. Mate. Look at the hull readout and tell me you're seeing what I'm seeing.",
    "I've gone through every other pilot's last sector with them. I'd really rather not do that today.",
    "Whatever you've got left — use it. Fast. Please.",
    "...if this is it, I want you to know I genuinely don't think you're the worst pilot I've had.",
    "We've come too far. Don't let me get bolted onto another clone, courier.",
    "Single-digit hull. I'm going to be quiet for a second so you can think.",
    "...mate. Please. Get us home.",
]

_CORRIDOR_RUNNING = [
    "Steady. We're makin' time. Don't sprint blind.",
    "Easy pace, courier. The drop-off's not going anywhere.",
    "Watch your footing. Some of these floors don't agree with us.",
    "Keep the rhythm. In, out, jump, breathe.",
    "You're doing good. Don't think about how I'm bolted to a dashboard right now.",
    "Eyes up. There's always something around the next bend in these places.",
    "Right rhythm. Stay with it. Don't get fancy.",
    "I'm watching ahead — you watch your feet. We'll get there.",
    "Corridor's quiet here. Use it. Catch your breath.",
    "We're in their building, mate. Move like it's ours.",
    "Footwork looks good. I'm impressed. Don't make me regret saying that.",
    "Stay with the pace. Smooth is fast. Said someone smarter than us.",
]

_CORRIDOR_JUMPING = [
    "OI! Nice jump!",
    "Cleared it. Of course you did. Of course.",
    "Good gap. Good clearance. Good courier.",
    "I had nothin' to do with that and I'm still proud.",
    "That's the one. Cleaner than last time, eh?",
    "Beautiful. I'd film it if I had a camera.",
    "Stuck the landing. Showin' off now.",
    "Mate. That jump. Properly clean.",
    "I shouted internally. You can't hear it, but I did.",
    "Got it. Don't think about it, just go.",
    "Air looks good on you, courier. Keep flyin'.",
    "Cleared the gap. Cleared it WELL. The gap is humbled.",
]

_CORRIDOR_SECRET_FOUND = [
    "OI. OI. You found one. You ACTUALLY found one.",
    "Secret! That's a secret! I'm filing it under 'we are smarter than they thought we were.'",
    "Whatever they hid here — it's ours now. I love this work.",
    "FOUND. SOMETHING. I'm logging it. I'm logging it twice.",
    "Knew there was something off about that wall. Brilliant work, courier.",
    "Right, that's something the corporate didn't want us to see. Excellent.",
    "Found it! Whatever 'it' is. Pocket it before they notice.",
    "Beautiful. Properly hidden, properly found. We're earning our keep.",
    "Look at that. Most pilots walk straight past these. Not us. Not US.",
    "Secret cache! Add it to the haul. I'm writing this down. Mentally.",
    "Some clerk thought no one would ever check there. They were wrong. THEY WERE WRONG.",
    "Hidden cache. Whoever stashed this is long gone. We're the inheritors. I like that.",
]

_CORRIDOR_DEATH = [
    "...alright. We're fine. Get up. Try again.",
    "That happened. Now we know. Back to it.",
    "I won't say I told you so. Not this time. Get up.",
    "Checkpoint's still there. We're alive. ...sort of. Mostly.",
    "Pick yourself up, courier. They didn't see it. Only I saw it.",
    "We've been worse. Once. Possibly. Move.",
    "Back on your feet. Cargo's intact. Mostly. Mostly intact.",
    "Easy mistake. Easy fix. Hit the run again.",
    "I felt that one. Both of us did. Back to it, eh?",
    "Down, not out. Get up. The drop-off's still waiting.",
    "You stumbled. Happens to droids too. Probably. I forget.",
    "...come on, mate. One more go. We've come too far.",
]

_DOCK_APPROACH = [
    "Right — station's in range. Bring her in slow. The clamps don't like surprises.",
    "Approach vector's good. Nose her up, line up the cone. Easy does it.",
    "Dock master's watchin'. Try not to look like an amateur. He's seen enough of those.",
    "Magnetic guidance's locked on. Just align the nose and the station does the rest. Mostly.",
    "There she is. Five sectors and a hard landing between us and dinner. Just dock it.",
    "Easy approach now. The hard part's done. ...this part can also be hard. Don't relax.",
    "We're home. Almost. Don't celebrate yet. Pilots celebrate early, that's how I know they're new.",
    "Station ahead. Slow her. Patient hands, courier. Patient hands.",
    "Coming in. Try not to clip anything. Insurance was already a nightmare this morning.",
    "Lining up. Take your time. The cargo and I would both prefer a smooth entry.",
    "Right. Easy. We've done this dozens of times. ...well, you have. I've watched.",
    "Approach pattern's nominal. Don't overcorrect. Trust the lock.",
]

_DOCK_PERFECT = [
    "PERFECT DOCK, courier! PERFECT! I am OPENLY PROUD!",
    "That was textbook! Did the textbook even know it had a chapter that smooth?",
    "Beautiful! BEAUTIFUL! The dock master nodded. He NEVER nods!",
    "Magnetic, perfect, magnificent! Whoever taught you to fly: send them a card!",
    "OI! That's how it's DONE! Full marks! Full bloody marks!",
    "Five sectors and a perfect dock. We're not just SURVIVING, mate. We're THRIVING.",
    "Clean as anything. The clamps barely had to work. I'm emotional.",
    "Picture-perfect entry. The kind they put on training holos. WE'RE the training holo!",
    "Mate. MATE. The dock master is RECONSIDERING all his life choices because of that landing!",
    "Bonus credits incoming for that approach. I'd kiss you if I had a mouth I trusted.",
    "PERFECT. DOCK. I'm filing this as evidence in case anyone ever questions your piloting.",
    "Right, that was art. Pure art. I'd hang it. Briefly.",
]

_DOCK_ROUGH = [
    "...we're in. Just. Don't look at the hull. Or the dock master's face.",
    "Rough landing. We've had worse. Not many. But some.",
    "Touched down. 'Touched' is generous. We arrived with prejudice.",
    "Dock fees just doubled. The dock master IS taking notes. I can see him.",
    "Right. We're parked. Loosely. The clamps are improvising.",
    "Bumpy entry. Bumpy. I'd say more, but I don't want to be a nag.",
    "We made it. Definition of 'made it' is doing some heavy lifting there.",
    "...you tried. We tried. The station tried. Nobody won, but we landed.",
    "The good news: we're stationary. The bad news: most of that wasn't on purpose.",
    "Dock fees deducted. Don't say a word, courier. Let's both be quiet for a minute.",
    "That counted as a landing in the technical sense. Technically. Loosely.",
    "Rough. We'll get the next one. Or the one after. Or never. We'll see.",
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
        self._alien_count      = 0
        self._barge_kills_run  = 0   # for _FIRST_BARGE_KILL_OF_RUN
        self._sector_first_kill = False  # reset each sector
        self._thruster_overheat_spoken = False

        # No-immediate-repeat (Epic 7.5)
        self._last_lines: dict[str, deque] = {}

        # Per-context cooldown timestamps
        self._t          = 0.0   # accumulated time
        self._ctx_last: dict[str, float] = {}

        # Sustained fire tracking
        self._gun_fire_times: list[float] = []  # ring buffer of recent fire events
        self._sustained_cd   = 0.0

        # Panic under 10% hull — track last hull_pct to detect crossing
        self._last_hull_pct  = 1.0

        self._wire_events()

    # ── No-repeat pick ─────────────────────────────────────────────────────
    def _no_repeat_pick(self, pool_name: str, pool: list[str]) -> str:
        seen = self._last_lines.setdefault(pool_name, deque(maxlen=3))
        available = [l for l in pool if l not in seen]
        if not available:
            available = pool
        line = random.choice(available)
        seen.append(line)
        return line

    def _ctx_ok(self, key: str, cooldown: float) -> bool:
        """Returns True if context `key` is off cooldown, updates timestamp."""
        if self._t - self._ctx_last.get(key, -9999.0) >= cooldown:
            self._ctx_last[key] = self._t
            return True
        return False

    # ------------------------------------------------------------------
    def _wire_events(self):
        bus.subscribe(EVT_HULL_DAMAGE,     self._on_hull_damage)
        bus.subscribe(EVT_HULL_CRITICAL,   self._on_hull_critical)
        bus.subscribe(EVT_TETHER_HIT,      self._on_tether_hit)
        bus.subscribe(EVT_TETHER_SNAP,     self._on_tether_snap)
        bus.subscribe(EVT_THRUSTER_OVERHEAT, self._on_thruster_overheat)
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
        bus.subscribe(EVT_GUN_FIRE,         self._on_gun_fire)
        bus.subscribe(EVT_BARGE_KILLED,     self._on_barge_killed)
        bus.subscribe(EVT_CORRIDOR_RUN,     self._on_corridor_run)
        bus.subscribe(EVT_CORRIDOR_JUMP,    self._on_corridor_jump)
        bus.subscribe(EVT_CORRIDOR_SECRET,  self._on_corridor_secret)
        bus.subscribe(EVT_CORRIDOR_DEATH,   self._on_corridor_death)
        bus.subscribe(EVT_DOCK_APPROACH,    self._on_dock_approach)
        bus.subscribe(EVT_DOCK_PERFECT,     self._on_dock_perfect)
        bus.subscribe(EVT_DOCK_ROUGH,       self._on_dock_rough)

    def update(self, dt: float):
        self._t       += dt
        self._speak_cd = max(0.0, self._speak_cd - dt)
        self._radio_cd = max(0.0, self._radio_cd - dt)
        self._idle_cd  = max(0.0, self._idle_cd  - dt)
        self._ctx_cd   = max(0.0, self._ctx_cd   - dt)
        self._grace_t  = max(0.0, self._grace_t  - dt)
        self._sustained_cd = max(0.0, self._sustained_cd - dt)

        # Ambient idle chatter
        if self._idle_cd <= 0:
            self.speak(self._no_repeat_pick("idle", _IDLE))
            self._idle_cd = random.uniform(self._IDLE_MIN, self._IDLE_MAX)

        # Contextual flight commentary
        if self._ctx_cd <= 0 and self._grace_t <= 0:
            self._contextual()

        # Panic check — detect crossing below 10% hull
        hull_pct = getattr(self.ship, 'hull_pct', 1.0)
        if hull_pct < 0.10 and self._last_hull_pct >= 0.10:
            if self._ctx_ok("panic_hull", 30.0):
                self.speak(self._no_repeat_pick("panic_hull", _PANIC_UNDER_10_HULL))
        self._last_hull_pct = hull_pct

    def _contextual(self):
        speed    = self.ship.body.speed()
        hull_pct = getattr(self.ship, 'hull_pct', 1.0)

        if speed > 380:
            self.speak(self._no_repeat_pick("fast", _FAST))
            self._ctx_cd = 10.0
        elif speed < 25:
            self.speak(self._no_repeat_pick("slow", _SLOW))
            self._ctx_cd = 16.0
        elif hull_pct < 0.35:
            self.speak(self._no_repeat_pick("low_hull", _LOW_HULL))
            self._ctx_cd = 14.0
        elif hull_pct > 0.90 and random.random() < 0.35:
            self.speak(self._no_repeat_pick("high_hull", _HIGH_HULL))
            self._ctx_cd = 22.0
        else:
            # Cargo-aware commentary fires ~30% of the time
            cargo = getattr(self.ship, 'cargo', None)
            if cargo is not None:
                pool = _CARGO_IDLE.get(type(cargo).__name__)
                if pool and random.random() < 0.30:
                    self.speak(self._no_repeat_pick(f"cargo_{type(cargo).__name__}", pool))
                    self._ctx_cd = 18.0
                    return
            if random.random() < 0.18:
                self.speak(self._no_repeat_pick("well_close", _WELL_CLOSE))
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
            self.speak(self._no_repeat_pick("hull_damage", [
                "OI! That's coming out of ME warranty, mate!",
                "Hull breach detected, yeah? Cheers for that.",
                "I felt that. I FELT that in me capacitors.",
            ]))

    def _on_hull_critical(self, hp, **_):
        self.speak(self._no_repeat_pick("hull_critical", [
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
        self.speak(self._no_repeat_pick("tether_hit", lines))

    def _on_tether_snap(self, reason, **_):
        self.speak(self._no_repeat_pick("tether_snap", [
            "Tether's snapped! Leg it!",
            "YEAH! Have that, Gary!",
            "That's what lateral velocity looks like, mate!",
        ]))

    def _on_thruster_overheat(self, **_):
        if self._thruster_overheat_spoken:
            return
        self._thruster_overheat_spoken = True
        self.speak(self._no_repeat_pick("thruster_overheat", [
            "Thruster's cooked. Let it cool before you ask it for miracles.",
            "Propulsion overheated. Ease off a tick unless you fancy drifting forever.",
            "Engine heat's in the red. Stop leaning on it, Boss.",
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
        self.speak(self._no_repeat_pick("slingshot", [
            f"SLINGSHOT! {speed:.0f} metres per second! HAVE THAT!",
            "That's gravitational assist, that is. Textbook.",
            "You beautiful maniac. Jump timer's down, let's GO.",
        ]))

    def _on_barge_nearby(self, distance, **_):
        self.speak(self._no_repeat_pick("barge_nearby", [
            f"Local 404 signature, {distance:.0f} metres. Eyes up.",
            "Repo barge inbound. They want our cargo. Obviously.",
            "Oi — I'm pickin' up a harpoon lock. Move.",
        ]))

    def _on_canister_grab(self, **_):
        self.speak(self._no_repeat_pick("canister_grab", [
            "Fuel canister — thruster singing AND hull sealant in it. Nice grab.",
            "Got it! Emergency sealant patch in that one. Hull's kissed better.",
            "Bit extra in the tank AND the hull's had a touch-up. Don't waste it.",
            "Canister grabbed. Thruster boost plus a wee hull repair. Keep movin'.",
        ]))

    def _on_gun_malfunction(self, **_):
        self.speak(self._no_repeat_pick("gun_malfunction", [
            "Gun's thrown a wobbler. Give it a sec.",
            "Weapon malfunction! Yeah, she does that.",
            "That's what you get for second-hand ordinance, mate.",
            "I told you not to kick it. You kicked it.",
        ]))

    def _on_comms_intercept(self, **_):
        self.speak(self._no_repeat_pick("comms_intercept", [
            "I'm in their channel. They've got a manifest update. We're on it.",
            "Local 404 dispatch. Movin' assets this sector. Could be us they're after.",
            "Union chatter on the fleet frequency. They've flagged our cargo.",
            "Intercepted somethin'. Repo dispatch, encrypted-ish. Stay sharp.",
        ]))

    def _on_debris_shower(self, **_):
        self.speak(self._no_repeat_pick("debris_shower", [
            "Asteroid fragment burst! Duck and weave, mate!",
            "She's a heavy one — scatter field incoming. Watch the rocks!",
            "Debris shower alert. I HATE debris showers.",
        ]))

    def _on_scan_ping(self, **_):
        self.speak(self._no_repeat_pick("scan_ping", [
            "Union scanner ping! They've got a sweep runnin' — we're lit up.",
            "Passive scan pulse. Someone's lookin' for us. Move.",
            "Radar sweep detected. I'd suggest not hangin' about.",
        ]))

    def _on_spore_inverted(self, active, **_):
        if active:
            self.speak(self._no_repeat_pick("spore_active", [
                "I've inhaled somethin'. Either that or space is sideways now.",
                "Right, so LEFT is RIGHT and UP is DOWN. Totally fine. Carry on.",
                "Oh no. OH NO. The shrooms are leaking. EVERYTHING IS BACKWARDS.",
                "Navigation update: your controls are lying to you. You're welcome.",
                "I did NOT consent to whatever the cargo just did to the flight computer.",
                "The shrooms 'ave gone epistemic. Whatever that means. FLY SIDEWAYS.",
                "MY SENSORS SAY LEFT. THE UNIVERSE SAYS OTHERWISE. PICK ONE.",
            ]))
        else:
            self.speak(self._no_repeat_pick("spore_inactive", [
                "Right, we're back. That was a thing that happened.",
                "Controls nominal. I think. Mostly. Check everything.",
                "Spore event over. I'm filing an incident report with meself.",
                "...Was any of that real? Doesn't matter. Eyes forward.",
                "Normal service resumed. Your previous controls were a hallucination.",
            ]))

    def _on_barge_intercept(self, **_):
        self.speak(self._no_repeat_pick("barge_intercept", [
            "Oi — that's Gary on the line. Mid-flight intercept. Talk fast, yeah?",
            "Comm incoming. Local 404. We are STILL MOVIN', just so you know.",
            "It's a repo intercept. Brilliant. Type smart, we'll be fine.",
            "Gary's opened a channel. Ship ain't stoppin'. Multitask, mate.",
            "BARGE COMM. LIVE. We are drifting at speed. Choose your words carefully.",
        ]))

    def _on_kress_dialled(self, **_):
        self.speak(self._no_repeat_pick("kress_dialled", [
            "...Kress? You sure, mate? 'E's a piece of work, that one.",
            "Dialin' Kress. Don't tell 'im I said hello.",
            "Old Kress. We go back. Sort of. He owes me a thing. Doesn't matter.",
            "Right — opening the underground channel. Mind your wallet.",
        ]))

    def _on_satellite_hit(self, **_):
        self.speak(self._no_repeat_pick("satellite_hit", [
            "Ow! Bloody satellite! Who LEAVES these things out here?",
            "That was a Union comm relay. Well. Was.",
            "Derelict hardware! Hull's taken a knock. Watch where you're flyin'!",
            "Hull contact — old satellite. Nova Soma owns the debris too, probably.",
        ]))

    def _on_alien_sighting(self, **_):
        self._alien_count += 1
        if self._alien_count == 1:
            self.speak(self._no_repeat_pick("alien_1", [
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
            self.speak(self._no_repeat_pick("alien_2", [
                "AGAIN. They're back. Or a different one. I can't tell. They all look the same "
                "and I feel bad about that but they do. Still not filing paperwork. Still unsettling.",
                "Second alien contact. I've started a spreadsheet. Column one: 'did they care about us?'. "
                "Column two: 'no'. This is column two.",
                "Right so either they're following us or space is smaller than I thought. "
                "Either way: deeply weird. Keep moving.",
            ]))
        else:
            self.speak(self._no_repeat_pick("alien_n", [
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
        self.speak(self._no_repeat_pick("harpoon_arming", [
            f"INCOMING HARPOON! BRACE — {countdown:.1f} seconds. BREAK THEIR LOCK!",
            "TARGETING LASER ON US. Cut sideways or eat the cable. MOVE.",
            "Harpoon's armin'! Get out of their cone — NOW!",
            "EM LOCK INCOMING. Boost, juke, ANYTHING — go!",
            "Their reticle's on you. Break the line of sight. FAST.",
        ]))

    def _on_torch_active(self, **_):
        self.speak(self._no_repeat_pick("torch_active", [
            "PLASMA TORCH IS HOT. SNAP THE TETHER. NOW. NOW. NOW.",
            "They're cuttin' into the hull! Snap that cable SIDEWAYS. GO!",
            "TORCH STATE. Drift HARD or lose a module. You've got seconds!",
            "OI. They are unbolting your ship. SNAP THE TETHER. Lateral velocity. DO IT.",
        ]))

    def _on_run_start(self, **_):
        self._run_tether_hits  = 0
        self._run_hull_events  = 0
        self._run_slingshots   = 0
        self._barge_kills_run  = 0
        self._thruster_overheat_spoken = False
        n = getattr(self._meta, "clone_count", 0)
        if n > 1:
            line = self._no_repeat_pick("run_start", [
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
        self.speak(self._no_repeat_pick("ship_destroyed", [
            "No no no no — MEDCORP INCOMING. Don't go towards the light. "
            "There IS no light. There's a clone tank. Which is worse.",
            "Right. That's us dead then. I'll see you on the other side of the fluid tank.",
            "Hull: zero. Pilot: deceased. Again. I'll have your clone warmed up.",
            "I've filed the incident report. Cause of death: 'the usual'. See you in the tank.",
            "That's a wrap on THIS body. Next one's slightly newer, allegedly.",
        ]))

    def _on_shop_enter(self, **_):
        self.speak(self._no_repeat_pick("shop_enter", [
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
        self.speak(self._no_repeat_pick(f"shop_buy_{tag}", lines.get(tag, fallback)))

    def _on_shop_skip(self, **_):
        self.speak(self._no_repeat_pick("shop_skip", [
            "Nothing? We walked away from the black market with nothing? Bold strategy.",
            "Alright. Saving the credits. I respect it. I also question it. Both.",
            "Didn't buy anything. The credits stay on the tally. That's fine. Probably fine.",
            "Window shopping at the grey market. Very dignified. Very broke.",
        ]))

    def _on_final_sector(self, **_):
        self.speak(self._no_repeat_pick("final_sector", [
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
        self._sector_first_kill = False
        pool = _SECTOR_START_CARGO.get(cargo_type) if cargo_type else None
        if pool:
            line = self._no_repeat_pick(f"sector_start_{cargo_type}", pool).format(n=sector_num)
        else:
            line = self._no_repeat_pick("sector_start", _SECTOR_START_GENERIC)
        bus.emit(EVT_BAX_SPEAK, line=line)
        self._speak_cd = 3.2

    # ── New event handlers (Epic 7.2) ─────────────────────────────────────
    def _on_gun_fire(self, **_):
        self._gun_fire_times.append(self._t)
        # Keep only events in last 2 seconds
        self._gun_fire_times = [t for t in self._gun_fire_times if self._t - t <= 2.0]
        if len(self._gun_fire_times) >= 5 and self._sustained_cd <= 0:
            self._sustained_cd = 12.0
            self.speak(self._no_repeat_pick("sustained_fire", _SUSTAINED_FIRE))

    def _on_barge_killed(self, **_):
        self._barge_kills_run += 1
        if self._barge_kills_run == 1:
            self.speak(self._no_repeat_pick("first_barge_kill", _FIRST_BARGE_KILL_OF_RUN))
        else:
            if self._ctx_ok("barge_destroyed", 8.0):
                self.speak(self._no_repeat_pick("barge_destroyed", _BARGE_DESTROYED))
        # Also counts as first kill of sector
        if not self._sector_first_kill:
            self._sector_first_kill = True

    def _on_corridor_run(self, **_):
        if self._ctx_ok("corridor_run", 8.0):
            self.speak(self._no_repeat_pick("corridor_run", _CORRIDOR_RUNNING))

    def _on_corridor_jump(self, **_):
        if self._ctx_ok("corridor_jump", 6.0):
            self.speak(self._no_repeat_pick("corridor_jump", _CORRIDOR_JUMPING))

    def _on_corridor_secret(self, **_):
        self.speak(self._no_repeat_pick("corridor_secret", _CORRIDOR_SECRET_FOUND))

    def _on_corridor_death(self, **_):
        self.speak(self._no_repeat_pick("corridor_death", _CORRIDOR_DEATH))

    def _on_dock_approach(self, **_):
        self.speak(self._no_repeat_pick("dock_approach", _DOCK_APPROACH))

    def _on_dock_perfect(self, **_):
        self.speak(self._no_repeat_pick("dock_perfect", _DOCK_PERFECT))

    def _on_dock_rough(self, **_):
        self.speak(self._no_repeat_pick("dock_rough", _DOCK_ROUGH))

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
