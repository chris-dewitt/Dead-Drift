from __future__ import annotations
import math
import random
import pygame
from ship.modules.thruster import Thruster
from cargo.acoustic_archive import AcousticArchive
from cargo.epi_shrooms import EpistemologicalShrooms
from cargo.paperwork import SentientPaperwork
from cargo.schrodinger_vip import SchrodingerVIP
from config import settings as S


# ---------------------------------------------------------------------------
# Frame pool — visual + statistical identity for each ship hull
# ---------------------------------------------------------------------------

_FRAME_POOL = [
    {
        "name": "RUSTBUCKET ALPHA",
        "hull_bonus": 0,   "mass_mod": 1.0,
        "subtitle": "standard issue courier hull",
        "tagline":  "balanced. honest. extremely on fire occasionally.",
        "bax":      "Standard scrap. She'll fly. Long as you don't ask too much.",
        "stats":    [("HULL", "+0"), ("MASS", "1.0x"), ("HANDLING", "STANDARD")],
    },
    {
        "name": "SCRAP DELTA-7",
        "hull_bonus": -15, "mass_mod": 0.8,
        "subtitle": "light frame, no warranty",
        "tagline":  "whippy. fragile. allegedly held together with hope.",
        "bax":      "Light frame. Turns sharp. Loses fights. Make it count.",
        "stats":    [("HULL", "-15"), ("MASS", "0.8x"), ("HANDLING", "TWITCHY")],
    },
    {
        "name": "REINFORCED JUNK MK2",
        "hull_bonus": 20,  "mass_mod": 1.3,
        "subtitle": "heavy plate, regrettable acceleration",
        "tagline":  "tanks the hits. tanks the corners too. tanks everything.",
        "bax":      "Built like a vault. Manoeuvres like a vault. You sure?",
        "stats":    [("HULL", "+20"), ("MASS", "1.3x"), ("HANDLING", "PONDEROUS")],
    },
]

# ---------------------------------------------------------------------------
# Module pool — propulsion variants
# ---------------------------------------------------------------------------

_MODULE_FACTORY = [
    lambda: Thruster("SALVAGE PLASMA",  tier="salvage"),
    lambda: Thruster("STANDARD BURNER", tier="standard"),
    lambda: Thruster("MILITARY TORCH",  tier="military"),
]

_MODULE_META = {
    "SALVAGE PLASMA":  {
        "subtitle": "scrap-grade plasma drive",
        "tagline":  "cheap. wheezy. occasionally produces propulsion.",
        "bax":      "Salvage burn. Fires when it feels like it. Bring a stick.",
        "stats":    [("TIER", "SALVAGE"), ("OUTPUT", "85%"), ("RELIABILITY", "LOW")],
    },
    "STANDARD BURNER": {
        "subtitle": "factory-spec ion burner",
        "tagline":  "competent. boring. won't make you cry. probably.",
        "bax":      "Standard kit. Does what it says. Refreshing, honestly.",
        "stats":    [("TIER", "STANDARD"), ("OUTPUT", "100%"), ("RELIABILITY", "OK")],
    },
    "MILITARY TORCH":  {
        "subtitle": "decommissioned Union surplus",
        "tagline":  "loud. proud. attracts auditors.",
        "bax":      "Mil-spec torch. Burns hot. Voids your warranty AND your insurance.",
        "stats":    [("TIER", "MILITARY"), ("OUTPUT", "130%"), ("RELIABILITY", "GOOD")],
    },
}

# ---------------------------------------------------------------------------
# Cargo pool — chapter-specific payloads
# ---------------------------------------------------------------------------

_CARGO_FACTORY = [
    lambda: AcousticArchive(),
    lambda: EpistemologicalShrooms(),
    lambda: SentientPaperwork(),
    lambda: SchrodingerVIP(),
]

_CARGO_META = [
    {
        "key":      "ARCHIVE",
        "name":     "ACOUSTIC ARCHIVE",
        "subtitle": "contraband uncompressed audio",
        "tagline":  "the last unlicensed music. don't lose it.",
        "bax":      "Bangers. Actual bangers. Don't let the Union nick 'em.",
        "mechanic": "Damage desaturates the HUD. Climaxes with Gary.",
        "stats":    [("RISK", "MEDIUM"), ("WEIGHT", "LIGHT"), ("BUYER", "ANON.")],
    },
    {
        "key":      "SHROOMS",
        "name":     "EPI. SHROOMS",
        "subtitle": "weaponized epistemological fungi",
        "tagline":  "they make you question whether 'left' was ever real.",
        "bax":      "I have inhaled somethin'. Up is sideways now. Lovely.",
        "mechanic": "Controls invert periodically. Inversion shortens on damage.",
        "stats":    [("RISK", "HIGH"), ("WEIGHT", "VAPOR"), ("BUYER", "PROF.")],
    },
    {
        "key":      "PAPERS",
        "name":     "SENTIENT PAPERWORK",
        "subtitle": "telepathic bureaucratic forms",
        "tagline":  "Form 7-B. By ORDER of the Union. You will sign.",
        "bax":      "It TELLS you what to sign. Mid-flight. Forever.",
        "mechanic": "Forms interrupt — sign them or thrust locks.",
        "stats":    [("RISK", "TEDIOUS"), ("WEIGHT", "HEAVY"), ("BUYER", "U-404")],
    },
    {
        "key":      "VIP",
        "name":     "SCHRÖDINGER VIP",
        "subtitle": "sealed box. alive AND dead.",
        "tagline":  "observation collapses the waveform. don't peek.",
        "bax":      "Don't open the box. I MEAN it. Actually... maybe open the box.",
        "mechanic": "Observation randomizes inventory. Climax: erase the ship.",
        "stats":    [("RISK", "UNKNOWN"), ("WEIGHT", "?"), ("BUYER", "?")],
    },
]


# ---------------------------------------------------------------------------
# Nova Soma propaganda — scrolls along the bottom of the screen
# ---------------------------------------------------------------------------

_PROPAGANDA = (
    "  >>  NOVA SOMA :: DEBT IS OPPORTUNITY  "
    "  >>  CLONE FASTER. EARN FASTER. THRIVE.  "
    "  >>  LOCAL 404 :: A PROUD PARTNER IN ENFORCEMENT  "
    "  >>  REMEMBER: YOUR BODY IS LEASED  "
    "  >>  GENUINE NOVA SOMA® PARTS IN EVERY CLONE  "
    "  >>  NEW! NEGATIVE-INTEREST DEBT CONSOLIDATION (T&Cs APPLY)  "
    "  >>  THE WIDOW'S CROSSING IS NOW THE QUARTERLY OBJECTIVES OVERLAP REGION  "
    "  >>  IF YOU CAN READ THIS YOU OWE NOVA SOMA THIRTY-TWO CREDITS  "
)


# ---------------------------------------------------------------------------
# 3D wireframe helpers — used for the rotating frame previews
# ---------------------------------------------------------------------------

def _project(x, y, z, cx, cy, scale, ry, tilt=0.42):
    rx = x * math.cos(ry) - z * math.sin(ry)
    rz = x * math.sin(ry) + z * math.cos(ry)
    fy = y * math.cos(tilt) - rz * math.sin(tilt)
    return int(cx + rx * scale), int(cy + fy * scale)


def _frame_geometry(name: str):
    """Return (verts, edges) for the wireframe ship of the given frame name."""
    if name == "RUSTBUCKET ALPHA":
        verts = [
            ( 40,  0,  0),   # 0 nose
            (-28, -22, 0),   # 1 rear-left
            (-28,  22, 0),   # 2 rear-right
            (-20,  0,  10),  # 3 dorsal fin
            (-20,  0, -10),  # 4 ventral fin
            (  5, -30, 0),   # 5 left wing
            (  5,  30, 0),   # 6 right wing
        ]
        edges = [(0,1),(0,2),(1,2),(0,5),(0,6),(1,5),(2,6),
                 (0,3),(1,3),(2,3),(0,4),(1,4),(2,4)]
    elif name == "SCRAP DELTA-7":
        verts = [
            ( 46,  0,  0),
            (-22, -14, 0),
            (-22,  14, 0),
            (-10,  0,  7),
            (-10,  0, -7),
            ( -2, -22, 0),
            ( -2,  22, 0),
        ]
        edges = [(0,1),(0,2),(1,2),(0,5),(0,6),(0,3),(0,4),(1,3),(2,3),(1,4),(2,4)]
    else:  # REINFORCED JUNK MK2
        verts = [
            ( 34,  0,  0),
            (-30, -25, 12),
            (-30,  25, 12),
            (-30, -25,-12),
            (-30,  25,-12),
            (  8, -26, 0),
            (  8,  26, 0),
            (-30,  0,  20),
        ]
        edges = [(0,1),(0,2),(0,3),(0,4),(1,2),(3,4),(1,3),(2,4),
                 (0,5),(0,6),(1,5),(3,5),(2,6),(4,6),(0,7),(1,7),(2,7)]
    return verts, edges


# ---------------------------------------------------------------------------
# LoadoutDraft
# ---------------------------------------------------------------------------

class LoadoutDraft:
    """
    Run-start draft: player picks one frame, one module, one cargo.
    Three columns; ARROWS navigate; ENTER on CARGO confirms.
    """

    COL_W      = 400
    GAP        = 20
    MARGIN     = 20
    HEADER_H   = 60
    PREVIEW_H  = 230
    BAX_H      = 88
    TICKER_H   = 32

    def __init__(self, chapter: int = 1):
        self._confirmed = False
        self._slot      = 0           # 0=frame, 1=module, 2=cargo
        ch_idx    = (chapter - 1) % len(_CARGO_FACTORY)
        others    = [i for i in range(len(_CARGO_FACTORY)) if i != ch_idx]
        cargo_idx = [ch_idx] + random.sample(others, min(2, len(others)))
        self._cargo_idx = cargo_idx   # for meta lookup
        self._choices: list = [
            random.sample(_FRAME_POOL, min(3, len(_FRAME_POOL))),
            [f() for f in _MODULE_FACTORY],
            [_CARGO_FACTORY[i]() for i in cargo_idx],
        ]
        self._selected  = [0, 0, 0]
        self._chapter   = chapter

    # ------------------------------------------------------------------
    def handle_key(self, event: pygame.event.Event):
        if event.key == pygame.K_LEFT:
            self._selected[self._slot] = max(0, self._selected[self._slot] - 1)
        elif event.key == pygame.K_RIGHT:
            self._selected[self._slot] = min(
                len(self._choices[self._slot]) - 1,
                self._selected[self._slot] + 1)
        elif event.key in (pygame.K_DOWN, pygame.K_TAB):
            self._slot = (self._slot + 1) % 3
        elif event.key == pygame.K_UP:
            self._slot = (self._slot - 1) % 3
        elif event.key == pygame.K_RETURN:
            if self._slot < 2:
                self._slot += 1
            else:
                self._confirmed = True

    def is_confirmed(self) -> bool:
        return self._confirmed

    @property
    def selected_frame(self):  return self._choices[0][self._selected[0]]
    @property
    def selected_module(self): return self._choices[1][self._selected[1]]
    @property
    def selected_cargo(self):  return self._choices[2][self._selected[2]]

    # ------------------------------------------------------------------
    # Render
    # ------------------------------------------------------------------
    def render(self, surface: pygame.Surface):
        t = pygame.time.get_ticks() / 1000.0
        surface.fill(S.VOID)
        self._draw_background_grid(surface, t)
        self._draw_header(surface, t)
        self._draw_columns(surface, t)
        self._draw_bax_panel(surface, t)
        self._draw_hint(surface, t)
        self._draw_propaganda(surface, t)
        self._draw_corner_brackets(surface, t)
        self._draw_scanlines(surface)

    # ------------------------------------------------------------------ background
    def _draw_background_grid(self, surface, t):
        """Sparse grid + drifting accent dots so the void isn't dead."""
        col = (16, 20, 26)
        spacing = 40
        for x in range(0, S.SCREEN_W, spacing):
            pygame.draw.line(surface, col, (x, self.HEADER_H), (x, S.SCREEN_H - self.TICKER_H), 1)
        for y in range(self.HEADER_H, S.SCREEN_H - self.TICKER_H, spacing):
            pygame.draw.line(surface, col, (0, y), (S.SCREEN_W, y), 1)

        # Drifting amber accent dots
        rng = random.Random(7)
        for _ in range(22):
            ox = rng.randint(0, S.SCREEN_W)
            oy = rng.randint(self.HEADER_H, S.SCREEN_H - self.TICKER_H)
            phase = rng.random() * math.tau
            bright = 0.4 + 0.3 * math.sin(t * 0.8 + phase)
            r = int(60 * bright); g = int(40 * bright)
            surface.set_at((ox, oy), (r, g, 0))

    # ------------------------------------------------------------------ header
    def _draw_header(self, surface, t):
        font_corp  = pygame.font.SysFont("monospace", 12)
        font_brand = pygame.font.SysFont("monospace", 22, bold=True)
        font_ch    = pygame.font.SysFont("monospace", 13)

        # Top bar: dark band with amber border
        pygame.draw.rect(surface, (10, 8, 4), pygame.Rect(0, 0, S.SCREEN_W, self.HEADER_H))
        pygame.draw.line(surface, (140, 90, 0), (0, self.HEADER_H), (S.SCREEN_W, self.HEADER_H), 1)

        # Left: brand
        brand = font_brand.render("NOVA SOMA :: COURIER OUTFITTING", True, S.AMBER_TERM)
        surface.blit(brand, (self.MARGIN, 12))
        sub = font_corp.render("A DIVISION OF NOVA SOMA HOLDINGS    //    LICENSED THROUGH LOCAL 404",
                               True, (110, 80, 0))
        surface.blit(sub, (self.MARGIN, 36))

        # Right: chapter title
        chapter_names = {
            1: "CH.1  THE ACOUSTIC ARCHIVE",
            2: "CH.2  THE MYCORRHIZAL PAYLOAD",
            3: "CH.3  THE PAPERWORK",
            4: "CH.4  THE SCHRÖDINGER VIP",
        }
        ch = chapter_names.get(self._chapter, f"CH.{self._chapter}")
        ch_surf = font_ch.render(ch, True, (200, 140, 0))
        surface.blit(ch_surf, (S.SCREEN_W - ch_surf.get_width() - self.MARGIN, 14))
        instr = font_corp.render("FILE COMPLETE LOADOUT BEFORE LAUNCH AUTHORIZATION",
                                 True, (110, 80, 0))
        surface.blit(instr, (S.SCREEN_W - instr.get_width() - self.MARGIN, 36))

    # ------------------------------------------------------------------ columns
    def _draw_columns(self, surface, t):
        labels = ["FRAME", "MODULE", "CARGO"]
        for i in range(3):
            col_x = self.MARGIN + i * (self.COL_W + self.GAP)
            self._draw_column(surface, i, col_x, labels[i], t)

    def _draw_column(self, surface, slot_i, x, label, t):
        active = (slot_i == self._slot)
        font_lbl   = pygame.font.SysFont("monospace", 14, bold=True)
        font_name  = pygame.font.SysFont("monospace", 22, bold=True)
        font_sub   = pygame.font.SysFont("monospace", 12)
        font_tag   = pygame.font.SysFont("monospace", 11, italic=True)
        font_stat  = pygame.font.SysFont("monospace", 12)
        font_page  = pygame.font.SysFont("monospace", 11)

        col_y_top = self.HEADER_H + 18
        preview_rect = pygame.Rect(x, col_y_top + 22, self.COL_W, self.PREVIEW_H)

        # Header label with selection chevron
        chevron = ">" if active else " "
        lbl_col = (255, 200, 60) if active else (95, 75, 30)
        lbl = font_lbl.render(f"{chevron} {label}  [ {slot_i + 1}/3 ]",
                              True, lbl_col)
        surface.blit(lbl, (x + 8, col_y_top - 2))

        # Preview panel background
        bg_col   = (10, 12, 16) if active else (6, 7, 10)
        edge_col = (180, 130, 20) if active else (40, 32, 14)
        pygame.draw.rect(surface, bg_col, preview_rect)
        pygame.draw.rect(surface, edge_col, preview_rect, 1 if not active else 2)
        # Inner brackets
        self._draw_panel_brackets(surface, preview_rect, edge_col)

        # Preview content
        choice = self._choices[slot_i][self._selected[slot_i]]
        if slot_i == 0:
            self._draw_frame_preview(surface, preview_rect, choice, t)
        elif slot_i == 1:
            self._draw_module_preview(surface, preview_rect, choice, t)
        else:
            self._draw_cargo_preview(surface, preview_rect, choice, slot_i, t)

        # Meta — name, subtitle, tagline, stats
        meta = self._lookup_meta(slot_i, choice)
        text_y = preview_rect.bottom + 10

        name_surf = font_name.render(meta["name"], True, S.AMBER_TERM if active else (130, 95, 0))
        surface.blit(name_surf, (x + 8, text_y))
        text_y += name_surf.get_height() + 2

        sub_surf = font_sub.render(meta["subtitle"], True, (160, 160, 170) if active else (75, 75, 85))
        surface.blit(sub_surf, (x + 8, text_y))
        text_y += sub_surf.get_height() + 8

        # Stats grid
        for key, val in meta["stats"]:
            kc = (140, 140, 150) if active else (60, 60, 70)
            vc = (220, 200, 90)  if active else (90, 80, 30)
            ks = font_stat.render(f"{key}:", True, kc)
            vs = font_stat.render(val, True, vc)
            surface.blit(ks, (x + 14, text_y))
            surface.blit(vs, (x + 130, text_y))
            text_y += 18

        # Tagline at bottom of column
        tag_surf = font_tag.render(meta["tagline"], True,
                                   (180, 140, 30) if active else (75, 60, 15))
        surface.blit(tag_surf, (x + 8, preview_rect.bottom + 140))

        # Page indicator < N/total > below preview right side
        cur = self._selected[slot_i] + 1
        tot = len(self._choices[slot_i])
        left  = "<" if self._selected[slot_i] > 0 else " "
        right = ">" if self._selected[slot_i] < tot - 1 else " "
        page = font_page.render(f"  {left}  {cur} / {tot}  {right}  ",
                                True, (200, 160, 60) if active else (80, 60, 20))
        surface.blit(page, (x + self.COL_W - page.get_width() - 8,
                            preview_rect.top - 18))

    # ------------------------------------------------------------------ panel brackets
    def _draw_panel_brackets(self, surface, rect, col):
        L = 12
        # Top-left
        pygame.draw.line(surface, col, rect.topleft, (rect.left + L, rect.top), 2)
        pygame.draw.line(surface, col, rect.topleft, (rect.left, rect.top + L), 2)
        # Top-right
        pygame.draw.line(surface, col, rect.topright, (rect.right - L, rect.top), 2)
        pygame.draw.line(surface, col, rect.topright, (rect.right, rect.top + L), 2)
        # Bottom-left
        pygame.draw.line(surface, col, rect.bottomleft, (rect.left + L, rect.bottom), 2)
        pygame.draw.line(surface, col, rect.bottomleft, (rect.left, rect.bottom - L), 2)
        # Bottom-right
        pygame.draw.line(surface, col, rect.bottomright, (rect.right - L, rect.bottom), 2)
        pygame.draw.line(surface, col, rect.bottomright, (rect.right, rect.bottom - L), 2)

    # ------------------------------------------------------------------ frame preview
    def _draw_frame_preview(self, surface, rect, frame, t):
        cx = rect.centerx
        cy = rect.centery - 6
        verts, edges = _frame_geometry(frame["name"])
        ry    = t * 0.45
        scale = min(rect.width / 130, rect.height / 130) * 1.5

        # Project all
        pts = [_project(x, y, z, cx, cy, scale, ry) for x, y, z in verts]

        # Stat-themed glow
        col_main  = (210, 240, 255)
        col_dim   = (60,  95, 130)
        col_glow  = (0,  140, 200)

        # Halo
        glow = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        ga = int(45 + 20 * math.sin(t * 1.3))
        pygame.draw.circle(glow, (*col_glow, ga),
                           (rect.width // 2, rect.height // 2 - 6),
                           min(rect.width, rect.height) // 3)
        surface.blit(glow, rect.topleft)

        # Edges
        for i, j in edges:
            pygame.draw.line(surface, col_dim, pts[i], pts[j], 2)
        for i, j in edges:
            pygame.draw.line(surface, col_main, pts[i], pts[j], 1)

        # Vertex dots
        for p in pts:
            pygame.draw.circle(surface, col_main, p, 2)

        # "Spec" label inside panel
        font_spec = pygame.font.SysFont("monospace", 10)
        spec = font_spec.render("HULL SCHEMATIC // ROT 0.45 rad/s", True, (60, 70, 80))
        surface.blit(spec, (rect.left + 8, rect.bottom - 18))

    # ------------------------------------------------------------------ module preview
    def _draw_module_preview(self, surface, rect, module, t):
        name = getattr(module, "name", "MODULE")
        cx = rect.centerx
        cy = rect.centery

        # Different visual per tier
        tier_colors = {
            "SALVAGE PLASMA":  ((200, 120, 40),  (90, 50, 10),  (255, 80,  30)),
            "STANDARD BURNER": ((100, 180, 255), (40, 80, 130), (60,  140, 255)),
            "MILITARY TORCH":  ((255, 255, 255), (110, 120, 140), (255, 200, 60)),
        }
        bright, dim, plume = tier_colors.get(name, ((180, 180, 200), (60, 60, 80), (255, 150, 60)))

        # Thruster nozzle body
        body_pts = [
            (cx - 40, cy - 22),
            (cx + 18, cy - 22),
            (cx + 30, cy - 8),
            (cx + 30, cy + 8),
            (cx + 18, cy + 22),
            (cx - 40, cy + 22),
        ]
        pygame.draw.polygon(surface, (12, 14, 18), body_pts)
        pygame.draw.polygon(surface, bright, body_pts, 2)

        # Internal "coil" lines
        for offset in range(-14, 15, 7):
            pygame.draw.line(surface, dim, (cx - 32, cy + offset), (cx + 18, cy + offset), 1)

        # Glowing core
        core_pulse = 0.6 + 0.4 * math.sin(t * 5.0)
        core_col = tuple(int(c * core_pulse) for c in bright)
        pygame.draw.circle(surface, core_col, (cx - 12, cy), 6)
        pygame.draw.circle(surface, bright,   (cx - 12, cy), 6, 1)

        # Exhaust plume (multi-layer)
        for i, alpha in enumerate((45, 80, 140, 220)):
            layer = pygame.Surface((140, 50), pygame.SRCALPHA)
            length = 70 + i * 12 + int(8 * math.sin(t * 6 + i))
            pts = [(0, 25 - (4 - i)*2), (-length, 0), (-length, 50), (0, 25 + (4 - i)*2)]
            pts = [(p[0] + 130, p[1]) for p in pts]
            pygame.draw.polygon(layer, (*plume, alpha), pts)
            surface.blit(layer, (cx + 30 - 130, cy - 25))

        # Mounting bolts
        for by in (cy - 22, cy + 22):
            for bx in (cx - 36, cx - 18, cx):
                pygame.draw.circle(surface, dim, (bx, by), 2)

        font_spec = pygame.font.SysFont("monospace", 10)
        spec = font_spec.render("THRUSTER // PLASMA EXHAUST PROFILE", True, (60, 70, 80))
        surface.blit(spec, (rect.left + 8, rect.bottom - 18))

    # ------------------------------------------------------------------ cargo preview
    def _draw_cargo_preview(self, surface, rect, cargo, slot_i, t):
        # Identify which cargo this is via the cargo_idx list
        idx_in_pool = self._cargo_idx[self._selected[slot_i]]
        key = ["ARCHIVE", "SHROOMS", "PAPERS", "VIP"][idx_in_pool]

        cx, cy = rect.centerx, rect.centery - 4

        if key == "ARCHIVE":
            self._draw_cargo_archive(surface, cx, cy, t)
        elif key == "SHROOMS":
            self._draw_cargo_shrooms(surface, cx, cy, t)
        elif key == "PAPERS":
            self._draw_cargo_papers(surface, cx, cy, t)
        else:
            self._draw_cargo_vip(surface, cx, cy, t)

        font_spec = pygame.font.SysFont("monospace", 10)
        label = f"PAYLOAD // {key}"
        spec = font_spec.render(label, True, (60, 70, 80))
        surface.blit(spec, (rect.left + 8, rect.bottom - 18))

    # ----- cargo: acoustic archive (vinyl record) -----
    def _draw_cargo_archive(self, surface, cx, cy, t):
        rot = t * 1.6
        # Vinyl disc
        pygame.draw.circle(surface, (12, 12, 14), (cx, cy), 78)
        pygame.draw.circle(surface, (25, 25, 30), (cx, cy), 78, 2)
        # Grooves
        for r in (70, 62, 54, 46, 38, 30):
            pygame.draw.circle(surface, (18, 18, 22), (cx, cy), r, 1)
        # Centre label (amber, like a Nova Soma promo)
        pygame.draw.circle(surface, (180, 80, 20), (cx, cy), 24)
        pygame.draw.circle(surface, (255, 130, 30), (cx, cy), 24, 1)
        # Centre hole
        pygame.draw.circle(surface, S.VOID, (cx, cy), 3)
        # Reflection highlight rotating
        hx = cx + int(math.cos(rot) * 40)
        hy = cy + int(math.sin(rot) * 40)
        pygame.draw.circle(surface, (80, 80, 90), (hx, hy), 5)
        # Tiny "side A" text
        font = pygame.font.SysFont("monospace", 8, bold=True)
        sa = font.render("SIDE A", True, (255, 220, 150))
        surface.blit(sa, (cx - sa.get_width() // 2, cy + 10))

    # ----- cargo: shrooms (pulsing fungus) -----
    def _draw_cargo_shrooms(self, surface, cx, cy, t):
        pulse = 0.5 + 0.5 * math.sin(t * 2.0)
        # Stem
        pygame.draw.rect(surface, (60, 50, 40),
                         pygame.Rect(cx - 10, cy + 8, 20, 50))
        pygame.draw.rect(surface, (100, 85, 65),
                         pygame.Rect(cx - 10, cy + 8, 20, 50), 1)
        # Cap (psychedelic gradient layers)
        for i, r in enumerate((58, 48, 38, 28, 18)):
            hue = (0.78 + 0.06 * math.sin(t * 1.2 + i)) % 1.0
            c   = _hsv(hue, 0.78, 0.45 + 0.30 * pulse * (i + 1) / 5)
            pygame.draw.circle(surface, c, (cx, cy + 10), r)
        # Spots
        for dx, dy in ((-32, -8), (24, -4), (-12, -22), (18, -18), (-2, -28)):
            spot_c = _hsv((t * 0.3 + dx * 0.01) % 1.0, 0.5, 0.9)
            pygame.draw.circle(surface, (255, 240, 220), (cx + dx, cy + 10 + dy), 4)
            pygame.draw.circle(surface, spot_c, (cx + dx, cy + 10 + dy), 4, 1)
        # Spore drift
        for i in range(8):
            sy = cy + 8 + ((int(t * 30 + i * 20)) % 80)
            sx = cx + int(math.sin(t * 1.5 + i * 0.7) * 28)
            alpha_col = _hsv((i * 0.1 + t * 0.2) % 1.0, 0.6, 0.6)
            surface.set_at((sx, sy), alpha_col)

    # ----- cargo: paperwork (stack of forms) -----
    def _draw_cargo_papers(self, surface, cx, cy, t):
        amber = S.AMBER_TERM
        # Stack of forms — perspective tilt
        for i in range(6):
            offset = i * 3
            rect = pygame.Rect(cx - 60 + offset, cy + 30 - offset, 120, 8)
            pygame.draw.rect(surface, (35, 28, 14), rect)
            pygame.draw.rect(surface, (90, 70, 20), rect, 1)
        # Top form (the active one, larger)
        top_rect = pygame.Rect(cx - 70, cy - 50, 140, 90)
        pygame.draw.rect(surface, (240, 220, 170), top_rect)
        pygame.draw.rect(surface, amber, top_rect, 2)
        # Form header
        font_h = pygame.font.SysFont("monospace", 10, bold=True)
        font_b = pygame.font.SysFont("monospace", 8)
        hdr = font_h.render("FORM 27-B", True, (90, 60, 0))
        surface.blit(hdr, (cx - 30, cy - 45))
        # Lines simulating fields
        for i in range(5):
            ly = cy - 30 + i * 12
            pygame.draw.line(surface, (170, 140, 80), (cx - 60, ly), (cx + 60, ly), 1)
        # Stamp (rotating slightly)
        wobble = 4 * math.sin(t * 0.8)
        stamp_pts = [
            (cx + 38 + wobble, cy + 22),
            (cx + 58 + wobble, cy + 18),
            (cx + 58 + wobble, cy + 38),
            (cx + 38 + wobble, cy + 42),
        ]
        pygame.draw.polygon(surface, (180, 40, 40), stamp_pts, 2)
        sf = font_b.render("VOID", True, (180, 40, 40))
        surface.blit(sf, (cx + 40 + wobble, cy + 24))
        # Cursor blink demanding signature
        if int(t * 2) % 2 == 0:
            pygame.draw.line(surface, (50, 20, 0),
                             (cx - 50, cy + 32), (cx + 0, cy + 32), 1)

    # ----- cargo: schrödinger vip (box with question marks) -----
    def _draw_cargo_vip(self, surface, cx, cy, t):
        # The box itself — lead grey, slightly tilted
        box_w, box_h = 130, 100
        box = pygame.Rect(cx - box_w // 2, cy - box_h // 2, box_w, box_h)
        pygame.draw.rect(surface, (40, 40, 48), box)
        pygame.draw.rect(surface, (110, 110, 130), box, 2)
        # Hazard stripes
        for sx in range(box.left, box.right, 12):
            pygame.draw.line(surface, (80, 60, 0),
                             (sx, box.top - 4), (sx + 8, box.top - 4), 2)
        # Top lid line
        pygame.draw.line(surface, (160, 160, 180),
                         (box.left + 6, box.top + 16),
                         (box.right - 6, box.top + 16), 1)
        # Big quantum question mark — flickering between ? and !
        font_q = pygame.font.SysFont("monospace", 64, bold=True)
        glyph = "?" if int(t * 3.5) % 4 != 0 else "!"
        col   = (210, 100, 240) if glyph == "?" else (255, 220, 50)
        qs = font_q.render(glyph, True, col)
        surface.blit(qs, (cx - qs.get_width() // 2, cy - qs.get_height() // 2 + 2))
        # Quantum particles drifting
        for i in range(10):
            phase = i * 0.62 + t * 0.9
            r = 40 + 20 * math.sin(t * 1.4 + i)
            px = int(cx + math.cos(phase) * r)
            py = int(cy + math.sin(phase) * r)
            c  = _hsv((i * 0.1 + t * 0.15) % 1.0, 0.7, 0.85)
            pygame.draw.circle(surface, c, (px, py), 2)

    # ------------------------------------------------------------------ bax commentary
    def _draw_bax_panel(self, surface, t):
        panel_y = self.HEADER_H + 18 + 22 + self.PREVIEW_H + 160 + 14
        panel   = pygame.Rect(self.MARGIN, panel_y,
                              S.SCREEN_W - 2 * self.MARGIN, self.BAX_H)
        pygame.draw.rect(surface, (8, 6, 0), panel)
        pygame.draw.rect(surface, (150, 100, 0), panel, 1)
        self._draw_panel_brackets(surface, panel, (200, 140, 30))

        # Bax mini portrait
        px = panel.left + 32
        py = panel.centery
        head = [(px - 16, py - 22), (px + 16, py - 22),
                (px + 20, py - 4),  (px - 20, py - 4)]
        pygame.draw.polygon(surface, (20, 20, 30), head)
        pygame.draw.polygon(surface, (110, 80, 0), head, 1)
        glow = 0.4 + 0.3 * abs(math.sin(t * 1.2))
        ec   = (int(220 * glow), int(140 * glow), 0)
        pygame.draw.circle(surface, ec, (px - 6, py - 14), 3)
        pygame.draw.circle(surface, ec, (px + 6, py - 14), 3)
        # Antenna
        pygame.draw.line(surface, (110, 80, 0), (px + 14, py - 22), (px + 18, py - 32), 1)
        pygame.draw.circle(surface, (200, 140, 0), (px + 18, py - 33), 2)
        # Body
        body = [(px - 18, py - 4), (px + 18, py - 4),
                (px + 16, py + 22), (px - 16, py + 22)]
        pygame.draw.polygon(surface, (28, 22, 8), body)
        pygame.draw.polygon(surface, (110, 80, 0), body, 1)

        # Caption + line
        font_cap  = pygame.font.SysFont("monospace", 11, bold=True)
        font_line = pygame.font.SysFont("monospace", 15)
        cap = font_cap.render("BAX, NAV-MORALE //  on your current selection:",
                              True, (180, 130, 30))
        surface.blit(cap, (panel.left + 70, panel.top + 12))

        choice = self._choices[self._slot][self._selected[self._slot]]
        meta = self._lookup_meta(self._slot, choice)
        bax_line = f'"{meta["bax"]}"'
        # Wrap if necessary (rough single-line is fine at this width)
        line_surf = font_line.render(bax_line, True, (245, 220, 130))
        surface.blit(line_surf, (panel.left + 70, panel.top + 36))

    # ------------------------------------------------------------------ hint
    def _draw_hint(self, surface, t):
        font = pygame.font.SysFont("monospace", 13)
        y = S.SCREEN_H - self.TICKER_H - 30

        if self._slot < 2:
            text = "[ ◄ ► ]  select option     [ ▼ TAB ]  next slot     [ ENTER ]  next slot"
            col  = (140, 140, 160)
        else:
            pulse = 0.5 + 0.5 * math.sin(t * 4.0)
            text = ">>>>  [ ENTER ]  LAUNCH RUN  <<<<"
            col  = (int(100 + 155 * pulse), int(255 * pulse), int(60 + 80 * pulse))

        surf = font.render(text, True, col)
        surface.blit(surf, (S.SCREEN_W // 2 - surf.get_width() // 2, y))

    # ------------------------------------------------------------------ propaganda ticker
    def _draw_propaganda(self, surface, t):
        h = self.TICKER_H
        bar_y = S.SCREEN_H - h
        pygame.draw.rect(surface, (10, 8, 4), pygame.Rect(0, bar_y, S.SCREEN_W, h))
        pygame.draw.line(surface, (140, 90, 0), (0, bar_y), (S.SCREEN_W, bar_y), 1)

        font = pygame.font.SysFont("monospace", 13, bold=True)
        full = _PROPAGANDA + _PROPAGANDA
        text_surf = font.render(full, True, (210, 150, 30))

        # Scroll offset
        speed = 70  # px/s
        offset = int((t * speed) % text_surf.get_width() // 2 * 2)
        x = -offset
        surface.blit(text_surf, (x, bar_y + 8))
        # Wrap-around second copy
        surface.blit(text_surf, (x + text_surf.get_width() // 2, bar_y + 8))

    # ------------------------------------------------------------------ corner brackets
    def _draw_corner_brackets(self, surface, t):
        col = (90, 90, 110)
        L = 22
        margins = ((6, 6), (S.SCREEN_W - 7, 6),
                   (6, S.SCREEN_H - 7), (S.SCREEN_W - 7, S.SCREEN_H - 7))
        for cx, cy in margins:
            sx = -1 if cx > S.SCREEN_W // 2 else 1
            sy = -1 if cy > S.SCREEN_H // 2 else 1
            pygame.draw.line(surface, col, (cx, cy), (cx + sx * L, cy), 2)
            pygame.draw.line(surface, col, (cx, cy), (cx, cy + sy * L), 2)

    # ------------------------------------------------------------------ scanlines
    def _draw_scanlines(self, surface):
        # Subtle every-4th-row darken
        sl = pygame.Surface((S.SCREEN_W, S.SCREEN_H), pygame.SRCALPHA)
        for y in range(0, S.SCREEN_H, 4):
            pygame.draw.line(sl, (0, 0, 0, 36), (0, y), (S.SCREEN_W, y), 1)
        surface.blit(sl, (0, 0))

    # ------------------------------------------------------------------ helpers
    def _lookup_meta(self, slot_i: int, choice) -> dict:
        if slot_i == 0:
            return choice   # frame dicts already have meta
        if slot_i == 1:
            name = getattr(choice, "name", "STANDARD BURNER")
            meta = _MODULE_META.get(name, _MODULE_META["STANDARD BURNER"]).copy()
            meta["name"] = name
            return meta
        # cargo
        idx = self._cargo_idx[self._selected[2]]
        return _CARGO_META[idx]


# ---------------------------------------------------------------------------
def _hsv(h, s, v):
    h = h % 1.0
    if s == 0:
        c = int(v * 255); return (c, c, c)
    i = int(h * 6); f = h * 6 - i
    p, q, tt = v * (1 - s), v * (1 - s * f), v * (1 - s * (1 - f))
    r, g, b = [(v,tt,p),(q,v,p),(p,v,tt),(p,q,v),(tt,p,v),(v,p,q)][i % 6]
    return (int(r * 255), int(g * 255), int(b * 255))
