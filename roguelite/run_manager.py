from __future__ import annotations
import random
import pygame
from roguelite.procedural import generate_sector, SectorLayout
from roguelite.loadout_draft import LoadoutDraft
from roguelite.meta_progression import MetaProgression
from roguelite.tutorial import TutorialManager
from antagonists.repo_barge import RepoBarge
from antagonists.debris import DebrisRock
from antagonists.fuel_canister import FuelCanister
from antagonists.satellite import SpinningSatellite
from antagonists.alien_ship import AlienShip
from terminal.terminal import Terminal
from terminal.npc_logic import make_npc
from core.event_bus import (bus, EVT_SECTOR_CLEAR, EVT_RUN_END,
                             EVT_SLINGSHOT, EVT_BARGE_NEARBY, EVT_CANISTER_GRAB,
                             EVT_COMMS_INTERCEPT, EVT_DEBRIS_SHOWER, EVT_SCAN_PING,
                             EVT_COMMS_SPEAK, EVT_TETHER_SNAP, EVT_BAX_SPEAK,
                             EVT_SATELLITE_HIT, EVT_ALIEN_SIGHTING, EVT_DEMO_NOTICE,
                             EVT_JUMP_READY, EVT_WARP_JUMP, EVT_FINAL_SECTOR,
                             EVT_RUN_START, EVT_SHOP_ENTER, EVT_SECTOR_START)
from config import settings as S


# ---------------------------------------------------------------------------
_KRESS_LINES = [
    "What in the seven hells are you doing out there? "
    "I am LOOKING at your trajectory. A drunk pigeon has better spatial awareness.",

    "Do you know what this cargo is worth? OF COURSE YOU DON'T "
    "because you failed basic numeracy THREE TIMES.",

    "I swear on the Union's pension fund, if you scratch that hull again, "
    "I am docking your clone allowance.",

    "The other couriers don't do this. SANDRA doesn't do this. "
    "Sandra has ZERO hull incidents. You are worse than Sandra.",

    "I'm getting a reading that says your ship is worth negative forty credits. "
    "That's not a typo. NEGATIVE. FORTY.",

    "JUST JUMP. JUMP THE SECTOR. WHY ARE YOU STILL IN THIS SECTOR. JUMP.",

    "Your debt is visible from orbit. I mean that literally. "
    "The creditors have a telescope.",

    "We had a meeting about you. It lasted four hours. "
    "No one said anything nice. I checked the minutes.",

    "You have the survival instincts of a tax form. DO SOMETHING.",

    "I hired you because you were cheap. I now understand why you were cheap.",
]

_DEMO_NOTICES = [
    ("GALACTIC INFRA.",
     "NOTICE: This sector is scheduled for clearance to accommodate Hyperspace Bypass Route 7-B. "
     "A planning notice was displayed at Nova Soma Central Admin for thirty seconds. "
     "Your concerns have been logged and disregarded."),

    ("GALACTIC INFRA.",
     "COMPULSORY ACQUISITION ORDER REF. SPC-7742: The route you are currently occupying "
     "has been allocated for infrastructure development. Resistance is noted as non-compliant. "
     "Have a productive existence."),

    ("GALACTIC INFRA.",
     "This message constitutes the legally required notification of demolition works. "
     "Residents were informed. Nobody they could find, but they were informed. "
     "Works commence regardless. Please clear the sector."),

    ("GALACTIC INFRA.",
     "A bypass corridor has been approved through this sector. "
     "The review committee met once, in a restaurant, and agreed. "
     "We appreciate your cooperation is not required."),

    ("GALACTIC INFRA.",
     "INFRASTRUCTURE UPDATE: The homes and livelihoods of this sector "
     "have been assessed as non-core assets and will be repurposed. "
     "Compensation forms are available. They have not been printed yet."),
]

_COLLECTOR_LINES = [
    ("MEDI-CORP",
     "Hello. This is a courtesy call from MediCorp Genomics regarding your outstanding "
     "clone fluid balance. We do hope your new body is treating you well. It won't for long. Pay up."),

    ("MEDI-CORP",
     "We notice you've been cloned again. Congratulations on not dying permanently. "
     "Your bill has been updated accordingly. Have a productive existence."),

    ("MEDI-CORP",
     "Your clone account is in arrears. We are legally permitted to reduce "
     "next-body quality. Enjoy your current teeth while you have them."),

    ("DOCK-7",
     "Dock Seven Salvage and Repair. We've been patient. We've been reasonable. "
     "We've been neither of those things, actually. Where's our money."),

    ("DOCK-7",
     "This is automated message four hundred and twelve regarding your outstanding "
     "hull repair invoice. You owe us more than your ship is worth. We checked."),

    ("DOCK-7",
     "Sir or madam, our records show you have not paid your repair bill since "
     "the Third Republic. That is not an exaggeration. Pay us."),

    ("DOCK-7",
     "We have your previous hull on a shelf. We're going to keep it. "
     "Not for any legal reason. We just want you to know we have it."),

    ("REP. LEGAL",
     "Union of Repo Men, Legal Division. We've been authorized to inform you "
     "that Local 404 has filed a lien on your soul. This is legally binding in twelve sectors."),

    ("REP. LEGAL",
     "You are in violation of Clause 9, Sub-section F of the Repo Charter: "
     "fleeing a lawful harpoon. The fine is your entire net worth. "
     "We've confirmed this is a very easy fine to calculate."),
]


class RunManager:
    """
    Manages a single run: sector progression, barge spawning,
    debris fields, fuel canisters, bullet-rock collision, random events.
    """

    def __init__(self, meta: MetaProgression):
        self.meta              = meta
        self.draft             = LoadoutDraft(chapter=1)
        self._sector_index     = 0
        self._sector: SectorLayout | None = None
        self._barges: list[RepoBarge]     = []
        self._debris: list[DebrisRock]    = []
        self._canisters: list[FuelCanister] = []
        self._satellites: list[SpinningSatellite] = []
        self._alien: AlienShip | None = None
        self._alien_spoken = False
        self._active_terminal: Terminal | None = None
        self._intercepting_barge = None   # set when a barge opens a mid-flight comm
        self._kress_called_this_sector = False
        self._sector_timer     = 0.0
        self._sector_dur       = 20.0
        self._ship             = None

        # Slingshot tracking
        self._sling_well_t: dict[int, float] = {}
        self._sling_cd         = 0.0

        # Proximity alarm cooldown
        self._prox_cd          = 0.0

        # Mid-flight random events (debris shower / scan / comms intercept)
        self._event_cd         = 40.0
        self._shower_rocks: list[DebrisRock] = []
        self._shower_t         = 0.0

        # KRESS and bill-collector transmission timers
        self._kress_cd         = random.uniform(S.KRESS_INTERVAL_MIN, S.KRESS_INTERVAL_MAX)
        self._collector_cd     = random.uniform(S.COLLECTOR_INTERVAL_MIN, S.COLLECTOR_INTERVAL_MAX)

        self._pending_advance  = False
        self._jump_ready_fired = False   # prevents duplicate jump-ready sound per sector
        self._run_debt_reduced = 0   # credits recovered this run (shown in HUD)
        self._run_snaps        = 0   # tether snaps this entire run
        self._run_slingshots   = 0   # slingshots this entire run
        self._shop_pending     = False   # True when a shop stop should open

        # Deferred object spawn queue — (trigger_time, kind) pairs
        # Populated by _spawn_sector_objects(), drained in update()
        self._spawn_queue: list[tuple[float, str]] = []

        # Tutorial — first-run only
        self._tutorial: TutorialManager | None = (
            TutorialManager() if meta.clone_count == 1 else None
        )

        # Per-sector stat tracking for the between-sector flash card
        self._sector_slingshots = 0
        self._sector_snaps      = 0
        self._sector_credits    = 0
        self._sector_start_hull = S.HULL_MAX
        self._flash_t           = 0.0
        self._last_stats: dict | None = None

        bus.subscribe(EVT_CANISTER_GRAB, self._on_canister_grab)
        bus.subscribe(EVT_TETHER_SNAP,   self._on_tether_snap)
        bus.subscribe(EVT_SLINGSHOT,     self._on_slingshot)

    # ------------------------------------------------------------------
    def start_run(self, ship):
        bus.emit(EVT_RUN_START)
        self._sector_index = 0
        self._barges.clear()
        self._debris.clear()
        self._canisters.clear()
        self._satellites.clear()
        self._alien      = None
        self._alien_spoken = False
        self._shower_rocks.clear()
        self._active_terminal    = None
        self._intercepting_barge = None
        self._pending_advance    = False
        self._jump_ready_fired   = False
        self._kress_called_this_sector = False
        self._run_debt_reduced   = 0
        self._run_snaps          = 0
        self._run_slingshots     = 0
        self._shop_pending       = False
        self._sector_slingshots  = 0
        self._sector_snaps       = 0
        self._sector_credits     = 0
        self._sector_start_hull  = ship.hull if ship else S.HULL_MAX
        self._flash_t            = 0.0
        self._last_stats         = None
        self._spawn_queue.clear()
        self._ship = ship
        self.draft = LoadoutDraft(chapter=self._current_chapter())
        self._kress_cd    = random.uniform(S.KRESS_INTERVAL_MIN, S.KRESS_INTERVAL_MAX)
        self._collector_cd = random.uniform(S.COLLECTOR_INTERVAL_MIN, S.COLLECTOR_INTERVAL_MAX)
        ship.reset()

    def apply_draft(self, ship):
        frame  = self.draft.selected_frame
        module = self.draft.selected_module
        cargo  = self.draft.selected_cargo

        ship.hull       = min(S.HULL_MAX, S.HULL_MAX + frame.get("hull_bonus", 0))
        ship.body.mass  = S.SHIP_MASS * frame.get("mass_mod", 1.0)
        ship.chain.install(module, 1)
        ship.cargo      = cargo
        self._ship      = ship

        self._sector    = generate_sector(self._sector_index, self._difficulty())
        self._sector_start_hull = ship.hull
        self._spawn_sector_objects()

        # Bax loadout handoff — frame brief + cargo-specific addendum
        _cargo_launch = {
            "AcousticArchive":        "Bangers in the hold. Don't let 'em nick it.",
            "EpistemologicalShrooms": "Mind the spores. Both of us.",
            "SentientPaperwork":      "The paperwork's already filing itself. Ignore it.",
            "SchrodingerVIP":         "Don't look in the back. Either state is fine until delivery.",
        }
        cargo_type = type(cargo).__name__ if cargo is not None else None
        frame_bax  = frame.get("bax", "She'll fly.")
        cargo_bax  = _cargo_launch.get(cargo_type, "Cargo's aboard.")
        bus.emit(EVT_BAX_SPEAK, line=f"{frame_bax} {cargo_bax}")

        bus.emit(EVT_SECTOR_START, sector_num=1, cargo_type=cargo_type)

    # ------------------------------------------------------------------
    def update(self, dt: float):
        if self._sector is None or self._ship is None:
            return

        self._sector_timer += dt
        self._sling_cd      = max(0.0, self._sling_cd - dt)
        self._prox_cd       = max(0.0, self._prox_cd  - dt)
        self._flash_t       = max(0.0, self._flash_t  - dt)

        # Drain deferred spawns
        due = [item for item in self._spawn_queue
               if item[0] <= self._sector_timer]
        for _, kind in due:
            if kind == "debris":
                self._debris.append(DebrisRock())
            elif kind == "satellite":
                self._satellites.append(SpinningSatellite())
            elif kind == "barge":
                self._spawn_barge()
        if due:
            self._spawn_queue = [item for item in self._spawn_queue
                                 if item[0] > self._sector_timer]

        if not self._jump_ready_fired and self._sector_timer >= self._sector_dur:
            self._jump_ready_fired = True
            bus.emit(EVT_JUMP_READY)

        self._sector.gravity.apply_all(self._ship.body)

        if self._tutorial is not None:
            self._tutorial.update(dt, self)

        cargo = self._ship.cargo
        if cargo is not None:
            if hasattr(cargo, "set_nearest_barge") and self._barges:
                nearest = min((b.pos - self._ship.pos).length() for b in self._barges)
                cargo.set_nearest_barge(nearest)
            if hasattr(cargo, "update"):
                cargo.update(dt, self._ship)

        for barge in self._barges[:]:
            barge.update(dt)
            if barge.is_destroyed:
                self._barges.remove(barge)

        for rock in self._debris:
            rock.update(dt)
            if rock.collides(self._ship.pos):
                self._ship.take_damage(S.DEBRIS_DAMAGE, source="debris")
                rock.hit()

        for can in self._canisters:
            can.update(dt, self._ship.pos)

        # Satellites — update + collision
        for sat in self._satellites[:]:
            sat.update(dt)
            if not sat.alive:
                self._satellites.remove(sat)
                continue
            if sat.collides(self._ship.pos):
                self._ship.take_damage(sat.HULL_DAMAGE, source="satellite")
                sat.hit()
                bus.emit(EVT_SATELLITE_HIT)

        # Alien ship — update, one-time Bax reaction
        if self._alien is not None:
            if self._alien.alive:
                self._alien.update(dt)
                if not self._alien_spoken:
                    self._alien_spoken = True
                    bus.emit(EVT_ALIEN_SIGHTING)
            else:
                self._alien = None

        # Debris shower tick
        if self._shower_t > 0:
            self._shower_t -= dt
            for rock in self._shower_rocks:
                rock.update(dt)
                if rock.collides(self._ship.pos):
                    self._ship.take_damage(S.DEBRIS_DAMAGE, source="debris_shower")
                    rock.hit()
            if self._shower_t <= 0:
                self._shower_rocks.clear()

        # Bullet-rock collision
        self._check_bullets()

        self._check_slingshot()
        self._check_proximity()
        self._check_random_event(dt)
        self._check_comms(dt)

    def handle_key(self, event: pygame.event.Event):
        # Route to cargo's key handler first (e.g. TriplicateForm popup)
        if self._ship is not None and self._ship.cargo is not None:
            if hasattr(self._ship.cargo, "handle_key"):
                if self._ship.cargo.handle_key(event):
                    return
        if event.key == pygame.K_j and self._sector_timer >= self._sector_dur:
            self._open_jump_terminal()
        elif event.key == pygame.K_k and not self._kress_called_this_sector:
            self._open_kress_terminal()

    def _open_kress_terminal(self):
        from core.event_bus import EVT_KRESS_DIALLED
        self._kress_called_this_sector = True
        bus.emit(EVT_KRESS_DIALLED)
        self.open_terminal("kress")

    # ------------------------------------------------------------------
    def _check_bullets(self):
        if self._ship is None or not hasattr(self._ship, "gun"):
            return
        bullets   = self._ship.gun.bullets
        all_rocks = list(self._debris) + list(self._shower_rocks)
        destroyed = []

        for bullet in list(bullets):
            if not bullet.alive:
                continue
            for rock in all_rocks:
                if rock in destroyed:
                    continue
                if (rock.pos - bullet.pos).length() < rock.radius + 3:
                    bullet.lifetime = -1   # kill bullet
                    if rock.hit():         # returns True when hp reaches 0
                        destroyed.append(rock)
                    break

        for rock in destroyed:
            if rock in self._debris:
                self._debris.remove(rock)
            elif rock in self._shower_rocks:
                self._shower_rocks.remove(rock)

        # Bullet hits on satellites
        for bullet in list(bullets):
            if not bullet.alive:
                continue
            for sat in list(self._satellites):
                if (sat.pos - bullet.pos).length() < sat.arm_len + 4:
                    bullet.lifetime = -1
                    if sat.hit():
                        self._satellites.remove(sat)
                        bus.emit(EVT_SATELLITE_HIT)
                    break

        # Bullet hits on repo barges — 3 hits forces a retreat
        for bullet in list(bullets):
            if not bullet.alive:
                continue
            for barge in self._barges:
                if barge.is_destroyed:
                    continue
                if (barge.pos - bullet.pos).length() < 26:
                    bullet.lifetime = -1
                    barge.take_hit()
                    break

    def _check_slingshot(self):
        if self._sling_cd > 0 or self._sector is None:
            return
        speed = self._ship.body.speed()
        for i, well in enumerate(self._sector.gravity.wells):
            dist = (well.pos - self._ship.body.pos).length()
            if dist < S.SLINGSHOT_RANGE:
                self._sling_well_t[i] = self._sector_timer

        if speed > S.SLINGSHOT_SPEED:
            for i, last_t in self._sling_well_t.items():
                if self._sector_timer - last_t < 2.5:
                    self._sector_timer = max(0.0,
                                             self._sector_timer - S.SLINGSHOT_BONUS)
                    bus.emit(EVT_SLINGSHOT, speed=speed)
                    self._sling_cd = 8.0
                    break

    def _check_proximity(self):
        if self._prox_cd > 0 or not self._barges:
            return
        min_dist = min((b.pos - self._ship.pos).length() for b in self._barges)
        if min_dist < 320:
            bus.emit(EVT_BARGE_NEARBY, distance=min_dist)
            self._prox_cd = 12.0

    def _check_random_event(self, dt: float):
        self._event_cd -= dt
        if self._event_cd > 0:
            return
        self._event_cd = random.uniform(S.EVENT_INTERVAL_MIN, S.EVENT_INTERVAL_MAX)
        kind = random.choice(["comms", "comms", "debris", "scan"])

        if kind == "comms":
            bus.emit(EVT_COMMS_INTERCEPT)
        elif kind == "debris":
            bus.emit(EVT_DEBRIS_SHOWER)
            self._shower_rocks = [DebrisRock() for _ in range(4)]
            self._shower_t = 14.0
        elif kind == "scan":
            bus.emit(EVT_SCAN_PING,
                     pos_x=random.randint(120, S.SCREEN_W - 120),
                     pos_y=random.randint(100, S.FLIGHT_H - 60))

    def _check_comms(self, dt: float):
        self._kress_cd    -= dt
        self._collector_cd -= dt

        if self._kress_cd <= 0:
            self._kress_cd = random.uniform(S.KRESS_INTERVAL_MIN, S.KRESS_INTERVAL_MAX)
            bus.emit(EVT_COMMS_SPEAK,
                     speaker="KRESS",
                     line=random.choice(_KRESS_LINES))

        if self._collector_cd <= 0:
            self._collector_cd = random.uniform(S.COLLECTOR_INTERVAL_MIN,
                                                S.COLLECTOR_INTERVAL_MAX)
            speaker, line = random.choice(_COLLECTOR_LINES)
            bus.emit(EVT_COMMS_SPEAK, speaker=speaker, line=line)

    def _on_slingshot(self, **_):
        self._sector_slingshots  += 1
        self._run_slingshots     += 1

    def _on_tether_snap(self, **_):
        bonus = 1200
        self.meta.pay_off(bonus)
        self._run_debt_reduced += bonus
        self._sector_snaps     += 1
        self._run_snaps        += 1
        self._sector_credits   += bonus
        bus.emit(EVT_BAX_SPEAK, line=random.choice([
            f"Snap! That's {bonus:,} off your tab. Union's gonna be LIVID.",
            "Beautiful lateral drift! Their claims department can cry about it.",
            f"{bonus:,} credits back. Every snap counts, mate.",
            "Tether snapped! Ha! They'll be filing an incident report for a WEEK.",
        ]))

    def _on_canister_grab(self, **_):
        from ship.modules.thruster import Thruster
        if self._ship is None:
            return
        for mod in self._ship.chain.get_active("propulsion"):
            if isinstance(mod, Thruster):
                mod.inject_fuel_mix(1.5, 8.0)

    # ------------------------------------------------------------------
    def _build_run_context(self) -> dict:
        ctx: dict = {"sector_index":    self._sector_index,
                     "run_credits":     self._run_debt_reduced,
                     "run_snaps":       self._run_snaps,
                     "run_slingshots":  self._run_slingshots}
        if self._ship is not None:
            ctx["hull_pct"] = self._ship.hull / S.HULL_MAX
            cargo = self._ship.cargo
            if cargo is not None and hasattr(cargo, "state_for_terminal"):
                ctx["cargo_state"] = cargo.state_for_terminal()
        if hasattr(self, "meta"):
            ctx["debt"] = self.meta.debt
        return ctx

    def open_terminal(self, npc_type: str, **npc_kwargs) -> Terminal:
        npc_kwargs.setdefault("run_context", self._build_run_context())
        npc = make_npc(npc_type, **npc_kwargs)
        self._active_terminal = Terminal(npc)
        return self._active_terminal

    def open_barge_terminal(self, barge) -> Terminal:
        """Mid-flight intercept: Gary opens a comm, no sector advance on close."""
        self._intercepting_barge = barge
        return self.open_terminal("gary", intercepted=True)

    def _open_jump_terminal(self):
        # Final sector: chapter climax — face the NPC tied to the cargo
        is_final = self._sector_index == S.SECTORS_PER_RUN - 1
        if is_final and self._ship is not None and self._ship.cargo is not None:
            npc_type = self._ship.cargo.terminal_climax()
            bus.emit(EVT_BAX_SPEAK, line=random.choice([
                "Final negotiation. Chapter climax. Make this one COUNT.",
                "Last terminal of the run. Cargo-specific contact incoming. Be sharp.",
                "Right — final exit interview. The whole chapter hinges on this.",
            ]))
        else:
            pool = ["gary", "synthetic_droid", "union_dispatcher"]
            # Insurance adjuster from sector 3 onward — she's claims, not enforcement
            if self._sector_index >= 3:
                pool.append("insurance_adjuster")
            npc_type = random.choice(pool)
            bus.emit(EVT_BAX_SPEAK, line=random.choice([
                "Gate authority checkpoint. They want passage fees before we jump.",
                "Sector boundary control. Standard stop — terminal incoming, hold course.",
                "Local 404 checkpoint. Pre-jump inspection. You know what to do.",
                "Clearance terminal inbound. Tell 'em what they wanna hear.",
                "Gate authority's pinged us. Talk us through or we pay double.",
                "Jump gate's flagging us. Pre-jump inspection — type smart.",
            ]))
        self.open_terminal(npc_type)
        self._pending_advance = True

    def on_terminal_complete(self, outcome):
        # Grant debt reduction based on how the negotiation went
        if outcome == "exploit":
            bonus = 9000
            self.meta.pay_off(bonus)
            self._run_debt_reduced += bonus
            self._sector_credits   += bonus
            bus.emit(EVT_BAX_SPEAK, line=random.choice([
                f"EXPLOITED their system. {bonus:,} credits rerouted. Blevins is gonna lose his MIND.",
                f"Their firewall had the structural integrity of wet paper. {bonus:,} back.",
                f"You just robbed a repo man digitally. {bonus:,} off. I'm proud.",
            ]))
        elif outcome == "release":
            bonus = 2500
            self.meta.pay_off(bonus)
            self._run_debt_reduced += bonus
            self._sector_credits   += bonus
            bus.emit(EVT_BAX_SPEAK, line=random.choice([
                f"Talked your way out. {bonus:,} off the invoice. Not bad.",
                f"They folded. {bonus:,} waived. Still in debt, but less of it.",
                f"Negotiated like a professional. A broke professional, but still. {bonus:,} saved.",
            ]))

        self._active_terminal = None
        if self._intercepting_barge is not None:
            barge = self._intercepting_barge
            self._intercepting_barge = None
            barge.on_terminal_outcome(outcome)
            return
        if self._pending_advance:
            self._pending_advance = False
            self._advance_sector()

    def _advance_sector(self):
        bus.emit(EVT_WARP_JUMP)
        sector_bonus = 4500
        self.meta.pay_off(sector_bonus)
        self._run_debt_reduced += sector_bonus
        self._sector_credits   += sector_bonus

        # Snapshot stats for the between-sector flash card
        hull_now  = self._ship.hull if self._ship else S.HULL_MAX
        hull_lost = max(0, int(self._sector_start_hull - hull_now))
        self._last_stats = {
            "sector":     self._sector_index + 1,   # the one we just cleared
            "credits":    self._sector_credits,
            "snaps":      self._sector_snaps,
            "slingshots": self._sector_slingshots,
            "hull_lost":  hull_lost,
        }
        self._flash_t = 2.8

        # Reset per-sector counters
        self._sector_slingshots = 0
        self._sector_snaps      = 0
        self._sector_credits    = 0
        self._sector_start_hull = hull_now

        completed_sector = self._sector_index
        self._sector_index += 1
        bus.emit(EVT_SECTOR_CLEAR, sector_num=self._sector_index)

        if self._sector_index >= S.SECTORS_PER_RUN:
            bus.emit(EVT_RUN_END, success=True)
            return

        # Shop stop — signal game.py to open the shop before next sector loads
        if completed_sector in S.SHOP_SECTORS:
            self._shop_pending = True
            bus.emit(EVT_SHOP_ENTER)
            return

        self._load_next_sector()

    def _load_next_sector(self):
        self._sector       = generate_sector(self._sector_index, self._difficulty())
        self._sector_timer = 0.0
        self._jump_ready_fired = False
        self._barges.clear()
        self._spawn_queue.clear()
        self._sling_well_t.clear()
        self._kress_called_this_sector = False
        self._shop_pending = False
        self._spawn_sector_objects()

        cargo_type = (type(self._ship.cargo).__name__
                      if self._ship and self._ship.cargo else None)
        bus.emit(EVT_SECTOR_START,
                 sector_num=self._sector_index + 1,
                 cargo_type=cargo_type)

        # Final sector: announce to bax + extra immediate barge
        if self._sector_index == S.SECTORS_PER_RUN - 1:
            bus.emit(EVT_FINAL_SECTOR)
            self._spawn_barge(immediate_chase=True)

        # Ambush: spawn an additional barge that's already hunting
        if self._sector.is_ambush:
            self._spawn_barge(immediate_chase=True)

    def _spawn_sector_objects(self):
        self._spawn_queue.clear()
        idx = self._sector_index

        # Debris: 1 rock immediately, rest drip in every 4-6s.
        # Sector 1 gets 1 immediate; later sectors get up to DEBRIS_COUNT total.
        immediate_debris = 1
        self._debris = [DebrisRock() for _ in range(immediate_debris)]
        for i in range(S.DEBRIS_COUNT - immediate_debris):
            t = 4.0 + i * random.uniform(3.5, 5.5)
            self._spawn_queue.append((t, "debris"))

        # Canisters spawn immediately — they're rewards, not threats
        self._canisters = [FuelCanister() for _ in range(S.CANISTER_COUNT)]

        # Satellites: none until 9s in on early sectors, 5s on late sectors.
        self._satellites = []
        sat_delay_base = max(5.0, 11.0 - idx * 0.6)
        for i in range(S.SATELLITE_COUNT):
            t = sat_delay_base + i * random.uniform(2.5, 4.0)
            self._spawn_queue.append((t, "satellite"))

        self._alien       = None
        self._alien_spoken = False

        # 22% chance of alien flythrough per sector
        if random.random() < 0.22:
            self._alien = AlienShip()

        # Barge spawn ramp — sector 1-2 are intro, then escalate.
        # Barges also deferred: first barge at 8s so player can orient.
        # Final sector gets heavier: handled by _load_next_sector spawning one immediately.
        barge_count = 0
        if idx >= 2:
            barge_count = 1
        if idx >= 6:
            barge_count = 2
        barge_delay = max(4.0, 9.0 - idx * 0.5)
        for i in range(barge_count):
            self._spawn_queue.append((barge_delay + i * 6.0, "barge"))

        # Final sector: queue a second deferred barge and one extra debris.
        # The gauntlet stays intense via the two barges, not via debris spam.
        if idx == S.SECTORS_PER_RUN - 1:
            self._spawn_queue.append((barge_delay + 3.0, "barge"))
            self._spawn_queue.append((3.0, "debris"))

        # Demolition notice — 22% chance from sector 2 onward
        if idx >= 1 and random.random() < 0.22:
            speaker, line = random.choice(_DEMO_NOTICES)
            bus.emit(EVT_DEMO_NOTICE)
            bus.emit(EVT_COMMS_SPEAK, speaker=speaker, line=line)

    def _spawn_barge(self, immediate_chase: bool = False):
        from antagonists.repo_barge import BargeState
        side  = random.choice(["left", "right", "top", "bottom"])
        pos_x = {"left": 0, "right": S.SCREEN_W}.get(side, random.randint(0, S.SCREEN_W))
        pos_y = {"top":  0, "bottom": S.SCREEN_H}.get(side, random.randint(0, S.SCREEN_H))
        barge = RepoBarge(pos_x, pos_y, self)
        if immediate_chase:
            barge.state = BargeState.CHASE
        self._barges.append(barge)

    # ------------------------------------------------------------------
    def _difficulty(self) -> float:
        return 1.0 + (self._sector_index / S.SECTORS_PER_RUN)

    def _current_chapter(self) -> int:
        completed = self.meta.chapters_completed
        for ch in [1, 2, 3, 4]:
            if ch not in completed:
                return ch
        return 4

    # ------------------------------------------------------------------
    @property
    def active_terminal(self) -> Terminal | None:
        return self._active_terminal

    @property
    def sector(self) -> SectorLayout | None:
        return self._sector

    @property
    def barges(self) -> list[RepoBarge]:
        return self._barges

    @property
    def debris(self) -> list[DebrisRock]:
        return self._debris

    @property
    def canisters(self) -> list[FuelCanister]:
        return self._canisters

    @property
    def shower_rocks(self) -> list[DebrisRock]:
        return self._shower_rocks

    @property
    def satellites(self) -> list[SpinningSatellite]:
        return self._satellites

    @property
    def alien(self) -> AlienShip | None:
        return self._alien

    @property
    def sector_num(self) -> int:
        return self._sector_index + 1

    @property
    def jump_ready(self) -> bool:
        return self._sector_timer >= self._sector_dur

    @property
    def jump_cooldown(self) -> float:
        return max(0.0, self._sector_dur - self._sector_timer)
