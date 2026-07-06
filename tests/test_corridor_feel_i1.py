"""Delivery v2 Phase I.1 — corridor movement feel regression tests.

Covers the momentum model (accel, skid, sprint charge), the jump-feel
trio (variable height, coyote time, jump buffering), and the pose /
feedback state they drive. All headless: pygame.key.get_pressed is
monkeypatched and updates are stepped at a fixed 60 Hz.
"""
from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest

from delivery.corridor.base import (
    Corridor, Room,
    WALK_SPEED, SPRINT_SPEED, RETREAT_FACTOR,
    COYOTE_TIME, JUMP_BUFFER,
    FLOOR_Y, PLAYER_H,
)

DT = 1.0 / 60.0


class _Keys:
    """Stand-in for pygame.key.get_pressed()."""
    def __init__(self, held=()):
        self._held = set(held)

    def __getitem__(self, k):
        return k in self._held


@pytest.fixture(autouse=True)
def _pygame(monkeypatch):
    pygame.init()
    yield


def _bare(length: int = 100_000) -> Corridor:
    return Corridor(chapter=1,
                    rooms=[Room(length=length, palette={}, elements=[])])


def _hold(monkeypatch, *keys):
    monkeypatch.setattr(pygame.key, "get_pressed", lambda: _Keys(keys))


def _press_jump(c: Corridor):
    c.handle_key(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_SPACE}))


# ── I.1.1 momentum ──────────────────────────────────────────────────────────

def test_ground_acceleration_ramps_to_walk_cap(monkeypatch):
    c = _bare()
    _hold(monkeypatch, pygame.K_d)
    c.update(DT)
    assert 0 < c._pvx < WALK_SPEED, "speed must ramp, not snap"
    for _ in range(90):
        c.update(DT)
    assert c._pvx == pytest.approx(WALK_SPEED)


def test_releasing_input_decelerates_not_stops(monkeypatch):
    c = _bare()
    _hold(monkeypatch, pygame.K_d)
    for _ in range(90):
        c.update(DT)
    _hold(monkeypatch)  # nothing held
    c.update(DT)
    assert 0 < c._pvx < WALK_SPEED, "momentum must carry after release"
    for _ in range(60):
        c.update(DT)
    assert c._pvx == pytest.approx(0.0)


def test_sprint_charge_is_earned_then_reaches_sprint_speed(monkeypatch):
    c = _bare()
    _hold(monkeypatch, pygame.K_d, pygame.K_LSHIFT)
    for _ in range(12):   # 0.2 s — charge still building
        c.update(DT)
    assert c._pvx < SPRINT_SPEED
    for _ in range(120):  # sustained run locks full sprint
        c.update(DT)
    assert c._pvx == pytest.approx(SPRINT_SPEED)
    assert c._sprint_locked is True


def test_without_sprint_key_speed_caps_at_walk(monkeypatch):
    c = _bare()
    _hold(monkeypatch, pygame.K_d)
    for _ in range(150):
        c.update(DT)
    assert c._pvx == pytest.approx(WALK_SPEED)


def test_reversal_at_speed_triggers_skid_with_dust(monkeypatch):
    c = _bare()
    _hold(monkeypatch, pygame.K_d)
    for _ in range(90):
        c.update(DT)
    _hold(monkeypatch, pygame.K_a)
    c.update(DT)
    assert c._skid_t > 0
    assert c._dust, "skid must kick up dust"
    assert c._pose() == "skid"


def test_retreat_speed_is_capped(monkeypatch):
    c = _bare()
    c._px = 5000.0
    c._cam_x = c._px - 100.0
    _hold(monkeypatch, pygame.K_a)
    for _ in range(90):
        c.update(DT)
    assert abs(c._pvx) <= WALK_SPEED * RETREAT_FACTOR + 1.0


# ── I.1.2 jump feel ─────────────────────────────────────────────────────────

def _apex_height(monkeypatch, hold_frames: int) -> float:
    c = _bare()
    _hold(monkeypatch)
    _press_jump(c)
    top = c._py
    for i in range(80):
        if i < hold_frames:
            _hold(monkeypatch, pygame.K_SPACE)
        else:
            _hold(monkeypatch)
        c.update(DT)
        top = min(top, c._py)
        if c._grounded and i > 3:
            break
    return (FLOOR_Y - PLAYER_H) - top


def test_variable_jump_height(monkeypatch):
    held = _apex_height(monkeypatch, hold_frames=40)
    tap  = _apex_height(monkeypatch, hold_frames=2)
    assert held > tap + 20, f"held jump ({held:.0f}px) must rise well above tap ({tap:.0f}px)"


def test_coyote_time_allows_late_jump(monkeypatch):
    c = _bare()
    c._grounded = False
    c._coyote_t = COYOTE_TIME * 0.8
    _press_jump(c)
    assert c._pvy < 0, "jump within coyote grace must fire"


def test_no_jump_after_coyote_expires(monkeypatch):
    c = _bare()
    c._grounded = False
    c._coyote_t = 0.0
    c._py -= 60.0
    c._pvy = 50.0
    _press_jump(c)
    assert c._pvy > 0, "airborne past coyote grace must not jump"


def test_jump_buffer_fires_on_landing(monkeypatch):
    c = _bare()
    c._grounded = False
    c._coyote_t = 0.0
    c._py -= 18.0
    c._pvy = 120.0    # touches down well inside the buffer window
    _press_jump(c)
    assert c._pvy > 0  # nothing yet — press is buffered
    assert c._jump_buf_t == pytest.approx(JUMP_BUFFER)
    _hold(monkeypatch)
    jumped = False
    for _ in range(20):
        c.update(DT)
        if c._pvy < 0:
            jumped = True
            break
    assert jumped, "buffered press must convert into a jump on touchdown"


def test_landing_from_height_squashes_and_dusts(monkeypatch):
    c = _bare()
    c._grounded = False
    c._py -= 120.0
    c._pvy = 0.0
    _hold(monkeypatch)
    for _ in range(60):
        c.update(DT)
        if c._grounded:
            break
    assert c._grounded
    assert c._land_squash_t > 0
    assert c._dust


# ── I.1.3 poses ─────────────────────────────────────────────────────────────

def test_pose_state_machine(monkeypatch):
    c = _bare()
    assert c._pose() == "idle"
    c._pvx = 200.0
    assert c._pose() == "run"
    c._grounded, c._pvy = False, -300.0
    assert c._pose() == "jump"
    c._pvy = 250.0
    assert c._pose() == "fall"
    c._grounded, c._pvy, c._pvx = True, 0.0, 0.0
    c._victory = True
    assert c._pose() == "victory"


def test_all_poses_render(monkeypatch):
    from renderer.sci_fi_ui import draw_courier_sprite
    pygame.font.init()
    surf = pygame.Surface((64, 76), pygame.SRCALPHA)
    for pose in ("idle", "run", "jump", "fall", "skid", "victory"):
        draw_courier_sprite(surf, 32, 22, 1.0, pose=pose, walk_phase=2.0)


# ── I.1 integration: chapters still construct and step ──────────────────────

def test_all_chapters_update_and_draw_with_new_movement(monkeypatch):
    pygame.font.init()
    from delivery.corridor import make_corridor
    _hold(monkeypatch, pygame.K_d)
    for ch in range(1, 7):
        c = make_corridor(ch)
        for _ in range(30):
            c.update(DT)
        c.draw(None, 0, 0)
        assert c._px > 120.0, f"chapter {ch}: courier must move forward"
