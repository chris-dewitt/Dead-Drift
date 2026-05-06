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
from antagonists.repo_barge import RepoBarge


class _DemoSector:
    """Minimal stand-in for a SectorLayout — only what VectorRenderer needs."""
    def __init__(self, gravity: ThreeBodySystem):
        self.gravity = gravity


class _DemoRunMgr:
    """Minimal stand-in for RunManager — exposes .sector, .barges, ._ship."""
    def __init__(self, gravity: ThreeBodySystem, ship: PlayerShip):
        self.sector = _DemoSector(gravity)
        self.barges: list[RepoBarge] = []
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

    print("[demo] Dead Drift flight demo running. Fly safe out there, courier.")

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
        gravity.apply_all(ship.body)            # pull the ship
        ship.update(dt)                          # input + integrate
        for barge in run_mgr.barges[:]:
            barge.update(dt)
            if barge.is_destroyed:
                run_mgr.barges.remove(barge)
        hud.update(dt)

        # Gravity well collision = instant heavy damage
        well = gravity.check_collisions(ship.body)
        if well is not None and ship.is_alive:
            ship.take_damage(35.0)
            # Bounce away so we don't stick
            push = (ship.body.pos - well.pos).normalized() * 250.0
            ship.body.apply_impulse(push)

        # --- render ---
        screen.fill(S.VOID)
        vec_renderer.draw(run_mgr, ship)
        hud.draw(screen)
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
