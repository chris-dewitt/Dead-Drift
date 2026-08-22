"""Writable paths on Android (app-private) vs desktop (repo cwd)."""
from __future__ import annotations

import os
from pathlib import Path

from config import settings as S

from mobile.mode import is_android, is_mobile


def writable_root() -> Path:
    for key in ("ANDROID_PRIVATE",):
        raw = os.environ.get(key)
        if raw:
            return Path(raw)
    try:
        from android.storage import app_storage_path  # type: ignore
        return Path(app_storage_path())
    except Exception:
        pass
    try:
        import pygame
        pref = pygame.system.get_pref_path("ChrisDewitt", "DeadDrift")
        if pref:
            return Path(pref)
    except Exception:
        pass
    return Path.cwd()


def install() -> Path | None:
    """Redirect settings + save dirs onto a writable root. No-op on desktop."""
    if not is_mobile() and not os.environ.get("DEAD_DRIFT_MOBILE_STORAGE"):
        return None
    if not is_android() and not os.environ.get("DEAD_DRIFT_MOBILE_STORAGE"):
        return None
    root = writable_root() / "data"
    saves = root / "saves"
    root.mkdir(parents=True, exist_ok=True)
    saves.mkdir(parents=True, exist_ok=True)
    S.DATA_DIR = str(root)
    S.SAVES_DIR = str(saves)
    S.MANIFEST_FILE = str(saves / "manifest.json")
    S.BAX_VOCAB_FILE = str(root / "bax_vocabulary.json")
    S.REPO_LEDGER_FILE = str(root / "repo_ledger.json")
    S.RUN_HISTORY_FILE = str(root / "run_history.json")
    from core import settings_store
    settings_store.set_path(root / "settings.json")
    return root
