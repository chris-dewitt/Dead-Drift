"""Regression — ComplianceVessel must not survive death sector restart.

EncryptedDrive pursuit drones live in `_compliance_vessels`. Barges are cleared
on DECANT → `respawn_after_death` → `_restart_current_sector`, but the drones
were left alive. The fresh clone respawns at screen center; a mid-pursuit drone
often sits in the same pocket and re-rams within seconds — a Ch5/6 death spiral.
"""
from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import types

from physics.body import RigidBody2D
from antagonists.compliance_vessel import ComplianceVessel
from roguelite.run_manager import RunManager


def _bare_rm():
    rm = RunManager.__new__(RunManager)
    rm._run_seed = 1
    rm._sector_index = 2
    rm._difficulty = lambda: 1.0
    rm._current_chapter = lambda: 5
    rm._cold_sector_theme = lambda rng: None
    rm._barges = []
    rm._spawn_queue = []
    rm._sling_well_t = {}
    rm._well_hit_times = {}
    rm._sector_slingshots = 0
    rm._sector_snaps = 0
    rm._sector_credits = 0
    rm._jump_ready_fired = False
    rm._kress_called_this_sector = False
    rm._fuel_warned = False
    rm._compliance_vessels = []
    rm._compliance_spawn_cd = 0.0
    rm._active_terminal = None
    rm._intercepting_barge = None
    rm._pending_advance = False
    rm._shower_rocks = []
    rm._ship = None
    return rm


def _fake_ship():
    ship = types.SimpleNamespace(
        _destroyed=True,
        hull=0.0,
        body=RigidBody2D(100.0, 100.0, mass=1.0),
        gun=object(),
        controls_inverted=False,
        cargo=None,
    )
    return ship


def test_restart_current_sector_clears_compliance_vessels(monkeypatch):
    rm = _bare_rm()
    ship = _fake_ship()
    rm._compliance_vessels = [
        ComplianceVessel(400.0, 300.0, rm),
        ComplianceVessel(450.0, 320.0, rm),
    ]
    rm._barges = ["sentinel"]
    rm._compliance_spawn_cd = 0.0

    monkeypatch.setattr(
        "roguelite.run_manager.generate_sector",
        lambda *a, **k: types.SimpleNamespace(theme="", name="", formerly=""),
    )
    monkeypatch.setattr(rm, "_spawn_sector_objects", lambda: None)

    rm._restart_current_sector(ship)

    assert rm._compliance_vessels == []
    assert rm._barges == []
    assert rm._compliance_spawn_cd == 12.0


def test_respawn_after_death_does_not_keep_mid_pursuit_drones(monkeypatch):
    """End-to-end: DECANT path must not leave drones next to the fresh clone."""
    rm = _bare_rm()
    ship = _fake_ship()
    # Park a drone on the center respawn point — the live death-spiral case.
    from config import settings as S
    rm._compliance_vessels = [
        ComplianceVessel(S.SCREEN_W / 2 + 30.0, S.FLIGHT_H / 2, rm),
    ]

    monkeypatch.setattr(
        "roguelite.run_manager.generate_sector",
        lambda *a, **k: types.SimpleNamespace(theme="", name="", formerly=""),
    )
    monkeypatch.setattr(rm, "_spawn_sector_objects", lambda: None)

    rm.respawn_after_death(ship)

    assert rm._compliance_vessels == []
    assert ship._destroyed is False
