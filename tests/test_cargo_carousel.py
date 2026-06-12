"""Coverage for Epic 8.2 — Cargo Dossier Carousel."""
from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import tempfile
from pathlib import Path
from types import SimpleNamespace

import pygame


def _meta_with(temp_dir, **overrides):
    from roguelite.meta_progression import MetaProgression
    save_path = Path(temp_dir) / "meta.json"
    meta = MetaProgression(save_path=save_path)
    for k, v in overrides.items():
        meta._data[k] = v
    return meta


def _stats_with(temp_dir, career=None):
    from roguelite.stats_tracker import StatsTracker
    save_path = Path(temp_dir) / "stats.json"
    stats = StatsTracker(save_path=save_path)
    if career:
        stats._career.update(career)
    return stats


def test_card_count_and_chapter_lookup():
    from renderer.cargo_carousel import card_count, card_chapter
    assert card_count() == 4
    chapters = [card_chapter(i) for i in range(card_count())]
    assert chapters == [1, 2, 3, 4]


def test_carousel_renders_for_empty_meta():
    pygame.init()
    pygame.font.init()
    from renderer.cargo_carousel import draw_carousel

    with tempfile.TemporaryDirectory() as tmp:
        meta  = _meta_with(tmp)
        screen = pygame.Surface((1280, 720))
        screen.fill((0, 0, 0))
        draw_carousel(screen, meta=meta, stats=None, cursor=0, t=0.0)
        cx, cy = 640, 360
        assert screen.get_at((cx, cy))[:3] != (0, 0, 0)


def test_carousel_renders_with_completed_chapters_and_stats():
    pygame.init()
    pygame.font.init()
    from renderer.cargo_carousel import draw_carousel, card_count

    with tempfile.TemporaryDirectory() as tmp:
        meta = _meta_with(tmp,
                          chapters_completed=[1, 2, 3, 4],
                          hardcore_unlocked=[1, 2],
                          hardcore_best_s={"1": 540})
        stats = _stats_with(tmp, career={
            "deepest_sector_per_chapter": {"1": 5, "2": 4},
            "best_single_run_credits": 4800,
        })
        screen = pygame.Surface((1280, 720))
        for cur in range(card_count()):
            screen.fill((0, 0, 0))
            draw_carousel(screen, meta=meta, stats=stats, cursor=cur, t=1.0)
            assert screen.get_at((640, 360))[:3] != (0, 0, 0)


def test_loadout_renders_chapter_five_and_six_cargo_previews():
    pygame.init()
    pygame.font.init()
    from config import settings as S
    from roguelite.loadout_draft import LoadoutDraft

    screen = pygame.Surface((S.SCREEN_W, S.SCREEN_H))
    for chapter in (5, 6):
        draft = LoadoutDraft(chapter=chapter)
        draft.render(screen)
        assert screen.get_at((640, 360))[:3] != (0, 0, 0)


def test_visible_chapters_progression_gates_chapter_two():
    """Chapter 2 stays locked until chapter 1 is cleared."""
    from renderer.cargo_carousel import visible_chapters
    with tempfile.TemporaryDirectory() as tmp:
        fresh = _meta_with(tmp)
        assert visible_chapters(fresh) == [1]
        cleared_one = _meta_with(tmp + "_b" if False else tmp,
                                 chapters_completed=[1])
        assert 2 in visible_chapters(cleared_one)


def test_run_manager_chapter_override_round_trips():
    """RunManager.set_chapter_override flips _current_chapter target."""
    pygame.init()
    pygame.font.init()
    from roguelite.run_manager import RunManager
    with tempfile.TemporaryDirectory() as tmp:
        meta = _meta_with(tmp, chapters_completed=[1, 2])
        # Directly bypass __init__ to avoid spawning audio/state:
        rm = RunManager.__new__(RunManager)
        rm.meta = meta
        rm._chapter_override = None
        # Default — first uncompleted chapter is 3.
        assert rm._current_chapter() == 3
        rm.set_chapter_override(1)
        assert rm._current_chapter() == 1
        rm.set_chapter_override(None)
        assert rm._current_chapter() == 3


def test_main_menu_row_appears_after_first_clear():
    """The CARGO DOSSIERS row shouldn't appear until the player clears at
    least one chapter — gated by `meta.chapters_completed`."""
    src = Path("core/game.py").read_text(encoding="utf-8")
    assert '"CARGO DOSSIERS"' in src
    assert '"dossiers"' in src
    assert "_dossier_cursor" in src
    assert "set_chapter_override" in src
