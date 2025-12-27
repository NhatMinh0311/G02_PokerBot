# 🃏 PokerBot - Texas Hold'em AI

An intelligent poker bot that plays Texas Hold'em using **MiniMax algorithm with Alpha-Beta pruning** and **Monte Carlo simulation** for optimal decision-making.

## 🎮 Game Description

**Players:** You vs Bot (2-player game)  
**Starting Money:** $100 each  
**Game Duration:** 5 rounds  
**Winner:** Whoever has more money after 5 rounds

---

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/NhatMinh0311/G02_PokerBot
cd G02_PokerBot

# Install dependencies (using uv)
uv sync

# Or using pip
pip install pygame treys
```

### Run the Game

```bash
# Using uv (recommended)
uv run python run_game.py

# Or using python directly
python run_game.py
```

---

## 🤖 Bot Features

### Aggressive AI Strategy
- **Only folds garbage hands** (<25% win probability)
- **Always defends medium hands** (25-55% win probability)
- **Raises with strong hands** (>55% win probability)
- Uses **MiniMax** to optimize raise vs call decisions

### Advanced Techniques
- ✅ **Monte Carlo Simulation** - Estimates win probability by simulating thousands of hands
- ✅ **Parallel Processing** - Multithreaded Monte Carlo for 3-4x speedup
- ✅ **Dynamic Bet Sizing** - Varies bet from $2-$50+ based on hand strength
- ✅ **Strategic Play** - Uses game theory optimal concepts
- ✅ **10 Difficulty Levels** - Adjustable depth and simulation count

---

## 📊 Performance

| Metric | Performance |
|--------|-------------|
| **Fold Rate** | ~10-15% (plays 85-90% of hands) |
| **Decision Speed** | 0.3-0.8s (with parallel Monte Carlo) |
| **Bet Sizing** | Dynamic $2-$50+ based on hand strength |
| **Win Rate** | ~50% against itself (balanced) |

---

## 🏗️ Architecture

### Core Modules

```
G02_PokerBot/
├── run_game.py              # Main launcher script
├── src/
│   ├── __init__.py          # Package marker
│   ├── app.py               # Pygame GUI and game engine
│   ├── bot.py               # AI decision-making logic
│   ├── bet_sizing.py        # Dynamic bet calculation
│   ├── monte_carlo_parallel.py  # Parallel Monte Carlo
│   ├── constants.py         # Centralized configuration
│   ├── config.py            # Type-safe settings
│   └── models.py            # Data structures
└── assets/                  # Images and sounds (optional)
```

### Key Technologies
- **pygame** - Game UI and rendering
- **treys** - Poker hand evaluation
- **Python 3.13+** - Modern Python features
- **ThreadPoolExecutor** - Parallel processing

---

## 🎯 Bot Algorithm

### Decision Flow

```python
# Calculate win probability using Monte Carlo
win_prob = monte_carlo_win_prob(bot_hand, community, n_simulations)

# Decision logic
if no_bet_yet:
    if win_prob >= 50%:
        action = "raise"  # Aggressive with coin-flip or better
    else:
        action = "check"
else:
    if win_prob < 25%:
        action = "fold"  # Only fold trash
    elif win_prob >= 55%:
        action = minimax_raise_or_call()  # Use MiniMax
    else:
        action = "call"  # Always defend medium hands
```

### MiniMax with Alpha-Beta Pruning
- Searches 2-5 moves ahead
- Assumes opponent plays optimally
- Evaluates game states using:
  - Win probability (68% weight)
  - Expected value (25% weight)
  - Bankroll ratio (7% weight)

### Monte Carlo Simulation
- Simulates 50-5000 random opponent hands
- Parallel processing for 100+ simulations
- Estimates win probability with 95%+ accuracy

---

## 🎮 Gameplay

### Main Menu
- **Start Game** - Begin new session
- **Bot Level** - Adjust difficulty (1-10)
  - Level 1: 50 simulations, depth 1 (~0.1s per decision)
  - Level 5: 2,250 simulations, depth 5 (~0.8s per decision)
  - Level 10: 5,000 simulations, depth 10 (~2s per decision)
- **Quit** - Exit game

### Controls
- **Fold** - Give up hand
- **Check / Call** - Match bet or check if no bet
- **Raise / Bet** - Increase bet (adjust with +/- buttons)
- **ESC** - Return to main menu

### Features
- 🎨 Professional GUI with animations
- 🔊 Sound effects (optional)
- 📊 Scrollable game log
- 🎲 Particle effects on wins
- 📈 Real-time statistics tracking

---

## 🧪 Development Phases

### ✅ Phase 1: Code Quality & Architecture
- Type hints and comprehensive docstrings
- Centralized configuration system
- Modular code structure
- Data models with validation

### ✅ Phase 2: AI Improvements  
- **Fixed over-folding** - Bot now plays 85-90% of hands
- **Parallel Monte Carlo** - 3-4x performance improvement
- **Dynamic bet sizing** - Intelligent bet amounts
- **Aggressive strategy** - Competitive gameplay

### 🔜 Phase 3: Advanced Features (Planned)
- Multi-player support (3-6 players)
- Tournament mode with blind escalation
- Hand history tracking and export
- Position-aware strategy

### 🔜 Phase 4: UI Enhancements (Planned)
- Statistics dashboard
- Tutorial mode
- Hand strength indicator
- Bot decision explanations

---

## 📚 Documentation

- **[ALGORITHM.md](docs/ALGORITHM.md)** - Detailed algorithm explanation
- **[walkthrough.md](docs/walkthrough.md)** - Phase 1 & 2 improvements
- **[task.md](docs/task.md)** - Development checklist

---

## 🔧 Configuration

### Adjust Bot Difficulty
Edit `src/constants.py` to tune bot behavior:

```python
# Make bot MORE aggressive
RAISE_MIN_WIN_PROB = 0.40  # Lower = more raises
FOLD_THRESHOLD = 0.20      # Lower = fewer folds

# Make bot LESS aggressive  
RAISE_MIN_WIN_PROB = 0.60  # Higher = fewer raises
FOLD_THRESHOLD = 0.30      # Higher = more folds
```

### Enable/Disable Parallel Processing
Edit `src/bot.py`:

```python
USE_PARALLEL_MONTE_CARLO = True   # 3-4x faster
USE_PARALLEL_MONTE_CARLO = False  # Sequential (debugging)
```

---

## 🧪 Testing

### Automated Bot vs Bot Testing

```bash
# Run bot vs bot simulations
uv run python src/autotest.py

# Default: 10 games, 20 rounds each
# Tests different difficulty configurations
```

### Performance Metrics
- Decision times
- Fold/raise/call frequencies
- Average win probability
- Win rates

---

## 🎓 Educational Value

This project demonstrates:
- **Game Theory** - MiniMax algorithm for optimal play
- **Probability Theory** - Monte Carlo simulation
- **Parallel Programming** - Multithreaded processing
- **AI Strategy** - Combining multiple decision factors
- **Software Engineering** - Clean architecture with type safety

---

## 🤝 Contributing

This is an educational project. Feel free to:
- Experiment with different AI strategies
- Add new features (e.g., bluffing, position awareness)
- Improve the UI
- Optimize performance

---

## 📝 License

Educational project - feel free to use and modify.

---

## 🙏 Credits

- **treys** library for poker hand evaluation
- **pygame** for game UI
- Modern poker strategy concepts

---
