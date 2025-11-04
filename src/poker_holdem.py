import random
from collections import Counter
from itertools import combinations

RANKS = '23456789TJQKA'
SUITS = '♠♥♦♣'
RANK_VALUE = {r: i + 2 for i, r in enumerate(RANKS)}  # 2 -> 2, ... A -> 14

HAND_NAMES = {
    8: "Straight Flush",
    7: "Four of a Kind",
    6: "Full House", 
    5: "Flush",
    4: "Straight",
    3: "Three of a Kind", 
    2: "Two Pair",
    1: "One Pair",
    0: "High Card",
}

def create_deck():
    return [r + s for r in RANKS for s in SUITS]

def deal(deck, n):
    return [deck.pop() for _ in range(n)]

def rank_to_value(card):
    return RANK_VALUE[card[0]]

def is_flush(cards):
    suits = [c[1] for c in cards]
    return len(set(suits)) == 1

def is_straight(values):
    # values: list of rank ints (no duplicates) sorted desc
    if not values:
        return False, None
    vals = sorted(set(values), reverse=True)
    # handle wheel (A-2-3-4-5)
    if 14 in vals:
        vals.append(1)
    consec = 1
    best_high = None
    for i in range(len(vals) - 1):
        if vals[i] - vals[i + 1] == 1:
            consec += 1
        else:
            consec = 1
        if consec >= 5:
            best_high = vals[i - 3]  # highest card of the straight
            break
    # check windows of size 5
    if len(vals) >= 5 and best_high is None:
        for i in range(len(vals) - 4):
            window = vals[i:i + 5]
            if window[0] - window[-1] == 4 and len(window) == 5:
                best_high = window[0]
                break
    if best_high is None and len(vals) >= 5:
        # special check for A-5 straight (wheel)
        if set([14, 5, 4, 3, 2]).issubset(set(values)):
            best_high = 5
    return (best_high is not None), best_high

def evaluate_5(cards):
    # Evaluate a 5-card hand. Return tuple (type, tiebreakers...)
    vals = sorted([rank_to_value(c) for c in cards], reverse=True)
    counts = Counter(vals)
    counts_by_freq = sorted(((freq, val) for val, freq in counts.items()), reverse=True)
    freqs = sorted(counts.values(), reverse=True)
    flush = is_flush(cards)
    straight, high_straight = is_straight(vals)
    if straight and flush:
        return (8, high_straight)
    if freqs[0] == 4:
        # four of a kind: (7, quad_rank, kicker)
        quad = counts_by_freq[0][1]
        kicker = max(v for v in vals if v != quad)
        return (7, quad, kicker)
    if freqs[0] == 3 and len(freqs) > 1 and freqs[1] == 2:
        # full house: (6, trip_rank, pair_rank)
        trip = counts_by_freq[0][1]
        pair = counts_by_freq[1][1]
        return (6, trip, pair)
    if flush:
        return (5, ) + tuple(vals)
    if straight:
        return (4, high_straight)
    if freqs[0] == 3:
        trip = counts_by_freq[0][1]
        kickers = sorted((v for v in vals if v != trip), reverse=True)
        return (3, trip) + tuple(kickers)
    if freqs[0] == 2 and len(freqs) > 1 and freqs[1] == 2:
        # two pair: (2, high_pair, low_pair, kicker)
        pair_high = counts_by_freq[0][1]
        pair_low = counts_by_freq[1][1]
        kicker = max(v for v in vals if v != pair_high and v != pair_low)
        return (2, pair_high, pair_low, kicker)
    if freqs[0] == 2:
        pair = counts_by_freq[0][1]
        kickers = sorted((v for v in vals if v != pair), reverse=True)
        return (1, pair) + tuple(kickers)
    return (0, ) + tuple(vals)

def best_hand_rank(seven_cards):
    # choose best 5-card combination from up to 7 cards
    best = None
    for comb in combinations(seven_cards, 5):
        rank = evaluate_5(comb)
        if best is None or rank > best:
            best = rank
    return best

def card_list_to_str(cards):
    return ' '.join(cards)

def pretty_rank(rank):
    t = HAND_NAMES[rank[0]]
    extras = rank[1:]
    return f"{t} {extras}"

class TexasHoldemGame:
    def __init__(self):
        self.player_chips = 1000
        self.bot_chips = 1000
        self.pot = 0
        self.min_bet = 20
        
    def get_player_action(self, stage):
        while True:
            print(f"\nChips của bạn: {self.player_chips}")
            print(f"Chips của bot: {self.bot_chips}")
            print(f"Pot: {self.pot}")
            action = input(f"Lượt của bạn ({stage}) - Chọn: (f)old, (c)all, (r)aise: ").strip().lower()
            
            if action == 'f':
                return 'fold', 0
            elif action == 'c':
                return 'call', self.min_bet
            elif action == 'r':
                while True:
                    try:
                        amount = int(input(f"Số chips muốn raise (tối thiểu {self.min_bet * 2}): "))
                        if amount >= self.min_bet * 2 and amount <= self.player_chips:
                            return 'raise', amount
                        print("Số chips không hợp lệ!")
                    except ValueError:
                        print("Vui lòng nhập số!")
            print("Lựa chọn không hợp lệ!")

    def bot_action(self, bot_hand, community, player_bet):
        if not community:  # Pre-flop
            hand_strength = sum(rank_to_value(card[0]) for card in bot_hand) / 28.0  # Max = 28 (AA)
        else:
            bot_rank = best_hand_rank(bot_hand + community)
            hand_strength = bot_rank[0] / 8.0  # Chuẩn hóa theo hand ranking (0-8)
        
        if hand_strength > 0.7:  # Bài rất mạnh
            if random.random() < 0.7:  # 70% raise
                return 'raise', min(player_bet * 2, self.bot_chips)
            return 'call', player_bet
        elif hand_strength > 0.4:  # Bài trung bình
            if random.random() < 0.3:  # 30% raise
                return 'raise', min(player_bet * 2, self.bot_chips)
            return 'call', player_bet
        else:  # Bài yếu
            if player_bet > self.min_bet * 2:  # Nếu người chơi raise cao
                return 'fold', 0
            return 'call', player_bet

    def run_game(self):
        print("=== Texas Hold'em: You vs Bot ===")
        print("Ván bài bắt đầu...")
        print()

        # Khởi tạo bộ bài và chia bài
        deck = create_deck()
        random.shuffle(deck)
        
        # Chia bài cho người chơi và bot
        player_hole = deal(deck, 2)
        bot_hole = deal(deck, 2)
        
        print(f"Bài của bạn: {card_list_to_str(player_hole)}")
        print(f"Bài của bot: ?? ??")
        
        # Pre-flop betting
        action, bet = self.get_player_action("Pre-flop")
        if action == 'fold':
            self.bot_chips += self.pot
            print("Bạn đã fold. Bot thắng pot!")
            return
        
        self.pot += bet
        self.player_chips -= bet
        
        bot_action, bot_bet = self.bot_action(bot_hole, [], bet)
        if bot_action == 'fold':
            self.player_chips += self.pot
            print("Bot đã fold. Bạn thắng pot!")
            return
        
        self.pot += bot_bet
        self.bot_chips -= bot_bet
        print(f"Bot {bot_action} với {bot_bet} chips")
        
        # Flop
        deal(deck, 1)  # burn
        flop = deal(deck, 3)
        print("\nFLOP:")
        print(f"Bài trên bàn: {card_list_to_str(flop)}")
        
        # Flop betting
        action, bet = self.get_player_action("Flop")
        if action == 'fold':
            self.bot_chips += self.pot
            print("Bạn đã fold. Bot thắng pot!")
            return
            
        self.pot += bet
        self.player_chips -= bet
        
        bot_action, bot_bet = self.bot_action(bot_hole, flop, bet)
        if bot_action == 'fold':
            self.player_chips += self.pot
            print("Bot đã fold. Bạn thắng pot!")
            return
            
        self.pot += bot_bet
        self.bot_chips -= bot_bet
        print(f"Bot {bot_action} với {bot_bet} chips")
        
        # Turn
        deal(deck, 1)  # burn
        turn = deal(deck, 1)
        print("\nTURN:")
        print(f"Bài trên bàn: {card_list_to_str(flop + turn)}")
        
        # Turn betting
        action, bet = self.get_player_action("Turn")
        if action == 'fold':
            self.bot_chips += self.pot
            print("Bạn đã fold. Bot thắng pot!")
            return
            
        self.pot += bet
        self.player_chips -= bet
        
        bot_action, bot_bet = self.bot_action(bot_hole, flop + turn, bet)
        if bot_action == 'fold':
            self.player_chips += self.pot
            print("Bot đã fold. Bạn thắng pot!")
            return
            
        self.pot += bot_bet
        self.bot_chips -= bot_bet
        print(f"Bot {bot_action} với {bot_bet} chips")
        
        # River
        deal(deck, 1)  # burn
        river = deal(deck, 1)
        print("\nRIVER:")
        community = flop + turn + river
        print(f"Bài trên bàn: {card_list_to_str(community)}")
        
        # River betting
        action, bet = self.get_player_action("River")
        if action == 'fold':
            self.bot_chips += self.pot
            print("Bạn đã fold. Bot thắng pot!")
            return
            
        self.pot += bet
        self.player_chips -= bet
        
        bot_action, bot_bet = self.bot_action(bot_hole, community, bet)
        if bot_action == 'fold':
            self.player_chips += self.pot
            print("Bot đã fold. Bạn thắng pot!")
            return
            
        self.pot += bot_bet
        self.bot_chips -= bot_bet
        print(f"Bot {bot_action} với {bot_bet} chips")
        
        # Showdown
        print("\nSHOWDOWN:")
        print(f"Bài của bạn: {card_list_to_str(player_hole)}")
        print(f"Bài của bot: {card_list_to_str(bot_hole)}")
        
        # Tính điểm và xác định người thắng
        player_rank = best_hand_rank(player_hole + community)
        bot_rank = best_hand_rank(bot_hole + community)
        
        print(f"\nBài của bạn: {pretty_rank(player_rank)}")
        print(f"Bài của bot: {pretty_rank(bot_rank)}")
        
        if player_rank > bot_rank:
            print("BẠN THẮNG! 🎉")
            self.player_chips += self.pot
        elif player_rank < bot_rank:
            print("BOT THẮNG! 🤖")
            self.bot_chips += self.pot
        else:
            print("HÒA! 🤝")
            split_pot = self.pot // 2
            self.player_chips += split_pot
            self.bot_chips += split_pot
        
        self.pot = 0

def main():
    while True:
        game = TexasHoldemGame()
        game.run_game()
        print(f"\nSố chips còn lại - Bạn: {game.player_chips}, Bot: {game.bot_chips}")
        play_again = input("\nChơi tiếp? (y/n): ").strip().lower()
        if play_again != 'y':
            break
    print("\nCảm ơn đã chơi!")

if __name__ == "__main__":
    main()