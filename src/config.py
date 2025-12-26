"""
Configuration management for PokerBot.

This module provides type-safe configuration classes using dataclasses
for game settings, bot configurations, and UI preferences.
"""

from dataclasses import dataclass, field
from typing import Tuple
from .constants import *


@dataclass
class GameConfig:
    """Configuration for game rules and settings."""
    
    starting_money: int = STARTING_MONEY
    small_blind: int = SMALL_BLIND
    big_blind: int = BIG_BLIND
    max_rounds: int = MAX_ROUNDS
    default_raise: int = DEFAULT_RAISE_AMOUNT
    
    def __post_init__(self):
        """Validate configuration values."""
        if self.starting_money <= 0:
            raise ValueError("Starting money must be positive")
        if self.small_blind <= 0 or self.big_blind <= 0:
            raise ValueError("Blinds must be positive")
        if self.big_blind <= self.small_blind:
            raise ValueError("Big blind must be greater than small blind")
        if self.max_rounds <= 0:
            raise ValueError("Max rounds must be positive")


@dataclass
class BotDifficultyConfig:
    """Configuration for bot AI difficulty levels."""
    
    level: int = 5
    depth: int = None
    mc_sims: int = None
    
    def __post_init__(self):
        """Calculate depth and mc_sims from level if not provided."""
        if not (BOT_LEVEL_MIN <= self.level <= BOT_LEVEL_MAX):
            raise ValueError(f"Bot level must be between {BOT_LEVEL_MIN} and {BOT_LEVEL_MAX}")
        
        # Auto-calculate depth and mc_sims from level if not explicitly set
        if self.depth is None:
            self.depth = self.level
        
        if self.mc_sims is None:
            self.mc_sims = MC_SIMS_BASE + (self.level - 1) * MC_SIMS_PER_LEVEL
    
    def get_description(self) -> str:
        """Get human-readable description of this difficulty level."""
        descriptions = {
            1: "Beginner: Quick decisions, basic strategy",
            2: "Novice: Simple analysis, learning fundamentals",
            3: "Casual: Reasonable play, good for practice",
            4: "Intermediate: Solid fundamentals, challenges beginners",
            5: "Competent: Balanced strategy, good opponent",
            6: "Advanced: Strong analysis, competitive play",
            7: "Expert: Deep thinking, difficult to beat",
            8: "Master: Near-optimal decisions, very strong",
            9: "Grandmaster: Exceptional play, rarely makes mistakes",
            10: "World Class: Maximum analysis, extremely strong"
        }
        return descriptions.get(self.level, "Unknown")
    
    def get_thinking_time_estimate(self) -> str:
        """Estimate average thinking time for this difficulty."""
        # Rough estimate based on mc_sims
        if self.mc_sims < 200:
            return "<0.5s per decision"
        elif self.mc_sims < 1000:
            return "0.5-1s per decision"
        elif self.mc_sims < 3000:
            return "1-2s per decision"
        else:
            return "2-4s per decision"


@dataclass
class UIConfig:
    """Configuration for UI appearance and behavior."""
    
    screen_width: int = SCREEN_WIDTH
    screen_height: int = SCREEN_HEIGHT
    fps: int = FPS
    
    # Colors
    color_background: Tuple[int, int, int] = COLOR_DARK
    color_table: Tuple[int, int, int] = COLOR_GREEN
    color_accent: Tuple[int, int, int] = COLOR_ACCENT
    
    # Card rendering
    card_width: int = CARD_WIDTH
    card_height: int = CARD_HEIGHT
    card_spacing: int = CARD_SPACING
    
    # Animations
    enable_animations: bool = True
    enable_particles: bool = True
    enable_sounds: bool = True
    
    # Log window
    log_line_height: int = LOG_LINE_HEIGHT
    log_max_lines: int = LOG_MAX_LINES
    
    def get_dimensions(self) -> Tuple[int, int]:
        """Get screen dimensions as tuple."""
        return (self.screen_width, self.screen_height)


@dataclass
class AITuningConfig:
    """Configuration for AI decision-making parameters."""
    
    # Evaluation weights
    weight_win_prob: float = WEIGHT_WIN_PROB
    weight_ev: float = WEIGHT_EXPECTED_VALUE
    weight_bankroll: float = WEIGHT_BANKROLL_RATIO
    
    # Thresholds
    raise_min_win_prob: float = RAISE_MIN_WIN_PROB
    large_pot_threshold: int = LARGE_POT_THRESHOLD
    cheap_defend_threshold: int = CHEAP_DEFEND_THRESHOLD
    
    # Penalties and adjustments
    risk_penalty: float = RISK_PENALTY_LARGE_POT
    cheap_defend_adjustment: float = CHEAP_DEFEND_ADJUSTMENT
    
    def __post_init__(self):
        """Validate that weights sum to approximately 1.0."""
        total_weight = self.weight_win_prob + self.weight_ev + self.weight_bankroll
        if not (0.99 <= total_weight <= 1.01):
            raise ValueError(f"Evaluation weights must sum to 1.0, got {total_weight}")


@dataclass
class AppConfig:
    """Main application configuration combining all sub-configs."""
    
    game: GameConfig = field(default_factory=GameConfig)
    bot: BotDifficultyConfig = field(default_factory=BotDifficultyConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    ai_tuning: AITuningConfig = field(default_factory=AITuningConfig)
    
    @classmethod
    def create_default(cls) -> 'AppConfig':
        """Create default configuration."""
        return cls()
    
    @classmethod
    def create_beginner(cls) -> 'AppConfig':
        """Create configuration for beginner players."""
        return cls(
            game=GameConfig(starting_money=200, small_blind=1, big_blind=2),
            bot=BotDifficultyConfig(level=2)
        )
    
    @classmethod
    def create_expert(cls) -> 'AppConfig':
        """Create configuration for expert players."""
        return cls(
            game=GameConfig(starting_money=100, small_blind=5, big_blind=10),
            bot=BotDifficultyConfig(level=9)
        )
    
    def update_bot_level(self, level: int):
        """Update bot difficulty level."""
        self.bot = BotDifficultyConfig(level=level)


# Global default configuration
default_config = AppConfig.create_default()
