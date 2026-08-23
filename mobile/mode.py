"""Mobile slice detection and feature flags.

Android builds always run the cut-down slice (flight + delivery tunnels,
no terminals). Desktop can opt in with DEAD_DRIFT_MOBILE=1 for overlay
playtesting without a device.
"""
from __future__ import annotations

import os
import sys

_forced: bool | None = None


def is_android() -> bool:
    if sys.platform == "android":
        return True
    if os.environ.get("ANDROID_ARGUMENT") or os.environ.get("ANDROID_PRIVATE"):
        return True
    try:
        import android  # noqa: F401  — python-for-android runtime
        return True
    except ImportError:
        return False


def activate_if_needed() -> bool:
    """Enable the mobile slice on Android or when explicitly requested."""
    if is_android() or os.environ.get("DEAD_DRIFT_MOBILE") == "1":
        set_mobile(True)
        return True
    return False


def set_mobile(on: bool) -> None:
    global _forced
    _forced = bool(on)
    if on:
        os.environ["DEAD_DRIFT_MOBILE"] = "1"
    else:
        os.environ.pop("DEAD_DRIFT_MOBILE", None)


def is_mobile() -> bool:
    if _forced is not None:
        return _forced
    return os.environ.get("DEAD_DRIFT_MOBILE") == "1" or is_android()


def skip_terminals() -> bool:
    """Terminals are the mobile slimdown — jump advances the sector directly."""
    return is_mobile()


def skip_shops() -> bool:
    """Mobile slice is flight + delivery tunnels only."""
    return is_mobile()
