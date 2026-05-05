from collections import defaultdict
from typing import Callable


class EventBus:
    """Lightweight pub/sub. All game systems talk through here."""

    def __init__(self):
        self._listeners: dict[str, list[Callable]] = defaultdict(list)

    def subscribe(self, event: str, callback: Callable):
        self._listeners[event].append(callback)

    def unsubscribe(self, event: str, callback: Callable):
        self._listeners[event].remove(callback)

    def emit(self, event: str, **payload):
        for cb in self._listeners[event]:
            cb(**payload)


# Global singleton — import and use anywhere.
bus = EventBus()

# --- Canonical event names ---
EVT_HULL_DAMAGE    = "hull_damage"       # payload: amount
EVT_HULL_CRITICAL  = "hull_critical"     # payload: hp
EVT_SHIP_DESTROYED = "ship_destroyed"
EVT_TETHER_HIT     = "tether_hit"        # payload: barge
EVT_TETHER_SNAP    = "tether_snap"
EVT_MODULE_UNBOLTED = "module_unbolted"  # payload: module
EVT_CARGO_DAMAGED  = "cargo_damaged"     # payload: cargo, severity
EVT_TERMINAL_OPEN  = "terminal_open"     # payload: npc
EVT_TERMINAL_CLOSE = "terminal_close"    # payload: outcome
EVT_NLP_EXPLOIT    = "nlp_exploit"       # payload: npc, exploit_key
EVT_RUN_START      = "run_start"
EVT_RUN_END        = "run_end"           # payload: success
EVT_SECTOR_CLEAR   = "sector_clear"      # payload: sector_num
EVT_BAX_SPEAK      = "bax_speak"         # payload: line
EVT_DEBT_UPDATE    = "debt_update"       # payload: delta, total
