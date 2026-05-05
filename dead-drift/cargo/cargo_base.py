from __future__ import annotations
from abc import ABC, abstractmethod


class BaseCargo(ABC):
    def __init__(self, name: str, integrity: float = 100.0):
        self.name      = name
        self.integrity = integrity
        self.is_damaged = False

    def take_damage(self, amount: float):
        self.integrity = max(0.0, self.integrity - amount)
        if self.integrity < 70.0:
            self.is_damaged = True
            self._on_damage()

    @abstractmethod
    def _on_damage(self):
        """Apply cargo-specific system effects when damaged."""
        ...

    @abstractmethod
    def terminal_climax(self) -> str:
        """Return the NPC type string for the chapter's terminal showdown."""
        ...

    def __str__(self) -> str:
        return self.name
