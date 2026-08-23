"""Android slice — virtual input, letterbox, skip-terminals."""
from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from pathlib import Path

import pygame
import pytest

from mobile.mode import set_mobile, is_mobile, skip_shops, skip_terminals
from mobile import virtual_input as V
from mobile.display import LetterboxDisplay
from config import settings as S


@pytest.fixture(autouse=True)
def _reset_mobile():
    pygame.init()
    set_mobile(False)
    V.reset()
    yield
    set_mobile(False)
    V.reset()


def test_mode_flags_follow_set_mobile():
    set_mobile(True)
    assert is_mobile() is True
    assert skip_terminals() is True
    assert skip_shops() is True
    set_mobile(False)
    assert skip_terminals() is False


def test_virtual_input_ors_keyboard(monkeypatch):
    class _Keys:
        def __getitem__(self, k):
            return k == pygame.K_w

    monkeypatch.setattr(pygame.key, "get_pressed", lambda: _Keys())
    V.hold(pygame.K_SPACE)
    keys = V.get_pressed()
    assert keys[pygame.K_w] is True
    assert keys[pygame.K_SPACE] is True
    assert keys[pygame.K_a] is False


def test_analog_mirrors_wasd():
    V.set_analog(0.8, 0.9)
    keys = V.get_pressed()
    assert keys[pygame.K_d]
    assert keys[pygame.K_w]
    V.set_analog(-0.9, -0.7)
    keys = V.get_pressed()
    assert keys[pygame.K_a]
    assert keys[pygame.K_s]


def test_analog_deadzone_is_neutral():
    V.set_analog(0.05, -0.04)
    assert V.analog_active() is False
    keys = V.get_pressed()
    assert not keys[pygame.K_w]
    assert not keys[pygame.K_a]


def test_ship_analog_rotates_and_thrusts():
    from ship.ship import PlayerShip
    ship = PlayerShip()
    start_angle = ship.body.angle
    V.set_analog(1.0, 1.0)
    ship.update(0.05)
    assert ship.body.angle != start_angle
    assert ship.body.vel.length() > 0
    assert ship._thrusting is True


def test_letterbox_maps_phone_and_tablet():
    window = pygame.Surface((2340, 1080))  # ~19.5:9 phone
    disp = LetterboxDisplay(window)
    disp.surface = pygame.Surface((S.SCREEN_W, S.SCREEN_H))
    disp.relayout()
    assert disp.dest.h == 1080
    assert disp.dest.w < 2340
    lx, ly = disp.to_logical(disp.dest.x + disp.dest.w / 2, disp.dest.y + disp.dest.h / 2)
    assert lx == pytest.approx(S.SCREEN_W / 2, abs=2)
    assert ly == pytest.approx(S.SCREEN_H / 2, abs=2)

    tablet = pygame.Surface((2560, 1600))  # 16:10
    disp.window = tablet
    disp.relayout()
    assert disp.dest.w <= 2560
    assert disp.dest.h <= 1600
    assert abs(disp.dest.w / disp.dest.h - S.SCREEN_W / S.SCREEN_H) < 0.02


def test_overlay_jump_pulses_when_ready():
    from mobile.overlay import TouchOverlay
    from types import SimpleNamespace
    from core.state_manager import GameState

    class _States:
        state = GameState.FLIGHT

    game = SimpleNamespace(
        _effective_state=lambda: GameState.FLIGHT,
        states=_States(),
        run_mgr=SimpleNamespace(jump_ready=True),
        ship=SimpleNamespace(cargo=None),
        _delivery=None,
    )
    ov = TouchOverlay()
    ov.sync(game)
    jump = next(b for b in ov.buttons if b.action == "jump")
    assert jump.enabled is True
    assert ov._down(1, jump.rect.centerx, jump.rect.centery, game) is True
    assert pygame.K_j in V.drain_pulses()


def test_open_terminal_noops_on_mobile(tmp_path):
    set_mobile(True)
    from roguelite.meta_progression import MetaProgression
    from roguelite.run_manager import RunManager
    meta = MetaProgression(save_path=tmp_path / "meta.json")
    rm = RunManager(meta)
    assert rm.open_terminal("gary") is None


def test_mobile_jump_advances_without_terminal(tmp_path):
    set_mobile(True)
    from roguelite.meta_progression import MetaProgression
    from roguelite.run_manager import RunManager
    meta = MetaProgression(save_path=tmp_path / "meta.json")
    rm = RunManager(meta)
    called = []
    rm._advance_sector = lambda: called.append("advance")
    rm._open_jump_terminal = lambda: called.append("terminal")
    rm._sector_timer = 30.0
    rm._sector_dur = 20.0
    rm._ship = None
    ev = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_j})
    rm.handle_key(ev)
    assert called == ["advance"]


def test_barge_intercept_skips_comm_on_mobile(tmp_path):
    set_mobile(True)
    from antagonists.repo_barge import RepoBarge, BargeState
    from roguelite.meta_progression import MetaProgression
    from roguelite.run_manager import RunManager
    meta = MetaProgression(save_path=tmp_path / "meta.json")
    rm = RunManager(meta)
    barge = RepoBarge(100, 100, rm)
    barge._open_comm()
    assert barge.state == BargeState.AIM


def test_shop_skipped_on_mobile(tmp_path, monkeypatch):
    set_mobile(True)
    from roguelite.meta_progression import MetaProgression
    from roguelite.run_manager import RunManager
    meta = MetaProgression(save_path=tmp_path / "meta.json")
    rm = RunManager(meta)
    loaded = []
    rm._load_next_sector = lambda: loaded.append(True)
    rm._sector_index = 1
    rm._sector_start_hull = 200
    rm._ship = None
    rm._sector_credits = 0
    rm._sector_snaps = 0
    rm._sector_slingshots = 0
    rm._run_debt_reduced = 0
    # sector 1 is a shop stop (0-based index 1 → completed_sector 1 in SHOP_SECTORS)
    rm._advance_sector()
    assert rm._shop_pending is False
    assert loaded == [True]


def test_storage_redirects_under_flag(tmp_path, monkeypatch):
    monkeypatch.setenv("DEAD_DRIFT_MOBILE_STORAGE", "1")
    monkeypatch.setenv("ANDROID_PRIVATE", str(tmp_path))
    saved = (S.DATA_DIR, S.SAVES_DIR, S.MANIFEST_FILE)
    from mobile.storage import install
    try:
        root = install()
        assert root is not None
        assert Path(S.SAVES_DIR).is_dir()
        assert str(tmp_path) in S.SAVES_DIR
    finally:
        S.DATA_DIR, S.SAVES_DIR, S.MANIFEST_FILE = saved


def test_buildozer_spec_is_android_landscape():
    spec = Path("buildozer.spec").read_text(encoding="utf-8")
    req = next(line for line in spec.splitlines() if line.startswith("requirements"))
    assert "pygame-ce" in req
    assert "nltk" not in req
    assert "orientation = landscape" in spec
    assert "org.chrisdewitt" in spec
    assert "arm64-v8a" in spec
