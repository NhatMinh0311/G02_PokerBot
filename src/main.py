import random
from treys import Deck, Card, Evaluator

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

    def reset(self):
        self.hand = []
        self.folded = False

    def bet(self, amount):
        if amount > self.money:
            amount = self.money
        self.money -= amount
        return amount


class PokerGame:
    def __init__(self):
        self.players = [Player("You"), Player("Bot", is_bot=True)]
        self.deck = None
        self.playingPlayer = len(self.players)
        self.community = []
        self.pot = 0
        self.current_bet = 5

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
        return self.playingPlayer <= 1
    
    def betting_round(self):
        print("\n=== Betting Round ===")
        for p in self.players:
            if p.folded:
                continue

            if p.is_bot:
                # Simple bot logic: random or always call/check
                if random.random() < 0.2:
                    p.folded = True
                    self.playingPlayer -= 1
                    print("🤖 Bot folds.")
                    
                else:
                    bet_amount = 0 if random.random() < 0.7 else self.current_bet
                    if bet_amount > 0:
                        self.pot += p.bet(bet_amount)
                        print(f"🤖 Bot bets ${bet_amount}.")
                    else:
                        print("🤖 Bot checks.")
            else:
                action = input("Your action [check/bet/fold]: ").strip().lower()
                if action == "fold":
                    p.folded = True
                    self.playingPlayer -= 1
                    print("You folded.")
                elif action == "bet":
                    self.pot += p.bet(self.current_bet)
                    print(f"You bet ${self.current_bet}. Pot = ${self.pot}")
                elif action == "check":
                    print("You check.")
                else:
                    print("Invalid action, check by default.")
            if self.isEnded():
                self.showdown()
                break

    def showdown(self):
        print("\n=== SHOWDOWN ===")
        self.show_table(reveal_bot=True)

        active = [p for p in self.players if not p.folded]
        if len(active) == 1:
            winner = active[0]
            print(f"{winner.name} wins the pot (${self.pot}) by default!")
            winner.money += self.pot
            return

        result = compare_hands(self.players[0].hand, self.players[1].hand, self.community)
        if result == 1:
            print(f"{self.players[0].name} wins ${self.pot}!")
            self.players[0].money += self.pot
        elif result == -1:
            print(f"{self.players[1].name} wins ${self.pot}!")
            self.players[1].money += self.pot
        else:
            print("It's a tie! Pot is split.")
            self.players[0].money += self.pot / 2
            self.players[1].money += self.pot / 2

    def reset(self):
        for p in self.players:
            p.reset()
        self.pot = 0
        self.community = []
        self.create_deck()
        self.playingPlayer = len(self.players)

    def play_round(self):
        self.reset()
        self.deal_hole_cards()
        print("\n============================")
        print("🎲 NEW ROUND STARTS")
        print("============================")
        self.show_table()

        # Pre-Flop
        self.betting_round()
        if self.isEnded():
            return
        # Flop
        self.deal_flop()
        self.show_table()
        self.betting_round()
        if self.isEnded():
            return
        # Turn
        self.deal_turn()
        self.show_table()
        self.betting_round()
        if self.isEnded():
            return
        # River
        self.deal_river()
        self.show_table()
        self.betting_round()
        if self.isEnded():
            return
        # Showdown
        self.showdown()

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


if __name__ == "__main__":
    game = PokerGame()
    game.play_game()