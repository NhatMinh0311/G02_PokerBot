import random
import copy
from treys import Evaluator, Deck, Card

import time

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

# -------------------------
# Monte Carlo evaluator setup

evaluator = Evaluator()

# -------------------------
# Monte Carlo win probability
# -------------------------
def monte_carlo_win_prob(bot_hand, community, n_sim=200):
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
        # no bet currently
        actions += ['check', 'raise']  # fold is allowed but unusual
    else:
        # there is a bet to match
        actions += ['call', 'raise', 'fold']
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
    Returns a numeric score (higher better for bot)
    """
    bot_hand = state['bot_hand']
    comm = state['community']
    # Quick MC estimate
    win_prob = monte_carlo_win_prob(bot_hand, comm, n_sim=mc_sims)

    # Pot odds / risk metric: expected gain if call now roughly win_prob * pot - (1-win_prob)*call_amount
    to_call = max(0, state['current_bet'] - state['bot_current_bet'])
    # approximate expected value of calling (normalized)
    ev_call = win_prob * state['pot'] - (1 - win_prob) * to_call

    # money balance factor
    money_factor = state['bot_money'] / (state['bot_money'] + state['opp_money'] + 1)

    # combine into score: emphasize EV for profit
    score = 0.4 * win_prob + 0.5 * (ev_call / (state['pot'] + 1)) + 0.1 * money_factor
    return score


# -------------------------
# MiniMax with alpha-beta
# -------------------------
def minimax(state, depth, alpha, beta, maximizing_player):
    # terminal check: fold winner
    if state.get('terminal', False) or depth == 0:
        return evaluate_state(state)

    if maximizing_player:
        max_eval = -float('inf')
        for action in get_possible_actions(state, actor='bot'):
            new_state = simulate_action(state, action, actor='bot')
            # If fold terminal, evaluate directly
            if new_state.get('terminal'):
                eval_v = evaluate_state(new_state)
            else:
                eval_v = minimax(new_state, depth - 1, alpha, beta, False)
            max_eval = max(max_eval, eval_v)
            alpha = max(alpha, eval_v)
            if beta <= alpha:
                break
        return max_eval
    else:
        # Opponent plays randomly: average the evaluations over possible actions
        total_eval = 0.0
        count = 0
        for action in get_possible_actions(state, actor='opp'):
            new_state = simulate_action(state, action, actor='opp')
            if new_state.get('terminal'):
                eval_v = evaluate_state(new_state)
            else:
                eval_v = minimax(new_state, depth - 1, alpha, beta, True)
            total_eval += eval_v
            count += 1
        if count > 0:
            return total_eval / count
        else:
            return 0


# -------------------------
# Main decision wrapper
# -------------------------
def bot_decision(state, depth=3, mc_sims=150, log=None):
    if log is None:
        log = BOT_LOG_TEMPLATE
    start = time.time()
    """
    state: dict with fields:
      - bot_hand (list ints), community (list ints), pot, current_bet,
      - bot_money, opp_money, bot_current_bet, opp_current_bet
    Returns one of: 'fold','check','call','raise'
    """
    # compute candidate actions
    candidates = get_possible_actions(state, actor='bot')
    best = None
    best_score = -float('inf')

    # attach montecarlo sims parameter to evaluate_state via closure if needed
    for action in candidates:
        s2 = simulate_action(state, action, actor='bot')
        # after simulate, run minimax (opponent to move)
        score = minimax(s2, depth - 1, -float('inf'), float('inf'), False)
        # tie-breaker prefer aggressive actions if scores close
        if score > best_score:
            best_score = score
            best = action

    # map 'check' vs 'call' preference: if both possible but call slightly better, pick call
    win_prob = monte_carlo_win_prob(state['bot_hand'], state['community'], n_sim=mc_sims)
    log["win_probs"].append(win_prob)

    candidates = get_possible_actions(state, actor='bot')
    # Maximize profit: fold if win_prob < threshold or EV negative
    fold_threshold = 0.65 - (depth - 1) * 0.05  # depth cao fold ít hơn
    to_call = max(0, state['current_bet'] - state['bot_current_bet'])
    ev_call = win_prob * state['pot'] - (1 - win_prob) * to_call
    if win_prob < fold_threshold or ev_call < 0:
        pass  # allow fold
    else:
        candidates = [c for c in candidates if c != 'fold']

    best, best_score = None, -float('inf')

    for action in candidates:
        s2 = simulate_action(state, action, actor='bot')
        score = minimax(s2, depth - 1, -float('inf'), float('inf'), False)
        # Bluff rate increases with depth for smarter play
        bluff_rate = 0.02 + (depth - 1) * 0.02
        bluff_bonus = 0.1 + (depth - 1) * 0.05  # depth cao bluff mạnh hơn
        if action == 'raise' and random.random() < bluff_rate:
            score += bluff_bonus
        # Remove pre-flop bonus for profit focus
        if score > best_score:
            best, best_score = action, score

    log["decisions"] += 1
    log["decision_times"].append(time.time() - start)
    log[best + "s"] = log.get(best + "s", 0) + 1
    return best


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

    # Quick win prob estimate for raise amount
    quick_win_prob = monte_carlo_win_prob(bot_player.hand, game.community, n_sim=bot_player.mc_sims // 10)
    # Calculate raise amount based on win prob and pot, scaled by depth
    depth_factor = bot_player.depth / 3.0  # depth 3 = 1, depth cao >1
    base_raise = max(5, int(quick_win_prob * 20 * depth_factor))
    pot_based = game.pot // 4 + 5
    raise_amount = min(base_raise, pot_based, bot_player.money // 2)  # cap at half money

    state = {
        'bot_hand': bot_player.hand.copy(),
        'community': game.community.copy(),
        'pot': game.pot,
        'current_bet': game.current_bet,
        'bot_money': bot_player.money,
        'opp_money': other.money,
        'bot_current_bet': bot_player.current_bet,
        'opp_current_bet': other.current_bet,
        'raise_amount': raise_amount,
        'terminal': False,
    }

    action = bot_decision(state, depth=bot_player.depth, mc_sims=bot_player.mc_sims, log=bot_player.bot_log)
    return action