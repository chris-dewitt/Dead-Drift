"""Aliveness A.6 — Ch.3 Paperwork corridor input lock + OneWayWall wiring.

Playtest (Chris, May 2026): in File Room 4 (at the ladder, paper visible),
input died — movement, ESC, pause (1), everything unresponsive. The
clerk dialog had opened modally with:
  * no ESC handler in `_CorridorDialog.handle_key`
  * `GameState.DELIVERY` not in `_PAUSEABLE`
  * `_check_npc_encounters` could fire while the player was climbing

This pins all four fixes."""
from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame


def test_dialog_esc_aborts_with_penalty_outcome():
    pygame.init()
    pygame.font.init()
    from delivery.corridor.base import _CorridorDialog
    from delivery.corridor.elements import NPCEncounter

    enc = NPCEncounter(
        x=300, npc_name="CLERK", prompt="Form 27-B please.",
        responses=[
            {"keywords": ["form"], "credits": 100, "outcome": "reward",
             "lore": "Done."},
            {"keywords": [], "credits": -50, "outcome": "penalty",
             "lore": "Filed under K-9."},
        ],
    )
    dlg = _CorridorDialog(enc)

    esc = pygame.event.Event(pygame.KEYDOWN,
                             {"key": pygame.K_ESCAPE, "unicode": "\x1b"})
    dlg.handle_key(esc)
    assert dlg._result is not None
    _credits, _lore, outcome = dlg._result
    assert outcome == "penalty"


def test_dialog_esc_uses_synthesised_penalty_when_none_declared():
    pygame.init()
    pygame.font.init()
    from delivery.corridor.base import _CorridorDialog
    from delivery.corridor.elements import NPCEncounter

    enc = NPCEncounter(
        x=300, npc_name="CLERK", prompt="Sign?",
        responses=[
            {"keywords": ["form"], "credits": 100, "outcome": "reward",
             "lore": "Done."},
        ],   # No penalty response declared
    )
    dlg = _CorridorDialog(enc)
    esc = pygame.event.Event(pygame.KEYDOWN,
                             {"key": pygame.K_ESCAPE, "unicode": "\x1b"})
    dlg.handle_key(esc)
    assert dlg._result is not None
    _credits, _lore, outcome = dlg._result
    assert outcome == "penalty"


def test_corridor_npc_encounter_defers_while_on_ladder():
    """Aliveness A.6 — encounter must not trigger while climbing."""
    pygame.init()
    pygame.font.init()
    from delivery.corridor import make_corridor
    from delivery.corridor.elements import NPCEncounter

    c = make_corridor(3)
    # Find a room that has an NPC encounter.
    target_room = None
    target_enc = None
    for room in c.rooms:
        for el in room.elements:
            if isinstance(el, NPCEncounter):
                target_room = room
                target_enc  = el
                break
        if target_room:
            break
    assert target_enc is not None, "Ch.3 should have at least one NPCEncounter"

    # Position the courier so the encounter would trigger if not for the ladder gate.
    c._room_idx     = c.rooms.index(target_room)
    c._px           = float(target_enc.x)
    c._py           = 100.0
    c._on_ladder    = True
    c._grounded     = False
    c._check_npc_encounters(target_room)
    assert c._dialog is None, "encounter must defer while on ladder"

    # Now drop off the ladder — encounter should fire.
    c._on_ladder = False
    c._grounded  = True
    c._check_npc_encounters(target_room)
    assert c._dialog is not None, "encounter should fire once grounded"


def test_delivery_is_now_pauseable():
    """Aliveness A.6 — DELIVERY belongs to the PAUSEABLE set so 1-key opens pause."""
    from pathlib import Path
    src = Path("core/game.py").read_text(encoding="utf-8")
    assert "GameState.DELIVERY," in src
    # The pause-on-ESC branch must exempt DELIVERY just like TERMINAL.
    assert "state != GameState.DELIVERY" in src


def test_oneway_wall_collision_now_gates_forward_movement():
    pygame.init()
    pygame.font.init()
    from delivery.corridor.base import Corridor, Room
    from delivery.corridor.elements import OneWayWall

    # Build a minimal one-room corridor with a single blocks-right wall.
    wall = OneWayWall(x=200, y_top=100, y_bot=400, blocks_right=True)
    room = Room(length=600, palette={}, elements=[wall])
    c = Corridor(chapter=1, rooms=[room])
    c._px = 100.0
    c._py = 200.0    # within wall's vertical band
    # Simulate forward motion arriving inside the wall's collision band
    # (PLAYER_W // 2 + 2 == 11). x=205 is well within abs(x-200) < 11.
    blocked = c._blocked_by_oneway(205.0, +220.0, room)
    assert blocked is True, "forward motion past blocks_right wall must be blocked"
    # Backward motion through the same band is allowed (blocks_right=True
    # only constrains forward motion).
    not_blocked = c._blocked_by_oneway(205.0, -220.0, room)
    assert not_blocked is False


def test_dialog_render_shows_escape_hint():
    """Aliveness A.6 — the corridor dialog now visibly advertises ESC skip."""
    pygame.init()
    pygame.font.init()
    from delivery.corridor.base import _CorridorDialog
    from delivery.corridor.elements import NPCEncounter, CORRIDOR_W, CORRIDOR_H

    enc = NPCEncounter(x=300, npc_name="CLERK", prompt="Form please.",
                       responses=[{"keywords": [], "credits": 0,
                                   "outcome": "penalty", "lore": "Skipped."}])
    dlg = _CorridorDialog(enc)
    surf = pygame.Surface((CORRIDOR_W, CORRIDOR_H))
    dlg.draw(surf, t=0.0)
    # Confirm the dialog box painted something inside its rectangle (we
    # just want to know the dialog draw fired; the hint string itself is
    # asserted by source inspection in the next test below).
    dx = (CORRIDOR_W - dlg.DIALOG_W) // 2
    dy = (CORRIDOR_H - dlg.DIALOG_H) // 2
    cx = dx + dlg.DIALOG_W // 2
    cy = dy + 4   # header area
    assert surf.get_at((cx, cy))[:3] != (0, 0, 0)


def test_dialog_render_source_includes_esc_hint_string():
    """Hard guard against the hint regressing out — string lives in source."""
    from pathlib import Path
    src = Path("delivery/corridor/base.py").read_text(encoding="utf-8")
    assert "ESC skip" in src
    assert "ENTER submit" in src
