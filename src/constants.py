"""
Constants for PokerBot game.

This module centralizes all magic numbers and constant values used throughout
the codebase to improve maintainability and make tuning easier.
"""

# =========================
# Game Constants
# =========================
STARTING_MONEY = 100
MAX_ROUNDS = 5
SMALL_BLIND = 2
BIG_BLIND = 5
DEFAULT_RAISE_AMOUNT = 5

# Bot AI Constants
# =========================
DEFAULT_BOT_DEPTH = 3
DEFAULT_BOT_MC_SIMS = 1000

# Aliases for backward compatibility
BOT_DEPTH = DEFAULT_BOT_DEPTH
BOT_MC_SIMS = DEFAULT_BOT_MC_SIMS

# Bot difficulty levels (1-10)
BOT_LEVEL_MIN = 1
BOT_LEVEL_MAX = 10

# Difficulty scaling
MC_SIMS_BASE = 50
MC_SIMS_PER_LEVEL = 550

# =========================
# AI Tuning Parameters
# =========================

# Evaluation weights
WEIGHT_WIN_PROB = 0.68
WEIGHT_EXPECTED_VALUE = 0.25
WEIGHT_BANKROLL_RATIO = 0.07

# Risk penalties
RISK_PENALTY_LARGE_POT = 0.15
LARGE_POT_THRESHOLD = 30
LOW_WIN_PROB_THRESHOLD = 0.45

# Decision thresholds
MARGIN_PER_DEPTH = 0.005  # Reduced from 0.01 (less conservative)
BASE_MARGIN = 0.01        # Reduced from 0.02 (more aggressive)

# Fold thresholds
CHEAP_DEFEND_THRESHOLD = 5
CHEAP_DEFEND_ADJUSTMENT = 0.08  # Increased from 0.05 (defend more)

# Raise thresholds (very aggressive settings)
RAISE_CHECK_WIN_PROB = 0.50      # Reduced from 0.57 (raise with 50%+ equity)
RAISE_CHECK_DEPTH_ADJUSTMENT = 0.01
RAISE_MIN_WIN_PROB = 0.45        # Reduced from 0.52 (allow more bluffs)
RAISE_LARGE_POT_THRESHOLD = 25
RAISE_LARGE_POT_WIN_PROB = 0.55  # Reduced from 0.60 (more aggressive in big pots)
RAISE_LARGE_POT_PENALTY = 0.05   # Reduced penalty

# Monte Carlo simulation
MC_SIMS_MIN = 80
MC_SIMS_MAX = 350
MC_SIMS_DEPTH_MULTIPLIER = 0.4

# Position adjustments (future use)
EARLY_POSITION_ADJUSTMENT = 0.05
LATE_POSITION_ADJUSTMENT = -0.05

# Position-based strategy adjustments
EARLY_POSITION_FOLD_INCREASE = 0.05   # Fold threshold +5% in early position (small blind)
LATE_POSITION_FOLD_DECREASE = 0.03    # Fold threshold -3% in late position (big blind)
EARLY_POSITION_RAISE_INCREASE = 0.05  # Raise threshold +5% in early position
LATE_POSITION_RAISE_DECREASE = 0.03   # Raise threshold -3% in late position

# Bluffing parameters
BLUFF_MIN_WIN_PROB = 0.30  # Minimum equity to consider bluffing (semi-bluff range)
BLUFF_MAX_WIN_PROB = 0.45  # Maximum equity for bluffing (above this, it's a value raise)
BLUFF_BASE_FREQUENCY = 0.12  # 12% base bluff frequency
BLUFF_LATE_POSITION_BONUS = 0.03  # +3% bluff frequency in late position
BLUFF_LARGE_POT_PENALTY = 0.05  # -5% bluff frequency in large pots
BLUFF_LARGE_POT_SIZE = 30  # Pot size threshold for large pot

# =========================
# UI Constants
# =========================

# Screen dimensions
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 800
FPS = 60

# Colors (RGB)
COLOR_WHITE = (255, 255, 255)
COLOR_BLACK = (0, 0, 0)
COLOR_GREEN = (34, 139, 34)
COLOR_BLUE = (70, 130, 180)
COLOR_RED = (220, 20, 60)
COLOR_YELLOW = (255, 215, 0)
COLOR_GRAY = (128, 128, 128)
COLOR_DARK = (26, 26, 28)
COLOR_PANEL = (36, 36, 40)
COLOR_ACCENT = (255, 230, 120)

# Card dimensions
CARD_WIDTH = 64
CARD_HEIGHT = 92
CARD_SPACING = 72

# Button dimensions
BUTTON_HEIGHT = 50

# Log window
LOG_LINE_HEIGHT = 20
LOG_MAX_LINES = 200
LOG_SCROLL_SPEED = 25

# Particle effects
PARTICLE_COUNT = 25
PARTICLE_LIFE_MIN = 25
PARTICLE_LIFE_MAX = 40

# Animation
REVEAL_ANIMATION_FRAMES = 21
REVEAL_ANIMATION_DELAY = 30  # ms

# Bot thinking delays
BOT_THINK_DELAY_MIN = 300  # ms
BOT_THINK_DELAY_MAX = 900  # ms

# =========================
# Asset Paths
# =========================
ASSET_DIR = "assets"
SOUND_CHECK = f"{ASSET_DIR}/check.wav"
SOUND_CALL = f"{ASSET_DIR}/call.wav"
SOUND_RAISE = f"{ASSET_DIR}/chips.wav"
SOUND_FOLD = f"{ASSET_DIR}/fold.wav"
SOUND_WIN = f"{ASSET_DIR}/win.wav"
SOUND_SHUFFLE = f"{ASSET_DIR}/shuffle.wav"

IMAGE_AVATAR_YOU = f"{ASSET_DIR}/you.png"
IMAGE_AVATAR_BOT = f"{ASSET_DIR}/bot.png"
IMAGE_CHIP = f"{ASSET_DIR}/chip.png"

# =========================
# Poker Constants
# =========================
CARDS_IN_DECK = 52
CARDS_PER_HAND = 2
COMMUNITY_CARDS_FLOP = 3
COMMUNITY_CARDS_TURN = 1
COMMUNITY_CARDS_RIVER = 1
COMMUNITY_CARDS_TOTAL = 5

# Action types
ACTION_FOLD = "fold"
ACTION_CHECK = "check"
ACTION_CALL = "call"
ACTION_RAISE = "raise"
ACTION_BET = "bet"

# Player positions (for future multi-player support)
POSITION_DEALER = "dealer"
POSITION_SMALL_BLIND = "small_blind"
POSITION_BIG_BLIND = "big_blind"
POSITION_UNDER_GUN = "under_the_gun"
POSITION_MIDDLE = "middle"
POSITION_CUTOFF = "cutoff"
POSITION_BUTTON = "button"
