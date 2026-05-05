from __future__ import annotations
import random
import pygame
from ship.modules.thruster import Thruster
from ship.modules.life_support import LifeSupport
from cargo.acoustic_archive import AcousticArchive
from cargo.epi_shrooms import EpistemologicalShrooms
from cargo.paperwork import SentientPaperwork
from cargo.schrodinger_vip import SchrodingerVIP
from config import settings as S


_FRAME_POOL = [
    {"name": "RUSTBUCKET ALPHA",   "hull_bonus": 0,   "mass_mod": 1.0},
    {"name": "SCRAP DELTA-7",      "hull_bonus": -15, "mass_mod": 0.8},
    {"name": "REINFORCED JUNK MK2","hull_bonus": 20,  "mass_mod": 1.3},
]

_MODULE_POOL = [
    lambda: Thruster("SALVAGE PLASMA",  tier="salvage"),
    lambda: Thruster("STANDARD BURNER", tier="standard"),
    lambda: Thruster("MILITARY TORCH",  tier="military"),
    lambda: LifeSupport(),
]

_CARGO_POOL = [
    lambda: AcousticArchive(),
    lambda: EpistemologicalShrooms(),
    lambda: SentientPaperwork(),
    lambda: SchrodingerVIP(),
]


class LoadoutDraft:
    """
    Run-start draft: player picks one frame, one module, one cargo.
    Presents three options per slot; player navigates with arrow keys.
    """

    def __init__(self, chapter: int = 1):
        self._confirmed = False
        self._slot      = 0           # 0=frame, 1=module, 2=cargo
        self._choices   = [
            random.sample(_FRAME_POOL, min(3, len(_FRAME_POOL))),
            [f() for f in random.sample(_MODULE_POOL, 3)],
            [_CARGO_POOL[(chapter - 1) % len(_CARGO_POOL)]()],  # chapter-locked cargo
        ]
        self._selected  = [0, 0, 0]

    # ------------------------------------------------------------------
    def handle_key(self, event: pygame.event.Event):
        if event.key == pygame.K_LEFT:
            self._selected[self._slot] = max(0, self._selected[self._slot] - 1)
        elif event.key == pygame.K_RIGHT:
            pool_len = len(self._choices[self._slot])
            self._selected[self._slot] = min(pool_len - 1, self._selected[self._slot] + 1)
        elif event.key == pygame.K_DOWN:
            self._slot = min(2, self._slot + 1)
        elif event.key == pygame.K_UP:
            self._slot = max(0, self._slot - 1)
        elif event.key == pygame.K_RETURN and self._slot == 2:
            self._confirmed = True

    def is_confirmed(self) -> bool:
        return self._confirmed

    @property
    def selected_frame(self) -> dict:
        return self._choices[0][self._selected[0]]

    @property
    def selected_module(self):
        return self._choices[1][self._selected[1]]

    @property
    def selected_cargo(self):
        return self._choices[2][self._selected[2]]

    # ------------------------------------------------------------------
    def render(self, surface: pygame.Surface):
        surface.fill(S.BLACK)
        font   = pygame.font.SysFont("monospace", 16)
        line_h = font.get_linesize()
        labels = ["FRAME", "MODULE", "CARGO"]
        y      = 60

        title = font.render("-- LOADOUT DRAFT --", True, S.AMBER_TERM)
        surface.blit(title, (S.SCREEN_W // 2 - title.get_width() // 2, 20))

        for slot_i, (label, choices) in enumerate(zip(labels, self._choices)):
            color = S.GREEN_TERM if slot_i == self._slot else S.GREY_DEAD
            hdr   = font.render(f"[ {label} ]", True, color)
            surface.blit(hdr, (60, y))
            y += line_h

            for ci, choice in enumerate(choices):
                active = (ci == self._selected[slot_i])
                name   = choice["name"] if isinstance(choice, dict) else str(choice)
                prefix = "-> " if active else "   "
                clr    = S.WHITE_VEC if active else S.GREY_DEAD
                txt    = font.render(f"{prefix}{name}", True, clr)
                surface.blit(txt, (80, y))
                y += line_h

            y += 10

        hint = font.render("ARROWS to navigate | ENTER on CARGO to confirm", True, S.AMBER_TERM)
        surface.blit(hint, (S.SCREEN_W // 2 - hint.get_width() // 2, S.SCREEN_H - 50))
