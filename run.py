#!/usr/bin/env python3
"""
Simple entry point script to run the Cyndi Taylor Website Bot.
"""
import sys
from src.main import main

if __name__ == "__main__":
    # If an instruction is provided as a command-line argument, use it
    instruction = sys.argv[1] if len(sys.argv) > 1 else None
    main(instruction)
