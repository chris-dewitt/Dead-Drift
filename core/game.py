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
        self.cockpit_renderer = CockpitRenderer(self.screen)

        self._dt = 0.016
        self._run_just_completed = False  # True if last run succeeded

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
    def run(self):
        self.states.transition(GameState.MAIN_MENU)

        while self.running:
            self._dt = self.clock.tick(S.FPS) / 1000.0
            self._handle_events()
            self._update(self._dt)
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

        elif state == GameState.TERMINAL:
            self.run_mgr.active_terminal.update(dt)

        elif state == GameState.LOADOUT_DRAFT:
            if self.run_mgr.draft.is_confirmed():
                self.run_mgr.apply_draft(self.ship)
                self.states.transition(GameState.FLIGHT)

        elif state == GameState.DECANTING:
            pass  # timed screen; transition handled by ENTER key

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
        t = pygame.time.get_ticks() / 1000.0

        # Animated background
        self.vec_renderer.draw_menu_background(t)

        cx = S.SCREEN_W // 2

        # Title
        font_title = pygame.font.SysFont("monospace", 76, bold=True)
        title_surf = font_title.render("DEAD DRIFT", True, S.AMBER_TERM)
        ty = 100
        self.screen.blit(title_surf, (cx - title_surf.get_width() // 2, ty))

        # Amber glow underline
        ul_w = title_surf.get_width() + 20
        ul_x = cx - ul_w // 2
        pygame.draw.line(self.screen, (120, 80, 0),
                         (ul_x, ty + title_surf.get_height() + 4),
                         (ul_x + ul_w, ty + title_surf.get_height() + 4), 1)

        # Tagline
        font_sub = pygame.font.SysFont("monospace", 18)
        tagline = font_sub.render(
            "10 sectors. crushing debt. one rusted ship.", True, (70, 70, 90))
        self.screen.blit(tagline, (cx - tagline.get_width() // 2, ty + 88))

        # Run complete / debt info block
        font_med = pygame.font.SysFont("monospace", 16)
        y_info = ty + 148

        if self._run_just_completed:
            complete_surf = font_med.render(
                "RUN COMPLETE  //  DEBT REDUCED", True, S.GREEN_TERM)
            self.screen.blit(complete_surf, (cx - complete_surf.get_width() // 2, y_info))
            y_info += 28

        if self.meta.debt > 0:
            debt_col = S.RED_WARN if self.meta.debt > 50000 else S.AMBER_TERM
            debt_surf = font_med.render(
                f"OUTSTANDING DEBT:  {self.meta.debt:,} cr   //   Clone #{self.meta.clone_count}",
                True, debt_col)
            self.screen.blit(debt_surf, (cx - debt_surf.get_width() // 2, y_info))

        # Atmospheric lore text
        lore_y = S.SCREEN_H - 230
        font_lore = pygame.font.SysFont("monospace", 13)
        lore_lines = [
            "Union of Repo Men, Local 404.",
            "They will come for what you carry.",
            "Fly fast. Drift hard. Don't die again.",
        ]
        for i, line in enumerate(lore_lines):
            surf = font_lore.render(line, True, (55, 55, 70))
            self.screen.blit(surf, (cx - surf.get_width() // 2, lore_y + i * 20))

        # Controls hint
        font_hint = pygame.font.SysFont("monospace", 12)
        hint_lines = [
            "WASD / ARROWS  move       J  jump sector       N  spawn barge (sandbox)",
            "ESC  quit",
        ]
        for i, line in enumerate(hint_lines):
            surf = font_hint.render(line, True, (45, 45, 58))
            self.screen.blit(surf, (cx - surf.get_width() // 2,
                                    S.SCREEN_H - 75 + i * 18))

        # Blinking PRESS ENTER prompt
        if int(t * 2) % 2 == 0:
            font_enter = pygame.font.SysFont("monospace", 22, bold=True)
            enter_surf = font_enter.render("[ PRESS ENTER TO BEGIN RUN ]",
                                           True, S.WHITE_VEC)
            ey = S.SCREEN_H // 2 + 40
            self.screen.blit(enter_surf, (cx - enter_surf.get_width() // 2, ey))

        # Bax portrait (small, bottom-right corner)
        self._render_menu_bax_portrait(t)

    def _render_menu_bax_portrait(self, t: float):
        """Tiny Bax silhouette on the menu for atmosphere."""
        px = S.SCREEN_W - 110
        py = S.SCREEN_H - 120
        head = [(px-14,py-22),(px+14,py-22),(px+18,py-4),(px-18,py-4)]
        pygame.draw.polygon(self.screen, (20, 20, 30), head)
        pygame.draw.polygon(self.screen, (55, 44, 0), head, 1)
        # Eyes — dim amber
        glow = 0.4 + 0.3 * abs(math.sin(t * 0.9))
        eye_col = (int(180 * glow), int(110 * glow), 0)
        pygame.draw.circle(self.screen, eye_col, (px - 5, py - 14), 3)
        pygame.draw.circle(self.screen, eye_col, (px + 5, py - 14), 3)
        # Antenna
        pygame.draw.line(self.screen, (55, 44, 0),
                         (px + 12, py - 22), (px + 16, py - 32), 1)
        pygame.draw.circle(self.screen, (80, 60, 0), (px + 16, py - 33), 2)
        # Body
        body = [(px-16,py-4),(px+16,py-4),(px+14,py+20),(px-14,py+20)]
        pygame.draw.polygon(self.screen, (18, 18, 28), body)
        pygame.draw.polygon(self.screen, (55, 44, 0), body, 1)
