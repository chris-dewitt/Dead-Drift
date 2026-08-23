"""Dead Drift Android slice — touch input, letterbox display, store wrap."""

from mobile.mode import activate_if_needed, is_android, is_mobile, set_mobile
from mobile.storage import install as install_storage

__all__ = [
    "activate_if_needed",
    "is_android",
    "is_mobile",
    "set_mobile",
    "install_storage",
]
