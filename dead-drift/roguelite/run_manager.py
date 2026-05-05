from __future__ import annotations
import pygame
from roguelite.procedural import generate_sector, SectorLayout
from roguelite.loadout_draft import LoadoutDraft
from roguelite.meta_progression import MetaProgression
from antagonists.repo_barge import RepoBarge
from terminal.terminal import Terminal
from terminal.npc_logic import make_npc
from core.event_bus import bus, EVT_SECTOR_CLEAR, EVT_RUN_END
from config import settings as S


class RunManager:
    """
    Manages a single 10-Miler run: sector progression, barge spawning,
    and terminal phase transitions.
    """

    def __init__(self, meta: MetaProgression):
        self.meta            = meta
        self.draft           = LoadoutDraft(chapter=1)
        self._sector_index   = 0
        self._sector: SectorLayout | None = None
        self._barges: list[RepoBarge]     = []
        self._active_terminal: Terminal | None = None
        self._sector_timer   = 0.0
        self._sector_dur     = 45.0       # seconds per sector before jump allowed
        self._ship           = None

    # ------------------------------------------------------------------
    def start_run(self, ship):
        self._sector_index = 0
        self._barges.clear()
        self._active_terminal = None
        self._ship = ship
        self.draft = LoadoutDraft(chapter=self._current_chapter())
        ship.reset()

    def apply_draft(self, ship):
        """Apply confirmed loadout selections to the ship."""
        frame  = self.draft.selected_frame
        module = self.draft.selected_module
        cargo  = self.draft.selected_cargo

        ship.hull  = min(S.HULL_MAX, S.HULL_MAX + frame.get("hull_bonus", 0))
        ship.body.mass = S.SHIP_MASS * frame.get("mass_mod", 1.0)
        ship.chain.install(module, 1)
        ship.cargo = cargo
        self._ship = ship

        self._sector = generate_sector(self._sector_index, self._difficulty())

    # ------------------------------------------------------------------
    def update(self, dt: float):
        if self._sector is None or self._ship is None:
            return

        self._sector_timer += dt
        self._sector.gravity.apply_all(self._ship.body)

        cargo = self._ship.cargo
        if cargo is not None and hasattr(cargo, "update"):
            cargo.update(dt, self._ship)

        for barge in self._barges[:]:
            barge.update(dt)
            if barge.is_destroyed:
                self._barges.remove(barge)

    def handle_key(self, event: pygame.event.Event):
        if event.key == pygame.K_j and self._sector_timer >= self._sector_dur:
            self._advance_sector()

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

        if self._sector.is_ambush:
            self._spawn_barge()

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
