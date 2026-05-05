from __future__ import annotations
import json
import os
from config import settings as S


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
        if os.path.exists(S.BAX_VOCAB_FILE):
            with open(S.BAX_VOCAB_FILE, "r") as f:
                self._data = json.load(f)

    def save(self):
        os.makedirs(os.path.dirname(S.BAX_VOCAB_FILE), exist_ok=True)
        with open(S.BAX_VOCAB_FILE, "w") as f:
            json.dump(self._data, f, indent=2)

    # ------------------------------------------------------------------
    def add_term(self, word: str):
        if word not in self._data["terms"]:
            self._data["terms"].append(word)

    def add_terms(self, words: list[str]):
        for w in words:
            self.add_term(w)

    def add_backdoor(self, npc_type: str, phrase: str):
        if npc_type not in self._data["backdoors"]:
            self._data["backdoors"][npc_type] = []
        if phrase not in self._data["backdoors"][npc_type]:
            self._data["backdoors"][npc_type].append(phrase)

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
