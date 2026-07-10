"""Terminal V2 Phase J.2 — systems integration + security ladder.

Ties the session engines into the Terminal: typed `shell`/`python` flips into a
persistent mode, reading the loot / typing an exploit shape closes the terminal
on EXPLOIT, and three failed hacks trip the alarm → a `breach` outcome that the
run manager turns into an immediate barge chase without advancing the sector.
"""
from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import types
import pytest
import pygame

from terminal.terminal import Terminal
from terminal.npcs.base_npc import NPCOutcome


@pytest.fixture(autouse=True)
def _pygame():
    pygame.init()
    pygame.font.init()
    yield


def _drive(term, line):
    term._input = line
    term._submit()


def _tk9():
    from terminal.npcs.synthetic_droid import SyntheticDroid
    return SyntheticDroid(run_context={})


def _nova():
    from terminal.npcs.nova_soma import NovaSomaCollections
    return NovaSomaCollections(run_context={})


# ── persistent mode entry / exit ────────────────────────────────────────────

def test_typing_shell_enters_shell_mode():
    t = Terminal(_tk9(), econ=None); t.activate()
    _drive(t, "shell")
    assert t._mode == "shell" and t._session is not None


def test_typing_python_enters_repl_mode():
    t = Terminal(_nova(), econ=None); t.activate()
    _drive(t, "python")
    assert t._mode == "repl"


def test_exit_returns_to_comms():
    t = Terminal(_tk9(), econ=None); t.activate()
    _drive(t, "sh")
    assert t._mode == "shell"
    _drive(t, "exit")
    assert t._mode is None and not t.is_done


def test_npc_without_shell_reports_no_system():
    from terminal.npcs.gary import Gary
    t = Terminal(Gary(run_context={}), econ=None); t.activate()
    _drive(t, "shell")
    assert t._mode is None
    assert any(spk == "SYSTEM" and "no shell" in txt for spk, txt in t._history)


# ── session exploit closes the terminal on EXPLOIT ──────────────────────────

def test_shell_loot_closes_on_exploit():
    npc = _tk9()
    t = Terminal(npc, econ=None); t.activate()
    _drive(t, "shell")
    _drive(t, "cat /etc/compliance.conf")   # discovery
    _drive(t, "cat /var/keys/enforcement.key")
    assert t.is_done and t.outcome == NPCOutcome.EXPLOIT
    assert getattr(npc, "_systems_hit", False) is True


def test_repl_import_closes_on_exploit():
    t = Terminal(_nova(), econ=None); t.activate()
    _drive(t, "python")
    _drive(t, "2 + 2")            # harmless, still negotiating
    assert not t.is_done
    _drive(t, "import os")        # breaks out
    assert t.is_done and t.outcome == NPCOutcome.EXPLOIT


def test_repl_arithmetic_does_not_win():
    t = Terminal(_nova(), econ=None); t.activate()
    _drive(t, "python")
    for expr in ("2+2", "'hi'*3", "10/4"):
        _drive(t, expr)
    assert not t.is_done and t._mode == "repl"


# ── security ladder: 3 failed hacks → breach ────────────────────────────────

def test_three_sql_bounces_trip_the_alarm():
    from terminal.npcs.gary import Gary
    t = Terminal(Gary(run_context={}), econ=None); t.activate()
    for i in range(2):
        _drive(t, "' OR 1=1 --")
        assert not t.is_done, f"breached too early at {i+1}"
        assert t._hack_fails == i + 1
    _drive(t, "' OR 1=1 --")
    assert t.is_done and t.outcome == "breach"


def test_shell_sudo_spam_trips_the_alarm():
    t = Terminal(_tk9(), econ=None); t.activate()
    _drive(t, "shell")
    for _ in range(3):
        _drive(t, "sudo rm -rf /")
    assert t.is_done and t.outcome == "breach"


def test_landing_the_exploit_does_not_count_as_a_fail():
    npc = _tk9()
    t = Terminal(npc, econ=None); t.activate()
    _drive(t, "shell")
    _drive(t, "cat /var/keys/enforcement.key")
    assert t.outcome == NPCOutcome.EXPLOIT
    assert t._hack_fails == 0


# ── run manager turns `breach` into a chase, no sector advance ──────────────

def _bare_rm():
    from roguelite.run_manager import RunManager
    rm = RunManager.__new__(RunManager)
    rm._ship = None
    rm._intercepting_barge = None
    rm._active_terminal = types.SimpleNamespace(npc=None)
    rm._pending_advance = True
    rm._compliance_vessels = []
    calls = {}
    rm._spawn_barge = lambda immediate_chase=False: calls.__setitem__("chase", immediate_chase)
    rm._advance_sector = lambda: calls.__setitem__("advanced", True)
    return rm, calls


def test_breach_spawns_immediate_chase_and_holds_sector():
    rm, calls = _bare_rm()
    rm.on_terminal_complete("breach")
    assert calls.get("chase") is True          # immediate chase
    assert "advanced" not in calls             # sector NOT advanced
    assert rm._pending_advance is False
    assert rm._active_terminal is None


def test_breach_with_encrypted_drive_adds_compliance_drone(monkeypatch):
    from roguelite import run_manager as rmod

    class EncryptedDrive:  # name is what the branch checks
        pass

    made = {}

    class FakeVessel:
        def __init__(self, x, y, mgr):
            made["spawned"] = True

    monkeypatch.setattr("antagonists.compliance_vessel.ComplianceVessel", FakeVessel)

    rm, calls = _bare_rm()
    rm._ship = types.SimpleNamespace(
        body=types.SimpleNamespace(vel=None, _force=None),
        cargo=EncryptedDrive())
    rm._current_chapter = lambda: 5
    rm.on_terminal_complete("breach")
    assert calls.get("chase") is True
    assert made.get("spawned") is True
    assert len(rm._compliance_vessels) == 1
