"""Multi-slot save files for campaign progress (meta / chapters / debt)."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from config import settings as S


@dataclass(frozen=True)
class SaveSlotInfo:
    slot_id: int
    label: str
    path: Path
    exists: bool
    updated_at: str | None
    chapters_completed: list[int]
    debt: int
    clone_count: int

    @property
    def chapter_display(self) -> str:
        if not self.chapters_completed:
            return "Ch.1 (new)"
        nxt = 1
        for ch in (1, 2, 3, 4, 5, 6):
            if ch not in self.chapters_completed:
                nxt = ch
                break
        else:
            nxt = 6
        return f"Ch.{nxt}  ({len(self.chapters_completed)}/6 done)"


class SaveManager:
    """
    Manages up to MAX_SAVE_SLOTS campaign files under data/saves/.

    Each slot is a JSON file compatible with MetaProgression._DEFAULTS keys.
    """

    def __init__(self) -> None:
        self._dir = Path(S.SAVES_DIR)
        self._manifest_path = Path(S.MANIFEST_FILE)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._manifest: dict = self._load_manifest()
        self._migrate_legacy_single_save()

    # ------------------------------------------------------------------
    def _load_manifest(self) -> dict:
        default = {
            "active_slot": 1,
            "slots": {
                str(i): {"label": f"SAVE {i}", "updated_at": None}
                for i in range(1, S.MAX_SAVE_SLOTS + 1)
            },
        }
        if not self._manifest_path.is_file():
            return default
        try:
            with open(self._manifest_path, encoding="utf-8") as f:
                data = json.load(f)
            return {**default, **data}
        except (json.JSONDecodeError, OSError):
            return default

    def _write_manifest(self) -> None:
        self._manifest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._manifest_path, "w", encoding="utf-8") as f:
            json.dump(self._manifest, f, indent=2)

    def _slot_path(self, slot_id: int) -> Path:
        return self._dir / f"slot_{slot_id:02d}.json"

    def _migrate_legacy_single_save(self) -> None:
        legacy = Path(S.RUN_HISTORY_FILE)
        if not legacy.is_file():
            return
        slot1 = self._slot_path(1)
        if slot1.is_file():
            return
        try:
            data = legacy.read_text(encoding="utf-8")
            slot1.write_text(data, encoding="utf-8")
            self._manifest["active_slot"] = 1
            self._manifest["slots"]["1"]["label"] = "IMPORTED"
            self._manifest["slots"]["1"]["updated_at"] = datetime.now(tz=UTC).isoformat()
            self._write_manifest()
        except OSError:
            pass

    # ------------------------------------------------------------------
    @property
    def active_slot_id(self) -> int:
        return int(self._manifest.get("active_slot", 1))

    def active_save_path(self) -> Path:
        return self._slot_path(self.active_slot_id)

    def set_active(self, slot_id: int) -> None:
        if slot_id < 1 or slot_id > S.MAX_SAVE_SLOTS:
            raise ValueError(f"Invalid slot {slot_id}")
        self._manifest["active_slot"] = slot_id
        self._write_manifest()

    def list_slots(self) -> list[SaveSlotInfo]:
        out: list[SaveSlotInfo] = []
        slots_meta = self._manifest.get("slots", {})
        for sid in range(1, S.MAX_SAVE_SLOTS + 1):
            path = self._slot_path(sid)
            sm = slots_meta.get(str(sid), {})
            label = str(sm.get("label") or f"SAVE {sid}")
            updated = sm.get("updated_at")
            if path.is_file():
                try:
                    with open(path, encoding="utf-8") as f:
                        data = json.load(f)
                except (json.JSONDecodeError, OSError):
                    data = {}
                out.append(SaveSlotInfo(
                    slot_id=sid,
                    label=label,
                    path=path,
                    exists=True,
                    updated_at=updated,
                    chapters_completed=list(data.get("chapters_completed", [])),
                    debt=int(data.get("debt", 0)),
                    clone_count=int(data.get("clone_count", 1)),
                ))
            else:
                out.append(SaveSlotInfo(
                    slot_id=sid,
                    label=label,
                    path=path,
                    exists=False,
                    updated_at=None,
                    chapters_completed=[],
                    debt=0,
                    clone_count=1,
                ))
        return out

    def slot_info(self, slot_id: int) -> SaveSlotInfo:
        for s in self.list_slots():
            if s.slot_id == slot_id:
                return s
        raise ValueError(slot_id)

    def create_fresh_save(self, slot_id: int, *, label: str | None = None) -> Path:
        """Overwrite slot with brand-new campaign defaults."""
        from roguelite.meta_progression import MetaProgression

        path = self._slot_path(slot_id)
        meta = MetaProgression(save_path=path)
        meta.reset_to_defaults()
        meta.save()
        self.delete_run_checkpoint(slot_id)
        slots = self._manifest.setdefault("slots", {})
        ent = slots.setdefault(str(slot_id), {})
        ent["label"] = label or f"SAVE {slot_id}"
        ent["updated_at"] = datetime.now(tz=UTC).isoformat()
        self._manifest["active_slot"] = slot_id
        self._write_manifest()
        return path

    def delete_slot(self, slot_id: int) -> None:
        path = self._slot_path(slot_id)
        if path.is_file():
            path.unlink()
        slots = self._manifest.setdefault("slots", {})
        ent = slots.setdefault(str(slot_id), {})
        ent["updated_at"] = None

    def sync_active(self, meta) -> None:
        """Refresh manifest summary after meta.save()."""
        sid = self.active_slot_id
        slots = self._manifest.setdefault("slots", {})
        ent = slots.setdefault(str(sid), {"label": f"SAVE {sid}"})
        ent["updated_at"] = datetime.now(tz=UTC).isoformat()
        if not ent.get("label"):
            ent["label"] = f"SAVE {sid}"
        self._write_manifest()

    def rename_active(self, label: str) -> None:
        sid = self.active_slot_id
        slots = self._manifest.setdefault("slots", {})
        ent = slots.setdefault(str(sid), {})
        ent["label"] = label.strip() or f"SAVE {sid}"
        self._write_manifest()

    # ------------------------------------------------------------------
    # In-run checkpoint (mid-sector progress)
    def run_checkpoint_path(self, slot_id: int | None = None) -> Path:
        sid = slot_id if slot_id is not None else self.active_slot_id
        return self._dir / f"slot_{sid:02d}_run.json"

    def has_run_checkpoint(self, slot_id: int | None = None) -> bool:
        return self.run_checkpoint_path(slot_id).is_file()

    def delete_run_checkpoint(self, slot_id: int | None = None) -> None:
        path = self.run_checkpoint_path(slot_id)
        if path.is_file():
            path.unlink()

    def save_run_checkpoint(self, game) -> None:
        from roguelite.run_checkpoint import save_checkpoint_file
        save_checkpoint_file(self.run_checkpoint_path(), game)

    def load_run_checkpoint(self, game) -> bool:
        from roguelite.run_checkpoint import load_checkpoint_file, restore_checkpoint
        data = load_checkpoint_file(self.run_checkpoint_path())
        if not data:
            return False
        return restore_checkpoint(game, data)
