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

from delivery.corridor.elements import (
    CORRIDOR_W, CORRIDOR_H, FLOOR_Y, CEIL_Y, PLAYER_H, PLAYER_W,
    Platform, MovingPlatform, CollapsingPlatform, Ladder,
    Hazard, MovingHazard, ToggleBeam, OneWayWall,
    NPCEncounter, Collectible, Secret, Checkpoint, StealthZone,
    BossRoomTrigger, SporeZone, QuantumDoor,
)
from core.event_bus import (bus, EVT_BAX_SPEAK, EVT_DELIVERY_DONE,
                            EVT_CORRIDOR_RUN, EVT_CORRIDOR_JUMP,
                            EVT_CORRIDOR_SECRET, EVT_CORRIDOR_DEATH)

GRAVITY   = 980.0
JUMP_VY   = -440.0
RUN_SPEED = 220.0
CLIMB_SPD = 120.0

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
        if event.key == pygame.K_RETURN:
            self._submit()
        elif event.key == pygame.K_BACKSPACE:
            self._input = self._input[:-1]
        elif event.unicode and event.unicode.isprintable():
            if len(self._input) < 40:
                self._input += event.unicode

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

        f_name  = pygame.font.SysFont("monospace", 11, bold=True)
        f_text  = pygame.font.SysFont("monospace", 10)
        f_input = pygame.font.SysFont("monospace", 11)

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
                 bax_boss_line: str = ""):
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


# ---------------------------------------------------------------------------
# Corridor
# ---------------------------------------------------------------------------

class Corridor:
    """
    Multi-room delivery corridor.
    Drop-in replacement for DeliveryRun (same external API).
    """

    def __init__(self, chapter: int, rooms: list[Room],
                 cargo_silhouette: str = "box"):
        self.chapter         = chapter
        self.rooms           = rooms
        self.cargo_silhouette = cargo_silhouette  # "box"|"archive"|"shroom"|"forms"|"vip"

        # Player state
        self._px        = 120.0
        self._py        = float(FLOOR_Y - PLAYER_H)
        self._pvy       = 0.0
        self._grounded  = True
        self._on_ladder  = False
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

        # NPC dialog
        self._dialog: _CorridorDialog | None = None

        # Near-end spoken flags
        self._mid1_spoken = False
        self._mid2_spoken = False
        self._near_end_spoken = False

        # Result
        self._done      = False
        self._stars     = 0

        # Ambient run Bax commentary timer
        self._run_speak_t = 10.0   # fire first corridor-run line after 10s
        self._result_t  = 0.0
        self._result_credits = 0

        # Surface
        self._surf = pygame.Surface((CORRIDOR_W, CORRIDOR_H))

        # Fire entry Bax line for Room 0
        self._fire_room_enter(0)

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
                self._on_ladder = False
                bus.emit(EVT_CORRIDOR_JUMP)
        elif event.key in (pygame.K_s, pygame.K_DOWN):
            pass  # descend on ladder handled by held-key

    def update(self, dt: float) -> None:
        if self._wipe_t > 0:
            self._wipe_t -= dt
            if self._wipe_t <= 0 and self._transition_pending:
                self._do_room_transition()
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
        self._run_speak_t  -= dt
        if self._run_speak_t <= 0:
            self._run_speak_t = 12.0
            bus.emit(EVT_CORRIDOR_RUN)

        keys = pygame.key.get_pressed()
        room = self.rooms[self._room_idx]

        # Ladder check
        ladder = self._active_ladder()
        self._on_ladder = ladder is not None and ladder.overlaps(self._px, self._py)

        if self._on_ladder:
            if keys[pygame.K_UP] or keys[pygame.K_w]:
                self._py  -= CLIMB_SPD * dt
                self._pvy  = 0.0
            if keys[pygame.K_DOWN] or keys[pygame.K_s]:
                self._py  += CLIMB_SPD * dt
                self._pvy  = 0.0

            # Dismount at top: step off onto the surface above the ladder
            if self._py + PLAYER_H <= ladder.y_top:
                self._py        = ladder.y_top - PLAYER_H
                self._pvy       = 0.0
                self._grounded  = True
                self._on_ladder = False
            # Dismount at bottom: drop to floor
            elif self._py >= ladder.y_bot - PLAYER_H:
                self._py        = float(FLOOR_Y - PLAYER_H)
                self._pvy       = 0.0
                self._grounded  = True
                self._on_ladder = False
            else:
                self._px       = ladder.x
                self._grounded = False
        else:
            # Branch choice at branch point
            if (room.branch_x is not None
                    and abs(self._px - room.branch_x) < 30
                    and self._active_path is None):
                if keys[pygame.K_UP] or keys[pygame.K_w]:
                    self._active_path = "high"
                else:
                    self._active_path = "low"

            # Player-controlled forward movement (D/RIGHT = run, A/LEFT = retreat)
            # Controls invert when spore-zone is active (Ch.2 mechanic)
            inverted = self._invert_t > 0
            move_fwd = keys[pygame.K_d] or keys[pygame.K_RIGHT]
            move_bck = keys[pygame.K_a] or keys[pygame.K_LEFT]
            if inverted:
                move_fwd, move_bck = move_bck, move_fwd

            if move_fwd:
                self._px += RUN_SPEED * dt
            elif move_bck:
                # Can retreat but only back to the camera left edge (can't go behind camera)
                min_x = self._cam_x + _PLAYER_X_FIXED * 0.5
                self._px = max(min_x, self._px - RUN_SPEED * 0.6 * dt)

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
            f = pygame.font.SysFont("monospace", 10)
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
            ov = pygame.Surface((CORRIDOR_W, CORRIDOR_H))
            ov.fill((0, 0, 0))
            ov.set_alpha(max(0, min(255, alpha)))
            surf.blit(ov, (0, 0))

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

    def _active_ladder(self):
        room = self.rooms[self._room_idx]
        for el in self._visible_elements(room):
            if isinstance(el, Ladder) and el.overlaps(self._px, self._py):
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
            if hit:
                self._take_hit()
                break

    def _check_collectibles(self, room: Room):
        for el in self._visible_elements(room):
            if isinstance(el, Collectible):
                v = el.try_collect(self._px, self._py)
                if v:
                    self._credits += v
            elif isinstance(el, Secret):
                v, lore = el.try_collect(self._px, self._py)
                if v or lore:
                    self._credits += v
                    bus.emit(EVT_CORRIDOR_SECRET)
                    if lore:
                        bus.emit(EVT_BAX_SPEAK, line=lore[:60])

    def _check_npc_encounters(self, room: Room):
        if self._dialog is not None:
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
                if el.check(self._px) and el.bax_line:
                    bus.emit(EVT_BAX_SPEAK, line=el.bax_line)

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
        self._wipe_t               = 0.5
        self._wipe_dir             = -1  # fade to black
        self._transition_pending   = True

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
        bg_off = self._cam_x * 0.5
        # Grid lines
        for gx in range(0, CORRIDOR_W, 40):
            pygame.draw.line(surf, pal.get("grid", (12, 22, 14)),
                             (gx, 0), (gx, CORRIDOR_H), 1)
        for gy in range(0, CORRIDOR_H, 40):
            pygame.draw.line(surf, pal.get("grid", (12, 22, 14)),
                             (0, gy), (CORRIDOR_W, gy), 1)
        # Ceiling lights
        light_sp = 180
        first_l  = int(self._cam_x / light_sp) * light_sp - light_sp
        for lx in range(first_l, int(self._cam_x) + CORRIDOR_W + light_sp, light_sp):
            sx = lx - int(self._cam_x)
            fl = 1.0 - 0.08 * math.sin(t * 7.3 + lx * 0.01)
            lc = tuple(int(c * fl) for c in pal.get("light", (0, 180, 80)))
            pygame.draw.rect(surf, lc, (sx - 12, CEIL_Y + 2, 24, 6))

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
            f = pygame.font.SysFont("monospace", 9, bold=True)
            s = f.render("?", True, (180, 100, 220))
            surf.blit(s, (bx + 5, by + 6))
        else:
            # Default box
            pygame.draw.rect(surf, (200, 150, 0), (bx, by + 4, 10, 14))
            pygame.draw.rect(surf, (255, 190, 0), (bx, by + 4, 10, 14), 1)

    def _draw_hud(self, surf, t, room):
        f    = pygame.font.SysFont("monospace", 13)
        fsm  = pygame.font.SysFont("monospace", 10)
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

        # Controls hint (only show for first 8s)
        if self._elapsed < 8.0:
            hint_alpha = min(255, int(255 * (1.0 - self._elapsed / 8.0) * 2))
            hint_col   = (0, max(0, int(160 * hint_alpha / 255)), 0)
            hint = fsm.render("D/→ run  A/← retreat  SPACE jump", True, hint_col)
            surf.blit(hint, (CORRIDOR_W // 2 - hint.get_width() // 2, CEIL_Y + 6))

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
        ov.fill((0, 0, 0, 160))
        surf.blit(ov, (0, 0))
        fh = pygame.font.SysFont("monospace", 20, bold=True)
        f  = pygame.font.SysFont("monospace", 13)
        label_col = [(220, 60, 60), (255, 180, 0), (0, 240, 110)][self._stars - 1]
        label_txt = ["★☆☆  1 STAR", "★★☆  2 STARS", "★★★  3 STARS!"][self._stars - 1]
        ls = fh.render(label_txt, True, label_col)
        surf.blit(ls, (CORRIDOR_W // 2 - ls.get_width() // 2, CORRIDOR_H // 2 - 28))
        ts = f.render(f"{self._elapsed:.1f}s  ·  {self._hits} hit(s)  ·  +{self._credits} cr",
                      True, (140, 140, 140))
        surf.blit(ts, (CORRIDOR_W // 2 - ts.get_width() // 2, CORRIDOR_H // 2 + 4))
