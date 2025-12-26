"""
Data models for PokerBot game.

This module defines the core data structures used throughout the application
using dataclasses for type safety and clarity.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Literal
from enum import Enum


# =========================
# Enums
# =========================

class ActionType(Enum):
    """Poker action types."""
    FOLD = "fold"
    CHECK = "check"
    CALL = "call"
    RAISE = "raise"
    BET = "bet"


class GamePhase(Enum):
    """Game phases."""
    PRE_FLOP = "pre_flop"
    FLOP = "flop"
    TURN = "turn"
    RIVER = "river"
    SHOWDOWN = "showdown"


# =========================
# Statistics Models
# =========================

@dataclass
class BotStatistics:
    """Statistics tracked for bot performance analysis."""
    
    decisions: int = 0
    folds: int = 0
    raises: int = 0
    calls: int = 0
    checks: int = 0
    
    decision_times: List[float] = field(default_factory=list)
    win_probs: List[float] = field(default_factory=list)
    
    rounds_total: int = 0
    rounds_won: int = 0
    rounds_lost: int = 0
    rounds_tied: int = 0
    
    def fold_rate(self) -> float:
        """Calculate fold rate."""
        return self.folds / self.decisions if self.decisions > 0 else 0.0
    
    def raise_rate(self) -> float:
        """Calculate raise rate."""
        return self.raises / self.decisions if self.decisions > 0 else 0.0
    
    def call_rate(self) -> float:
        """Calculate call rate."""
        return self.calls / self.decisions if self.decisions > 0 else 0.0
    
    def check_rate(self) -> float:
        """Calculate check rate."""
        return self.checks / self.decisions if self.decisions > 0 else 0.0
    
    def avg_decision_time(self) -> float:
        """Calculate average decision time."""
        return sum(self.decision_times) / len(self.decision_times) if self.decision_times else 0.0
    
    def avg_win_prob(self) -> float:
        """Calculate average win probability."""
        return sum(self.win_probs) / len(self.win_probs) if self.win_probs else 0.0
    
    def win_rate(self) -> float:
        """Calculate win rate."""
        total = self.rounds_won + self.rounds_lost + self.rounds_tied
        return self.rounds_won / total if total > 0 else 0.0


@dataclass
class PlayerStatistics:
    """Statistics tracked for human players."""
    
    hands_played: int = 0
    hands_won: int = 0
    hands_lost: int = 0
    hands_tied: int = 0
    
    total_money_won: float = 0.0
    total_money_lost: float = 0.0
    biggest_pot_won: float = 0.0
    biggest_pot_lost: float = 0.0
    
    # Player tendencies
    vpip: float = 0.0  # Voluntarily Put money In Pot
    pfr: float = 0.0   # Pre-Flop Raise
    aggression_factor: float = 0.0  # (Bets + Raises) / Calls
    
    def win_rate(self) -> float:
        """Calculate win rate."""
        total = self.hands_won + self.hands_lost + self.hands_tied
        return self.hands_won / total if total > 0 else 0.0
    
    def net_profit(self) -> float:
        """Calculate net profit."""
        return self.total_money_won - self.total_money_lost


# =========================
# Game State Models
# =========================

@dataclass
class PlayerState:
    """Represents the current state of a player."""
    
    name: str
    money: float
    hand: List[int] = field(default_factory=list)
    current_bet: float = 0.0
    folded: bool = False
    is_bot: bool = False
    
    # Bot-specific
    depth: Optional[int] = None
    mc_sims: Optional[int] = None
    bot_stats: Optional[BotStatistics] = None
    
    # Player-specific
    player_stats: Optional[PlayerStatistics] = None
    
    def reset_hand(self):
        """Reset player state for a new hand."""
        self.hand = []
        self.current_bet = 0.0
        self.folded = False
    
    def is_active(self) -> bool:
        """Check if player is still active in the hand."""
        return not self.folded and self.money > 0
    
    def can_bet(self, amount: float) -> bool:
        """Check if player can make a bet of given amount."""
        return self.money >= amount and not self.folded


@dataclass
class GameState:
    """Represents the complete state of the poker game."""
    
    players: List[PlayerState]
    community_cards: List[int] = field(default_factory=list)
    pot: float = 0.0
    current_bet: float = 0.0
    phase: GamePhase = GamePhase.PRE_FLOP
    dealer_index: int = 0
    active_player_index: int = 0
    
    def get_active_players(self) -> List[PlayerState]:
        """Get list of players still in the hand."""
        return [p for p in self.players if p.is_active()]
    
    def is_round_over(self) -> bool:
        """Check if the current round is over."""
        return len(self.get_active_players()) <= 1
    
    def get_bot_player(self) -> Optional[PlayerState]:
        """Get the bot player if exists."""
        bots = [p for p in self.players if p.is_bot]
        return bots[0] if bots else None
    
    def get_human_player(self) -> Optional[PlayerState]:
        """Get the human player if exists."""
        humans = [p for p in self.players if not p.is_bot]
        return humans[0] if humans else None


@dataclass
class BotDecisionState:
    """State information used for bot decision making."""
    
    bot_hand: List[int]
    community: List[int]
    pot: float
    current_bet: float
    bot_money: float
    opp_money: float
    bot_current_bet: float
    raise_amount: float
    terminal: bool = False
    winner: Optional[str] = None


@dataclass
class ActionRecord:
    """Record of a single action in the game."""
    
    player_name: str
    action: ActionType
    amount: float
    pot_after: float
    phase: GamePhase
    timestamp: Optional[float] = None


@dataclass
class HandHistory:
    """Complete record of a poker hand."""
    
    hand_id: str
    players: List[str]
    starting_stacks: Dict[str, float]
    actions: List[ActionRecord] = field(default_factory=list)
    community_cards: List[int] = field(default_factory=list)
    winner: Optional[str] = None
    pot_size: float = 0.0
    
    def add_action(self, action: ActionRecord):
        """Add an action to the hand history."""
        self.actions.append(action)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "hand_id": self.hand_id,
            "players": self.players,
            "starting_stacks": self.starting_stacks,
            "actions": [
                {
                    "player": a.player_name,
                    "action": a.action.value,
                    "amount": a.amount,
                    "pot_after": a.pot_after,
                    "phase": a.phase.value
                }
                for a in self.actions
            ],
            "community_cards": self.community_cards,
            "winner": self.winner,
            "pot_size": self.pot_size
        }


# =========================
# Legacy Compatibility
# =========================

# For backward compatibility with existing code
BOT_LOG_TEMPLATE = {
    "decisions": 0,
    "folds": 0,
    "raises": 0,
    "calls": 0,
    "checks": 0,
    "decision_times": [],
    "win_probs": [],
    "rounds": {
        "total": 0,
        "bot_wins": 0,
        "player_wins": 0,
        "ties": 0
    }
}
