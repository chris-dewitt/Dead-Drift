"""Regression tests for Chapter 5/6 loadout drafting."""
from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest


@pytest.mark.parametrize("chapter", [5, 6])
def test_chapter_5_and_6_loadout_render_without_cargo_index_crash(chapter):
    pygame.init()
    pygame.font.init()

    from config import settings as S
    from roguelite.loadout_draft import LoadoutDraft

    draft = LoadoutDraft(chapter=chapter)
    surface = pygame.Surface((S.SCREEN_W, S.SCREEN_H))

    draft.render(surface)

    assert surface.get_at((S.SCREEN_W // 2, S.SCREEN_H // 2))[:3] != (0, 0, 0)
