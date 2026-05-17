import sys
import math
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
from renderer.cockpit_renderer import CockpitRenderer
from audio.audio_manager import AudioManager


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

        self.vec_renderer     = VectorRenderer(self.screen)
        self.hud_renderer     = HUDRenderer(self.screen)
        self.term_renderer    = TerminalRenderer(self.screen)
        # Pass live references so the cockpit info panel always reads current state
        self.cockpit_renderer = CockpitRenderer(
            self.screen, self.ship, self.run_mgr, self.meta
        )
        self.audio = AudioManager()

        self._dt                  = 0.016
        self._run_just_completed  = False

        self._wire_events()

    def _wire_events(self):
        bus.subscribe(EVT_SHIP_DESTROYED, self._on_ship_destroyed)
        bus.subscribe(EVT_RUN_END,        self._on_run_end)

    def _on_ship_destroyed(self, **_):
        self.meta.apply_death_penalty()
        self._run_just_completed = False
        self.states.transition(GameState.DECANTING)

    def _on_run_end(self, success, **_):
        if success:
            self.meta.clear_debt_chunk()
        self.meta.save()
        self._run_just_completed = success
        self.states.transition(GameState.MAIN_MENU)

    # ------------------------------------------------------------------
    def run(self, start_state: GameState = None, start_sector: int = 0):
        """
        Entry point.  Pass start_state to boot directly into any screen
        (used by test_stage.py).
        """
        if start_state is None or start_state == GameState.MAIN_MENU:
            self.states.transition(GameState.MAIN_MENU)
        elif start_state == GameState.LOADOUT_DRAFT:
            self.run_mgr.start_run(self.ship)
            self.states.transition(GameState.LOADOUT_DRAFT)
        elif start_state == GameState.FLIGHT:
            self._dev_start_flight(start_sector)
        elif start_state == GameState.DECANTING:
            self.states.transition(GameState.DECANTING)
        else:
            self.states.transition(start_state)

        while self.running:
            self._dt = self.clock.tick(S.FPS) / 1000.0
            self._handle_events()
            self._update(self._dt)
            self._render()

    def _dev_start_flight(self, sector_index: int = 0):
        """Boot straight into flight at the given sector (for dev/testing)."""
        from roguelite.procedural import generate_sector
        from ship.modules.thruster import Thruster
        from ship.modules.life_support import LifeSupport
        from ship.loadout import SignalChain

        self.run_mgr.start_run(self.ship)
        self.run_mgr._sector_index = sector_index
        self.run_mgr._sector       = generate_sector(sector_index, self.run_mgr._difficulty())
        self.run_mgr._spawn_sector_objects()

        self.ship.chain = SignalChain()
        self.ship.chain.install(LifeSupport(),       0)
        self.ship.chain.install(Thruster("salvage"), 1)
        self.run_mgr._ship = self.ship

        self.states.transition(GameState.FLIGHT)

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
            if self.run_mgr.active_terminal is not None:
                self.run_mgr.active_terminal.handle_key(event)
        elif state == GameState.LOADOUT_DRAFT:
            self.run_mgr.draft.handle_key(event)
        elif state in (GameState.DECANTING, GameState.MAIN_MENU):
            if event.key == pygame.K_RETURN:
                self.run_mgr.start_run(self.ship)
                self._run_just_completed = False
                self.states.transition(GameState.LOADOUT_DRAFT)

    # ------------------------------------------------------------------
    def _update(self, dt: float):
        state = self.states.state

        if state == GameState.FLIGHT:
            self.run_mgr.update(dt)
            self.ship.update(dt)
            self.bax.update(dt)
            self.cockpit_renderer.update(dt)
            self.audio.update(self.ship.body.speed(), dt)
            # Terminal opened by jump key — transition immediately
            if self.run_mgr.active_terminal is not None:
                self.states.transition(GameState.TERMINAL)

        elif state == GameState.TERMINAL:
            terminal = self.run_mgr.active_terminal
            if terminal is not None:
                terminal.update(dt)
                # Ship keeps drifting mid-intercept — gravity + momentum, no controls
                if self.run_mgr._intercepting_barge is not None:
                    sector = self.run_mgr.sector
                    if sector is not None:
                        sector.gravity.apply_all(self.ship.body)
                    self.ship.body.integrate(dt)
                    self.ship._wrap_screen()
                if terminal.is_done:
                    self.run_mgr.on_terminal_complete(terminal.outcome)
                    # Only go back to FLIGHT if run_end hasn't already redirected us
                    if self.states.state == GameState.TERMINAL:
                        self.states.transition(GameState.FLIGHT)

        elif state == GameState.LOADOUT_DRAFT:
            if self.run_mgr.draft.is_confirmed():
                self.run_mgr.apply_draft(self.ship)
                self.states.transition(GameState.FLIGHT)

        elif state == GameState.DECANTING:
            pass

    # ------------------------------------------------------------------
    def _render(self):
        self.screen.fill(S.VOID)
        state = self.states.state

        if state == GameState.FLIGHT:
            self.vec_renderer.draw(self.run_mgr, self.ship, self._dt)
            self.hud_renderer.draw(self.ship)
            self._render_sector_hud()
            self.cockpit_renderer.draw(pygame.time.get_ticks() / 1000.0)

        elif state == GameState.TERMINAL:
            self.term_renderer.draw(self.run_mgr.active_terminal)
            if self.run_mgr._intercepting_barge is not None:
                self._render_drift_strip()

        elif state == GameState.LOADOUT_DRAFT:
            self.run_mgr.draft.render(self.screen)

        elif state == GameState.DECANTING:
            self._render_decanting()

        elif state == GameState.MAIN_MENU:
            self._render_main_menu()

        pygame.display.flip()

    def _render_sector_hud(self):
        font  = pygame.font.SysFont("monospace", 14)
        rm    = self.run_mgr
        sec_w = S.SCREEN_W

        sec_txt = font.render(
            f"SECTOR  {min(rm.sector_num, S.SECTORS_PER_RUN)} / {S.SECTORS_PER_RUN}",
            True, S.GREY_DEAD,
        )
        self.screen.blit(sec_txt, (sec_w // 2 - sec_txt.get_width() // 2, 20))

        if rm.jump_ready:
            jump_txt = font.render("[ J ]  JUMP READY", True, S.GREEN_TERM)
        else:
            jump_txt = font.render(
                f"JUMP IN  {rm.jump_cooldown:>4.0f}s", True, S.GREY_DEAD,
            )
        self.screen.blit(jump_txt, (sec_w // 2 - jump_txt.get_width() // 2, 38))

        # Speed readout
        speed     = self.ship.body.speed()
        speed_col = (255, 120, 0) if speed > 500 else S.GREY_DEAD
        spd_txt   = font.render(f"{speed:>5.0f} m/s", True, speed_col)
        self.screen.blit(spd_txt, (sec_w // 2 - spd_txt.get_width() // 2, 56))

    def _render_drift_strip(self):
        """Amber status bar shown at top of terminal during mid-flight intercept."""
        speed    = self.ship.body.speed()
        hull_pct = self.ship.hull_pct * 100
        t        = pygame.time.get_ticks() / 1000.0
        blink    = int(t * 2) % 2 == 0

        font = pygame.font.SysFont("monospace", 14, bold=True)
        col  = (255, 80, 0) if speed > 400 else S.AMBER_TERM

        strip = pygame.Surface((S.SCREEN_W, 20), pygame.SRCALPHA)
        strip.fill((0, 0, 0, 180))
        self.screen.blit(strip, (0, 0))

        if blink:
            warn = font.render(
                f"  !! SHIP DRIFTING  {speed:>5.0f} m/s  |  HULL {hull_pct:.0f}%  |  "
                "NEGOTIATE OR CLAMP IN ~20s  !!",
                True, col)
            self.screen.blit(warn, (8, 3))

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

    def _render_main_menu(self):
        t  = pygame.time.get_ticks() / 1000.0
        cx = S.SCREEN_W // 2

        self.vec_renderer.draw_menu_background(t)

        # Title
        font_title = pygame.font.SysFont("monospace", 76, bold=True)
        title_surf = font_title.render("DEAD DRIFT", True, S.AMBER_TERM)
        ty = 95
        self.screen.blit(title_surf, (cx - title_surf.get_width() // 2, ty))

        ul_w = title_surf.get_width() + 20
        ul_x = cx - ul_w // 2
        pygame.draw.line(self.screen, (120, 80, 0),
                         (ul_x, ty + title_surf.get_height() + 4),
                         (ul_x + ul_w, ty + title_surf.get_height() + 4), 1)

        font_sub = pygame.font.SysFont("monospace", 18)
        tagline  = font_sub.render(
            "5 sectors.  crushing debt.  one rusted ship.", True, (70, 70, 90))
        self.screen.blit(tagline, (cx - tagline.get_width() // 2, ty + 88))

        y_info = ty + 148
        font_med = pygame.font.SysFont("monospace", 16)

        if self._run_just_completed:
            c = font_med.render("RUN COMPLETE  //  DEBT REDUCED", True, S.GREEN_TERM)
            self.screen.blit(c, (cx - c.get_width() // 2, y_info))
            y_info += 28

        if self.meta.debt > 0:
            debt_col = S.RED_WARN if self.meta.debt > 50000 else S.AMBER_TERM
            ds = font_med.render(
                f"OUTSTANDING DEBT:  {self.meta.debt:,} cr   //   Clone #{self.meta.clone_count}",
                True, debt_col)
            self.screen.blit(ds, (cx - ds.get_width() // 2, y_info))

        # Blinking prompt
        if int(t * 2) % 2 == 0:
            font_enter = pygame.font.SysFont("monospace", 22, bold=True)
            es = font_enter.render("[ PRESS ENTER TO BEGIN RUN ]", True, S.WHITE_VEC)
            self.screen.blit(es, (cx - es.get_width() // 2, S.SCREEN_H // 2 + 40))

        # Lore
        font_lore = pygame.font.SysFont("monospace", 13)
        lore_lines = [
            "Union of Repo Men, Local 404.",
            "They will come for what you carry.",
            "Fly fast.  Drift hard.  Don't die again.",
        ]
        for i, line in enumerate(lore_lines):
            s = font_lore.render(line, True, (55, 55, 70))
            self.screen.blit(s, (cx - s.get_width() // 2, S.SCREEN_H - 225 + i * 20))

        # Controls
        font_hint = pygame.font.SysFont("monospace", 12)
        hints = [
            "WASD / ARROWS  move     SPACE  fire     J  jump     N  spawn barge",
        ]
        for i, line in enumerate(hints):
            s = font_hint.render(line, True, (45, 45, 58))
            self.screen.blit(s, (cx - s.get_width() // 2, S.SCREEN_H - 75 + i * 18))

        self._render_menu_bax_portrait(t)

    def _render_menu_bax_portrait(self, t: float):
        px = S.SCREEN_W - 110
        py = S.SCREEN_H - 120
        head = [(px-14,py-22),(px+14,py-22),(px+18,py-4),(px-18,py-4)]
        pygame.draw.polygon(self.screen, (20, 20, 30), head)
        pygame.draw.polygon(self.screen, (55, 44, 0), head, 1)
        glow   = 0.4 + 0.3 * abs(math.sin(t * 0.9))
        ec     = (int(180 * glow), int(110 * glow), 0)
        pygame.draw.circle(self.screen, ec, (px-5, py-14), 3)
        pygame.draw.circle(self.screen, ec, (px+5, py-14), 3)
        pygame.draw.line(self.screen, (55, 44, 0), (px+12, py-22), (px+16, py-32), 1)
        pygame.draw.circle(self.screen, (80, 60, 0), (px+16, py-33), 2)
        body = [(px-16,py-4),(px+16,py-4),(px+14,py+20),(px-14,py+20)]
        pygame.draw.polygon(self.screen, (18, 18, 28), body)
        pygame.draw.polygon(self.screen, (55, 44, 0), body, 1)
