"""Regression coverage for loadout draft rendering."""
from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame


def test_chapter_five_and_six_loadout_cargo_previews_render():
    """New drive cargos must render without indexing the old four-cargo key list."""
    from config import settings as S
    from roguelite.loadout_draft import LoadoutDraft

    pygame.init()
    pygame.font.init()
    surface = pygame.Surface((S.SCREEN_W, S.SCREEN_H))
    for chapter in (5, 6):
        draft = LoadoutDraft(chapter=chapter)
        surface.fill((0, 0, 0))
        draft.render(surface)
        assert surface.get_at((S.SCREEN_W // 2, S.SCREEN_H // 2))[:3] != (0, 0, 0)
