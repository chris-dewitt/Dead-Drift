"""Aliveness A.9 — cockpit hull-glow tier verification.

Epic 7.1 doc claims healthy / warning / critical / panic glow tiers
shipped, but the Aliveness plan flagged it 'suspect by audit'. These
tests render Bax's portrait at each tier and verify the glow band
actually paints with the right palette."""
from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame


def _build_cockpit():
    pygame.init()
    pygame.font.init()
    from renderer.cockpit_renderer import CockpitRenderer
    from config import settings as S
    from types import SimpleNamespace
    # Match the cockpit's geometry (it uses S.SCREEN_W/SCREEN_H verbatim).
    surf = pygame.Surface((S.SCREEN_W, S.SCREEN_H))
    ship = SimpleNamespace(hull_pct=1.0,
                            hull=200, gun=SimpleNamespace(is_jammed=False,
                                                          jam_pct=0.0))
    run_mgr = SimpleNamespace(sector=None, sector_num=1)
    meta    = SimpleNamespace(debt=0, clone_count=1)
    cr = CockpitRenderer(surf, ship=ship, run_mgr=run_mgr, meta=meta)
    return cr, surf


def _sample_portrait_glow(surf):
    """Sample several pixels inside Bax's portrait area and return a
    representative (r, g, b) for the dominant glow ink. The portrait
    occupies the bottom-right corner of the screen — _PORT_X..+_PORT_W
    by STRIP_TOP..+_PORT_H. _PORT_W is 130, _PORT_H is COCKPIT_H - 6."""
    from config import settings as S
    port_x = S.SCREEN_W - 132
    port_y = S.SCREEN_H - S.COCKPIT_H + 3
    port_w = 130
    port_h = S.COCKPIT_H - 6
    samples = []
    for dx in (10, 30, 60, 100):
        for dy in (10, 30, 60):
            sx = min(S.SCREEN_W - 1, port_x + dx)
            sy = min(S.SCREEN_H - 1, port_y + dy)
            if dx >= port_w or dy >= port_h:
                continue
            r, g, b = surf.get_at((sx, sy))[:3]
            samples.append((r, g, b))
    # Pick the brightest sample by total intensity — that's the glow tint.
    samples.sort(key=lambda c: -sum(c))
    return samples[0] if samples else (0, 0, 0)


def _portrait_bg_sample(surf):
    """Sample a pixel reliably inside the portrait rect but outside any
    overlay (avoid Bax's body polygon). The portrait box is ~130x84;
    the top-left corner of the box is empty space."""
    from config import settings as S
    port_x = S.SCREEN_W - 132
    port_y = S.SCREEN_H - S.COCKPIT_H + 3
    return surf.get_at((port_x + 6, port_y + 6))[:3]


def test_healthy_glow_tier_paints_dim_amber():
    """Healthy tier (>= 60% hull) — dim warm amber.

    The glow uses (180, 80, 0) at alpha 20 over a (5, 5, 13) strip
    background, so the sampled pixel should be red-dominant but dim."""
    cr, surf = _build_cockpit()
    cr._hull_pct = 1.0
    cr._hull_flicker_t = 1.0
    surf.fill((0, 0, 0))
    cr._draw_bax(t=0.0)
    r, g, b = _portrait_bg_sample(surf)
    assert r >= g, f"healthy tier should have r >= g (got {(r, g, b)})"
    assert r > b, f"healthy tier glow should be amber-warm (got {(r, g, b)})"


def test_warning_tier_paints_orange():
    """Warning tier (30-60% hull) — orange glow visibly brighter than
    healthy. We compare two samples directly."""
    # Healthy frame.
    cr, surf = _build_cockpit()
    cr._hull_pct = 1.0
    cr._hull_flicker_t = 0.0
    cr._dmg_scan_t = 0.0
    surf.fill((0, 0, 0))
    cr._draw_bax(t=0.0)
    healthy_r = _portrait_bg_sample(surf)[0]

    # Warning frame.
    cr._hull_pct = 0.45
    surf.fill((0, 0, 0))
    cr._draw_bax(t=0.0)
    warning_r = _portrait_bg_sample(surf)[0]

    assert warning_r > healthy_r, (
        f"warning tier should paint a brighter red than healthy "
        f"(warning={warning_r} vs healthy={healthy_r})"
    )


def test_critical_tier_paints_red_with_border_tint():
    cr, surf = _build_cockpit()
    cr._hull_pct = 0.20
    cr._hull_flicker_t = 0.5
    surf.fill((0, 0, 0))
    cr._draw_bax(t=0.0)
    # Border should be the red-tinge (220, 30, 30) at hp < 0.30. The
    # border is drawn at the rect edge so sample exactly on it.
    from config import settings as S
    port_x = S.SCREEN_W - 132
    port_y = S.SCREEN_H - S.COCKPIT_H + 3
    border_r, border_g, _ = surf.get_at((port_x, port_y + 20))[:3]
    assert border_r > 100 and border_g < 80, \
        f"critical tier should paint a red border tint (got {(border_r, border_g)})"


def test_panic_tier_paints_persistent_red_flicker():
    """Panic tier (< 10% hull) — bright red glow with persistent flicker.

    The peak flicker pixel should be red-dominant and brighter than the
    critical-tier peak."""
    cr, surf = _build_cockpit()
    cr._hull_pct = 0.05

    # Find the brightest red frame across a phase sweep — flicker
    # oscillates as abs(sin(_hull_flicker_t * 18.0)), peaks at
    # _hull_flicker_t = pi / 36 ≈ 0.0873.
    panic_peak = 0
    for phase in (0.0, 0.04, 0.0873, 0.12, 0.16, 0.20, 0.25):
        cr._hull_flicker_t = phase
        surf.fill((0, 0, 0))
        cr._draw_bax(t=phase)
        r, g, b = _portrait_bg_sample(surf)
        if r > panic_peak and g < 30 and b < 30:
            panic_peak = r

    # Critical tier peak for comparison.
    cr._hull_pct = 0.20
    critical_peak = 0
    for phase in (0.0, 0.10, 0.22, 0.33, 0.45):
        cr._hull_flicker_t = phase
        surf.fill((0, 0, 0))
        cr._draw_bax(t=phase)
        r, g, b = _portrait_bg_sample(surf)
        if r > critical_peak and g < 60 and b < 60:
            critical_peak = r

    assert panic_peak > 30, (
        f"panic tier never produced visible red glow (peak r={panic_peak})"
    )
    assert panic_peak > critical_peak, (
        f"panic tier glow should be brighter than critical "
        f"(panic={panic_peak}, critical={critical_peak})"
    )


def test_hull_damage_event_arms_eye_widen_reaction():
    """The reaction state machine still wires (cooldown to 1.5s after damage)."""
    from core.event_bus import bus, EVT_HULL_DAMAGE
    cr, _ = _build_cockpit()
    cr._dmg_cd = 0.0
    bus.emit(EVT_HULL_DAMAGE, amount=10)
    assert cr._dmg_eyes_t > 0.0
    assert cr._dmg_scan_t > 0.0
    assert cr._dmg_ant_t > 0.0
    assert cr._dmg_cd > 0.0
