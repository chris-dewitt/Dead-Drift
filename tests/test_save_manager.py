"""Tests for multi-slot campaign saves."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from config import settings as S
from roguelite.save_manager import SaveManager


@pytest.fixture
def save_env(tmp_path, monkeypatch):
    saves = tmp_path / "saves"
    monkeypatch.setattr(S, "SAVES_DIR", str(saves))
    monkeypatch.setattr(S, "MANIFEST_FILE", str(saves / "manifest.json"))
    monkeypatch.setattr(S, "RUN_HISTORY_FILE", str(tmp_path / "run_history.json"))
    monkeypatch.setattr(S, "MAX_SAVE_SLOTS", 3)
    return saves


def test_create_fresh_save_empty_chapters(save_env):
    mgr = SaveManager()
    path = mgr.create_fresh_save(2)
    assert path.is_file()
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    assert data["chapters_completed"] == []
    assert data["debt"] == 350000
    info = mgr.slot_info(2)
    assert info.exists
    assert info.chapters_completed == []
    assert mgr.active_slot_id == 2


def test_set_active_and_list_slots(save_env):
    mgr = SaveManager()
    mgr.create_fresh_save(1)
    mgr.create_fresh_save(3)
    mgr.set_active(3)
    assert mgr.active_slot_id == 3
    slots = {s.slot_id: s.exists for s in mgr.list_slots()}
    assert slots == {1: True, 2: False, 3: True}


def test_resume_of_truncated_checkpoint_does_not_start_a_new_run(save_env):
    """RESUME on a half-written slot_XX_run.json must not delete it.

    `_begin_run_from_menu` unlinks the checkpoint. That is correct when
    the player asks for a new run, and it used to also run when RESUME
    could not parse the snapshot.
    """
    from core.game import Game

    mgr = SaveManager()
    mgr.create_fresh_save(1)
    ckpt = mgr.run_checkpoint_path(1)
    ckpt.write_text("{not json", encoding="utf-8")
    started: list[str] = []

    class _Host:
        save_mgr = mgr

        def _bind_meta_from_active_slot(self):
            return None

        def _begin_run_from_menu(self):
            started.append("new")

        def _goto(self, state):
            started.append(str(state))

    Game._continue_from_menu(_Host())
    assert started == []
    assert ckpt.read_text(encoding="utf-8") == "{not json"


def test_continue_without_checkpoint_still_starts_a_run(save_env):
    from core.game import Game

    mgr = SaveManager()
    mgr.create_fresh_save(1)
    started: list[str] = []

    class _Host:
        save_mgr = mgr

        def _bind_meta_from_active_slot(self):
            return None

        def _begin_run_from_menu(self):
            started.append("new")

        def _goto(self, state):
            started.append(str(state))

    Game._continue_from_menu(_Host())
    assert started == ["new"]


def test_delete_run_checkpoint(save_env):
    mgr = SaveManager()
    mgr.create_fresh_save(1)
    ckpt = mgr.run_checkpoint_path(1)
    ckpt.write_text("{}", encoding="utf-8")
    assert mgr.has_run_checkpoint(1)
    mgr.delete_run_checkpoint(1)
    assert not mgr.has_run_checkpoint(1)
    assert not ckpt.is_file()


def test_migrate_legacy_run_history(save_env, monkeypatch):
    legacy = Path(S.RUN_HISTORY_FILE)
    legacy.parent.mkdir(parents=True, exist_ok=True)
    legacy.write_text(
        json.dumps({"debt": 999, "clone_count": 5, "chapters_completed": [1]}),
        encoding="utf-8",
    )
    mgr = SaveManager()
    slot1 = save_env / "slot_01.json"
    assert slot1.is_file()
    with open(slot1, encoding="utf-8") as f:
        data = json.load(f)
    assert data["debt"] == 999
    assert data["chapters_completed"] == [1]
