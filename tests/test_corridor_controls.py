"""Regression coverage for corridor jump and ladder control."""
from __future__ import annotations

import pygame
import pytest


class _PressedKeys:
    def __init__(self, *keys: int):
        self._keys = set(keys)

    def __getitem__(self, key: int) -> bool:
        return key in self._keys


def _set_pressed(monkeypatch: pytest.MonkeyPatch, *keys: int) -> None:
    monkeypatch.setattr(pygame.key, "get_pressed", lambda: _PressedKeys(*keys))


def _corridor_with_ladder():
    from delivery.corridor.base import Corridor, Room
    from delivery.corridor.elements import CEIL_Y, FLOOR_Y, Ladder

    ladder = Ladder(120, CEIL_Y, FLOOR_Y - 10)
    room = Room(800, {}, [ladder])
    return Corridor(1, [room]), ladder


def test_ladder_bottom_does_not_recapture_when_pressing_down(monkeypatch):
    from delivery.corridor.elements import FLOOR_Y, PLAYER_H

    corridor, ladder = _corridor_with_ladder()
    corridor._px = ladder.x
    corridor._py = float(FLOOR_Y - PLAYER_H)
    corridor._grounded = True
    corridor._on_ladder = False

    _set_pressed(monkeypatch, pygame.K_DOWN)
    corridor.update(0.1)

    assert corridor._on_ladder is False
    assert corridor._grounded is True
    assert corridor._py == pytest.approx(FLOOR_Y - PLAYER_H)


def test_ladder_bottom_still_allows_climbing_up(monkeypatch):
    from delivery.corridor.elements import FLOOR_Y, PLAYER_H

    corridor, ladder = _corridor_with_ladder()
    corridor._px = ladder.x
    corridor._py = float(FLOOR_Y - PLAYER_H)
    corridor._grounded = True
    corridor._on_ladder = False

    _set_pressed(monkeypatch, pygame.K_UP)
    corridor.update(0.1)

    assert corridor._on_ladder is True
    assert corridor._grounded is False
    assert corridor._py < FLOOR_Y - PLAYER_H


def test_horizontal_input_steps_off_ladder(monkeypatch):
    corridor, ladder = _corridor_with_ladder()
    corridor._px = ladder.x
    corridor._py = 180.0
    corridor._grounded = False
    corridor._on_ladder = True

    _set_pressed(monkeypatch, pygame.K_d)
    corridor.update(0.1)

    assert corridor._px > ladder.x
    assert corridor._on_ladder is False
    assert corridor._ladder_release_t > 0


def test_space_jump_from_ladder_reenters_air_control(monkeypatch):
    corridor, ladder = _corridor_with_ladder()
    start_x = ladder.x
    start_y = 180.0
    corridor._px = start_x
    corridor._py = start_y
    corridor._grounded = False
    corridor._on_ladder = True

    event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE)
    corridor.handle_key(event)

    assert corridor._on_ladder is False
    assert corridor._pvy < 0

    _set_pressed(monkeypatch, pygame.K_d)
    corridor.update(0.1)

    assert corridor._px > start_x
    assert corridor._py < start_y
