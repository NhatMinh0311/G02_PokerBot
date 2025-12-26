"""
Automated bot vs bot testing with statistics.

Usage:
    uv run python src/autotest.py
    uv run python src/autotest.py basic advanced
"""

import json
import sys
import time
from typing import Dict, Any
from treys import Deck, Card, Evaluator

# Import bot decision logic
sys.path.insert(0, '.')
from src.bot import bot_decision


def load_config(config_file: str = "config_autotest.json") -> Dict[str, Any]:
    """Load test configuration from JSON file."""
    with open(config_file, 'r') as f:
        return json.load(f)


class Player:
    """Represents a bot player."""
    def __init__(self, name: str, depth: int = 3, mc_sims: int = 500):
        self.name = name
        self.money = 100
        self.hand = []
        self.folded = False
        self.current_bet = 0
        self.depth = depth
        self.mc_sims = mc_sims
        self.bot_log = {
            "decisions": 0,
            "folds": 0,
            "calls": 0,
            "raises": 0,
            "checks": 0,
            "win_probs": [],
            "decision_times": []
        }

    def reset(self):
        """Reset for new hand."""
        self.hand = []
        self.folded = False
        self.current_bet = 0


class PokerGame:
    """Simple poker game for testing."""
    def __init__(self, player1: Player, player2: Player, small_blind: int = 2, big_blind: int = 5):
        self.players = [player1, player2]
        self.small_blind = small_blind
        self.big_blind = big_blind
        self.deck = Deck()
        self.community = []
        self.pot = 0
        self.current_bet = 0
        self.evaluator = Evaluator()

    def reset_hand(self):
        """Reset for new hand."""
        for p in self.players:
            p.reset()
        self.deck = Deck()
        self.community = []
        self.pot = 0
        self.current_bet = 0

    def play_hand(self) -> bool:
        """Play one hand. Returns True if game can continue."""
        self.reset_hand()
        
        # Post blinds
        self.players[0].current_bet = self.small_blind
        self.players[0].money -= self.small_blind
        self.players[1].current_bet = self.big_blind
        self.players[1].money -= self.big_blind
        self.pot = self.small_blind + self.big_blind

        # Deal cards
        for p in self.players:
            p.hand = self.deck.draw(2)

        # Pre-flop
        if not self.betting_round():
            return self.check_bankrupt()

        # Flop
        self.community = self.deck.draw(3)
        if not self.betting_round():
            return self.check_bankrupt()

        # Turn
        self.community.append(self.deck.draw(1)[0])
        if not self.betting_round():
            return self.check_bankrupt()

        # River
        self.community.append(self.deck.draw(1)[0])
        if not self.betting_round():
            return self.check_bankrupt()

        # Showdown
        self.showdown()
        return self.check_bankrupt()

    def betting_round(self) -> bool:
        """Execute betting round. Returns False if folded."""
        actions = 0
        max_actions = 10

        while actions < max_actions:
            all_matched = all(p.current_bet == self.current_bet or p.folded for p in self.players)
            if all_matched and actions > 0:
                break

            for p in self.players:
                if p.folded or p.money <= 0:
                    continue

                action = self.get_bot_action(p)
                
                if action == "fold":
                    p.folded = True
                    self.award_pot(self.get_opponent(p))
                    return False
                elif action == "call":
                    to_call = min(self.current_bet - p.current_bet, p.money)
                    p.money -= to_call
                    p.current_bet += to_call
                    self.pot += to_call
                elif action == "raise":
                    raise_amt = 5
                    new_bet = self.current_bet + raise_amt
                    diff = min(new_bet - p.current_bet, p.money)
                    p.money -= diff
                    p.current_bet += diff
                    self.pot += diff
                    self.current_bet = new_bet

            actions += 1

        # Reset for next street
        for p in self.players:
            p.current_bet = 0
        self.current_bet = 0
        return True

    def get_bot_action(self, bot: Player) -> str:
        """Get bot decision."""
        opp = self.get_opponent(bot)
        bot_is_small_blind = (bot == self.players[0])
        
        state = {
            "bot_hand": bot.hand.copy(),
            "community": self.community.copy(),
            "pot": self.pot,
            "current_bet": self.current_bet,
            "bot_money": bot.money,
            "opp_money": opp.money if opp else 0,
            "bot_current_bet": bot.current_bet,
            "raise_amount": 5,
            "terminal": False,
            "bot_is_small_blind": bot_is_small_blind
        }

        return bot_decision(state, bot.depth, bot.mc_sims, bot.bot_log)

    def get_opponent(self, player: Player):
        """Get opponent."""
        for p in self.players:
            if p != player and not p.folded:
                return p
        return None

    def showdown(self):
        """Determine winner."""
        active = [p for p in self.players if not p.folded]
        if len(active) == 1:
            self.award_pot(active[0])
            return

        p1, p2 = active[0], active[1]
        rank1 = self.evaluator.evaluate(self.community, p1.hand)
        rank2 = self.evaluator.evaluate(self.community, p2.hand)

        if rank1 < rank2:
            self.award_pot(p1)
        elif rank2 < rank1:
            self.award_pot(p2)
        else:
            p1.money += self.pot // 2
            p2.money += self.pot // 2

    def award_pot(self, winner: Player):
        """Award pot."""
        if winner:
            winner.money += self.pot

    def check_bankrupt(self) -> bool:
        """Check if game can continue."""
        return all(p.money > 0 for p in self.players)


def print_statistics(player: Player):
    """Print bot statistics."""
    log = player.bot_log
    total = log["decisions"]
    if total == 0:
        return
    
    fold_pct = (log["folds"] / total) * 100
    call_pct = (log["calls"] / total) * 100
    raise_pct = (log["raises"] / total) * 100
    check_pct = (log["checks"] / total) * 100
    
    avg_time = sum(log["decision_times"]) / len(log["decision_times"]) if log["decision_times"] else 0
    
    print(f"  {player.name}:")
    print(f"    Decisions: {total}")
    print(f"    Fold:  {log['folds']:3d} ({fold_pct:5.1f}%)")
    print(f"    Call:  {log['calls']:3d} ({call_pct:5.1f}%)")
    print(f"    Raise: {log['raises']:3d} ({raise_pct:5.1f}%)")
    print(f"    Check: {log['checks']:3d} ({check_pct:5.1f}%)")
    print(f"    Avg decision time: {avg_time:.3f}s")


def show_bot_info(config: Dict[str, Any]):
    """Display available bot configurations."""
    print("\n📋 Available Bot Configurations:\n")
    for name, cfg in config["bots"].items():
        print(f"  • {name.upper()}")
        print(f"    - Depth: {cfg['depth']} (searches {cfg['depth']} moves ahead)")
        print(f"    - Simulations: {cfg['mc_sims']} (Monte Carlo runs per decision)")
        
        # Estimate difficulty
        if cfg['depth'] <= 1 and cfg['mc_sims'] <= 200:
            difficulty = "⭐ Easy"
        elif cfg['depth'] <= 2 and cfg['mc_sims'] <= 500:
            difficulty = "⭐⭐ Medium"
        elif cfg['depth'] <= 3 and cfg['mc_sims'] <= 1000:
            difficulty = "⭐⭐⭐ Hard"
        else:
            difficulty = "⭐⭐⭐⭐ Expert"
        print(f"    - Difficulty: {difficulty}")
        print()
    
    settings = config["settings"]
    print(f"🎮 Test Settings:")
    print(f"  - Games per test: {settings['num_games']}")
    print(f"  - Rounds per game: {settings['rounds_per_game']}")
    print(f"  - Starting money: ${settings['starting_money']}")
    print(f"  - Blinds: ${settings['small_blind']}/${settings['big_blind']}")
    print()


def run_test(bot1_name: str, bot2_name: str, config: Dict[str, Any]):
    """Run test between two bots."""
    bot1_cfg = config["bots"][bot1_name]
    bot2_cfg = config["bots"][bot2_name]
    settings = config["settings"]
    
    print(f"\n{'='*60}")
    print(f"🎮 Testing: {bot1_name.upper()} vs {bot2_name.upper()}")
    print(f"   {bot1_name}: depth={bot1_cfg['depth']}, sims={bot1_cfg['mc_sims']}")
    print(f"   {bot2_name}: depth={bot2_cfg['depth']}, sims={bot2_cfg['mc_sims']}")
    print(f"   Games: {settings['num_games']}, Rounds: {settings['rounds_per_game']}")
    print(f"{'='*60}\n")
    
    bot1_wins = 0
    bot2_wins = 0
    
    for game_num in range(settings["num_games"]):
        player1 = Player(bot1_name.capitalize(), bot1_cfg["depth"], bot1_cfg["mc_sims"])
        player2 = Player(bot2_name.capitalize(), bot2_cfg["depth"], bot2_cfg["mc_sims"])
        player1.money = settings["starting_money"]
        player2.money = settings["starting_money"]
        
        game = PokerGame(player1, player2, settings["small_blind"], settings["big_blind"])
        
        # Progress indicator
        print(f"Game {game_num + 1}/{settings['num_games']}: ", end='', flush=True)
        
        for round_num in range(settings["rounds_per_game"]):
            if not game.play_hand():
                break
            # Show progress dots
            if (round_num + 1) % 5 == 0:
                print('.', end='', flush=True)
        
        # Determine winner
        if player1.money > player2.money:
            bot1_wins += 1
            winner = bot1_name
        elif player2.money > player1.money:
            bot2_wins += 1
            winner = bot2_name  
        else:
            winner = "tie"
        
        print(f" ✓ {winner} (${player1.money} vs ${player2.money})")
    
    # Results
    print(f"\n📊 RESULTS:")
    print(f"  {bot1_name}: {bot1_wins} wins ({(bot1_wins/settings['num_games'])*100:.1f}%)")
    print(f"  {bot2_name}: {bot2_wins} wins ({(bot2_wins/settings['num_games'])*100:.1f}%)")
    
    print(f"\n📈 STATISTICS:")
    print_statistics(player1)
    print_statistics(player2)


def main():
    """Main entry point."""
    print("🤖 PokerBot Automated Testing\n")
    
    # Load config
    config = load_config()
    
    # Show bot configurations
    show_bot_info(config)
    
    # Get bot names from command line or use defaults
    if len(sys.argv) >= 3:
        bot1 = sys.argv[1]
        bot2 = sys.argv[2]
        run_test(bot1, bot2, config)
    else:
        # Run all combinations
        bot_names = list(config["bots"].keys())
        for i, bot1 in enumerate(bot_names):
            for bot2 in bot_names[i+1:]:
                run_test(bot1, bot2, config)
                time.sleep(0.5)


if __name__ == "__main__":
    main()
