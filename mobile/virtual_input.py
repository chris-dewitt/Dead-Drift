"""Synthetic controls for touch overlays.

Gameplay code keeps reading pygame-style key state. This module ORs a
virtual hold-set and an analog stick on top of the real keyboard so
desktop WASD still works in mobile-preview mode.
"""
from __future__ import annotations

import pygame

DEADZONE = 0.18

# analog: x -1..1 (left/right), y -1..1 (down/up, +y is forward / climb)
_analog_x = 0.0
_analog_y = 0.0
_held: set[int] = set()
_analog_keys: set[int] = set()
_pulses: list[int] = []


class _MergedPressed:
    """Dict-like stand-in for pygame.key.get_pressed()."""

    def __init__(self, keys, extra: set[int]):
        self._keys = keys
        self._extra = extra

    def __getitem__(self, key: int) -> bool:
        try:
            if self._keys[key]:
                return True
        except (IndexError, TypeError, KeyError):
            pass
        return key in self._extra


def reset() -> None:
    global _analog_x, _analog_y
    _analog_x = 0.0
    _analog_y = 0.0
    _held.clear()
    _analog_keys.clear()
    _pulses.clear()


def set_analog(x: float, y: float) -> None:
    global _analog_x, _analog_y
    _analog_x = max(-1.0, min(1.0, float(x)))
    _analog_y = max(-1.0, min(1.0, float(y)))
    _sync_analog_keys()


def get_analog() -> tuple[float, float]:
    return _analog_x, _analog_y


def analog_active() -> bool:
    return abs(_analog_x) > DEADZONE or abs(_analog_y) > DEADZONE


def hold(key: int) -> None:
    _held.add(int(key))


def release(key: int) -> None:
    _held.discard(int(key))


def pulse(key: int) -> None:
    """One-frame KEYDOWN to inject into Game._route_keydown."""
    _pulses.append(int(key))


def drain_pulses() -> list[int]:
    keys = list(_pulses)
    _pulses.clear()
    return keys


def get_pressed():
    extra = _held | _analog_keys
    try:
        keys = pygame.key.get_pressed()
    except (pygame.error, TypeError):
        keys = {}
    return _MergedPressed(keys, extra)


def _sync_analog_keys() -> None:
    """Corridor / dock still poll discrete WASD — mirror the stick."""
    _analog_keys.clear()
    if _analog_x < -DEADZONE:
        _analog_keys.add(pygame.K_a)
        _analog_keys.add(pygame.K_LEFT)
    elif _analog_x > DEADZONE:
        _analog_keys.add(pygame.K_d)
        _analog_keys.add(pygame.K_RIGHT)
    if _analog_y > DEADZONE:
        _analog_keys.add(pygame.K_w)
        _analog_keys.add(pygame.K_UP)
    elif _analog_y < -DEADZONE:
        _analog_keys.add(pygame.K_s)
        _analog_keys.add(pygame.K_DOWN)


def extra_keys() -> frozenset[int]:
    return frozenset(_held | _analog_keys)
