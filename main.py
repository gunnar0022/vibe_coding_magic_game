#!/usr/bin/env python3
"""
Magic Game - Entry Point

A systems-driven magic simulation game where player knowledge is the core progression mechanic.

To run:
    python main.py

Requirements:
    pip install pygame

Controls:
    WASD / Arrow Keys - Move
    1-9              - Select magic symbols (sorted alphabetically)
    0                - Clear symbol selection
    Space            - Cast selected magic
    E / Enter        - Interact with NPCs and objects
    Tab / M          - Open magic selection menu
    N                - Open notebook (work in progress)
    H                - Show help
    F5               - Quick save
    F9               - Quick load
    ESC              - Close menu / Quit game
"""
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))


def check_dependencies():
    """Check that required dependencies are installed."""
    try:
        import pygame
        return True
    except ImportError:
        print("ERROR: pygame is not installed.")
        print("Please install it with: pip install pygame")
        print("Or: pip install -r requirements.txt")
        return False


def main():
    """Entry point for the game."""
    if not check_dependencies():
        sys.exit(1)

    print("=" * 60)
    print("MAGIC GAME")
    print("A systems-driven magic simulation")
    print("=" * 60)
    print()
    print("Controls:")
    print("  WASD / Arrows  - Move")
    print("  1-9            - Select magic symbols")
    print("  0              - Clear selection")
    print("  Space          - Cast selected magic")
    print("  E              - Interact")
    print("  Tab / M        - Magic menu")
    print("  H              - Help")
    print("  F5 / F9        - Quick Save / Load")
    print("  ESC            - Quit")
    print()
    print("Starting game...")
    print()

    try:
        from src.core import Game
        game = Game()
        game.run()
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print("\nGame closed. Thank you for playing!")


if __name__ == "__main__":
    main()
