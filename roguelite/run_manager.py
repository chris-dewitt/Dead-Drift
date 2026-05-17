from __future__ import annotations
import random
import pygame
from roguelite.procedural import generate_sector, SectorLayout
from roguelite.loadout_draft import LoadoutDraft
from roguelite.meta_progression import MetaProgression
from antagonists.repo_barge import RepoBarge
from antagonists.debris import DebrisRock
from antagonists.fuel_canister import FuelCanister
from terminal.terminal import Terminal
from terminal.npc_logic import make_npc
from core.event_bus import (bus, EVT_SECTOR_CLEAR, EVT_RUN_END,
                             EVT_SLINGSHOT, EVT_BARGE_NEARBY, EVT_CANISTER_GRAB,
                             EVT_COMMS_INTERCEPT, EVT_DEBRIS_SHOWER, EVT_SCAN_PING,
                             EVT_COMMS_SPEAK, EVT_TETHER_SNAP, EVT_BAX_SPEAK)
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
        self._run_debt_reduced = 0   # credits recovered this run (shown in HUD)

        bus.subscribe(EVT_CANISTER_GRAB, self._on_canister_grab)
        bus.subscribe(EVT_TETHER_SNAP,   self._on_tether_snap)

    # ------------------------------------------------------------------
    def start_run(self, ship):
        self._sector_index = 0
        self._barges.clear()
        self._debris.clear()
        self._canisters.clear()
        self._shower_rocks.clear()
        self._active_terminal    = None
        self._intercepting_barge = None
        self._pending_advance    = False
        self._kress_called_this_sector = False
        self._run_debt_reduced   = 0
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
        self._spawn_sector_objects()

    # ------------------------------------------------------------------
    def update(self, dt: float):
        if self._sector is None or self._ship is None:
            return

        self._sector_timer += dt
        self._sling_cd      = max(0.0, self._sling_cd - dt)
        self._prox_cd       = max(0.0, self._prox_cd  - dt)

        self._sector.gravity.apply_all(self._ship.body)

        cargo = self._ship.cargo
        if cargo is not None and hasattr(cargo, "update"):
            cargo.update(dt, self._ship)

        for barge in self._barges[:]:
            barge.update(dt)
            if barge.is_destroyed:
                self._barges.remove(barge)

        for rock in self._debris:
            rock.update(dt)
            if rock.collides(self._ship.pos):
                self._ship.take_damage(S.DEBRIS_DAMAGE)
                rock.hit()

        for can in self._canisters:
            can.update(dt, self._ship.pos)

        # Debris shower tick
        if self._shower_t > 0:
            self._shower_t -= dt
            for rock in self._shower_rocks:
                rock.update(dt)
                if rock.collides(self._ship.pos):
                    self._ship.take_damage(S.DEBRIS_DAMAGE)
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

    def _on_tether_snap(self, **_):
        bonus = 1200
        self.meta.pay_off(bonus)
        self._run_debt_reduced += bonus
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
    def open_terminal(self, npc_type: str, **npc_kwargs) -> Terminal:
        npc = make_npc(npc_type, **npc_kwargs)
        self._active_terminal = Terminal(npc)
        return self._active_terminal

    def open_barge_terminal(self, barge) -> Terminal:
        """Mid-flight intercept: Gary opens a comm, no sector advance on close."""
        self._intercepting_barge = barge
        return self.open_terminal("gary", intercepted=True)

    def _open_jump_terminal(self):
        npc_type = random.choice(["gary", "synthetic_droid", "union_dispatcher"])
        self.open_terminal(npc_type)
        self._pending_advance = True

    def on_terminal_complete(self, outcome):
        # Grant debt reduction based on how the negotiation went
        if outcome == "exploit":
            bonus = 9000
            self.meta.pay_off(bonus)
            self._run_debt_reduced += bonus
            bus.emit(EVT_BAX_SPEAK, line=random.choice([
                f"EXPLOITED their system. {bonus:,} credits rerouted. Blevins is gonna lose his MIND.",
                f"Their firewall had the structural integrity of wet paper. {bonus:,} back.",
                f"You just robbed a repo man digitally. {bonus:,} off. I'm proud.",
            ]))
        elif outcome == "release":
            bonus = 2500
            self.meta.pay_off(bonus)
            self._run_debt_reduced += bonus
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
        sector_bonus = 4500
        self.meta.pay_off(sector_bonus)
        self._run_debt_reduced += sector_bonus

        self._sector_index += 1
        bus.emit(EVT_SECTOR_CLEAR, sector_num=self._sector_index)

        if self._sector_index >= S.SECTORS_PER_RUN:
            bus.emit(EVT_RUN_END, success=True)
            return

        self._sector       = generate_sector(self._sector_index, self._difficulty())
        self._sector_timer = 0.0
        self._barges.clear()
        self._sling_well_t.clear()
        self._kress_called_this_sector = False
        self._spawn_sector_objects()

        if self._sector.is_ambush:
            self._spawn_barge()

    def _spawn_sector_objects(self):
        self._debris    = [DebrisRock() for _ in range(S.DEBRIS_COUNT)]
        self._canisters = [FuelCanister() for _ in range(S.CANISTER_COUNT)]

    def _spawn_barge(self):
        side  = random.choice(["left", "right", "top", "bottom"])
        pos_x = {"left": 0, "right": S.SCREEN_W}.get(side, random.randint(0, S.SCREEN_W))
        pos_y = {"top":  0, "bottom": S.SCREEN_H}.get(side, random.randint(0, S.SCREEN_H))
        self._barges.append(RepoBarge(pos_x, pos_y, self))

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
    def sector_num(self) -> int:
        return self._sector_index + 1

    @property
    def jump_ready(self) -> bool:
        return self._sector_timer >= self._sector_dur

    @property
    def jump_cooldown(self) -> float:
        return max(0.0, self._sector_dur - self._sector_timer)
