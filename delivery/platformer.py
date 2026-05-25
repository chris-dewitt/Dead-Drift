"""
Delivery Run — side-scrolling platformer mini-game.

The courier sprints right through a Union station corridor
to drop off the cargo.  Four obstacle types stand in the way.
Star rating based on time taken + hits received.
"""
from __future__ import annotations
import math
import random
import pygame

from delivery.obstacles import (
    Guard, Gate, MovingPlatform, ScannerBeam,
    CORRIDOR_H, FLOOR_Y, CEIL_Y, PLAYER_H,
)
from core.event_bus import bus, EVT_BAX_SPEAK, EVT_DELIVERY_STEP, EVT_DELIVERY_HIT, EVT_DELIVERY_DONE
from core.text import get_font

# ── Layout inside the corridor surface ──────────────────────────────────────
CORRIDOR_W     = 400    # visible width of the corridor viewport
LEVEL_LENGTH   = 3200   # total world length (player walks this far to finish)
PLAYER_X_FIXED = 100    # player screen X stays constant; camera moves
PLAYER_W       = 18

GRAVITY        = 980.0  # px/s²
JUMP_VY        = -440.0
RUN_SPEED      = 220.0  # px/s (auto-run right)

STAR_3_TIME    = 18.0   # seconds
STAR_2_TIME    = 28.0
MAX_HITS       = 3      # more than this → 1 star regardless

_BAX_START = [
    "Right, out you go. I'll watch the ship. And by watch I mean panic quietly.",
    "Delivery entrance is straight through. Don't look the guards in the eye.",
    "I'll be 'ere. In the ship. Being useful. Don't rush on my account.",
]
_BAX_HIT = [
    "OI! Guard got ya! Keep movin'!",
    "Scanner clipped ya! DUCK next time!",
    "That gate was TIMED, mate. Read the room.",
]
_BAX_NEAR_END = [
    "I can see the drop-off from here! Almost there!",
    "Nearly through! DON'T balls it up NOW!",
    "Last stretch! You've got this! Probably!",
]
_BAX_3STAR = [
    "THREE STARS. THREE. I'm framing that.",
    "Look at you, blendin' in like a PROFESSIONAL courier. Disgusting. I love it.",
]
_BAX_2STAR = [
    "Two stars. Solid. Not embarrassing. Well — slightly embarrassing.",
    "Delivery complete. You've got the grace of a fridge, but it worked.",
]
_BAX_1STAR = [
    "One star. One. That's barely a rating, that is.",
    "Next time maybe don't walk INTO the scanner beam on purpose.",
]


def _build_level() -> list:
    """Generate obstacle list for one delivery run."""
    obstacles = []
    x = 400.0   # first obstacle starts well after player spawn

    while x < LEVEL_LENGTH - 300:
        kind = random.choices(
            ["guard", "gate", "platform", "scanner"],
            weights=[3, 2, 2, 2],
        )[0]

        if kind == "guard":
            obstacles.append(Guard(x))
            x += random.uniform(260, 380)

        elif kind == "gate":
            obstacles.append(Gate(x))
            x += random.uniform(200, 320)

        elif kind == "platform":
            gap = random.uniform(120, 180)
            obstacles.append(MovingPlatform(x + gap / 2, gap))
            x += gap + random.uniform(80, 140)

        elif kind == "scanner":
            obstacles.append(ScannerBeam(x + 60, random.uniform(80, 140)))
            x += random.uniform(200, 300)

    return obstacles


class DeliveryRun:
    """
    Side-scrolling platformer phase.

    Call update(dt) each frame, draw(surface) to render,
    handle_key(event) for KEYDOWN events.
    """

    def __init__(self):
        self._player_x   = 120.0    # world X
        self._player_y   = float(FLOOR_Y - PLAYER_H)
        self._player_vy  = 0.0
        self._grounded   = True
        self._camera_x   = 0.0     # world X of left edge of viewport

        self._obstacles  = _build_level()
        self._hits       = 0
        self._elapsed    = 0.0
        self._stun_t     = 0.0     # brief invincibility after a hit
        self._near_end_spoken = False

        self._done       = False
        self._stars      = 0
        self._result_t   = 0.0    # countdown before auto-advance

        self._step_cd    = 0.0    # footstep sound cooldown
        self._mid1_spoken = False
        self._mid2_spoken = False

        # Surface for the corridor viewport
        self._surf = pygame.Surface((CORRIDOR_W, CORRIDOR_H))

        # Leg animation
        self._leg_t = 0.0

        bus.emit(EVT_BAX_SPEAK, line=random.choice(_BAX_START))

    # ----------------------------------------------------------------
    def handle_key(self, event: pygame.event.Event):
        if self._done:
            return
        if event.key in (pygame.K_SPACE, pygame.K_w, pygame.K_UP):
            if self._grounded:
                self._player_vy = JUMP_VY
                self._grounded  = False

    # ----------------------------------------------------------------
    def update(self, dt: float):
        if self._done:
            self._result_t -= dt
            return

        self._elapsed += dt
        self._stun_t   = max(0.0, self._stun_t - dt)
        self._leg_t   += dt

        # Footstep rhythm
        self._step_cd -= dt
        if self._step_cd <= 0.0 and self._grounded:
            bus.emit(EVT_DELIVERY_STEP)
            self._step_cd = 0.32

        # Auto-run
        self._player_x += RUN_SPEED * dt

        # Gravity
        self._player_vy += GRAVITY * dt
        self._player_y  += self._player_vy * dt

        # Floor collision
        self._grounded = False
        if self._player_y >= FLOOR_Y - PLAYER_H:
            self._player_y  = float(FLOOR_Y - PLAYER_H)
            self._player_vy = 0.0
            self._grounded  = True

        # Ceiling collision
        if self._player_y < CEIL_Y + 2:
            self._player_y  = float(CEIL_Y + 2)
            self._player_vy = max(0.0, self._player_vy)

        # Camera tracks player
        self._camera_x = self._player_x - PLAYER_X_FIXED

        # Update obstacles and check collisions
        t = self._elapsed
        for obs in self._obstacles:
            obs.update(dt, self._player_x - self._camera_x, self._player_x)

            if self._stun_t > 0:
                continue

            hit = False
            if isinstance(obs, Guard):
                hit = obs.collides(self._player_x, self._player_y)
            elif isinstance(obs, Gate):
                hit = obs.collides(self._player_x, self._player_y, t)
            elif isinstance(obs, MovingPlatform):
                if obs.collides_top(self._player_x, self._player_y, self._player_vy):
                    self._player_y  = obs.top_y - PLAYER_H
                    self._player_vy = 0.0
                    self._grounded  = True
            elif isinstance(obs, ScannerBeam):
                hit = obs.collides(self._player_x, self._player_y)

            if hit:
                self._hits   += 1
                self._stun_t  = 1.2
                bus.emit(EVT_DELIVERY_HIT)
                bus.emit(EVT_BAX_SPEAK, line=random.choice(_BAX_HIT))

        # Mid-run Bax updates
        prog = self._player_x / LEVEL_LENGTH
        if not self._mid1_spoken and prog > 0.33:
            self._mid1_spoken = True
            bus.emit(EVT_BAX_SPEAK, line=random.choice([
                "Third of the way through! Dodge the guards, yeah?",
                "I can see you on the station cameras. You look ridiculous. Keep going.",
                "Halfway soon. Don't get scanned, mate.",
            ]))
        if not self._mid2_spoken and prog > 0.66:
            self._mid2_spoken = True
            bus.emit(EVT_BAX_SPEAK, line=random.choice([
                "Two thirds done! One last push!",
                "Almost there — don't balls it now!",
                "Door's just ahead! I can see it! RUN!",
            ]))

        # Near-end Bax line
        if not self._near_end_spoken and self._player_x > LEVEL_LENGTH - 600:
            self._near_end_spoken = True
            bus.emit(EVT_BAX_SPEAK, line=random.choice(_BAX_NEAR_END))

        # Check completion
        if self._player_x >= LEVEL_LENGTH:
            self._finish()

    def _finish(self):
        self._done = True
        bus.emit(EVT_DELIVERY_DONE)
        if self._elapsed <= STAR_3_TIME and self._hits == 0:
            self._stars = 3
            bus.emit(EVT_BAX_SPEAK, line=random.choice(_BAX_3STAR))
        elif self._elapsed <= STAR_2_TIME and self._hits <= 1:
            self._stars = 2
            bus.emit(EVT_BAX_SPEAK, line=random.choice(_BAX_2STAR))
        else:
            self._stars = 1
            bus.emit(EVT_BAX_SPEAK, line=random.choice(_BAX_1STAR))
        self._result_t = 3.5

    # ----------------------------------------------------------------
    def draw(self, screen: pygame.Surface, screen_x: int, screen_y: int):
        """Render the corridor viewport onto screen at (screen_x, screen_y)."""
        surf = self._surf
        t    = self._elapsed

        # ── Corridor background ───────────────────────────────────────
        surf.fill((6, 10, 8))

        # Grid lines on walls
        for gx in range(0, CORRIDOR_W, 40):
            pygame.draw.line(surf, (12, 22, 14), (gx, 0), (gx, CORRIDOR_H), 1)
        for gy in range(0, CORRIDOR_H, 40):
            pygame.draw.line(surf, (12, 22, 14), (0, gy), (CORRIDOR_W, gy), 1)

        # Ceiling + floor strips
        pygame.draw.rect(surf, (20, 36, 20), (0, 0, CORRIDOR_W, CEIL_Y))
        pygame.draw.line(surf, (0, 160, 70), (0, CEIL_Y), (CORRIDOR_W, CEIL_Y), 2)
        pygame.draw.rect(surf, (18, 30, 18), (0, FLOOR_Y, CORRIDOR_W, CORRIDOR_H - FLOOR_Y))
        pygame.draw.line(surf, (0, 140, 60), (0, FLOOR_Y), (CORRIDOR_W, FLOOR_Y), 2)

        # ── Environmental detail (parallax bg at 50% camera speed) ───────
        bg_off = self._camera_x * 0.5

        # Overhead conduit pipes running the length of the corridor
        for py_c in (CEIL_Y + 5, CEIL_Y + 9):
            pygame.draw.line(surf, (10, 22, 12), (0, py_c), (CORRIDOR_W, py_c), 1)
        for cx_c in range(int(-bg_off % 60), CORRIDOR_W, 60):
            pygame.draw.line(surf, (8, 20, 10), (cx_c, CEIL_Y), (cx_c, CEIL_Y + 14), 2)

        # Propaganda posters along walls (world-space, parallax)
        poster_data = [
            ( 200, "YOUR DEBT IS YOUR IDENTITY",    (110, 60,  0)),
            ( 700, "LOCAL 404 PROTECTS OUR UNION",  (  0, 80, 40)),
            (1100, "CLONE WELLNESS PROGRAMME",       ( 80,  0, 80)),
            (1500, "REPORT UNLICENSED COURIERS",     (110, 70,  0)),
            (1900, "DEBT SETTLEMENT AVAILABLE",      (  0, 80, 40)),
            (2300, "DEBT IS SECURITY",               (110, 60,  0)),
            (2700, "YOUR CARGO IS OUR CONCERN",      (  0, 80, 40)),
            (3050, "STAY COMPLIANT. STAY ALIVE.",    ( 80,  0, 80)),
        ]
        f_poster = get_font(8)
        for bg_wx, text, col in poster_data:
            psx = int(bg_wx - bg_off)
            if -110 < psx < CORRIDOR_W + 10:
                pw_p, ph_p = 100, 20
                # Bottom poster (above floor strip)
                py_p = FLOOR_Y - 28
                pygame.draw.rect(surf, (int(col[0]*0.18), int(col[1]*0.18), int(col[2]*0.18)),
                                 (psx, py_p, pw_p, ph_p))
                pygame.draw.rect(surf, col, (psx, py_p, pw_p, ph_p), 1)
                surf.set_clip(pygame.Rect(psx + 1, py_p + 1, pw_p - 2, ph_p - 2))
                surf.blit(f_poster.render(text, True, col), (psx + 2, py_p + 4))
                surf.set_clip(None)
                # Top poster (below ceiling strip)
                py_t2 = CEIL_Y + 17
                pygame.draw.rect(surf, (int(col[0]*0.12), int(col[1]*0.12), int(col[2]*0.12)),
                                 (psx, py_t2, pw_p, ph_p))
                pygame.draw.rect(surf, (int(col[0]*0.5), int(col[1]*0.5), int(col[2]*0.5)),
                                 (psx, py_t2, pw_p, ph_p), 1)

        # Wall monitors (small screens showing debt data)
        f_mon = get_font(7)
        for mon_wx in (350, 900, 1450, 1950, 2450, 2950):
            msx = int(mon_wx - bg_off)
            if -50 < msx < CORRIDOR_W + 10:
                mon_y = CEIL_Y + 26
                pygame.draw.rect(surf, (8, 16, 10), (msx, mon_y, 38, 26))
                pygame.draw.rect(surf, (0, 60, 30), (msx, mon_y, 38, 26), 1)
                scroll = int((t * 18 + mon_wx * 0.08) % 54)
                for li, ln in enumerate(["DEBT: 847K cr", "CLONE #: 003", "QUOTA: 2/5", "404 ACTIVE"]):
                    ly = mon_y + 2 + li * 6 - scroll
                    if mon_y + 2 <= ly <= mon_y + 22:
                        surf.set_clip(pygame.Rect(msx + 1, mon_y + 1, 36, 24))
                        surf.blit(f_mon.render(ln, True, (0, 140, 60)), (msx + 2, ly))
                        surf.set_clip(None)

        # Background NPC silhouettes (slower parallax — 40% speed)
        bg_off2 = self._camera_x * 0.4
        for npc_wx, walk_dir in [(400, 1), (950, -1), (1550, 1), (2100, -1), (2700, 1)]:
            npc_wx2 = npc_wx + t * 16 * walk_dir
            nsx = int(npc_wx2 - bg_off2)
            if -25 < nsx < CORRIDOR_W + 20:
                ny2 = FLOOR_Y - 1
                lp2 = t * 2.8
                pygame.draw.rect(surf, (4, 14, 8), (nsx - 5, ny2 - 24, 10, 16))
                pygame.draw.circle(surf, (4, 14, 8), (nsx, ny2 - 30), 6)
                pygame.draw.line(surf, (4, 14, 8),
                                 (nsx - 2, ny2 - 8),
                                 (nsx - 4 + int(3 * math.sin(lp2)), ny2), 2)
                pygame.draw.line(surf, (4, 14, 8),
                                 (nsx + 2, ny2 - 8),
                                 (nsx + 4 + int(3 * math.sin(lp2 + math.pi)), ny2), 2)

        # Debt collection drone — slow drift, scan beam, blink light
        drone_wx = int(t * 22 + 450) % LEVEL_LENGTH
        d_sx = int(drone_wx - bg_off)
        if -40 < d_sx < CORRIDOR_W + 20:
            d_sy = CEIL_Y + 28 + int(8 * math.sin(t * 0.7))
            pygame.draw.ellipse(surf, (10, 22, 12), (d_sx - 20, d_sy - 7, 40, 14))
            pygame.draw.ellipse(surf, (0, 60, 30),  (d_sx - 20, d_sy - 7, 40, 14), 1)
            for r_a in (0, 180):
                rax = d_sx + int(20 * math.cos(math.radians(r_a)))
                ray = d_sy + int(7  * math.sin(math.radians(r_a)))
                pygame.draw.circle(surf, (0, 40, 20), (rax, ray), 4)
            # Downward scan beam
            beam_h = FLOOR_Y - d_sy - 7
            if beam_h > 0:
                bm = pygame.Surface((12, beam_h), pygame.SRCALPHA)
                bm.fill((200, 0, 0, int(50 + 30 * math.sin(t * 2.0))))
                surf.blit(bm, (d_sx - 6, d_sy + 7))
            if abs(math.sin(t * 4.0)) > 0.7:
                pygame.draw.circle(surf, (220, 40, 40), (d_sx, d_sy - 5), 2)
            surf.blit(f_poster.render("COLLECT-BOT", True, (0, 60, 30)),
                      (d_sx - 28, d_sy + 8))

        # Ceiling lights at intervals
        light_spacing = 180
        first_light = int(self._camera_x / light_spacing) * light_spacing - light_spacing
        for lx in range(first_light, int(self._camera_x) + CORRIDOR_W + light_spacing, light_spacing):
            sx = lx - int(self._camera_x)
            flicker = 1.0 - 0.08 * math.sin(t * 7.3 + lx * 0.01)
            col = (0, int(180 * flicker), int(80 * flicker))
            pygame.draw.rect(surf, col, (sx - 12, CEIL_Y + 2, 24, 6))
            # Light cone
            pygame.draw.polygon(surf, (0, 20, 8),
                                [(sx - 10, CEIL_Y + 8), (sx + 10, CEIL_Y + 8),
                                 (sx + 30, FLOOR_Y - 10), (sx - 30, FLOOR_Y - 10)])

        # ── Obstacles ─────────────────────────────────────────────────
        for obs in self._obstacles:
            sx = obs.x - self._camera_x
            if -200 < sx < CORRIDOR_W + 200:
                obs.draw(surf, self._camera_x, t)

        # ── Player ────────────────────────────────────────────────────
        px = PLAYER_X_FIXED
        py = int(self._player_y)
        stun_flash = self._stun_t > 0 and int(t * 10) % 2 == 0

        if not stun_flash:
            # Body
            body_col = (0, 210, 100) if self._grounded else (0, 180, 255)
            pygame.draw.rect(surf, body_col, (px - PLAYER_W // 2, py, PLAYER_W, PLAYER_H))
            pygame.draw.rect(surf, (0, 255, 140), (px - PLAYER_W // 2, py, PLAYER_W, PLAYER_H), 1)
            # Head
            pygame.draw.rect(surf, (0, 190, 90),
                             (px - 7, py - 12, 14, 12))
            pygame.draw.rect(surf, (0, 240, 120),
                             (px - 7, py - 12, 14, 12), 1)
            # Visor
            pygame.draw.rect(surf, (0, 150, 220), (px - 4, py - 10, 8, 4))
            # Package on back
            pygame.draw.rect(surf, (200, 150, 0),
                             (px + PLAYER_W // 2, py + 4, 10, 14))
            pygame.draw.rect(surf, (255, 190, 0),
                             (px + PLAYER_W // 2, py + 4, 10, 14), 1)
            # Legs (animated)
            if self._grounded:
                leg_phase = self._leg_t * 8.0
                l1 = int(6 * math.sin(leg_phase))
                l2 = int(6 * math.sin(leg_phase + math.pi))
                pygame.draw.line(surf, (0, 160, 70),
                                 (px - 4, py + PLAYER_H),
                                 (px - 4, py + PLAYER_H + 10 + l1), 2)
                pygame.draw.line(surf, (0, 160, 70),
                                 (px + 4, py + PLAYER_H),
                                 (px + 4, py + PLAYER_H + 10 + l2), 2)
            else:
                pygame.draw.line(surf, (0, 160, 70),
                                 (px - 4, py + PLAYER_H),
                                 (px - 8, py + PLAYER_H + 8), 2)
                pygame.draw.line(surf, (0, 160, 70),
                                 (px + 4, py + PLAYER_H),
                                 (px + 10, py + PLAYER_H + 6), 2)

        # ── Delivery door on the far right ────────────────────────────
        door_world_x = LEVEL_LENGTH - 60
        door_sx = door_world_x - self._camera_x
        if -20 < door_sx < CORRIDOR_W + 20:
            pulse = 0.6 + 0.4 * math.sin(t * 3.0)
            dcol  = (int(0 + 200 * pulse), int(200 * pulse), 0)
            pygame.draw.rect(surf, (10, 28, 10), (int(door_sx), CEIL_Y, 50, FLOOR_Y - CEIL_Y))
            pygame.draw.rect(surf, dcol, (int(door_sx), CEIL_Y, 50, FLOOR_Y - CEIL_Y), 2)
            f = get_font(11, bold=True)
            s = f.render("DROP", True, dcol)
            surf.blit(s, (int(door_sx) + 25 - s.get_width() // 2,
                          (CEIL_Y + FLOOR_Y) // 2 - s.get_height() // 2))

        # ── Progress bar ──────────────────────────────────────────────
        prog = min(1.0, self._player_x / LEVEL_LENGTH)
        pygame.draw.rect(surf, (10, 22, 10), (0, CORRIDOR_H - 8, CORRIDOR_W, 8))
        pygame.draw.rect(surf, (0, 180, 80),
                         (0, CORRIDOR_H - 8, int(CORRIDOR_W * prog), 8))

        # ── HUD ───────────────────────────────────────────────────────
        f   = get_font(13)
        fsm = get_font(11)
        timer_col = (0, 220, 100) if self._elapsed < STAR_3_TIME else \
                    (255, 180, 0) if self._elapsed < STAR_2_TIME else (220, 60, 60)
        surf.blit(f.render(f"TIME  {self._elapsed:>5.1f}s", True, timer_col), (6, 4))
        hits_col = (220, 60, 60) if self._hits > 0 else (0, 180, 80)
        surf.blit(f.render(f"HITS  {self._hits}", True, hits_col), (140, 4))
        surf.blit(fsm.render("SPACE / W = JUMP", True, (40, 70, 40)), (CORRIDOR_W - 130, 4))

        # Star preview
        for i in range(3):
            filled = (self._elapsed <= STAR_3_TIME and self._hits == 0 and i < 3) or \
                     (self._elapsed <= STAR_2_TIME and self._hits <= 1 and i < 2) or i < 1
            sc = (255, 210, 0) if filled else (40, 50, 40)
            pygame.draw.polygon(surf, sc,
                                [(250 + i * 18, 14), (254 + i * 18, 6),
                                 (258 + i * 18, 14), (250 + i * 18, 9),
                                 (258 + i * 18, 9)])

        # ── Result overlay ────────────────────────────────────────────
        if self._done:
            ov = pygame.Surface((CORRIDOR_W, CORRIDOR_H), pygame.SRCALPHA)
            ov.fill((0, 0, 0, 160))
            surf.blit(ov, (0, 0))
            fh = get_font(20, bold=True)
            label_col = [(220, 60, 60), (255, 180, 0), (0, 240, 110)][self._stars - 1]
            label_txt = ["★☆☆  1 STAR", "★★☆  2 STARS", "★★★  3 STARS!"][self._stars - 1]
            ls = fh.render(label_txt, True, label_col)
            surf.blit(ls, (CORRIDOR_W // 2 - ls.get_width() // 2, CORRIDOR_H // 2 - 20))
            ts = f.render(f"{self._elapsed:.1f}s  ·  {self._hits} hit(s)", True, (140, 140, 140))
            surf.blit(ts, (CORRIDOR_W // 2 - ts.get_width() // 2, CORRIDOR_H // 2 + 10))

        screen.blit(surf, (screen_x, screen_y))

    # ----------------------------------------------------------------
    @property
    def is_done(self) -> bool:
        return self._done and self._result_t <= 0

    @property
    def stars(self) -> int:
        return self._stars
