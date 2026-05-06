from __future__ import annotations
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
                             EVT_SLINGSHOT, EVT_BARGE_NEARBY, EVT_CANISTER_GRAB)
from config import settings as S


class RunManager:
    """
    Manages a single 10-Miler run: sector progression, barge spawning,
    debris fields, fuel canisters, slingshot detection.
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
        self._sector_timer     = 0.0
        self._sector_dur       = 20.0
        self._ship             = None

        # Slingshot tracking
        self._sling_well_t: dict[int, float] = {}
        self._sling_cd         = 0.0

        # Proximity alarm cooldown (so Bax doesn't spam it)
        self._prox_cd          = 0.0

        bus.subscribe(EVT_CANISTER_GRAB, self._on_canister_grab)

    # ------------------------------------------------------------------
    def start_run(self, ship):
        self._sector_index = 0
        self._barges.clear()
        self._debris.clear()
        self._canisters.clear()
        self._active_terminal = None
        self._ship = ship
        self.draft = LoadoutDraft(chapter=self._current_chapter())
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

        self._check_slingshot()
        self._check_proximity()

    def handle_key(self, event: pygame.event.Event):
        if event.key == pygame.K_j and self._sector_timer >= self._sector_dur:
            self._advance_sector()

    # ------------------------------------------------------------------
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

    def _advance_sector(self):
        self._sector_index += 1
        bus.emit(EVT_SECTOR_CLEAR, sector_num=self._sector_index)

        if self._sector_index >= S.SECTORS_PER_RUN:
            bus.emit(EVT_RUN_END, success=True)
            return

        self._sector       = generate_sector(self._sector_index, self._difficulty())
        self._sector_timer = 0.0
        self._barges.clear()
        self._sling_well_t.clear()
        self._spawn_sector_objects()

        if self._sector.is_ambush:
            self._spawn_barge()

    def _spawn_sector_objects(self):
        import random
        self._debris    = [DebrisRock() for _ in range(S.DEBRIS_COUNT)]
        self._canisters = [FuelCanister() for _ in range(S.CANISTER_COUNT)]

    def _spawn_barge(self):
        import random
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
    def sector_num(self) -> int:
        return self._sector_index + 1

    @property
    def jump_ready(self) -> bool:
        return self._sector_timer >= self._sector_dur

    @property
    def jump_cooldown(self) -> float:
        return max(0.0, self._sector_dur - self._sector_timer)
