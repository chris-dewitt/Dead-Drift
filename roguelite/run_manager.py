from __future__ import annotations
import random
import secrets
import pygame
from physics.body import RigidBody2D, Vec2
from roguelite.procedural import (generate_sector, SectorLayout,
                                   THEME_WRECKAGE_BELT, THEME_INDUSTRIAL_GRAVEYARD,
                                   THEME_JUNK_BELT, THEME_MINE_STRIP,
                                   THEME_FROZEN_TRAIL, THEME_FLARE_CORRIDOR,
                                   THEME_TOLL_AUTHORITY)
from roguelite.loadout_draft import LoadoutDraft
from roguelite.meta_progression import MetaProgression
from roguelite.mutators import MutatorRegistry
from roguelite.stats_tracker import StatsTracker
from roguelite.tutorial import TutorialManager
from antagonists.repo_barge import RepoBarge
from antagonists.debris import DebrisRock
from antagonists.fuel_canister import FuelCanister
from antagonists.satellite import SpinningSatellite
from antagonists.alien_ship import AlienShip
from antagonists.ai_ship import (AIShip, ALL_CLASSES, CLASS_DERELICT, CLASS_GUNBOAT,
                                  BEHAVIOR_HAILER, BEHAVIOR_PIRATE, BEHAVIOR_TRAFFIC)
from antagonists.wreck import SpaceWreck
from antagonists.dead_station import DeadStation
from antagonists.trash_field import TrashField
from antagonists.mine_field import MineField
from antagonists.ice_field import IceField
from antagonists.comet_trail import CometTrail
from terminal.terminal import Terminal
from terminal.npc_logic import make_npc
from core.event_bus import (bus, EVT_SECTOR_CLEAR, EVT_RUN_END,
                             EVT_SLINGSHOT, EVT_BARGE_NEARBY, EVT_CANISTER_GRAB,
                             EVT_COMMS_INTERCEPT, EVT_DEBRIS_SHOWER, EVT_SCAN_PING,
                             EVT_COMMS_SPEAK, EVT_TETHER_SNAP, EVT_BAX_SPEAK,
                             EVT_SATELLITE_HIT, EVT_ALIEN_SIGHTING, EVT_DEMO_NOTICE,
                             EVT_JUMP_READY, EVT_WARP_JUMP, EVT_FINAL_SECTOR,
                             EVT_RUN_START, EVT_SHOP_ENTER, EVT_SECTOR_START,
                             EVT_AISHIP_HAIL, EVT_AISHIP_DESTROYED, EVT_VOICE_CHAR,
                             EVT_MUTATOR_SET, EVT_FIRST_TETHER_SNAP,
                             EVT_LONG_FIGHT_SURVIVED, EVT_BARGE_KILLED,
                             EVT_GUN_FIRE, EVT_CLOSE_CALL)
from config import settings as S

SLINGSHOT_CREDIT_BONUS = 800


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
        self._ai_ships: list[AIShip] = []
        self._aiship_hail_pending: AIShip | None = None
        bus.subscribe(EVT_AISHIP_HAIL, self._on_aiship_hail)
        bus.subscribe(EVT_AISHIP_DESTROYED, self._on_aiship_destroyed)
        # Theme-based obstacles (Epic 3)
        self._wrecks: list[SpaceWreck]       = []
        self._dead_station: DeadStation | None = None
        self._trash_field: TrashField | None   = None
        self._mine_field: MineField | None     = None
        self._ice_field: IceField | None       = None
        self._comet_trail: CometTrail | None   = None
        # Solar flare state
        self._flare_cd        = 22.0   # seconds until next flare event
        self._flare_active    = False
        self._flare_t         = 0.0    # countdown during active flare
        # Toll checkpoint state
        self._toll_pending    = False
        self._toll_t          = 10.0   # trigger at 10s into sector
        self._well_hit_times: dict[int, float] = {}  # per-well core damage cooldown
        self._active_terminal: Terminal | None = None
        self._intercepting_barge = None   # set when a barge opens a mid-flight comm

        # Terminal popup pacing (Epic 9.3) — defer opening until Bax's line settles.
        # Gate logic: pending terminal becomes active when (a) ≥2.5s elapsed AND
        # Bax has stopped emitting voice chars for ≥0.5s, OR (b) 5s hard cap.
        self._t                 = 0.0
        self._pending_terminal: Terminal | None = None
        self._terminal_arm_t    = -1.0
        self._last_voice_char_t = -10.0
        bus.subscribe(EVT_VOICE_CHAR, self._on_voice_char)
        self._vault = None
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
        self._last_winning_path: str = ""  # path that won the previous terminal
        self._run_debt_reduced = 0   # credits recovered this run (shown in HUD)
        self._run_snaps        = 0   # tether snaps this entire run
        self._run_slingshots   = 0   # slingshots this entire run
        self._shop_pending     = False   # True when a shop stop should open

        # Deferred object spawn queue — (trigger_time, kind) pairs
        # Populated by _spawn_sector_objects(), drained in update()
        self._spawn_queue: list[tuple[float, str]] = []

        # Tutorial — shown for first three clones so quick deaths still get hints
        self._tutorial: TutorialManager | None = (
            TutorialManager() if meta.clone_count <= 3 else None
        )

        # Per-sector stat tracking for the between-sector flash card
        self._sector_slingshots = 0
        self._sector_snaps      = 0
        self._sector_credits    = 0
        self._sector_start_hull = S.HULL_MAX
        self._flash_t           = 0.0
        self._last_stats: dict | None = None
        self._run_seed          = 0
        self._frame_name        = ""

        bus.subscribe(EVT_CANISTER_GRAB, self._on_canister_grab)
        bus.subscribe(EVT_TETHER_SNAP,   self._on_tether_snap)
        bus.subscribe(EVT_SLINGSHOT,     self._on_slingshot)
        bus.subscribe(EVT_GUN_FIRE,      self._on_gun_fire)

        # Epic 12.1 — Run mutators
        self.mutators = MutatorRegistry()

        # Epic 12.4 — Stats tracker (subscribes to bus internally)
        self.stats = StatsTracker()

        # Epic 11.3 — bax_context: state Bax reads to reference past runs
        # Persists across sectors within a run; reset on run start.
        self.bax_context: dict = {
            "times_died_this_sector":   {},   # sector_idx -> count
            "last_sector_reached":      0,
            "exploits_used_run":        0,
            "slingshot_used_run":       False,
            "shops_visited_this_chapter": 0,
            "chapter_at_session_start": 1,
        }
        # Epic 11.4 — NPC opinions fired-once tracker: (npc_key, chapter) set
        self._bax_opinion_fired: set[tuple[str, int]] = set()
        # Epic 11.2 — long-fight tracking
        self._barge_pursuit_t = 0.0
        self._long_fight_emitted = False
        # Epic 11.2 — close-call tracking: per-object min-distance witnesses
        self._close_witness: dict[int, float] = {}  # id(obj) -> last_dist
        self._close_call_cd = 0.0
        # Epic 12.1 — NOVICE_PASS first-death-free flag
        self._novice_pass_consumed = False

    # ------------------------------------------------------------------
    def start_run(self, ship):
        # Epic 12.1 — roll a mutator. First run of each chapter has none.
        # Detect "first run of chapter" by checking if the previous chapter is
        # the highest completed; if no chapters_completed, this is the first
        # run period (no mutator).
        first_run_of_chapter = (
            not self.meta.chapters_completed or
            (self._current_chapter() - 1) not in self.meta.chapters_completed
        )
        self.mutators.roll_for_run(first_run_of_chapter=first_run_of_chapter)
        bus.emit(EVT_MUTATOR_SET,
                 mutator_key=self.mutators.active.key if self.mutators.active else None)
        # Epic 12.1 — apply mutator to Gun's class-level malfunction multiplier
        from ship.gun import Gun
        Gun.malfunction_multiplier = (3.0 if self.mutators.is_active("system_glitch")
                                       else 1.0)
        self._novice_pass_consumed = False
        # Stats tracker resets via its own EVT_RUN_START handler
        bus.emit(EVT_RUN_START)
        self.stats.set_chapter(self._current_chapter())
        # Apply mutator-driven debt at run start
        starting_debt_bonus = self.mutators.starting_debt_bonus()
        if starting_debt_bonus:
            self.meta.add_debt(starting_debt_bonus)
        # Reset bax_context for this run
        self.bax_context["times_died_this_sector"] = {}
        self.bax_context["last_sector_reached"]    = 0
        self.bax_context["exploits_used_run"]      = 0
        self.bax_context["slingshot_used_run"]     = False
        self._barge_pursuit_t   = 0.0
        self._long_fight_emitted = False
        self._run_seed = secrets.randbelow(2 ** 31)
        self._frame_name = ""
        self._sector_index = 0
        self._barges.clear()
        self._debris.clear()
        self._canisters.clear()
        self._satellites.clear()
        self._alien      = None
        self._alien_spoken = False
        self._ai_ships.clear()
        self._aiship_hail_pending = None
        self._shower_rocks.clear()
        self._active_terminal    = None
        self._pending_terminal   = None
        self._terminal_arm_t     = -1.0
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
        self._well_hit_times.clear()
        self._flash_t            = 0.0
        self._last_stats         = None
        self._spawn_queue.clear()
        self._ship = ship
        self.draft = LoadoutDraft(chapter=self._current_chapter())
        self.draft.set_mutator(self.mutators.active)
        self._kress_cd    = random.uniform(S.KRESS_INTERVAL_MIN, S.KRESS_INTERVAL_MAX)
        self._collector_cd = random.uniform(S.COLLECTOR_INTERVAL_MIN, S.COLLECTOR_INTERVAL_MAX)
        ship.reset()

    def apply_draft(self, ship):
        frame  = self.draft.selected_frame
        module = self.draft.selected_module
        cargo  = self.draft.selected_cargo
        self._frame_name = frame.get("name", "")

        ship.hull       = min(S.HULL_MAX, S.HULL_MAX + frame.get("hull_bonus", 0))
        ship.body.mass  = S.SHIP_MASS * frame.get("mass_mod", 1.0)
        ship.chain.install(module, 1)
        ship.cargo      = cargo
        self._ship      = ship

        rng = random.Random(self._run_seed + self._sector_index * 997)
        self._sector    = generate_sector(self._sector_index, self._difficulty(),
                                          rng=rng, chapter=self._current_chapter(),
                                          force_theme=self._cold_sector_theme(rng))
        self._sector_start_hull = ship.hull
        self._sector_timer      = 0.0
        self._jump_ready_fired  = False
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
        # Walltime tick — used by terminal popup gate even before a sector loads.
        self._t += dt
        self._tick_terminal_gate()

        if self._sector is None or self._ship is None:
            return

        # Epic 12.1 — SLINGSHOT_ONLY: timer only advances via slingshot bonus
        if not self.mutators.is_active("slingshot_only"):
            self._sector_timer += dt
        self._sling_cd      = max(0.0, self._sling_cd - dt)
        self._prox_cd       = max(0.0, self._prox_cd  - dt)
        self._flash_t       = max(0.0, self._flash_t  - dt)
        self._close_call_cd = max(0.0, self._close_call_cd - dt)
        # Epic 11.2 — close call detection: any barge/debris within 30px that
        # was further away last frame, without intervening collision = close call
        if self._ship is not None and self._close_call_cd <= 0:
            ship_pos = self._ship.pos
            candidates = list(self._barges)
            candidates.extend(self._debris)
            candidates.extend(self._shower_rocks)
            for obj in candidates:
                op = getattr(obj, "pos", None)
                if op is None:
                    continue
                obj_id = id(obj)
                dist = (op - ship_pos).length()
                prev = self._close_witness.get(obj_id, 9999.0)
                # Departing from very close range without hit = close call
                if prev <= 30.0 and dist > 30.0 and dist < 60.0:
                    bus.emit(EVT_CLOSE_CALL, distance=prev)
                    self._close_call_cd = 6.0
                    break
                self._close_witness[obj_id] = dist
            # Trim witness table for vanished objects
            live_ids = {id(o) for o in candidates}
            self._close_witness = {k: v for k, v in self._close_witness.items()
                                    if k in live_ids}

        # Epic 11.2 — Long fight survived: if a barge has been alive >45s
        # without capturing the player, emit once per run.
        if self._barges and not self._long_fight_emitted:
            self._barge_pursuit_t += dt
            if self._barge_pursuit_t >= 45.0:
                self._long_fight_emitted = True
                bus.emit(EVT_LONG_FIGHT_SURVIVED)
        elif not self._barges:
            self._barge_pursuit_t = 0.0

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
            elif kind == "ai_ship":
                self._spawn_ai_ship()
        if due:
            self._spawn_queue = [item for item in self._spawn_queue
                                 if item[0] > self._sector_timer]

        if not self._jump_ready_fired and self._sector_timer >= self._sector_dur:
            self._jump_ready_fired = True
            bus.emit(EVT_JUMP_READY)

        self._sector.gravity.apply_all(self._ship.body)
        self._sector.gravity.update(dt)   # three-body well drift

        # Gravity-well core — capped hull damage (matches play.py demo)
        if self._ship.is_alive:
            well = self._sector.gravity.check_collisions(self._ship.body)
            if well is not None:
                well_id = id(well)
                last = self._well_hit_times.get(well_id, -999.0)
                if self._sector_timer - last >= 1.0:
                    self._ship.take_damage(15.0, source="gravity_well")
                    self._well_hit_times[well_id] = self._sector_timer
                push = (self._ship.body.pos - well.pos).normalized() * 200.0
                self._ship.body.apply_impulse(push)

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
            if rock.collides(self._ship.pos) and rock.can_damage_ship():
                self._ship.take_damage(S.DEBRIS_DAMAGE, source="debris")
                rock.register_ship_hit()
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

        # AI ships — update each, prune dead, handle ram damage already in tick
        for ai in list(self._ai_ships):
            ai.update(dt, self._ship)
            if not ai.alive:
                self._ai_ships.remove(ai)

        # Debris shower tick
        if self._shower_t > 0:
            self._shower_t -= dt
            for rock in self._shower_rocks:
                rock.update(dt)
                if rock.collides(self._ship.pos) and rock.can_damage_ship():
                    self._ship.take_damage(S.DEBRIS_DAMAGE, source="debris_shower")
                    rock.register_ship_hit()
                    rock.hit()
            if self._shower_t <= 0:
                self._shower_rocks.clear()

        # Bullet-rock collision
        self._check_bullets()

        # Theme-based obstacle updates
        self._update_theme_obstacles(dt)

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
        elif event.key == pygame.K_e and self._aiship_hail_pending is not None:
            self._open_aiship_terminal()

    def _open_kress_terminal(self):
        from core.event_bus import EVT_KRESS_DIALLED
        self._kress_called_this_sector = True
        bus.emit(EVT_KRESS_DIALLED)
        self.open_terminal("kress")

    def _open_aiship_terminal(self):
        """Open the terminal for a hailing AI ship and consume the pending hail."""
        hailer = self.take_ai_hail()
        if hailer is None:
            return
        from antagonists.ai_ship import _HAIL_NPC_BY_CLASS, ST_DEPART
        npc_type = _HAIL_NPC_BY_CLASS.get(hailer.ship_class)
        if not npc_type:
            return
        # Ship leaves once the talk starts
        hailer.state = ST_DEPART
        hailer._state_t = 0.0
        self.open_terminal(npc_type)

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
                if (barge.pos - bullet.pos).length() < 32:
                    bullet.lifetime = -1
                    barge.take_hit()
                    break

        # Bullet hits on AI ships — hostiles take 6 hits, freighters 4, etc.
        for bullet in list(bullets):
            if not bullet.alive:
                continue
            for ai in list(self._ai_ships):
                if not ai.alive:
                    continue
                if (ai.pos - bullet.pos).length() < ai.radius + 4:
                    bullet.lifetime = -1
                    ai.take_hit(1)
                    break

    def _check_slingshot(self):
        if self._sling_cd > 0 or self._sector is None:
            return
        speed   = self._ship.body.speed()
        sling_r2 = S.SLINGSHOT_RANGE * S.SLINGSHOT_RANGE
        for i, well in enumerate(self._sector.gravity.wells):
            delta = well.pos - self._ship.body.pos
            if delta.length_sq() < sling_r2:
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
        min_dist_sq = min((b.pos - self._ship.pos).length_sq() for b in self._barges)
        if min_dist_sq < 320 * 320:
            min_dist = min_dist_sq ** 0.5
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

    def _on_slingshot(self, speed=0, **_):
        self._sector_slingshots += 1
        self._run_slingshots    += 1
        # Epic 11.3 — mark slingshot used for bax_context
        self.bax_context["slingshot_used_run"] = True
        # Credit bonus per clean slingshot (Epic 12.1 — mutator scale)
        bonus = int(SLINGSHOT_CREDIT_BONUS * self.mutators.credit_pickup_multiplier())
        self.meta.pay_off(bonus)
        self._run_debt_reduced += bonus
        self._sector_credits   += bonus
        # Epic 12.1 — SLINGSHOT_ONLY: each slingshot grants ~1/3 of jump timer.
        if self.mutators.is_active("slingshot_only"):
            self._sector_timer += self._sector_dur / 3.0
        # Overdrive window: 2s at 1.5× cap (Epic 12.1 — fragile_frame doubles duration)
        if self._ship and self._ship.is_alive:
            self._ship.body._vel_cap_override = S.MAX_VELOCITY * 1.5
            self._ship.body._overdrive_t      = 2.0 * self.mutators.slingshot_overdrive_multiplier()
        # Epic 12.2 — milestone unlock: 10 lifetime slingshots → SLINGSHOT_ONLY mutator
        total = self.meta.inc_milestone("slingshots_total")
        if total >= 10 and not self.meta.has_unlock("slingshot_only_mutator"):
            self.meta.add_unlock("slingshot_only_mutator")

    def _on_gun_fire(self, **_):
        # Epic 12.1 — SYSTEM_GLITCH: each successful shot pays +50 cr
        if self.mutators.is_active("system_glitch"):
            bonus = 50
            self.meta.pay_off(bonus)
            self._run_debt_reduced += bonus
            self._sector_credits   += bonus

    def _on_tether_snap(self, **_):
        bonus = int(1200 * self.mutators.credit_pickup_multiplier())
        self.meta.pay_off(bonus)
        self._run_debt_reduced += bonus
        self._sector_snaps     += 1
        self._run_snaps        += 1
        self._sector_credits   += bonus
        # Epic 11.2 — emit FIRST_TETHER_SNAP once per run
        if self._run_snaps == 1:
            bus.emit(EVT_FIRST_TETHER_SNAP)
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
        # Small hull patch — emergency sealant in the canister
        self._ship.repair(12.0)

    # ------------------------------------------------------------------
    def _build_run_context(self) -> dict:
        ctx: dict = {"sector_index":    self._sector_index,
                     "run_credits":     self._run_debt_reduced,
                     "run_snaps":       self._run_snaps,
                     "run_slingshots":  self._run_slingshots}
        if self._ship is not None:
            ctx["hull_pct"] = self._ship.hull / S.HULL_MAX
            cargo = self._ship.cargo
            if cargo is not None:
                ctx["cargo_type"] = type(cargo).__name__
                ctx["cargo_name"] = getattr(cargo, "name", str(cargo))
                ctx["cargo_integrity"] = getattr(cargo, "integrity", None)
                ctx["cargo_damaged"] = bool(getattr(cargo, "is_damaged", False))
                if hasattr(cargo, "state_for_terminal"):
                    ctx["cargo_state"] = cargo.state_for_terminal()
        if hasattr(self, "meta"):
            ctx["debt"] = self.meta.debt
        # Epic 11.3 — share Bax's run-memory dict so NPCs/Bax can react to it
        if hasattr(self, "bax_context"):
            ctx["bax_context"] = dict(self.bax_context)
        return ctx

    def open_terminal(self, npc_type: str, **npc_kwargs) -> Terminal:
        # Don't use dict.setdefault here — its default arg is evaluated eagerly,
        # which would call _build_run_context() even when run_context is already
        # supplied by the caller (and would crash if the caller bypassed __init__,
        # e.g. in unit tests using RunManager.__new__).
        if "run_context" not in npc_kwargs:
            npc_kwargs["run_context"] = self._build_run_context()
        # Mira Voss needs a ship reference so she can call ship.repair() on success.
        if npc_type == "mira_voss" and self._ship is not None:
            npc_kwargs.setdefault("ship", self._ship)
        npc = make_npc(npc_type, **npc_kwargs)
        terminal = Terminal(
            npc,
            blocked_paths=frozenset({self._last_winning_path}) if self._last_winning_path else frozenset(),
            vocabulary_vault=getattr(self, "_vault", None),
        )
        self._install_terminal(terminal)
        return terminal

    # ------------------------------------------------------------------
    def _install_terminal(self, terminal: Terminal) -> None:
        """Route every Terminal creation through here so the popup gate fires.
        Defers `_active_terminal` assignment until Bax's priority line settles."""
        t_now  = getattr(self, '_t', 0.0)
        t_last = getattr(self, '_last_voice_char_t', -10.0)
        silent = (t_now - t_last) > 0.5
        if silent:
            self._active_terminal = terminal
            if hasattr(self, '_pending_terminal'):
                self._pending_terminal = None
            if hasattr(self, '_terminal_arm_t'):
                self._terminal_arm_t = -1.0
        else:
            if hasattr(self, '_pending_terminal'):
                self._pending_terminal = terminal
            if hasattr(self, '_terminal_arm_t'):
                self._terminal_arm_t = t_now

    def _tick_terminal_gate(self) -> None:
        if self._pending_terminal is None or self._active_terminal is not None:
            return
        elapsed = self._t - self._terminal_arm_t
        silent  = (self._t - self._last_voice_char_t) > 0.5
        # Hard cap = 5s. Soft promote at ≥2.5s once Bax is quiet.
        if elapsed >= 5.0 or (elapsed >= 2.5 and silent):
            self._active_terminal = self._pending_terminal
            self._pending_terminal = None
            self._terminal_arm_t = -1.0

    def _on_voice_char(self, **_) -> None:
        self._last_voice_char_t = self._t

    def open_barge_terminal(self, barge) -> Terminal:
        """Mid-flight intercept: repo comm — Gary is common but not guaranteed."""
        self._intercepting_barge = barge
        pool = ["union_dispatcher", "synthetic_droid"]
        if self._sector_index >= 2:
            pool.append("insurance_adjuster")
        if self._sector_index >= 4:
            pool.append("pirate")
        # Gary ~30%; other pool members share the rest
        if self._sector_index >= 1 and random.random() < 0.30:
            npc_type = "gary"
        else:
            npc_type = random.choice(pool)
        if npc_type == "gary":
            bus.emit(EVT_BAX_SPEAK, line=random.choice([
                "Gary Pruitt on the comm. Repo intercept. Same tricks — deal, bribe, sympathy.",
                "Local 404 hail. It's Gary again. Talk 'im down before the 'arpoon.",
                "Barge is hailing. Gary Pruitt. Outstanding fees. You know the script.",
            ]))
            return self.open_terminal("gary", intercepted=True)
        framing = {
            "union_dispatcher": [
                "Union dispatcher on the barge channel. Paperwork angle might work.",
                "That's Central Dispatch, not Gary for once. Forms, grievance, or break-room chat.",
            ],
            "synthetic_droid": [
                "TK-9 answering the barge relay. Paradox or SQL — same as the gates.",
                "Droid on the intercept comm. Logic exploits only. No charm.",
            ],
            "insurance_adjuster": [
                "Insurance adjuster piggybacking the repo signal. Claims and forms.",
                "Morwenna on the line via the barge relay. Legal pressure might work.",
            ],
            "pirate": [
                "That's NOT Gary — pirate relay on the barge frequency. Talk weird.",
                "Pirate cuttin' through the repo comm. No Article 7 here.",
            ],
        }
        bus.emit(EVT_BAX_SPEAK, line=random.choice(
            framing.get(npc_type, ["Intercept comm open. Type smart."])
        ))
        return self.open_terminal(npc_type)

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
            pool = ["synthetic_droid", "union_dispatcher", "cargo_inspector"]
            if self._sector_index >= 1:
                pool.extend(["underground_dj", "nervous_fence", "dray"])
            if self._sector_index >= 2:
                pool.extend(["sandra", "pirate", "nova_soma_collections"])
            if self._sector_index >= 3:
                pool.extend(["insurance_adjuster", "cargo_inspector", "mira_voss"])
            if self._sector_index >= 5:
                pool.append("gary")
            npc_type = random.choice(pool)
            framing = {
                "sandra": [
                    "Gate channel pickup — that's SANDRA. The 'perfect courier.' "
                    "Brace yourself, mate. She's all manners and judgement.",
                    "Comm incoming. Sandra Vega-Marsh. She doesn't usually slum it on gate duty. "
                    "Something's up. Type sharp.",
                    "Oh god. Sandra. The poster girl herself. "
                    "Don't take the bait. Type like an adult.",
                ],
                "pirate": [
                    "That's not a Union frequency. PIRATE intercept. No charter, no Article 7. "
                    "Talk fast and weird. They respect weird.",
                    "Outer Belt signature. We're past the Union's reach. "
                    "These ones DON'T do paperwork. Mind the words.",
                    "Pirate hail on the channel. They want cargo or blood. "
                    "Pick your angle carefully — sympathy don't work on them.",
                ],
                "underground_dj": [
                    "Oh — that's MARROW. Pirate radio. Friendly! "
                    "He'll cut us a deal if you're nice. Ask for jamming if we're cookin'.",
                    "Roost broadcast cuttin' through the gate channel. "
                    "It's an ally, mate. Marrow. Use him — intel, jamming, dedications.",
                    "Pirate radio signal punching through the gate comm. "
                    "Marrow. He's on our side. Don't blow it.",
                ],
                "toll_authority": [
                    "Gate checkpoint incomin'. Transit levy — fifteen 'undred credits. "
                    "Could try talkin' 'im down. Could mention the Union.",
                    "Toll booth. Some bored Transit Authority bloke. "
                    "Pay up, run the paperwork angle, or complain about Local 404. 'E hates 'em.",
                    "Gate Seven checkpoint. Looks like a long-shift type. "
                    "Might sympathise if you bring up the Union. Worth a shot.",
                ],
                "synthetic_droid": [
                    "TK-9 on the channel. Their logic unit's got exploits. "
                    "Hit it with a paradox or flash the SQL. Don't make friends.",
                    "Droid checkpoint. They run on Union logic trees. "
                    "Find the exploit and they fold. Article overrides work.",
                    "Machine gate authority. No feelings, but definite bugs. "
                    "Paradoxes, override commands — their weakness, our door.",
                ],
                "gary": [
                    "Gary Pruitt, jump gate. 'E's everywhere, this one. "
                    "Same tricks work — deal, bribe, sympathy. You know the drill.",
                    "Gary again. Different gate, same bloke. "
                    "At least we know 'is weaknesses. Give 'im somethin' to work with.",
                ],
                "nervous_fence": [
                    "Picking up a grey-market relay. It's a FENCE. Felix. "
                    "He wants the cargo manifest or some credits. Friendly-ish. "
                    "Ask about his 'business plans' if you want a laugh.",
                    "Private relay signal. That's a contact, not a blockade. "
                    "Felix runs patrol intel — get him talking about his five-year plan.",
                    "Ooh, it's Felix! Legit-adjacent middleman. "
                    "Give 'im a manifest reading or talk debt — he's sympathetic. Useful bloke.",
                ],
                "cargo_inspector": [
                    "Cargo inspection checkpoint. Inspector wants a manifest declaration. "
                    "Tell 'im it's 'standard freight' and he'll tick the box. Easy.",
                    "Manifest check incoming. STA Inspector Holt. "
                    "Just sound boring and official — he loves that. "
                    "Or cite a cargo code. Any code. He won't check.",
                    "Cargo inspector. Nine years on the job. "
                    "Be vague three times and he gives up — or just say 'general goods'.",
                ],
                "dray": [
                    "Open relay — that's Dray. Fellow courier, sector three. "
                    "He's bored, he's bitter, he hates Nova Soma — same as us. "
                    "Gripe with him about the job and he'll trade gate intel. "
                    "Whatever you do, DON'T sound like Compliance.",
                    "Dray on the comm. Slacker. Lazy in the best way. "
                    "He's got tip-offs but you've got to earn 'em with sympathy. "
                    "Talk debt, talk barges, talk burnout. Don't talk procedure.",
                    "Courier-to-courier channel. Dray. "
                    "Bloke's been on the job four years and still only one warning. "
                    "Match his energy — bitter, bored, badly paid. He'll hook us up.",
                ],
                "nova_soma_collections": [
                    "Oh. OH. That's Nova Soma — the debt department. "
                    "Automated. It's a BOT, mate. Wellness chatbot reading from a script. "
                    "Hit it with a paradox or an SQL inject — it'll crash and route to handled. "
                    "DON'T swear. DON'T threaten. It escalates to a human, who calls a barge.",
                    "Nova Soma Collections AI on the line. "
                    "Corporate wellness script. Fully exploitable — drop tables, paradoxes, "
                    "policy citations all work. Be polite about it. The bot logs hostility.",
                    "Debt bot incoming. 'Hi there, valued customer.' Gag me. "
                    "Logic flaws everywhere — paradoxes, SQL, fake form numbers. "
                    "Hardship clause works too — pretend you're in crisis. "
                    "It's literally programmed to back off.",
                ],
                "mira_voss": [
                    "Bay nine medic — that's MIRA VOSS. Off-books hull tech. "
                    "Used to work Local 404 maintenance, got fired, now she's freelance. "
                    "Pay her or trade intel or share cargo. She'll seal the hull. "
                    "Don't waste her time — she'll close the comm.",
                    "Voss on the channel. Hull medic, no questions, no paperwork. "
                    "Cash, gate intel, or cargo cuts — pick one. "
                    "If you know any actual welding terms, drop 'em. She'll patch for free.",
                    "Repair stand opening up — Mira Voss. Best off-books mechanic in the sector. "
                    "She doesn't care who you are. Just don't be rude and "
                    "have something to offer. Don't ramble — she's working.",
                ],
            }
            default_framing = [
                "Gate authority checkpoint. They want passage fees before we jump.",
                "Sector boundary control. Standard stop — terminal incoming, hold course.",
                "Local 404 checkpoint. Pre-jump inspection. You know what to do.",
                "Clearance terminal inbound. Tell 'em what they wanna hear.",
                "Gate authority's pinged us. Talk us through or we pay double.",
                "Jump gate's flagging us. Pre-jump inspection — type smart.",
            ]
            lines = framing.get(npc_type, default_framing)
            bus.emit(EVT_BAX_SPEAK, line=random.choice(lines))
        self.open_terminal(npc_type)
        self._pending_advance = True

    def on_terminal_complete(self, outcome):
        # Return to flight at rest — the ship was visually frozen during the
        # terminal but its velocity was preserved; resuming flight at the
        # pre-terminal momentum is disorienting. Skip when an intercepting
        # barge is alive: that's a continuing combat encounter, momentum stays.
        if self._ship is not None and self._intercepting_barge is None:
            self._ship.body.vel    = Vec2()
            self._ship.body._force = Vec2()

        # ESC abort: static burst deals hull damage, no reward
        if outcome == "abort":
            if self._ship is not None:
                self._ship.take_damage(20, source="terminal_abort")
            bus.emit(EVT_BAX_SPEAK, line=random.choice([
                "You HUNG UP on a repo man. Their jammer just spiked our 'ull. Twenty points.",
                "Static blowback from the cut. Hull's taken a hit. Next time, negotiate.",
                "Rude. Also painful. Twenty hull gone from the signal blowback.",
            ]))
            self._active_terminal = None
            if self._intercepting_barge is not None:
                barge = self._intercepting_barge
                self._intercepting_barge = None
                barge.on_terminal_outcome("impound")
            return

        # Deduct any bribe the player paid
        npc = self._active_terminal.npc if self._active_terminal else None
        bribe_paid = npc.bribe_cost() if npc else 0
        if bribe_paid > 0:
            self.meta.add_debt(bribe_paid)
            self._sector_credits = max(0, self._sector_credits - bribe_paid)
            self._run_debt_reduced = max(0, self._run_debt_reduced - bribe_paid)
            bus.emit(EVT_BAX_SPEAK, line=random.choice([
                f"−{bribe_paid:,} credits out the airlock. Debt just went UP. "
                f"Not the cleanest exit, Boss.",
                f"Paid {bribe_paid:,} to walk. That's off this sector AND added to the tab.",
                f"Bribe logged: {bribe_paid:,} credits. I felt that one in the ledger.",
            ]))

        # Toll authority IMPOUND: he actually calls Local 404 — spawn a chaser
        if outcome == "impound" and getattr(npc, "barge_called", False):
            self._spawn_barge(immediate_chase=True)
            bus.emit(EVT_BAX_SPEAK, line=random.choice([
                "'E wasn't bluffin'. Repo on intercept course. STRAP IN.",
                "Toll bloke flagged us. Barge incoming. Brilliant. Just brilliant.",
                "Local 404 is en route. Should've paid. Or not been so polite.",
            ]))

        # Track winning path for cross-terminal cooldown
        if outcome in ("exploit", "release") and npc is not None:
            self._last_winning_path = getattr(npc, '_current_path', '')
        elif outcome == "impound":
            self._last_winning_path = ""  # reset on loss

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
        elif outcome == "release" and bribe_paid == 0:
            # Only give the full release bonus when no bribe was needed
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
            "slingshot_credit_each": SLINGSHOT_CREDIT_BONUS,
            "slingshot_credits": self._sector_slingshots * SLINGSHOT_CREDIT_BONUS,
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
        # Epic 12.1 — NO_SHOP mutator suppresses shop appearances entirely.
        if completed_sector in S.SHOP_SECTORS and self.mutators.shops_enabled():
            self._shop_pending = True
            self.bax_context["shops_visited_this_chapter"] = (
                self.bax_context.get("shops_visited_this_chapter", 0) + 1)
            bus.emit(EVT_SHOP_ENTER)
            return

        self._load_next_sector()

    def _load_next_sector(self):
        rng = random.Random(self._run_seed + self._sector_index * 997)
        self._sector       = generate_sector(self._sector_index, self._difficulty(),
                                             rng=rng, chapter=self._current_chapter(),
                                             force_theme=self._cold_sector_theme(rng))
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
                 sector_num  = self._sector_index + 1,
                 cargo_type  = cargo_type,
                 theme       = getattr(self._sector, "theme", ""),
                 sector_name = getattr(self._sector, "name", ""),
                 formerly    = getattr(self._sector, "formerly", ""))

        # Final sector: announce to Bax; extra barge only if player arrived healthy.
        if self._sector_index == S.SECTORS_PER_RUN - 1:
            bus.emit(EVT_FINAL_SECTOR)
            hull_pct = (self._ship.hull / S.HULL_MAX
                        if self._ship and self._ship.is_alive else 0.5)
            if hull_pct > 0.7:
                # Arrived in good shape — earned the gauntlet
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
        self._ai_ships.clear()
        self._aiship_hail_pending = None

        # 22% chance of alien flythrough per sector
        if random.random() < 0.22:
            self._alien = AlienShip()

        # AI ships — 1-3 per sector, queued so the player isn't dogpiled on entry.
        # First spawn deferred AISHIP_SPAWN_DELAY seconds after sector load.
        n_ai = random.randint(S.AISHIP_PER_SECTOR_MIN, S.AISHIP_PER_SECTOR_MAX)
        for i in range(n_ai):
            self._spawn_queue.append((S.AISHIP_SPAWN_DELAY + i * 7.0, "ai_ship"))

        # Barge spawn ramp — sector 1-2 are intro, then escalate.
        # Barges also deferred: first barge at 8s so player can orient.
        # Final sector extra spawns depend on hull state — see _load_next_sector.
        barge_count = 0
        if idx >= 2:
            barge_count = 1
        if idx >= 6:
            barge_count = 2
        barge_delay = max(4.0, 9.0 - idx * 0.5)
        for i in range(barge_count):
            self._spawn_queue.append((barge_delay + i * 6.0, "barge"))

        # Final sector: extra deferred barge only if player arrived healthy (checked in _load_next_sector).
        if idx == S.SECTORS_PER_RUN - 1:
            hull_pct = (self._ship.hull / S.HULL_MAX
                        if self._ship and self._ship.is_alive else 0.5)
            if hull_pct > 0.7:
                self._spawn_queue.append((barge_delay + 3.0, "barge"))
                self._spawn_queue.append((3.0, "debris"))

        # Demolition notice — 22% chance from sector 2 onward
        if idx >= 1 and random.random() < 0.22:
            speaker, line = random.choice(_DEMO_NOTICES)
            bus.emit(EVT_DEMO_NOTICE)
            bus.emit(EVT_COMMS_SPEAK, speaker=speaker, line=line)

        # --- Theme-based obstacle spawning (Epic 3) ---
        self._wrecks.clear()
        self._dead_station = None
        self._trash_field  = None
        self._mine_field   = None
        self._ice_field    = None
        self._comet_trail  = None
        self._flare_cd     = 22.0
        self._flare_active = False
        self._flare_t      = 0.0
        self._toll_pending = False
        self._toll_t       = 10.0
        self._well_hit_times.clear()

        theme = getattr(self._sector, "theme", "")

        if theme == THEME_WRECKAGE_BELT:
            # 1-2 wrecks (no fuel canisters in this sector)
            n = random.randint(1, 2)
            self._wrecks = [SpaceWreck() for _ in range(n)]
            self._canisters.clear()

        elif theme == THEME_INDUSTRIAL_GRAVEYARD:
            self._dead_station = DeadStation()
            self._wrecks = [SpaceWreck()]
            self._canisters.clear()

        elif theme == THEME_JUNK_BELT:
            self._trash_field = TrashField()
            self._canisters.clear()
            # Asteroid-field: more debris, higher HP
            extra = int(S.DEBRIS_COUNT * 0.6)
            for i in range(extra):
                rock = DebrisRock()
                rock.hp += 1
                self._debris.append(rock)

        elif theme == THEME_MINE_STRIP:
            self._mine_field = MineField()

        elif theme == THEME_FROZEN_TRAIL:
            self._ice_field   = IceField()
            self._comet_trail = CometTrail()

        elif theme == THEME_FLARE_CORRIDOR:
            self._flare_cd = 22.0   # first flare in ~22s

        elif theme == THEME_TOLL_AUTHORITY:
            self._toll_pending = True
            self._toll_t       = 10.0

    def _update_theme_obstacles(self, dt: float):
        """Per-frame update for all theme-specific obstacles."""
        ship = self._ship
        if ship is None or not ship.is_alive:
            return

        # Wrecks — collision check
        for wreck in self._wrecks:
            wreck.update(dt)
            if wreck.collides(ship.pos):
                ship.take_damage(wreck.damage, source="wreck")

        # Dead station — core + ring collision
        if self._dead_station is not None:
            self._dead_station.update(dt)
            if self._dead_station.collides_body(ship.pos):
                ship.take_damage(S.DEBRIS_DAMAGE * 1.2, source="dead_station")
            elif self._dead_station.collides_ring(ship.pos):
                ship.take_damage(self._dead_station.ring_damage, source="station_ring")

        # Trash field — chip damage + alive pieces
        if self._trash_field is not None:
            self._trash_field.update(dt)
            for piece in self._trash_field.alive_pieces:
                if piece.collides(ship.pos):
                    ship.take_damage(piece.chip_damage, source="trash")

        # Mine field — proximity arming + detonation
        if self._mine_field is not None:
            results = self._mine_field.update(dt, ship.pos)
            for r in results:
                if r == "detonate":
                    ship.take_damage(S.DEBRIS_DAMAGE * 2.0, source="mine")

        # Ice field — apply slick physics if inside
        if self._ice_field is not None:
            self._ice_field.apply_to(ship)

        # Comet trail — chip damage on fragment contact
        if self._comet_trail is not None:
            self._comet_trail.update(dt)
            for frag in self._comet_trail.all_fragments():
                if frag.collides(ship.pos):
                    ship.take_damage(self._comet_trail.chip_damage, source="comet")

        # Solar flare — periodic sweep
        if THEME_FLARE_CORRIDOR == getattr(self._sector, "theme", ""):
            self._flare_cd -= dt
            if self._flare_active:
                self._flare_t -= dt
                if self._flare_t <= 0:
                    self._flare_active = False
                    self._flare_cd     = random.uniform(18.0, 28.0)
            elif self._flare_cd <= 0:
                self._flare_active = True
                self._flare_t      = 4.0
                bus.emit(EVT_BAX_SPEAK, line=random.choice([
                    "Solar flare incoming. Yeah, ROMANTIC. Shield your eyes, the ship has none.",
                    "Radiation spike! The gun's gonna fizzle. Hold tight.",
                    "Flare sweep. HUD's gonna glitch. Keep flying straight.",
                ]))

        # Toll checkpoint — one-time terminal at t=10s
        if self._toll_pending and self._sector_timer >= self._toll_t:
            self._toll_pending = False
            self._open_toll_terminal()

    def _open_toll_terminal(self):
        from terminal.npc_logic import make_npc
        from terminal.terminal import Terminal
        bus.emit(EVT_BAX_SPEAK, line=random.choice([
            "Toll checkpoint live on the comm. Fifteen 'undred — pay, paperwork, or Union gripe.",
            "Transit Authority hailing. Gate Seven. Pay up or talk 'im down.",
            "Checkpoint booth on channel. 'E hates Local 404. Might work in our favour.",
        ]))
        npc = make_npc("toll_authority",
                       vocabulary_vault=getattr(self, "_vault", None),
                       run_context=self._build_run_context())
        terminal = Terminal(
            npc,
            blocked_paths=frozenset({self._last_winning_path}) if self._last_winning_path else frozenset(),
            vocabulary_vault=getattr(self, "_vault", None),
        )
        self._install_terminal(terminal)

    def _spawn_barge(self, immediate_chase: bool = False):
        # Epic 12.1 — QUIET_SECTOR: suppress sectors 0-2, double up sectors 3-4
        if self.mutators.is_active("quiet_sector"):
            if self._sector_index <= 2:
                return
            # Sectors 3-4: spawn a second barge immediately on the first call
            from antagonists.repo_barge import BargeState as _BS
            side  = random.choice(["left", "right", "top", "bottom"])
            pos_x = {"left": 0, "right": S.SCREEN_W}.get(side, random.randint(0, S.SCREEN_W))
            pos_y = {"top":  0, "bottom": S.SCREEN_H}.get(side, random.randint(0, S.SCREEN_H))
            extra = RepoBarge(pos_x, pos_y, self)
            if immediate_chase:
                extra.state = _BS.CHASE
            self._barges.append(extra)
        from antagonists.repo_barge import BargeState
        side  = random.choice(["left", "right", "top", "bottom"])
        pos_x = {"left": 0, "right": S.SCREEN_W}.get(side, random.randint(0, S.SCREEN_W))
        pos_y = {"top":  0, "bottom": S.SCREEN_H}.get(side, random.randint(0, S.SCREEN_H))
        barge = RepoBarge(pos_x, pos_y, self)
        if immediate_chase:
            barge.state = BargeState.CHASE
        self._barges.append(barge)

    def _spawn_ai_ship(self):
        """Spawn a contextual AI ship — pirates rarer early, derelicts capped."""
        idx = self._sector_index
        weights = {
            "fighter":   3,
            "freighter": 4,
            "hauler":    3,
            "gunboat":   1 if idx < 3 else 2,    # pirates rarer in early sectors
            "derelict":  2 if idx >= 1 else 0,
        }
        # Cap derelicts at 1 per sector
        if any(s.ship_class == "derelict" for s in self._ai_ships):
            weights["derelict"] = 0
        # Cap pirates at 1 per sector
        if any(s.is_pirate for s in self._ai_ships):
            weights["gunboat"] = 0
        pool = [k for k, w in weights.items() for _ in range(w)]
        if not pool:
            return
        ship_class = random.choice(pool)
        self._ai_ships.append(AIShip(ship_class=ship_class))

    def _on_aiship_hail(self, ship=None, npc_type=None, ship_class=None, **_):
        # Defer terminal opening — let core/game.py poll this and react via E key.
        if ship is None or npc_type is None:
            return
        self._aiship_hail_pending = ship
        bus.emit(EVT_BAX_SPEAK, line=random.choice([
            f"Hailer pulling alongside — {ship_class}. Press E to answer.",
            f"That ship's signalling. {ship_class.title()} build. Talk or don't.",
            f"Open comm request. {ship_class.title()}. Your call.",
        ]))

    def _on_aiship_destroyed(self, ship=None, **_):
        # Awards a small kill bonus when a hostile pirate goes down
        if ship is None:
            return
        if ship.is_pirate:
            bus.emit(EVT_BAX_SPEAK, priority=True, line=random.choice([
                "Hostile down. Nice shooting.",
                "Pirate gunboat scrapped. They had it coming.",
                "Threat neutralised. Good kill.",
            ]))

    # ------------------------------------------------------------------
    def _difficulty(self) -> float:
        return 1.0 + (self._sector_index / S.SECTORS_PER_RUN)

    def _current_chapter(self) -> int:
        completed = self.meta.chapters_completed
        for ch in [1, 2, 3, 4]:
            if ch not in completed:
                return ch
        return 4

    def _cold_sector_theme(self, rng: random.Random) -> str | None:
        """Epic 12.1 — COLD_SECTOR mutator forces every sector to FROZEN_TRAIL
        or MINE_STRIP. Returns None when the mutator is inactive."""
        if not self.mutators.is_active("cold_sector"):
            return None
        return rng.choice([THEME_FROZEN_TRAIL, THEME_MINE_STRIP])

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
    def ai_ships(self) -> list[AIShip]:
        return self._ai_ships

    def take_ai_hail(self) -> AIShip | None:
        """Consume and return the pending hail (if any). Caller opens terminal."""
        h = self._aiship_hail_pending
        self._aiship_hail_pending = None
        return h

    @property
    def sector_num(self) -> int:
        return self._sector_index + 1

    @property
    def jump_ready(self) -> bool:
        return self._sector_timer >= self._sector_dur

    @property
    def jump_cooldown(self) -> float:
        return max(0.0, self._sector_dur - self._sector_timer)

    def barge_threat_level(self) -> float:
        """0..1 scalar for AudioManager flight_pressure. 1.0 when tethered."""
        if not self._barges or self._ship is None:
            return 0.0
        from config import settings as S
        min_dist = min(
            (b.pos - self._ship.pos).length() for b in self._barges
        )
        proximity_range = getattr(S, 'BARGE_PROXIMITY_RANGE', 320.0)
        # 1.0 if any barge has active tether; else scale by inverse proximity
        for b in self._barges:
            if getattr(b, '_tether', None) and getattr(b._tether, 'active', False):
                return 1.0
        return max(0.0, 1.0 - min_dist / (proximity_range * 2.0))

    def cargo_alarm_level(self) -> float:
        """0..1 chapter-specific cargo stress level for flight_pressure."""
        if self._ship is None or self._ship.cargo is None:
            return 0.0
        cargo = self._ship.cargo
        # AcousticArchive: proximity to barge degrades audio
        if hasattr(cargo, 'degradation'):
            return float(cargo.degradation)
        # MycoShroom: spore level
        if hasattr(cargo, 'spore_level'):
            return float(cargo.spore_level)
        return 0.0

    # ------------------------------------------------------------------
    # Death respawn + sector restart (same run, fresh sector attempt)
    def respawn_after_death(self, ship) -> None:
        """After decanting: new clone, same contract, retry current sector."""
        from ship.gun import Gun

        ship._destroyed = False
        ship.hull = S.HULL_MAX
        ship.body = RigidBody2D(S.SCREEN_W / 2, S.SCREEN_H / 2, mass=ship.body.mass)
        ship.body.angle = 270.0
        ship.body.vel = Vec2()
        ship.gun = Gun()
        ship.controls_inverted = False
        self._active_terminal = None
        self._intercepting_barge = None
        self._pending_advance = False
        self._shower_rocks.clear()
        self._restart_current_sector(ship)
        bus.emit(EVT_BAX_SPEAK, line=random.choice([
            "New body, same debt, same sector. Welcome back to work, Boss.",
            "Clone's online. Sector's still hostile. Let's not die twice in a row.",
            "Decant complete. They billed us AND kept the contract. Typical. Fly.",
            "Fresh meat, old job. Hull's mint. Try not to spend it all at once.",
        ]))
        bus.emit(EVT_SECTOR_START,
                 sector_num=self._sector_index + 1,
                 cargo_type=type(ship.cargo).__name__ if ship.cargo else None,
                 theme=getattr(self._sector, "theme", ""),
                 sector_name=getattr(self._sector, "name", ""),
                 formerly=getattr(self._sector, "formerly", ""))

    def _restart_current_sector(self, ship) -> None:
        """Reset sector timer and respawn hazards; keep sector index and loadout."""
        rng = random.Random(self._run_seed + self._sector_index * 997)
        self._sector = generate_sector(
            self._sector_index, self._difficulty(),
            rng=rng, chapter=self._current_chapter(),
            force_theme=self._cold_sector_theme(rng),
        )
        self._sector_timer = 0.0
        self._jump_ready_fired = False
        self._kress_called_this_sector = False
        self._barges.clear()
        self._spawn_queue.clear()
        self._sling_well_t.clear()
        self._well_hit_times.clear()
        self._sector_slingshots = 0
        self._sector_snaps = 0
        self._sector_credits = 0
        self._sector_start_hull = ship.hull
        self._ship = ship
        self._spawn_sector_objects()
