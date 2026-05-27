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
)
from delivery.corridor.mutators import get_corridor_mutator, CorridorMutator
from core.event_bus import (bus, EVT_BAX_SPEAK, EVT_DELIVERY_DONE,
                            EVT_CORRIDOR_RUN, EVT_CORRIDOR_JUMP,
                            EVT_CORRIDOR_SECRET, EVT_CORRIDOR_DEATH,
                            EVT_LORE_FOUND, EVT_CORRIDOR_ENTER,
                            EVT_CORRIDOR_BOSS_ROOM, EVT_CORRIDOR_EXIT)

GRAVITY   = 980.0
JUMP_VY   = -440.0
RUN_SPEED = 220.0
CLIMB_SPD = 120.0
LADDER_REGRAB_COOLDOWN = 0.18
LADDER_SIDE_STEP_SPEED = RUN_SPEED * 0.75

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
                 name: str = ""):
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
        self._pvy       = 0.0
        self._grounded  = True
        self._on_ladder  = False
        self._ladder_release_t = 0.0
        self._cam_x     = 0.0

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
            return
        if event.key in (pygame.K_SPACE, pygame.K_w, pygame.K_UP):
            if self._grounded and not self._on_ladder:
                self._pvy      = JUMP_VY
                self._grounded = False
                bus.emit(EVT_CORRIDOR_JUMP)
            elif self._on_ladder and event.key == pygame.K_SPACE:
                # Jump off ladder mid-way
                self._pvy       = JUMP_VY * 0.75
                self._grounded  = False
                self._release_ladder()
                bus.emit(EVT_CORRIDOR_JUMP)
        elif event.key in (pygame.K_s, pygame.K_DOWN):
            pass  # descend on ladder handled by held-key
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
            self._result_t -= dt
            return

        self._elapsed      += dt
        self._stun_t        = max(0.0, self._stun_t - dt)
        self._invert_t      = max(0.0, self._invert_t - dt)
        self._ladder_release_t = max(0.0, self._ladder_release_t - dt)
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

        # Ladder check
        ladder = self._active_ladder(wants_ladder, climb_down)
        self._on_ladder = ladder is not None and (self._on_ladder or wants_ladder)

        if self._on_ladder:
            self._pvy = 0.0
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

            if move_fwd:
                proposed = self._px + RUN_SPEED * dt
                # Aliveness A.6 — wire OneWayWall collision so the
                # Ch.3 cubicle zigzag actually constrains movement
                # instead of decorating it. Block forward motion if any
                # OneWayWall says we're entering its blocked side.
                if not self._blocked_by_oneway(proposed, +RUN_SPEED, room):
                    self._px = proposed
            elif move_bck:
                # Can retreat but only back to the camera left edge (can't go behind camera)
                min_x = self._cam_x + _PLAYER_X_FIXED * 0.5
                proposed = self._px - RUN_SPEED * 0.6 * dt
                if not self._blocked_by_oneway(proposed, -RUN_SPEED, room):
                    self._px = max(min_x, proposed)

            # Gravity
            self._pvy += GRAVITY * dt
            self._py  += self._pvy * dt

            # Platform collision (floor first)
            self._grounded = False
            if self._py >= FLOOR_Y - PLAYER_H:
                self._py      = float(FLOOR_Y - PLAYER_H)
                self._pvy     = 0.0
                self._grounded = True
            if self._py < CEIL_Y + 2:
                self._py  = float(CEIL_Y + 2)
                self._pvy = max(0.0, self._pvy)

            # Platform elements
            for el in self._visible_elements(room):
                if isinstance(el, (Platform, CollapsingPlatform)):
                    if el.collides_top(self._px, self._py, self._pvy):
                        self._py      = el.y - PLAYER_H
                        self._pvy     = 0.0
                        self._grounded = True
                        if isinstance(el, CollapsingPlatform):
                            el.step_on()
                elif isinstance(el, MovingPlatform):
                    if el.collides_top(self._px, self._py, self._pvy):
                        self._py      = el.y - PLAYER_H
                        self._pvy     = 0.0
                        self._grounded = True

        # Camera
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
                    self._credits += v
                    self._collectibles_found += 1
            elif isinstance(el, Secret):
                v, lore = el.try_collect(self._px, self._py)
                if v or lore:
                    self._credits += v
                    self._secrets_found += 1
                    bus.emit(EVT_CORRIDOR_SECRET)
                    if lore:
                        bus.emit(EVT_BAX_SPEAK, line=lore[:60])
                        # Epic 8.3 — persist for Bax's Records, Tab 4.
                        bus.emit(EVT_LORE_FOUND, text=lore, chapter=self.chapter)

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

    def _take_hit(self):
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

    def _finish(self):
        self._done = True
        bus.emit(EVT_DELIVERY_DONE)
        if not self._exit_emitted:
            self._exit_emitted = True
            bus.emit(EVT_CORRIDOR_EXIT, chapter=self.chapter)
        total_t = self._elapsed
        room    = self.rooms[self._room_idx]
        if total_t <= room.star3_t and self._hits == 0:
            self._stars = 3
        elif total_t <= room.star2_t and self._hits <= 1:
            self._stars = 2
        else:
            self._stars = max(1, 3 - self._hits)
        self._result_credits = self._credits
        self._result_t = 4.0

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

    def _draw_player(self, surf, t):
        px       = _PLAYER_X_FIXED
        py       = int(self._py)
        stun_fls = self._stun_t > 0 and int(t * 10) % 2 == 0
        inv_glow = self._invert_t > 0

        if not stun_fls:
            draw_courier_sprite(surf, px, py - 8, t,
                                inv=inv_glow, grounded=self._grounded)
            self._draw_cargo_silhouette(surf, px, py)
            if not self._grounded and not self._on_ladder:
                pygame.draw.line(surf, (0, 160, 70),
                                 (px - 4, py + PLAYER_H),
                                 (px - 8, py + PLAYER_H + 8), 2)
                pygame.draw.line(surf, (0, 160, 70),
                                 (px + 4, py + PLAYER_H),
                                 (px + 10, py + PLAYER_H + 6), 2)

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
        t_col = (0, 220, 100) if self._elapsed < room.star3_t else \
                (255, 180, 0) if self._elapsed < room.star2_t else (220, 60, 60)
        surf.blit(f.render(f"TIME  {self._elapsed:>5.1f}s", True, t_col), (6, 4))
        h_col = (220, 60, 60) if self._hits > 0 else (0, 180, 80)
        surf.blit(f.render(f"HITS  {self._hits}", True, h_col), (140, 4))
        cr_s  = fsm.render(f"+{self._credits} cr", True, (200, 160, 0))
        surf.blit(cr_s, (CORRIDOR_W - cr_s.get_width() - 6, 4))

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
        ov = pygame.Surface((CORRIDOR_W, CORRIDOR_H), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 170))
        surf.blit(ov, (0, 0))

        fh  = get_font(20, bold=True)
        f   = get_font(12)
        fsm = get_font(11)

        label_col = [(220, 60, 60), (255, 180, 0), (0, 240, 110)][self._stars - 1]
        label_txt = ["★☆☆  1 STAR", "★★☆  2 STARS", "★★★  3 STARS!"][self._stars - 1]
        ls = fh.render(label_txt, True, label_col)
        cy = CORRIDOR_H // 2 - 46
        surf.blit(ls, (CORRIDOR_W // 2 - ls.get_width() // 2, cy))

        # Separator
        pygame.draw.line(surf, (60, 80, 60),
                         (CORRIDOR_W // 2 - 100, cy + 28),
                         (CORRIDOR_W // 2 + 100, cy + 28), 1)

        def _stat(label, value, col, y):
            lbl = fsm.render(label, True, (100, 120, 100))
            val = f.render(value, True, col)
            surf.blit(lbl, (CORRIDOR_W // 2 - 120, y))
            surf.blit(val, (CORRIDOR_W // 2 + 10, y))

        room = self.rooms[self._room_idx]
        lh   = f.get_linesize() + 2
        y0   = cy + 36

        t_col = (0, 220, 100) if self._elapsed <= room.star3_t else \
                (255, 180, 0) if self._elapsed <= room.star2_t else (200, 80, 80)
        _stat("TIME",       f"{self._elapsed:.1f}s", t_col, y0)

        h_col = (0, 200, 80) if self._hits == 0 else \
                (255, 180, 0) if self._hits <= 1 else (200, 80, 80)
        _stat("DAMAGE",     f"{self._hits} hit{'s' if self._hits != 1 else ''}", h_col, y0 + lh)

        if self._collectibles_total > 0:
            c_col = (0, 220, 100) if self._collectibles_found == self._collectibles_total \
                    else (200, 160, 60)
            _stat("COLLECT", f"{self._collectibles_found} / {self._collectibles_total}",
                  c_col, y0 + lh * 2)

        s_col = (0, 200, 200) if self._secrets_found > 0 else (100, 100, 100)
        _stat("SECRETS",    str(self._secrets_found), s_col, y0 + lh * 3)

        cr_col = (200, 160, 0) if self._credits > 0 else (100, 100, 100)
        _stat("CREDITS",    f"+{self._credits} cr", cr_col, y0 + lh * 4)
