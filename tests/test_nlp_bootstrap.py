"""Coverage for the lazy NLTK bootstrap (Epic 1.10)."""
from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import time


def test_bootstrap_module_has_required_api():
    from terminal import nlp_bootstrap
    for name in ("is_ready", "start_in_background", "progress_label",
                 "packages_remaining", "already_present", "reset_for_tests"):
        assert hasattr(nlp_bootstrap, name), f"missing {name}"


def test_already_present_returns_bool():
    from terminal import nlp_bootstrap
    val = nlp_bootstrap.already_present()
    assert isinstance(val, bool)


def test_progress_label_starts_initialising():
    from terminal import nlp_bootstrap
    nlp_bootstrap.reset_for_tests()
    assert "INITIAL" in nlp_bootstrap.progress_label() \
        or "FETCH" in nlp_bootstrap.progress_label() \
        or "READY" in nlp_bootstrap.progress_label()


def test_start_in_background_is_idempotent():
    """Calling twice does not spawn a second worker thread."""
    from terminal import nlp_bootstrap
    nlp_bootstrap.reset_for_tests()
    nlp_bootstrap.start_in_background()
    first = nlp_bootstrap._thread
    nlp_bootstrap.start_in_background()
    second = nlp_bootstrap._thread
    assert first is second
    # Wait briefly so the daemon thread can complete (it calls nltk.download
    # in this test environment which is already downloaded).
    if first is not None:
        first.join(timeout=15)
    assert nlp_bootstrap.is_ready() is True
    assert nlp_bootstrap.packages_remaining() == 0
    assert nlp_bootstrap.progress_label() == "READY"


def test_main_module_no_longer_eagerly_bootstraps():
    """`main.py` must not block on NLTK at import time anymore."""
    from pathlib import Path
    src = Path("main.py").read_text(encoding="utf-8")
    assert "_bootstrap_nltk" not in src, \
        "main.py should not eagerly call _bootstrap_nltk anymore"
    # And the bootstrap module is referenced from Game (or main) so the
    # background download fires once pygame is up.
    game_src = Path("core/game.py").read_text(encoding="utf-8")
    assert "nlp_bootstrap" in game_src, \
        "Game must hand off NLTK download to the lazy bootstrap"


def test_game_renders_splash_helper_exists():
    """The splash overlay method is wired into the terminal render path."""
    from pathlib import Path
    src = Path("core/game.py").read_text(encoding="utf-8")
    assert "_maybe_render_nlp_splash" in src
    assert "LINGUISTIC PROCESSOR INITIALISING" in src
    assert "comms array's still warmin'" in src
