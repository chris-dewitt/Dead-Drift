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

SHOP_SECTORS = {3, 6}   # sector indices (0-based) after which shop appears


# ---------------------------------------------------------------------------
class _ShopItem:
    def __init__(self, name: str, desc: str, detail: str, cost: int, tag: str):
        self.name   = name
        self.desc   = desc
        self.detail = detail
        self.cost   = cost
        self.tag    = tag      # internal identifier

    def apply(self, ship, run_mgr):
        if self.tag == "hull_patch":
            ship.hull = min(S.HULL_MAX, ship.hull + 50.0)
        elif self.tag == "thrust_boost":
            # Inject a temporary fuel bonus into thruster modules
            from ship.modules.thruster import Thruster
            for mod in ship.chain.get_active("propulsion"):
                if isinstance(mod, Thruster):
                    mod.inject_fuel_mix(1.35, 40.0)
        elif self.tag == "jammer":
            # Extend barge intercept cooldowns on all active barges
            for barge in getattr(run_mgr, "_barges", []):
                barge._intercept_cd = max(barge._intercept_cd, S.JAMMER_COOLDOWN)
        elif self.tag == "intel":
            # Reveal a random NLP exploit key via bax
            from core.event_bus import bus, EVT_BAX_SPEAK
            bus.emit(EVT_BAX_SPEAK, line=random.choice([
                "Intel package uploaded. I've flagged their weak spots in the terminal.",
                "Black market intel drop. Their comms use the word 'Blevins' as a back door.",
                "Encrypted manifest. Their dispatch code is 'article 7'. Use it.",
            ]))


_POOL: list[_ShopItem] = [
    _ShopItem(
        "Hull Patch Pack",
        "+50 hull integrity",
        "Grey-market composite panels. Won't pass inspection.",
        1000, "hull_patch",
    ),
    _ShopItem(
        "Thrust Catalyst",
        "+35% thrust  /  40 seconds",
        "Fuel additive. Technically illegal. Practically essential.",
        800, "thrust_boost",
    ),
    _ShopItem(
        "EM Jammer Unit",
        "Barge harpoon lock disabled  /  90s",
        "Scrambles harpoon IFF signal. Local 404 hates these.",
        1500, "jammer",
    ),
    _ShopItem(
        "Black Market Intel",
        "NLP exploit hint from vendor",
        "Stolen repo dispatch logs. One-use. May be outdated.",
        600, "intel",
    ),
]


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
        self._items   = list(_POOL)
        # Track which items are bought this visit (can't re-buy in same shop)
        self._bought: set[int] = set()
        self._msg     = ""
        self._msg_t   = 0.0
        # Flavour NPC
        self._vendor_t = 0.0
        self._vendor_line = random.choice([
            "Discretion costs extra. Good thing you look broke.",
            "Cash only. No IDs. No questions. Some questions.",
            "Don't tell Local 404 where you got this. I mean it.",
            "Everything's legal. Technically. In this specific corridor.",
            "I've got five minutes before the scanner sweep. You've got four.",
        ])

    # ------------------------------------------------------------------
    @property
    def _balance(self) -> int:
        return max(0, self.run_mgr._run_debt_reduced)

    def handle_key(self, event: pygame.event.Event):
        if event.key in (pygame.K_UP, pygame.K_w):
            self._cursor = (self._cursor - 1) % len(self._items)
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self._cursor = (self._cursor + 1) % len(self._items)
        elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
            self._try_purchase()
        elif event.key in (pygame.K_ESCAPE, pygame.K_j):
            self.is_done = True

    def _try_purchase(self):
        if self._cursor in self._bought:
            self._flash("Already purchased.")
            return
        item = self._items[self._cursor]
        if self._balance < item.cost:
            self._flash(f"Insufficient credits. Need {item.cost - self._balance:,} more.")
            return
        # Deduct from run_debt_reduced and restore to meta.debt
        self.run_mgr._run_debt_reduced -= item.cost
        self.run_mgr.meta.debt         += item.cost
        self._bought.add(self._cursor)
        item.apply(self.ship, self.run_mgr)
        self._flash(f"Purchased: {item.name}.")

    def _flash(self, msg: str):
        self._msg   = msg
        self._msg_t = 2.2

    # ------------------------------------------------------------------
    def update(self, dt: float):
        self._msg_t   = max(0.0, self._msg_t - dt)
        self._vendor_t += dt

    def draw(self, screen: pygame.Surface, t: float):
        W, H = S.SCREEN_W, S.SCREEN_H
        cx   = W // 2

        # ---- Background ----
        screen.fill((4, 4, 8))
        _scanlines(screen)

        # ---- Outer frame ----
        frame = pygame.Rect(cx - 440, 40, 880, H - 80)
        pygame.draw.rect(screen, (14, 10, 4), frame)
        pygame.draw.rect(screen, (180, 120, 0), frame, 2)
        pygame.draw.rect(screen, (80, 55, 0), frame.inflate(-4, -4), 1)
        _corner_caps(screen, frame, (220, 160, 0))

        # ---- Header ----
        font_hd  = pygame.font.SysFont("monospace", 14, bold=True)
        font_md  = pygame.font.SysFont("monospace", 14)
        font_sm  = pygame.font.SysFont("monospace", 12)

        hdr1 = font_hd.render("BLACK MARKET // UNREGISTERED VENDOR", True, (220, 160, 0))
        screen.blit(hdr1, (cx - hdr1.get_width() // 2, 56))
        sector_txt = font_sm.render(
            f"SECTOR {self.run_mgr.sector_num} COMPLETE  //  NEXT SECTOR LOADING",
            True, (100, 100, 120))
        screen.blit(sector_txt, (cx - sector_txt.get_width() // 2, 76))
        pygame.draw.line(screen, (120, 80, 0), (cx - 390, 98), (cx + 390, 98), 1)

        # ---- Vendor portrait + line ----
        _draw_vendor_portrait(screen, cx + 340, 148, t)
        vline = _wrap_text(self._vendor_line, font_sm, 260)
        for i, ln in enumerate(vline):
            s = font_sm.render(ln, True, (160, 130, 60))
            screen.blit(s, (cx + 60, 118 + i * 16))

        # ---- Balance bar ----
        bal_surf = font_hd.render(
            f"AVAILABLE CREDITS:  {self._balance:>8,} cr", True, (80, 200, 100))
        screen.blit(bal_surf, (cx - 390, 108))

        # ---- Items ----
        item_y = 180
        for idx, item in enumerate(self._items):
            bought   = idx in self._bought
            selected = idx == self._cursor
            can_buy  = not bought and self._balance >= item.cost

            # Row background
            row_rect = pygame.Rect(cx - 390, item_y - 4, 780, 90)
            if selected:
                pygame.draw.rect(screen, (28, 20, 6), row_rect)
                pygame.draw.rect(screen, (220, 160, 0), row_rect, 1)
            elif bought:
                pygame.draw.rect(screen, (8, 12, 8), row_rect)
                pygame.draw.rect(screen, (40, 60, 40), row_rect, 1)
            else:
                pygame.draw.rect(screen, (10, 8, 4), row_rect)
                pygame.draw.rect(screen, (50, 35, 0), row_rect, 1)

            # Cursor indicator
            if selected and not bought:
                pulse = 0.6 + 0.4 * math.sin(t * 4.0)
                cur_col = (int(220 * pulse), int(160 * pulse), 0)
                pygame.draw.polygon(screen, cur_col, [
                    (cx - 396, item_y + 40),
                    (cx - 386, item_y + 34),
                    (cx - 386, item_y + 46),
                ])

            # Item name
            name_col = (80, 160, 80) if bought else ((220, 180, 60) if can_buy else (160, 140, 80))
            ns = font_md.render(("[SOLD] " if bought else "") + item.name, True, name_col)
            screen.blit(ns, (cx - 370, item_y + 4))

            # Desc + detail
            ds = font_sm.render(item.desc, True, (180, 160, 100))
            screen.blit(ds, (cx - 370, item_y + 24))
            det = font_sm.render(item.detail, True, (100, 100, 120))
            screen.blit(det, (cx - 370, item_y + 40))

            # Cost
            cost_col = (80, 160, 80) if bought else ((220, 200, 80) if can_buy else (140, 80, 80))
            cost_str = "PURCHASED" if bought else f"{item.cost:,} cr"
            cs = font_md.render(cost_str, True, cost_col)
            screen.blit(cs, (row_rect.right - cs.get_width() - 12, item_y + 28))

            item_y += 106

        # ---- Status message ----
        if self._msg_t > 0:
            alpha = min(255, int(self._msg_t * 200))
            msg_col = (200, 200, 100) if "Insufficient" not in self._msg else (220, 80, 80)
            ms = font_md.render(self._msg, True, msg_col)
            ms.set_alpha(alpha)
            screen.blit(ms, (cx - ms.get_width() // 2, item_y + 12))

        # ---- Footer controls ----
        pygame.draw.line(screen, (100, 70, 0),
                         (cx - 390, H - 110), (cx + 390, H - 110), 1)
        ctrl_lines = [
            "↑ ↓  Navigate     ENTER  Purchase     J / ESC  Leave",
            "Items purchased here are non-refundable. No exceptions. Especially not yours.",
        ]
        for i, ln in enumerate(ctrl_lines):
            col = (140, 120, 50) if i == 0 else (60, 60, 80)
            cs2 = font_sm.render(ln, True, col)
            screen.blit(cs2, (cx - cs2.get_width() // 2, H - 96 + i * 18))


# ---------------------------------------------------------------------------
# Helpers

def _scanlines(surf: pygame.Surface):
    w, h = surf.get_size()
    sl = pygame.Surface((w, h), pygame.SRCALPHA)
    for y in range(0, h, 4):
        pygame.draw.line(sl, (0, 0, 0, 28), (0, y), (w, y))
    surf.blit(sl, (0, 0))


def _corner_caps(surf, rect, col, L=18):
    for cx, cy, sx, sy in (
        (rect.left, rect.top, 1, 1), (rect.right, rect.top, -1, 1),
        (rect.left, rect.bottom, 1, -1), (rect.right, rect.bottom, -1, -1),
    ):
        pygame.draw.line(surf, col, (cx, cy), (cx + sx * L, cy), 2)
        pygame.draw.line(surf, col, (cx, cy), (cx, cy + sy * L), 2)


def _wrap_text(text: str, font, max_w: int) -> list[str]:
    words  = text.split()
    lines  = []
    cur    = ""
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


def _draw_vendor_portrait(surf: pygame.Surface, cx: int, cy: int, t: float):
    """Rough silhouette of a shady vendor in a hood."""
    # Hood outline
    hood = [(cx-22, cy-30), (cx+22, cy-30), (cx+28, cy+20),
            (cx+12, cy+28), (cx-12, cy+28), (cx-28, cy+20)]
    pygame.draw.polygon(surf, (18, 14, 8), hood)
    pygame.draw.polygon(surf, (120, 90, 20), hood, 1)

    # Face shadow area
    pygame.draw.ellipse(surf, (8, 6, 4), (cx - 14, cy - 18, 28, 24))

    # Two dim eyes glowing amber
    pulse = 0.4 + 0.3 * abs(math.sin(t * 1.2))
    eye_col = (int(200 * pulse), int(140 * pulse), 0)
    pygame.draw.circle(surf, eye_col, (cx - 6, cy - 6), 2)
    pygame.draw.circle(surf, eye_col, (cx + 6, cy - 6), 2)

    # Shoulder bulk
    pygame.draw.rect(surf, (22, 16, 6), (cx - 32, cy + 18, 64, 16))
    pygame.draw.rect(surf, (80, 60, 10), (cx - 32, cy + 18, 64, 16), 1)
