#!/usr/bin/env python3
"""
run.py — single-file launcher for Game AI Platform.

Usage:
  python run.py                    # Start web server on :8000
  python run.py serve --port 3000  # Custom port
  python run.py create "贪吃蛇"    # CLI create
  python run.py list               # List projects
"""

import sys
import os

# Ensure project root is on PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.cli import main

if __name__ == "__main__":
    # Default to 'serve' if no command given
    if len(sys.argv) == 1:
        sys.argv.append("serve")
    main()
