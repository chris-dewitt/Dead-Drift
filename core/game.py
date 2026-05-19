import sys
import math
import random
import pygame

from config import settings as S
from core.state_manager import StateManager, GameState
from core.event_bus import bus, EVT_SHIP_DESTROYED, EVT_RUN_END, EVT_TORCH_ACTIVE, EVT_DEBT_DING
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
        self._torch_warn_t        = 0.0   # seconds remaining until next module loss
        self._last_debt_milestone = 0     # last 1000cr milestone we dinged

        self._wire_events()

    def _wire_events(self):
        bus.subscribe(EVT_SHIP_DESTROYED, self._on_ship_destroyed)
        bus.subscribe(EVT_RUN_END,        self._on_run_end)
        bus.subscribe(EVT_TORCH_ACTIVE,   self._on_torch_active)

    def _on_torch_active(self, countdown=5.0, **_):
        self._torch_warn_t = countdown

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
            self._torch_warn_t = max(0.0, self._torch_warn_t - dt)
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
            if self.run_mgr._flash_t > 0 and self.run_mgr._last_stats:
                self._render_sector_flash(
                    self.run_mgr._last_stats, self.run_mgr._flash_t)
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
        font     = pygame.font.SysFont("monospace", 14)
        font_sm  = pygame.font.SysFont("monospace", 12)
        font_hd  = pygame.font.SysFont("monospace", 14, bold=True)
        rm    = self.run_mgr
        sec_w = S.SCREEN_W
        t     = pygame.time.get_ticks() / 1000.0

        sec_txt = font.render(
            f"SECTOR  {min(rm.sector_num, S.SECTORS_PER_RUN)} / {S.SECTORS_PER_RUN}",
            True, S.GREY_DEAD,
        )
        self.screen.blit(sec_txt, (sec_w // 2 - sec_txt.get_width() // 2, 20))

        # Sector name + "formerly" — the corporate rebrand
        sector = rm.sector
        if sector is not None and getattr(sector, "name", ""):
            name_surf = font_hd.render(sector.name, True, (170, 170, 110))
            self.screen.blit(name_surf,
                             (sec_w // 2 - name_surf.get_width() // 2, 74))
            if sector.formerly:
                fm_surf = font_sm.render(
                    f"(formerly: {sector.formerly})", True, (95, 95, 95))
                self.screen.blit(fm_surf,
                                 (sec_w // 2 - fm_surf.get_width() // 2, 92))

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

        # Debt ticker — bottom-left
        interest_per_sec = max(0.01, self.meta.debt * S.DEBT_INTEREST_RATE)
        session_accrued  = t * interest_per_sec
        displayed_debt   = int(self.meta.debt + session_accrued)
        milestone = (displayed_debt // 1000) * 1000
        if milestone > self._last_debt_milestone and milestone > 0:
            self._last_debt_milestone = milestone
            bus.emit(EVT_DEBT_DING)
        blink = int(t * 1.6) % 2 == 0
        ticker_col = (110, 50, 50) if not blink else (160, 60, 60)
        debt_txt = font.render(
            f"DEBT  {displayed_debt:,} cr  +{interest_per_sec:.2f}/s", True, ticker_col)

        run_reduced = rm._run_debt_reduced
        if run_reduced > 0:
            rec_surf = font_sm.render(
                f"recovered: -{run_reduced:,} cr this run", True, (55, 185, 75))
            self.screen.blit(rec_surf, (10, S.FLIGHT_H - 38))

        self.screen.blit(debt_txt, (10, S.FLIGHT_H - 22))

        # Kress comm hint — bottom-right, dim when unavailable, brighter when ready
        kress_avail = not rm._kress_called_this_sector
        k_col   = (90, 110, 130) if kress_avail else (60, 60, 60)
        k_label = "[ K ]  CALL KRESS" if kress_avail else "[ K ]  channel used"
        k_surf  = font_sm.render(k_label, True, k_col)
        self.screen.blit(k_surf, (sec_w - k_surf.get_width() - 12, S.FLIGHT_H - 22))

        # Torch countdown — pulsing red danger bar when barge is torching hull
        if self._torch_warn_t > 0:
            pulse = abs(math.sin(t * 9.0))
            r_val = int(200 + 55 * pulse)
            torch_font = pygame.font.SysFont("monospace", 20, bold=True)
            torch_surf = torch_font.render(
                f"!! SNAP TETHER — MODULE LOSS IN  {self._torch_warn_t:.1f}s !!",
                True, (r_val, 30, 20))
            cx_t = sec_w // 2 - torch_surf.get_width() // 2
            # Dark backing strip
            bg_r  = pygame.Rect(cx_t - 6, S.FLIGHT_H // 2 - 40,
                                torch_surf.get_width() + 12, 30)
            pygame.draw.rect(self.screen, (12, 2, 2), bg_r)
            pygame.draw.rect(self.screen, (r_val, 30, 20), bg_r, 1)
            self.screen.blit(torch_surf, (cx_t, S.FLIGHT_H // 2 - 37))

    def _render_sector_flash(self, stats: dict, t_left: float):
        """Celebration card overlaid for ~2.8s after a sector clear."""
        cx = S.SCREEN_W // 2
        cy = S.FLIGHT_H // 2
        W, H = 480, 252

        # Fade alpha: pop in fast, hold, fade out in last 0.5s
        if t_left > 2.5:
            fade = (2.8 - t_left) / 0.3
        elif t_left < 0.5:
            fade = t_left / 0.5
        else:
            fade = 1.0
        fade = max(0.0, min(1.0, fade))
        a    = int(255 * fade)
        a_bg = int(225 * fade)

        panel = pygame.Surface((W, H), pygame.SRCALPHA)
        panel.fill((6, 18, 8, a_bg))
        pygame.draw.rect(panel, (0, 220, 90, a), (0, 0, W, H), 2)
        pygame.draw.rect(panel, (0, 110, 45, a), (4, 4, W - 8, H - 8), 1)

        font_hd = pygame.font.SysFont("monospace", 19, bold=True)
        font_md = pygame.font.SysFont("monospace", 17)
        font_sm = pygame.font.SysFont("monospace", 13)

        # Header
        hdr = font_hd.render(
            f"SECTOR {stats['sector']} / {S.SECTORS_PER_RUN}  CLEARED",
            True, (0, 240, 110))
        hdr.set_alpha(a)
        panel.blit(hdr, (W // 2 - hdr.get_width() // 2, 20))
        pygame.draw.line(panel, (0, 130, 60, a), (24, 54), (W - 24, 54), 1)

        rows = [
            ("CREDITS RECOVERED", f"{stats['credits']:,} cr",
             (90, 230, 110) if stats['credits'] > 0 else (140, 140, 140)),
            ("TETHER SNAPS",      f"{stats['snaps']}",
             (255, 180, 50) if stats['snaps'] > 0 else (110, 110, 110)),
            ("SLINGSHOTS",        f"{stats['slingshots']}",
             (180, 130, 255) if stats['slingshots'] > 0 else (110, 110, 110)),
            ("HULL LOST",         f"{stats['hull_lost']}",
             (220, 90, 90) if stats['hull_lost'] > 0 else (90, 200, 100)),
        ]

        y = 76
        for label, value, col in rows:
            lbl = font_md.render(label, True, (150, 160, 150))
            val = font_md.render(value, True, col)
            lbl.set_alpha(a)
            val.set_alpha(a)
            panel.blit(lbl, (32, y))
            panel.blit(val, (W - 32 - val.get_width(), y))
            y += 30

        # Footer
        pygame.draw.line(panel, (0, 130, 60, a), (24, H - 38), (W - 24, H - 38), 1)
        foot = font_sm.render("// JUMPING TO NEXT SECTOR //", True, (90, 200, 110))
        foot.set_alpha(a)
        panel.blit(foot, (W // 2 - foot.get_width() // 2, H - 28))

        self.screen.blit(panel, (cx - W // 2, cy - H // 2))

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
        t = pygame.time.get_ticks() / 1000.0
        font_sm  = pygame.font.SysFont("monospace", 13)
        font     = pygame.font.SysFont("monospace", 17)
        font_hd  = pygame.font.SysFont("monospace", 11)

        # Nova Soma header — cheerful, monstrous
        header = pygame.font.SysFont("monospace", 15, bold=True)
        tagline_surf = header.render(
            "NOVA SOMA SOLUTIONS  ·  Your Body, Our Investment  ·  Est. 2041",
            True, (80, 80, 80))
        self.screen.blit(tagline_surf,
                         (S.SCREEN_W // 2 - tagline_surf.get_width() // 2, 18))
        pygame.draw.line(self.screen, (50, 50, 50), (80, 36), (S.SCREEN_W - 80, 36), 1)

        lines = [
            ("PATIENT INTAKE SUMMARY", S.AMBER_TERM, font),
            (f"Unit ID: CLN-{self.meta.clone_count:04d}  ·  Template: BASELINE-7  ·  "
             f"Condition on Arrival: DECEASED", (140, 140, 140), font_sm),
            ("", None, font),
            ("ITEMISED CHARGES", (100, 100, 100), font_sm),
            (f"  Clone fluid & substrate . . . . -{S.CLONE_FLUID_FEE:>8,} cr",
             (180, 180, 180), font),
            (f"  Wreckage recovery & tow . . . . -{S.WRECKAGE_TOW_FEE:>8,} cr",
             (180, 180, 180), font),
            (f"  Body lease (standard term) . . . -{S.BASE_CLONE_DEBT:>8,} cr",
             (180, 180, 180), font),
            ("", None, font),
            (f"OUTSTANDING BALANCE:   {self.meta.debt:,} cr",
             S.AMBER_TERM, pygame.font.SysFont("monospace", 20, bold=True)),
            ("", None, font),
            ("This invoice is non-negotiable. Debt is hereditary and compound.",
             (70, 70, 70), font_sm),
            ("Nova Soma Solutions is not responsible for psychological distress",
             (70, 70, 70), font_sm),
            ("arising from repeated decanting. See Form NS-19b for opt-out options.",
             (70, 70, 70), font_sm),
            ("(Form NS-19b is not available in your jurisdiction.)",
             (55, 55, 55), font_sm),
            ("", None, font),
            ("[ PRESS ENTER TO CONTINUE ]", S.GREEN_TERM, font),
        ]

        y = 56
        for text, col, f in lines:
            if col is None:
                y += 10
                continue
            surf = f.render(text, True, col)
            self.screen.blit(surf, (S.SCREEN_W // 2 - surf.get_width() // 2, y))
            y += f.get_linesize() + 2

    def _render_main_menu(self):
        t  = pygame.time.get_ticks() / 1000.0
        cx = S.SCREEN_W // 2

        self.vec_renderer.draw_menu_background(t)

        # --- Cinematic letterbox bars ---
        bar_h = 56
        pygame.draw.rect(self.screen, (0, 0, 0),
                         pygame.Rect(0, 0, S.SCREEN_W, bar_h))
        pygame.draw.rect(self.screen, (0, 0, 0),
                         pygame.Rect(0, S.SCREEN_H - bar_h, S.SCREEN_W, bar_h))
        pygame.draw.line(self.screen, (120, 80, 0),
                         (0, bar_h), (S.SCREEN_W, bar_h), 1)
        pygame.draw.line(self.screen, (120, 80, 0),
                         (0, S.SCREEN_H - bar_h), (S.SCREEN_W, S.SCREEN_H - bar_h), 1)

        # --- Top bar text: classification stamp + chapter ---
        font_corp = pygame.font.SysFont("monospace", 12)
        stamp = font_corp.render(
            "CLASSIFIED // NOVA SOMA ENTERTAINMENT DIVISION // INTERNAL USE",
            True, (130, 95, 30))
        self.screen.blit(stamp, (16, 22))
        ver = font_corp.render("VER 0.5  //  SECTOR BUILD", True, (130, 95, 30))
        self.screen.blit(ver, (S.SCREEN_W - ver.get_width() - 16, 22))

        # --- Title with chromatic aberration ---
        font_title = pygame.font.SysFont("monospace", 96, bold=True)
        title_str  = "DEAD DRIFT"
        ty = 138

        # Glitch jitter — occasional one-frame offset
        glitch = (int(t * 6.3) % 47) == 0
        gx, gy = (random.randint(-3, 3), random.randint(-2, 2)) if glitch else (0, 0)

        # Chromatic split: red/cyan offsets behind the main amber title
        title_r = font_title.render(title_str, True, (200, 30, 30))
        title_c = font_title.render(title_str, True, (30, 220, 220))
        title_m = font_title.render(title_str, True, S.AMBER_TERM)
        offset  = 4 + int(2 * math.sin(t * 0.8))
        tx      = cx - title_m.get_width() // 2 + gx
        ty_g    = ty + gy
        self.screen.blit(title_r, (tx - offset, ty_g))
        self.screen.blit(title_c, (tx + offset, ty_g))
        self.screen.blit(title_m, (tx, ty_g))

        # Underline + outer brackets
        ul_y = ty + title_m.get_height() + 4
        ul_w = title_m.get_width() + 60
        ul_x = cx - ul_w // 2
        pygame.draw.line(self.screen, (160, 110, 0),
                         (ul_x, ul_y), (ul_x + ul_w, ul_y), 1)
        # Bracket caps
        cap = 14
        pygame.draw.line(self.screen, (200, 140, 0), (ul_x, ul_y - cap), (ul_x, ul_y + 2), 2)
        pygame.draw.line(self.screen, (200, 140, 0), (ul_x + ul_w, ul_y - cap), (ul_x + ul_w, ul_y + 2), 2)

        # --- Tagline ---
        font_sub = pygame.font.SysFont("monospace", 18)
        tagline_lines = [
            "A NEWTONIAN COURIER SIMULATION  //  FOR THE TERMINALLY INDEBTED",
            "5 sectors. crushing debt. one rusted ship. one bolted-on droid.",
        ]
        for i, line in enumerate(tagline_lines):
            col = (170, 120, 30) if i == 0 else (80, 80, 100)
            ts  = font_sub.render(line, True, col)
            self.screen.blit(ts, (cx - ts.get_width() // 2, ul_y + 16 + i * 24))

        # --- Live debt / clone counter panel (top-left) ---
        self._render_menu_debt_panel(t)

        # --- Run status / spec sheet panel (top-right) ---
        self._render_menu_spec_panel(t)

        # --- Wireframe rotating ship hull "studio" panel (mid-left) ---
        self._render_menu_ship_studio(t)

        # --- "Begin Run" pulsing prompt ---
        self._render_menu_begin_prompt(t)

        # --- Lore strap line (above bottom bar) ---
        font_lore = pygame.font.SysFont("monospace", 13)
        lore_lines = [
            "Union of Repo Men, Local 404. They will come for what you carry.",
            "Fly fast.  Drift hard.  Snap the tether.  Don't die again.",
        ]
        for i, line in enumerate(lore_lines):
            s = font_lore.render(line, True, (75, 75, 95))
            self.screen.blit(s, (cx - s.get_width() // 2,
                                  S.SCREEN_H - bar_h - 60 + i * 18))

        # --- Bottom bar: scrolling Nova Soma propaganda ticker ---
        self._render_menu_propaganda(t)

        # --- Bax mini portrait (bottom right) ---
        self._render_menu_bax_portrait(t)

        # --- Outer corner brackets + scanlines ---
        self._render_menu_corner_brackets()
        self._render_menu_scanlines()

    # ------------------------------------------------------------------
    def _render_menu_debt_panel(self, t: float):
        panel = pygame.Rect(20, 80, 280, 80)
        pygame.draw.rect(self.screen, (8, 4, 4), panel)
        pygame.draw.rect(self.screen, (160, 50, 50), panel, 1)
        # bracket caps
        for c, sx, sy in ((panel.topleft, 1, 1), (panel.topright, -1, 1),
                          (panel.bottomleft, 1, -1), (panel.bottomright, -1, -1)):
            pygame.draw.line(self.screen, (200, 70, 70), c, (c[0] + sx * 10, c[1]), 2)
            pygame.draw.line(self.screen, (200, 70, 70), c, (c[0], c[1] + sy * 10), 2)

        font_h = pygame.font.SysFont("monospace", 11, bold=True)
        font_d = pygame.font.SysFont("monospace", 22, bold=True)
        font_s = pygame.font.SysFont("monospace", 11)

        hdr = font_h.render("OUTSTANDING BALANCE", True, (200, 80, 80))
        self.screen.blit(hdr, (panel.left + 12, panel.top + 8))

        # Live drip — interest accruing per second
        interest = max(0.01, self.meta.debt * S.DEBT_INTEREST_RATE)
        displayed = int(self.meta.debt + t * interest)
        blink = int(t * 1.6) % 2 == 0
        debt_col = (220, 80, 80) if not blink else (255, 110, 110)
        ds = font_d.render(f"{displayed:>10,} cr", True, debt_col)
        self.screen.blit(ds, (panel.left + 12, panel.top + 26))

        ts = font_s.render(f"+{interest:.2f} cr/s  //  CLONE #{self.meta.clone_count}",
                           True, (180, 100, 100))
        self.screen.blit(ts, (panel.left + 12, panel.top + 56))

    # ------------------------------------------------------------------
    def _render_menu_spec_panel(self, t: float):
        panel = pygame.Rect(S.SCREEN_W - 300, 80, 280, 80)
        pygame.draw.rect(self.screen, (4, 6, 8), panel)
        pygame.draw.rect(self.screen, (60, 130, 180), panel, 1)
        for c, sx, sy in ((panel.topleft, 1, 1), (panel.topright, -1, 1),
                          (panel.bottomleft, 1, -1), (panel.bottomright, -1, -1)):
            pygame.draw.line(self.screen, (80, 160, 220), c, (c[0] + sx * 10, c[1]), 2)
            pygame.draw.line(self.screen, (80, 160, 220), c, (c[0], c[1] + sy * 10), 2)

        font_h = pygame.font.SysFont("monospace", 11, bold=True)
        font_v = pygame.font.SysFont("monospace", 12)

        hdr = font_h.render("PILOT MANIFEST", True, (120, 200, 255))
        self.screen.blit(hdr, (panel.left + 12, panel.top + 8))

        rows = [
            ("STATUS", "ALIVE-ISH" if self.meta.clone_count > 0 else "ROOKIE"),
            ("DEBT TIER", "CRUSHING" if self.meta.debt > 50000 else "MANAGEABLE"),
            ("LICENCE", "PROVISIONAL // L-404"),
        ]
        for i, (k, v) in enumerate(rows):
            ks = font_v.render(f"{k:<10}", True, (90, 140, 180))
            vs = font_v.render(v, True, (180, 220, 240))
            self.screen.blit(ks, (panel.left + 12, panel.top + 26 + i * 16))
            self.screen.blit(vs, (panel.left + 110, panel.top + 26 + i * 16))

    # ------------------------------------------------------------------
    def _render_menu_ship_studio(self, t: float):
        """Slowly rotating wireframe ship in the bottom-left — like a brochure shot."""
        panel = pygame.Rect(40, S.SCREEN_H // 2 + 30, 250, 180)
        pygame.draw.rect(self.screen, (4, 6, 10, 220), panel)
        pygame.draw.rect(self.screen, (60, 80, 110), panel, 1)
        for c, sx, sy in ((panel.topleft, 1, 1), (panel.topright, -1, 1),
                          (panel.bottomleft, 1, -1), (panel.bottomright, -1, -1)):
            pygame.draw.line(self.screen, (80, 110, 150), c, (c[0] + sx * 10, c[1]), 2)
            pygame.draw.line(self.screen, (80, 110, 150), c, (c[0], c[1] + sy * 10), 2)

        font = pygame.font.SysFont("monospace", 10, bold=True)
        hdr = font.render("HULL SCHEMATIC // RUSTBUCKET-α", True, (110, 150, 200))
        self.screen.blit(hdr, (panel.left + 8, panel.top + 6))

        cx_p = panel.centerx
        cy_p = panel.centery + 12
        ry   = t * 0.55
        scale = 1.6

        verts = [
            ( 40,  0,  0), (-28, -22, 0), (-28,  22, 0),
            (-20,  0,  10), (-20,  0, -10),
            (  5, -30, 0), (  5,  30, 0),
        ]
        edges = [(0,1),(0,2),(1,2),(0,5),(0,6),(1,5),(2,6),
                 (0,3),(1,3),(2,3),(0,4),(1,4),(2,4)]

        def proj(x, y, z):
            rx = x * math.cos(ry) - z * math.sin(ry)
            rz = x * math.sin(ry) + z * math.cos(ry)
            tilt = 0.45
            fy = y * math.cos(tilt) - rz * math.sin(tilt)
            return (int(cx_p + rx * scale), int(cy_p + fy * scale))

        pts = [proj(*v) for v in verts]
        for i, j in edges:
            pygame.draw.line(self.screen, (50, 80, 110), pts[i], pts[j], 2)
        for i, j in edges:
            pygame.draw.line(self.screen, (180, 220, 255), pts[i], pts[j], 1)
        for p in pts:
            pygame.draw.circle(self.screen, (200, 230, 255), p, 2)

        # Bottom label strip
        font_s = pygame.font.SysFont("monospace", 9)
        s1 = font_s.render(f"ROT  {ry:5.2f} rad", True, (90, 120, 160))
        s2 = font_s.render("MASS  1.0t  //  HULL 100", True, (90, 120, 160))
        self.screen.blit(s1, (panel.left + 8, panel.bottom - 24))
        self.screen.blit(s2, (panel.left + 8, panel.bottom - 12))

    # ------------------------------------------------------------------
    def _render_menu_begin_prompt(self, t: float):
        cx = S.SCREEN_W // 2
        py = S.SCREEN_H // 2 + 70

        pulse = 0.5 + 0.5 * math.sin(t * 3.0)
        font_enter = pygame.font.SysFont("monospace", 26, bold=True)
        text = "[  PRESS  ENTER  TO  BEGIN  RUN  ]"

        # Soft glow background
        glow_col = (int(60 + 60 * pulse), int(255 * pulse * 0.5), int(40 + 40 * pulse))
        gs = font_enter.render(text, True, glow_col)
        self.screen.blit(gs, (cx - gs.get_width() // 2 + 2, py + 2))

        main_col = (int(180 + 75 * pulse), int(180 + 75 * pulse), int(190 + 65 * pulse))
        ms = font_enter.render(text, True, main_col)
        self.screen.blit(ms, (cx - ms.get_width() // 2, py))

        # Subtitle below
        if self._run_just_completed:
            font_c = pygame.font.SysFont("monospace", 14, bold=True)
            cs = font_c.render("// RUN COMPLETE //  DEBT REDUCED  //",
                               True, S.GREEN_TERM)
            self.screen.blit(cs, (cx - cs.get_width() // 2, py - 38))

    # ------------------------------------------------------------------
    def _render_menu_propaganda(self, t: float):
        bar_h = 56
        bar_y = S.SCREEN_H - bar_h
        # Inside the letterbox bar — scrolling ticker
        font = pygame.font.SysFont("monospace", 14, bold=True)
        text = (
            "  >>  NOVA SOMA :: DEBT IS OPPORTUNITY  "
            "  >>  CLONE FASTER. EARN FASTER. THRIVE.  "
            "  >>  LOCAL 404 :: A PROUD PARTNER IN ENFORCEMENT  "
            "  >>  REMEMBER: YOUR BODY IS LEASED  "
            "  >>  GENUINE NOVA SOMA® PARTS IN EVERY CLONE  "
            "  >>  NEGATIVE-INTEREST DEBT CONSOLIDATION (T&Cs APPLY)  "
            "  >>  IF YOU CAN READ THIS YOU OWE NOVA SOMA THIRTY-TWO CREDITS  "
        )
        full = text + text
        surf = font.render(full, True, (200, 140, 30))
        speed = 70
        ox = int((t * speed) % (surf.get_width() // 2))
        self.screen.blit(surf, (-ox, bar_y + 16))
        self.screen.blit(surf, (-ox + surf.get_width() // 2, bar_y + 16))

    # ------------------------------------------------------------------
    def _render_menu_corner_brackets(self):
        col = (110, 110, 130)
        L = 26
        for cx, cy, sx, sy in (
            (6, 6, 1, 1), (S.SCREEN_W - 7, 6, -1, 1),
            (6, S.SCREEN_H - 7, 1, -1), (S.SCREEN_W - 7, S.SCREEN_H - 7, -1, -1)):
            pygame.draw.line(self.screen, col, (cx, cy), (cx + sx * L, cy), 2)
            pygame.draw.line(self.screen, col, (cx, cy), (cx, cy + sy * L), 2)

    # ------------------------------------------------------------------
    def _render_menu_scanlines(self):
        sl = pygame.Surface((S.SCREEN_W, S.SCREEN_H), pygame.SRCALPHA)
        for y in range(0, S.SCREEN_H, 4):
            pygame.draw.line(sl, (0, 0, 0, 32), (0, y), (S.SCREEN_W, y), 1)
        self.screen.blit(sl, (0, 0))

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
