import random
import copy
from treys import Evaluator, Deck

import time

# Template lưu trữ thống kê hoạt động của bot
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

# Khởi tạo công cụ đánh giá tay poker
evaluator = Evaluator()

# Tính xác suất thắng bằng phương pháp Monte Carlo
def monte_carlo_win_prob(bot_hand, community, n_sim=200):
    deck = Deck()
    used = set(bot_hand + community)
    deck_cards = [c for c in deck.cards if c not in used]
    wins = 0.0

    # Chạy n_sim vòng mô phỏng
    for _ in range(n_sim):
        deck_copy = deck_cards.copy()
        random.shuffle(deck_copy)

        # Tạo tay đối thủ ngẫu nhiên
        opp_hand = [deck_copy.pop(), deck_copy.pop()]

        # Hoàn thành bộ bài cộng đồng
        sim_community = community.copy()
        while len(sim_community) < 5:
            sim_community.append(deck_copy.pop())

        # So sánh điểm số
        bot_score = evaluator.evaluate(sim_community, bot_hand)
        opp_score = evaluator.evaluate(sim_community, opp_hand)
        if bot_score < opp_score:
            wins += 1.0
        elif bot_score == opp_score:
            wins += 0.5

    return wins / n_sim


DEFAULT_RAISE = 5

# Lấy danh sách hành động có thể thực hiện
def get_possible_actions(state, actor='bot'):
    actions = []
    
    if actor == 'bot':
        current_bet = state['bot_current_bet']
    else:
        current_bet = state['opp_current_bet']

    # Nếu chưa có cược, có thể check hoặc raise
    # Nếu đã có cược, có thể call, raise, hoặc fold
    if state['current_bet'] == 0:
        actions += ['check', 'raise']
    else:
        actions += ['call', 'raise', 'fold']
    
    return actions


# Mô phỏng kết quả của một hành động
def simulate_action(state, action, actor='bot'):
    s = copy.deepcopy(state)
    raise_amt = s.get('raise_amount', DEFAULT_RAISE)

    # Fold: kết thúc trò chơi, đối thủ thắng
    if action == 'fold':
        s['terminal'] = True
        s['winner'] = 'opp' if actor == 'bot' else 'bot'
        return s

    # Check: không cược gì thêm
    if action == 'check':
        return s

    # Call: cược để ngang bằng cược hiện tại
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
        return s

    # Raise: tăng cược
    if action == 'raise':
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
        return s

    return s


# Đánh giá giá trị của trạng thái hiện tại
def evaluate_state(state, mc_sims=100):
    bot_hand = state['bot_hand']
    comm = state['community']
    # Tính xác suất thắng của bot
    win_prob = monte_carlo_win_prob(bot_hand, comm, n_sim=mc_sims)

    # Tính Expected Value của việc call
    to_call = max(0, state['current_bet'] - state['bot_current_bet'])
    ev_call = win_prob * state['pot'] - (1 - win_prob) * to_call

    # Tính tỷ lệ tiền so với đối thủ
    money_factor = state['bot_money'] / (state['bot_money'] + state['opp_money'] + 1)

    # Tính điểm theo công thức kết hợp
    score = 0.4 * win_prob + 0.5 * (ev_call / (state['pot'] + 1)) + 0.1 * money_factor
    return score


# Thuật toán Minimax với cắt tỉa Alpha-Beta
def minimax(state, depth, alpha, beta, maximizing_player):
    # Điều kiện dừng: trò chơi kết thúc hoặc đạt độ sâu tối đa
    if state.get('terminal', False) or depth == 0:
        return evaluate_state(state)

    if maximizing_player:
        # Bot tìm hành động tối đa hóa điểm
        max_eval = -float('inf')
        for action in get_possible_actions(state, actor='bot'):
            new_state = simulate_action(state, action, actor='bot')
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
        # Đối thủ chọn hành động trung bình (khó đoán)
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


# Hàm quyết định hành động chính của bot
def bot_decision(state, depth=3, mc_sims=150, log=None):
    if log is None:
        log = BOT_LOG_TEMPLATE
    
    start = time.time()
    
    candidates = get_possible_actions(state, actor='bot')
    win_prob = monte_carlo_win_prob(state['bot_hand'], state['community'], n_sim=mc_sims)
    log["win_probs"].append(win_prob)

    # Loại bỏ fold nếu xác suất thắng cao hoặc Expected Value dương
    fold_threshold = 0.65 - (depth - 1) * 0.05
    to_call = max(0, state['current_bet'] - state['bot_current_bet'])
    ev_call = win_prob * state['pot'] - (1 - win_prob) * to_call
    
    if win_prob < fold_threshold or ev_call < 0:
        pass
    else:
        candidates = [c for c in candidates if c != 'fold']

    # Tìm hành động tốt nhất bằng Minimax
    best, best_score = None, -float('inf')

    for action in candidates:
        s2 = simulate_action(state, action, actor='bot')
        score = minimax(s2, depth - 1, -float('inf'), float('inf'), False)
        
        # Thêm yếu tố ngẫu nhiên cho raise để tạo tính không lường trước
        if action == 'raise' and random.random() < 0.05:
            score += 0.2
        
        if score > best_score:
            best, best_score = action, score

    # Cập nhật log
    log["decisions"] += 1
    log["decision_times"].append(time.time() - start)
    log[best + "s"] = log.get(best + "s", 0) + 1
    
    return best


# Wrapper để gọi bot_decision từ trò chơi
def bot_decision_wrapper(game, bot_player):
    other = next(p for p in game.players if p is not bot_player)

    raise_amount = 5

    # Tạo state từ thông tin trò chơi
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
