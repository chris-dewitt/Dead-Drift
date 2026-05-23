"""
Mid-run black market between sectors.
Appears after sectors 3 and 6 (configurable via SHOP_SECTORS).
Player spends run credits (recovered debt) on one-time upgrades.
"""
from __future__ import annotations
import math
import random
import pygame
from config import settings as S

SHOP_SECTORS = {3, 6}

_INTRO_DURATION  = 3.8   # seconds before items appear; any key skips
_TYPEWRITER_RATE = 30    # chars per second during intro

_TAG_COL: dict[str, tuple] = {
    "hull_patch":       (0,   200, 100),
    "thrust_boost":     (60,  160, 255),
    "jammer":           (200,  50, 255),
    "intel":            (255, 200,   0),
    "repair_drone":     (0,   255, 128),
    "cargo_stabilizer": (0,   200, 255),
    "scrap_bullets":    (255,  80,  50),
}

_VENDOR_LINES = [
    "Cash only. No IDs. No questions. Some questions.",
    "Discretion costs extra. You look all out.",
    "Don't tell Local 404 where you got this. I mean it.",
    "Everything's legal. Technically. In this corridor.",
    "Scanner sweep in four minutes. Pick fast.",
    "You look like trouble. I like trouble. Briefly.",
    "No names. You're 'Customer'. I'm 'Not Here'. Clear?",
    "The jammer's fresh off a Union sergeant. Don't ask.",
]

_LOCATIONS = [
    "CORRIDOR 7-G  ░░  DEAD ZONE SECTOR",
    "JUNCTION 404-B  ░░  PAST SCANNER SWEEP",
    "SUB-LEVEL NINE  ░░  UNREGISTERED NODE",
    "TRANSIT RING C  ░░  MAINTENANCE CRAWL",
]

_STEAM_X_FRACS = [0.06, 0.28, 0.72, 0.94]

# Module-level font cache — avoids re-creating fonts every frame
_FONT_CACHE: dict[tuple, pygame.font.Font] = {}


def _font(size: int, bold: bool = False) -> pygame.font.Font:
    key = (size, bold)
    if key not in _FONT_CACHE:
        _FONT_CACHE[key] = pygame.font.SysFont("monospace", size, bold=bold)
    return _FONT_CACHE[key]


# ---------------------------------------------------------------------------
class _ShopItem:
    def __init__(self, name: str, desc: str, detail: str, cost: int, tag: str):
        self.name   = name
        self.desc   = desc
        self.detail = detail
        self.cost   = cost
        self.tag    = tag

    def apply(self, ship, run_mgr):
        if self.tag == "hull_patch":
            ship.hull = min(S.HULL_MAX, ship.hull + 50.0)
        elif self.tag == "thrust_boost":
            from ship.modules.thruster import Thruster
            for mod in ship.chain.get_active("propulsion"):
                if isinstance(mod, Thruster):
                    mod.inject_fuel_mix(1.35, 40.0)
        elif self.tag == "jammer":
            for barge in getattr(run_mgr, "_barges", []):
                barge._intercept_cd = max(barge._intercept_cd, S.JAMMER_COOLDOWN)
        elif self.tag == "intel":
            from core.event_bus import bus, EVT_BAX_SPEAK
            bus.emit(EVT_BAX_SPEAK, line=random.choice([
                "Intel package uploaded. I've flagged their weak spots in the terminal.",
                "Black market intel drop. Their comms use the word 'Blevins' as a back door.",
                "Encrypted manifest. Their dispatch code is 'article 7'. Use it.",
            ]))
        elif self.tag == "repair_drone":
            ship.hull = min(S.HULL_MAX, ship.hull + 110.0)
        elif self.tag == "cargo_stabilizer":
            if ship.cargo is not None:
                ship.cargo.integrity = min(100.0, ship.cargo.integrity + 60.0)
                ship.cargo.is_damaged = ship.cargo.integrity < 70.0
                if hasattr(ship.cargo, "sorrow_level"):
                    ship.cargo.sorrow_level = max(0.0, ship.cargo.sorrow_level - 0.5)
                if hasattr(ship.cargo, "spore_level"):
                    ship.cargo.spore_level  = max(0.0, ship.cargo.spore_level - 0.5)
        elif self.tag == "scrap_bullets":
            if hasattr(ship, "gun"):
                ship.gun._cooldown = 0.0
                ship.gun._jam_t    = 0.0


_POOL_ALL: list[_ShopItem] = [
    _ShopItem(
        "Hull Patch Pack",    "+50 hull integrity",
        "Grey-market composite panels. Won't pass inspection.",
        1000, "hull_patch",
    ),
    _ShopItem(
        "Thrust Catalyst",    "+35% thrust  /  40 seconds",
        "Fuel additive. Technically illegal. Practically essential.",
        800, "thrust_boost",
    ),
    _ShopItem(
        "EM Jammer Unit",     "Barge harpoon lock disabled  /  90s",
        "Scrambles harpoon IFF signal. Local 404 hates these.",
        1500, "jammer",
    ),
    _ShopItem(
        "Black Market Intel", "NLP exploit hint from vendor",
        "Stolen repo dispatch logs. One-use. May be outdated.",
        600, "intel",
    ),
    _ShopItem(
        "Auto-Repair Drone",  "+110 hull integrity",
        "Salvaged MediCorp drone. Refurbished. Mostly.",
        2200, "repair_drone",
    ),
    _ShopItem(
        "Cargo Stabilizer",   "Restore cargo integrity, suppress effects",
        "Calms the cargo. Briefly. We hope.",
        1100, "cargo_stabilizer",
    ),
    _ShopItem(
        "Scrap Ammo Clip",    "Resets gun cooldown / clears jams",
        "Loose rounds from a Union sergeant's locker. Don't ask.",
        500, "scrap_bullets",
    ),
]


def _pick_stock(run_mgr, ship) -> list[_ShopItem]:
    """Pick 4 items based on run context — gives the shop dynamic flavour."""
    hull_pct      = ship.hull / S.HULL_MAX if ship is not None else 1.0
    tether_hits   = getattr(run_mgr, "_run_tether_hits", 0)
    cargo_damaged = (ship is not None and ship.cargo is not None
                     and getattr(ship.cargo, "is_damaged", False))
    gun_jammed    = (ship is not None and hasattr(ship, "gun")
                     and getattr(ship.gun, "is_jammed", False))
    sector_idx    = getattr(run_mgr, "_sector_index", 0)

    by_tag = {it.tag: it for it in _POOL_ALL}
    picks: list[_ShopItem] = []

    if hull_pct < 0.45:
        picks.append(by_tag["repair_drone"])
    if tether_hits >= 2:
        picks.append(by_tag["jammer"])
    if cargo_damaged:
        picks.append(by_tag["cargo_stabilizer"])
    if gun_jammed:
        picks.append(by_tag["scrap_bullets"])

    fillers = ["hull_patch", "thrust_boost", "intel"]
    if sector_idx >= 2:
        fillers = ["thrust_boost", "hull_patch", "intel"]
    for tag in fillers:
        if by_tag[tag] not in picks:
            picks.append(by_tag[tag])

    for tag in ("hull_patch", "intel", "jammer"):
        if len(picks) >= 4:
            break
        if by_tag[tag] not in picks:
            picks.append(by_tag[tag])

    return picks[:4]


# ---------------------------------------------------------------------------
class ShopScreen:
    """
    Rendered from game.py in GameState.SHOP.
    Call draw(screen, t) each frame. handle_key(event) for input.
    is_done becomes True when the player exits.
    """

    def __init__(self, run_mgr, ship):
        self.run_mgr  = run_mgr
        self.ship     = ship
        self.is_done  = False
        self._cursor  = 0
        self._items   = _pick_stock(run_mgr, ship)
        self._bought: set[int] = set()
        self._msg     = ""
        self._msg_t   = 0.0

        # Intro sequence state
        self._phase       = "intro"
        self._intro_t     = 0.0
        self._intro_chars = 0

        self._vendor_t    = 0.0
        self._vendor_line = random.choice(_VENDOR_LINES)
        self._location    = random.choice(_LOCATIONS)

        # Per-sign flicker seed (one per background neon sign)
        self._flicker = [random.uniform(0, 10) for _ in range(4)]

        # Steam particles: [x, y, vx, vy, life, size]
        self._steam: list[list[float]] = []
        self._steam_t = 0.0

    # ------------------------------------------------------------------
    @property
    def _balance(self) -> int:
        return max(0, self.run_mgr._run_debt_reduced)

    def handle_key(self, event: pygame.event.Event):
        if self._phase == "intro":
            self._phase = "browse"
            return
        if event.key in (pygame.K_UP, pygame.K_w):
            self._cursor = (self._cursor - 1) % len(self._items)
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self._cursor = (self._cursor + 1) % len(self._items)
        elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
            self._try_purchase()
        elif event.key in (pygame.K_ESCAPE, pygame.K_j):
            from core.event_bus import bus, EVT_SHOP_SKIP
            if not self._bought:
                bus.emit(EVT_SHOP_SKIP)
            self.is_done = True

    def _try_purchase(self):
        if self._cursor in self._bought:
            self._flash("Already purchased.")
            return
        item = self._items[self._cursor]
        if self._balance < item.cost:
            self._flash(f"Insufficient credits. Need {item.cost - self._balance:,} more.")
            return
        self.run_mgr._run_debt_reduced -= item.cost
        self.run_mgr.meta.add_debt(item.cost)
        self._bought.add(self._cursor)
        item.apply(self.ship, self.run_mgr)
        self._flash(f"Purchased: {item.name}.")
        from core.event_bus import bus, EVT_SHOP_BUY
        bus.emit(EVT_SHOP_BUY, tag=item.tag, name=item.name)

    def _flash(self, msg: str):
        self._msg   = msg
        self._msg_t = 2.2

    # ------------------------------------------------------------------
    def update(self, dt: float):
        self._msg_t    = max(0.0, self._msg_t - dt)
        self._vendor_t += dt

        if self._phase == "intro":
            self._intro_t += dt
            self._intro_chars = min(len(self._vendor_line),
                                    int(self._intro_t * _TYPEWRITER_RATE))
            if self._intro_t >= _INTRO_DURATION:
                self._phase = "browse"

        # Steam particles
        W, H = S.SCREEN_W, S.SCREEN_H
        self._steam = [p for p in self._steam if p[4] > 0]
        for p in self._steam:
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[4] -= dt

        self._steam_t -= dt
        if self._steam_t <= 0:
            self._steam_t = random.uniform(0.12, 0.25)
            sx = random.choice(_STEAM_X_FRACS) * W + random.uniform(-10, 10)
            self._steam.append([
                sx,
                H * 0.88 + random.uniform(-5, 5),
                random.uniform(-5, 5),
                random.uniform(-26, -14),
                random.uniform(2.0, 3.6),
                random.uniform(2.0, 5.0),
            ])

    # ------------------------------------------------------------------
    def draw(self, screen: pygame.Surface, t: float):
        W, H = S.SCREEN_W, S.SCREEN_H
        cx   = W // 2

        _draw_alley_bg(screen, W, H, t, self._flicker)
        _draw_steam(screen, self._steam)

        if self._phase == "intro":
            self._draw_intro(screen, cx, W, H, t)
        else:
            self._draw_browse(screen, cx, W, H, t)

    # ------------------------------------------------------------------
    def _draw_intro(self, surf: pygame.Surface, cx: int, W: int, H: int, t: float):
        # Dark overlay
        ov = pygame.Surface((W, H), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 155))
        surf.blit(ov, (0, 0))

        # Location breadcrumb
        loc_s = _font(10).render(self._location, True, (70, 70, 110))
        surf.blit(loc_s, (cx - loc_s.get_width() // 2, 36))

        # Title
        hdr = _font(18, bold=True).render("[ BLACK MARKET ]", True, (190, 130, 0))
        surf.blit(hdr, (cx - hdr.get_width() // 2, 56))
        pygame.draw.line(surf, (110, 75, 0),
                         (cx - 170, 82), (cx + 170, 82), 1)

        # Large vendor portrait
        vy = int(H * 0.36)
        _draw_vendor_large(surf, cx, vy, t)

        # Vendor greeting — typewriter reveal
        shown = self._vendor_line[:self._intro_chars]
        lines = _wrap(shown, _font(13), 460)
        ty = vy + 110
        lh = 20
        for i, ln in enumerate(lines):
            ls = _font(13).render(ln, True, (200, 170, 80))
            surf.blit(ls, (cx - ls.get_width() // 2, ty + i * lh))

        # Blinking cursor while typing
        if self._intro_chars < len(self._vendor_line):
            if int(t * 3) % 2 == 0:
                last_w = _font(13).size(lines[-1])[0] if lines else 0
                cursor_x = cx + last_w // 2 + 3
                cursor_y = ty + (len(lines) - 1) * lh
                surf.fill((200, 170, 80), (cursor_x, cursor_y + 2, 7, 13))

        # Sector footer
        sec_s = _font(10).render(
            f"SECTOR {self.run_mgr.sector_num} COMPLETE  //  NEXT DEPARTURE LOADING",
            True, (55, 55, 85))
        surf.blit(sec_s, (cx - sec_s.get_width() // 2, H - 72))

        # "any key" prompt — fades in after 0.8s
        if self._intro_t > 0.8 and int(t * 2) % 2 == 0:
            pk = _font(11).render("[ PRESS ANY KEY ]", True, (140, 115, 50))
            surf.blit(pk, (cx - pk.get_width() // 2, H - 50))

    # ------------------------------------------------------------------
    def _draw_browse(self, surf: pygame.Surface, cx: int, W: int, H: int, t: float):
        # Semi-transparent backing panel
        panel = pygame.Rect(cx - 420, 28, 840, H - 56)
        psurf = pygame.Surface((panel.w, panel.h), pygame.SRCALPHA)
        psurf.fill((4, 4, 10, 215))
        surf.blit(psurf, panel.topleft)
        pygame.draw.rect(surf, (90, 62, 0), panel, 1)
        pygame.draw.rect(surf, (45, 30, 0), panel.inflate(-4, -4), 1)
        _corner_caps(surf, panel, (190, 130, 0))

        # Header
        hdr = _font(14, bold=True).render(
            "[ BLACK MARKET  //  UNREGISTERED VENDOR ]", True, (190, 130, 0))
        surf.blit(hdr, (cx - hdr.get_width() // 2, 42))
        loc_s = _font(10).render(self._location, True, (55, 55, 85))
        surf.blit(loc_s, (cx - loc_s.get_width() // 2, 62))
        pygame.draw.line(surf, (90, 62, 0), (cx - 390, 80), (cx + 390, 80), 1)

        # Balance
        bal_s = _font(14, bold=True).render(
            f"AVAILABLE:  {self._balance:>8,} cr", True, (55, 200, 100))
        surf.blit(bal_s, (cx - 390, 86))

        # Vendor portrait + line (right column)
        _draw_vendor_small(surf, cx + 326, 158, t)
        vlines = _wrap(self._vendor_line, _font(11), 210)
        for i, ln in enumerate(vlines):
            vs = _font(11).render(ln, True, (130, 105, 48))
            surf.blit(vs, (cx + 136, 116 + i * 16))

        # Item cards
        item_y = 198
        for idx, item in enumerate(self._items):
            bought   = idx in self._bought
            selected = idx == self._cursor
            can_buy  = not bought and self._balance >= item.cost
            tcol     = _TAG_COL.get(item.tag, (140, 140, 140))

            row = pygame.Rect(cx - 390, item_y, 668, 82)

            # Row fill
            bg = (8, 14, 8) if bought else ((20, 16, 6) if selected else (7, 7, 11))
            pygame.draw.rect(surf, bg, row)

            if not bought:
                border_col = (140, 100, 0) if selected else (50, 44, 65)
                pygame.draw.rect(surf, border_col, row, 1)
                # Left accent bar
                ab_alpha = 210 if selected else 90
                ab = pygame.Surface((4, row.h), pygame.SRCALPHA)
                ab.fill((*tcol, ab_alpha))
                surf.blit(ab, (row.x, row.y))
            else:
                pygame.draw.rect(surf, (28, 46, 28), row, 1)

            # Selection glow
            if selected and not bought:
                pulse = 0.45 + 0.55 * abs(math.sin(t * 3.5))
                gs = pygame.Surface((row.w + 6, row.h + 6), pygame.SRCALPHA)
                gc = tuple(int(v * pulse * 0.35) for v in tcol)
                pygame.draw.rect(gs, (*gc, 70), gs.get_rect(), 3)
                surf.blit(gs, (row.x - 3, row.y - 3))
                # Arrow cursor
                ac = tuple(int(v * pulse) for v in tcol)
                pygame.draw.polygon(surf, ac, [
                    (row.x - 15, item_y + 41),
                    (row.x - 5,  item_y + 35),
                    (row.x - 5,  item_y + 47),
                ])

            # Tag label (top-left, small)
            tg_col = (45, 90, 45) if bought else (tcol if can_buy else
                      tuple(v // 3 for v in tcol))
            tg = _font(10, bold=True).render(
                item.tag.upper().replace("_", " "), True, tg_col)
            surf.blit(tg, (row.x + 14, item_y + 5))

            # Item name
            name_col = (55, 115, 55) if bought else (
                (215, 185, 70) if can_buy else (110, 95, 58))
            ns = _font(14, bold=True).render(
                ("[SOLD]  " if bought else "") + item.name, True, name_col)
            surf.blit(ns, (row.x + 14, item_y + 18))

            # Description + detail
            ds = _font(12).render(item.desc, True, (155, 140, 95))
            surf.blit(ds, (row.x + 14, item_y + 38))
            det = _font(11).render(item.detail, True, (75, 75, 98))
            surf.blit(det, (row.x + 14, item_y + 55))

            # Cost (right-aligned)
            cost_col = (55, 175, 55) if bought else (
                (215, 195, 60) if can_buy else (160, 55, 55))
            cost_str = "PURCHASED" if bought else f"{item.cost:,} cr"
            cs = _font(14).render(cost_str, True, cost_col)
            surf.blit(cs, (row.right - cs.get_width() - 14, item_y + 28))

            item_y += 94

        # Status message
        if self._msg_t > 0:
            alpha = min(255, int(self._msg_t * 180))
            is_err = "Insufficient" in self._msg or "Already" in self._msg
            mc = (220, 75, 75) if is_err else (75, 215, 115)
            ms = _font(12).render(self._msg, True, mc)
            ms.set_alpha(alpha)
            surf.blit(ms, (cx - ms.get_width() // 2, item_y + 8))

        # Footer
        pygame.draw.line(surf, (70, 48, 0),
                         (cx - 390, H - 76), (cx + 390, H - 76), 1)
        ctrl = _font(10, bold=True).render(
            "↑ ↓  Navigate     ENTER  Purchase     J / ESC  Leave",
            True, (115, 95, 38))
        surf.blit(ctrl, (cx - ctrl.get_width() // 2, H - 62))
        disc = _font(10).render(
            "Non-refundable. No exceptions. Especially not yours.",
            True, (45, 45, 65))
        surf.blit(disc, (cx - disc.get_width() // 2, H - 44))


# ---------------------------------------------------------------------------
# Atmospheric background

def _draw_alley_bg(surf: pygame.Surface, W: int, H: int, t: float,
                   flicker: list[float]):
    surf.fill((4, 4, 8))

    # Perspective floor grid — vanishing point at screen center-ish
    vp_x, vp_y = W // 2, int(H * 0.56)
    for ri in range(9):
        gy = vp_y + (H - vp_y) * ri // 8
        pygame.draw.line(surf, (13, 11, 20), (0, gy), (W, gy), 1)
    for ci in range(13):
        bx = int(W * ci / 12)
        pygame.draw.line(surf, (13, 11, 20), (vp_x, vp_y), (bx, H), 1)

    # Wall panels — left strip
    strip_h = (H - 130) // 7
    for i in range(7):
        ry = 70 + i * strip_h
        pygame.draw.rect(surf, (9, 8, 14), (0, ry, 105, strip_h - 3), 1)
    # Wall panels — right strip
    for i in range(7):
        ry = 70 + i * strip_h
        pygame.draw.rect(surf, (9, 8, 14), (W - 105, ry, 105, strip_h - 3), 1)

    # Overhead pipes
    for py, pw, pc in [(20, 5, (44, 38, 54)), (36, 3, (36, 32, 46)), (50, 2, (26, 23, 36))]:
        pygame.draw.line(surf, pc, (0, py), (W, py), pw)
        for px in range(55, W, 95):
            pygame.draw.rect(surf, (58, 52, 68), (px - 6, py - 4, 12, pw + 8))
            pygame.draw.rect(surf, (75, 68, 85), (px - 6, py - 4, 12, pw + 8), 1)

    # Neon signs
    sign_data = [
        (int(W * 0.10), 68,  "VOID GOODS",       (0,   200, 255), flicker[0]),
        (int(W * 0.73), 50,  "NO SURVEILLANCE",  (200,  50, 255), flicker[1]),
        (int(W * 0.88), 86,  "GREY MARKET",      (255, 130,   0), flicker[2]),
        (int(W * 0.34), 34,  "COLD STORAGE",     (0,   220, 180), flicker[3]),
    ]
    fsign = _font(10, bold=True)
    for sx, sy, txt, col, seed in sign_data:
        # Flicker: two independent sine waves — sign goes dark when both low
        on = (math.sin(t * 7.1 + seed * 13.7) > -0.92 and
              math.sin(t * 3.3 + seed * 4.9) > -0.85)
        if not on:
            # Fast buzz flash
            if math.sin(t * 22.0 + seed) < 0.6:
                continue
        intensity = 0.6 + 0.4 * abs(math.sin(t * 1.9 + seed * 2.1))
        c = tuple(min(255, int(v * intensity)) for v in col)
        s = fsign.render(txt, True, c)
        sw, sh = s.get_size()
        sr = pygame.Rect(sx - sw // 2 - 7, sy - 3, sw + 14, sh + 6)
        pygame.draw.rect(surf, (14, 11, 18), sr)
        pygame.draw.rect(surf, c, sr, 1)
        surf.blit(s, (sx - sw // 2, sy))

    # Crates — left side
    for cy, cw, ch in [(H - 128, 56, 42), (H - 170, 42, 36), (H - 204, 50, 28)]:
        r = pygame.Rect(40, cy, cw, ch)
        pygame.draw.rect(surf, (10, 8, 6), r)
        pygame.draw.rect(surf, (46, 36, 16), r, 1)
        pygame.draw.line(surf, (34, 26, 10), (40, cy + ch // 2), (40 + cw, cy + ch // 2), 1)
        pygame.draw.line(surf, (34, 26, 10), (40 + cw // 2, cy), (40 + cw // 2, cy + ch), 1)

    # Crates — right side
    for cy, cw, ch in [(H - 122, 50, 38), (H - 160, 44, 34)]:
        r = pygame.Rect(W - 96, cy, cw, ch)
        pygame.draw.rect(surf, (10, 8, 6), r)
        pygame.draw.rect(surf, (46, 36, 16), r, 1)
        pygame.draw.line(surf, (34, 26, 10),
                         (W - 96, cy + ch // 2), (W - 46, cy + ch // 2), 1)

    # Scanlines
    _scanlines(surf)


# ---------------------------------------------------------------------------
# Steam particles

def _draw_steam(surf: pygame.Surface, particles: list[list[float]]):
    for p in particles:
        x, y, _vx, _vy, life, size = p
        alpha = max(0, min(85, int(life * 32)))
        if alpha < 4:
            continue
        r = max(1, int(size))
        ps = pygame.Surface((r * 2 + 2, r * 2 + 2), pygame.SRCALPHA)
        pygame.draw.circle(ps, (195, 195, 215, alpha), (r + 1, r + 1), r)
        surf.blit(ps, (int(x) - r - 1, int(y) - r - 1))


# ---------------------------------------------------------------------------
# Vendor portraits

def _draw_vendor_large(surf: pygame.Surface, cx: int, cy: int, t: float):
    """Detailed shady vendor, ~130px tall. cy = vertical midpoint."""
    bob = int(math.sin(t * 1.4) * 2.5)

    # Coat/body
    pygame.draw.polygon(surf, (11, 9, 15), [
        (cx - 26, cy + 68 + bob), (cx + 26, cy + 68 + bob),
        (cx + 20, cy + 18 + bob), (cx - 20, cy + 18 + bob),
    ])
    pygame.draw.polygon(surf, (58, 48, 75), [
        (cx - 26, cy + 68 + bob), (cx + 26, cy + 68 + bob),
        (cx + 20, cy + 18 + bob), (cx - 20, cy + 18 + bob),
    ], 1)
    # Coat seam
    pygame.draw.line(surf, (38, 30, 50),
                     (cx - 20, cy + 18 + bob), (cx - 26, cy + 68 + bob), 1)
    pygame.draw.line(surf, (38, 30, 50),
                     (cx + 20, cy + 18 + bob), (cx + 26, cy + 68 + bob), 1)

    # Shoulders
    pygame.draw.polygon(surf, (15, 12, 20), [
        (cx - 42, cy + 27 + bob), (cx + 42, cy + 27 + bob),
        (cx + 30, cy + 16 + bob), (cx - 30, cy + 16 + bob),
    ])
    pygame.draw.polygon(surf, (66, 56, 82), [
        (cx - 42, cy + 27 + bob), (cx + 42, cy + 27 + bob),
        (cx + 30, cy + 16 + bob), (cx - 30, cy + 16 + bob),
    ], 1)

    # Hood
    pygame.draw.polygon(surf, (13, 11, 17), [
        (cx - 28, cy - 50 + bob), (cx + 28, cy - 50 + bob),
        (cx + 34, cy + 12 + bob), (cx + 18, cy + 16 + bob),
        (cx - 18, cy + 16 + bob), (cx - 34, cy + 12 + bob),
    ])
    pygame.draw.polygon(surf, (66, 56, 82), [
        (cx - 28, cy - 50 + bob), (cx + 28, cy - 50 + bob),
        (cx + 34, cy + 12 + bob), (cx + 18, cy + 16 + bob),
        (cx - 18, cy + 16 + bob), (cx - 34, cy + 12 + bob),
    ], 1)

    # Face shadow
    pygame.draw.ellipse(surf, (5, 4, 7), (cx - 17, cy - 42 + bob, 34, 30))

    # Visor bar
    vp = 0.5 + 0.5 * abs(math.sin(t * 2.2))
    vc = (int(0 * vp), int(175 * vp), int(255 * vp))
    pygame.draw.rect(surf, vc, (cx - 14, cy - 30 + bob, 28, 5))
    vgs = pygame.Surface((38, 14), pygame.SRCALPHA)
    pygame.draw.rect(vgs, (*vc, 35), vgs.get_rect())
    surf.blit(vgs, (cx - 19, cy - 32 + bob))

    # Eyes above visor
    ep = 0.4 + 0.3 * abs(math.sin(t * 1.2))
    ec = (int(215 * ep), int(138 * ep), 0)
    pygame.draw.circle(surf, ec, (cx - 7, cy - 35 + bob), 2)
    pygame.draw.circle(surf, ec, (cx + 7, cy - 35 + bob), 2)

    # Datapad (left hand area)
    dp_x, dp_y = cx - 38, cy + 42 + bob
    pygame.draw.rect(surf, (14, 12, 20), (dp_x, dp_y, 22, 16))
    pygame.draw.rect(surf, (38, 32, 52), (dp_x, dp_y, 22, 16), 1)
    if int(t * 4) % 3 != 0:
        sc = (0, 95, 170) if int(t * 2) % 2 == 0 else (0, 75, 145)
        pygame.draw.rect(surf, sc, (dp_x + 2, dp_y + 2, 18, 10))
        pygame.draw.line(surf, (0, 175, 255),
                         (dp_x + 4, dp_y + 5), (dp_x + 16, dp_y + 5), 1)
        pygame.draw.line(surf, (0, 115, 195),
                         (dp_x + 4, dp_y + 8), (dp_x + 11, dp_y + 8), 1)

    # Arm circuit lines
    ag = int(55 * (0.5 + 0.5 * math.sin(t * 3.0)))
    for ay in [cy + 30 + bob, cy + 36 + bob]:
        pygame.draw.line(surf, (0, ag, ag * 2),
                         (cx - 36, ay), (cx - 22, ay), 1)

    # Floating holo-display above datapad
    holo_a = int(38 + 28 * abs(math.sin(t * 2.8)))
    hs = pygame.Surface((24, 16), pygame.SRCALPHA)
    pygame.draw.rect(hs, (0, 175, 255, holo_a), hs.get_rect(), 1)
    if int(t * 3) % 2 == 0:
        pygame.draw.line(hs, (0, 255, 200, holo_a // 2), (2, 4), (16, 4), 1)
        pygame.draw.line(hs, (0, 200, 255, holo_a // 2), (2, 8), (10, 8), 1)
    surf.blit(hs, (cx - 50, cy + 20 + bob))


def _draw_vendor_small(surf: pygame.Surface, cx: int, cy: int, t: float):
    """Compact sidebar vendor portrait, ~60px tall. cy = vertical midpoint."""
    bob = int(math.sin(t * 1.4) * 1.5)

    # Coat
    pygame.draw.polygon(surf, (11, 9, 15), [
        (cx - 15, cy + 36 + bob), (cx + 15, cy + 36 + bob),
        (cx + 11, cy + 9  + bob), (cx - 11, cy + 9  + bob),
    ])
    # Shoulders
    pygame.draw.polygon(surf, (15, 12, 20), [
        (cx - 24, cy + 16 + bob), (cx + 24, cy + 16 + bob),
        (cx + 17, cy + 8  + bob), (cx - 17, cy + 8  + bob),
    ])
    pygame.draw.polygon(surf, (65, 55, 80), [
        (cx - 24, cy + 16 + bob), (cx + 24, cy + 16 + bob),
        (cx + 17, cy + 8  + bob), (cx - 17, cy + 8  + bob),
    ], 1)
    # Hood
    pygame.draw.polygon(surf, (13, 11, 17), [
        (cx - 15, cy - 27 + bob), (cx + 15, cy - 27 + bob),
        (cx + 19, cy + 7  + bob), (cx + 9,  cy + 9  + bob),
        (cx - 9,  cy + 9  + bob), (cx - 19, cy + 7  + bob),
    ])
    pygame.draw.polygon(surf, (58, 48, 73), [
        (cx - 15, cy - 27 + bob), (cx + 15, cy - 27 + bob),
        (cx + 19, cy + 7  + bob), (cx + 9,  cy + 9  + bob),
        (cx - 9,  cy + 9  + bob), (cx - 19, cy + 7  + bob),
    ], 1)
    # Face + visor
    pygame.draw.ellipse(surf, (5, 4, 7), (cx - 9, cy - 22 + bob, 18, 16))
    vp = 0.5 + 0.5 * abs(math.sin(t * 2.2))
    vc = (0, int(155 * vp), int(215 * vp))
    pygame.draw.rect(surf, vc, (cx - 7, cy - 15 + bob, 14, 3))
    # Eyes
    ep = 0.4 + 0.3 * abs(math.sin(t * 1.2))
    ec = (int(195 * ep), int(125 * ep), 0)
    pygame.draw.circle(surf, ec, (cx - 4, cy - 18 + bob), 1)
    pygame.draw.circle(surf, ec, (cx + 4, cy - 18 + bob), 1)


# ---------------------------------------------------------------------------
# Shared helpers

def _scanlines(surf: pygame.Surface):
    w, h = surf.get_size()
    sl = pygame.Surface((w, h), pygame.SRCALPHA)
    for y in range(0, h, 4):
        pygame.draw.line(sl, (0, 0, 0, 26), (0, y), (w, y))
    surf.blit(sl, (0, 0))


def _corner_caps(surf: pygame.Surface, rect: pygame.Rect,
                 col: tuple, L: int = 16):
    for bx, by, sx, sy in (
        (rect.left,  rect.top,     1,  1),
        (rect.right, rect.top,    -1,  1),
        (rect.left,  rect.bottom,  1, -1),
        (rect.right, rect.bottom, -1, -1),
    ):
        pygame.draw.line(surf, col, (bx, by), (bx + sx * L, by), 2)
        pygame.draw.line(surf, col, (bx, by), (bx, by + sy * L), 2)


def _wrap(text: str, font: pygame.font.Font, max_w: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    cur   = ""
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
    return lines or [""]
