import sys
import pygame

from config import settings as S
from core.state_manager import StateManager, GameState
from core.event_bus import bus, EVT_SHIP_DESTROYED, EVT_RUN_END
from roguelite.meta_progression import MetaProgression
from roguelite.run_manager import RunManager
from ship.ship import PlayerShip
from bax.bax import Bax
from renderer.vector_renderer import VectorRenderer
from renderer.hud_renderer import HUDRenderer
from renderer.terminal_renderer import TerminalRenderer


class Game:
    def __init__(self):
        pygame.init()
        self.screen  = pygame.display.set_mode((S.SCREEN_W, S.SCREEN_H))
        pygame.display.set_caption(S.TITLE)
        self.clock   = pygame.time.Clock()
        self.running = True

        self.states  = StateManager()
        self.meta    = MetaProgression()
        self.run_mgr = RunManager(self.meta)
        self.ship    = PlayerShip()
        self.bax     = Bax(self.ship, self.meta)

        self.vec_renderer  = VectorRenderer(self.screen)
        self.hud_renderer  = HUDRenderer(self.screen)
        self.term_renderer = TerminalRenderer(self.screen)

        self._wire_events()

    def _wire_events(self):
        bus.subscribe(EVT_SHIP_DESTROYED, self._on_ship_destroyed)
        bus.subscribe(EVT_RUN_END,        self._on_run_end)

    def _on_ship_destroyed(self, **_):
        self.meta.apply_death_penalty()
        self.states.transition(GameState.DECANTING)

    def _on_run_end(self, success, **_):
        if success:
            self.meta.clear_debt_chunk()
        self.meta.save()
        self.states.transition(GameState.MAIN_MENU)

    # ------------------------------------------------------------------
    def run(self):
        self.states.transition(GameState.LOADOUT_DRAFT)

        while self.running:
            dt = self.clock.tick(S.FPS) / 1000.0
            self._handle_events()
            self._update(dt)
            self._render()

    # ------------------------------------------------------------------
    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                self._route_keydown(event)

    def _route_keydown(self, event: pygame.event.Event):
        state = self.states.state

        if state == GameState.FLIGHT:
            self.run_mgr.handle_key(event)
        elif state == GameState.TERMINAL:
            self.run_mgr.active_terminal.handle_key(event)
        elif state == GameState.LOADOUT_DRAFT:
            self.run_mgr.draft.handle_key(event)
        elif state in (GameState.DECANTING, GameState.MAIN_MENU):
            if event.key == pygame.K_RETURN:
                self.run_mgr.start_run(self.ship)
                self.states.transition(GameState.LOADOUT_DRAFT)

    # ------------------------------------------------------------------
    def _update(self, dt: float):
        state = self.states.state

        if state == GameState.FLIGHT:
            self.run_mgr.update(dt)
            self.ship.update(dt)
            self.bax.update(dt)

        elif state == GameState.TERMINAL:
            self.run_mgr.active_terminal.update(dt)

        elif state == GameState.LOADOUT_DRAFT:
            if self.run_mgr.draft.is_confirmed():
                self.run_mgr.apply_draft(self.ship)
                self.states.transition(GameState.FLIGHT)

        elif state == GameState.DECANTING:
            pass  # timed screen; transition handled by run loop timer

    # ------------------------------------------------------------------
    def _render(self):
        self.screen.fill(S.VOID)
        state = self.states.state

        if state == GameState.FLIGHT:
            self.vec_renderer.draw(self.run_mgr, self.ship)
            self.hud_renderer.draw(self.ship)

        elif state == GameState.TERMINAL:
            self.term_renderer.draw(self.run_mgr.active_terminal)

        elif state == GameState.LOADOUT_DRAFT:
            self.run_mgr.draft.render(self.screen)

        elif state == GameState.DECANTING:
            self._render_decanting()

        pygame.display.flip()

    def _render_decanting(self):
        font = pygame.font.SysFont("monospace", 18)
        lines = [
            "DECANTING SEQUENCE INITIATED",
            f"Clone #{self.meta.clone_count}  |  Body: BASELINE MODEL",
            "",
            f"Clone fluid . . . . . -{S.CLONE_FLUID_FEE:,} cr",
            f"Wreckage tow  . . . . -{S.WRECKAGE_TOW_FEE:,} cr",
            f"Clone fee . . . . . . -{S.BASE_CLONE_DEBT:,} cr",
            "",
            f"TOTAL DEBT: {self.meta.debt:,} cr",
            "",
            "[ PRESS ENTER TO BEGIN NEXT RUN ]",
        ]
        y = S.SCREEN_H // 3
        for line in lines:
            surf = font.render(line, True, S.AMBER_TERM)
            self.screen.blit(surf, (S.SCREEN_W // 2 - surf.get_width() // 2, y))
            y += 28
