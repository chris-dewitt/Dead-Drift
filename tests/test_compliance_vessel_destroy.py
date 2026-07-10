"""Regression — destroying a ComplianceVessel must not crash.

EVT_AISHIP_DESTROYED is fired by AIShip *and* by ComplianceVessel. The single
handler `_on_aiship_destroyed` read `ship.is_pirate` unconditionally, but a
ComplianceVessel is not an AIShip and has no such attribute — so shooting one
down raised `AttributeError: 'ComplianceVessel' object has no attribute
'is_pirate'` (hit live while play-testing; a J.2.4 breach spawns these drones).
"""
from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import types

from core.event_bus import bus, EVT_AISHIP_DESTROYED
from antagonists.compliance_vessel import ComplianceVessel
from roguelite.run_manager import RunManager


def _bare_rm():
    return RunManager.__new__(RunManager)


def test_compliance_vessel_has_no_is_pirate():
    cv = ComplianceVessel(100.0, 100.0, run_manager=_bare_rm())
    assert not hasattr(cv, "is_pirate")   # the premise of the bug


def test_handler_survives_a_downed_compliance_vessel():
    rm = _bare_rm()
    cv = ComplianceVessel(100.0, 100.0, run_manager=rm)
    rm._on_aiship_destroyed(ship=cv)       # used to raise AttributeError


def test_full_bus_path_take_hit_to_death_does_not_crash():
    """Reproduce the live crash: take_hit → EVT_AISHIP_DESTROYED → handler."""
    rm = _bare_rm()
    bus.subscribe(EVT_AISHIP_DESTROYED, rm._on_aiship_destroyed)
    try:
        cv = ComplianceVessel(100.0, 100.0, run_manager=rm)
        for _ in range(ComplianceVessel.HULL_HITS):
            cv.take_hit(1)                 # last hit emits the event
        assert cv.alive is False
    finally:
        # don't leak the subscription into other tests
        bus.unsubscribe(EVT_AISHIP_DESTROYED, rm._on_aiship_destroyed)


def test_pirate_kill_still_recognised():
    rm = _bare_rm()
    pirate = types.SimpleNamespace(is_pirate=True)
    rm._on_aiship_destroyed(ship=pirate)   # must not raise
    rm._on_aiship_destroyed(ship=None)     # None is a safe no-op
