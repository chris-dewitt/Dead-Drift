from __future__ import annotations
import json
import os
from pathlib import Path
from config import settings as S


def _atomic_json_dump(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


class VocabularyVault:
    """
    Persistent NLP knowledge base — Bax's core memory.

    Survives ship destruction.  Grows across runs as the player discovers
    new NPC exploits and dialogue paths.

    Structure:
    {
      "terms":     ["word", ...],        # unlocked vocabulary
      "backdoors": {"npc_type": ["..."]} # known exploit phrases per NPC
    }
    """

    def __init__(self):
        self._data: dict = {"terms": [], "backdoors": {}}
        self.load()

    # ------------------------------------------------------------------
    def load(self):
        if not os.path.exists(S.BAX_VOCAB_FILE):
            return
        try:
            with open(S.BAX_VOCAB_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
        except (json.JSONDecodeError, OSError, TypeError):
            # Same truncate-on-write hole as campaign slots: a killed save
            # must not prevent Game() from constructing Bax.
            return
        if isinstance(loaded, dict):
            terms = loaded.get("terms", [])
            backdoors = loaded.get("backdoors", {})
            self._data = {
                "terms": terms if isinstance(terms, list) else [],
                "backdoors": backdoors if isinstance(backdoors, dict) else {},
            }

    def save(self):
        _atomic_json_dump(Path(S.BAX_VOCAB_FILE), self._data)

    # ------------------------------------------------------------------
    def add_term(self, word: str):
        if word not in self._data["terms"]:
            self._data["terms"].append(word)
            self.save()

    def add_terms(self, words: list[str]):
        for w in words:
            self.add_term(w)

    def add_backdoor(self, npc_type: str, phrase: str):
        if npc_type not in self._data["backdoors"]:
            self._data["backdoors"][npc_type] = []
        if phrase not in self._data["backdoors"][npc_type]:
            self._data["backdoors"][npc_type].append(phrase)
            self.save()

    def record(self, npc_type: str, phrase: str):
        """Compatibility alias for NPCs that record discovered paths directly."""
        self.add_backdoor(npc_type, phrase)

    # ------------------------------------------------------------------
    def get_all_terms(self) -> list[str]:
        return list(self._data["terms"])

    def get_backdoors(self, npc_type: str) -> list[str]:
        return list(self._data["backdoors"].get(npc_type, []))

    def has_term(self, word: str) -> bool:
        return word in self._data["terms"]

    def unlock_chapter_vocab(self, chapter: int):
        """Seed vocabulary from a completed chapter's exploits."""
        chapter_words = {
            1: ["melancholy", "feelings", "management", "blevins", "overtime", "article"],
            2: ["permanence", "spores", "hallucinate", "invert", "perception"],
            3: ["audit", "contract", "clause", "null", "legal", "paradox", "void"],
            4: ["schrodinger", "superposition", "collapse", "observer", "quantum",
                "undefined", "exist", "manifest"],
        }
        self.add_terms(chapter_words.get(chapter, []))
