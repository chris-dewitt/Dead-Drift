from typing import Callable


class EventBus:
    """Lightweight pub/sub. All game systems talk through here."""

    def __init__(self):
        self._listeners: dict[str, list[Callable]] = {}

    def subscribe(self, event: str, callback: Callable):
        if event not in self._listeners:
            self._listeners[event] = []
        self._listeners[event].append(callback)

    def unsubscribe(self, event: str, callback: Callable):
        lst = self._listeners.get(event)
        if lst:
            try:
                lst.remove(callback)
            except ValueError:
                pass

    def emit(self, event: str, **payload):
        # Snapshot the list before iterating so a callback that unsubscribes
        # itself during dispatch doesn't skip adjacent entries.
        for cb in list(self._listeners.get(event, ())):
            cb(**payload)


# Global singleton — import and use anywhere.
bus = EventBus()


class Subscriber:
    """
    Mixin for any system that owns event subscriptions and may be torn down
    or rebuilt (Epic 1.4).  Track subscriptions made via self.subscribe() so
    unsubscribe_all() can release them in one call — prevents handlers on
    dead instances firing after a rebuild.

    Usage:
        class Bax(Subscriber):
            def __init__(self):
                super().__init__()
                self.subscribe(EVT_HULL_DAMAGE, self._on_hull_damage)
                ...

            def teardown(self):
                self.unsubscribe_all()
    """

    def __init__(self):
        self._subscriptions: list[tuple[str, Callable]] = []

    def subscribe(self, event: str, callback: Callable) -> None:
        bus.subscribe(event, callback)
        self._subscriptions.append((event, callback))

    def unsubscribe_all(self) -> None:
        for event, callback in self._subscriptions:
            bus.unsubscribe(event, callback)
        self._subscriptions.clear()

# --- Canonical event names ---
EVT_HULL_DAMAGE    = "hull_damage"       # payload: amount
EVT_HULL_CRITICAL  = "hull_critical"     # payload: hp
EVT_SHIP_DESTROYED = "ship_destroyed"
EVT_TETHER_HIT     = "tether_hit"        # payload: barge
EVT_TETHER_SNAP    = "tether_snap"
EVT_THRUSTER_OVERHEAT = "thruster_overheat"  # payload: thruster, heat
EVT_MODULE_UNBOLTED = "module_unbolted"  # payload: module
EVT_CARGO_DAMAGED  = "cargo_damaged"     # payload: cargo, severity
EVT_TERMINAL_OPEN  = "terminal_open"     # payload: npc
EVT_TERMINAL_CLOSE = "terminal_close"    # payload: outcome
EVT_TERMINAL_KEY   = "terminal_key"      # payload: kind (normal/backspace/enter)
EVT_NLP_EXPLOIT    = "nlp_exploit"       # payload: npc, exploit_key
EVT_RUN_START      = "run_start"
EVT_RUN_END        = "run_end"           # payload: success
EVT_SECTOR_CLEAR   = "sector_clear"      # payload: sector_num
EVT_BAX_SPEAK      = "bax_speak"         # payload: line
EVT_DEBT_UPDATE    = "debt_update"       # payload: delta, total
EVT_SLINGSHOT      = "slingshot"         # payload: speed
EVT_BARGE_NEARBY   = "barge_nearby"     # payload: distance
EVT_CANISTER_GRAB  = "canister_grab"    # payload: (none)
EVT_COMMS_INTERCEPT = "comms_intercept" # random Union radio chatter intercepted
EVT_DEBRIS_SHOWER  = "debris_shower"    # temporary asteroid belt fragment shower
EVT_SCAN_PING      = "scan_ping"        # Union passive scanner pulse; payload: pos_x, pos_y
EVT_SOLAR_WIND     = "solar_wind"       # payload: direction, duration, strength
EVT_GUN_FIRE       = "gun_fire"         # bullet fired successfully
EVT_GUN_MALFUNCTION = "gun_malfunction" # gun fizzled/jammed
EVT_COMMS_SPEAK    = "comms_speak"      # non-Bax transmission; payload: speaker, line
EVT_SPORE_INVERTED  = "spore_inverted"   # payload: active (bool)
EVT_VOICE_CHAR      = "voice_char"       # payload: speaker (str) — emitted per N chars by typewriter
EVT_BARGE_INTERCEPT = "barge_intercept" # barge opened comm mid-flight; payload: barge
EVT_KRESS_DIALLED   = "kress_dialled"   # player called Kress mid-flight
EVT_SATELLITE_HIT   = "satellite_hit"   # player ship hit a satellite
EVT_ALIEN_SIGHTING  = "alien_sighting"  # alien ship passed through sector
EVT_TORCH_ACTIVE    = "torch_active"    # barge entered TORCH state; payload: barge
EVT_HARPOON_ARMING  = "harpoon_arming"  # barge entered AIM state; payload: barge, countdown
EVT_DEMO_NOTICE     = "demo_notice"     # galactic infrastructure demolition notice
EVT_JUMP_READY      = "jump_ready"      # sector timer complete — jump window open
EVT_DEBT_DING       = "debt_ding"       # debt crossed another 1000cr milestone
EVT_DELIVERY_STEP   = "delivery_step"   # footstep during delivery run
EVT_DELIVERY_HIT    = "delivery_hit"    # obstacle contact during delivery run
EVT_DELIVERY_DONE   = "delivery_done"   # courier reached drop-off
EVT_WARP_JUMP       = "warp_jump"       # sector-to-sector jump initiated
EVT_SHOP_ENTER      = "shop_enter"      # shop screen opened between sectors
EVT_SHOP_BUY        = "shop_buy"        # item purchased; payload: tag, name
EVT_SHOP_SKIP       = "shop_skip"       # player left shop without buying
EVT_FINAL_SECTOR    = "final_sector"    # entering the last sector of the run
EVT_SECTOR_START    = "sector_start"    # new sector loaded; payload: sector_num, cargo_type

# New events (Epic 7 / corridor / dock)
EVT_BARGE_KILLED    = "barge_killed"    # repo barge destroyed; payload: barge
EVT_KILL_SCORED     = "kill_scored"     # any target killed in sector
EVT_CORRIDOR_RUN    = "corridor_run"    # ambient: player running in corridor
EVT_CORRIDOR_JUMP   = "corridor_jump"   # player jumped a gap in corridor
EVT_CORRIDOR_SECRET = "corridor_secret" # secret found in corridor
EVT_CORRIDOR_DEATH  = "corridor_death"  # player hit/died in corridor (respawn)
EVT_DOCK_APPROACH   = "dock_approach"   # landing Beat 1 begins
EVT_DOCK_PERFECT    = "dock_perfect"    # both landing inputs hit cleanly
EVT_DOCK_ROUGH      = "dock_rough"      # both landing inputs missed
EVT_AISHIP_HAIL     = "aiship_hail"     # NPC ship pulled alongside; payload: ship, npc_type, ship_class
EVT_AISHIP_DESTROYED = "aiship_destroyed"  # NPC ship shot down; payload: ship

# Epic 11 — Bax skill-reaction events
EVT_CLOSE_CALL          = "close_call"          # barge/debris passed within 30px without hitting
EVT_SKILL_MANEUVER      = "skill_maneuver"      # slingshot + velocity redirect within 2s
EVT_LONG_FIGHT_SURVIVED = "long_fight_survived" # barge in pursuit >45s, no capture
EVT_FIRST_TETHER_SNAP   = "first_tether_snap"   # tether snapped first time this run

# Epic 12 — Replayability events
EVT_MUTATOR_SET     = "mutator_set"     # payload: mutator_key (or None)
EVT_UNLOCK_EARNED   = "unlock_earned"   # payload: key, label

# Epic 8 — Meta-progression / replay events
EVT_LORE_FOUND      = "lore_found"      # payload: text, chapter (corridor secret)

# Epic 4.6 — corridor music phases
EVT_CORRIDOR_ENTER     = "corridor_enter"      # payload: chapter
EVT_CORRIDOR_BOSS_ROOM = "corridor_boss_room"  # payload: chapter (boss-room trigger)
EVT_CORRIDOR_EXIT      = "corridor_exit"       # payload: chapter

# Aliveness Phase F
EVT_BAX_HARMONICA      = "bax_harmonica"       # harmonica trigger at <10% hull
EVT_CARGO_FIRST_SEEN   = "cargo_first_seen"    # first time a cargo type is aboard this run; payload: cargo_type

# Aliveness Phase G
EVT_DOCK_GARY_LINE     = "dock_gary_line"      # payload: line — Gary speaks during Beat 3
EVT_DOCK_RADIO         = "dock_radio"          # payload: line, clear (bool) — Dock Control during approach
EVT_CORRIDOR_UNEASE    = "corridor_unease"     # Bax awkward in corridor; no payload
