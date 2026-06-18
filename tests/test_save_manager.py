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


def test_chapter_display_uses_six_chapter_campaign(save_env):
    mgr = SaveManager()
    path = mgr.create_fresh_save(1)
    data = json.loads(path.read_text(encoding="utf-8"))
    data["chapters_completed"] = [1, 2, 3, 4]
    path.write_text(json.dumps(data), encoding="utf-8")

    assert mgr.slot_info(1).chapter_display == "Ch.5  (4/6 done)"


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
