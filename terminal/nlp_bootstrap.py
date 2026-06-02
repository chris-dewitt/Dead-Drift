"""
Lazy NLTK bootstrap — Epic 1.10 / Phase 2.

The original `main.py` blocked at startup downloading NLTK data for the
terminal NLP layer.  That meant every cold launch sat on a black screen
until the network finished, with zero in-game feedback.

This module flips that to:
  * Boot the menu instantly.  No work done synchronously at import time.
  * Kick the download off as a background thread the first time the
    game asks for it (`start_in_background()`).
  * Expose a non-blocking `is_ready()` check + `progress_label()` for
    the splash overlay.

`terminal/nlp_parser.py` already degrades gracefully when packages are
missing (regex fallback for tokenize/POS, neutral fallback for VADER),
so the terminal stays playable while the download is in flight — but
once `is_ready()` flips to True, subsequent terminals get the full
NLTK behaviour automatically because `nltk.data.find` succeeds.

Bundled-data priority (Phase 2):
  assets/nltk_data/ is prepended to nltk.data.path at import time.
  Run  tools/bundle_nltk.py  once before packaging to populate it.
  When all packages are present there, no network access is attempted.
"""
from __future__ import annotations
import os
import threading
from pathlib import Path
from typing import Iterable

from core.resource_path import resource_path

# Bundled NLTK data shipped alongside the game executable.  Populated by
# tools/bundle_nltk.py at build time; ignored by git (binary data).
_BUNDLE_DIR = Path(resource_path("assets", "nltk_data"))

# (package, data path) — same list main.py used eagerly.
_PACKAGES: tuple[tuple[str, str], ...] = (
    ("punkt_tab",                  "tokenizers/punkt_tab"),
    ("punkt",                      "tokenizers/punkt"),
    ("averaged_perceptron_tagger", "taggers/averaged_perceptron_tagger"),
    ("vader_lexicon",              "sentiment/vader_lexicon"),
)

_state_lock   = threading.Lock()
_thread:        threading.Thread | None = None
_done:          bool = False
_current_pkg:   str = ""
_packages_left: int = len(_PACKAGES)


def is_ready() -> bool:
    """True when every required package is present locally (or the bundle
    has finished downloading). Cheap to call every frame."""
    with _state_lock:
        return _done


def progress_label() -> str:
    """Human-readable label for the splash overlay. 'READY' when done."""
    with _state_lock:
        if _done:
            return "READY"
        if _current_pkg:
            return f"FETCHING  {_current_pkg.upper()}"
        return "INITIALISING LINGUISTIC PROCESSOR"


def packages_remaining() -> int:
    """Number of packages still pending. 0 when done."""
    with _state_lock:
        return _packages_left


def reset_for_tests() -> None:
    """Test helper — drop module state so the bootstrap can be re-run."""
    global _thread, _done, _current_pkg, _packages_left
    with _state_lock:
        _thread = None
        _done = False
        _current_pkg = ""
        _packages_left = len(_PACKAGES)


def start_in_background() -> None:
    """Begin the download on a daemon thread. Idempotent — safe to call
    every frame."""
    global _thread
    with _state_lock:
        if _done:
            return
        if _thread is not None and _thread.is_alive():
            return
        _thread = threading.Thread(
            target=_run_download, name="nltk-bootstrap", daemon=True)
        _thread.start()


def _ensure_bundle_path(nltk) -> None:
    """Prepend the shipped bundle dir to nltk.data.path if it exists."""
    bundle_str = str(_BUNDLE_DIR)
    if bundle_str not in nltk.data.path:
        nltk.data.path.insert(0, bundle_str)


def _run_download() -> None:
    """Worker — called on the bootstrap thread."""
    global _done, _current_pkg, _packages_left

    try:
        import nltk
    except Exception:
        # NLTK isn't installed at all. Mark done so we stop nagging — the
        # parser's regex fallback will keep the terminal functional.
        with _state_lock:
            _done = True
            _current_pkg = ""
            _packages_left = 0
        return

    _ensure_bundle_path(nltk)

    remaining = list(_PACKAGES)
    for pkg, path in _PACKAGES:
        with _state_lock:
            _current_pkg = pkg
        try:
            nltk.data.find(path)
        except LookupError:
            try:
                # Prefer downloading into the bundle dir so subsequent
                # launches also skip the network.  Falls back to the
                # default NLTK search path if the dir isn't writable.
                dl_dir = str(_BUNDLE_DIR) if _BUNDLE_DIR.exists() else None
                kwargs = {"quiet": True}
                if dl_dir:
                    kwargs["download_dir"] = dl_dir
                nltk.download(pkg, **kwargs)
            except Exception:
                # Network down / disk read-only / etc. We don't want to
                # spin forever; just move on. The parser falls back to
                # regex tokenisation when the data can't be loaded.
                pass
        with _state_lock:
            try:
                remaining.remove((pkg, path))
            except ValueError:
                pass
            _packages_left = len(remaining)

    with _state_lock:
        _done = True
        _current_pkg = ""
        _packages_left = 0


def already_present() -> bool:
    """Synchronous check — True if every package is already on disk so
    the splash can be skipped entirely."""
    try:
        import nltk
    except Exception:
        return True   # parser falls back to regex; no splash needed.
    _ensure_bundle_path(nltk)
    for _pkg, path in _PACKAGES:
        try:
            nltk.data.find(path)
        except LookupError:
            return False
        except Exception:
            return False
    return True
