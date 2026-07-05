"""
core/resource_path.py — asset path resolution for frozen and dev builds.

Call resource_path() for read-only assets shipped with the game (fonts,
nltk_data, etc.).  In a PyInstaller frozen build it resolves inside the
_MEIPASS temp tree; in a normal Python dev tree it resolves relative to
the repo root.

Do NOT use this for writable user data (saves, run history) — those stay
relative to the working directory so they land in a user-writable location.
"""
from __future__ import annotations
import os
import sys


def resource_path(*parts: str) -> str:
    """Return the absolute path to a bundled read-only asset.

    Handles both  sys.frozen + sys._MEIPASS  (PyInstaller --onedir /
    --onefile) and a normal Python source tree.
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base: str = sys._MEIPASS
    else:
        # Repo root is the parent of this file's directory (core/).
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, *parts)
