#!/usr/bin/env python3
"""Startup script for the song selector backend."""
import sys
import os

# Add the backend directory to the path
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

from app.main import main

if __name__ == "__main__":
    main()
