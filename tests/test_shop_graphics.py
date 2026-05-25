"""Smoke coverage for black market shop rendering."""
from __future__ import annotations

from types import SimpleNamespace

import pygame


def _has_non_black_pixel(surface: pygame.Surface) -> bool:
    w, h = surface.get_size()
    for x in range(w):
        for y in range(h):
            if surface.get_at((x, y))[:3] != (0, 0, 0):
                return True
    return False


def test_shop_item_icons_render_for_each_stock_tag():
    from roguelite.shop import _POOL_ALL, _TAG_COL, _draw_item_icon

    pygame.font.init()
    for item in _POOL_ALL:
        surface = pygame.Surface((56, 56))
        rect = pygame.Rect(6, 6, 44, 44)
        _draw_item_icon(surface, rect, item.tag, _TAG_COL[item.tag], 1.0)
        assert _has_non_black_pixel(surface)


def test_shop_browse_screen_renders_polished_market_surface():
    from config import settings as S
    from roguelite.shop import ShopScreen

    pygame.font.init()
    run_mgr = SimpleNamespace(
        _run_debt_reduced=2400,
        _run_tether_hits=0,
        _sector_index=0,
        sector_num=2,
        meta=SimpleNamespace(add_debt=lambda amount: None, debt=42000),
    )
    ship = SimpleNamespace(hull=S.HULL_MAX, cargo=None)
    shop = ShopScreen(run_mgr, ship)
    shop._phase = "browse"

    screen = pygame.Surface((S.SCREEN_W, S.SCREEN_H))
    shop.draw(screen, 1.0)

    assert screen.get_at((S.SCREEN_W // 2 - 360, 222))[:3] != (0, 0, 0)
