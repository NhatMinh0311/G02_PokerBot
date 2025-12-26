"""Bot AI decision-making logic for PokerBot.

This module implements the core bot intelligence using:
- Monte Carlo simulation for win probability estimation (with parallel support)
- MiniMax algorithm with Alpha-Beta pruning for optimal decision-making
- Dynamic strategy adjustments based on game state
- Dynamic bet sizing based on hand strength
"""

import random
import copy
import time
from typing import List, Dict, Tuple, Optional, Any
from treys import Evaluator, Deck

# Import configuration and constants
from .constants import (
    DEFAULT_RAISE_AMOUNT,
    WEIGHT_WIN_PROB,
    WEIGHT_EXPECTED_VALUE,
    WEIGHT_BANKROLL_RATIO,
    RISK_PENALTY_LARGE_POT,
    LARGE_POT_THRESHOLD,
    LOW_WIN_PROB_THRESHOLD,
    MARGIN_PER_DEPTH,
    BASE_MARGIN,
    CHEAP_DEFEND_THRESHOLD,
    CHEAP_DEFEND_ADJUSTMENT,
    RAISE_CHECK_WIN_PROB,
    RAISE_CHECK_DEPTH_ADJUSTMENT,
    RAISE_MIN_WIN_PROB,
    RAISE_LARGE_POT_THRESHOLD,
    RAISE_LARGE_POT_WIN_PROB,
    RAISE_LARGE_POT_PENALTY,
    MC_SIMS_MIN,
    MC_SIMS_MAX,
    MC_SIMS_DEPTH_MULTIPLIER,
    # Bluffing constants
    BLUFF_MIN_WIN_PROB,
    BLUFF_MAX_WIN_PROB,
    BLUFF_BASE_FREQUENCY,
    BLUFF_LATE_POSITION_BONUS,
    BLUFF_LARGE_POT_PENALTY,
    BLUFF_LARGE_POT_SIZE,
)
from .models import BOT_LOG_TEMPLATE
from .bet_sizing import calculate_bet_size
from .monte_carlo_parallel import monte_carlo_parallel

# Global instances (will be refactored to dependency injection later)
evaluator = Evaluator()
FULL_DECK = Deck()

# Flag to enable/disable parallel Monte Carlo (can be toggled for testing)
USE_PARALLEL_MONTE_CARLO = True


# ===============================
# MONTE CARLO WIN PROBABILITY
# ===============================

def monte_carlo_win_prob(
    bot_hand: List[int],
    community: List[int],
    n_sim: int = 200
) -> float:
    """
    Estimate win probability using Monte Carlo simulation.
    
    Simulates random opponent hands and community card completions to estimate
    the probability that the bot's hand will win at showdown.
    
    Uses parallel Monte Carlo for n_sim >= 100 for better performance.
    
    Args:
        bot_hand: List of card integers representing bot's hole cards
        community: List of card integers for community cards dealt so far
        n_sim: Number of simulations to run (higher = more accurate but slower)
    
    Returns:
        Estimated win probability as a float between 0.0 and 1.0
        
    Example:
        >>> bot_hand = [Card.new('As'), Card.new('Kh')]
        >>> community = [Card.new('Ah'), Card.new('Kd'), Card.new('Qs')]
        >>> win_prob = monte_carlo_win_prob(bot_hand, community, 1000)
        >>> print(f"Win probability: {win_prob:.2%}")
        Win probability: 78.50%
    """
    # Use parallel version for larger simulations (significant speedup)
    if USE_PARALLEL_MONTE_CARLO and n_sim >= 100:
        return monte_carlo_parallel(bot_hand, community, FULL_DECK.cards, n_sim)
    
    # Fallback to sequential implementation for small simulations
    # Get all cards that are already in play
    used = set(bot_hand + community)
    deck_cards = [c for c in FULL_DECK.cards if c not in used]

    wins = 0.0
    n_sim = max(1, n_sim)  # Ensure at least 1 simulation

    for _ in range(n_sim):
        # Shuffle and deal random opponent hand
        random.shuffle(deck_cards)
        opp_hand = deck_cards[:2]

        # Complete the community cards to 5 cards
        sim_comm = community.copy()
        idx = 2
        while len(sim_comm) < 5:
            sim_comm.append(deck_cards[idx])
            idx += 1

        # Evaluate both hands (lower score = better hand in treys)
        bot_rank = evaluator.evaluate(sim_comm, bot_hand)
        opp_rank = evaluator.evaluate(sim_comm, opp_hand)

        # Count wins and ties
        if bot_rank < opp_rank:
            wins += 1
        elif bot_rank == opp_rank:
            wins += 0.5  # Count ties as half a win

    return wins / n_sim


# ===============================
# ACTION SPACE
# ===============================

def get_possible_actions(state: Dict[str, Any]) -> List[str]:
    """
    Get list of valid actions based on current game state.
    
    Args:
        state: Dictionary containing game state with 'current_bet' key
    
    Returns:
        List of valid action strings: ['check', 'raise'] or ['fold', 'call', 'raise']
    """
    if state["current_bet"] == 0:
        return ["check", "raise"]
    return ["fold", "call", "raise"]


# ===============================
# SIMULATE ACTION
# ===============================

def simulate_action(
    state: Dict[str, Any],
    action: str,
    actor: str = "bot"
) -> Dict[str, Any]:
    """
    Simulate the effect of an action on the game state.
    
    Creates a deep copy of the state and applies the action to it, allowing
    MiniMax to explore future game states without modifying the current state.
    
    Args:
        state: Current game state dictionary
        action: Action to simulate ('fold', 'check', 'call', 'raise')
        actor: Who is taking the action ('bot' or other)
    
    Returns:
        New state dictionary after applying the action
    """
    s = copy.deepcopy(state)
    raise_amt = s["raise_amount"]

    if action == "fold":
        s["terminal"] = True
        s["winner"] = "opp" if actor == "bot" else "bot"
        return s

    if action == "check":
        return s

    if action == "call":
        to_call = s["current_bet"] - s["bot_current_bet"]
        to_call = max(0, to_call)
        s["bot_money"] -= to_call
        s["bot_current_bet"] += to_call
        s["pot"] += to_call
        return s

    if action == "raise":
        # Use dynamic bet sizing if provided, otherwise fall back to default
        if "dynamic_raise" in s and s["dynamic_raise"]:
            raise_amt = s["dynamic_raise"]
        else:
            raise_amt = s["raise_amount"]
            
        new_total = s["current_bet"] + raise_amt
        diff = new_total - s["bot_current_bet"]
        diff = max(0, diff)

        s["bot_money"] -= diff
        s["bot_current_bet"] += diff
        s["pot"] += diff
        s["current_bet"] = new_total
        return s

    return s


# ===============================
# STATE EVALUATION
# ===============================

def evaluate_state(state: Dict[str, Any], mc_sims: int = 120) -> float:
    """
    Evaluate the current game state for the bot.
    
    Combines win probability, expected value, and bankroll considerations
    to score a game state. Higher scores are better for the bot.
    
    Args:
        state: Game state dictionary
        mc_sims: Number of Monte Carlo simulations to run
    
    Returns:
        Score representing the value of this state for the bot
    """
    win_prob = monte_carlo_win_prob(state["bot_hand"], state["community"], mc_sims)
    to_call = max(0, state["current_bet"] - state["bot_current_bet"])
    pot = state["pot"]
    raise_amt = state["raise_amount"]

    # Expected value calculations
    ev_call = win_prob * (pot + to_call) - (1 - win_prob) * to_call
    ev_raise = win_prob * (pot + to_call + raise_amt) - (1 - win_prob) * (to_call + raise_amt)

    # Bankroll ratio (avoid division by zero)
    total_money = state["bot_money"] + state["opp_money"]
    if total_money > 0:
        bankroll_ratio = state["bot_money"] / total_money
    else:
        bankroll_ratio = 0.5  # Default to equal if both broke

    # Risk penalty for large pots with weak hands
    risk_penalty = 0.0
    if pot > LARGE_POT_THRESHOLD and win_prob < LOW_WIN_PROB_THRESHOLD:
        risk_penalty -= RISK_PENALTY_LARGE_POT

    # Combined score
    score = (
        WEIGHT_WIN_PROB * win_prob
        + WEIGHT_EXPECTED_VALUE * max(ev_call, ev_raise) / (pot + 1)
        + WEIGHT_BANKROLL_RATIO * bankroll_ratio
        + risk_penalty
    )
    return score



# ===============================
# MINIMAX – OPPONENT = MINIMIZER
# ===============================

def minimax(
    state: Dict[str, Any],
    depth: int,
    alpha: float,
    beta: float,
    maximizing: bool
) -> float:
    """
    MiniMax algorithm with Alpha-Beta pruning for optimal decision making.
    
    Recursively explores the game tree to find the best move assuming both
    players play optimally. Uses alpha-beta pruning to skip unnecessary branches.
    
    Args:
        state: Current game state dictionary
        depth: Maximum depth to search (0 = evaluate immediately)
        alpha: Best value the maximizer can guarantee (for pruning)
        beta: Best value the minimizer can guarantee (for pruning)
        maximizing: True if bot's turn (maximize), False if opponent's turn (minimize)
    
    Returns:
        Score representing the value of the state for the bot
        
    Algorithm:
        - Bot (maximizer) wants to maximize the score
        - Opponent (minimizer) wants to minimize the bot's score
        - Alpha-beta pruning cuts off branches that won't affect the final decision
    """
    # Base cases: terminal state or max depth reached
    if state.get("terminal") or depth == 0:
        return evaluate_state(state)

    if maximizing:
        # Bot's turn: maximize score
        best = -1e9
        for action in get_possible_actions(state):
            s2 = simulate_action(state, action)
            val = minimax(s2, depth - 1, alpha, beta, False)
            best = max(best, val)
            alpha = max(alpha, best)
            if beta <= alpha:
                break  # Beta cutoff
        return best
    else:
        # Opponent's turn: minimize bot's score
        worst = 1e9
        for action in get_possible_actions(state):
            s2 = simulate_action(state, action)
            val = minimax(s2, depth - 1, alpha, beta, True)
            worst = min(worst, val)
            beta = min(beta, worst)
            if beta <= alpha:
                break  # Alpha cutoff
        return worst


# ===============================
# MAIN BOT DECISION
# ===============================

def bot_decision(
    state: Dict[str, Any],
    depth: int,
    mc_sims: int,
    log: Dict[str, Any]
) -> str:
    """
    AGGRESSIVE bot decision-making function with POSITION AWARENESS.
    
    New simplified strategy:
    1. Calculate win probability
    2. Adjust thresholds based on position (early = tighter, late = looser)
    3. ONLY FOLD if win_prob < threshold (25% base, adjusted for position)
    4. RAISE if win_prob > threshold (55% base, adjusted for position)
    5. CALL otherwise
    
    This ensures the bot plays aggressively and adapts to position.
    
    Args:
        state: Current game state dictionary
        depth: How many moves ahead to search
        mc_sims: Number of Monte Carlo simulations to run
        log: Statistics tracking dictionary
    
    Returns:
        Action string: 'fold', 'check', 'call', or 'raise'
    """
    start = time.time()

    # Scale simulations based on depth (deeper = more accurate)
    sims = min(MC_SIMS_MAX, max(MC_SIMS_MIN, int(mc_sims * (1 + MC_SIMS_DEPTH_MULTIPLIER * (depth - 1)))))
    win_prob = monte_carlo_win_prob(state["bot_hand"], state["community"], sims)
    log["win_probs"].append(win_prob)

    to_call = max(0, state["current_bet"] - state["bot_current_bet"])
    pot = state["pot"]

    # ===== POSITION AWARENESS =====
    # Determine position based on who is small blind
    # Small blind = early position (acts first post-flop) = play tighter
    # Big blind = late position (acts last post-flop) = play looser
    is_early_position = state.get("bot_is_small_blind", False)
    
    # Base thresholds
    fold_threshold = 0.25
    raise_threshold_no_bet = 0.50
    raise_threshold_facing_bet = 0.55
    
    # Adjust thresholds based on position
    if is_early_position:
        # Early position: play tighter (higher thresholds)
        fold_threshold += 0.05  # 30% in early position
        raise_threshold_no_bet += 0.05  # 55% to raise
        raise_threshold_facing_bet += 0.05  # 60% to raise facing bet
    else:
        # Late position: play looser (lower thresholds)
        fold_threshold -= 0.03  # 22% in late position
        raise_threshold_no_bet -= 0.03  # 47% to raise
        raise_threshold_facing_bet -= 0.03  # 52% to raise facing bet

    # ===== SIMPLIFIED AGGRESSIVE STRATEGY =====
    
    # If no one has bet yet
    if state["current_bet"] == 0:
        # Raise with any decent hand (adjusted for position)
        if win_prob >= raise_threshold_no_bet:
            action = "raise"
        else:
            action = "check"
    
    # Someone has bet - decide whether to fold/call/raise
    else:
        # FOLD THRESHOLD: Only fold trash (adjusted for position)
        if win_prob < fold_threshold:
            action = "fold"
        
        # RAISE THRESHOLD: Raise with decent hands (adjusted for position)
        elif win_prob >= raise_threshold_facing_bet:
            # Use MiniMax to decide if raising is better than calling
            call_state = simulate_action(state, "call")
            call_value = minimax(call_state, depth - 1, -1e9, 1e9, False)
            
            raise_state = simulate_action(state, "raise")
            raise_value = minimax(raise_state, depth - 1, -1e9, 1e9, False)
            
            # Raise if it's better than calling
            if raise_value > call_value - 0.05:  # Small threshold
                action = "raise"
            else:
                action = "call"
        
        # BLUFF ZONE: Semi-bluff with medium-weak hands (30-45% equity)
        elif BLUFF_MIN_WIN_PROB <= win_prob < BLUFF_MAX_WIN_PROB:
            # Calculate bluff frequency based on situation
            bluff_freq = BLUFF_BASE_FREQUENCY
            
            # Bluff more in late position (better position)
            if not is_early_position:
                bluff_freq += BLUFF_LATE_POSITION_BONUS
            
            # Bluff less in large pots (more risk)
            if pot > BLUFF_LARGE_POT_SIZE:
                bluff_freq -= BLUFF_LARGE_POT_PENALTY
            
            # Decide whether to bluff
            import random
            if random.random() < bluff_freq:
                action = "raise"  # BLUFF!
            else:
                action = "call"  # Not this time
        
        # CALL ZONE: Weak-medium hands - always call
        else:
            action = "call"

    # ---- Update statistics ----
    log["decisions"] += 1
    log["decision_times"].append(time.time() - start)
    if action == "fold":
        log["folds"] += 1
    elif action == "call":
        log["calls"] += 1
    elif action == "raise":
        log["raises"] += 1
    else:
        log["checks"] += 1

    return action



# ===============================
# WRAPPER FUNCTION
# ===============================

def bot_decision_wrapper(game: Any, bot_player: Any) -> str:
    """
    Wrapper function to convert game objects into state dictionary for bot_decision.
    
    This function bridges the gap between the game engine's object-oriented
    representation and the bot's dictionary-based state representation.
    
    Args:
        game: Game object containing current game state
        bot_player: Player object representing the bot
    
    Returns:
        Bot's chosen action as a string
    """
    # Find opponent player
    opp = next(p for p in game.players if p is not bot_player)
    
    # Determine bot's position
    # In 2-player: dealer (button) is small blind, other is big blind
    # Small blind acts first post-flop = early position
    bot_is_small_blind = (bot_player == game.players[0])  # First player is small blind

    # Convert game objects to state dictionary
    state = {
        "bot_hand": bot_player.hand.copy(),
        "community": game.community.copy(),
        "pot": game.pot,
        "current_bet": game.current_bet,
        "bot_money": bot_player.money,
        "opp_money": opp.money,
        "bot_current_bet": bot_player.current_bet,
        "raise_amount": DEFAULT_RAISE_AMOUNT,  # Fallback default
        "terminal": False,
        "bot_is_small_blind": bot_is_small_blind,  # Position tracking
    }
    
    # Quick win prob estimate for bet sizing (using fewer sims for speed)
    quick_sims = min(100, bot_player.mc_sims // 4)
    quick_win_prob = monte_carlo_win_prob(state["bot_hand"], state["community"], quick_sims)
    
    # Calculate dynamic bet size based on hand strength
    dynamic_bet = calculate_bet_size(
        win_prob=quick_win_prob,
        pot=game.pot,
        current_bet=game.current_bet,
        bot_money=bot_player.money,
        community_cards=len(game.community)
    )
    
    # Store dynamic bet in state for use in decision making
    state["dynamic_raise"] = dynamic_bet

    return bot_decision(
        state,
        depth=bot_player.depth,
        mc_sims=bot_player.mc_sims,
        log=bot_player.bot_log,
    )
