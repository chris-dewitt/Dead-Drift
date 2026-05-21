import pygame

# --- Display ---
SCREEN_W  = 1280
SCREEN_H  = 720
COCKPIT_H = 80        # bottom strip reserved for Bax cockpit
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
MAX_VELOCITY      = 440.0         # px/s hard cap
DRAG              = 0.0           # true Newtonian: no drag
ROTATION_SPEED    = 200.0         # degrees/s
STEER_RCS_DEG     = 90.0          # deg/s velocity redirect toward facing when thrusting (post-integrate)

# --- Ship ---
HULL_MAX          = 200.0
THRUSTER_FORCE    = 205.0         # Newtons (gameplay units)
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
SPORE_INTERVAL_MIN = 13.0          # seconds between inversion triggers
SPORE_INTERVAL_MAX = 25.0
SPORE_DURATION     = 4.0           # seconds controls are inverted

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
FORM_TRIGGER_MIN = 18.0          # seconds between form popup triggers
FORM_TRIGGER_MAX = 38.0
FORM_TIMEOUT     = 6.0           # seconds to respond before penalty

# --- Tether ---
TETHER_FORCE      = 780.0         # spring constant for EM harpoon
TETHER_MAX_LENGTH = 350.0         # px before it snaps on its own
SNAP_VELOCITY     = 200.0         # lateral drift speed needed to snap tether

# --- Paths ---
DATA_DIR          = "data"
ASSETS_DIR        = "assets"
BAX_VOCAB_FILE    = "data/bax_vocabulary.json"
REPO_LEDGER_FILE  = "data/repo_ledger.json"
RUN_HISTORY_FILE  = "data/run_history.json"
