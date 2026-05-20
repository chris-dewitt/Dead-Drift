from __future__ import annotations
from core.event_bus import (bus, EVT_BAX_SPEAK, EVT_RUN_START,
                             EVT_TETHER_HIT, EVT_JUMP_READY, EVT_BARGE_NEARBY)
from config import settings as S

_CONTROLS = (
    "Right — quick brief. W thrusts forward, A and D rotate. "
    "No drag in this void. Whatever speed you build, you keep. Plan your burns."
)
_JUMP_EARLY = (
    "Twenty seconds minimum per sector, then J to jump. "
    "Terminal opens, you talk your way through — or exploit their system entirely."
)
_WELL = (
    "Gravity well in range. Swing close and burn out fast enough — "
    "that's a slingshot. Cuts the jump timer. Worth a go."
)
_BARGE = (
    "When the harpoon locks on — drift SIDEWAYS. "
    "Lateral velocity snaps the cable. That's the only way out."
)
_TETHER_FOLLOW = (
    "Perpendicular to the cable — SIDEWAYS, not forward. "
    "Hard lateral burn snaps it."
)
_JUMP_READY = (
    "Jump window's open. Press J — "
    "sector terminal opens, negotiate your exit."
)


class TutorialManager:
    """
    First-run contextual hints fired once per mechanic, delivered as Bax lines.
    Only instantiated when meta.clone_count == 1 (player has never died).
    """

    def __init__(self):
        self._seen:  set[str] = set()
        self._queue: list[tuple[float, str]] = []   # (fire_at_abs_t, line)
        self._t      = 0.0

        bus.subscribe(EVT_RUN_START,    self._on_run_start)
        bus.subscribe(EVT_TETHER_HIT,   self._on_tether_hit)
        bus.subscribe(EVT_JUMP_READY,   self._on_jump_ready)
        bus.subscribe(EVT_BARGE_NEARBY, self._on_barge_nearby)

    # ------------------------------------------------------------------
    def update(self, dt: float, run_mgr) -> None:
        self._t += dt

        ready = [e for e in self._queue if e[0] <= self._t]
        for entry in ready:
            bus.emit(EVT_BAX_SPEAK, line=entry[1])
            self._queue.remove(entry)

        # Proactive well tip — fires when ship first drifts close to a gravity well
        if "well_tip" not in self._seen and run_mgr.sector is not None:
            ship = run_mgr._ship
            if ship is not None:
                for well in run_mgr.sector.gravity.wells:
                    if (well.pos - ship.body.pos).length() < S.SLINGSHOT_RANGE * 2.2:
                        self._fire_once("well_tip", _WELL)
                        break

    # ------------------------------------------------------------------
    def _fire_once(self, beat_id: str, line: str) -> None:
        if beat_id in self._seen:
            return
        self._seen.add(beat_id)
        bus.emit(EVT_BAX_SPEAK, line=line)

    def _on_run_start(self, **_) -> None:
        t = self._t
        if "controls" not in self._seen:
            self._seen.add("controls")
            self._queue.append((t + 4.5, _CONTROLS))
        if "jump_early" not in self._seen:
            self._seen.add("jump_early")
            self._queue.append((t + 16.0, _JUMP_EARLY))

    def _on_tether_hit(self, **_) -> None:
        if "tether_tip" not in self._seen:
            self._seen.add("tether_tip")
            # Delay so Bax's existing "DRIFT!" reaction displays first
            self._queue.append((self._t + 3.8, _TETHER_FOLLOW))

    def _on_jump_ready(self, **_) -> None:
        self._fire_once("jump_ready", _JUMP_READY)

    def _on_barge_nearby(self, **_) -> None:
        if "barge_tip" not in self._seen:
            self._seen.add("barge_tip")
            # Delay so Bax's existing proximity alert displays first
            self._queue.append((self._t + 3.0, _BARGE))
