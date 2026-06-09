"""Regression coverage for recent high-severity gameplay fixes."""

from __future__ import annotations

from unittest.mock import MagicMock

import pygame

from cargo.encrypted_drive import EncryptedDrive
from config import settings as S
from core.state_manager import GameState
from physics.body import Vec2
from roguelite.meta_progression import MetaProgression
from roguelite.run_checkpoint import build_checkpoint, restore_checkpoint
from roguelite.run_manager import RunManager
from ship.gun import Bullet
from ship.ship import PlayerShip


def _game_stub(run_mgr, ship):
    game = MagicMock()
    game.run_mgr = run_mgr
    game.ship = ship
    game.states = MagicMock(state=GameState.FLIGHT)
    game._state_before_pause = None
    return game


def test_chapter_five_and_six_loadout_render_without_crash():
    pygame.init()
    pygame.font.init()

    from roguelite.loadout_draft import LoadoutDraft

    surface = pygame.Surface((S.SCREEN_W, S.SCREEN_H))
    for chapter in (5, 6):
        LoadoutDraft(chapter=chapter).render(surface)


def test_compliance_vessel_destroy_event_does_not_crash(tmp_path):
    from antagonists.compliance_vessel import ComplianceVessel

    meta = MetaProgression(save_path=tmp_path / "meta.json")
    rm = RunManager(meta)
    cv = ComplianceVessel(0, 0, rm)

    cv.take_hit(cv.HULL_HITS)

    assert not cv.alive


def test_checkpoint_preserves_encrypted_drive_fuel_and_gun_upgrades(tmp_path):
    meta = MetaProgression(save_path=tmp_path / "meta.json")
    ship = PlayerShip()
    rm = RunManager(meta)
    rm.start_run(ship)
    rm.apply_draft(ship)

    drive = EncryptedDrive()
    drive.trace_level = 0.75
    drive._ping_t = 8.5
    ship.cargo = drive
    ship.fuel = 42.0
    ship.gun.fire_rate_mult = 2.0
    ship.gun.damage_mult = 2
    ship.gun.bullets.append(Bullet(Vec2(12, 34), 15, damage=2))

    data = build_checkpoint(_game_stub(rm, ship))

    restored_ship = PlayerShip()
    restored_rm = RunManager(meta)
    assert restore_checkpoint(_game_stub(restored_rm, restored_ship), data)

    assert isinstance(restored_ship.cargo, EncryptedDrive)
    assert restored_ship.cargo.trace_level == 0.75
    assert restored_ship.cargo._ping_t == 8.5
    assert restored_ship.fuel == 42.0
    assert restored_ship.gun.fire_rate_mult == 2.0
    assert restored_ship.gun.damage_mult == 2
    assert restored_ship.gun.bullets[0].damage == 2


def test_interactive_wreck_salvage_pays_down_meta_debt(tmp_path):
    class TriggeredWreck:
        SUBTYPE_INTERACTIVE = "interactive"

        def __init__(self):
            self.subtype = self.SUBTYPE_INTERACTIVE
            self.is_triggered = False
            self.pos = Vec2(100, 100)
            self.length = 20
            self.weak_hp = 1

        def hit_weak_point(self, _pos):
            self.is_triggered = True
            self.weak_hp = 0
            return True

    meta = MetaProgression(save_path=tmp_path / "meta.json")
    ship = PlayerShip()
    ship.gun.bullets.append(Bullet(Vec2(100, 100), 0))
    rm = RunManager(meta)
    rm._ship = ship
    rm._wrecks = [TriggeredWreck()]

    debt_before = meta.debt
    rm._check_bullets()

    assert meta.debt == debt_before - 1200
    assert rm._run_debt_reduced == 1200
    assert rm._sector_credits == 1200
