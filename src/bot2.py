import random
import copy
from treys import Evaluator, Deck, Card

import time

BOT_LOG = {
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

# -------------------------
# Monte Carlo evaluator setup

evaluator = Evaluator()

# -------------------------
# Monte Carlo win probability
# -------------------------
def monte_carlo_win_prob(bot_hand, community, n_sim=800):
    """
    bot_hand: list of 2 treys-int cards
    community: list of 0..5 treys-int cards (current community on table)
    Returns estimated probability bot wins (ties count as 0.5)
    """
    # prepare deck
    deck = Deck()              # deck.cards is list of ints
    used = set(bot_hand + community)
    # remove used cards from deck
    deck_cards = [c for c in deck.cards if c not in used]
    wins = 0.0
    sims = n_sim

    for _ in range(sims):
        deck_copy = deck_cards.copy()
        random.shuffle(deck_copy)

        # opponent two cards
        opp_hand = [deck_copy.pop(), deck_copy.pop()]

        # fill community to 5
        sim_community = community.copy()
        while len(sim_community) < 5:
            sim_community.append(deck_copy.pop())

        bot_score = evaluator.evaluate(sim_community, bot_hand)
        opp_score = evaluator.evaluate(sim_community, opp_hand)
        if bot_score < opp_score:
            wins += 1.0
        elif bot_score == opp_score:
            wins += 0.5

    return wins / sims


# -------------------------
# State helpers & simulation
# -------------------------
DEFAULT_RAISE = 5

def get_possible_actions(state, actor='bot'):
    """
    state keys: bot_money, opp_money, pot, current_bet, bot_current_bet, opp_current_bet, community, bot_hand
    Return list of actions allowed: 'fold','check','call','raise'
    """
    actions = []
    # determine actor-specific bet amounts
    if actor == 'bot':
        my_cur = state['bot_current_bet']
    else:
        my_cur = state['opp_current_bet']

    if state['current_bet'] == 0:
        # no bet currently - only check or raise, NO FOLD when no one has bet
        actions += ['check', 'raise']
    else:
        # there is a bet to match - can fold, call, or raise
        actions += ['fold', 'call', 'raise']
    return actions


def simulate_action(state, action, actor='bot'):
    """
    Return a new state (deep copy) after applying action by actor.
    actor: 'bot' or 'opp'
    """
    s = copy.deepcopy(state)
    raise_amt = s.get('raise_amount', DEFAULT_RAISE)

    if action == 'fold':
        # if actor folds, the other side wins immediately
        s['terminal'] = True
        s['winner'] = 'opp' if actor == 'bot' else 'bot'
        return s

    if action == 'check':
        # no money exchange; nothing changes except turn passes
        return s

    if action == 'call':
        to_call = s['current_bet'] - (s['bot_current_bet'] if actor == 'bot' else s['opp_current_bet'])
        to_call = max(0, to_call)
        if actor == 'bot':
            taken = min(to_call, s['bot_money'])
            s['bot_money'] -= taken
            s['bot_current_bet'] += taken
        else:
            taken = min(to_call, s['opp_money'])
            s['opp_money'] -= taken
            s['opp_current_bet'] += taken
        s['pot'] += taken
        # after call normally current_bet stays same, not reset here (caller has matched)
        return s

    if action == 'raise':
        # new total bet = current_bet + raise_amt (simple fixed raise)
        new_total = s['current_bet'] + raise_amt
        if actor == 'bot':
            diff = new_total - s['bot_current_bet']
            diff = max(0, diff)
            diff = min(diff, s['bot_money'])
            s['bot_money'] -= diff
            s['bot_current_bet'] += diff
        else:
            diff = new_total - s['opp_current_bet']
            diff = max(0, diff)
            diff = min(diff, s['opp_money'])
            s['opp_money'] -= diff
            s['opp_current_bet'] += diff
        s['pot'] += diff
        s['current_bet'] = max(s['current_bet'], new_total)
        # mark that a raise happened; game continues
        return s

    return s


# -------------------------
# Evaluation / utility
# -------------------------
def evaluate_state(state, mc_sims=100):
    """
    A heuristic evaluation:
    - Use monte carlo win prob as base
    - Combine with money factors and pot odds
    - Compare with fold value (losing current bet)
    Returns a numeric score (higher better for bot)
    """
    bot_hand = state['bot_hand']
    comm = state['community']
    # Quick MC estimate
    win_prob = monte_carlo_win_prob(bot_hand, comm, n_sim=mc_sims)

    # Pot odds / risk metric: expected gain if call now roughly win_prob * pot - (1-win_prob)*call_amount
    to_call = max(0, state['current_bet'] - state['bot_current_bet'])
    
    # Explicit fold value: if we fold now, we lose what we've already bet this round
    fold_value = -state['bot_current_bet'] * 0.5  # Lose invested chips at this stage
    
    # Expected value of calling 
    if to_call > 0:
        ev_call = win_prob * (state['pot'] + to_call) - (1 - win_prob) * to_call
    else:
        ev_call = win_prob * state['pot']  # No cost to call if already matched

    # money balance factor
    money_factor = state['bot_money'] / (state['bot_money'] + state['opp_money'] + 1)

    # combine into score, but floor it vs fold_value
    score = 0.6 * win_prob + 0.3 * (ev_call / (state['pot'] + 1)) + 0.1 * money_factor
    
    # If EV is really bad (negative) and fold preserves chips, prefer fold
    if ev_call < -2 and to_call > state['bot_money'] * 0.3:
        # If calling would be very expensive relative to chip stack and negative EV, lean fold
        score = max(score, fold_value + 2)  # Make fold more attractive
    
    return score


# -------------------------
# EV-based decision logic (replaces minimax)
# -------------------------
def calculate_action_ev(action, state):
    """
    Calculate expected value of an action WITHOUT deep minimax search.
    Uses: win probability + pot odds + bankroll awareness.
    
    Returns: (action, ev_value) for comparison
    """
    to_call = max(0, state['current_bet'] - state['bot_current_bet'])
    pot = state['pot']
    win_prob = monte_carlo_win_prob(state['bot_hand'], state['community'], n_sim=200)
    
    if action == 'fold':
        # EV of fold = 0 (you give up, lose what you bet this round)
        # Small penalty for the sunk cost/opportunity
        return -state['bot_current_bet'] * 0.15
    
    elif action == 'check':
        # EV of check = 0 (no money changes) + potential upside
        # Favorable if win_prob is decent and no bet to match
        if to_call == 0:
            return win_prob * 0.5  # Slight positive if we check and likely win
        else:
            return -float('inf')  # Can't check if there's a bet to match
    
    elif action == 'call':
        # EV of call = win_prob * (pot + to_call) - (1 - win_prob) * to_call
        # Simplified: win_prob * total_pot - (1 - win_prob) * call_cost
        if to_call == 0:
            return 0  # Calling when matched = neutral
        
        ev = win_prob * (pot + to_call) - (1 - win_prob) * to_call
        
        # Bankroll preservation: if call is expensive relative to stack, reduce EV
        if state['bot_money'] > 0:
            call_ratio = to_call / state['bot_money']
            if call_ratio > 0.20:  # Calling more than 20% of remaining stack is risky
                risk_penalty = call_ratio * 15  # Penalty for high-risk calls
                ev -= risk_penalty
            if call_ratio > 0.40:  # Calling >40% is very risky
                ev -= 40  # Severe penalty
        
        # Pot odds check: only call weak hands if pot odds are excellent
        if ev < 2 and win_prob < 0.40:
            ev -= 5  # Slight penalty for marginal calls with weak hands
        
        return ev
    
    elif action == 'raise':
        # EV of raise = win_prob * (pot + 2*raise_amount) - (1 - win_prob) * raise_amount
        raise_amount = DEFAULT_RAISE
        new_total = state['current_bet'] + raise_amount
        if state['bot_current_bet'] >= new_total:
            return -float('inf')  # Can't raise if already bet that much
        
        diff_to_raise = new_total - state['bot_current_bet']
        if diff_to_raise > state['bot_money']:
            return -float('inf')  # Can't raise with insufficient chips
        
        ev = win_prob * (pot + diff_to_raise + DEFAULT_RAISE) - (1 - win_prob) * diff_to_raise
        
        # STRONG penalty for raising with weak hands
        # Only raise with >60% win probability to avoid bluffing too much
        if win_prob < 0.60:
            ev -= 20  # Big penalty for weak raises
        
        # Additional penalty if already significant money in pot
        if to_call > 0 and win_prob < 0.65:
            ev -= 15  # Don't re-raise with marginal hands
        
        return ev
    
    return -float('inf')

# -------------------------
# Main decision wrapper
# -------------------------
def bot_decision(state, depth=3, mc_sims=800):
    """
    NEW EV-BASED DECISION (replaces minimax):
    
    Makes decisions based on:
    1. Monte-Carlo win probability estimation
    2. Pot odds calculation (EV of each action)
    3. Bankroll preservation (avoid risking too much)
    4. Stack-aware bet sizing
    
    This bot will:
    - FOLD bad hands with negative EV
    - CALL medium hands with positive EV
    - RAISE strong hands with high win probability
    - CHECK when no bet and decent hand strength
    """
    start = time.time()
    
    # Calculate win probability once
    win_prob = monte_carlo_win_prob(state['bot_hand'], state['community'], n_sim=mc_sims)
    BOT_LOG["win_probs"].append(win_prob)
    
    # Get available actions
    candidates = get_possible_actions(state, actor='bot')
    
    # Calculate EV for each candidate action
    action_evs = {}
    for action in candidates:
        ev = calculate_action_ev(action, state)
        action_evs[action] = ev
    
    # Choose action with highest EV
    best_action = max(action_evs.items(), key=lambda x: x[1])[0]
    
    # Log statistics
    BOT_LOG["decisions"] += 1
    BOT_LOG["decision_times"].append(time.time() - start)
    BOT_LOG[best_action + "s"] = BOT_LOG.get(best_action + "s", 0) + 1
    
    return best_action


# -------------------------
# wrapper to be used in betting_round
# -------------------------
def bot_decision_wrapper(game, bot_player):
    """
    Build state from game object and call bot_decision.
    game: your PokerGame instance
    bot_player: Player instance (bot)
    """
    # find opponent
    other = next(p for p in game.players if p is not bot_player)

    state = {
        'bot_hand': bot_player.hand.copy(),
        'community': game.community.copy(),
        'pot': game.pot,
        'current_bet': game.current_bet,
        'bot_money': bot_player.money,
        'opp_money': other.money,
        'bot_current_bet': bot_player.current_bet,
        'opp_current_bet': other.current_bet,
        'raise_amount': DEFAULT_RAISE,
        'terminal': False,
    }

    action = bot_decision(state, depth=10, mc_sims=120)
    return action