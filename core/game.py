import sys
import math
import random
import pygame

from config import settings as S
from core.state_manager import StateManager, GameState
from renderer.visual_fx import VisualFX
from core.transitions import TransitionManager
from core.text import install_font_patch
from core.event_bus import bus, EVT_SHIP_DESTROYED, EVT_RUN_END, EVT_TORCH_ACTIVE, EVT_DEBT_DING, EVT_BAX_SPEAK
from roguelite.meta_progression import MetaProgression
from roguelite.save_manager import SaveManager
from roguelite.run_manager import RunManager
from ship.ship import PlayerShip
from bax.bax import Bax
from renderer.vector_renderer import VectorRenderer
from renderer.hud_renderer import HUDRenderer
from renderer.terminal_renderer import TerminalRenderer
from renderer.cockpit_renderer import CockpitRenderer
from audio.audio_manager import (
    AudioManager,
    SCENE_MENU, SCENE_FLIGHT, SCENE_TERMINAL, SCENE_DELIVERY,
    SCENE_SHOP, SCENE_INTERSTITIAL, SCENE_DECANTING, SCENE_LOADOUT,
    SCENE_RADIO,
)
from delivery.delivery_sequence import DeliverySequence
from roguelite.shop import ShopScreen


def _format_slingshot_flash_value(stats: dict) -> str:
    slingshots = int(stats.get("slingshots", 0))
    sling_credits = int(stats.get("slingshot_credits", 0))
    sling_each = int(stats.get(
        "slingshot_credit_each",
        sling_credits // slingshots if slingshots else 0,
    ))

    if slingshots > 0 and sling_credits > 0:
        return f"{slingshots} x {sling_each:,} = +{sling_credits:,} cr"
    return f"{slingshots}"


class Game:
    _PAUSEABLE = frozenset({
        GameState.FLIGHT,
        GameState.TERMINAL,
        GameState.SHOP,
        GameState.LOADOUT_DRAFT,
        GameState.INTERSTITIAL,
    })

    def __init__(self):
        pygame.init()
        # Route every pygame.font.SysFont("monospace", ...) call through
        # the bundled DejaVu Sans Mono with a +2pt size bump.
        install_font_patch()
        self.screen  = pygame.display.set_mode((S.SCREEN_W, S.SCREEN_H))
        pygame.display.set_caption(S.TITLE)
        self.clock   = pygame.time.Clock()
        self.running = True

        self.states  = StateManager()
        self.save_mgr = SaveManager()
        self.ship    = PlayerShip()
        self._menu_mode         = "main"   # main | pick_new | pick_load | confirm_overwrite
        self._menu_cursor       = 0
        self._slot_cursor       = 0
        self._pending_slot: int | None = None
        self._pause_menu_cursor = 0
        self._state_before_pause: GameState | None = None
        self.meta    = MetaProgression(save_path=self.save_mgr.active_save_path())
        self.meta._after_save = lambda: self.save_mgr.sync_active(self.meta)
        self.run_mgr = RunManager(self.meta)
        self.bax     = Bax(self.ship, self.meta)
        self.run_mgr._vault = self.bax.vault
        # Epic 11.3 — give Bax a live read on bax_context so handlers can reference past runs.
        if hasattr(self.bax, "attach_run_context"):
            self.bax.attach_run_context(self.run_mgr.bax_context)

        self.vec_renderer     = VectorRenderer(self.screen)
        self._menu_vfx        = VisualFX()
        self._checkpoint_cd   = 25.0   # autosave interval during flight
        self.hud_renderer     = HUDRenderer(self.screen)
        self.term_renderer    = TerminalRenderer(self.screen)
        # Pass live references so the cockpit info panel always reads current state
        self.cockpit_renderer = CockpitRenderer(
            self.screen, self.ship, self.run_mgr, self.meta
        )
        self.audio = AudioManager()

        # CRT power-down scene transitions
        self.transition = TransitionManager()

        self._dt                  = 0.016
        self._run_just_completed  = False
        self._torch_warn_t        = 0.0   # seconds remaining until next module loss
        self._last_debt_milestone = 0     # last 1000cr milestone we dinged
        self._delivery: DeliverySequence | None = None
        self._shop: ShopScreen | None = None
        self._delivery_pending    = False  # waiting for Bax delivery line to finish
        self._delivery_delay_t    = 0.0
        self._delivery_chapter    = 1      # chapter being delivered (set at run-end)

        # Interstitial state (between successful delivery and next chapter loadout)
        self._interstitial_t          = 0.0
        self._interstitial_completed  = 1
        self._interstitial_next       = 2
        self._interstitial_campaign_end = False

        # Epic 18 — difficulty selector state
        self._diff_cursor: int = 1   # 0=casual  1=standard  2=irons
        _diff_names = ("casual", "standard", "irons")
        saved = getattr(self.meta, "difficulty", "standard")
        self._diff_cursor = _diff_names.index(saved) if saved in _diff_names else 1

        # Epic 16 — floating debt change label (shown 2s beside the debt counter)
        self._debt_float_label: str = ""
        self._debt_float_t:     float = 0.0
        from core.event_bus import EVT_DEBT_UPDATE
        bus.subscribe(EVT_DEBT_UPDATE, self._on_debt_update_hud)

        # Decanting — cached Bax wake-up line (picked once on death, not per frame)
        self._decant_bax_line: str = ""

        # Terminal win hold — show outcome for 2s before returning to flight
        self._terminal_win_hold_t: float = 0.0
        self._terminal_win_str: str = ""

        # Death hold — brief black screen before DECANTING to let the explosion register
        self._death_hold_t: float = 0.0   # >0 = holding on death flash before transition

        # Bax hum trigger (§7.4) — once per run on first delivery success
        self._hum_played_this_run: bool = False

        # Jukebox menu state — only enterable after a campaign clear
        self._jukebox_cursor: int = 0

        self._wire_events()

    def _bind_meta_from_active_slot(self) -> None:
        """Reload campaign progress from the active save slot."""
        path = self.save_mgr.active_save_path()
        self.meta = MetaProgression(save_path=path)
        self.meta._after_save = lambda: self.save_mgr.sync_active(self.meta)
        self.run_mgr.meta = self.meta
        self.bax._meta = self.meta
        self.run_mgr._vault = self.bax.vault
        if hasattr(self.bax, "attach_run_context"):
            self.bax.attach_run_context(self.run_mgr.bax_context)
        self.cockpit_renderer._meta = self.meta

    def _effective_state(self) -> GameState:
        if self.states.state == GameState.PAUSED and self._state_before_pause is not None:
            return self._state_before_pause
        return self.states.state

    def _wire_events(self):
        bus.subscribe(EVT_SHIP_DESTROYED, self._on_ship_destroyed)
        bus.subscribe(EVT_RUN_END,        self._on_run_end)
        bus.subscribe(EVT_TORCH_ACTIVE,   self._on_torch_active)
        from core.event_bus import EVT_DELIVERY_DONE, EVT_RUN_START
        bus.subscribe(EVT_DELIVERY_DONE,  self._on_delivery_done)
        bus.subscribe(EVT_RUN_START,      self._on_bax_hum_run_start)

    # ------------------------------------------------------------------
    # State → musical scene mapping. Drives AudioManager.set_scene().
    _STATE_TO_SCENE = {
        GameState.MAIN_MENU:          SCENE_MENU,
        GameState.LOADOUT_DRAFT:      SCENE_LOADOUT,
        GameState.DIFFICULTY_SELECT:  SCENE_LOADOUT,
        GameState.FLIGHT:             SCENE_FLIGHT,
        GameState.TERMINAL:           SCENE_TERMINAL,
        GameState.DELIVERY:           SCENE_DELIVERY,
        GameState.SHOP:               SCENE_SHOP,
        GameState.INTERSTITIAL:       SCENE_INTERSTITIAL,
        GameState.DECANTING:          SCENE_DECANTING,
        GameState.SECTOR_JUMP:        SCENE_FLIGHT,
        GameState.GAME_OVER:          SCENE_MENU,
    }

    def _goto(self, new_state: GameState):
        """Animated state change: capture the current frame, start the
        CRT power-down transition, then swap state."""
        if new_state == GameState.PAUSED:
            self.states.transition(GameState.PAUSED)
            return
        try:
            snapshot = self.screen.copy()
        except (pygame.error, AttributeError):
            snapshot = pygame.Surface((S.SCREEN_W, S.SCREEN_H))
        self.transition.start(snapshot)
        self.states.transition(new_state)
        if new_state == GameState.MAIN_MENU:
            self._bind_meta_from_active_slot()
        scene = self._STATE_TO_SCENE.get(new_state)
        if scene is not None and self.audio is not None:
            # Pass current chapter for chapter-keyed scenes (flight + delivery)
            if scene in (SCENE_FLIGHT, SCENE_DELIVERY) and self.run_mgr is not None:
                try:
                    chap = self.run_mgr._current_chapter()
                    self.audio.set_scene(scene, chapter=chap)
                    return
                except Exception:
                    pass
            self.audio.set_scene(scene)

    def _on_torch_active(self, countdown=5.0, **_):
        self._torch_warn_t = countdown

    def _on_ship_destroyed(self, **_):
        sector_idx = getattr(self.run_mgr, '_sector_index', 0) if self.run_mgr else 0
        # Epic 12.1 — NOVICE_PASS: first death of run skips the debt penalty
        novice_skip = (self.run_mgr is not None and
                       getattr(self.run_mgr, "mutators", None) is not None and
                       self.run_mgr.mutators.is_active("novice_pass") and
                       not getattr(self.run_mgr, "_novice_pass_consumed", False))
        if novice_skip:
            self.run_mgr._novice_pass_consumed = True
            # Skip debt penalty but still increment clone_count for the death
            self.meta._data["clone_count"] = self.meta.clone_count + 1
            self.meta.save()
            bus.emit(EVT_BAX_SPEAK, line="NOVICE PASS used — this clone's on the house. "
                     "Don't get used to it.")
        else:
            self.meta.apply_death_penalty(sector_index=sector_idx)
        # Epic 11.3 — track died-this-sector for Bax past-run references
        if self.run_mgr is not None and hasattr(self.run_mgr, 'bax_context'):
            tds = self.run_mgr.bax_context.setdefault("times_died_this_sector", {})
            tds[sector_idx] = tds.get(sector_idx, 0) + 1
            # Update last_sector_reached watermark
            cur_last = self.run_mgr.bax_context.get("last_sector_reached", 0)
            if sector_idx > cur_last:
                self.run_mgr.bax_context["last_sector_reached"] = sector_idx
        self._run_just_completed = False
        # Pick the Bax decanting line once — cached so _render_decanting doesn't
        # re-roll it every frame, which makes the text flash/go crazy.
        src  = getattr(self.ship, "last_damage_source", "unknown")
        pool = self._DECANT_BAX_BY_SOURCE.get(src, self._DECANT_BAX)
        self._decant_bax_line = random.choice(pool).format(n=self.meta.clone_count)
        # Brief death hold (0.9s) before transitioning — gives the explosion a moment
        self._death_hold_t = 0.9

    def _on_run_end(self, success, **_):
        if success:
            self.save_mgr.delete_run_checkpoint()
            self._delivery_chapter = self.run_mgr._current_chapter()
            self.meta.clear_debt_chunk()
            bus.emit(EVT_BAX_SPEAK, priority=True, line=random.choice([
                "Five sectors. FIVE. And we're still breathin'. "
                "Drop-off confirmed. Station on approach. Don't crash now.",
                "That's all five sectors cleared. Cargo intact, pilot in one piece — "
                "mostly. Delivery window's open. Let's not blow it.",
                "Run complete. COMPLETE. I cannot believe we pulled that off. "
                "Drop-off point's on screen. Easy does it from 'ere.",
                "All five sectors. We did the gauntlet. "
                "Station's in range. Land this thing like we know what we're doin'.",
            ]))
            self._delivery_pending = True
            self._delivery_delay_t = 2.4
        else:
            self.meta.save()
            self._run_just_completed = False
            self._goto(GameState.MAIN_MENU)

    # ------------------------------------------------------------------
    # Bax hum (§7.4) — one per run on first delivery success.
    def _on_bax_hum_run_start(self, **_):
        self._hum_played_this_run = False

    def _on_delivery_done(self, **_):
        if self._hum_played_this_run:
            return
        self._hum_played_this_run = True
        if self.audio is None:
            return
        from audio.bax_hum import CAMPAIGN_CLEAR_HUM_IDX, hum_count
        heard = set(self.meta.bax_hums_heard)
        # Hum 7 is reserved for Chapter 4 deliveries.
        if self._delivery_chapter == 4:
            idx = CAMPAIGN_CLEAR_HUM_IDX
        else:
            # Pick the first unheard non-7 hum; fall back to a random replay.
            unheard = [i for i in range(hum_count())
                       if i not in heard and i != CAMPAIGN_CLEAR_HUM_IDX]
            if unheard:
                idx = unheard[0]
            else:
                non_seven = [i for i in range(hum_count()) if i != CAMPAIGN_CLEAR_HUM_IDX]
                idx = random.choice(non_seven)
        self.meta.mark_hum_heard(idx)
        self.audio.play_bax_hum(idx)

    # ------------------------------------------------------------------
    def run(self, start_state: GameState = None, start_sector: int = 0):
        """
        Entry point.  Pass start_state to boot directly into any screen
        (used by test_stage.py).
        """
        if start_state is None or start_state == GameState.MAIN_MENU:
            self._goto(GameState.MAIN_MENU)
        elif start_state == GameState.LOADOUT_DRAFT:
            self.run_mgr.start_run(self.ship)
            self._goto(GameState.LOADOUT_DRAFT)
        elif start_state == GameState.FLIGHT:
            self._dev_start_flight(start_sector)
        elif start_state == GameState.DECANTING:
            self._goto(GameState.DECANTING)
        else:
            self._goto(start_state)

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
        if self.audio is not None:
            self.audio.set_scene(SCENE_FLIGHT)

    # ------------------------------------------------------------------
    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                self._route_keydown(event)
            elif event.type == pygame.KEYUP:
                if self.states.state == GameState.DELIVERY and self._delivery:
                    self._delivery.handle_keyup(event)

    def _pause_game(self) -> None:
        if self.states.state in self._PAUSEABLE:
            self._state_before_pause = self.states.state
            self._pause_menu_cursor = 0
            self.states.transition(GameState.PAUSED)

    def _resume_game(self) -> None:
        if self.states.state != GameState.PAUSED or self._state_before_pause is None:
            return
        self.states._state = self._state_before_pause
        self._state_before_pause = None

    def _pause_to_main_menu(self, *, save: bool) -> None:
        if save:
            self.meta.save()
            self._save_run_checkpoint()
        self._state_before_pause = None
        self._menu_mode = "main"
        self._goto(GameState.MAIN_MENU)

    def _main_menu_rows(self) -> list[tuple[str, bool, str]]:
        active = self.save_mgr.slot_info(self.save_mgr.active_slot_id)
        has_ckpt = self.save_mgr.has_run_checkpoint()
        if has_ckpt:
            cont_label = "RESUME RUN"
            cont_ok = True
        else:
            cont_label = "CONTINUE"
            cont_ok = active.exists
        rows: list[tuple[str, bool, str]] = [
            (cont_label, cont_ok, "continue"),
        ]
        if has_ckpt:
            rows.append(("DELETE RUN", True, "delete_run"))
        rows.extend([
            ("NEW GAME", True, "new"),
            ("LOAD GAME", True, "load"),
        ])
        # Jukebox unlocks after the player has completed all 4 chapters at least once
        if self.meta.campaign_cleared_at_least_once:
            rows.append(("BAX'S TAPES", True, "jukebox"))
        rows.append(("QUIT", True, "quit"))
        return rows

    def _menu_activate(self) -> None:
        if self._menu_mode == "confirm_delete_run":
            self.save_mgr.delete_run_checkpoint()
            self._menu_mode = "main"
            return

        if self._menu_mode == "confirm_overwrite":
            sid = self._pending_slot
            if sid is None:
                self._menu_mode = "pick_new"
                return
            self.save_mgr.create_fresh_save(sid)
            self._bind_meta_from_active_slot()
            self._pending_slot = None
            self._menu_mode = "main"
            self.save_mgr.delete_run_checkpoint()
            self._begin_run_from_menu()
            return

        if self._menu_mode in ("pick_new", "pick_load"):
            sid = self._slot_cursor + 1
            if self._menu_mode == "pick_new":
                info = self.save_mgr.slot_info(sid)
                if info.exists:
                    self._pending_slot = sid
                    self._menu_mode = "confirm_overwrite"
                    return
                self.save_mgr.create_fresh_save(sid)
                self._bind_meta_from_active_slot()
                self._menu_mode = "main"
                self.save_mgr.delete_run_checkpoint()
                self._begin_run_from_menu()
            else:
                self.save_mgr.set_active(sid)
                self._bind_meta_from_active_slot()
                self._menu_mode = "main"
            return

        rows = self._main_menu_rows()
        _label, enabled, action = rows[self._menu_cursor]
        if not enabled:
            return
        if action == "continue":
            self._continue_from_menu()
        elif action == "delete_run":
            self._menu_mode = "confirm_delete_run"
        elif action == "new":
            self._menu_mode = "pick_new"
            self._slot_cursor = self.save_mgr.active_slot_id - 1
        elif action == "load":
            self._menu_mode = "pick_load"
            self._slot_cursor = 0
        elif action == "jukebox":
            self._menu_mode = "jukebox"
            self._jukebox_cursor = 0
        elif action == "quit":
            self.running = False

    def _save_run_checkpoint(self) -> None:
        if self.run_mgr._sector is None and not self.run_mgr.draft.is_confirmed():
            return
        try:
            self.save_mgr.save_run_checkpoint(self)
        except OSError:
            pass

    def _continue_from_menu(self) -> None:
        self._bind_meta_from_active_slot()
        self._run_just_completed = False
        if self.save_mgr.has_run_checkpoint():
            if self.save_mgr.load_run_checkpoint(self):
                from roguelite.run_checkpoint import load_checkpoint_file
                data = load_checkpoint_file(self.save_mgr.run_checkpoint_path())
                gs_name = (data or {}).get("game_state", "FLIGHT")
                try:
                    target = GameState[gs_name]
                except KeyError:
                    target = GameState.FLIGHT
                if target == GameState.SHOP:
                    self._shop = ShopScreen(self.run_mgr, self.ship)
                self._goto(target)
                return
        if self.save_mgr.slot_info(self.save_mgr.active_slot_id).exists:
            self._begin_run_from_menu()
        else:
            self._menu_mode = "pick_new"
            self._slot_cursor = 0

    def _begin_run_from_menu(self) -> None:
        self._run_just_completed = False
        self.save_mgr.delete_run_checkpoint()
        self.run_mgr.start_run(self.ship)
        self._goto(GameState.LOADOUT_DRAFT)

    def _handle_main_menu_key(self, event: pygame.event.Event) -> None:
        if self._menu_mode == "confirm_delete_run":
            if event.key in (pygame.K_y, pygame.K_RETURN):
                self._menu_activate()
            elif event.key in (pygame.K_n, pygame.K_ESCAPE):
                self._menu_mode = "main"
            return

        if self._menu_mode == "confirm_overwrite":
            if event.key in (pygame.K_y, pygame.K_RETURN):
                self._menu_activate()
            elif event.key in (pygame.K_n, pygame.K_ESCAPE):
                self._menu_mode = "pick_new"
                self._pending_slot = None
            return

        if self._menu_mode in ("pick_new", "pick_load"):
            if event.key == pygame.K_UP:
                self._slot_cursor = (self._slot_cursor - 1) % S.MAX_SAVE_SLOTS
            elif event.key == pygame.K_DOWN:
                self._slot_cursor = (self._slot_cursor + 1) % S.MAX_SAVE_SLOTS
            elif event.key == pygame.K_RETURN:
                self._menu_activate()
            elif event.key == pygame.K_ESCAPE:
                self._menu_mode = "main"
                self._pending_slot = None
            return

        if self._menu_mode == "jukebox":
            from audio.bax_hum import hum_count
            if event.key in (pygame.K_UP, pygame.K_w):
                self._jukebox_cursor = (self._jukebox_cursor - 1) % hum_count()
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self._jukebox_cursor = (self._jukebox_cursor + 1) % hum_count()
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                heard = set(self.meta.bax_hums_heard)
                if self._jukebox_cursor in heard and self.audio:
                    self.audio.play_bax_hum(self._jukebox_cursor)
            elif event.key == pygame.K_ESCAPE:
                self._menu_mode = "main"
            return

        rows = self._main_menu_rows()
        if event.key == pygame.K_UP:
            self._menu_cursor = (self._menu_cursor - 1) % len(rows)
        elif event.key == pygame.K_DOWN:
            self._menu_cursor = (self._menu_cursor + 1) % len(rows)
        elif event.key == pygame.K_RETURN:
            self._menu_activate()
        elif event.key == pygame.K_ESCAPE:
            self.running = False

    def _handle_pause_menu_key(self, event: pygame.event.Event) -> None:
        items = ("RESUME", "SAVE & RETURN TO MENU")
        if event.key in (pygame.K_1, pygame.K_ESCAPE) and self._pause_menu_cursor == 0:
            self._resume_game()
            return
        if event.key == pygame.K_UP:
            self._pause_menu_cursor = (self._pause_menu_cursor - 1) % len(items)
        elif event.key == pygame.K_DOWN:
            self._pause_menu_cursor = (self._pause_menu_cursor + 1) % len(items)
        elif event.key == pygame.K_RETURN:
            if self._pause_menu_cursor == 0:
                self._resume_game()
            else:
                self._pause_to_main_menu(save=True)

    def _route_keydown(self, event: pygame.event.Event):
        state = self.states.state

        if state == GameState.PAUSED:
            self._handle_pause_menu_key(event)
            return

        if state == GameState.SHOP and event.key == pygame.K_ESCAPE:
            if self._shop is not None:
                self._shop.handle_key(event)
            return

        if state in self._PAUSEABLE:
            if event.key == pygame.K_1:
                self._pause_game()
                return
            if event.key == pygame.K_ESCAPE and state != GameState.TERMINAL:
                self._pause_game()
                return

        if state == GameState.FLIGHT:
            # R = cockpit radio (cycles stations); also acts as toggle to/from SCENE_FLIGHT
            if event.key == pygame.K_r and self.audio is not None:
                if self.audio._scene == SCENE_RADIO:
                    self.audio.cycle_radio_station()
                else:
                    self.audio.cycle_radio_station()
                    self.audio._play_current_radio_station()
                return
            self.run_mgr.handle_key(event)
        elif state == GameState.TERMINAL:
            if self.run_mgr.active_terminal is not None:
                self.run_mgr.active_terminal.handle_key(event)
        elif state == GameState.LOADOUT_DRAFT:
            self.run_mgr.draft.handle_key(event)
        elif state == GameState.DIFFICULTY_SELECT:
            self._handle_difficulty_key(event)
        elif state == GameState.DELIVERY:
            if self._delivery is not None:
                self._delivery.handle_key(event)
        elif state == GameState.SHOP:
            if self._shop is not None:
                self._shop.handle_key(event)
        elif state == GameState.MAIN_MENU:
            self._handle_main_menu_key(event)
        elif state == GameState.DECANTING:
            if event.key == pygame.K_RETURN:
                self.meta.save()
                self._menu_mode = "main"
                self._goto(GameState.MAIN_MENU)
        elif state == GameState.INTERSTITIAL:
            if event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                self._exit_interstitial()

    # ------------------------------------------------------------------
    def _update(self, dt: float):
        state = self.states.state

        if state == GameState.PAUSED:
            if self.audio is not None:
                self.audio.update(
                    0.0, dt,
                    hull_pct=self.ship.hull_pct if self.ship else 1.0,
                )
            return

        # Death hold — freeze in FLIGHT for a moment, then transition to DECANTING
        if self._death_hold_t > 0:
            self._death_hold_t -= dt
            if self._death_hold_t <= 0:
                self._goto(GameState.DECANTING)
            return   # skip all other update logic during hold

        if state == GameState.FLIGHT:
            if self._delivery_pending:
                # Hold in FLIGHT so Bax's "we did it" line plays in the cockpit strip
                self._delivery_delay_t -= dt
                self.bax.update(dt)
                self.cockpit_renderer.update(dt)
                if self._delivery_delay_t <= 0:
                    self._delivery_pending = False
                    self._delivery = DeliverySequence(self.meta, chapter=self._delivery_chapter)
                    self._goto(GameState.DELIVERY)
            else:
                self._torch_warn_t = max(0.0, self._torch_warn_t - dt)
                self.run_mgr.update(dt)
                self.ship.update(dt)
                self.bax.update(dt)
                self.cockpit_renderer.update(dt)
                self.audio.update(
                    self.ship.body.speed(), dt,
                    hull_pct=self.ship.hull_pct,
                    barge_threat=self.run_mgr.barge_threat_level(),
                    sector_idx=getattr(self.run_mgr, '_sector_index', 0),
                    cargo_alarm=self.run_mgr.cargo_alarm_level(),
                )
                # Shop stop between sectors
                self._checkpoint_cd -= dt
                if self._checkpoint_cd <= 0:
                    self._checkpoint_cd = 25.0
                    self._save_run_checkpoint()
                if self.run_mgr._shop_pending:
                    self._shop = ShopScreen(self.run_mgr, self.ship)
                    self._save_run_checkpoint()
                    self._goto(GameState.SHOP)
                # Terminal opened by jump key — transition immediately
                elif self.run_mgr.active_terminal is not None:
                    self._goto(GameState.TERMINAL)

        elif state == GameState.SHOP:
            if self._shop is not None:
                self._shop.update(dt)
                if self._shop.is_done:
                    self._shop = None
                    self.run_mgr._load_next_sector()
                    self._save_run_checkpoint()
                    self._goto(GameState.FLIGHT)

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
                if terminal.is_done and self._terminal_win_hold_t <= 0:
                    outcome = terminal.outcome
                    if not self._start_terminal_outcome_hold(outcome):
                        self.run_mgr.on_terminal_complete(terminal.outcome)
                        if self.states.state == GameState.TERMINAL:
                            self._goto(GameState.FLIGHT)
            # Win-hold countdown — complete the terminal and leave after timer
            if self._terminal_win_hold_t > 0:
                self._terminal_win_hold_t -= dt
                if self._terminal_win_hold_t <= 0:
                    if self.run_mgr.active_terminal is not None:
                        self.run_mgr.on_terminal_complete(
                            self.run_mgr.active_terminal.outcome)
                    if self.states.state == GameState.TERMINAL:
                        if self._delivery_pending:
                            # Run just ended via terminal win — hold here for Bax line,
                            # then go directly to DELIVERY without cutting to FLIGHT first.
                            pass
                        else:
                            self._goto(GameState.FLIGHT)
            # If delivery is pending while still in TERMINAL, run the countdown here
            # so we never show the FLIGHT/space view after a terminal win
            if self._delivery_pending and state == GameState.TERMINAL:
                self._delivery_delay_t -= dt
                self.bax.update(dt)
                self.cockpit_renderer.update(dt)
                if self._delivery_delay_t <= 0:
                    self._delivery_pending = False
                    self._delivery = DeliverySequence(self.meta,
                                                      chapter=self._delivery_chapter)
                    self._goto(GameState.DELIVERY)

        elif state == GameState.LOADOUT_DRAFT:
            if self.run_mgr.draft.is_confirmed():
                self.run_mgr.apply_draft(self.ship)
                self._checkpoint_cd = 25.0
                self._save_run_checkpoint()
                # Epic 18 — show difficulty picker before launching into FLIGHT
                self._goto(GameState.DIFFICULTY_SELECT)

        elif state == GameState.DIFFICULTY_SELECT:
            pass   # driven entirely by key events in handle_event()

        elif state == GameState.DELIVERY:
            if self._delivery is not None:
                self._delivery.update(self._dt)
                if self._delivery.is_done:
                    self._delivery = None
                    self._enter_interstitial()

        elif state == GameState.INTERSTITIAL:
            self._interstitial_t = max(0.0, self._interstitial_t - dt)
            self.cockpit_renderer.update(dt)
            if self._interstitial_t <= 0:
                self._exit_interstitial()

        elif state == GameState.DECANTING:
            pass

        # Always tick audio (xfade, band volumes, Bax voice) — not just in FLIGHT.
        # In non-flight states use speed=0 so engine hum is silent.
        if state != GameState.FLIGHT and self.audio is not None:
            ship_speed = getattr(self.ship.body, 'speed', lambda: 0.0)() \
                         if self.ship is not None else 0.0
            self.audio.update(
                ship_speed, dt,
                hull_pct=self.ship.hull_pct if self.ship else 1.0,
            )

    # ── Epic 16 — debt float label ─────────────────────────────────────────
    def _on_debt_update_hud(self, delta=0, total=0, **_):
        if delta == 0:
            return
        sign = "+" if delta > 0 else "−"
        self._debt_float_label = f"{sign}{abs(int(delta)):,} cr"
        self._debt_float_t = 2.0

    # ── Epic 18 — difficulty selector ──────────────────────────────────────
    _DIFF_OPTS = [
        ("CASUAL",   "hull +30 · debt rate ×0.7 · barges: patient",  "casual"),
        ("STANDARD", "baseline risk — no modifiers",                   "standard"),
        ("IRONS",    "hull −20 · debt rate ×1.5 · barges: relentless", "irons"),
    ]

    def _handle_difficulty_key(self, event: "pygame.event.Event") -> None:
        import pygame as _pg
        if event.key in (_pg.K_UP, _pg.K_w):
            self._diff_cursor = (self._diff_cursor - 1) % 3
        elif event.key in (_pg.K_DOWN, _pg.K_s):
            self._diff_cursor = (self._diff_cursor + 1) % 3
        elif event.key in (_pg.K_RETURN, _pg.K_SPACE):
            _, _, key = self._DIFF_OPTS[self._diff_cursor]
            self.meta.set_difficulty(key)
            # Apply hull delta immediately on the ship
            delta = self.meta.hull_start_delta()
            if delta != 0 and self.ship is not None:
                import config.settings as _S
                self.ship.hull = max(1.0, min(
                    _S.HULL_MAX + delta,
                    self.ship.hull + delta,
                ))
            self._goto(GameState.FLIGHT)

    def _render_difficulty_select(self) -> None:
        cx = S.SCREEN_W // 2
        cy = S.SCREEN_H // 2
        t  = pygame.time.get_ticks() / 1000.0

        # Dim the loadout background that's still in the frame buffer
        ov = pygame.Surface((S.SCREEN_W, S.SCREEN_H), pygame.SRCALPHA)
        ov.fill((0, 0, 5, 210))
        self.screen.blit(ov, (0, 0))

        W, H = 560, 240
        x, y = cx - W // 2, cy - H // 2 - 20
        bg = pygame.Surface((W, H), pygame.SRCALPHA)
        bg.fill((8, 8, 18, 240))
        self.screen.blit(bg, (x, y))
        pygame.draw.rect(self.screen, (160, 110, 30), (x, y, W, H), 2)

        fhd  = pygame.font.SysFont("monospace", 17, bold=True)
        frow = pygame.font.SysFont("monospace", 15, bold=True)
        fsub = pygame.font.SysFont("monospace", 11)

        title = fhd.render("NOVA SOMA COURIER RISK ASSESSMENT", True, (220, 185, 80))
        self.screen.blit(title, (cx - title.get_width() // 2, y + 14))
        pygame.draw.line(self.screen, (100, 72, 20),
                         (x + 14, y + 36), (x + W - 14, y + 36), 1)

        pulse = 0.5 + 0.5 * math.sin(t * 3.0)
        for i, (label, desc, _key) in enumerate(self._DIFF_OPTS):
            ry = y + 52 + i * 58
            sel = i == self._diff_cursor
            row_col = (int(200 + 55 * pulse), int(220 + 35 * pulse), 110) if sel \
                      else (100, 100, 120)
            prefix = ">  " if sel else "   "
            ls = frow.render(f"{prefix}{label}", True, row_col)
            self.screen.blit(ls, (x + 24, ry))
            ds = fsub.render(f"      {desc}", True,
                             (160, 145, 90) if sel else (70, 70, 85))
            self.screen.blit(ds, (x + 24, ry + 20))
            if sel:
                pygame.draw.line(self.screen, (120, 85, 20),
                                 (x + 14, ry + 40), (x + W - 14, ry + 40), 1)

        hint = fsub.render("↑↓ / W·S  select      ENTER / SPACE  confirm", True, (80, 80, 100))
        self.screen.blit(hint, (cx - hint.get_width() // 2, y + H - 22))

    def _start_terminal_outcome_hold(self, outcome: str) -> bool:
        """Start a visible terminal outcome beat. Returns False for instant closes."""
        from terminal.npcs.base_npc import NPCOutcome

        if outcome in (NPCOutcome.RELEASE, "release"):
            self._terminal_win_hold_t = 5.0
            self._terminal_win_str = "NEGOTIATION SUCCESS"
            return True
        if outcome in (NPCOutcome.EXPLOIT, "exploit"):
            self._terminal_win_hold_t = 5.0
            self._terminal_win_str = "SYSTEM EXPLOITED"
            return True
        if outcome in (NPCOutcome.IMPOUND, "impound"):
            self._terminal_win_hold_t = 1.35
            self._terminal_win_str = "TERMINAL TERMINATED"
            return True
        return False

    # ------------------------------------------------------------------
    def _render(self):
        self.screen.fill(S.VOID)
        state = self._effective_state()

        # Death hold: red flash that fades to black before DECANTING
        if self._death_hold_t > 0:
            # Show the ship explosion moment: red->black flash
            frac = self._death_hold_t / 0.9   # 1.0 at start, 0.0 at end
            r    = int(200 * frac)
            self.screen.fill((r, 0, 0))
            f = pygame.font.SysFont("monospace", 28, bold=True)
            if frac > 0.4:
                txt = f.render("SHIP DESTROYED", True, (255, 80, 80))
                self.screen.blit(txt, (S.SCREEN_W // 2 - txt.get_width() // 2,
                                       S.SCREEN_H // 2 - 14))
            self.transition.draw(self.screen, self._dt)
            pygame.display.flip()
            return

        if state == GameState.FLIGHT:
            self.vec_renderer.draw(self.run_mgr, self.ship, self._dt)
            self.hud_renderer.draw(self.ship, self.run_mgr)
            self._render_sector_hud()
            if self.run_mgr._flash_t > 0 and self.run_mgr._last_stats:
                self._render_sector_flash(
                    self.run_mgr._last_stats, self.run_mgr._flash_t)
            self.cockpit_renderer.draw(pygame.time.get_ticks() / 1000.0)

        elif state == GameState.TERMINAL:
            self.term_renderer.draw(self.run_mgr.active_terminal)
            if self.run_mgr._intercepting_barge is not None:
                self._render_drift_strip()
            # Terminal win overlay — show outcome message before returning to flight
            if self._terminal_win_hold_t > 0 and self._terminal_win_str:
                self._render_terminal_win_overlay()

        elif state == GameState.LOADOUT_DRAFT:
            self.run_mgr.draft.render(self.screen)

        elif state == GameState.DIFFICULTY_SELECT:
            self._render_difficulty_select()

        elif state == GameState.DELIVERY:
            if self._delivery is not None:
                self._delivery.draw(self.screen)

        elif state == GameState.DECANTING:
            self._render_decanting()

        elif state == GameState.INTERSTITIAL:
            self._render_interstitial()

        elif state == GameState.SHOP:
            if self._shop is not None:
                self._shop.draw(self.screen, pygame.time.get_ticks() / 1000.0)

        elif state == GameState.MAIN_MENU:
            self._render_main_menu()

        if self.states.state == GameState.PAUSED:
            self._render_pause_overlay()

        # CRT power-down overlay (no-op when no transition is active)
        self.transition.draw(self.screen, self._dt)

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
        self.screen.blit(sec_txt, (sec_w // 2 - sec_txt.get_width() // 2, 12))

        # 5-pip run progress bar
        pip_w, pip_h, pip_gap = 14, 8, 4
        total_pip_w = S.SECTORS_PER_RUN * pip_w + (S.SECTORS_PER_RUN - 1) * pip_gap
        pip_x0 = sec_w // 2 - total_pip_w // 2
        pip_y  = 30
        pulse  = 0.55 + 0.45 * math.sin(t * 4.0)
        for i in range(S.SECTORS_PER_RUN):
            px = pip_x0 + i * (pip_w + pip_gap)
            if i + 1 < rm.sector_num:          # completed
                col = (180, 120, 0)
            elif i + 1 == rm.sector_num:        # current
                col = (int(0 + 200 * pulse), int(200 * pulse), int(50 * pulse))
            else:                               # upcoming
                col = (30, 30, 35)
            pygame.draw.rect(self.screen, col, (px, pip_y, pip_w, pip_h))
            pygame.draw.rect(self.screen, (60, 50, 20), (px, pip_y, pip_w, pip_h), 1)

        # Label upcoming shop stops and the delivery
        pip_label_font = pygame.font.SysFont("monospace", 9)
        for i in range(S.SECTORS_PER_RUN):
            px = pip_x0 + i * (pip_w + pip_gap)
            if i in S.SHOP_SECTORS:
                lbl = pip_label_font.render("S", True, (140, 100, 0))
                self.screen.blit(lbl, (px + pip_w // 2 - lbl.get_width() // 2, pip_y - 10))
        # Delivery indicator after the last pip
        del_x = pip_x0 + S.SECTORS_PER_RUN * (pip_w + pip_gap)
        dlbl = pip_label_font.render("DROP", True, (0, 160, 90))
        self.screen.blit(dlbl, (del_x, pip_y))

        if rm.jump_ready:
            jump_txt = font.render("[ J ]  JUMP READY", True, S.GREEN_TERM)
        elif (getattr(rm, "mutators", None) is not None
              and rm.mutators.is_active("slingshot_only")):
            # Sector timer doesn't advance — only slingshots fill the bar.
            # Render N slingshots remaining instead of a misleading countdown.
            deficit = max(0.0, rm._sector_dur - rm._sector_timer)
            per_sling = rm._sector_dur / 3.0
            slings_needed = max(1, int(-(-deficit // per_sling)))  # ceil div
            label = (f"SLING TO JUMP  ({slings_needed})"
                     if slings_needed > 1 else "SLING TO JUMP")
            jump_txt = font.render(label, True, (190, 140, 60))
        else:
            jump_txt = font.render(
                f"JUMP IN  {rm.jump_cooldown:>4.0f}s", True, S.GREY_DEAD,
            )
        self.screen.blit(jump_txt, (sec_w // 2 - jump_txt.get_width() // 2, 48))

        # Speed readout
        speed     = self.ship.body.speed()
        speed_col = (255, 120, 0) if speed > 500 else S.GREY_DEAD
        spd_txt   = font.render(f"{speed:>5.0f} m/s", True, speed_col)
        self.screen.blit(spd_txt, (sec_w // 2 - spd_txt.get_width() // 2, 64))

        # Sector name + "formerly" — the corporate rebrand
        sector = rm.sector
        if sector is not None and getattr(sector, "name", ""):
            name_surf = font_hd.render(sector.name, True, (170, 170, 110))
            self.screen.blit(name_surf,
                             (sec_w // 2 - name_surf.get_width() // 2, 84))
            if sector.formerly:
                fm_surf = font_sm.render(
                    f"(formerly: {sector.formerly})", True, (95, 95, 95))
                self.screen.blit(fm_surf,
                                 (sec_w // 2 - fm_surf.get_width() // 2, 102))
            # Epic 12.3 — hazard/opportunity ticker, only first 8s of sector
            if rm._sector_timer < 8.0 and (sector.hazard_roll or sector.opportunity_roll):
                from roguelite.procedural import SECTOR_HAZARD_ROLLS, SECTOR_OPPORTUNITY_ROLLS
                fade = min(1.0, max(0.0, (8.0 - rm._sector_timer) / 8.0))
                y_off = 118
                if sector.hazard_roll:
                    hz_txt = SECTOR_HAZARD_ROLLS.get(sector.hazard_roll, sector.hazard_roll)
                    hcol = (int(180 * fade), int(70 * fade), int(40 * fade))
                    hs = font_sm.render(f"HAZARD: {hz_txt}", True, hcol)
                    self.screen.blit(hs, (sec_w // 2 - hs.get_width() // 2, y_off))
                    y_off += 14
                if sector.opportunity_roll:
                    op_txt = SECTOR_OPPORTUNITY_ROLLS.get(sector.opportunity_roll, sector.opportunity_roll)
                    ocol = (int(40 * fade), int(160 * fade), int(80 * fade))
                    os_s = font_sm.render(f"OPPORTUNITY: {op_txt}", True, ocol)
                    self.screen.blit(os_s, (sec_w // 2 - os_s.get_width() // 2, y_off))

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
        # Apply difficulty rate multiplier to the displayed interest figure.
        diff_mult = self.meta.debt_rate_mult()
        debt_txt = font.render(
            f"DEBT  {displayed_debt:,} cr  +{interest_per_sec * diff_mult:.2f}/s",
            True, ticker_col)

        # Epic 16 — float debt change label for 2s beside the counter
        self._debt_float_t = max(0.0, self._debt_float_t - dt)
        if self._debt_float_t > 0 and self._debt_float_label:
            fade = min(1.0, self._debt_float_t)
            alpha = int(220 * fade)
            is_gain = self._debt_float_label.startswith("+")
            fl_col = (60, 200, 90) if is_gain else (220, 90, 60)
            fl_surf = font_sm.render(self._debt_float_label, True, fl_col)
            fl_surf.set_alpha(alpha)
            self.screen.blit(fl_surf, (10 + debt_txt.get_width() + 8, S.FLIGHT_H - 22))

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

        # Epic 13.2 — flight event choice popup (amber panel, ~8s countdown)
        fe = getattr(rm, "flight_events", None)
        if fe is not None and fe.active is not None:
            self._draw_flight_event_popup(fe, t)

    def _draw_flight_event_popup(self, fe, t):
        """Center-top amber bordered popup with title, choices, and countdown."""
        ev = fe.active
        if ev is None:
            return
        W, H = 360, 96
        cx = S.SCREEN_W // 2
        x  = cx - W // 2
        y  = 142   # below sector name strip

        # Backing — dark slate, subtle pulse on the border
        pulse = 0.65 + 0.35 * (1.0 - (fe.t_remaining / 8.0))   # tightens as time runs out
        border_col = (int(190 + 50 * pulse), int(120 + 30 * pulse), 30)
        bg = pygame.Surface((W, H), pygame.SRCALPHA)
        bg.fill((14, 12, 8, 215))
        self.screen.blit(bg, (x, y))
        pygame.draw.rect(self.screen, border_col, (x, y, W, H), 2)

        # Header chip — left-justified title with thin underline
        title_font = pygame.font.SysFont("monospace", 14, bold=True)
        sub_font   = pygame.font.SysFont("monospace", 11)
        title_surf = title_font.render(ev.title, True, (240, 200, 90))
        self.screen.blit(title_surf, (x + 12, y + 8))
        # COMMS tag right-justified
        tag_surf = sub_font.render("INCOMING / COMMS", True, (130, 100, 60))
        self.screen.blit(tag_surf, (x + W - tag_surf.get_width() - 12, y + 10))
        pygame.draw.line(self.screen, (90, 60, 20),
                         (x + 10, y + 26), (x + W - 10, y + 26), 1)

        # Countdown bar — full width below header, drains red
        bar_y = y + 32
        bar_w = W - 24
        bar_h = 4
        pygame.draw.rect(self.screen, (40, 30, 20), (x + 12, bar_y, bar_w, bar_h))
        frac = max(0.0, min(1.0, fe.t_remaining / 8.0))
        fill_w = int(bar_w * frac)
        fill_col = (220, 160, 40) if frac > 0.35 else (220, 70, 40)
        pygame.draw.rect(self.screen, fill_col, (x + 12, bar_y, fill_w, bar_h))

        # Choice prompts — bottom row
        choice_font = pygame.font.SysFont("monospace", 13, bold=True)
        accept = choice_font.render(f"[Y]  {ev.accept_label}", True, (110, 220, 130))
        ignore = choice_font.render(f"  -  {ev.ignore_label}", True, (150, 150, 150))
        sec_txt = choice_font.render(f"{fe.t_remaining:0.1f}s", True, (200, 160, 90))
        self.screen.blit(accept, (x + 14, y + H - 26))
        self.screen.blit(ignore, (x + 150, y + H - 26))
        self.screen.blit(sec_txt, (x + W - sec_txt.get_width() - 14, y + H - 26))

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

        slingshots = int(stats.get("slingshots", 0))
        sling_value = _format_slingshot_flash_value(stats)

        rows = [
            ("CREDITS RECOVERED", f"{stats['credits']:,} cr",
             (90, 230, 110) if stats['credits'] > 0 else (140, 140, 140)),
            ("TETHER SNAPS",      f"{stats['snaps']}",
             (255, 180, 50) if stats['snaps'] > 0 else (110, 110, 110)),
            ("SLINGSHOTS",        sling_value,
             (180, 130, 255) if slingshots > 0 else (110, 110, 110)),
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
        is_final = stats['sector'] >= S.SECTORS_PER_RUN
        foot_str = "// DELIVERY RUN — CARGO DROP-OFF NEXT //" if is_final \
            else f"// SECTOR {stats['sector'] + 1} OF {S.SECTORS_PER_RUN} LOADING //"
        foot_col = (100, 255, 160) if is_final else (90, 200, 110)
        foot = font_sm.render(foot_str, True, foot_col)
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

    # Nova Soma taglines — rotated per clone count on the death screen
    _DECANT_TAGLINES = [
        "Your Body, Our Investment.  Est. 2041.",
        "We Value Your Continued Productivity.",
        "Clone Activated. Debt Transferred. Welcome Back.",
        "Your Previous Self Exceeded Expectations — Briefly.",
        "Another You. Same Invoice. Fresh Start (Terms Apply).",
        "Genuine Nova Soma® Parts In Every Clone.",
        "Your Sacrifice Is Noted. Your Debt Is Not Forgiven.",
        "Reconstituted For Your Convenience. Billed Accordingly.",
        "You Are Our Most Important Asset. Also Our Most Indebted.",
        "Nova Soma: We Never Lose A Customer. Only A Body.",
    ]

    # Bax clone wake-up quips — generic fallback when death cause is unknown
    _DECANT_BAX = [
        "BAX: '...sensor re-initialised. Right. You're dead again. "
        "Clone number {n}. Still owe 'em everything. Welcome back.'",
        "BAX: 'New body smells like the old one, just cleaner. "
        "That won't last. Clone {n}. Let's get moving.'",
        "BAX: 'Sensors nominal. You're back. Debt's worse. "
        "Clone {n}. Same as before, only more indebted. Hello.'",
        "BAX: 'Ah. Clone {n}. They kept your ears this time, which is nice. "
        "Same debt. Same ship. Same droid. Sorry about that last one.'",
        "BAX: 'Systems online. Pilot confirmed: not dead. Technically. "
        "Clone {n}. I'll warm up the thrusters. Try not to die again.'",
    ]

    # Death-cause-specific Bax reactions — keyed by ship.last_damage_source
    _DECANT_BAX_BY_SOURCE = {
        "debris": [
            "BAX: 'Cause of death: a ROCK. An ordinary, un-aimed rock. "
            "Clone {n} respectfully suggests we look where we're flying.'",
            "BAX: 'You were killed by debris. Inanimate debris. "
            "I'm not going to lecture you. Much. Clone {n}, by the way.'",
            "BAX: 'Forensic report: rock-shaped indentation, pilot-shaped pilot. "
            "Match confirmed. Clone {n} is online.'",
        ],
        "debris_shower": [
            "BAX: 'Asteroid scatter, mate. Caught the worst of it. "
            "Clone {n}'s here. Maybe duck next time. Or weave. Either works.'",
            "BAX: 'You went TOWARD the debris shower. I noticed. "
            "Clone {n} has noticed. We've both noticed.'",
        ],
        "satellite": [
            "BAX: 'Killed by a satellite. A DERELICT satellite. "
            "Nova Soma's debris bill is shameful. Clone {n} online.'",
            "BAX: 'You hit an old comm relay at full speed. It was already broken. "
            "Now you're broken too. Clone {n} is fresh.'",
        ],
        "form_missed": [
            "BAX: 'Cause of death: BUREAUCRACY. You missed Form 27-B. "
            "Hull integrity penalty proved fatal. Clone {n} reports for duty.'",
            "BAX: 'The Union killed you with paperwork. They actually did it. "
            "I've seen everything now. Clone {n} is decanted.'",
            "BAX: 'Death by triplicate form. Subsection 9. "
            "I'll let that one sink in. Clone {n} online.'",
        ],
        "tether": [
            "BAX: 'Local 404 finally caught us. Tether did the rest. "
            "Clone {n} is up. Drift HARDER next time.'",
            "BAX: 'Repo Union 1, Pilot 0. Clone {n} ready for the rematch.'",
        ],
    }

    def _render_terminal_win_overlay(self):
        """Semi-transparent overlay shown after a terminal outcome beat."""
        t    = pygame.time.get_ticks() / 1000.0
        frac = min(1.0, self._terminal_win_hold_t / 5.0)
        # Fade in quickly, hold, fade out near end
        alpha = 200 if frac > 0.15 else int(200 * frac / 0.15)
        ov    = pygame.Surface((S.SCREEN_W, S.SCREEN_H), pygame.SRCALPHA)
        ov.fill((0, 0, 0, alpha))
        self.screen.blit(ov, (0, 0))

        cx = S.SCREEN_W // 2
        cy = S.SCREEN_H // 2
        is_exploit = "EXPLOIT" in self._terminal_win_str
        is_failure = (
            "TERMINATED" in self._terminal_win_str or
            "IMPOUND" in self._terminal_win_str
        )
        col = (
            (255, 55, 55) if is_failure else
            (200, 80, 255) if is_exploit else
            (0, 255, 140)
        )

        # Pulsing glow ring
        pulse = 0.7 + 0.3 * math.sin(t * 4.0)
        glow_col = (int(col[0] * pulse * 0.35), int(col[1] * pulse * 0.35),
                    int(col[2] * pulse * 0.35))
        pygame.draw.circle(self.screen, glow_col, (cx, cy - 30), 80, 4)

        fh = pygame.font.SysFont("monospace", 28, bold=True)
        fs = pygame.font.SysFont("monospace", 14)
        title = fh.render(self._terminal_win_str, True, col)
        self.screen.blit(title, (cx - title.get_width() // 2, cy - 50))

        dim_col = (int(col[0] * 0.6), int(col[1] * 0.6), int(col[2] * 0.6))
        if is_failure:
            sub_lines = ["terminal terminated  ·  barge channel hot", "returning to flight..."]
        elif is_exploit:
            sub_lines = ["system compromised  ·  credits rerouted", "they'll find out eventually."]
        else:
            sub_lines = ["channel closed  ·  sector advance", "returning to flight..."]
        for i, line in enumerate(sub_lines):
            s = fs.render(line, True, dim_col)
            self.screen.blit(s, (cx - s.get_width() // 2, cy + 10 + i * 20))

    def _draw_clone_tube_bg(self, t: float):
        """Cold clinical clone-vat room background for the decanting screen."""
        W, H = S.SCREEN_W, S.SCREEN_H
        surf  = self.screen

        surf.fill((3, 5, 9))

        # Floor grid — cold blue-grey
        gy = int(H * 0.72)
        for fi in range(10):
            y = gy + (H - gy) * fi // 9
            pygame.draw.line(surf, (9, 12, 18), (0, y), (W, y))
        vp_x = W // 2
        for ci in range(14):
            bx = W * ci // 13
            pygame.draw.line(surf, (9, 12, 18), (vp_x, gy), (bx, H))

        # Ceiling conduit
        for px in range(0, W, 120):
            pygame.draw.rect(surf, (8, 12, 18), (px, 0, 88, 14))
            pygame.draw.rect(surf, (14, 20, 28), (px, 0, 88, 14), 1)

        # Back wall — cold institutional
        pygame.draw.rect(surf, (5, 7, 11), (0, 18, W, gy - 18))
        pygame.draw.line(surf, (14, 20, 30), (0, gy), (W, gy), 1)

        # Clone tubes — 5 cylinders, one center glowing (new clone)
        tube_data = [
            (int(W * 0.08), False), (int(W * 0.24), False),
            (int(W * 0.50), True),  # active — player's new body
            (int(W * 0.76), False), (int(W * 0.92), False),
        ]
        tube_w, tube_h = 44, int(H * 0.46)
        tube_top = int(H * 0.22)
        glow_pulse = 0.55 + 0.45 * abs(math.sin(t * 1.8))

        for tx, active in tube_data:
            # Tube body
            tr = pygame.Rect(tx - tube_w // 2, tube_top, tube_w, tube_h)
            if active:
                bg_col = (4, 14, 22)
                border_col = (0, int(80 * glow_pulse), int(140 * glow_pulse))
                fluid_col  = (0, int(55 * glow_pulse), int(110 * glow_pulse))
            else:
                bg_col = (4, 6, 9)
                border_col = (14, 18, 24)
                fluid_col  = (6, 9, 13)

            pygame.draw.rect(surf, bg_col, tr)
            pygame.draw.rect(surf, border_col, tr, 2)

            # Fluid fill gradient (bottom third)
            fluid_rect = pygame.Rect(tr.x + 2, tr.y + tube_h * 2 // 3,
                                     tr.w - 4, tube_h // 3 - 2)
            pygame.draw.rect(surf, fluid_col, fluid_rect)

            # Top dome cap
            cap = pygame.Rect(tr.x - 4, tr.y - 8, tube_w + 8, 16)
            pygame.draw.ellipse(surf, bg_col, cap)
            pygame.draw.ellipse(surf, border_col, cap, 1)

            # Base plate
            base = pygame.Rect(tr.x - 8, tr.bottom - 2, tube_w + 16, 10)
            pygame.draw.rect(surf, (12, 10, 7), base)
            pygame.draw.rect(surf, (30, 22, 14), base, 1)

            # Side conduit pipes
            for ox in (-tube_w // 2 - 10, tube_w // 2 + 4):
                pygame.draw.line(surf, (10, 14, 20),
                                 (tx + ox, tube_top), (tx + ox, tr.bottom), 2)

            if active:
                # Glow halo around active tube
                halo = pygame.Surface((tube_w + 40, tube_h + 40), pygame.SRCALPHA)
                a = int(25 * glow_pulse)
                pygame.draw.rect(halo, (0, 80, 160, a), halo.get_rect(), 12)
                surf.blit(halo, (tx - tube_w // 2 - 20, tube_top - 20))

                # "DECANTING" label below active tube
                fa = pygame.font.SysFont("monospace", 9, bold=True)
                lbl = fa.render("DECANTING", True,
                                (0, int(130 * glow_pulse), int(220 * glow_pulse)))
                surf.blit(lbl, (tx - lbl.get_width() // 2, tr.bottom + 14))

        # Nova Soma logo on back wall (dim, corporate)
        f_logo = pygame.font.SysFont("monospace", 11, bold=True)
        logo = f_logo.render("NOVA SOMA SOLUTIONS — DECANTING WARD 7", True, (20, 22, 28))
        surf.blit(logo, (W // 2 - logo.get_width() // 2, gy - 22))

    def _render_decanting(self):
        t = pygame.time.get_ticks() / 1000.0
        font_sm  = pygame.font.SysFont("monospace", 13)
        font     = pygame.font.SysFont("monospace", 17)
        font_hd  = pygame.font.SysFont("monospace", 11)

        # Clone tube hospital background
        self._draw_clone_tube_bg(t)

        # Nova Soma header — rotating tagline per clone
        header = pygame.font.SysFont("monospace", 14, bold=True)
        tagline = self._DECANT_TAGLINES[
            self.meta.clone_count % len(self._DECANT_TAGLINES)]
        tagline_surf = header.render(
            f"NOVA SOMA SOLUTIONS  ·  {tagline}",
            True, (65, 65, 70))
        self.screen.blit(tagline_surf,
                         (S.SCREEN_W // 2 - tagline_surf.get_width() // 2, 12))
        pygame.draw.line(self.screen, (40, 42, 48), (80, 30), (S.SCREEN_W - 80, 30), 1)

        # Invoice panel — centred, semi-transparent over the tubes
        W, H = S.SCREEN_W, S.SCREEN_H
        cx = W // 2
        panel_w, panel_h = 640, 300
        panel_x = cx - panel_w // 2
        panel_y = int(H * 0.56)
        psurf = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        psurf.fill((3, 4, 8, 230))
        self.screen.blit(psurf, (panel_x, panel_y))
        pygame.draw.rect(self.screen, (40, 42, 50),
                         (panel_x, panel_y, panel_w, panel_h), 1)

        lines = [
            ("PATIENT INTAKE SUMMARY", S.AMBER_TERM, font),
            (f"Unit ID: CLN-{self.meta.clone_count:04d}  ·  Template: BASELINE-7  ·  "
             f"Condition on Arrival: DECEASED", (120, 120, 130), font_sm),
            ("", None, font_sm),
            ("ITEMISED CHARGES", (80, 82, 95), font_sm),
            (f"  Clone fluid & substrate . . . . -{S.CLONE_FLUID_FEE:>8,} cr",
             (160, 160, 170), font),
            (f"  Wreckage recovery & tow . . . . -{S.WRECKAGE_TOW_FEE:>8,} cr",
             (160, 160, 170), font),
            (f"  Body lease (standard term) . . . -{S.BASE_CLONE_DEBT:>8,} cr",
             (160, 160, 170), font),
            ("", None, font_sm),
            (f"OUTSTANDING BALANCE:   {self.meta.debt:,} cr",
             S.AMBER_TERM, pygame.font.SysFont("monospace", 20, bold=True)),
            ("", None, font_sm),
            ("This invoice is non-negotiable. Debt is hereditary and compound.",
             (60, 60, 68), font_sm),
            ("(Form NS-19b opt-out is not available in your jurisdiction.)",
             (48, 48, 56), font_sm),
            ("", None, font_sm),
            ("[ ENTER : ACCEPT CHARGES (non-optional) ]", S.GREEN_TERM, font),
        ]

        y = panel_y + 14
        for text, col, f in lines:
            if col is None:
                y += 8
                continue
            surf = f.render(text, True, col)
            self.screen.blit(surf, (cx - surf.get_width() // 2, y))
            y += f.get_linesize() + 2

        # Epic 12.4 — Career stats panel (right side of invoice)
        stats_tracker = getattr(self.run_mgr, "stats", None) if self.run_mgr else None
        if stats_tracker is not None:
            stats_x = panel_x + panel_w + 28
            stats_w = 220
            stats_h = 200
            stats_y = panel_y + 10
            if stats_x + stats_w < S.SCREEN_W - 16:
                stats_panel = pygame.Surface((stats_w, stats_h), pygame.SRCALPHA)
                stats_panel.fill((4, 8, 14, 200))
                self.screen.blit(stats_panel, (stats_x, stats_y))
                pygame.draw.rect(self.screen, (35, 50, 70),
                                 (stats_x, stats_y, stats_w, stats_h), 1)
                f_hdr = pygame.font.SysFont("monospace", 10, bold=True)
                f_body = pygame.font.SysFont("monospace", 9)
                hdr = f_hdr.render("CAREER LEDGER", True, (95, 150, 180))
                self.screen.blit(hdr, (stats_x + 10, stats_y + 8))
                # Run + career summaries combined
                rows = stats_tracker.career_summary_lines()[:8]
                ry = stats_y + 26
                for row in rows:
                    s = f_body.render(row, True, (140, 160, 180))
                    self.screen.blit(s, (stats_x + 10, ry))
                    ry += 13
                # Unlocks earned this run/session
                if self.meta.unlocks:
                    pygame.draw.line(self.screen, (40, 60, 80),
                                     (stats_x + 8, ry + 4), (stats_x + stats_w - 8, ry + 4), 1)
                    ul = f_hdr.render("UNLOCKS EARNED", True, (180, 140, 60))
                    self.screen.blit(ul, (stats_x + 10, ry + 8))
                    ry += 22
                    for uk in self.meta.unlocks[:3]:
                        s = f_body.render(f"• {uk.replace('_', ' ')}",
                                          True, (200, 170, 90))
                        self.screen.blit(s, (stats_x + 10, ry))
                        ry += 12

        # Bax wake-up line — use the line cached at death time (not re-rolled each frame)
        bax_line = self._decant_bax_line or random.choice(self._DECANT_BAX).format(
            n=self.meta.clone_count)
        font_bax = pygame.font.SysFont("monospace", 12)
        bax_surf = font_bax.render(bax_line, True, (100, 130, 100))
        self.screen.blit(bax_surf,
                         (S.SCREEN_W // 2 - bax_surf.get_width() // 2,
                          S.SCREEN_H - 52))
        pygame.draw.line(self.screen, (40, 60, 40),
                         (80, S.SCREEN_H - 62), (S.SCREEN_W - 80, S.SCREEN_H - 62), 1)

    # ------------------------------------------------------------------
    # Interstitial — bridge between successful delivery and next chapter
    # ------------------------------------------------------------------
    _CHAPTER_NAMES = {
        1: "ACOUSTIC ARCHIVE",
        2: "MYCORRHIZAL PAYLOAD",
        3: "THE PAPERWORK",
        4: "SCHRÖDINGER VIP",
    }
    _CHAPTER_SUBTITLES = {
        1: "contraband uncompressed audio",
        2: "weaponized epistemological fungi",
        3: "telepathic bureaucratic forms",
        4: "sealed box. alive AND dead.",
    }
    _INTERSTITIAL_BAX = {
        1: ("Archive's in their hands. Don't think too hard about who 'they' are. "
            "They paid clean. The music's safe. That's what matters. "
            "Next gig: psychoactive fungus. I'll air the cabin. Probably won't help."),
        2: ("Shrooms delivered. Cabin still smells funny. The lab signed off and the "
            "colours stopped. Mostly. Next: telepathic paperwork. I am NOT making that up. "
            "Get the antacids ready, mate."),
        3: ("Forms signed and silenced. The Union now has bureaucracy that files itself. "
            "Whoever runs that office is doomed and doesn't know it yet. "
            "Next: one passenger, sealed box. Don't open it. ...Fine, open it. I'm curious too."),
        4: ("All four cargos. All four payouts. Local 404 didn't win. Neither did we. "
            "We just kept goin'. That's the gig. Rest up. "
            "We'll be back. We're always back."),
    }

    def _enter_interstitial(self):
        # Mark delivery complete in meta_progression handled by DeliverySequence._compute_result
        completed = self._delivery_chapter
        next_ch = completed + 1
        campaign_end = next_ch > 4 or len(self.meta.chapters_completed) >= 4
        self._interstitial_completed     = completed
        self._interstitial_next          = next_ch
        self._interstitial_campaign_end  = campaign_end
        self._interstitial_t             = 11.0   # auto-advance window
        self._goto(GameState.INTERSTITIAL)

    def _exit_interstitial(self):
        if self._interstitial_campaign_end:
            self._run_just_completed = True
            self._goto(GameState.MAIN_MENU)
        else:
            # Auto-advance into next chapter's loadout draft
            self.run_mgr.start_run(self.ship)
            self._run_just_completed = False
            self._goto(GameState.LOADOUT_DRAFT)

    def _render_interstitial(self):
        t  = pygame.time.get_ticks() / 1000.0
        cx = S.SCREEN_W // 2
        completed = self._interstitial_completed
        next_ch   = self._interstitial_next
        is_end    = self._interstitial_campaign_end

        # Background — drifting starfield, dimmed
        self.vec_renderer.draw_menu_background(t)
        overlay = pygame.Surface((S.SCREEN_W, S.SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        self.screen.blit(overlay, (0, 0))

        # Letterbox bars
        bar_h = 64
        pygame.draw.rect(self.screen, (0, 0, 0),
                         pygame.Rect(0, 0, S.SCREEN_W, bar_h))
        pygame.draw.rect(self.screen, (0, 0, 0),
                         pygame.Rect(0, S.SCREEN_H - bar_h, S.SCREEN_W, bar_h))
        pygame.draw.line(self.screen, (120, 80, 0),
                         (0, bar_h), (S.SCREEN_W, bar_h), 1)
        pygame.draw.line(self.screen, (120, 80, 0),
                         (0, S.SCREEN_H - bar_h), (S.SCREEN_W, S.SCREEN_H - bar_h), 1)

        # --- Completed chapter banner ---
        f_label = pygame.font.SysFont("monospace", 13, bold=True)
        f_title = pygame.font.SysFont("monospace", 34, bold=True)
        f_sub   = pygame.font.SysFont("monospace", 14, italic=True)

        # Stamp
        label = f_label.render(f"CHAPTER {completed}  ::  DELIVERED",
                               True, S.GREEN_TERM)
        self.screen.blit(label, (cx - label.get_width() // 2, bar_h + 22))
        title_name = self._CHAPTER_NAMES.get(completed, f"CHAPTER {completed}")
        ts = f_title.render(title_name, True, S.AMBER_TERM)
        self.screen.blit(ts, (cx - ts.get_width() // 2, bar_h + 44))
        # Subtitle
        sub = f_sub.render(self._CHAPTER_SUBTITLES.get(completed, ""),
                           True, (160, 130, 60))
        self.screen.blit(sub, (cx - sub.get_width() // 2, bar_h + 86))

        # Separator
        sep_y = bar_h + 116
        pygame.draw.line(self.screen, (80, 60, 0),
                         (160, sep_y), (S.SCREEN_W - 160, sep_y), 1)

        # --- Bax monologue (typewriter) ---
        monologue = self._INTERSTITIAL_BAX.get(completed, "")
        elapsed   = max(0.0, 11.0 - self._interstitial_t)
        # type ~32 chars/sec — full reveal by ~5s into screen
        reveal_n  = int(elapsed * 38)
        shown     = monologue[:reveal_n]
        # Cursor blink
        cursor = "_" if int(t * 2.4) % 2 == 0 and reveal_n < len(monologue) else " "
        shown += cursor

        # Wrapped render
        f_bax = pygame.font.SysFont("monospace", 17)
        max_w = S.SCREEN_W - 220
        words = shown.split(" ")
        lines: list[str] = []
        cur = ""
        for w in words:
            test = (cur + " " + w).strip()
            if f_bax.size(test)[0] > max_w and cur:
                lines.append(cur)
                cur = w
            else:
                cur = test
        if cur:
            lines.append(cur)

        ly = sep_y + 26
        # Mini Bax portrait next to text
        px, py = 130, ly + 22
        self._draw_bax_mini(px, py, t, speaking=(reveal_n < len(monologue)))

        for line in lines[:6]:
            ts = f_bax.render(line, True, (235, 215, 130))
            self.screen.blit(ts, (190, ly))
            ly += 24

        # --- Next chapter or campaign end card ---
        next_y = S.SCREEN_H - bar_h - 140
        if is_end:
            f_end_l = pygame.font.SysFont("monospace", 12, bold=True)
            f_end_t = pygame.font.SysFont("monospace", 28, bold=True)
            f_end_s = pygame.font.SysFont("monospace", 13)
            pulse = 0.5 + 0.5 * math.sin(t * 1.6)
            end_col = (int(160 + 80 * pulse), int(220 * pulse + 35), int(40 + 40 * pulse))
            top_label = f_end_l.render("CAMPAIGN COMPLETE", True, (140, 200, 80))
            self.screen.blit(top_label, (cx - top_label.get_width() // 2, next_y))
            big = f_end_t.render("ALL FOUR CARGOS DELIVERED", True, end_col)
            self.screen.blit(big, (cx - big.get_width() // 2, next_y + 18))
            stats = (f"DEBT: {self.meta.debt:,} cr   ·   CLONES: {self.meta.clone_count}   ·   "
                     "ROUTE: CLEAR")
            ss = f_end_s.render(stats, True, (170, 170, 190))
            self.screen.blit(ss, (cx - ss.get_width() // 2, next_y + 56))
        else:
            f_n_l = pygame.font.SysFont("monospace", 12, bold=True)
            f_n_t = pygame.font.SysFont("monospace", 26, bold=True)
            f_n_s = pygame.font.SysFont("monospace", 13, italic=True)
            next_name = self._CHAPTER_NAMES.get(next_ch, f"CHAPTER {next_ch}")
            next_sub  = self._CHAPTER_SUBTITLES.get(next_ch, "")
            label_next = f_n_l.render(f"NEXT  //  CHAPTER {next_ch}", True, (180, 130, 30))
            self.screen.blit(label_next, (cx - label_next.get_width() // 2, next_y))
            tn = f_n_t.render(next_name, True, (255, 200, 80))
            self.screen.blit(tn, (cx - tn.get_width() // 2, next_y + 18))
            sn = f_n_s.render(next_sub, True, (140, 110, 50))
            self.screen.blit(sn, (cx - sn.get_width() // 2, next_y + 50))

        # --- Footer: auto-advance bar + ENTER prompt ---
        bar_w  = 360
        bar_x  = cx - bar_w // 2
        bar_y  = S.SCREEN_H - bar_h - 30
        progress = max(0.0, min(1.0, 1.0 - self._interstitial_t / 11.0))
        pygame.draw.rect(self.screen, (40, 30, 0),
                         pygame.Rect(bar_x, bar_y, bar_w, 4))
        pygame.draw.rect(self.screen, (220, 160, 30),
                         pygame.Rect(bar_x, bar_y, int(bar_w * progress), 4))

        f_foot = pygame.font.SysFont("monospace", 12)
        prompt = (f"[ ENTER ]  return to depot"
                  if is_end else
                  f"[ ENTER ]  load next chapter   //   auto in {self._interstitial_t:.0f}s")
        prompt_pulse = 0.55 + 0.45 * math.sin(t * 3.2)
        col = (int(140 + 100 * prompt_pulse), int(190 + 60 * prompt_pulse), int(100 + 60 * prompt_pulse))
        ps = f_foot.render(prompt, True, col)
        self.screen.blit(ps, (cx - ps.get_width() // 2, S.SCREEN_H - bar_h - 14))

    def _draw_bax_mini(self, px: int, py: int, t: float, speaking: bool):
        """Compact vector Bax portrait for the interstitial."""
        head = [(px - 20, py - 26), (px + 22, py - 26),
                (px + 26, py - 4),  (px - 24, py - 4)]
        pygame.draw.polygon(self.screen, (20, 20, 30), head)
        pygame.draw.polygon(self.screen, (140, 100, 0), head, 1)
        # CRT scan lines on head
        for sy in range(py - 24, py - 4, 3):
            pygame.draw.line(self.screen, (40, 28, 0),
                             (px - 18, sy), (px + 20, sy), 1)
        glow = 0.55 + 0.40 * abs(math.sin(t * (3.0 if speaking else 0.8)))
        ec = (int(80 + 175 * glow), int(220 * glow), int(255 * glow))
        pygame.draw.circle(self.screen, ec, (px - 8, py - 16), 4)
        pygame.draw.circle(self.screen, ec, (px + 8, py - 16), 4)
        pygame.draw.circle(self.screen, (255, 255, 255), (px - 8, py - 16), 1)
        pygame.draw.circle(self.screen, (255, 255, 255), (px + 8, py - 16), 1)
        # Mouth
        mouth_y = py - 8 + int(2 * math.sin(t * 16.0)) if speaking else py - 8
        pygame.draw.line(self.screen, (200, 140, 0),
                         (px - 10, mouth_y), (px + 10, mouth_y), 2)
        # Antenna
        pygame.draw.line(self.screen, (140, 100, 0),
                         (px + 16, py - 26), (px + 22, py - 38), 1)
        pygame.draw.circle(self.screen, (255, 180, 30), (px + 22, py - 38), 3)
        # Body
        body = [(px - 24, py - 4), (px + 26, py - 4),
                (px + 22, py + 30), (px - 22, py + 30)]
        pygame.draw.polygon(self.screen, (28, 22, 8), body)
        pygame.draw.polygon(self.screen, (140, 100, 0), body, 1)

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

        # Chapter cards only on the main list (slot picker / confirms need a clear center)
        if self._menu_mode == "main":
            self._render_menu_cargo_dossier(t)

        # --- Lore strap line (above bottom bar) ---
        font_lore = pygame.font.SysFont("monospace", 13)
        lore_lines = [
            "Union of Repo Men, Local 404. They will come for what you carry.",
            "5 sectors → cargo drop-off → debt reduction.  Snap the tether.  Don't die again.",
        ]
        for i, line in enumerate(lore_lines):
            s = font_lore.render(line, True, (75, 75, 95))
            self.screen.blit(s, (cx - s.get_width() // 2,
                                  S.SCREEN_H - bar_h - 34 + i * 18))

        # --- Bottom bar: scrolling Nova Soma propaganda ticker ---
        self._render_menu_propaganda(t)

        # --- Bax mini portrait (bottom right) ---
        self._render_menu_bax_portrait(t)

        # Run controls last so nothing paints over RESUME / NEW GAME / etc.
        self._render_main_menu_actions(t)

        # --- Outer corner brackets + scanlines ---
        self._render_menu_corner_brackets()
        self._render_menu_scanlines()
        self._menu_vfx.apply_menu_grade(self.screen, self._dt)

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
        panel = pygame.Rect(S.SCREEN_W - 300, 80, 280, 98)
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

        delivery_status = "UNLOCKED" if self.meta.chapters_completed else "COMPLETE A RUN"
        rows = [
            ("STATUS",   "ALIVE-ISH" if self.meta.clone_count > 0 else "ROOKIE"),
            ("DEBT",     "CRUSHING"  if self.meta.debt > 50000 else "MANAGEABLE"),
            ("DELIVERY", delivery_status),
            ("LICENCE",  "PROVISIONAL // L-404"),
        ]
        for i, (k, v) in enumerate(rows):
            ks = font_v.render(f"{k:<10}", True, (90, 140, 180))
            vs = font_v.render(v, True, (180, 220, 240))
            self.screen.blit(ks, (panel.left + 12, panel.top + 28 + i * 17))
            self.screen.blit(vs, (panel.left + 110, panel.top + 28 + i * 17))

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
        s2 = font_s.render(f"MASS  1.0t  //  HULL {int(S.HULL_MAX)}", True, (90, 120, 160))
        self.screen.blit(s1, (panel.left + 8, panel.bottom - 24))
        self.screen.blit(s2, (panel.left + 8, panel.bottom - 12))

    # ------------------------------------------------------------------
    def _render_jukebox_panel(self, t: float, py: int,
                               font_h: pygame.font.Font,
                               font_row: pygame.font.Font,
                               font_sm: pygame.font.Font) -> None:
        """Bax's Tapes — Bax-clipboard layout, hum titles only revealed once heard."""
        from audio.bax_hum import hum_count, hum_title
        cx = S.SCREEN_W // 2
        heard = set(self.meta.bax_hums_heard)

        title = "BAX'S TAPES — CLONE-TANK B-SIDES"
        ts = font_h.render(title, True, (210, 170, 60))
        self.screen.blit(ts, (cx - ts.get_width() // 2, py - 12))

        sub = font_sm.render(
            f"{len(heard)} / {hum_count()} hums on the clipboard.  "
            "Eight in total.  He won't say where the rest are.",
            True, (110, 130, 150),
        )
        self.screen.blit(sub, (cx - sub.get_width() // 2, py + 10))

        row_y = py + 36
        # Soft scanline cycle on the selected row
        scan_phase = (t * 1.6) % 1.0
        for i in range(hum_count()):
            is_sel    = (i == self._jukebox_cursor)
            was_heard = (i in heard)
            label = hum_title(i) if was_heard else "■■■■■■■■■■"
            glyph = "○" if was_heard else "✕"
            num   = f"{i + 1:02d}"
            row_text = f"  {num}   {glyph}   {label}"
            if was_heard:
                col = (230, 190, 70) if is_sel else (180, 150, 60)
            else:
                col = (90, 70, 40) if is_sel else (60, 55, 70)
            if is_sel:
                # Amber selection chevron + faint backdrop strip
                strip = pygame.Surface((460, 28), pygame.SRCALPHA)
                strip.fill((40, 30, 8, 130))
                self.screen.blit(strip, (cx - 230, row_y - 4))
                pygame.draw.rect(self.screen, (200, 150, 50),
                                 (cx - 230, row_y - 4, 460, 28), 1)
                chev = font_row.render(">", True, (255, 200, 80))
                self.screen.blit(chev, (cx - 222, row_y))
                # Scanline glow line drifting through the row
                sy = int(row_y + 20 * scan_phase)
                pygame.draw.line(self.screen, (255, 200, 80, 80),
                                 (cx - 226, sy), (cx + 226, sy), 1)
            rs = font_row.render(row_text, True, col)
            self.screen.blit(rs, (cx - rs.get_width() // 2, row_y))
            row_y += 32

        hint = font_sm.render(
            "↑↓ select   ENTER play heard hum   ESC back",
            True, (90, 90, 110),
        )
        self.screen.blit(hint, (cx - hint.get_width() // 2, row_y + 8))

    def _render_main_menu_actions(self, t: float) -> None:
        cx = S.SCREEN_W // 2
        py = int(S.SCREEN_H * 0.54)
        font_h = pygame.font.SysFont("monospace", 13, bold=True)
        font_row = pygame.font.SysFont("monospace", 20, bold=True)
        font_sm = pygame.font.SysFont("monospace", 11)
        pulse = 0.5 + 0.5 * math.sin(t * 3.0)

        sid = self.save_mgr.active_slot_id
        active = self.save_mgr.slot_info(sid)
        hdr_text = (
            f"ACTIVE SAVE: SLOT {sid}  —  {active.chapter_display}  "
            f"//  {active.debt:,} cr  //  CLONE #{active.clone_count}"
        )
        hdr = font_sm.render(hdr_text, True, (120, 120, 150))

        if self._run_just_completed:
            font_c = pygame.font.SysFont("monospace", 14, bold=True)
            cs = font_c.render("// RUN COMPLETE //  DEBT REDUCED  //",
                               True, S.GREEN_TERM)
            self.screen.blit(cs, (cx - cs.get_width() // 2, py - 48))

        if self._menu_mode != "main":
            self.screen.blit(hdr, (cx - hdr.get_width() // 2, py - 28))

        if self._menu_mode == "confirm_overwrite":
            slot = self._pending_slot or 1
            lines = [
                f"OVERWRITE SAVE SLOT {slot}?",
                "All progress in this slot will be erased.",
                "[ Y / ENTER ]  confirm     [ N / ESC ]  cancel",
            ]
            for i, line in enumerate(lines):
                col = (220, 80, 80) if i == 0 else (140, 140, 160)
                s = font_row.render(line, True, col)
                self.screen.blit(s, (cx - s.get_width() // 2, py + i * 28))
            return

        if self._menu_mode == "confirm_delete_run":
            lines = [
                "DELETE MID-RUN CHECKPOINT?",
                "Campaign save stays. You will start fresh on next run.",
                "[ Y / ENTER ]  confirm     [ N / ESC ]  cancel",
            ]
            for i, line in enumerate(lines):
                col = (220, 140, 60) if i == 0 else (140, 140, 160)
                s = font_row.render(line, True, col)
                self.screen.blit(s, (cx - s.get_width() // 2, py + i * 28))
            return

        if self._menu_mode == "jukebox":
            self._render_jukebox_panel(t, py, font_h, font_row, font_sm)
            return

        if self._menu_mode in ("pick_new", "pick_load"):
            title = "SELECT SLOT — NEW GAME" if self._menu_mode == "pick_new" else "SELECT SLOT — LOAD"
            ts = font_h.render(title, True, (200, 160, 60))
            self.screen.blit(ts, (cx - ts.get_width() // 2, py - 8))
            for i, info in enumerate(self.save_mgr.list_slots()):
                sel = i == self._slot_cursor
                mark = ">" if sel else " "
                status = "EMPTY" if not info.exists else info.chapter_display
                debt_s = f"{info.debt:,} cr" if info.exists else "—"
                row = f"{mark} SLOT {info.slot_id}  {status}  //  {debt_s}"
                col = (255, 220, 120) if sel else (90, 90, 110)
                if not info.exists and not sel:
                    col = (55, 55, 70)
                rs = font_row.render(row, True, col)
                self.screen.blit(rs, (cx - rs.get_width() // 2, py + 22 + i * 30))
            hint = font_sm.render("↑↓ select   ENTER confirm   ESC back", True, (80, 80, 100))
            self.screen.blit(hint, (cx - hint.get_width() // 2, py + 22 + S.MAX_SAVE_SLOTS * 30 + 8))
            return

        n_rows = len(self._main_menu_rows())
        foot = font_sm.render(
            "[ 1 ] pause in-run  //  [ ESC ] pause (not at terminal)  //  data/saves/",
            True, (60, 60, 80),
        )
        hint_top = font_sm.render("↑↓ select   ENTER confirm", True, (80, 80, 100))

        hdr_y = py - 32
        hint_y = py - 10
        row_y0 = py + 20
        foot_y = row_y0 + n_rows * 32 + 8
        panel_top = hdr_y - 14
        panel_bottom = foot_y + foot.get_height() + 14
        content_w = max(hdr.get_width(), hint_top.get_width(), foot.get_width(), 320)
        panel_w = content_w + 56
        panel = pygame.Rect(cx - panel_w // 2, panel_top, panel_w, panel_bottom - panel_top)
        backdrop = pygame.Surface((panel.w, panel.h), pygame.SRCALPHA)
        backdrop.fill((4, 6, 12, 235))
        self.screen.blit(backdrop, panel.topleft)
        pygame.draw.rect(self.screen, (120, 90, 30), panel, 1)

        self.screen.blit(hdr, (cx - hdr.get_width() // 2, hdr_y))
        self.screen.blit(hint_top, (cx - hint_top.get_width() // 2, hint_y))

        for i, (label, enabled, _action) in enumerate(self._main_menu_rows()):
            sel = i == self._menu_cursor
            prefix = ">" if sel else " "
            if not enabled:
                col = (55, 55, 65)
            elif sel:
                col = (int(180 + 75 * pulse), int(200 + 55 * pulse), int(120 + 40 * pulse))
            else:
                col = (130, 130, 150)
            text = f"{prefix}  {label}"
            rs = font_row.render(text, True, col)
            self.screen.blit(rs, (cx - rs.get_width() // 2, row_y0 + i * 32))

        self.screen.blit(foot, (cx - foot.get_width() // 2, foot_y))

    def _render_pause_overlay(self) -> None:
        ov = pygame.Surface((S.SCREEN_W, S.SCREEN_H), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 170))
        self.screen.blit(ov, (0, 0))

        cx = S.SCREEN_W // 2
        cy = S.SCREEN_H // 2 - 40
        font_t = pygame.font.SysFont("monospace", 32, bold=True)
        font_r = pygame.font.SysFont("monospace", 22, bold=True)
        font_s = pygame.font.SysFont("monospace", 12)

        title = font_t.render("—  PAUSED  —", True, S.AMBER_TERM)
        self.screen.blit(title, (cx - title.get_width() // 2, cy))

        items = ("RESUME", "SAVE & RETURN TO MENU")
        for i, label in enumerate(items):
            sel = i == self._pause_menu_cursor
            col = S.GREEN_TERM if sel else (100, 100, 120)
            prefix = ">" if sel else " "
            rs = font_r.render(f"{prefix}  {label}", True, col)
            self.screen.blit(rs, (cx - rs.get_width() // 2, cy + 50 + i * 36))

        sub = font_s.render("↑↓ select   ENTER   //   ESC or 1 — resume", True, (80, 80, 100))
        self.screen.blit(sub, (cx - sub.get_width() // 2, cy + 140))

    # ------------------------------------------------------------------
    def _render_menu_cargo_dossier(self, t: float):
        """4 cargo chapter cards — completed = bright, unfinished = dimmed (Epic 8.2)."""
        _CARGO_CARDS = [
            (1, "CH.1  —  ACOUSTIC ARCHIVE",
             "Illegal music library.",
             "Proximity → signal static.",
             (160, 80,  30), (220, 120, 40)),
            (2, "CH.2  —  MYCORRHIZAL PAYLOAD",
             "Psychoactive fungal spores.",
             "Spore leak → controls invert.",
             (40,  120, 200), (80,  200, 160)),
            (3, "CH.3  —  THE PAPERWORK",
             "Sentient bureaucratic forms.",
             "Random HUD filing popups.",
             (140, 160, 80), (180, 200, 100)),
            (4, "CH.4  —  SCHRÖDINGER VIP",
             "Passenger: alive or deceased.",
             "Observation collapses payout.",
             (200, 160, 40), (255, 210, 80)),
        ]
        completed = set(self.meta.chapters_completed)
        card_w, card_h = 220, 72
        gap  = 12
        total_w = len(_CARGO_CARDS) * card_w + (len(_CARGO_CARDS) - 1) * gap
        x0   = (S.SCREEN_W - total_w) // 2
        bar_h = 56
        cy   = S.SCREEN_H - bar_h - 118   # lower on screen, below main menu box

        font_h  = pygame.font.SysFont("monospace", 10, bold=True)
        font_sm = pygame.font.SysFont("monospace", 9)

        for i, (chap, title, desc1, desc2, col, accent) in enumerate(_CARGO_CARDS):
            cx_card = x0 + i * (card_w + gap)
            done    = chap in completed
            dim     = 1.0 if done else 0.35
            pulse   = 0.8 + 0.2 * abs(math.sin(t * 2.0 + i)) if done else 0.5

            bg_col  = tuple(int(c * dim * 0.25) for c in col)
            bd_col  = tuple(int(c * dim * pulse) for c in accent)

            pygame.draw.rect(self.screen, bg_col,
                             pygame.Rect(cx_card, cy, card_w, card_h))
            pygame.draw.rect(self.screen, bd_col,
                             pygame.Rect(cx_card, cy, card_w, card_h), 1)

            # Completion badge or dim lock
            if done:
                badge_col = tuple(int(c * pulse) for c in accent)
                bs = font_h.render("✓ DELIVERED", True, badge_col)
            else:
                badge_col = tuple(int(c * dim) for c in accent)
                bs = font_h.render("[ LOCKED ]", True, badge_col)
            self.screen.blit(bs, (cx_card + 6, cy + 6))

            # Title
            ts = font_h.render(title, True, tuple(int(c * dim) for c in accent))
            self.screen.blit(ts, (cx_card + 6, cy + 22))

            # Description lines
            for j, dline in enumerate((desc1, desc2)):
                ds = font_sm.render(dline, True,
                                    tuple(int(c * dim * 0.8) for c in accent))
                self.screen.blit(ds, (cx_card + 6, cy + 40 + j * 14))

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
        from renderer.bax_doodle import draw_bax_droid

        hull_top = S.SCREEN_H // 2 + 30
        panel = pygame.Rect(S.SCREEN_W - 210, hull_top, 195, 248)
        pygame.draw.rect(self.screen, (6, 8, 12), panel)
        pygame.draw.rect(self.screen, (140, 100, 35), panel, 1)
        for c, sx, sy in ((panel.topleft, 1, 1), (panel.topright, -1, 1),
                          (panel.bottomleft, 1, -1), (panel.bottomright, -1, -1)):
            pygame.draw.line(self.screen, (200, 150, 50), c, (c[0] + sx * 14, c[1]), 2)
            pygame.draw.line(self.screen, (200, 150, 50), c, (c[0], c[1] + sy * 14), 2)

        font_h = pygame.font.SysFont("monospace", 11, bold=True)
        font_s = pygame.font.SysFont("monospace", 10)
        hdr = font_h.render("BAX // NAV-MORALE", True, (255, 190, 50))
        sub = font_s.render("bolt-on advisor droid", True, (110, 100, 80))
        self.screen.blit(hdr, (panel.centerx - hdr.get_width() // 2, panel.top + 10))
        self.screen.blit(sub, (panel.centerx - sub.get_width() // 2, panel.top + 26))

        speaking = abs(math.sin(t * 1.4)) > 0.92
        draw_bax_droid(
            self.screen, panel.centerx, panel.centery + 18, t,
            scale=2.35, speaking=speaking,
        )
