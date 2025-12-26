#!/usr/bin/env python
"""
PokerBot Launcher Script

Run this script to start the Texas Hold'em poker game.
Usage: python run_game.py
   or: uv run run_game.py
"""

if __name__ == "__main__":
    from src.app import PokerGame
    
    game = PokerGame()
    game.play_game()
