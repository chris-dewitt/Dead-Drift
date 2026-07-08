"""
Corridor — drop-in replacement for DeliveryRun.

API matches delivery/platformer.py:
  update(dt), draw(surface, screen_x, screen_y)
  handle_key(event), is_done, stars, credits_earned
"""
from __future__ import annotations
import math
import random
import pygame

from renderer.sci_fi_ui import draw_courier_sprite
from core.text import get_font

from delivery.corridor.elements import (
    CORRIDOR_W, CORRIDOR_H, FLOOR_Y, CEIL_Y, PLAYER_H, PLAYER_W,
    Platform, MovingPlatform, CollapsingPlatform, Ladder,
    Hazard, MovingHazard, ToggleBeam, OneWayWall,
    NPCEncounter, Collectible, Secret, Checkpoint, StealthZone,
    BossRoomTrigger, SporeZone, QuantumDoor,
    SteamVent, Tripwire, SecurityBeam,
    LoreRoom, NPCShortcut,
    Spring, ConveyorBelt, BreakableBlock, QuestionBlock,
    PowerUp, WarpPipe, TimedLift,
)
from delivery.corridor.mutators import get_corridor_mutator, CorridorMutator
from core.event_bus import (bus, EVT_BAX_SPEAK, EVT_DELIVERY_DONE,
                            EVT_CORRIDOR_RUN, EVT_CORRIDOR_JUMP,
                            EVT_CORRIDOR_SECRET, EVT_CORRIDOR_DEATH,
                            EVT_LORE_FOUND, EVT_CORRIDOR_ENTER,
                            EVT_CORRIDOR_BOSS_ROOM, EVT_CORRIDOR_EXIT,
                            EVT_CORRIDOR_LAND, EVT_CORRIDOR_SKID,
                            EVT_CORRIDOR_SPRINT, EVT_CORRIDOR_CHIP,
                            EVT_CORRIDOR_TALLY, EVT_CORRIDOR_STAR,
                            EVT_CORRIDOR_SPRING, EVT_CORRIDOR_BREAK,
                            EVT_CORRIDOR_QBLOCK, EVT_CORRIDOR_PIPE,
                            EVT_CORRIDOR_POWERUP, EVT_CORRIDOR_POWERDOWN)

# ── Movement feel — Delivery v2 I.1 tunables ────────────────────────────────
# These constants ARE the corridor's game feel. Tune here, nowhere else.
GRAVITY          = 980.0    # base gravity px/s²
FALL_GRAV_MULT   = 1.28     # falling is heavier than rising (the Mario asymmetry)
JUMP_CUT_MULT    = 2.35     # extra gravity while rising after jump is released
JUMP_VY          = -470.0   # jump take-off velocity
COYOTE_TIME      = 0.10     # s of jump grace after running off a ledge
JUMP_BUFFER      = 0.12     # s a jump press is remembered before landing
WALK_SPEED       = 220.0    # px/s ground cap (pre-v2 RUN_SPEED)
SPRINT_SPEED     = 320.0    # px/s cap at full sprint charge
SPRINT_CHARGE_T  = 0.8      # s of sustained ground running to earn full sprint
GROUND_ACCEL     = 900.0    # px/s² toward target speed on the ground
GROUND_DECEL     = 1400.0   # px/s² toward zero with no input
AIR_CONTROL      = 0.55     # fraction of ground accel available in the air
SKID_DECEL       = 2200.0   # px/s² while skidding out of a reversal
SKID_MIN_SPEED   = 130.0    # |vx| needed for a reversal to read as a skid
RETREAT_FACTOR   = 0.6      # backward cap fraction (corridor is forward-biased)
LAND_SFX_VY      = 260.0    # touchdown vy that warrants a land thud/squash

RUN_SPEED = WALK_SPEED      # legacy alias (ladder side-step, oneway hints)
CLIMB_SPD = 120.0
LADDER_REGRAB_COOLDOWN = 0.18
LADDER_SIDE_STEP_SPEED = RUN_SPEED * 0.75

# ── Reward loop — Delivery v2 I.2 tunables ──────────────────────────────────
CHIP_CHAIN_WINDOW  = 1.5     # s between chips to keep a chain alive
CHIP_CHAIN_MAX     = 5       # chain multiplier cap (×1..×5)
PUNCTUALITY_BONUS  = 1500    # credits for beating total par (never affects stars)
STAR3_CHIP_PCT     = 0.75    # chip collection needed for 3★ (with ≤1 hit)
STAR2_CHIP_PCT     = 0.40    # chip collection needed for 2★

# ── Levels — Delivery v2 I.3 tunables ───────────────────────────────────────
POWERUP_DURATION   = {"magboots": 12.0, "stimsoles": 10.0}  # hardhat: until hit
MAGBOOT_RADIUS     = 96.0    # px — chips inside drift toward the courier
MAGBOOT_PULL       = 260.0   # px/s chip drift speed
STIM_SPEED_MULT    = 1.25    # stimsoles speed cap multiplier
STIM_JUMP_MULT     = 1.12    # stimsoles jump velocity multiplier
LONG_RUN_MAX_HITS  = 5       # hit budget for corridors of 6+ rooms (I.3.5)
CHASE_CRUSH_T      = 0.45    # s pinned on the chase wall before it costs a hit

STAR_3_TIME = 18.0
STAR_2_TIME = 28.0
MAX_HITS    = 3

_PLAYER_X_FIXED = 100


# ---------------------------------------------------------------------------
# Inline NPC dialog
# ---------------------------------------------------------------------------

class _CorridorDialog:
    """Small text dialog rendered over the corridor mid-run."""

    DIALOG_W = CORRIDOR_W - 40
    DIALOG_H = 120

    def __init__(self, encounter: NPCEncounter):
        self._enc     = encounter
        self._input   = ""
        self._result  = None     # None | (credits, lore, outcome_str)
        self._show_t  = 0.0      # seconds to show result before closing
        self._done    = False
        self.credits  = 0
        self.lore     = ""

    @property
    def is_done(self) -> bool:
        return self._done

    def handle_key(self, event: pygame.event.Event) -> None:
        if self._result is not None:
            return
        # Aliveness A.6 — ESC bails the dialog with a 'penalty' outcome so
        # the player is never modal-locked. Without this the Ch.3 Paperwork
        # corridor's clerk encounter wedged input (no movement, no pause,
        # no escape) when the dialog overlay was missed.
        if event.key == pygame.K_ESCAPE:
            self._abort()
            return
        if event.key == pygame.K_RETURN:
            self._submit()
        elif event.key == pygame.K_BACKSPACE:
            self._input = self._input[:-1]
        elif event.unicode and event.unicode.isprintable():
            if len(self._input) < 40:
                self._input += event.unicode

    def _abort(self):
        """Player pressed ESC — bail with the dialog's `penalty` response
        (or a synthesised one if the encounter doesn't define one)."""
        penalty_match = next(
            (r for r in self._enc.responses
             if r.get("outcome") == "penalty"),
            None,
        )
        if penalty_match is None:
            penalty_match = {
                "credits": 0,
                "lore": "Skipped. Clerk files a complaint.",
                "outcome": "penalty",
            }
        self.credits = int(penalty_match.get("credits", 0))
        self.lore    = penalty_match.get("lore", "")
        outcome      = penalty_match.get("outcome", "penalty")
        self._result = (self.credits, self.lore, outcome)
        self._show_t = 1.5
        self._enc.complete()

    def _submit(self):
        text_lower = self._input.lower()
        matched = None
        for resp in self._enc.responses:
            for kw in resp.get("keywords", []):
                if kw.lower() in text_lower:
                    matched = resp
                    break
            if matched:
                break
        if matched is None:
            # Default fallback (last entry with empty keywords, or first entry)
            matched = next(
                (r for r in self._enc.responses if not r.get("keywords")),
                self._enc.responses[0]
            )
        self.credits     = matched.get("credits", 0)
        self.lore        = matched.get("lore", "")
        outcome          = matched.get("outcome", "pass")
        self._result     = (self.credits, self.lore, outcome)
        self._show_t     = 2.0
        self._enc.complete()

    def update(self, dt: float) -> None:
        if self._result is not None:
            self._show_t -= dt
            if self._show_t <= 0:
                self._done = True

    def draw(self, surf: pygame.Surface, t: float) -> None:
        dx = (CORRIDOR_W - self.DIALOG_W) // 2
        dy = (CORRIDOR_H - self.DIALOG_H) // 2

        # Background
        bg = pygame.Surface((self.DIALOG_W, self.DIALOG_H), pygame.SRCALPHA)
        bg.fill((0, 10, 6, 210))
        surf.blit(bg, (dx, dy))
        pygame.draw.rect(surf, (0, 200, 100),
                         (dx, dy, self.DIALOG_W, self.DIALOG_H), 2)

        f_name  = get_font(11, bold=True)
        f_text  = get_font(10)
        f_input = get_font(11)

        # NPC name header
        ns = f_name.render(f"[ {self._enc.npc_name} ]", True, (0, 230, 110))
        surf.blit(ns, (dx + 8, dy + 8))

        pygame.draw.line(surf, (0, 120, 60),
                         (dx + 4, dy + 24), (dx + self.DIALOG_W - 4, dy + 24), 1)

        if self._result is None:
            # Show prompt
            prompt_lines = _wrap(self._enc.prompt, self.DIALOG_W - 16, f_text)
            for i, line in enumerate(prompt_lines[:3]):
                ps = f_text.render(line, True, (160, 200, 160))
                surf.blit(ps, (dx + 8, dy + 30 + i * 14))

            # Input line
            pygame.draw.line(surf, (0, 160, 80),
                             (dx + 8, dy + self.DIALOG_H - 30),
                             (dx + self.DIALOG_W - 8, dy + self.DIALOG_H - 30), 1)
            cursor = "█" if int(t * 3) % 2 == 0 else " "
            is2 = f_input.render(f"> {self._input}{cursor}", True, (0, 255, 140))
            surf.blit(is2, (dx + 8, dy + self.DIALOG_H - 24))
            # Aliveness A.6 — visible escape hatch so the player never
            # gets modal-locked in a corridor dialog again.
            hint = get_font(8).render(
                "ENTER submit · BACKSPACE delete · ESC skip (penalty)",
                True, (90, 140, 100))
            surf.blit(hint, (dx + 8, dy + self.DIALOG_H - 10))
        else:
            credits, lore, outcome = self._result
            out_col = {
                "reward": (0, 255, 140), "penalty": (255, 80, 80),
                "paradox": (200, 80, 255),
            }.get(outcome, (160, 200, 160))
            rs = f_name.render(
                f"+{credits} cr" if credits > 0 else outcome.upper(),
                True, out_col)
            surf.blit(rs, (dx + self.DIALOG_W // 2 - rs.get_width() // 2,
                           dy + self.DIALOG_H // 2 - 12))
            if lore:
                ls = f_text.render(lore[:48], True, (120, 160, 120))
                surf.blit(ls, (dx + 8, dy + self.DIALOG_H // 2 + 10))


def _wrap(text: str, max_w: int, font: pygame.font.Font) -> list[str]:
    words = text.split()
    lines, cur = [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if font.size(test)[0] <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


# ---------------------------------------------------------------------------
# Room
# ---------------------------------------------------------------------------

class Room:
    """One scrolling section of a corridor."""

    def __init__(self, length: int, palette: dict, elements: list,
                 bg_draw_fn=None,
                 branch_x: float | None = None,
                 converge_x: float | None = None,
                 star3_t: float = STAR_3_TIME,
                 star2_t: float = STAR_2_TIME,
                 bax_enter_line: str = "",
                 bax_boss_line: str = "",
                 name: str = "",
                 auto_scroll: float = 0.0):
        self.length        = length
        self.palette       = palette
        self.elements      = elements
        self.bg_draw_fn    = bg_draw_fn   # fn(surf, camera_x, t, palette)
        self.branch_x      = branch_x     # x where path forks
        self.converge_x    = converge_x   # x where paths merge
        self.star3_t       = star3_t
        self.star2_t       = star2_t
        self.bax_enter_line = bax_enter_line
        self.bax_boss_line  = bax_boss_line
        self.name           = name
        # Delivery v2 I.3.4 — px/s the camera sweeps on its own. >0 makes
        # this a chase room: the left edge pushes, being pinned costs a hit.
        self.auto_scroll    = auto_scroll


# ---------------------------------------------------------------------------
# Corridor
# ---------------------------------------------------------------------------

class Corridor:
    """
    Multi-room delivery corridor.
    Drop-in replacement for DeliveryRun (same external API).
    """

    def __init__(self, chapter: int, rooms: list[Room],
                 cargo_silhouette: str = "box",
                 cargo=None,
                 force_time_pressure: bool = False):
        self.chapter          = chapter
        self.rooms            = rooms
        self.cargo_silhouette = cargo_silhouette  # "box"|"archive"|"shroom"|"forms"|"vip"
        # Aliveness G.9 / G.10 — cargo mutator
        self._mutator: CorridorMutator = get_corridor_mutator(
            cargo, force_time_pressure=force_time_pressure
        )

        # Player state
        self._px        = 120.0
        self._py        = float(FLOOR_Y - PLAYER_H)
        self._pvx       = 0.0
        self._pvy       = 0.0
        self._grounded  = True
        self._on_ladder  = False
        self._ladder_release_t = 0.0
        self._cam_x     = 0.0

        # Delivery v2 I.1 — movement feel state
        self._coyote_t       = 0.0     # >0: may still jump after leaving ground
        self._jump_buf_t     = 0.0     # >0: a jump press is waiting for ground
        self._jump_held      = False   # polled each frame for variable height
        self._sprint_charge  = 0.0     # 0..1 — earned by sustained ground run
        self._sprint_locked  = False   # latch for the sprint-lock event/burst
        self._skid_t         = 0.0     # >0: currently skidding out of a turn
        self._facing         = 1
        self._walk_phase     = 0.0     # leg-cycle phase, advances with |vx|
        self._land_squash_t  = 0.0     # >0: landing squash animation
        self._jump_stretch_t = 0.0     # >0: take-off stretch animation
        self._victory        = False   # finished — victory pose
        self._dust: list[list[float]] = []   # [x, y, vx, vy, life, size]

        # Run state
        self._room_idx  = 0
        self._elapsed   = 0.0
        self._hits      = 0
        self._stun_t    = 0.0
        self._credits   = 0

        # Branching
        self._active_path: str | None = None  # None | "high" | "low"
        self._at_branch: bool = False

        # Checkpoints
        self._cp_px     = 60.0
        self._cp_py     = float(FLOOR_Y - PLAYER_H)

        # Chapter 2 spore inversion
        self._invert_t  = 0.0

        # Room transitions
        self._wipe_t    = 0.0   # >0 = black wipe in progress
        self._wipe_dir  = 1     # 1=entering, -1=exiting
        self._transition_pending = False
        self._transition_caption = ""  # "ENTERING: <room name>" shown over wipe
        self._transition_subcaption = ""  # I.2.4 — per-room chip tally line

        # NPC dialog
        self._dialog: _CorridorDialog | None = None

        # Near-end spoken flags
        self._mid1_spoken = False
        self._mid2_spoken = False
        self._near_end_spoken = False

        # Result
        self._done      = False
        self._stars     = 0
        self._collectibles_found = 0
        self._secrets_found      = 0
        self._collectibles_total = sum(
            sum(1 for el in r.elements if isinstance(el, Collectible))
            for r in rooms
        )
        self._secrets_total = sum(
            sum(1 for el in r.elements if isinstance(el, Secret))
            for r in rooms
        )

        # Delivery v2 I.2 — reward loop state
        self._chain      = 0          # current chip chain (×multiplier)
        self._chain_t    = 0.0        # window remaining to extend the chain
        self._best_chain = 0
        self._floaters: list[list] = []   # [x, y, text, life, (r,g,b)]
        self._room_chip_total = [
            sum(1 for el in r.elements if isinstance(el, Collectible))
            for r in rooms
        ]
        self._room_chip_got = [0] * len(rooms)
        self._par_total  = sum(r.star3_t for r in rooms)
        self._punctual   = False
        self._tally_t    = 0.0        # drives the staged tally screen
        self._tally_schedule: list[tuple[float, str]] = []
        self._tally_done_t = 0.0      # when the last tally stage lands
        self._tally_chip_shown = 0    # chips counted up so far (for ticks)
        self._stars_shown  = 0
        self._bax_graded   = False
        self.meta = None              # attached by make_corridor (I.2.5)

        # Delivery v2 I.3 — power-ups, chase camera, hit budget
        self._power_kind: str | None = None
        self._power_t    = 0.0        # remaining (hardhat ignores this)
        self._ground_el  = None       # element we grounded on this frame
        self._cut_exempt = False      # rising from a spring, not a jump
        self._chase_cam  = 0.0        # auto-scroll camera x (chase rooms)
        self._chase_crush_t = 0.0     # time pinned against the chase wall
        self.max_hits = LONG_RUN_MAX_HITS if len(rooms) >= 6 else MAX_HITS

        # Ambient run Bax commentary timer
        self._run_speak_t = 10.0   # fire first corridor-run line after 10s
        self._result_t  = 0.0
        self._result_credits = 0

        # Surface
        self._surf = pygame.Surface((CORRIDOR_W, CORRIDOR_H))

        # Fire entry Bax line for Room 0
        self._fire_room_enter(0)

        # Epic 4.6 — corridor music: signal entry so the audio manager can
        # swell the chapter signature loop in.
        self._boss_room_emitted = False
        self._exit_emitted      = False
        bus.emit(EVT_CORRIDOR_ENTER, chapter=self.chapter)

    # ── Public API ───────────────────────────────────────────────────────

    def handle_key(self, event: pygame.event.Event) -> None:
        if self._dialog is not None:
            self._dialog.handle_key(event)
            return
        if self._done:
            # Tally screen: first press fast-forwards the count-up,
            # second press hands the cargo off (ends the corridor).
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                if self._tally_t < self._tally_done_t:
                    self._skip_tally()
                else:
                    self._result_t = 0.0
            return
        if event.key in (pygame.K_SPACE, pygame.K_w, pygame.K_UP):
            if self._on_ladder and event.key == pygame.K_SPACE:
                # Jump off ladder mid-way
                self._pvy       = JUMP_VY * 0.75
                self._grounded  = False
                self._jump_stretch_t = 0.10
                self._release_ladder()
                bus.emit(EVT_CORRIDOR_JUMP)
            elif not self._on_ladder:
                # Delivery v2 I.1.2 — buffered jump: remember the press and
                # let _try_jump honour ground OR coyote grace.
                self._jump_buf_t = JUMP_BUFFER
                self._try_jump()
        elif event.key in (pygame.K_s, pygame.K_DOWN):
            # I.3.2 — standing on a warp pipe? DOWN takes it.
            room = self.rooms[self._room_idx]
            for el in room.elements:
                if isinstance(el, WarpPipe) and el.can_enter(
                        self._px, self._py, self._grounded):
                    self._spawn_dust(self._px, self._py + PLAYER_H, n=6,
                                     spread=50.0, color=(80, 210, 110))
                    self._px  = el.exit_x
                    self._py  = float(FLOOR_Y - PLAYER_H)
                    self._pvx = 0.0
                    self._pvy = 0.0
                    self._cam_x = self._px - _PLAYER_X_FIXED
                    self._spawn_dust(self._px, self._py + PLAYER_H, n=6,
                                     spread=50.0, color=(80, 210, 110))
                    bus.emit(EVT_CORRIDOR_PIPE)
                    break
            # (ladder descend stays a held-key behaviour)
        elif event.key in (pygame.K_e, pygame.K_RETURN):
            # Aliveness G.7 — try to activate any nearby NPCShortcut
            room = self.rooms[self._room_idx]
            for el in room.elements:
                if isinstance(el, NPCShortcut):
                    el.try_activate(self._px, self._credits)

    def update(self, dt: float) -> None:
        if self._wipe_t > 0:
            self._wipe_t -= dt
            if self._wipe_t <= 0:
                if self._transition_pending:
                    self._do_room_transition()
                else:
                    self._transition_caption = ""
            return

        if self._dialog is not None:
            self._dialog.update(dt)
            if self._dialog.is_done:
                self._credits += self._dialog.credits
                if self._dialog.lore:
                    bus.emit(EVT_BAX_SPEAK, line=self._dialog.lore[:60])
                self._dialog = None
            return

        if self._done:
            self._result_t = max(0.0, self._result_t - dt)
            self._advance_tally(dt)
            return

        self._elapsed      += dt
        self._stun_t        = max(0.0, self._stun_t - dt)
        self._invert_t      = max(0.0, self._invert_t - dt)
        self._ladder_release_t = max(0.0, self._ladder_release_t - dt)

        # Delivery v2 I.1 — feel timers + dust particles
        self._jump_buf_t     = max(0.0, self._jump_buf_t - dt)
        self._land_squash_t  = max(0.0, self._land_squash_t - dt)
        self._jump_stretch_t = max(0.0, self._jump_stretch_t - dt)
        if self._dust:
            for d in self._dust:
                d[0] += d[2] * dt
                d[1] += d[3] * dt
                d[3] += 300.0 * dt
                d[4] -= dt
            self._dust = [d for d in self._dust if d[4] > 0]

        # Delivery v2 I.2 — chip chain window + floating pickup text
        if self._chain_t > 0:
            self._chain_t = max(0.0, self._chain_t - dt)
            if self._chain_t <= 0:
                self._chain = 0
        if self._floaters:
            for fl in self._floaters:
                fl[1] -= 34.0 * dt
                fl[3] -= dt
            self._floaters = [fl for fl in self._floaters if fl[3] > 0]

        # Delivery v2 I.3.3 — power-up lifecycle + Mag-Boots chip magnet
        if self._power_kind in POWERUP_DURATION:
            self._power_t -= dt
            if self._power_t <= 0:
                self._end_power("expired")
        if self._power_kind == "magboots":
            cur_room = self.rooms[self._room_idx]
            for el in self._visible_elements(cur_room):
                if isinstance(el, Collectible) and not el._collected:
                    dx = self._px - el.x
                    dy = (self._py + PLAYER_H / 2) - el.y
                    d2 = dx * dx + dy * dy
                    if d2 < MAGBOOT_RADIUS * MAGBOOT_RADIUS and d2 > 1.0:
                        d = d2 ** 0.5
                        el.x += (dx / d) * MAGBOOT_PULL * dt
                        el.y += (dy / d) * MAGBOOT_PULL * dt
        self._run_speak_t  -= dt
        if self._run_speak_t <= 0:
            self._run_speak_t = 12.0
            bus.emit(EVT_CORRIDOR_RUN)

        # Aliveness G.9 / G.10 — mutator update
        self._mutator.update(dt, self._elapsed)

        # Aliveness G.10 — time pressure expiry = forced death
        from delivery.corridor.mutators import TimePressureMutator
        if isinstance(self._mutator, TimePressureMutator) and self._mutator.is_expired():
            self._take_hit()

        keys = pygame.key.get_pressed()
        room = self.rooms[self._room_idx]

        climb_up = keys[pygame.K_UP] or keys[pygame.K_w]
        climb_down = keys[pygame.K_DOWN] or keys[pygame.K_s]
        wants_ladder = climb_up or climb_down

        # Player-controlled forward movement (D/RIGHT = run, A/LEFT = retreat)
        # Controls invert when spore-zone is active (Ch.2 mechanic)
        inverted = self._invert_t > 0
        move_fwd = keys[pygame.K_d] or keys[pygame.K_RIGHT]
        move_bck = keys[pygame.K_a] or keys[pygame.K_LEFT]
        if inverted:
            move_fwd, move_bck = move_bck, move_fwd

        # Jump key polled every frame for variable jump height (I.1.2)
        self._jump_held = bool(keys[pygame.K_SPACE] or keys[pygame.K_w]
                               or keys[pygame.K_UP])

        # Ladder check
        ladder = self._active_ladder(wants_ladder, climb_down)
        self._on_ladder = ladder is not None and (self._on_ladder or wants_ladder)

        if self._on_ladder:
            self._pvy = 0.0
            self._pvx = 0.0
            self._coyote_t = 0.0
            self._skid_t   = 0.0
            if climb_up:
                self._py  -= CLIMB_SPD * dt
            if climb_down:
                self._py  += CLIMB_SPD * dt
            if move_fwd:
                self._px += LADDER_SIDE_STEP_SPEED * dt
            elif move_bck:
                min_x = self._cam_x + _PLAYER_X_FIXED * 0.5
                self._px = max(min_x, self._px - LADDER_SIDE_STEP_SPEED * dt)

            # Dismount at top: step off onto the surface above the ladder
            if self._py + PLAYER_H <= ladder.y_top:
                self._py        = ladder.y_top - PLAYER_H
                self._pvy       = 0.0
                self._grounded  = True
                self._release_ladder()
            # Dismount at bottom: drop to floor
            elif self._py >= ladder.y_bot - PLAYER_H:
                self._py        = float(FLOOR_Y - PLAYER_H)
                self._pvy       = 0.0
                self._grounded  = True
                self._release_ladder()
            elif not ladder.overlaps(self._px, self._py):
                self._pvy       = 0.0
                self._grounded  = False
                self._release_ladder()
            else:
                if not (move_fwd or move_bck):
                    self._px   = ladder.x
                self._grounded = False
        else:
            # Branch choice at branch point
            if (room.branch_x is not None
                    and abs(self._px - room.branch_x) < 30
                    and self._active_path is None):
                if climb_up:
                    self._active_path = "high"
                else:
                    self._active_path = "low"

            # ── Delivery v2 I.1.1 — momentum movement ────────────────────
            axis = (1 if move_fwd else 0) - (1 if move_bck else 0)

            # Sprint charge is earned by sustained forward ground running
            # with the sprint key held; airborne time keeps it (jumps don't
            # break P-speed), anything else bleeds it off fast.
            sprint_held = (keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
                           or keys[pygame.K_x])
            if sprint_held and axis > 0 and self._grounded:
                self._sprint_charge = min(
                    1.0, self._sprint_charge + dt / SPRINT_CHARGE_T)
            elif axis > 0 and not self._grounded:
                pass
            else:
                self._sprint_charge = max(0.0, self._sprint_charge - dt * 2.5)
            if self._sprint_charge >= 1.0 and not self._sprint_locked:
                self._sprint_locked = True
                self._spawn_dust(self._px - 8, self._py + PLAYER_H,
                                 n=6, spread=90.0)
                bus.emit(EVT_CORRIDOR_SPRINT)
            elif self._sprint_charge < 0.5:
                self._sprint_locked = False

            # Forward may sprint; retreat stays capped (forward-biased level)
            if axis > 0:
                top = WALK_SPEED + (SPRINT_SPEED - WALK_SPEED) * self._sprint_charge
            else:
                top = WALK_SPEED * RETREAT_FACTOR
            if self._power_kind == "stimsoles":
                top *= STIM_SPEED_MULT      # I.3.3
            target_vx = axis * top

            # Skid: reversing against real speed on the ground
            if (self._grounded and axis != 0
                    and axis * self._pvx < 0
                    and abs(self._pvx) > SKID_MIN_SPEED
                    and self._skid_t <= 0):
                self._skid_t = 0.14
                self._spawn_dust(self._px + (6 if self._pvx > 0 else -6),
                                 self._py + PLAYER_H, n=5, spread=70.0)
                bus.emit(EVT_CORRIDOR_SKID)
            self._skid_t = max(0.0, self._skid_t - dt)

            if self._skid_t > 0:
                accel = SKID_DECEL
            elif axis != 0:
                accel = GROUND_ACCEL
            else:
                accel = GROUND_DECEL
            if not self._grounded:
                accel *= AIR_CONTROL
            if self._pvx < target_vx:
                self._pvx = min(target_vx, self._pvx + accel * dt)
            elif self._pvx > target_vx:
                self._pvx = max(target_vx, self._pvx - accel * dt)
            if abs(self._pvx) > 2.0:
                self._facing = 1 if self._pvx > 0 else -1

            if abs(self._pvx) > 0.01:
                proposed = self._px + self._pvx * dt
                # Aliveness A.6 — OneWayWall still constrains movement;
                # a blocked wall also kills momentum. I.3.2 adds solid
                # pipes and breakable crates (sprint shatters them).
                if self._blocked_by_walls(proposed, self._pvx, room):
                    self._pvx = 0.0
                else:
                    # Can retreat only back to the camera left edge
                    min_x = self._cam_x + _PLAYER_X_FIXED * 0.5
                    if proposed < min_x:
                        proposed  = min_x
                        self._pvx = max(0.0, self._pvx)
                    self._px = proposed

            # 0.041 rad/px ≈ the pre-v2 leg cadence at walk speed; sprinting
            # naturally quickens the stride because phase follows |vx|.
            self._walk_phase += abs(self._pvx) * dt * 0.041

            # ── Delivery v2 I.1.2 — jump-feel gravity ────────────────────
            g = GRAVITY
            if self._pvy < 0:
                # Jump-cut only applies to actual jumps: spring launches
                # (I.3.2) rise at full power regardless of the jump key.
                if not self._jump_held and not self._cut_exempt:
                    g *= JUMP_CUT_MULT      # early release cuts the jump
            else:
                g *= FALL_GRAV_MULT         # falls read heavier than rises
                self._cut_exempt = False
            self._pvy += g * dt
            self._py  += self._pvy * dt

            impact_vy    = self._pvy
            was_airborne = not self._grounded

            # I.3.2 — ?-blocks bonk from below while rising
            if self._pvy < 0:
                for el in self._visible_elements(room):
                    if isinstance(el, QuestionBlock):
                        got = el.try_bump(self._px, self._py, self._pvy)
                        if got:
                            self._pvy = 90.0          # head bounce-down
                            self._pop_qblock(el, got, room)
                            break

            # Platform collision (floor first)
            self._grounded  = False
            self._ground_el = None
            if self._py >= FLOOR_Y - PLAYER_H:
                self._py      = float(FLOOR_Y - PLAYER_H)
                self._pvy     = 0.0
                self._grounded = True
            if self._py < CEIL_Y + 2:
                self._py  = float(CEIL_Y + 2)
                self._pvy = max(0.0, self._pvy)

            # I.3.2 — springs launch before anything grounds you
            if self._pvy >= 0:
                for el in self._visible_elements(room):
                    if isinstance(el, Spring) and el.try_bounce(
                            self._px, self._py, self._pvy):
                        self._py  = el.y - PLAYER_H
                        self._pvy = Spring.LAUNCH_VY
                        self._cut_exempt = True
                        self._jump_stretch_t = 0.12
                        self._spawn_dust(self._px, el.y, n=5, spread=70.0)
                        bus.emit(EVT_CORRIDOR_SPRING)
                        break

            # Platform elements
            for el in self._visible_elements(room):
                if isinstance(el, (Platform, CollapsingPlatform)):
                    if el.collides_top(self._px, self._py, self._pvy):
                        self._py      = el.y - PLAYER_H
                        self._pvy     = 0.0
                        self._grounded = True
                        self._ground_el = el
                        if isinstance(el, CollapsingPlatform):
                            el.step_on()
                elif isinstance(el, (MovingPlatform, TimedLift)):
                    if el.collides_top(self._px, self._py, self._pvy):
                        self._py      = el.y - PLAYER_H
                        self._pvy     = 0.0
                        self._grounded = True
                        self._ground_el = el
                elif isinstance(el, WarpPipe):
                    if el.collides_top(self._px, self._py, self._pvy):
                        self._py      = el.y_top - PLAYER_H
                        self._pvy     = 0.0
                        self._grounded = True
                        self._ground_el = el

            # I.3.2 — conveyor belts drag whoever stands on them
            if isinstance(self._ground_el, ConveyorBelt):
                drifted = self._px + self._ground_el.drift * dt
                if not self._blocked_by_walls(drifted, self._ground_el.drift,
                                              room):
                    min_x = self._cam_x + _PLAYER_X_FIXED * 0.5
                    self._px = max(min_x, drifted)

            # ── Delivery v2 I.1.2 — landing, coyote, buffered jump ───────
            if self._grounded:
                self._coyote_t = COYOTE_TIME
                if was_airborne:
                    if impact_vy > LAND_SFX_VY:
                        self._land_squash_t = 0.12
                        self._spawn_dust(
                            self._px, self._py + PLAYER_H,
                            n=4 + min(4, int(impact_vy / 200)), spread=60.0)
                        bus.emit(EVT_CORRIDOR_LAND, impact=impact_vy)
                    if self._jump_buf_t > 0:
                        self._try_jump()
            else:
                self._coyote_t = max(0.0, self._coyote_t - dt)

        # Camera — chase rooms sweep on their own (I.3.4)
        if room.auto_scroll > 0 and not self._done:
            self._chase_cam += room.auto_scroll * dt
            self._cam_x = max(self._px - _PLAYER_X_FIXED, self._chase_cam)
            # Can't outrun the sweep's right edge
            max_px = self._cam_x + CORRIDOR_W - 60
            if self._px > max_px:
                self._px = max_px
            # Pinned against the sweep wall = crushed
            wall_x = self._cam_x + 10
            if self._px < wall_x:
                self._px = wall_x
                self._chase_crush_t += dt
                if self._chase_crush_t >= CHASE_CRUSH_T and self._stun_t <= 0:
                    self._chase_crush_t = 0.0
                    self._take_hit()
                    self._px = wall_x + 70.0   # shoved clear
            else:
                self._chase_crush_t = 0.0
        else:
            self._cam_x = self._px - _PLAYER_X_FIXED

        # Update elements
        for el in room.elements:
            el.update(dt, self._px, self._py)
            # Aliveness G.7 — NPCShortcut teleport request
            if isinstance(el, NPCShortcut) and el.teleport_request is not None:
                self._px = el.teleport_request
                el.teleport_request = None
                self._cam_x = self._px - _PLAYER_X_FIXED

        # Collisions (only if not stunned)
        if self._stun_t <= 0:
            self._check_hazards(room, dt)

        self._check_collectibles(room)
        self._check_npc_encounters(room)
        self._check_checkpoints(room)
        self._check_boss_triggers(room)
        self._check_stealth(room, dt)

        # Spore zones (Chapter 2)
        for el in self._visible_elements(room):
            if isinstance(el, SporeZone) and el.overlaps(self._px):
                if self._invert_t <= 0:
                    self._invert_t = 1.5

        # Mid-run Bax
        prog = self._px / max(1, room.length)
        if not self._mid1_spoken and prog > 0.33:
            self._mid1_spoken = True
            bus.emit(EVT_BAX_SPEAK, line="Corridor's long. Keep movin'. D/→ to run.")
        if not self._mid2_spoken and prog > 0.66:
            self._mid2_spoken = True
            bus.emit(EVT_BAX_SPEAK, line="Nearly there. Watch the beams. Jump with W.")
        if not self._near_end_spoken and self._px > room.length - 400:
            self._near_end_spoken = True
            bus.emit(EVT_BAX_SPEAK, line="Drop-off's ahead. Don't faceplant at the finish.")

        # Room end
        if self._px >= room.length:
            if self._room_idx >= len(self.rooms) - 1:
                self._finish()
            else:
                self._start_wipe_out()

    def draw(self, screen: pygame.Surface, screen_x: int, screen_y: int) -> None:
        surf = self._surf
        t    = self._elapsed
        room = self.rooms[self._room_idx]
        pal  = room.palette

        # Background
        surf.fill(pal.get("bg", (6, 10, 8)))
        if room.bg_draw_fn:
            room.bg_draw_fn(surf, self._cam_x, t, pal)
        else:
            self._draw_default_bg(surf, t, pal)
        # Epic 10.4 — additive corridor visual layer: cracked / numbered
        # panels, floor wear, drips, deep parallax, directional light.
        # Renders behind everything else but on top of the per-room
        # custom backdrop so chapter art still drives the look.
        self._draw_corridor_decay(surf, t, pal, room)

        # Ceiling + floor
        pygame.draw.rect(surf, pal.get("ceiling_fill", (18, 30, 18)),
                         (0, 0, CORRIDOR_W, CEIL_Y))
        pygame.draw.line(surf, pal.get("ceiling_line", (0, 140, 60)),
                         (0, CEIL_Y), (CORRIDOR_W, CEIL_Y), 2)
        pygame.draw.rect(surf, pal.get("floor_fill", (18, 30, 18)),
                         (0, FLOOR_Y, CORRIDOR_W, CORRIDOR_H - FLOOR_Y))
        brick = pal.get("brick", (100, 50, 20))
        for tx in range(-16, CORRIDOR_W + 16, 16):
            sx = tx - int(self._cam_x * 0.3) % 16
            pygame.draw.rect(surf, brick, (sx, FLOOR_Y + 2, 14, 8))
            pygame.draw.rect(surf, pal.get("brick_hi", brick), (sx, FLOOR_Y + 2, 14, 3))
        pygame.draw.line(surf, pal.get("floor_line", (0, 140, 60)),
                         (0, FLOOR_Y), (CORRIDOR_W, FLOOR_Y), 3)

        # Elements
        for el in room.elements:
            if not el.active:
                continue
            if el.path_tag and self._active_path and el.path_tag != self._active_path:
                continue
            sx = el.x - self._cam_x
            if -200 < sx < CORRIDOR_W + 200:
                el.draw(surf, self._cam_x, t, pal)

        # Branch prompt
        if (room.branch_x is not None
                and abs(self._px - room.branch_x) < 80
                and self._active_path is None):
            f = get_font(10)
            s = f.render("W/↑ = HIGH PATH  ·  keep running = LOW PATH",
                         True, (200, 200, 0))
            surf.blit(s, (CORRIDOR_W // 2 - s.get_width() // 2, CEIL_Y + 8))

        # Player
        self._draw_player(surf, t)

        # NPC dialog overlay
        if self._dialog is not None:
            self._dialog.draw(surf, t)

        # HUD
        self._draw_hud(surf, t, room)

        # Result overlay
        if self._done:
            self._draw_result(surf)

        # Black wipe
        if self._wipe_t > 0:
            alpha = int(255 * (1.0 - self._wipe_t / 0.5)) \
                    if self._wipe_dir == 1 else int(255 * (self._wipe_t / 0.5))
            alpha = max(0, min(255, alpha))
            ov = pygame.Surface((CORRIDOR_W, CORRIDOR_H))
            ov.fill((0, 0, 0))
            ov.set_alpha(alpha)
            surf.blit(ov, (0, 0))
            # Caption — visible as screen fades back in (dir=1); fades with overlay
            if self._transition_caption and alpha > 0:
                fc = get_font(14, bold=True)
                cs = fc.render(self._transition_caption, True, (0, 220, 100))
                cap = pygame.Surface(cs.get_size(), pygame.SRCALPHA)
                cap.blit(cs, (0, 0))
                cap.set_alpha(alpha)
                surf.blit(cap, (CORRIDOR_W // 2 - cs.get_width() // 2,
                                CORRIDOR_H // 2 - cs.get_height() // 2))
                # I.2.4 — per-room chip tally under the room name
                if self._transition_subcaption:
                    fs2 = get_font(11)
                    gold = (255, 210, 60) if "SWEEP" in self._transition_subcaption \
                           else (170, 150, 90)
                    ss = fs2.render(self._transition_subcaption, True, gold)
                    sub = pygame.Surface(ss.get_size(), pygame.SRCALPHA)
                    sub.blit(ss, (0, 0))
                    sub.set_alpha(alpha)
                    surf.blit(sub, (CORRIDOR_W // 2 - ss.get_width() // 2,
                                    CORRIDOR_H // 2 + cs.get_height() // 2 + 4))

        # Aliveness G.9 / G.10 — mutator overlay (drawn last, on top of everything)
        self._mutator.draw_overlay(surf, t, self._cam_x, self._px, self._py)

        if screen is not None:
            screen.blit(surf, (screen_x, screen_y))

    # ── Properties ──────────────────────────────────────────────────────

    @property
    def is_done(self) -> bool:
        return self._done and self._result_t <= 0

    @property
    def stars(self) -> int:
        return self._stars

    @property
    def credits_earned(self) -> int:
        return self._credits

    def get_surface(self) -> pygame.Surface:
        """Return the internally rendered corridor surface (before screen blit)."""
        return self._surf

    # ── Internal helpers ────────────────────────────────────────────────

    def _visible_elements(self, room: Room):
        for el in room.elements:
            if not el.active:
                continue
            if el.path_tag and self._active_path and el.path_tag != self._active_path:
                continue
            yield el

    def _release_ladder(self) -> None:
        self._on_ladder = False
        self._ladder_release_t = LADDER_REGRAB_COOLDOWN

    def _active_ladder(self, wants_ladder: bool = True, climb_down: bool = False):
        if self._ladder_release_t > 0:
            return None
        room = self.rooms[self._room_idx]
        for el in self._visible_elements(room):
            if isinstance(el, Ladder) and el.overlaps(self._px, self._py):
                if self._on_ladder:
                    return el
                if not wants_ladder:
                    continue
                at_bottom = self._py >= el.y_bot - PLAYER_H - 2
                if at_bottom and climb_down:
                    continue
                return el
        return None

    def _check_hazards(self, room: Room, dt: float):
        for el in self._visible_elements(room):
            hit = False
            if isinstance(el, Hazard):
                hit = el.collides(self._px, self._py)
            elif isinstance(el, MovingHazard):
                hit = el.collides(self._px, self._py)
            elif isinstance(el, ToggleBeam):
                hit = el.collides(self._px, self._py, self._elapsed)
            elif isinstance(el, SteamVent):
                hit = el.collides(self._px, self._py)
            elif isinstance(el, SecurityBeam):
                hit = el.collides(self._px, self._py, self._elapsed)
            elif isinstance(el, Tripwire):
                if el.collides(self._px, self._py):
                    # Tripwire: alarm only, not damage. Trigger and continue.
                    el.trigger()
                    continue
            if hit:
                self._take_hit()
                break

    def _check_collectibles(self, room: Room):
        for el in self._visible_elements(room):
            if isinstance(el, Collectible):
                v = el.try_collect(self._px, self._py)
                if v:
                    # I.2.3 — chips inside the window build a ×1→×5 chain
                    if self._chain_t > 0:
                        self._chain = min(CHIP_CHAIN_MAX, self._chain + 1)
                    else:
                        self._chain = 1
                    self._chain_t    = CHIP_CHAIN_WINDOW
                    self._best_chain = max(self._best_chain, self._chain)
                    gained = v * self._chain
                    self._credits += gained
                    self._collectibles_found += 1
                    self._room_chip_got[self._room_idx] += 1
                    # I.2.2 — pickup pop: floating value + gold sparkle
                    txt = f"+{gained}"
                    if self._chain > 1:
                        txt += f" ×{self._chain}"
                    self._floaters.append(
                        [el.x, el.y - 12, txt, 0.8, (255, 220, 60)])
                    self._spawn_dust(el.x, el.y, n=4, spread=50.0,
                                     color=(255, 210, 40))
                    bus.emit(EVT_CORRIDOR_CHIP, chain=self._chain)
            elif isinstance(el, Secret):
                v, lore = el.try_collect(self._px, self._py)
                if v or lore:
                    self._credits += v
                    self._secrets_found += 1
                    self._floaters.append(
                        [el.x, el.y - 14, "SECRET!", 1.1, (0, 230, 210)])
                    bus.emit(EVT_CORRIDOR_SECRET)
                    if lore:
                        bus.emit(EVT_BAX_SPEAK, line=lore[:60])
                        # Epic 8.3 — persist for Bax's Records, Tab 4.
                        bus.emit(EVT_LORE_FOUND, text=lore, chapter=self.chapter)
            elif isinstance(el, PowerUp):
                kind = el.try_collect(self._px, self._py)
                if kind:
                    self._grant_power(kind)

    def _blocked_by_oneway(self, proposed_px: float, vx: float, room: Room) -> bool:
        """Aliveness A.6 — true if a `OneWayWall` element would block the
        player at the proposed position with the given velocity sign.

        Walls only block when the player would enter their disallowed side,
        so re-tracing the same wall in the reverse direction stays free."""
        for el in self._visible_elements(room):
            if isinstance(el, OneWayWall):
                if el.blocks(proposed_px, self._py, vx):
                    return True
        return False

    def _blocked_by_walls(self, proposed_px: float, vx: float, room: Room) -> bool:
        """I.3.2 — combined wall check: one-way walls, solid pipes, and
        breakable crates. Sprint speed shatters crates instead of stopping."""
        if self._blocked_by_oneway(proposed_px, vx, room):
            return True
        for el in self._visible_elements(room):
            if isinstance(el, BreakableBlock) and el.blocks(proposed_px, self._py):
                if el.try_break(vx):
                    self._spawn_dust(el.x, el.y_top + el.H // 2, n=10,
                                     spread=140.0, color=(200, 150, 80))
                    # Crates scatter chips forward — they join the room live
                    for i in range(el.chips):
                        room.elements.append(Collectible(
                            el.x + 34 + i * 30, FLOOR_Y - 18, value=200))
                        self._collectibles_total += 1
                        self._room_chip_total[self._room_idx] += 1
                    bus.emit(EVT_CORRIDOR_BREAK)
                    continue        # shattered — no block
                return True
            if isinstance(el, WarpPipe) and el.blocks(proposed_px, self._py):
                return True
        return False

    def _check_npc_encounters(self, room: Room):
        if self._dialog is not None:
            return
        # Aliveness A.6 — defer NPC dialog until courier is grounded.
        # Ch.3 Paperwork repro: ladder + clerk trigger overlapped and the
        # player got a modal dialog while still climbing, with no clean
        # way to dismiss it. Wait for grounded so the player has a clear
        # 'I just walked into this' moment.
        if self._on_ladder or not self._grounded:
            return
        for el in self._visible_elements(room):
            if isinstance(el, NPCEncounter):
                if el.collides_trigger(self._px) and not el._triggered:
                    el.trigger()
                    self._dialog = _CorridorDialog(el)
                    break

    def _check_checkpoints(self, room: Room):
        for el in self._visible_elements(room):
            if isinstance(el, Checkpoint):
                if el.check_pass(self._px):
                    self._cp_px = self._px
                    self._cp_py = self._py
                    # I.3.5 — checkpoints patch one hit on the way past
                    if self._hits > 0:
                        self._hits -= 1
                        self._floaters.append(
                            [self._px, self._py - 18, "HIT PATCHED", 1.0,
                             (0, 220, 120)])

    def _check_boss_triggers(self, room: Room):
        for el in self._visible_elements(room):
            if isinstance(el, BossRoomTrigger):
                if el.check(self._px):
                    if el.bax_line:
                        bus.emit(EVT_BAX_SPEAK, line=el.bax_line)
                    # Epic 4.6 — first boss-room trigger this corridor peaks
                    # the chapter signature music. Idempotent per corridor.
                    if not self._boss_room_emitted:
                        self._boss_room_emitted = True
                        bus.emit(EVT_CORRIDOR_BOSS_ROOM, chapter=self.chapter)

    def _check_stealth(self, room: Room, dt: float):
        if self._stun_t > 0:
            return
        for el in self._visible_elements(room):
            if isinstance(el, StealthZone):
                if el.detects(self._px, self._py):
                    self._take_hit()
                    # Retreat to checkpoint
                    self._px  = self._cp_px
                    self._py  = self._cp_py
                    self._pvy = 0.0
                    self._cam_x = self._px - _PLAYER_X_FIXED
                    break

    def _try_jump(self) -> None:
        """Execute a jump if grounded or within coyote grace (I.1.2)."""
        if self._on_ladder or self._done:
            return
        if not (self._grounded or self._coyote_t > 0):
            return
        jump_vy = JUMP_VY
        if self._power_kind == "stimsoles":
            jump_vy *= STIM_JUMP_MULT
        self._pvy        = jump_vy
        self._grounded   = False
        self._coyote_t   = 0.0
        self._jump_buf_t = 0.0
        self._jump_stretch_t = 0.10
        bus.emit(EVT_CORRIDOR_JUMP)

    def _pop_qblock(self, block: QuestionBlock, contains: str,
                    room: Room) -> None:
        """I.3.2 — spawn a bonked ?-block's contents above it."""
        self._spawn_dust(block.x, block.y, n=5, spread=60.0,
                         color=(255, 215, 80))
        bus.emit(EVT_CORRIDOR_QBLOCK, contains=contains)
        if contains == "chips":
            for i in range(block.n_chips):
                off = (i - (block.n_chips - 1) / 2.0) * 26.0
                room.elements.append(Collectible(
                    block.x + off, block.y - 22, value=200))
            self._collectibles_total += block.n_chips
            self._room_chip_total[self._room_idx] += block.n_chips
        elif contains in PowerUp.KINDS:
            room.elements.append(PowerUp(block.x, block.y - 26, contains))

    def _grant_power(self, kind: str) -> None:
        """I.3.3 — pick up a power-up (replaces any current one)."""
        self._power_kind = kind
        self._power_t    = POWERUP_DURATION.get(kind, 0.0)
        label = {"magboots": "MAG-BOOTS!", "hardhat": "HARDHAT!",
                 "stimsoles": "STIM SOLES!"}.get(kind, kind.upper())
        self._floaters.append(
            [self._px, self._py - 18, label, 1.1, (140, 220, 255)])
        bus.emit(EVT_CORRIDOR_POWERUP, kind=kind)

    def _end_power(self, reason: str = "expired") -> None:
        if self._power_kind is None:
            return
        self._power_kind = None
        self._power_t    = 0.0
        bus.emit(EVT_CORRIDOR_POWERDOWN, reason=reason)

    def _spawn_dust(self, x: float, y: float, n: int = 4,
                    spread: float = 60.0,
                    color: tuple | None = None) -> None:
        """Chunky particle puffs at (x, y) world-space. Grey dust for
        landing/skid/sprint; pass a color for pickup sparkles (I.2.2)."""
        for _ in range(n):
            self._dust.append([
                x + random.uniform(-4, 4), y + random.uniform(-2, 0),
                random.uniform(-spread, spread), random.uniform(-70, -20),
                random.uniform(0.18, 0.34), random.uniform(1.5, 3.0),
                color,
            ])

    def _take_hit(self):
        # I.3.3 — a hardhat eats the hit Mario-style: lose the hat, not
        # the hit count. Brief stun still applies so it reads.
        if self._power_kind == "hardhat":
            self._end_power("spent")
            self._stun_t = 0.6
            self._floaters.append(
                [self._px, self._py - 18, "HARDHAT SPENT", 0.9,
                 (255, 205, 40)])
            return
        self._hits    += 1
        self._stun_t   = 1.2
        from core.event_bus import EVT_DELIVERY_HIT
        bus.emit(EVT_DELIVERY_HIT)
        bus.emit(EVT_CORRIDOR_DEATH)

    def _start_wipe_out(self):
        next_idx = self._room_idx + 1
        if next_idx < len(self.rooms):
            n = self.rooms[next_idx].name
            self._transition_caption = f"ENTERING: {n}" if n else f"ENTERING: ROOM {next_idx + 1}"
        else:
            self._transition_caption = ""
        # I.2.4 — room-clear flourish: per-room chip tally on the wipe
        got = self._room_chip_got[self._room_idx]
        tot = self._room_chip_total[self._room_idx]
        if tot > 0:
            self._transition_subcaption = f"CHIPS {got}/{tot}"
            if got >= tot:
                self._transition_subcaption += " — CLEAN SWEEP"
                bus.emit(EVT_BAX_SPEAK,
                         line="Every chip in that room. You SWEPT it. Framing this.")
            elif tot - got >= 2:
                bus.emit(EVT_BAX_SPEAK,
                         line=f"Left {tot - got} chips back there, mate. They don't walk out on their own.")
        else:
            self._transition_subcaption = ""
        self._wipe_t             = 0.5
        self._wipe_dir           = -1   # fade to black
        self._transition_pending = True

    def _do_room_transition(self):
        self._transition_pending = False
        self._room_idx   += 1
        self._px          = 60.0
        self._py          = float(FLOOR_Y - PLAYER_H)
        self._pvy         = 0.0
        self._cam_x       = 0.0
        self._chase_cam   = 0.0      # I.3.4 — chase camera restarts per room
        self._chase_crush_t = 0.0
        self._active_path = None
        self._cp_px       = 60.0
        self._cp_py       = float(FLOOR_Y - PLAYER_H)
        self._mid1_spoken = False
        self._mid2_spoken = False
        self._near_end_spoken = False
        self._fire_room_enter(self._room_idx)
        # Fade back in
        self._wipe_t   = 0.5
        self._wipe_dir = 1

    def _fire_room_enter(self, idx: int):
        if idx < len(self.rooms):
            line = self.rooms[idx].bax_enter_line
            if line:
                bus.emit(EVT_BAX_SPEAK, line=line)

    _BAX_GRADE_LINES = {
        3: ["THREE STARS. The Union'll think I bribed someone.",
            "Full marks, mate! I'd hug ya if I had arms in 'ere.",
            "Swept it CLEAN. That's goin' in me records."],
        2: ["Two stars. Solid. The third one's still back in that corridor.",
            "Decent run! Left a bit of shine behind, mind."],
        1: ["One star. We delivered. That's... technically the job.",
            "Rough one. Cargo's intact, pride's negotiable."],
    }

    def _finish(self):
        self._done = True
        self._victory = True
        bus.emit(EVT_DELIVERY_DONE)
        if not self._exit_emitted:
            self._exit_emitted = True
            bus.emit(EVT_CORRIDOR_EXIT, chapter=self.chapter)

        # I.2.1 — style scoring: exploration and clean play rate the run.
        # Time NEVER rates it (Delivery v2 resolved decision #1).
        total = self._collectibles_total
        pct   = (self._collectibles_found / total) if total else 1.0
        if pct >= STAR3_CHIP_PCT and self._hits <= 1:
            self._stars = 3
        elif pct >= STAR2_CHIP_PCT and self._hits <= self.max_hits:
            self._stars = 2
        else:
            self._stars = 1

        # Par pays credits, not stars.
        self._punctual = self._elapsed <= self._par_total
        if self._punctual:
            self._credits += PUNCTUALITY_BONUS

        # I.2.5 — COURIER'S PRIDE: a perfect sweep (every chip, every
        # secret) stamps the chapter's dossier card permanently.
        if (total > 0 and self._collectibles_found >= total
                and self._secrets_found >= self._secrets_total
                and self.meta is not None
                and hasattr(self.meta, "mark_courier_pride")):
            self.meta.mark_courier_pride(self.chapter)

        self._result_credits = self._credits

        # I.2.1 — tally reveal schedule: one beat per row, DKC-style.
        chips_dur = min(2.2, 0.06 * max(1, self._collectibles_found)) \
                    if total else 0.0
        t0 = 0.6
        marks: list[tuple[str, float]] = [("chips_start", t0)]
        t1 = t0 + chips_dur
        marks.append(("secrets", t1 + 0.35))
        marks.append(("hits",    t1 + 0.70))
        t2 = t1 + 1.05
        if self._punctual:
            marks.append(("punctual", t2))
            t2 += 0.35
        marks.append(("credits", t2))
        for i in range(self._stars):
            marks.append((f"star{i + 1}", t2 + 0.5 + 0.45 * i))
        t_end = t2 + 0.5 + 0.45 * self._stars + 0.3
        marks.append(("bax", t_end))
        self._tally_schedule = marks
        self._tally_done_t   = t_end
        self._tally_t        = 0.0
        self._result_t       = t_end + 3.0   # auto-advance; ENTER skips

    def _mark_t(self, name: str) -> float | None:
        for n, mt in self._tally_schedule:
            if n == name:
                return mt
        return None

    def _advance_tally(self, dt: float) -> None:
        """Step the staged tally reveal; emits tick/star/Bax cues (I.2.1)."""
        prev = self._tally_t
        self._tally_t += dt
        cs = self._mark_t("chips_start")
        if cs is not None and self._tally_t > cs and self._collectibles_total:
            shown = min(self._collectibles_found,
                        int((self._tally_t - cs) / 0.06))
            if shown > self._tally_chip_shown:
                self._tally_chip_shown = shown
                bus.emit(EVT_CORRIDOR_TALLY)
        for name, mt in self._tally_schedule:
            if prev < mt <= self._tally_t:
                if name.startswith("star"):
                    self._stars_shown = min(self._stars, self._stars_shown + 1)
                    bus.emit(EVT_CORRIDOR_STAR)
                elif name in ("secrets", "hits", "punctual", "credits"):
                    bus.emit(EVT_CORRIDOR_TALLY)
                elif name == "bax" and not self._bax_graded:
                    self._bax_graded = True
                    bus.emit(EVT_BAX_SPEAK,
                             line=random.choice(self._BAX_GRADE_LINES[self._stars]))

    def _skip_tally(self) -> None:
        """ENTER during the count-up: reveal everything at once."""
        self._tally_t = self._tally_done_t
        self._tally_chip_shown = self._collectibles_found
        self._stars_shown = self._stars
        if not self._bax_graded:
            self._bax_graded = True
            bus.emit(EVT_BAX_SPEAK,
                     line=random.choice(self._BAX_GRADE_LINES[self._stars]))

    def _draw_default_bg(self, surf, t, pal):
        """Atmospheric sci-fi corridor background with parallax layers."""
        # ── Layer 0: deep background wall panels (slow parallax) ─────────────
        wall_col   = pal.get("wall_panel", (10, 18, 12))
        seam_col   = pal.get("wall_seam",  (0, 60, 30))
        panel_w    = 120
        bg_off     = int(self._cam_x * 0.15) % panel_w
        for px in range(-bg_off, CORRIDOR_W + panel_w, panel_w):
            pygame.draw.rect(surf, wall_col, (px, CEIL_Y, panel_w - 2, FLOOR_Y - CEIL_Y))
            pygame.draw.line(surf, seam_col, (px, CEIL_Y), (px, FLOOR_Y), 1)

        # ── Layer 1: mid-wall pipes and conduit strips (medium parallax) ──────
        pipe_off = int(self._cam_x * 0.35) % 200
        for px in range(-pipe_off, CORRIDOR_W + 200, 200):
            # Main conduit bar
            pygame.draw.rect(surf, pal.get("pipe",  (0, 80, 40)),
                             (px - 4, CEIL_Y + 14, 8, FLOOR_Y - CEIL_Y - 28))
            # Connector rings
            for ry in range(CEIL_Y + 30, FLOOR_Y - 20, 40):
                pygame.draw.rect(surf, pal.get("pipe_ring", (0, 120, 60)),
                                 (px - 6, ry, 12, 6))
            # Status blinker (alternating pipes blink)
            blink_on = int(t * 2.0 + px * 0.005) % 2 == 0
            if blink_on:
                pygame.draw.circle(surf, (0, 200, 100), (px, CEIL_Y + 22), 3)

        # ── Layer 2: floor warning stripes (fast parallax — moves with camera) ─
        stripe_off = int(self._cam_x * 0.7) % 60
        for sx in range(-stripe_off, CORRIDOR_W + 60, 60):
            sc = pal.get("stripe", (16, 26, 14))
            pygame.draw.rect(surf, sc, (sx, FLOOR_Y - 4, 30, 4))

        # ── Layer 3: ceiling cable run ────────────────────────────────────────
        cable_col = pal.get("cable", (0, 50, 25))
        cable_off = int(self._cam_x * 0.5) % CORRIDOR_W
        for cy_i in range(2):
            cy_y = CEIL_Y + 8 + cy_i * 6
            # Draw as segmented cable with slight sag
            seg_w = 40
            c_off = int(self._cam_x * (0.5 + cy_i * 0.1)) % seg_w
            for cx_s in range(-c_off, CORRIDOR_W + seg_w, seg_w):
                sag = int(3 * math.sin(t * 0.8 + cx_s * 0.05))
                pygame.draw.line(surf, cable_col,
                                 (cx_s, cy_y + sag), (cx_s + seg_w, cy_y + sag), 1)

        # ── Layer 4: ceiling light panels ─────────────────────────────────────
        light_sp = 160
        first_l  = int(self._cam_x / light_sp) * light_sp - light_sp
        for lx in range(first_l, int(self._cam_x) + CORRIDOR_W + light_sp, light_sp):
            sx = lx - int(self._cam_x)
            # Flicker — each light has independent phase
            fl = 1.0 - 0.06 * abs(math.sin(t * 5.8 + lx * 0.03))
            # Some lights are broken (warm red-amber tint instead of green)
            broken = (abs(hash(lx)) % 9) == 0
            if broken:
                lc = (int(180 * fl), int(60 * fl), int(20 * fl))
                # Intermittent flicker for broken lights
                if int(t * 8 + lx) % 7 < 2:
                    lc = (20, 8, 4)
            else:
                lc = tuple(int(c * fl) for c in pal.get("light", (0, 180, 80)))
            pygame.draw.rect(surf, lc, (sx - 16, CEIL_Y + 2, 32, 8))
            # Light cone (subtle gradient trapezoid)
            if not broken:
                cone_col = (int(lc[0] * 0.08), int(lc[1] * 0.08), int(lc[2] * 0.08))
                pts = [(sx - 16, CEIL_Y + 10), (sx + 16, CEIL_Y + 10),
                       (sx + 40, CEIL_Y + 50), (sx - 40, CEIL_Y + 50)]
                pygame.draw.polygon(surf, cone_col, pts)

        # ── Layer 5: background warning text stencils on wall ─────────────────
        warn_off = int(self._cam_x * 0.3) % 320
        f_stencil = get_font(9)
        for wx in range(-warn_off, CORRIDOR_W + 320, 320):
            msgs = ["AUTHORISED PERSONNEL ONLY", "SECTION 7-C", "NO CARGO BEYOND THIS POINT",
                    "TRANSIT ZONE — KEEP MOVING", "UNION LOCALS ONLY", "CLEARANCE REQUIRED"]
            msg = msgs[(abs(wx) // 320) % len(msgs)]
            stencil = f_stencil.render(msg, True, pal.get("stencil", (0, 45, 22)))
            surf.blit(stencil, (wx, FLOOR_Y - 18))

    # ── Epic 10.4 — corridor decay layer ────────────────────────────────
    def _draw_corridor_decay(self, surf, t, pal, room):
        """Cracked + numbered panels, floor wear, drips, deep parallax,
        and per-room directional lighting. Additive — drawn after the
        chapter's bespoke backdrop so chapter art still leads."""
        # Layer A — deep second parallax: dim distant station structure.
        # Painted on the wall band between CEIL_Y and FLOOR_Y, very dim.
        deep_off = int(self._cam_x * 0.08) % 240
        deep_col = pal.get("deep_struct", (0, 30, 18))
        for px in range(-deep_off, CORRIDOR_W + 240, 240):
            # Skeletal frame: vertical I-beam + cross-brace.
            pygame.draw.line(surf, deep_col,
                             (px + 60, CEIL_Y + 10),
                             (px + 60, FLOOR_Y - 10), 1)
            pygame.draw.line(surf, deep_col,
                             (px + 60, CEIL_Y + 30),
                             (px + 180, FLOOR_Y - 30), 1)
            pygame.draw.line(surf, deep_col,
                             (px + 60, FLOOR_Y - 30),
                             (px + 180, CEIL_Y + 30), 1)
            # Distant rectangular window — black hole in the wall.
            win_h = 18
            win_y = CEIL_Y + 70
            pygame.draw.rect(surf, (4, 4, 8),
                             pygame.Rect(px + 110, win_y, 28, win_h))

        # Layer B — numbered + cracked wall panels. Sparse — every 4th
        # default panel slot gets a number stamp + crack.
        panel_w = 240
        num_off = int(self._cam_x * 0.18) % panel_w
        f_num = get_font(7, bold=True)
        for px in range(-num_off, CORRIDOR_W + panel_w, panel_w):
            slot = (abs(hash((px // panel_w, room.length))) % 5)
            if slot == 0:
                # Numbered plate + cracks
                num_lbl = f_num.render(
                    f"S-{(abs(hash((px, room.length))) % 99) + 1:02d}-C",
                    True, pal.get("panel_num", (0, 90, 50)))
                surf.blit(num_lbl, (px + 14, CEIL_Y + 28))
                # Hairline crack
                pygame.draw.line(surf, pal.get("crack", (0, 50, 30)),
                                 (px + 8, CEIL_Y + 60),
                                 (px + 22, CEIL_Y + 90), 1)
                pygame.draw.line(surf, pal.get("crack", (0, 50, 30)),
                                 (px + 22, CEIL_Y + 90),
                                 (px + 14, CEIL_Y + 110), 1)
            elif slot == 2:
                # Scratched-off Nova Soma branding — rendered as faded
                # block with diagonal scrub marks across it.
                brand_rect = pygame.Rect(px + 16, CEIL_Y + 40, 60, 14)
                pygame.draw.rect(surf, (16, 22, 18), brand_rect)
                lbl = f_num.render("NOVA SOMA", True,
                                   pal.get("branding", (60, 80, 60)))
                surf.blit(lbl, (brand_rect.left + 2, brand_rect.top + 3))
                # Scrub marks
                for sx in range(brand_rect.left + 2, brand_rect.right, 6):
                    pygame.draw.line(surf, pal.get("scrub", (40, 30, 20)),
                                     (sx, brand_rect.top + 1),
                                     (sx + 4, brand_rect.bottom - 1), 1)

        # Layer C — floor wear: subtle grid + lightened high-traffic patches.
        grid_off = int(self._cam_x * 0.7) % 32
        floor_grid = pal.get("floor_grid", (0, 60, 30))
        for sx in range(-grid_off, CORRIDOR_W + 32, 32):
            pygame.draw.line(surf, floor_grid,
                             (sx, FLOOR_Y + 1),
                             (sx, CORRIDOR_H), 1)
        # Worn patches every ~140 px — slight lighter overlay.
        wear_off = int(self._cam_x * 0.7) % 280
        wear_col = pal.get("floor_wear", (24, 36, 24))
        for sx in range(-wear_off, CORRIDOR_W + 280, 280):
            pygame.draw.ellipse(surf, wear_col,
                                pygame.Rect(sx, FLOOR_Y + 4, 80, 8))

        # Layer D — pipe drips: a couple of points along the ceiling that
        # release a slow droplet every couple of seconds.
        drip_col = pal.get("drip", (0, 110, 70))
        for i, drip_world_x in enumerate((220, 760, 1320, 1880)):
            sx = int(drip_world_x - self._cam_x * 1.0)
            if sx < -20 or sx > CORRIDOR_W + 20:
                continue
            cycle = (t + i * 0.7) % 2.6
            if cycle < 0.4:
                # Pipe puddle highlight only.
                pygame.draw.line(surf, drip_col,
                                 (sx - 5, CEIL_Y + 22),
                                 (sx + 5, CEIL_Y + 22), 1)
            elif cycle < 1.6:
                # Drop falling.
                fall_pct = (cycle - 0.4) / 1.2
                drop_y = int(CEIL_Y + 22 + fall_pct * (FLOOR_Y - CEIL_Y - 28))
                pygame.draw.circle(surf, drip_col, (sx, drop_y), 2)
            else:
                # Splash on floor.
                radius = int(2 + 2 * (cycle - 1.6))
                pygame.draw.circle(surf, drip_col,
                                   (sx, FLOOR_Y - 4), radius, 1)

        # Layer E — directional lighting overlay. Each room can declare:
        #   "light_tint": (r, g, b)  e.g. (60, 90, 150) for cold blue
        #   "light_alpha": int 0..255
        # Default chapters can opt-in by adding the keys; otherwise no-op.
        tint = pal.get("light_tint")
        if tint is not None:
            alpha = int(pal.get("light_alpha", 32))
            tint_surf = pygame.Surface((CORRIDOR_W, CORRIDOR_H), pygame.SRCALPHA)
            tint_surf.fill((tint[0], tint[1], tint[2], alpha))
            surf.blit(tint_surf, (0, 0))

        # Layer F — red emergency wash when invert / spore-zone is active.
        if self._invert_t > 0:
            wash = pygame.Surface((CORRIDOR_W, CORRIDOR_H), pygame.SRCALPHA)
            pulse = 0.5 + 0.5 * math.sin(t * 6.0)
            wash.fill((180, 30, 30, int(40 + 30 * pulse)))
            surf.blit(wash, (0, 0))

    def _pose(self) -> str:
        """Delivery v2 I.1.3 — pick the courier pose from movement state."""
        if self._victory:
            return "victory"
        if self._on_ladder:
            return "jump"                       # climbing tuck
        if self._skid_t > 0:
            return "skid"
        if not self._grounded:
            return "jump" if self._pvy < -40 else "fall"
        if abs(self._pvx) > 15:
            return "run"
        return "idle"

    def _draw_player(self, surf, t):
        px       = _PLAYER_X_FIXED
        py       = int(self._py)
        stun_fls = self._stun_t > 0 and int(t * 10) % 2 == 0
        inv_glow = self._invert_t > 0

        # Dust puffs (world-space, behind the courier)
        for d in self._dust:
            dx = int(d[0] - self._cam_x)
            dy = int(d[1])
            a  = max(0.0, min(1.0, d[4] / 0.3))
            if d[6] is not None:   # coloured sparkle (chip pop)
                col = tuple(max(0, min(255, int(c * (0.35 + 0.65 * a))))
                            for c in d[6])
            else:
                g = int(120 + 80 * a)
                col = (g, g, g)
            s = max(1, int(d[5]))
            pygame.draw.rect(surf, col, (dx, dy, s, s))

        if stun_fls:
            return

        pose = self._pose()
        # Squash on landing, stretch at take-off (I.1.3). k>0 squashes.
        k = 2.3 * self._land_squash_t - 1.6 * self._jump_stretch_t
        if abs(k) < 0.02:
            draw_courier_sprite(surf, px, py - 8, t, inv=inv_glow,
                                grounded=self._grounded, pose=pose,
                                walk_phase=self._walk_phase)
            self._draw_cargo_silhouette(surf, px, py)
        else:
            # Render to a small temp surface, scale, anchor at the feet.
            tmp = getattr(self, "_sprite_tmp", None)
            if tmp is None:
                tmp = pygame.Surface((64, 76), pygame.SRCALPHA)
                self._sprite_tmp = tmp
            tmp.fill((0, 0, 0, 0))
            draw_courier_sprite(tmp, 32, 22, t, inv=inv_glow,
                                grounded=self._grounded, pose=pose,
                                walk_phase=self._walk_phase)
            self._draw_cargo_silhouette(tmp, 32, 30)
            sw = max(1, int(64 * (1.0 + 0.9 * k)))
            sh = max(1, int(76 * (1.0 - k)))
            scaled = pygame.transform.scale(tmp, (sw, sh))
            # Feet anchor: world bottom of the temp canvas is py + 46
            surf.blit(scaled, (px - sw // 2, py + 46 - sh))

        if not self._grounded and not self._on_ladder:
            pygame.draw.line(surf, (0, 160, 70),
                             (px - 4, py + PLAYER_H),
                             (px - 8, py + PLAYER_H + 8), 2)
            pygame.draw.line(surf, (0, 160, 70),
                             (px + 4, py + PLAYER_H),
                             (px + 10, py + PLAYER_H + 6), 2)

        # I.2.2 — floating pickup text (rises + fades, on top of the courier)
        if self._floaters:
            ff = get_font(11, bold=True)
            for fl in self._floaters:
                fx = int(fl[0] - self._cam_x)
                fy = int(fl[1])
                a  = max(0, min(255, int(255 * (fl[3] / 0.8))))
                fs = ff.render(fl[2], True, fl[4])
                fsurf = pygame.Surface(fs.get_size(), pygame.SRCALPHA)
                fsurf.blit(fs, (0, 0))
                fsurf.set_alpha(a)
                surf.blit(fsurf, (fx - fs.get_width() // 2, fy))

    def _draw_cargo_silhouette(self, surf, px, py):
        cs = self.cargo_silhouette
        bx = px + PLAYER_W // 2
        by = py + 2
        if cs == "archive":
            # Vinyl record shape
            pygame.draw.circle(surf, (180, 60, 0), (bx + 7, by + 10), 10)
            pygame.draw.circle(surf, (220, 90, 0), (bx + 7, by + 10), 10, 1)
            pygame.draw.circle(surf, (30, 10, 0), (bx + 7, by + 10), 3)
        elif cs == "shroom":
            # Jar
            pygame.draw.rect(surf, (60, 180, 120), (bx + 2, by + 4, 12, 16))
            pygame.draw.rect(surf, (100, 255, 160), (bx + 2, by + 4, 12, 16), 1)
            pygame.draw.rect(surf, (80, 160, 100), (bx, by + 2, 16, 4))
            for i in range(3):
                pygame.draw.circle(surf, (180, 255, 80),
                                   (bx + 4 + i * 3, by + 10 + i * 2), 2)
        elif cs == "forms":
            # Stack of paper
            for i in range(3):
                pygame.draw.rect(surf, (200, 190, 160),
                                 (bx + i, by + i * 3, 14, 10))
                pygame.draw.rect(surf, (220, 210, 180),
                                 (bx + i, by + i * 3, 14, 10), 1)
        elif cs == "vip":
            # Small box with question mark
            pygame.draw.rect(surf, (60, 20, 80), (bx + 2, by + 2, 14, 18))
            pygame.draw.rect(surf, (120, 60, 160), (bx + 2, by + 2, 14, 18), 1)
            f = get_font(9, bold=True)
            s = f.render("?", True, (180, 100, 220))
            surf.blit(s, (bx + 5, by + 6))
        else:
            # Default box
            pygame.draw.rect(surf, (200, 150, 0), (bx, by + 4, 10, 14))
            pygame.draw.rect(surf, (255, 190, 0), (bx, by + 4, 10, 14), 1)

    def _draw_hud(self, surf, t, room):
        f    = get_font(13)
        fsm  = get_font(10)
        # I.2.1 — time no longer rates the run, so it no longer glares red.
        surf.blit(f.render(f"TIME  {self._elapsed:>5.1f}s", True,
                           (120, 150, 120)), (6, 4))
        h_col = (220, 60, 60) if self._hits > 0 else (0, 180, 80)
        surf.blit(f.render(f"HITS  {self._hits}", True, h_col), (140, 4))
        # Chip count — the number the run is now about
        if self._collectibles_total > 0:
            chip_s = f.render(
                f"CHIPS {self._collectibles_found}/{self._collectibles_total}",
                True, (255, 210, 60))
            surf.blit(chip_s, (228, 4))
        cr_s  = fsm.render(f"+{self._credits} cr", True, (200, 160, 0))
        surf.blit(cr_s, (CORRIDOR_W - cr_s.get_width() - 6, 4))

        # I.3.3 — active power-up chip in the corner
        if self._power_kind is not None and not self._done:
            label = {"magboots": "MAG-BOOTS", "hardhat": "HARDHAT",
                     "stimsoles": "STIM SOLES"}[self._power_kind]
            if self._power_kind != "hardhat":
                label += f"  {max(0.0, self._power_t):.0f}s"
            pw_s = fsm.render(label, True, (140, 220, 255))
            surf.blit(pw_s, (6, 20))

        # I.2.3 — chain meter: multiplier + draining window bar
        if self._chain >= 2 and self._chain_t > 0 and not self._done:
            pul = 0.75 + 0.25 * math.sin(t * 10.0)
            ch_col = (int(255 * pul), int(215 * pul), 40)
            ch_s = f.render(f"CHAIN ×{self._chain}", True, ch_col)
            chx = CORRIDOR_W // 2 - ch_s.get_width() // 2
            surf.blit(ch_s, (chx, 18))
            bar_w = int(56 * (self._chain_t / CHIP_CHAIN_WINDOW))
            pygame.draw.rect(surf, (90, 75, 20),
                             (CORRIDOR_W // 2 - 28, 34, 56, 3))
            pygame.draw.rect(surf, ch_col,
                             (CORRIDOR_W // 2 - 28, 34, bar_w, 3))

        # Inversion warning
        if self._invert_t > 0:
            iw = f.render("CONTROLS INVERTED", True,
                           (int(200 + 55 * math.sin(t * 8)), 80, 255))
            surf.blit(iw, (CORRIDOR_W // 2 - iw.get_width() // 2, CEIL_Y + 4))

        # Bright introductory hint (first 6s) — brighter and includes climb
        if self._elapsed < 6.0:
            hint_alpha = min(255, int(255 * (1.0 - self._elapsed / 6.0) * 2))
            hint_col   = (0, max(0, int(200 * hint_alpha / 255)),
                          max(0, int(60 * hint_alpha / 255)))
            hint = fsm.render(
                "A/← D/→ MOVE    W/S CLIMB LADDER    SPACE JUMP",
                True, hint_col)
            surf.blit(hint, (CORRIDOR_W // 2 - hint.get_width() // 2, CEIL_Y + 6))

        # Persistent compact legend (bottom-right, always on)
        legend = fsm.render(
            "←/→ move   ↑/↓ climb   SPACE jump", True, (55, 95, 60))
        surf.blit(legend, (CORRIDOR_W - legend.get_width() - 6,
                           CORRIDOR_H - 20))

        # Progress bar
        prog = min(1.0, self._px / max(1, room.length))
        pygame.draw.rect(surf, (10, 22, 10),
                         (0, CORRIDOR_H - 8, CORRIDOR_W, 8))
        pygame.draw.rect(surf, (0, 180, 80),
                         (0, CORRIDOR_H - 8, int(CORRIDOR_W * prog), 8))

        # Room indicator
        ri = fsm.render(f"RM {self._room_idx + 1}/{len(self.rooms)}", True, (60, 80, 60))
        surf.blit(ri, (6, CORRIDOR_H - 20))

    def _draw_result(self, surf):
        """Delivery v2 I.2.1 — staged DKC-style tally screen.
        Rows reveal on the _finish() schedule as _tally_t advances."""
        ov = pygame.Surface((CORRIDOR_W, CORRIDOR_H), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 190))
        surf.blit(ov, (0, 0))

        tt   = self._tally_t
        fh   = get_font(20, bold=True)
        f    = get_font(13, bold=True)
        fsm  = get_font(11)
        cx   = CORRIDOR_W // 2

        # Title plate
        title = fh.render("CARGO DELIVERED", True, (0, 230, 120))
        surf.blit(title, (cx - title.get_width() // 2, 34))
        pygame.draw.line(surf, (40, 90, 60),
                         (cx - 120, 62), (cx + 120, 62), 1)

        def _row(label, value, col, y):
            lbl = fsm.render(label, True, (110, 130, 110))
            val = f.render(value, True, col)
            surf.blit(lbl, (cx - 130, y + 2))
            surf.blit(val, (cx + 18, y))

        lh = f.get_linesize() + 6
        y  = 82

        # CHIPS — counts up with ticks
        cs = self._mark_t("chips_start")
        if cs is not None and tt >= cs:
            total = self._collectibles_total
            if total > 0:
                shown = self._tally_chip_shown
                pct   = int(100 * self._collectibles_found / total)
                done_counting = shown >= self._collectibles_found
                c_col = (255, 215, 60) if (done_counting and pct == 100) \
                        else (220, 190, 100)
                val = f"{shown} / {total}"
                if done_counting:
                    val += f"   {pct}%"
                _row("CHIPS", val, c_col, y)
                if done_counting and self._best_chain >= 2:
                    bc = fsm.render(f"best chain ×{self._best_chain}", True,
                                    (170, 150, 80))
                    surf.blit(bc, (cx + 18, y + f.get_linesize() - 2))
                    y += 10
            else:
                _row("CHIPS", "—", (110, 110, 110), y)
        y += lh

        m = self._mark_t("secrets")
        if m is not None and tt >= m:
            s_col = (0, 220, 200) if self._secrets_found >= self._secrets_total \
                    and self._secrets_total > 0 else (140, 170, 170)
            _row("SECRETS", f"{self._secrets_found} / {self._secrets_total}",
                 s_col, y)
        y += lh

        m = self._mark_t("hits")
        if m is not None and tt >= m:
            h_col = (0, 210, 90) if self._hits == 0 else \
                    (255, 180, 0) if self._hits <= 1 else (210, 90, 90)
            _row("HITS", f"{self._hits}", h_col, y)
        y += lh

        m = self._mark_t("punctual")
        if m is not None and tt >= m:
            _row("UNION PUNCTUALITY", f"+{PUNCTUALITY_BONUS:,} cr",
                 (120, 200, 255), y)
            y += lh

        m = self._mark_t("credits")
        if m is not None and tt >= m:
            _row("CREDITS", f"+{self._result_credits:,} cr",
                 (255, 200, 40), y)
        y += lh + 6

        # Stars burst in one at a time
        if self._stars_shown > 0:
            star_f = get_font(26, bold=True)
            spacing = 40
            x0 = cx - spacing * (3 - 1) // 2
            for i in range(3):
                lit  = i < self._stars_shown
                col  = (255, 220, 40) if lit else (60, 60, 55)
                # newest star flashes bright for its first beat
                if lit and i == self._stars_shown - 1:
                    mt = self._mark_t(f"star{i + 1}") or 0.0
                    if tt - mt < 0.3:
                        col = (255, 235, 120)
                s = star_f.render("★" if lit else "☆", True, col)
                surf.blit(s, (x0 + i * spacing - s.get_width() // 2, y))
            y += 34

        # Exit hint once the tally has fully landed
        if tt >= self._tally_done_t:
            blink = int(tt * 2.4) % 2 == 0
            if blink:
                hint = fsm.render("ENTER — hand off the cargo", True,
                                  (0, 190, 90))
                surf.blit(hint, (cx - hint.get_width() // 2,
                                 CORRIDOR_H - 34))
            par = fsm.render(
                f"time {self._elapsed:.0f}s · par {self._par_total:.0f}s",
                True, (90, 100, 90))
            surf.blit(par, (cx - par.get_width() // 2, CORRIDOR_H - 20))
