"""Regression coverage for loadout draft rendering."""
from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from config import settings as S


def test_chapter_five_and_six_loadout_render_without_crashing():
    pygame.init()
    pygame.font.init()

    from roguelite.loadout_draft import LoadoutDraft

    surface = pygame.Surface((S.SCREEN_W, S.SCREEN_H))
    for chapter in (5, 6):
        draft = LoadoutDraft(chapter=chapter)
        draft.render(surface)
