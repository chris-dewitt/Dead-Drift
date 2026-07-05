"""
core/settings_store.py — user preference persistence.

Stored in data/settings.json (writable, user-specific, not bundled).
Module-level state so any subsystem can read without passing references.

Keys:
    master_volume : float 0.0–1.0   (default 0.70)
    fullscreen    : bool             (default False)
"""
from __future__ import annotations

import json
from pathlib import Path

_PATH = Path("data/settings.json")

_DEFAULTS: dict = {
    "master_volume": 0.70,
    "fullscreen":    False,
}

_data: dict = {}


def load() -> None:
    """Load from disk. Safe to call multiple times."""
    global _data
    try:
        with open(_PATH, encoding="utf-8") as f:
            loaded = json.load(f)
        _data = {**_DEFAULTS, **{k: v for k, v in loaded.items() if k in _DEFAULTS}}
    except (OSError, json.JSONDecodeError):
        _data = dict(_DEFAULTS)


def save() -> None:
    """Persist current in-memory settings to disk."""
    _PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_PATH, "w", encoding="utf-8") as f:
        json.dump(_data, f, indent=2)


def get(key: str):
    """Return current value for key. Lazy-loads on first call."""
    if not _data:
        load()
    return _data.get(key, _DEFAULTS.get(key))


def set_value(key: str, value) -> None:
    """Set and immediately persist a setting."""
    if not _data:
        load()
    _data[key] = value
    save()
