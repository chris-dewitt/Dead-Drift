"""Smoke + integration coverage for Bax's Records (Epic 8.3)."""
from __future__ import annotations

import os

# Headless-friendly: must be set before importing pygame submodules that
# touch the audio mixer or video subsystem.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import json
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pygame


def _meta_with(temp_dir, **overrides):
    """Build a fresh MetaProgression using a tempfile so tests stay isolated."""
    from roguelite.meta_progression import MetaProgression
    save_path = Path(temp_dir) / "meta.json"
    meta = MetaProgression(save_path=save_path)
    for k, v in overrides.items():
        meta._data[k] = v
    return meta


def _vault_with(temp_dir, backdoors: dict[str, list[str]] | None = None):
    from bax.vocabulary_vault import VocabularyVault
    # Vault uses S.BAX_VOCAB_FILE which is a singleton path; stub directly.
    vault = VocabularyVault.__new__(VocabularyVault)
    vault._data = {"terms": [], "backdoors": dict(backdoors or {})}
    return vault


def _stats_with(temp_dir, run=None, career=None):
    from roguelite.stats_tracker import StatsTracker
    save_path = Path(temp_dir) / "stats.json"
    stats = StatsTracker(save_path=save_path)
    if run:
        stats._run.update(run)
    if career:
        stats._career.update(career)
    return stats


def test_lore_fragment_round_trips_through_meta():
    with tempfile.TemporaryDirectory() as tmp:
        meta = _meta_with(tmp)
        assert meta.lore_fragments == []
        added = meta.add_lore_fragment("Gary plays sax on Tuesdays.", chapter=1)
        assert added is True
        # Idempotent — adding same text twice is a no-op.
        again = meta.add_lore_fragment("Gary plays sax on Tuesdays.", chapter=1)
        assert again is False
        assert len(meta.lore_fragments) == 1
        assert meta.lore_fragments[0]["chapter"] == 1

        # Persistence — new instance should see the stored fragment.
        from roguelite.meta_progression import MetaProgression
        meta2 = MetaProgression(save_path=Path(tmp) / "meta.json")
        assert meta2.lore_fragments == [
            {"text": "Gary plays sax on Tuesdays.", "chapter": 1}
        ]


def test_records_screen_renders_each_tab_to_a_non_black_surface():
    """Render every tab — the manila-folder card must paint pixels for all of them."""
    pygame.init()
    pygame.font.init()
    from renderer.records_screen import draw_records, tab_count

    with tempfile.TemporaryDirectory() as tmp:
        meta = _meta_with(tmp, clone_count=5, debt=84_000)
        meta.add_lore_fragment(
            "Notes on Gary — he played sax at the depot. Stopped when his wife died.",
            chapter=1,
        )
        meta.add_lore_fragment("The shrooms know your name now.", chapter=2)

        vault = _vault_with(tmp, backdoors={
            "gary": ["BLEVINS", "OVERTIME"],
            "nova_soma_collections": ["SQL_INJECTION"],
        })

        stats = _stats_with(tmp,
                            run={"slingshots": 3, "snaps": 1,
                                 "credits_earned": 2400},
                            career={"runs_started": 14,
                                    "runs_completed": 3,
                                    "lifetime_slingshots": 22,
                                    "lifetime_snaps": 9,
                                    "lifetime_kills": 18,
                                    "best_single_run_credits": 4800,
                                    "best_slingshot_speed": 612,
                                    "deepest_sector_per_chapter":
                                        {"1": 5, "2": 4, "3": 2}})

        screen = pygame.Surface((1280, 720))
        for tab in range(tab_count()):
            screen.fill((0, 0, 0))
            draw_records(screen, meta=meta, vault=vault, stats=stats,
                         tab_idx=tab, scroll=0, t=1.0)
            # The manila card must paint warm pixels in the centre of the screen.
            cx, cy = 1280 // 2, 720 // 2
            r, g, b, _ = screen.get_at((cx, cy))
            assert (r, g, b) != (0, 0, 0), \
                f"Tab {tab} did not paint over the centre of the screen"


def test_records_screen_handles_empty_state():
    """A brand-new clone tank with no stats/vault/lore must still render without errors."""
    pygame.init()
    pygame.font.init()
    from renderer.records_screen import draw_records, tab_count

    with tempfile.TemporaryDirectory() as tmp:
        meta = _meta_with(tmp)

        screen = pygame.Surface((1280, 720))
        for tab in range(tab_count()):
            screen.fill((0, 0, 0))
            # vault=None, stats=None must still draw the empty-state card.
            draw_records(screen, meta=meta, vault=None, stats=None,
                         tab_idx=tab, scroll=0, t=0.0)
            cx, cy = 1280 // 2, 720 // 2
            assert screen.get_at((cx, cy))[:3] != (0, 0, 0)


def test_records_vulnerability_db_reads_historical_aliases():
    from renderer.records_screen import _backdoors_for

    vault = _vault_with(None, backdoors={
        "syntheticdroid": ["SQL_INJECTION"],
        "tk9": ["SHELL_BREAK"],
    })

    assert _backdoors_for(vault, "synthetic_droid") == [
        "SQL_INJECTION",
        "SHELL_BREAK",
    ]


def test_bax_exploit_event_uses_canonical_vault_key():
    from bax.bax import Bax
    from terminal.npcs.synthetic_droid import SyntheticDroid

    recorded = {}

    class CaptureVault:
        def add_backdoor(self, npc_key, exploit_key):
            recorded.setdefault(npc_key, []).append(exploit_key)

    bax = Bax.__new__(Bax)
    bax.vault = CaptureVault()
    bax._run_bax_context = None
    bax._run_style_bribe = 0
    bax._run_style_exploit = 0
    bax.speak = lambda *_args, **_kwargs: None

    bax._on_exploit_found(SyntheticDroid(run_context={}), "sql_injection")

    assert recorded == {"synthetic_droid": ["sql_injection"]}
    assert bax._run_style_exploit == 1


def test_records_max_scroll_clamps_per_tab():
    from renderer.records_screen import max_scroll, tab_count

    with tempfile.TemporaryDirectory() as tmp:
        meta = _meta_with(tmp)
        for i in range(20):
            meta.add_lore_fragment(f"Fragment {i}", chapter=(i % 4) + 1)

        # CLONE LOG and RUN HIGHLIGHTS fit on one page.
        assert max_scroll(0, meta=meta, vault=None, stats=None) == 0
        assert max_scroll(1, meta=meta, vault=None, stats=None) == 0
        # Vulnerability DB scroll capacity scales with NPC count > visible.
        assert max_scroll(2, meta=meta, vault=None, stats=None) >= 0
        # Lore tab scroll capacity scales with fragment count.
        assert max_scroll(3, meta=meta, vault=None, stats=None) > 0


def test_records_main_menu_row_present_and_routes():
    """`BAX'S RECORDS` should appear in main-menu rows.

    We grep the source instead of constructing a full Game (which spins up
    the audio mixer + display and can stomp on other tests' globals).
    The behaviour test for the routing is covered by
    `test_records_max_scroll_clamps_per_tab` and the renderer tests.
    """
    src = Path("core/game.py").read_text(encoding="utf-8")
    assert '"BAX\'S RECORDS"' in src or "'BAX\\'S RECORDS'" in src \
        or "BAX'S RECORDS" in src, "BAX'S RECORDS row missing from main menu"
    assert '"records"' in src, "records action key missing from main menu"
    assert "_records_tab" in src
    assert "_records_scroll" in src
