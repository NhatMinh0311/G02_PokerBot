import random
import statistics
import copy
from treys import Deck, Evaluator
from bot import bot_decision_wrapper, BOT_LOG_TEMPLATE


def compare_hands(cards1, cards2, community):
    evaluator = Evaluator()
    r1 = evaluator.evaluate(community, cards1)
    r2 = evaluator.evaluate(community, cards2)
    return 1 if r1 < r2 else -1 if r1 > r2 else 0


class Player:
    def __init__(self, name, money=1000, is_bot=False, depth=2, mc_sims=50):
        self.name = name
        self.is_bot = is_bot
        self.money = money
        self.hand = []
        self.folded = False
        self.current_bet = 0
        self.statistics = {"fold": 0, "call": 0, "raise": 0}
        self.depth = depth
        self.mc_sims = mc_sims
        self.bot_log = copy.deepcopy(BOT_LOG_TEMPLATE) if is_bot else None

    def reset(self):
        self.hand = []
        self.folded = False
        self.current_bet = 0

    def bet(self, amount):
        amount = min(amount, self.money)
        self.money -= amount
        self.current_bet += amount
        return amount

    def show(self):
        print(self.statistics)


class PokerGame:
    def __init__(self, players):
        self.players = players
        self.dealer_index = 0
        self.reset()
        self.rounds = {"p0_wins": 0, "p1_wins": 0, "ties": 0}

    def reset(self):
        for p in self.players:
            p.reset()
        self.deck = Deck()
        self.community = []
        self.pot = 0
        self.current_bet = 0
        self.active_player_index = (self.dealer_index + 2) % len(self.players)

    def isEnded(self):
        return sum(1 for p in self.players if not p.folded) <= 1

    def deal_hole_cards(self):
        for p in self.players:
            p.hand = self.deck.draw(2)

    def burn(self):
        self.deck.draw(1)

    def deal_flop(self):
        self.burn()
        self.community.extend(self.deck.draw(3))

    def deal_turn(self):
        self.burn()
        self.community.extend(self.deck.draw(1))

    def deal_river(self):
        self.burn()
        self.community.extend(self.deck.draw(1))

    def post_blinds(self, small=2, big=5):
        sb = self.players[self.dealer_index % len(self.players)]
        bb = self.players[(self.dealer_index + 1) % len(self.players)]

        self.pot += sb.bet(small)
        sb.current_bet = small

        self.pot += bb.bet(big)
        bb.current_bet = big

        self.current_bet = big
        self.active_player_index = (self.dealer_index + 2) % len(self.players)

    def _apply_action(self, p, action):
        if action == "fold":
            p.folded = True
            return False

        if action == "call":
            call_amount = max(0, self.current_bet - p.current_bet)
            self.pot += p.bet(call_amount)
            return False

        if action == "raise":
            raise_amount = 5
            new_total = self.current_bet + raise_amount
            diff = max(0, new_total - p.current_bet)
            self.pot += p.bet(diff)
            self.current_bet = new_total
            return True

        return False

    def betting_round(self):
        last_raise_idx = -1

        while True:
            start_idx = (
                (last_raise_idx + 1) % len(self.players)
                if last_raise_idx != -1
                else self.active_player_index
            )

            ended = True
            for i in range(len(self.players)):
                if self.isEnded():
                    break

                idx = (start_idx + i) % len(self.players)
                p = self.players[idx]
                if p.folded:
                    continue

                if last_raise_idx != -1 and idx == last_raise_idx:
                    break

                action = (
                    bot_decision_wrapper(self, p)
                    if p.is_bot
                    else random.choice(["call", "fold", "raise"])
                )

                raised = self._apply_action(p, action)
                if raised:
                    ended = False
                    last_raise_idx = idx
                    break

            if ended:
                break

        if self.isEnded():
            self.showdown()
            return

        self.active_player_index = self.dealer_index % len(self.players)
        self.current_bet = 0
        for p in self.players:
            p.current_bet = 0

    def showdown(self):
        active = [p for p in self.players if not p.folded]
        if len(active) == 1:
            winner = active[0]
            winner.money += self.pot
            if winner == self.players[0]:
                self.rounds["p0_wins"] += 1
            else:
                self.rounds["p1_wins"] += 1
            return

        result = compare_hands(self.players[0].hand, self.players[1].hand, self.community)
        if result == 1:
            self.players[0].money += self.pot
            self.rounds["p0_wins"] += 1
        elif result == -1:
            self.players[1].money += self.pot
            self.rounds["p1_wins"] += 1
        else:
            self.players[0].money += self.pot / 2
            self.players[1].money += self.pot / 2
            self.rounds["ties"] += 1

    def play_round(self):
        self.reset()
        self.post_blinds()
        self.deal_hole_cards()

        self.betting_round()
        if self.isEnded():
            self.dealer_index += 1
            return

        self.deal_flop()
        self.betting_round()
        if self.isEnded():
            self.dealer_index += 1
            return

        self.deal_turn()
        self.betting_round()
        if self.isEnded():
            self.dealer_index += 1
            return

        self.deal_river()
        self.betting_round()
        if self.isEnded():
            self.dealer_index += 1
            return

        self.showdown()
        self.dealer_index += 1

    def play_game(self, max_rounds=50):
        i = 0
        while all(p.money > 0 for p in self.players) and i < max_rounds:
            self.play_round()
            i += 1
            print(f"{i}/{max_rounds} rounds played.")

        print("\n=== GAME OVER ===")
        print_bot_stats(game)
        for p in self.players:
            print(f"{p.name}: ${p.money}")

        if self.players[0].money > self.players[1].money:
            print(f">>>>>>>>>>>>{self.players[0].name} wins overall!<<<<<<<<<<")
        elif self.players[0].money < self.players[1].money:
            print(f">>>>>>>>>>>>{self.players[1].name} wins overall!<<<<<<<<<<")
        else:
            print("🤝 It's a tie!")


def print_bot_stats(game):
    rounds = game.rounds
    for p in game.players:
        if p.is_bot:
            log = p.bot_log
            print(f"\n=== {p.name} STATISTICS ===")
            print(f"Total decisions: {log['decisions']}")
            if log['win_probs']:
                print(f"Average win prob: {statistics.mean(log['win_probs']):.3f}")
            if log['decision_times']:
                print(f"Average decision time: {statistics.mean(log['decision_times']):.3f}s")
                print(f"Median decision time: {statistics.median(log['decision_times']):.3f}s")
                print(f"Max decision time: {max(log['decision_times']):.3f}s")
                print(f"Min decision time: {min(log['decision_times']):.3f}s")
            if log['decisions'] > 0:
                print(f"Raise rate: {log['raises'] / log['decisions']:.2%}")
                print(f"Raise count: {log['raises']}")
                print(f"Fold rate: {log['folds'] / log['decisions']:.2%}")
                print(f"Fold count: {log['folds']}")
                print(f"Call rate: {log['calls'] / log['decisions']:.2%}")
                print(f"Call count: {log['calls']}")
                print(f"Check rate: {log['checks'] / log['decisions']:.2%}")
                print(f"Check count: {log['checks']}")
    print(f"\n=== GAME ROUNDS ===")
    print(f"Bot1 wins: {rounds['p0_wins']}")
    print(f"Bot2 wins: {rounds['p1_wins']}")
    print(f"Ties: {rounds['ties']}")


if __name__ == "__main__":
    game = PokerGame(players=[
        Player("Bot1", is_bot=True, depth=5, mc_sims=50),
        Player("Bot2", is_bot=True, depth=2, mc_sims=100)
    ])
    game.play_game(max_rounds=50)
