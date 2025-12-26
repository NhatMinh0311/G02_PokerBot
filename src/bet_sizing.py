"""
Dynamic bet sizing for poker bot.

This module calculates optimal bet sizes based on hand strength, pot size,
and game situation to make the bot's betting more realistic and unpredictable.
"""

import random
from typing import Optional


def calculate_bet_size(
    win_prob: float,
    pot: float,
    current_bet: float,
    bot_money: float,
    community_cards: int = 0
) -> float:
    """
    Calculate optimal bet size based on hand strength and situation.
    
    Uses different betting strategies based on hand strength:
    - Very strong (>85%): Bet 70-100% pot to extract maximum value
    - Strong (70-85%): Bet 60-75% pot for value
    - Medium-strong (55-70%): Bet 40-60% pot for protection
    - Medium (45-55%): Bet 25-40% pot or check
    - Bluff range (<45%): Bet 40-60% pot to balance range
    
    Args:
        win_prob: Estimated win probability (0.0 to 1.0)
        pot: Current pot size in dollars
        current_bet: Current bet to call
        bot_money: Bot's remaining stack
        community_cards: Number of community cards dealt (for phase detection)
    
    Returns:
        Bet amount in dollars (rounded to nearest dollar)
    
    Example:
        >>> calculate_bet_size(win_prob=0.75, pot=20, current_bet=5, bot_money=100)
        14  # 70% of pot for strong hand
    """
    # Very strong hands: bet big for value (70-100% pot)
    if win_prob >= 0.85:
        bet_pct = random.uniform(0.70, 1.00)
    
    # Strong hands: value bet (60-75% pot)
    elif win_prob >= 0.70:
        bet_pct = random.uniform(0.60, 0.75)
    
    # Medium-strong: protection bet (40-60% pot)
    elif win_prob >= 0.55:
        bet_pct = random.uniform(0.40, 0.60)
    
    # Medium: smaller bet (25-40% pot)
    elif win_prob >= 0.45:
        bet_pct = random.uniform(0.25, 0.40)
    
    # Bluff territory: semi-bluff sizing (40-60% pot, same as value for balance)
    else:
        bet_pct = random.uniform(0.40, 0.60)
    
    # Calculate actual bet amount
    bet_amount = pot * bet_pct
    
    # Minimum bet: $2 (small blind)
    bet_amount = max(2, bet_amount)
    
    # Don't bet more than we have
    bet_amount = min(bet_amount, bot_money)
    
    # Round to nearest dollar
    return round(bet_amount)


def determine_phase(community_cards: int) -> str:
    """
    Determine the current game phase based on community cards.
    
    Args:
        community_cards: Number of community cards dealt
    
    Returns:
        Phase string: 'pre_flop', 'flop', 'turn', or 'river'
    """
    if community_cards == 0:
        return 'pre_flop'
    elif community_cards == 3:
        return 'flop'
    elif community_cards == 4:
        return 'turn'
    else:
        return 'river'
