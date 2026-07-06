"""Coverage for the font-caching helper (Epic 1.2)."""
from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame


def test_get_font_returns_same_instance_for_same_args():
    pygame.font.init()
    from core.text import get_font
    a = get_font(14)
    b = get_font(14)
    assert a is b, "get_font must return the cached instance"


def test_get_font_distinguishes_bold_and_italic():
    pygame.font.init()
    from core.text import get_font
    base = get_font(12)
    bold = get_font(12, bold=True)
    ital = get_font(12, italic=True)
    bold_ital = get_font(12, bold=True, italic=True)
    assert base is not bold
    assert base is not ital
    assert bold is not bold_ital


def test_get_font_supports_italic_set_after_creation():
    """Italic flag must round-trip through set_italic so renders look italic."""
    pygame.font.init()
    from core.text import get_font
    f = get_font(14, italic=True)
    assert f.get_italic() is True


def test_install_font_patch_is_idempotent_and_routes_monospace():
    pygame.font.init()
    from core.text import install_font_patch, get_font
    install_font_patch()
    install_font_patch()  # no-op
    cached = get_font(13)
    via_sysfont = pygame.font.SysFont("monospace", 13)
    assert via_sysfont is cached, \
        "Patched SysFont must dispatch monospace requests through get_font"


def test_no_raw_sysfont_calls_in_hot_paths():
    """Sweep the directly-touched per-frame draw modules.

    These are the hot paths from Epic 1.2: cockpit, HUD, vector/sci-fi
    renderers, terminal, npc portraits, delivery sequence + corridor
    framework. They should now use get_font. (The old platformer/obstacles
    modules were deleted in Delivery v2 I.1.5.)
    """
    from pathlib import Path
    targets = [
        "renderer/cockpit_renderer.py",
        "ship/hud.py",
        "renderer/vector_renderer.py",
        "renderer/sci_fi_ui.py",
        "terminal/terminal.py",
        "terminal/npc_portraits.py",
        "delivery/delivery_sequence.py",
        "delivery/corridor/base.py",
        "delivery/corridor/elements.py",
        "roguelite/loadout_draft.py",
    ]
    bad = []
    for fp in targets:
        src = Path(fp).read_text(encoding="utf-8")
        # The comment in core/game.py is fine, but no module in this
        # whitelist should call SysFont as code anymore.
        for line in src.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if "pygame.font.SysFont" in line:
                bad.append((fp, stripped))
    assert not bad, \
        "raw pygame.font.SysFont call(s) remain:\n" + \
        "\n".join(f"  {fp}: {line}" for fp, line in bad)
