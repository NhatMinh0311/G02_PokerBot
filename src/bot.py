import random
import copy
import time
from treys import Evaluator, Deck

# ===============================
# BOT LOG TEMPLATE
# ===============================
BOT_LOG_TEMPLATE = {
    "decisions": 0,
    "folds": 0,
    "raises": 0,
    "calls": 0,
    "checks": 0,
    "decision_times": [],
    "win_probs": [],
    "rounds": {              # ✅ thêm lại để app.py không lỗi
        "total": 0,
        "bot_wins": 0,
        "player_wins": 0,
        "ties": 0
    }
}


evaluator = Evaluator()
FULL_DECK = Deck()
DEFAULT_RAISE = 5


# ===============================
# MONTE CARLO WIN PROB
# ===============================
def monte_carlo_win_prob(bot_hand, community, n_sim=200):
    used = set(bot_hand + community)
    deck_cards = [c for c in FULL_DECK.cards if c not in used]

    wins = 0.0
    n_sim = max(1, n_sim)

    for _ in range(n_sim):
        random.shuffle(deck_cards)
        opp_hand = deck_cards[:2]

        sim_comm = community.copy()
        idx = 2
        while len(sim_comm) < 5:
            sim_comm.append(deck_cards[idx])
            idx += 1

        b = evaluator.evaluate(sim_comm, bot_hand)
        o = evaluator.evaluate(sim_comm, opp_hand)

        if b < o:
            wins += 1
        elif b == o:
            wins += 0.5

    return wins / n_sim


# ===============================
# ACTION SPACE
# ===============================
def get_possible_actions(state):
    if state["current_bet"] == 0:
        return ["check", "raise"]
    return ["fold", "call", "raise"]


# ===============================
# SIMULATE ACTION
# ===============================
def simulate_action(state, action, actor="bot"):
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
def evaluate_state(state, mc_sims=120):
    win_prob = monte_carlo_win_prob(state["bot_hand"], state["community"], mc_sims)

    to_call = max(0, state["current_bet"] - state["bot_current_bet"])
    pot = state["pot"]
    raise_amt = state["raise_amount"]

    # EV(call): nếu call xong, pot tăng thêm to_call
    ev_call = win_prob * (pot + to_call) - (1 - win_prob) * to_call

    # EV(raise) worst-case: assume opp calls raise
    ev_raise = win_prob * (pot + to_call + raise_amt) - (1 - win_prob) * (to_call + raise_amt)

    bankroll_ratio = state["bot_money"] / (state["bot_money"] + state["opp_money"] + 1)

    # Penalty: nếu win_prob thấp mà đang all-in-ish / pot lớn, phạt mạnh hơn
    risk_penalty = 0.0
    if pot > 30 and win_prob < 0.45:
        risk_penalty -= 0.15

    score = (
        0.68 * win_prob
        + 0.25 * max(ev_call, ev_raise) / (pot + 1)
        + 0.07 * bankroll_ratio
        + risk_penalty
    )
    return score



# ===============================
# MINIMAX – OPPONENT = MINIMIZER
# ===============================
def minimax(state, depth, alpha, beta, maximizing):
    if state.get("terminal") or depth == 0:
        return evaluate_state(state)

    if maximizing:
        best = -1e9
        for a in get_possible_actions(state):
            s2 = simulate_action(state, a)
            val = minimax(s2, depth - 1, alpha, beta, False)
            best = max(best, val)
            alpha = max(alpha, best)
            if beta <= alpha:
                break
        return best
    else:
        # Opponent best-response (minimize bot EV)
        worst = 1e9
        for a in get_possible_actions(state):
            s2 = simulate_action(state, a)
            val = minimax(s2, depth - 1, alpha, beta, True)
            worst = min(worst, val)
            beta = min(beta, worst)
            if beta <= alpha:
                break
        return worst


# ===============================
# MAIN BOT DECISION
# ===============================
def bot_decision(state, depth, mc_sims, log):
    start = time.time()

    # Depth cao -> estimate tốt hơn chút, nhưng cap lại
    sims = min(350, max(80, int(mc_sims * (1 + 0.4 * (depth - 1)))))
    win_prob = monte_carlo_win_prob(state["bot_hand"], state["community"], sims)
    log["win_probs"].append(win_prob)

    to_call = max(0, state["current_bet"] - state["bot_current_bet"])
    pot = state["pot"]

    # Pot odds chuẩn
    pot_odds = to_call / (pot + to_call + 1e-9)

    # Margin: depth cao chắc hơn nhưng KHÔNG quá gắt
    margin = 0.02 + 0.01 * (depth - 1)   # depth=2 -> 0.03, depth=4 -> 0.05

    # ---- Nếu chưa có bet: mặc định check, chỉ raise khi bài đủ mạnh ----
    if state["current_bet"] == 0:
        # Raise value khi win_prob cao, còn lại check
        action = "raise" if win_prob >= (0.62 - 0.01 * (depth - 2)) else "check"
    else:
        # ---- Có bet: chống fold quá tay ----

        # Nếu call rất rẻ (blinds nhỏ), defend nhiều hơn
        cheap_defend = (to_call <= 5)

        # Điều kiện fold: win_prob thấp hơn pot_odds + margin,
        # nhưng nếu call rẻ thì nới lỏng
        fold_line = pot_odds + margin
        if cheap_defend:
            fold_line -= 0.05  # defend hơn khi rẻ

        if win_prob < fold_line:
            action = "fold"
        else:
            # chọn action bằng minimax
            best_action = "call"
            best_score = -1e9

            for a in get_possible_actions(state):
                # Không bluff raise với win_prob thấp
                if a == "raise" and win_prob < 0.58:
                    continue

                s2 = simulate_action(state, a)
                val = minimax(s2, depth - 1, -1e9, 1e9, False)

                # Phạt raise nhẹ nếu pot đã lớn mà win_prob không cao
                if a == "raise" and pot > 25 and win_prob < 0.62:
                    val -= 0.08

                if val > best_score:
                    best_score = val
                    best_action = a

            action = best_action

    # ---- LOG ----
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
# WRAPPER
# ===============================
def bot_decision_wrapper(game, bot_player):
    opp = next(p for p in game.players if p is not bot_player)

    state = {
        "bot_hand": bot_player.hand.copy(),
        "community": game.community.copy(),
        "pot": game.pot,
        "current_bet": game.current_bet,
        "bot_money": bot_player.money,
        "opp_money": opp.money,
        "bot_current_bet": bot_player.current_bet,
        "raise_amount": DEFAULT_RAISE,
        "terminal": False,
    }

    return bot_decision(
        state,
        depth=bot_player.depth,
        mc_sims=bot_player.mc_sims,
        log=bot_player.bot_log,
    )
