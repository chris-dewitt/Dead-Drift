#!/usr/bin/env python3
"""
DEAD DRIFT - Minimal Flight Demo

Boots in seconds. No NLTK, no state machine, no roguelite loop.
Just pure flight physics so you can feel the inertia.

Controls:
  W / UP        : thrust forward
  S / DOWN      : reverse thrust (40%)
  A / LEFT      : rotate counter-clockwise
  D / RIGHT     : rotate clockwise
  N             : spawn a Repo Barge (tests tether mechanic)
  R             : reset ship to center
  ESC / Q       : quit

Tip: build up speed near a gravity well, cut thrust, and slingshot.
That's the feel we're going for.
"""
import os
import sys
import pygame

# Ensure local imports work no matter where you run this from
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from config import settings as S
from physics.body import RigidBody2D, Vec2
from physics.gravity import GravityWell, ThreeBodySystem
from ship.ship import PlayerShip
from ship.hud import HUD
from renderer.vector_renderer import VectorRenderer
from renderer.cockpit_renderer import CockpitRenderer
from antagonists.repo_barge import RepoBarge
from antagonists.debris import DebrisRock
from antagonists.fuel_canister import FuelCanister
from bax.bax import Bax
from roguelite.meta_progression import MetaProgression


class _DemoSector:
    """Minimal stand-in for a SectorLayout — only what VectorRenderer needs."""
    def __init__(self, gravity: ThreeBodySystem):
        self.gravity = gravity


class _DemoRunMgr:
    """Minimal stand-in for RunManager — exposes .sector, .barges, ._ship."""
    def __init__(self, gravity: ThreeBodySystem, ship: PlayerShip):
        self.sector      = _DemoSector(gravity)
        self.sector_num  = 1   # cockpit HUD expects this
        self.barges:    list[RepoBarge]    = []
        self.debris:    list[DebrisRock]   = [DebrisRock() for _ in range(S.DEBRIS_COUNT)]
        self.canisters: list[FuelCanister] = [FuelCanister() for _ in range(S.CANISTER_COUNT)]
        self._ship = ship


def _spawn_barge(run_mgr: _DemoRunMgr):
    """Drop a barge at a random screen edge."""
    import random
    side = random.choice(["left", "right", "top", "bottom"])
    x = {"left": 40, "right": S.SCREEN_W - 40}.get(side, random.randint(80, S.SCREEN_W - 80))
    y = {"top": 40, "bottom": S.SCREEN_H - 40}.get(side, random.randint(80, S.SCREEN_H - 80))
    run_mgr.barges.append(RepoBarge(x, y, run_mgr))
    print(f"[demo] barge spawned at ({x}, {y})")


def _draw_help(surface, font):
    lines = [
        "WASD/Arrows: fly  |  N: spawn barge  |  R: reset  |  ESC: quit",
    ]
    for i, line in enumerate(lines):
        surf = font.render(line, True, S.GREY_DEAD)
        surface.blit(surf, (20, S.SCREEN_H - 28 - i * 18))


def main():
    pygame.init()
    from core.text import install_font_patch
    install_font_patch()
    pygame.display.set_caption(f"{S.TITLE} - Flight Demo")
    screen = pygame.display.set_mode((S.SCREEN_W, S.SCREEN_H))
    clock  = pygame.time.Clock()
    font   = pygame.font.SysFont("monospace", 14)

    # Build the world
    ship    = PlayerShip()
    gravity = ThreeBodySystem()
    gravity.add(GravityWell(S.SCREEN_W * 0.65, S.SCREEN_H * 0.55, mass=4500.0, radius=55))
    gravity.add(GravityWell(S.SCREEN_W * 0.25, S.SCREEN_H * 0.30, mass=2200.0, radius=35))

    run_mgr      = _DemoRunMgr(gravity, ship)
    vec_renderer = VectorRenderer(screen)
    hud          = HUD(ship)
    meta         = MetaProgression()
    bax          = Bax(ship, meta)
    cockpit      = CockpitRenderer(screen, ship=ship, run_mgr=run_mgr, meta=meta)

    print("[demo] Dead Drift flight demo running. Fly safe out there, courier.")

    _well_hit_times: dict = {}   # per-well last-damage timestamps
    running = True
    while running:
        dt = clock.tick(S.FPS) / 1000.0

        # --- events ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_q):
                    running = False
                elif event.key == pygame.K_n:
                    _spawn_barge(run_mgr)
                elif event.key == pygame.K_r:
                    ship.reset()
                    print("[demo] ship reset")

        # --- update ---
        gravity.apply_all(ship.body)
        ship.update(dt)
        for barge in run_mgr.barges[:]:
            barge.update(dt)
            if barge.is_destroyed:
                run_mgr.barges.remove(barge)
        for rock in run_mgr.debris:
            rock.update(dt)
            if rock.collides(ship.pos) and rock.can_damage_ship():
                ship.take_damage(S.DEBRIS_DAMAGE)
                rock.register_ship_hit()
                rock.hit()
        for can in run_mgr.canisters:
            can.update(dt, ship.pos)
        hud.update(dt)
        bax.update(dt)
        cockpit.update(dt)

        # Gravity well core collision — 15 hull once per second per well
        well = gravity.check_collisions(ship.body)
        if well is not None and ship.is_alive:
            well_id = id(well)
            now     = pygame.time.get_ticks() / 1000.0
            if now - _well_hit_times.get(well_id, -999) > 1.0:
                ship.take_damage(15.0)
                _well_hit_times[well_id] = now
            # Bounce away from core so we don't get stuck inside
            push = (ship.body.pos - well.pos).normalized() * 200.0
            ship.body.apply_impulse(push)

        # --- render ---
        screen.fill(S.VOID)
        vec_renderer.draw(run_mgr, ship, dt)
        hud.draw(screen)
        cockpit.draw(pygame.time.get_ticks() / 1000.0)
        _draw_help(screen, font)

        # Show "DESTROYED" overlay if hull is gone
        if not ship.is_alive:
            big = pygame.font.SysFont("monospace", 32, bold=True)
            msg = big.render("HULL BREACH - press R to reset", True, S.RED_WARN)
            screen.blit(msg, (S.SCREEN_W // 2 - msg.get_width() // 2, S.SCREEN_H // 2))

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
