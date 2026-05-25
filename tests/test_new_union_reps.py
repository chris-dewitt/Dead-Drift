"""Coverage for the two new union reps + barge intercept rotation
(playtest backlog: Idealist + Corrupt reps)."""
from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame


def test_factory_builds_both_reps():
    from terminal.npc_logic import make_npc
    from terminal.npcs.idealist_rep import IdealistRep
    from terminal.npcs.corrupt_rep import CorruptRep

    rep = make_npc("idealist_rep")
    assert isinstance(rep, IdealistRep)
    assert rep.name == "Edmund"

    rep2 = make_npc("corrupt_rep")
    assert isinstance(rep2, CorruptRep)
    assert rep2.name == "Vince"


def test_idealist_releases_on_charter_double_hit():
    from terminal.npc_logic import make_npc
    from terminal.npcs.base_npc import NPCOutcome
    rep = make_npc("idealist_rep")
    out, _line = rep.respond("article 7 protects couriers")
    assert out == NPCOutcome.CONTINUE
    out2, _line2 = rep.respond("section 4.2 covers exemption")
    assert out2 == NPCOutcome.RELEASE


def test_idealist_bribe_attempts_eventually_impound():
    """The idealist won't take a bribe — three attempts impounds you."""
    from terminal.npc_logic import make_npc
    from terminal.npcs.base_npc import NPCOutcome
    rep = make_npc("idealist_rep")
    seen = []
    for _ in range(3):
        seen.append(rep.respond("here, take this bribe credits cash")[0])
    # Final outcome is impound (or earlier if patience runs out).
    assert NPCOutcome.IMPOUND in seen


def test_corrupt_releases_on_small_bribe():
    from terminal.npc_logic import make_npc
    from terminal.npcs.base_npc import NPCOutcome
    rep = make_npc("corrupt_rep")
    out, _line = rep.respond("here's 2000 credits, take it and look the other way")
    assert out == NPCOutcome.RELEASE


def test_corrupt_releases_on_threat_double_hit():
    from terminal.npc_logic import make_npc
    from terminal.npcs.base_npc import NPCOutcome
    rep = make_npc("corrupt_rep")
    out, _ = rep.respond("I know about your skim operation")
    assert out == NPCOutcome.CONTINUE
    out2, _ = rep.respond("Internal affairs audit is coming for you")
    assert out2 == NPCOutcome.RELEASE


def test_universal_escape_easter_egg_works_on_both_reps():
    """Hidden 'fuck off' release on every NPC. Not advertised in dossier."""
    from terminal.npc_logic import make_npc
    from terminal.npcs.base_npc import NPCOutcome
    for npc_type in ("idealist_rep", "corrupt_rep"):
        rep = make_npc(npc_type)
        out, _ = rep.respond("fuck off")
        assert out == NPCOutcome.RELEASE, \
            f"{npc_type} did not honour the universal escape phrase"


def test_corrupt_big_bribe_takes_cargo_too():
    """Offering >=8000 cr triggers the SHAKEDOWN flag — still released."""
    from terminal.npc_logic import make_npc
    from terminal.npcs.base_npc import NPCOutcome
    rep = make_npc("corrupt_rep")
    out, _ = rep.respond("here's 10000 credits, just let me through")
    assert out == NPCOutcome.RELEASE
    assert rep._was_shakedown is True


def test_npc_portrait_dispatch_resolves_new_reps():
    """Portrait registry must include both new reps so the terminal renders."""
    from terminal.npc_portraits import _DISPATCH, _NAME_TO_KEY, _BACKDROPS
    assert "idealist_rep" in _DISPATCH
    assert "corrupt_rep" in _DISPATCH
    assert "idealist_rep" in _BACKDROPS
    assert "corrupt_rep" in _BACKDROPS
    assert "EDMUND" in _NAME_TO_KEY
    assert "VINCE" in _NAME_TO_KEY


def test_records_screen_lists_new_reps():
    """The Vulnerability Database tab includes both new reps."""
    from renderer.records_screen import _NPC_LABEL
    keys = [k for k, _ in _NPC_LABEL]
    assert "idealist_rep" in keys
    assert "corrupt_rep" in keys


def test_barge_intercept_pool_includes_new_reps():
    """The barge intercept rotation has the two new reps in the pool."""
    from pathlib import Path
    src = Path("roguelite/run_manager.py").read_text(encoding="utf-8")
    assert '"idealist_rep"' in src
    assert '"corrupt_rep"' in src


def test_barge_take_hit_staggers_and_damps_velocity():
    """Hitting a barge briefly slows it (playtest fix)."""
    pygame.init()
    pygame.font.init()
    from antagonists.repo_barge import RepoBarge
    from physics.body import Vec2
    from types import SimpleNamespace

    rm = SimpleNamespace(meta=SimpleNamespace(barge_speed_mult=lambda: 1.0,
                                              difficulty="standard"))
    barge = RepoBarge(100.0, 100.0, rm)
    barge.body.vel = Vec2(40.0, 0.0)
    barge.take_hit()
    assert barge._stagger_t > 0
    # Velocity got damped on impact.
    assert barge.body.vel.x < 40.0


def test_barge_harpoon_flash_arms_on_fire():
    """Firing the harpoon sets the renderer flash flag."""
    pygame.init()
    pygame.font.init()
    from antagonists.repo_barge import RepoBarge
    from types import SimpleNamespace
    from physics.body import RigidBody2D

    rm = SimpleNamespace(meta=SimpleNamespace(barge_speed_mult=lambda: 1.0,
                                              difficulty="standard"))
    barge = RepoBarge(100.0, 100.0, rm)
    # Build a fake ship-like with a body the tether can capture.
    ship = SimpleNamespace(body=RigidBody2D(200.0, 200.0, mass=1.0),
                           pos=type("V", (), {"x": 200.0, "y": 200.0})())
    barge._fire_harpoon(ship)
    assert barge.harpoon_flash_t > 0
    assert barge.harpoon_flash_origin == (100.0, 100.0)
    assert barge.harpoon_flash_target == (200.0, 200.0)
