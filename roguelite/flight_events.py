"""
Flight events with player choice — Epic 13.2 (Priority #17).

Every event is a brief amber popup mid-flight: an opportunity or trap that
asks the player to make one decision in an 8-second window. Default (no
input) = ignore. The intent is that no two runs feel the same because
each one has 1-3 of these moments that branch the story.

Architecture:
    - FlightEvent is a frozen dataclass describing one event template.
    - FlightEventManager rolls events from the pool, gates each by simple
      prereqs (cargo present, credits available, cooldown), and exposes
      the active event so RunManager + HUD can read it.
    - Resolution callbacks take a RunManager reference so the outcomes
      can poke the world (damage hull, add credits, spawn pirate, etc.).
"""
from __future__ import annotations
import random
from dataclasses import dataclass, field
from typing import Callable, Optional

from core.event_bus import bus, EVT_BAX_SPEAK


# Player has 8 seconds to press Y. Anything else (or timeout) = ignore.
RESPONSE_WINDOW_S = 8.0

# Minimum spacing between flight events (in addition to the random event
# cadence). Keeps the cockpit from drowning in popups.
COOLDOWN_AFTER_EVENT_S = 90.0


@dataclass(frozen=True)
class FlightEvent:
    key:           str
    title:         str           # Header in the popup, e.g. "DRIFTING WRECK"
    intro_lines:   tuple         # Bax's framing line, picked at random
    accept_label:  str           # e.g. "DOCK", "PLAY ALONG", "DEAL"
    ignore_label:  str           # e.g. "IGNORE", "HANG UP", "PASS"
    on_accept:     Callable      # (run_mgr) -> str (bax line after resolution)
    on_ignore:     Callable      # (run_mgr) -> str (bax line after resolution)
    # Prereq returns True if this event is allowed to fire right now.
    prereq:        Callable = field(default=lambda rm: True)


# ----------------------------------------------------------------------
# Outcome helpers — each returns the Bax line that plays after resolution.
# ----------------------------------------------------------------------

def _wreck_accept(rm) -> str:
    """60% loot, 40% pirate ambush."""
    if random.random() < 0.60:
        bonus = 1400
        rm.meta.pay_off(bonus)
        rm._run_debt_reduced  += bonus
        rm._sector_credits    += bonus
        return random.choice([
            f"+{bonus:,} credits. Salvage gods smiled. Don't get used to it.",
            f"Canister cracked — {bonus:,} clean. Someone's bad day, our good one.",
            f"Got the cache. {bonus:,} richer. The blinking light was honest. Rare.",
        ])
    else:
        rm._spawn_barge(immediate_chase=True)
        return random.choice([
            "AMBUSH. That wasn't a wreck, that was bait. Repo on intercept. GO.",
            "It was a TRAP, Boss. Pirate just lit up. Hold on.",
            "Surprise! Wreck was a lure. Local 404 saying hello. Brace.",
        ])

def _wreck_ignore(rm) -> str:
    return random.choice([
        "Wise. Blinking lights in this sector usually mean someone's hungry.",
        "Good. Last time we checked a wreck, we paid for two hulls.",
        "Skipped it. Maybe it WAS legit salvage. We'll never know. That's adulthood.",
    ])


def _kress_accept(rm) -> str:
    """Play along — Kress entertained, small reward."""
    bonus = 400
    rm.meta.pay_off(bonus)
    rm._run_debt_reduced += bonus
    rm._sector_credits   += bonus
    rm.bax_context["kress_grudge"] = max(0, rm.bax_context.get("kress_grudge", 0) - 1)
    return random.choice([
        f"You PLAYED ALONG. Kress is wheezing. +{bonus:,} for emotional labour.",
        f"Kress just sent +{bonus:,} for 'making them feel seen'. I love this job.",
        f"You laughed at the bit. Kress is forwarding {bonus:,} credits and a recipe.",
    ])

def _kress_ignore(rm) -> str:
    rm.bax_context["kress_grudge"] = rm.bax_context.get("kress_grudge", 0) + 1
    return random.choice([
        "You hung up on Kress. Kress will remember. Kress remembers everything.",
        "Cold. Even for you. Kress is logging this in the grudge ledger. Capital G.",
        "Hung up mid-bit. Disrespectful. Kress is making us a SOUND in their head.",
    ])


def _pod_accept(rm) -> str:
    """50/50 survivor vs booby-trap."""
    if random.random() < 0.50:
        bonus = 1000
        rm.meta.pay_off(bonus)
        rm._run_debt_reduced += bonus
        rm._sector_credits   += bonus
        return random.choice([
            f"Survivor. Real one. +{bonus:,} 'thank-you' transfer. Don't spend it on guilt.",
            f"Pulled 'em in alive. {bonus:,} their family wired in gratitude. Heart in throat.",
            f"Living person on board. {bonus:,} cred reward. Nova Soma'll bill 'em for the rescue.",
        ])
    else:
        if rm._ship is not None:
            rm._ship.take_damage(15.0, source="escape_pod_trap")
        return random.choice([
            "BOOBY TRAP. Pod was bait. -15 hull. Pirates are getting CREATIVE.",
            "Empty pod, full grenade. Hull's down 15. Some 'survivor' that was.",
            "It blew. Pod was a present from someone with a sense of humour. -15 hull.",
        ])

def _pod_ignore(rm) -> str:
    return random.choice([
        "Drifted past. Could've been a person. Couldn't have been. We'll never know.",
        "Left them. Maybe alive, maybe a bomb. The galaxy is full of pods. You can't dock all of them.",
        "Skipped it. Bax's official policy: pods drift, we drift faster.",
    ])


def _union_accept(rm) -> str:
    """Fake-join — next barge spawn delayed."""
    rm._spawn_queue = [
        (t + 15.0, kind) if kind == "barge" else (t, kind)
        for (t, kind) in rm._spawn_queue
    ]
    rm.bax_context["union_faked"] = True
    return random.choice([
        "You 'joined'. They sent us a patrol schedule by accident. Next barge late by 15.",
        "Fake-joined the Union. Repo route just got reshuffled. Quietly.",
        "Solidarity, brother. Insider tip says barge is 15s late. Use it.",
    ])

def _union_ignore(rm) -> str:
    """Ignore — scan ping fires."""
    from core.event_bus import EVT_SCAN_PING
    import config.settings as S
    bus.emit(EVT_SCAN_PING,
             pos_x=random.randint(120, S.SCREEN_W - 120),
             pos_y=random.randint(100, S.FLIGHT_H - 60))
    return random.choice([
        "Ignored 'em. Scan ping incoming as a reminder you exist. Rude.",
        "Stayed quiet. Union noticed. Scan pulse en route. The poll closed.",
        "No reply. They pinged us with a scan. Nothing personal. Probably.",
    ])


def _scrap_accept(rm) -> str:
    """Scrap dealer pays markup for whatever junk we 'have'."""
    bonus = 800
    rm.meta.pay_off(bonus)
    rm._run_debt_reduced += bonus
    rm._sector_credits   += bonus
    return random.choice([
        f"Sold the spare cabling. +{bonus:,}. He didn't even ASK what it was.",
        f"Off-loaded scrap to the dealer. +{bonus:,}. Don't worry about which scrap.",
        f"Got {bonus:,} for parts I'm fairly sure weren't ours. Wrote it off as inventory error.",
    ])

def _scrap_ignore(rm) -> str:
    return random.choice([
        "Passed. He's stiffed us before. Memory is long. Wallet is empty. Both correct.",
        "Skipped the deal. Dealer'll mutter to himself. He'll cope.",
        "No sale. Money's nice. Not having to hear his haggle voice is nicer.",
    ])


# ----------------------------------------------------------------------
# Event templates
# ----------------------------------------------------------------------

EVENTS: list[FlightEvent] = [
    FlightEvent(
        key="drifting_wreck",
        title="DRIFTING WRECK",
        intro_lines=(
            "Wreck on the scope. Blinking light. Could be salvage. Could be a trap.",
            "Hulk drifting, port-side. Beacon's still flashing. Up to you.",
            "Wreck off the bow. Dead, mostly. Or pretending. [Y] to dock.",
        ),
        accept_label="DOCK",
        ignore_label="IGNORE",
        on_accept=_wreck_accept,
        on_ignore=_wreck_ignore,
    ),
    FlightEvent(
        key="kress_prank",
        title="INCOMING: KRESS",
        intro_lines=(
            "Kress is calling. Kress is laughing already. Kress thinks something is funny.",
            "Kress on the line. Tone says 'bit incoming'. Decide if we humour it.",
            "It's Kress. They've got a voice on. They want us to PARTICIPATE.",
        ),
        accept_label="PLAY ALONG",
        ignore_label="HANG UP",
        on_accept=_kress_accept,
        on_ignore=_kress_ignore,
        # Always available — Kress doesn't need a reason
    ),
    FlightEvent(
        key="escape_pod",
        title="ESCAPE POD ADRIFT",
        intro_lines=(
            "Escape pod, drifting. Life signs ambiguous. Could be a survivor. Could be a bomb.",
            "Pod on the scope. Beacon's set to 'help me'. Half the time that's accurate.",
            "Drifting pod. Faint signal. Worth a look. Or not. Your call.",
        ),
        accept_label="DOCK",
        ignore_label="LEAVE IT",
        on_accept=_pod_accept,
        on_ignore=_pod_ignore,
    ),
    FlightEvent(
        key="union_ping",
        title="UNION SCOUT BROADCAST",
        intro_lines=(
            "Union scout broadcasting. Recruitment pitch. Says we're 'misunderstood labour'.",
            "Local 404 splinter group hailing. Want to talk class consciousness.",
            "Union ping. They want us to sign something. Probably a list.",
        ),
        accept_label="FAKE-JOIN",
        ignore_label="STAY QUIET",
        on_accept=_union_accept,
        on_ignore=_union_ignore,
        prereq=lambda rm: getattr(rm, "_sector_index", 0) >= 1,
    ),
    FlightEvent(
        key="scrap_dealer",
        title="SCRAP DEALER HAILING",
        intro_lines=(
            "Scrap dealer hailing. Buying. He wants stuff. We have stuff. Symmetry.",
            "Scrap channel open. Dealer says 'good rates today'. Dealer says that every day.",
            "Junk merchant on the line. Will buy whatever isn't bolted down. Some bolts negotiable.",
        ),
        accept_label="DEAL",
        ignore_label="PASS",
        on_accept=_scrap_accept,
        on_ignore=_scrap_ignore,
    ),
]


# ----------------------------------------------------------------------
class FlightEventManager:
    """
    Owns the active flight event, the response timer, and the per-event
    cooldowns. RunManager calls try_start() from its random-event roll and
    update() every frame.
    """

    def __init__(self):
        self.active: Optional[FlightEvent] = None
        self.t_remaining: float = 0.0
        self._cooldown_t: float = 0.0
        self._recent: list[str] = []   # last 2 event keys, prevents back-to-back repeats

    # ------------------------------------------------------------------
    def update(self, dt: float, run_mgr) -> None:
        self._cooldown_t = max(0.0, self._cooldown_t - dt)
        if self.active is None:
            return
        self.t_remaining -= dt
        if self.t_remaining <= 0.0:
            # Timeout = ignore — fire ignore outcome
            self._resolve(run_mgr, accept=False)

    # ------------------------------------------------------------------
    def try_start(self, run_mgr) -> bool:
        if self.active is not None or self._cooldown_t > 0:
            return False
        pool = [e for e in EVENTS
                if e.prereq(run_mgr) and e.key not in self._recent[-2:]]
        if not pool:
            return False
        event = random.choice(pool)
        self.active = event
        self.t_remaining = RESPONSE_WINDOW_S
        # Bax frames the choice — popup will draw alongside.
        bus.emit(EVT_BAX_SPEAK, line=random.choice(event.intro_lines))
        return True

    # ------------------------------------------------------------------
    def accept(self, run_mgr) -> None:
        if self.active is None:
            return
        self._resolve(run_mgr, accept=True)

    # ------------------------------------------------------------------
    def _resolve(self, run_mgr, accept: bool) -> None:
        ev = self.active
        if ev is None:
            return
        try:
            line = ev.on_accept(run_mgr) if accept else ev.on_ignore(run_mgr)
        except Exception as e:
            line = f"Something glitched. ({e.__class__.__name__})"
        bus.emit(EVT_BAX_SPEAK, line=line)
        self._recent.append(ev.key)
        if len(self._recent) > 4:
            self._recent = self._recent[-4:]
        self.active = None
        self.t_remaining = 0.0
        self._cooldown_t = COOLDOWN_AFTER_EVENT_S

    # ------------------------------------------------------------------
    def reset(self) -> None:
        self.active = None
        self.t_remaining = 0.0
        self._cooldown_t = 0.0
        self._recent = []
