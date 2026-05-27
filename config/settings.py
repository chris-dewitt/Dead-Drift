import pygame

# --- Display ---
SCREEN_W  = 1600
SCREEN_H  = 900
COCKPIT_H = 90        # bottom strip reserved for Bax cockpit
FLIGHT_H  = SCREEN_H - COCKPIT_H   # usable flight area height
FPS   = 60
TITLE = "DEAD DRIFT"

# --- Colors ---
BLACK       = (0,   0,   0)
VOID        = (4,   4,   8)       # background: almost-black space
GREEN_TERM  = (0,   255, 70)      # terminal text
AMBER_TERM  = (255, 176, 0)       # terminal alt / repo barge hazard
NEON_BLUE   = (30,  80,  255)     # thruster exhaust
WHITE_VEC   = (220, 220, 220)     # vector ship lines
RED_WARN    = (220, 40,  40)
GREY_DEAD   = (60,  60,  60)

# --- Physics ---
GRAVITY_CONSTANT  = 340.0         # scaled G for gameplay feel — produces ~13 px/s² at 200px from a standard well
MAX_VELOCITY      = 280.0         # px/s soft cap (was 380 — death-spiral fix: gives the world breathing room)
DRAG              = 0.0           # true Newtonian: no drag
ROTATION_SPEED    = 240.0         # degrees/s (was 200 — snappier turns)
STEER_RCS_DEG     = 140.0         # deg/s velocity redirect toward facing when thrusting (was 90 — cuts the "blur" feel)
HIT_IFRAME_T      = 1.5           # seconds of debris/obstacle invulnerability after any hull damage

# --- Camera glide ---
# Soft lead-camera. The flight area tile-blits with an offset that follows
# ship velocity, returning to center when slow. World still wraps; offset is
# capped so the displaced view never feels untethered.
CAMERA_GLIDE_MAX   = 56.0          # px — max offset in either axis
CAMERA_GLIDE_GAIN  = 0.20          # offset = clamp(vel * gain, ±MAX)
CAMERA_GLIDE_RATE  = 1.6           # exponential approach rate (per second)

# --- AI ships ---
# NPC ships that share the sector with the player. See antagonists/ai_ship.py.
AISHIP_PER_SECTOR_MIN = 1          # always at least one ambient ship
AISHIP_PER_SECTOR_MAX = 3          # cap so the sector doesn't get crowded
AISHIP_SPAWN_DELAY    = 6.0        # seconds after sector load before first AI ship
AISHIP_RAM_DAMAGE     = 18.0       # hull damage per pirate ram

# --- Ship ---
HULL_MAX          = 200.0
THRUSTER_FORCE    = 175.0         # Newtons (gameplay units) — was 205, reduced for weightier feel
SHIP_MASS         = 1.0

# --- Guns ---
BULLET_SPEED          = 860.0     # px/s
BULLET_LIFETIME       = 0.68      # seconds before bullet expires
GUN_COOLDOWN          = 0.17      # seconds between shots
GUN_MALFUNCTION_CHANCE = 0.04     # probability per shot of fizzle
GUN_JAM_DURATION      = 2.2       # seconds gun is out after malfunction

# --- HUD Glitch Thresholds ---
HUD_FLICKER_HP    = 120.0         # below this: HUD flickers  (60% of 200)
HUD_DESATURATE_HP = 80.0          # below this: color drains  (40%)
HUD_SCRAMBLE_HP   = 40.0          # below this: vector tracking scrambles (20%)

# --- Terminal ---
TERMINAL_COLS     = 80
TERMINAL_ROWS     = 24
CURSOR_BLINK_MS   = 530
TYPEWRITER_SPEED  = 44.0          # chars/sec for NPC dialogue reveal

# --- MycoShroom (Ch.2 cargo) ---
SPORE_INTERVAL_MIN = 10.0          # seconds between inversion triggers
SPORE_INTERVAL_MAX = 20.0
SPORE_DURATION     = 6.0           # seconds controls are inverted
# Aliveness A.2 (May 2026 playtest) — the *first* inversion of a fresh cargo
# lands inside this tighter window so the player reliably experiences the
# mechanic before the 20s sector-jump terminal can open. Subsequent triggers
# fall back to SPORE_INTERVAL_MIN/MAX.
SPORE_FIRST_TRIGGER_MIN = 6.0
SPORE_FIRST_TRIGGER_MAX = 9.0

# --- Roguelite ---
SECTORS_PER_RUN   = 5             # the 5-sector sprint
BASE_CLONE_DEBT   = 15000         # credits tacked on per death
CLONE_FLUID_FEE   = 3500
WRECKAGE_TOW_FEE  = 8000
DEBT_INTEREST_RATE = 0.00004      # fraction of debt accruing per second (display only)

# --- Debris / Canisters / Satellites ---
DEBRIS_COUNT      = 3
CANISTER_COUNT    = 3
SATELLITE_COUNT   = 3
CANISTER_PICKUP_R = 28.0
DEBRIS_DAMAGE     = 8.0

# --- Mid-flight Events ---
EVENT_INTERVAL_MIN = 55.0         # min seconds between random flight events
EVENT_INTERVAL_MAX = 110.0        # max seconds between random flight events
KRESS_INTERVAL_MIN = 80.0         # min seconds between KRESS transmissions
KRESS_INTERVAL_MAX = 140.0
COLLECTOR_INTERVAL_MIN = 110.0
COLLECTOR_INTERVAL_MAX = 200.0

# --- Slingshot ---
SLINGSHOT_SPEED   = 220.0    # px/s needed to count
SLINGSHOT_RANGE   = 190.0    # px — must have been this close to a well
SLINGSHOT_BONUS   = 5.0      # seconds shaved off jump timer

# --- Shop ---
SHOP_SECTORS          = {1, 3}            # 0-based sector indices that trigger shop (after sector 2 and 4)
JAMMER_COOLDOWN       = 90.0             # seconds barge intercept suppressed after buying jammer

# --- TriplicateForm (Ch.3 cargo) ---
FORM_TRIGGER_MIN = 7.0           # seconds between form popup triggers
FORM_TRIGGER_MAX = 16.0
FORM_TIMEOUT     = 4.0           # seconds to respond before penalty

# --- Tether ---
TETHER_FORCE      = 780.0         # spring constant for EM harpoon
TETHER_MAX_LENGTH = 350.0         # px before it snaps on its own
SNAP_VELOCITY     = 200.0         # lateral drift speed needed to snap tether

# --- Aliveness Phase C (May 2026) — gameplay mechanics ---
COLLISION_SPEED_BASE    = 80.0    # px/s below which impact damage is unscaled
COLLISION_SPEED_SCALE   = 0.012   # extra damage per px/s above base
SLINGSHOT_CHAIN_WINDOW  = 3.0       # seconds between slingshots to stack chain
SLINGSHOT_CHAIN_MULTS   = (1.0, 1.5, 2.0, 2.5)
SECTOR_ESCALATION_INTERVAL = 30.0 # seconds between sector pressure ramps
ORBIT_BONUS_DURATION    = 3.0       # seconds in velocity band near a well
ORBIT_BONUS_MULT        = 1.5       # credit multiplier vs base slingshot bonus
ORBIT_SPEED_MIN         = 120.0     # px/s lower band for orbital hold
DEBT_RECOVERED_MILESTONE = 500      # cr recovered this run before debt bites back
BARGE_PATROL_CONE_DEG   = 55.0
BARGE_PATROL_CONE_LEN   = 280.0

# --- Fuel ---
FUEL_MAX          = 100.0         # full tank
FUEL_DRAIN_FWD    = 5.0           # per second forward thrust
FUEL_DRAIN_REV    = 3.0           # per second reverse thrust
FUEL_PICKUP_AMT   = 50.0          # restored by picking up a canister
FUEL_LOW_WARN     = 25.0          # below this: Bax warns once per sector

# --- Paths ---
DATA_DIR          = "data"
ASSETS_DIR        = "assets"
BAX_VOCAB_FILE    = "data/bax_vocabulary.json"
REPO_LEDGER_FILE  = "data/repo_ledger.json"
RUN_HISTORY_FILE  = "data/run_history.json"   # legacy; migrated to slot 1 on first launch
SAVES_DIR         = "data/saves"
MANIFEST_FILE     = "data/saves/manifest.json"
MAX_SAVE_SLOTS    = 3
