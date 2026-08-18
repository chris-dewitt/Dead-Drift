"""Pirate CARGO OFFER must be a real sacrifice, not a substring farm.

Bare tokens like "yours" / "keep it" / "the cargo" used to RELEASE
ordinary refusals ("talk about yourself", "I want to keep it") and then
grant the 2,500 negotiation payout while leaving the hold intact.
"""
from __future__ import annotations

import os
from types import SimpleNamespace

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest

from terminal.npc_logic import make_npc
from terminal.npcs.base_npc import NPCOutcome


@pytest.fixture(autouse=True)
def _pygame():
    pygame.init()
    pygame.font.init()
    yield


def _pirate():
    return make_npc("pirate", run_context={"run_snaps": 0})


@pytest.mark.parametrize("phrase", [
    "I want to keep it",
    "don't take it",
    "I won't give it to you",
    "talk about yourself",
    "I will not give you the cargo",
    "you can't have the cargo",
    "leave the ship alone",
    "drop the attitude",
    "all of it is mine",
    "the cargo is mine",
    "hello",
])
def test_refusal_and_chatter_do_not_sacrifice_cargo(phrase):
    npc = _pirate()
    out, _ = npc.respond(phrase)
    assert out != NPCOutcome.RELEASE
    assert npc._current_path != "CARGO OFFER"
    assert npc._cargo_offered is False


@pytest.mark.parametrize("phrase", [
    "take the cargo",
    "have the cargo",
    "you can have my cargo",
    "the cargo is yours",
    "it's yours",
    "drop the cargo",
    "leave the cargo",
    "take it",
    "give you the cargo",
    "take all of it",
])
def test_explicit_cargo_offer_releases(phrase):
    npc = _pirate()
    out, _ = npc.respond(phrase)
    assert out == NPCOutcome.RELEASE
    assert npc._current_path == "CARGO OFFER"
    assert npc._cargo_offered is True


def test_cargo_offer_clears_hold_and_skips_negotiation_payout():
    from cargo.acoustic_archive import AcousticArchive
    from roguelite.meta_progression import MetaProgression
    from roguelite.run_manager import RunManager

    meta = MetaProgression.__new__(MetaProgression)
    meta._data = {
        "debt": 80000,
        "chapters_completed": [],
        "bar_credits": 0,
        "clone_count": 0,
    }
    meta.pay_off = MetaProgression.pay_off.__get__(meta, MetaProgression)
    meta.add_debt = MetaProgression.add_debt.__get__(meta, MetaProgression)

    cargo = AcousticArchive()
    ship = SimpleNamespace(cargo=cargo, body=SimpleNamespace(vel=None, _force=None))

    rm = RunManager.__new__(RunManager)
    rm.meta = meta
    rm._ship = ship
    rm._intercepting_barge = None
    rm._pending_advance = False
    rm._active_terminal = None
    rm._run_debt_reduced = 0
    rm._sector_credits = 0
    rm._last_winning_path = ""
    rm._barges = []
    rm._spawn_queue = []
    rm._barge_suppression_t = 0.0

    npc = _pirate()
    out, _ = npc.respond("take the cargo")
    assert out == NPCOutcome.RELEASE

    terminal = SimpleNamespace(npc=npc)
    rm._active_terminal = terminal
    debt_before = meta._data["debt"]
    rm.on_terminal_complete("release")

    assert ship.cargo is None
    assert rm._run_debt_reduced == 0
    assert rm._sector_credits == 0
    assert meta._data["debt"] == debt_before


def test_mutual_respect_still_pays_release_bonus():
    from roguelite.meta_progression import MetaProgression
    from roguelite.run_manager import RunManager
    from terminal.economy import RELEASE_PAYOUT

    meta = MetaProgression.__new__(MetaProgression)
    meta._data = {
        "debt": 80000,
        "chapters_completed": [],
        "bar_credits": 0,
        "clone_count": 0,
    }
    meta.pay_off = MetaProgression.pay_off.__get__(meta, MetaProgression)

    cargo = object()
    ship = SimpleNamespace(cargo=cargo, body=SimpleNamespace(vel=None, _force=None))

    rm = RunManager.__new__(RunManager)
    rm.meta = meta
    rm._ship = ship
    rm._intercepting_barge = None
    rm._pending_advance = False
    rm._active_terminal = None
    rm._run_debt_reduced = 0
    rm._sector_credits = 0
    rm._last_winning_path = ""
    rm._barges = []
    rm._spawn_queue = []
    rm._barge_suppression_t = 0.0

    npc = _pirate()
    npc.respond("bollocks to the charter")
    out, _ = npc.respond("no law out here mate")
    assert out == NPCOutcome.RELEASE
    assert npc._current_path == "MUTUAL RESPECT"

    rm._active_terminal = SimpleNamespace(npc=npc)
    rm.on_terminal_complete("release")

    assert ship.cargo is cargo
    assert rm._run_debt_reduced == RELEASE_PAYOUT
    assert rm._sector_credits == RELEASE_PAYOUT
    assert meta._data["debt"] == 80000 - RELEASE_PAYOUT
