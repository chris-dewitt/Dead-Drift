from enum import Enum, auto


class GameState(Enum):
    MAIN_MENU      = auto()
    LOADOUT_DRAFT  = auto()
    FLIGHT         = auto()
    TERMINAL       = auto()   # NLP interrogation
    DECANTING      = auto()   # clone-vat death screen
    SECTOR_JUMP    = auto()   # transition between sectors
    GAME_OVER      = auto()   # debt cleared or permanent death


class StateManager:
    def __init__(self):
        self._state   = GameState.MAIN_MENU
        self._history = []

    @property
    def state(self) -> GameState:
        return self._state

    def transition(self, new_state: GameState):
        self._history.append(self._state)
        self._state = new_state

    def back(self):
        if self._history:
            self._state = self._history.pop()

    def is_flight(self)    -> bool: return self._state == GameState.FLIGHT
    def is_terminal(self)  -> bool: return self._state == GameState.TERMINAL
    def is_decanting(self) -> bool: return self._state == GameState.DECANTING
