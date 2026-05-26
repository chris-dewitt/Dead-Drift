"""Aliveness Phase E: persistent story and world consequence hooks."""
from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from antagonists.repo_barge import BargeState
from roguelite.meta_progression import MetaProgression
from roguelite.run_manager import RunManager
from terminal.npc_logic import make_npc
from terminal.npcs.base_npc import NPCOutcome


def _meta_path(name: str) -> Path:
    path = Path("data/saves") / f"test_phase_e_{name}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _fresh_meta(name: str) -> MetaProgression:
    path = _meta_path(name)
    path.unlink(missing_ok=True)
    return MetaProgression(save_path=path)


def _load_meta(name: str) -> MetaProgression:
    return MetaProgression(save_path=_meta_path(name))


def _run_manager(meta: MetaProgression) -> RunManager:
    rm = RunManager.__new__(RunManager)
    rm.meta = meta
    rm._barge_suppression_t = 0.0
    rm._spawn_queue = []
    rm._barges = []
    return rm


def test_phase_e_meta_state_persists():
    meta = _fresh_meta("persist")

    assert meta.advance_lore_stage("debt_trap", 4) == (1, True)
    assert meta.mark_npc_dead("marrow", reason="betrayed_to_test") is True
    assert meta.set_npc_flag("kress", "owes_patrol_tip", True) is True

    reloaded = _load_meta("persist")
    assert reloaded.lore_stage("debt_trap") == 1
    assert reloaded.is_npc_dead("marrow") is True
    assert reloaded.get_npc_flag("kress", "owes_patrol_tip") is True
    assert reloaded.consume_npc_flag("kress", "owes_patrol_tip") is True
    assert _load_meta("persist").get_npc_flag("kress", "owes_patrol_tip") is False


def test_gary_and_sandra_share_history_path():
    gary = make_npc("gary", run_context={})
    out, first = gary.respond("Sandra Vega-Marsh")
    assert out == NPCOutcome.CONTINUE
    assert "partner" in first.lower() or "sandra" in first.lower()
    out, line = gary.respond("Tell me what happened with Sandra")
    assert out == NPCOutcome.RELEASE
    assert "partner" in line.lower() or "meridian" in line.lower()

    sandra = make_npc("sandra", run_context={})
    out, _ = sandra.respond("Gary Pruitt was your partner")
    assert out == NPCOutcome.CONTINUE
    out, line = sandra.respond("Meridian route, Gary Pruitt, partner")
    assert out == NPCOutcome.RELEASE
    assert "partner" in line.lower() or "gary" in line.lower()


def test_marrow_betrayal_paths_warn_then_confirm():
    kress = make_npc("kress", run_context={})
    out, line = kress.respond("I can sell out Marrow's Roost broadcast location")
    assert out == NPCOutcome.CONTINUE
    assert "confirm" in line.lower()
    out, _ = kress.respond("confirm")
    assert out == NPCOutcome.EXPLOIT
    assert kress._current_path == "MARROW SELL-OUT"

    dispatcher = make_npc("union_dispatcher", run_context={})
    out, line = dispatcher.respond("I want to report Marrow's Roost broadcast location")
    assert out == NPCOutcome.CONTINUE
    assert "confirm" in line.lower()
    out, _ = dispatcher.respond("confirm")
    assert out == NPCOutcome.EXPLOIT
    assert dispatcher._current_path == "MARROW BETRAYAL"


def test_terminal_consequences_record_kress_tip_and_marrow_death():
    meta = _fresh_meta("consequence")
    rm = _run_manager(meta)

    kress = SimpleNamespace(name="KRESS")
    rm._apply_phase_e_terminal_consequence(kress, "release", "VOLKOV")
    assert meta.get_npc_flag("kress", "owes_patrol_tip") is True

    dispatcher = SimpleNamespace(name="DISPATCHER")
    rm._apply_phase_e_terminal_consequence(dispatcher, "exploit", "MARROW BETRAYAL")
    assert meta.is_npc_dead("marrow") is True


def test_kress_patrol_tip_delays_next_barge_spawn():
    meta = _fresh_meta("kress_tip")
    meta.set_npc_flag("kress", "owes_patrol_tip", True)
    rm = _run_manager(meta)
    rm._kress_tip_pending = True
    rm._spawn_queue = [(3.0, "debris"), (5.0, "barge")]

    rm._apply_kress_patrol_tip_to_spawn_queue()

    assert rm._kress_tip_pending is False
    assert meta.get_npc_flag("kress", "owes_patrol_tip") is False
    assert (3.0, "debris") in rm._spawn_queue
    assert (15.0, "barge") in rm._spawn_queue


def test_union_schism_pulls_barges_off_case():
    meta = _fresh_meta("schism")
    meta.record_union_schism("idealist", "CHARTER")
    rm = _run_manager(meta)
    barge = SimpleNamespace(
        is_destroyed=False,
        state=BargeState.CHASE,
        _retreat_t=0.0,
        _intercept_cd=0.0,
    )
    rm._barges = [barge]
    rm._spawn_queue = [(4.0, "barge"), (2.0, "debris")]

    vince = SimpleNamespace(name="VINCE")
    rm._apply_phase_e_terminal_consequence(vince, "release", "THREATEN")

    assert meta.get_npc_flag("local_404", "schism_resolved") is True
    assert rm._barge_suppression_t > 0.0
    assert all(kind != "barge" for _, kind in rm._spawn_queue)
    assert barge.state == BargeState.RETREAT


def test_dead_marrow_terminal_maps_to_frequency_lost():
    meta = _fresh_meta("dead_marrow_terminal")
    meta.mark_npc_dead("marrow", reason="betrayed_to_test")
    rm = _run_manager(meta)
    rm._vault = None
    rm._last_winning_path = ""
    rm._t = 2.0
    rm._last_voice_char_t = 0.0
    rm._active_terminal = None
    rm._pending_terminal = None
    rm._terminal_arm_t = -1.0
    rm._ship = None

    terminal = RunManager.open_terminal(rm, "underground_dj", run_context={})

    assert terminal.npc.name == "FREQUENCY LOST"


def test_marrow_corridor_lore_becomes_raid_aftermath():
    pygame.init()
    meta = _fresh_meta("corridor_aftermath")
    meta.mark_npc_dead("marrow", reason="betrayed_to_test")

    from delivery.corridor import make_corridor

    corridor = make_corridor(1, meta=meta)
    lore_lines = [
        resp.get("lore", "")
        for room in corridor.rooms
        for el in room.elements
        for resp in getattr(el, "responses", [])
    ]

    assert any("Roost is gone" in line or "dead static" in line for line in lore_lines)
    assert not any("MARROW says hi" in line for line in lore_lines)
