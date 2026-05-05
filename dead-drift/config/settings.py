import pygame

# --- Display ---
SCREEN_W = 1280
SCREEN_H = 720
FPS = 60
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
GRAVITY_CONSTANT  = 6.674e-3      # scaled G for gameplay feel
MAX_VELOCITY      = 600.0         # px/s hard cap
DRAG              = 0.0           # true Newtonian: no drag
ROTATION_SPEED    = 180.0         # degrees/s

# --- Ship ---
HULL_MAX          = 100.0
THRUSTER_FORCE    = 280.0         # Newtons (gameplay units)
SHIP_MASS         = 1.0

# --- HUD Glitch Thresholds ---
HUD_FLICKER_HP    = 60.0          # below this: HUD flickers
HUD_DESATURATE_HP = 40.0          # below this: color drains
HUD_SCRAMBLE_HP   = 20.0          # below this: vector tracking scrambles

# --- Terminal ---
TERMINAL_COLS     = 80
TERMINAL_ROWS     = 24
CURSOR_BLINK_MS   = 530

# --- Roguelite ---
SECTORS_PER_RUN   = 10            # the 10-Miler
BASE_CLONE_DEBT   = 15000         # credits tacked on per death
CLONE_FLUID_FEE   = 3500
WRECKAGE_TOW_FEE  = 8000

# --- Tether ---
TETHER_FORCE      = 1200.0        # spring constant for EM harpoon
TETHER_MAX_LENGTH = 350.0         # px before it snaps on its own
SNAP_VELOCITY     = 500.0         # drift speed needed to snap tether

# --- Paths ---
DATA_DIR          = "data"
ASSETS_DIR        = "assets"
BAX_VOCAB_FILE    = "data/bax_vocabulary.json"
REPO_LEDGER_FILE  = "data/repo_ledger.json"
RUN_HISTORY_FILE  = "data/run_history.json"
