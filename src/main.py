import random
from treys import Deck, Card, Evaluator
from bot import bot_decision_wrapper
import statistics
from bot import BOT_LOG
def compare_hands(cards1, cards2, community):
    """So sánh bài của hai người chơi (7 lá mỗi người = 2 riêng + 5 chung)"""
    evaluator = Evaluator()
    rank1 = evaluator.evaluate(community, cards1)
    rank2 = evaluator.evaluate(community, cards2)
    if rank1 < rank2:
        return 1
    elif rank1 > rank2:
        return -1
    return 0

# -----------------------------
# Player & Game Classes
# -----------------------------
class Player:
    def __init__(self, name, is_bot=False):
        self.name = name
        self.is_bot = is_bot
        self.money = 100
        self.hand = []
        self.folded = False
        self.current_bet = 0

    def reset(self):
        self.hand = []
        self.folded = False

    def bet(self, amount):
        if amount > self.money:
            amount = self.money
        self.money -= amount
        self.current_bet += amount
        return amount


class PokerGame:
    def __init__(self):
        self.players = [Player("You"), Player("Bot", is_bot=True)]
        self.deck = None
        self.community = []
        self.pot = 0
        self.current_bet = 0
        self.dealer_index = 0
        self.active_player_index = (self.dealer_index + 2) % len(self.players)
        self.is_pre_flop = True
    def create_deck(self):
        self.deck = Deck()

    def deal_hole_cards(self):
        for p in self.players:
            p.hand = self.deck.draw(2)

    def burn_card(self):
        if self.deck:
            self.deck.draw(1)

    def deal_flop(self):
        self.burn_card()
        self.community.extend(self.deck.draw(3))

    def deal_turn(self):
        self.burn_card()
        self.community.extend(self.deck.draw(1))

    def deal_river(self):
        self.burn_card()
        self.community.extend(self.deck.draw(1))

    def show_table(self, reveal_bot=False):
        print("\n--- TABLE ---")
        print(f"Community Cards: { Card.ints_to_pretty_str(self.community) }")
        for p in self.players:
            if p.is_bot and not reveal_bot:
                print(f"{p.name}: [?? ??]")
            else:
                print(f"{p.name}: {Card.ints_to_pretty_str(p.hand)}")

    def isEnded(self):
        return len([p for p in self.players if not p.folded]) <= 1

    def post_blinds(self):
        """Đặt small blind ($2) và big blind ($5), luân phiên mỗi ván."""
        small_blind = 2
        big_blind = 5

        small_blind_player = self.players[self.dealer_index % len(self.players)]
        big_blind_player = self.players[(self.dealer_index + 1) % len(self.players)]

        # Đặt blind
        self.pot += small_blind_player.bet(small_blind)
        small_blind_player.current_bet = small_blind

        self.pot += big_blind_player.bet(big_blind)
        big_blind_player.current_bet = big_blind

        self.current_bet = big_blind
        self.active_player_index = (self.dealer_index + 2) % len(self.players)  # Người chơi tiếp theo sau big blind
        print("\n--- BLINDS POSTED ---")
        print(f"{small_blind_player.name} (Small Blind): ${small_blind}")
        print(f"{big_blind_player.name} (Big Blind): ${big_blind}")
        print(f"Pot = ${self.pot}")

    def betting_round(self):
        print("\n=== Betting Round ===")

        # Đảm bảo current_bet mỗi người tồn tại
        for p in self.players:
            if not hasattr(p, "current_bet"):
                p.current_bet = 0
        last_raise_idx =  -1
        
        while True:
            start_player_idx = (last_raise_idx + 1) % len(self.players) if last_raise_idx != -1 else self.active_player_index
            is_end_round = True
            for i in range(len(self.players)):
                # Nếu còn 1 người duy nhất → kết thúc sớm
                if (self.isEnded()):
                    break
                p = self.players[(start_player_idx + i) % len(self.players)]
                if p.folded:
                    continue
                if last_raise_idx != -1 and (start_player_idx + i) % len(self.players) == last_raise_idx:
                    break
                can_check = (p.current_bet == self.current_bet)

                print(f"\n--- {p.name}'s Turn ---")
                print(f"Pot: ${self.pot} | Current Bet: ${self.current_bet}")

                

                # ========== BOT ==========
                if p.is_bot:
                    # roll = random.random()
                    # if can_check:
                    #     if roll < 0.1:
                    #         p.folded = True
                    #         print("🤖 Bot folds.")
                    #     elif roll < 0.3:
                    #         if self.current_bet == 0:
                    #             bet_amount = 5
                    #             self.current_bet += bet_amount
                    #             self.pot += p.bet(bet_amount)
                    #             print(f"🤖 Bot bets ${bet_amount}.")
                    #         else:
                    #             raise_amount = 5
                    #             new_bet = self.current_bet + raise_amount
                    #             diff = new_bet - p.current_bet
                    #             self.pot += p.bet(diff)
                    #             self.current_bet = new_bet
                    #             print(f"🤖 Bot raises to ${new_bet}.")
                    #         is_end_round = False
                    #         last_raise_idx = (start_player_idx + i) % len(self.players)
                    #         break
                    #     else:
                    #         print("🤖 Bot checks.")
                    # else:
                    #     # Bot phải phản ứng với bet
                    #     if roll < 0.2:
                    #         p.folded = True
                    #         print("🤖 Bot folds.")
                    #     elif roll < 0.8:
                    #         call_amount = self.current_bet - p.current_bet
                    #         self.pot += p.bet(call_amount)
                    #         #p.current_bet = self.current_bet
                    #         print(f"🤖 Bot calls ${call_amount}.")
                    #     else:
                    #         raise_amount = 5
                    #         new_bet = self.current_bet + raise_amount
                    #         diff = new_bet - p.current_bet
                    #         self.pot += p.bet(diff)
                    #         #p.current_bet = new_bet
                    #         self.current_bet = new_bet
                    #         print(f"🤖 Bot raises to ${new_bet}.")
                    #         is_end_round = False
                    #         last_raise_idx = (start_player_idx + i) % len(self.players)
                    #         break
                    action = bot_decision_wrapper(self, p)
                    print(f"🤖 Bot chooses: {action}")

                    if action == 'fold':
                        p.folded = True
                    elif action == 'check':
                        print("🤖 Bot checks.")
                    elif action == 'call':
                        call_amount = self.current_bet - p.current_bet
                        call_amount = max(0, call_amount)
                        self.pot += p.bet(call_amount)
                        #p.current_bet = self.current_bet
                        print(f"🤖 Bot calls ${call_amount}.")
                    elif action == 'raise':
                        raise_amount = 5
                        new_total = self.current_bet + raise_amount
                        diff = new_total - p.current_bet
                        diff = max(0, diff)
                        self.pot += p.bet(diff)
                        #p.current_bet = new_total
                        self.current_bet = new_total
                        print(f"🤖 Bot raises to ${new_total}.")
                        is_end_round = False
                        last_raise_idx = (start_player_idx + i) % len(self.players)
                        break
                # ========== PLAYER ==========
                else:
                    if can_check and self.current_bet == 0:
                        action = input("Your action [check/bet/fold]: ").strip().lower()
                    elif can_check and self.current_bet > 0:
                        action = input("Your action [check/raise/fold]: ").strip().lower()
                    else:
                        action = input("Your action [call/raise/fold]: ").strip().lower()
                    if action == "fold":
                        p.folded = True
                        print("You folded.")
                    elif can_check and action == "check":
                        print("You check.")
                    elif can_check and action == "bet":
                        bet_amount = 5
                        self.current_bet += bet_amount
                        self.pot += p.bet(bet_amount)
                        #p.current_bet += bet_amount
                        print(f"You bet ${bet_amount}. Pot = ${self.pot}")
                        is_end_round = False
                        last_raise_idx = (start_player_idx + i) % len(self.players)
                        break
                    elif not can_check and action == "call":
                        call_amount = self.current_bet - p.current_bet
                        self.pot += p.bet(call_amount)
                        #p.current_bet = self.current_bet
                        print(f"You call ${call_amount}. Pot = ${self.pot}")
                    elif action == "raise":
                        raise_amount = 5
                        new_bet = self.current_bet + raise_amount
                        diff = new_bet - p.current_bet
                        self.pot += p.bet(diff)
                        #p.current_bet = new_bet
                        self.current_bet = new_bet
                        print(f"You raise to ${new_bet}. Pot = ${self.pot}")
                        is_end_round = False
                        last_raise_idx = (start_player_idx + i) % len(self.players)
                        break
                    else:
                        print("Invalid action, you check/call by default.")
            if is_end_round:
                break
        if sum(1 for pl in self.players if not pl.folded) == 1:
            print("💥 All others folded!")
            self.showdown()
            return
        print("\n=== Betting Round Ended ===")

        # Reset vòng cược
        self.active_player_index = self.dealer_index % len(self.players)
        self.current_bet = 0
        for p in self.players:
            p.current_bet = 0
        

    def showdown(self):
        print("\n=== SHOWDOWN ===")
        self.show_table(reveal_bot=True)

        active = [p for p in self.players if not p.folded]
        if len(active) == 1:
            winner = active[0]
            print(f"{winner.name} wins the pot (${self.pot}) by default!")
            winner.money += self.pot
             # --- log thắng/thua ---
            if winner.is_bot:
                BOT_LOG['rounds']['bot_wins'] += 1
            else:
                BOT_LOG['rounds']['player_wins'] += 1
            return

        result = compare_hands(self.players[0].hand, self.players[1].hand, self.community)
        if result == 1:
            print(f"{self.players[0].name} wins ${self.pot}!")
            self.players[0].money += self.pot
            BOT_LOG['rounds']['player_wins'] += 1
        elif result == -1:
            print(f"{self.players[1].name} wins ${self.pot}!")
            self.players[1].money += self.pot
            BOT_LOG['rounds']['bot_wins'] += 1
        else:
            print("It's a tie! Pot is split.")
            self.players[0].money += self.pot / 2
            self.players[1].money += self.pot / 2
            BOT_LOG['rounds']['ties'] += 1

    def reset(self):
        for p in self.players:
            p.reset()
        self.pot = 0
        self.current_bet = 0
        self.community = []
        self.create_deck()
        self.is_pre_flop = True

    def play_round(self):
        self.reset()
        print("\n============================")
        print("🎲 NEW ROUND STARTS")
        print("============================")

        # --- Small & Big Blind ---
        self.post_blinds()
        self.deal_hole_cards()
        self.show_table()

        # --- Pre-Flop ---
        print("\n=== PRE-FLOP ===")
        self.betting_round()
        if self.isEnded():
            self.dealer_index += 1
            return

        # --- Flop ---
        self.deal_flop()
        print("\n=== FLOP ===")
        self.show_table()
        self.betting_round()
        if self.isEnded():
            self.dealer_index += 1
            return

        # --- Turn ---
        self.deal_turn()
        print("\n=== TURN ===")
        self.show_table()
        self.betting_round()
        if self.isEnded():
            self.dealer_index += 1
            return

        # --- River ---
        self.deal_river()
        print("\n=== RIVER ===")
        self.show_table()
        self.betting_round()
        if self.isEnded():
            self.dealer_index += 1
            return

        # --- Showdown ---
        self.showdown()

        # Sau mỗi ván, đổi vị trí dealer (đổi small/blind)
        self.dealer_index += 1


    def play_game(self):
        print("=== TEXAS HOLD'EM POKER ===")
        while all(p.money > 0 for p in self.players):
            self.play_round()
            cont = input("\nPlay another round? (y/n): ").strip().lower()
            if cont != "y":
                break

        print("\n=== GAME OVER ===")
        for p in self.players:
            print(f"{p.name}: ${p.money}")
        if self.players[0].money > self.players[1].money:
            print("🎉 You win overall!")
        elif self.players[0].money < self.players[1].money:
            print("🤖 Bot wins overall!")
        else:
            print("🤝 It's a tie!")
def print_bot_stats():
        print("\n=== BOT STATISTICS ===")
        print(f"Total decisions: {BOT_LOG['decisions']}")
        print(f"Average win prob: {statistics.mean(BOT_LOG['win_probs']):.3f}")
        print(f"Average decision time: {statistics.mean(BOT_LOG['decision_times']):.3f}s")
        print(f"Raise rate: {BOT_LOG['raises'] / BOT_LOG['decisions']:.2%}")
        print(f"Fold rate: {BOT_LOG['folds'] / BOT_LOG['decisions']:.2%}")
        print(f"Call rate: {BOT_LOG['calls'] / BOT_LOG['decisions']:.2%}")
        print(f"Check rate: {BOT_LOG['checks'] / BOT_LOG['decisions']:.2%}")
        print(f"Bot wins: {BOT_LOG['rounds']['bot_wins']}")
        print(f"Player wins: {BOT_LOG['rounds']['player_wins']}")
        print(f"Ties: {BOT_LOG['rounds']['ties']}")

if __name__ == "__main__":
    game = PokerGame()
    game.play_game()
    print_bot_stats()

