#!/usr/bin/env python3
"""Entry point for PyInstaller build."""
import sys
import os
from pathlib import Path

# Detect if running from PyInstaller bundle
if getattr(sys, 'frozen', False):
    # Running in a PyInstaller bundle
    bundle_dir = Path(sys._MEIPASS)  # Temporary extraction directory
    work_dir = Path(sys.executable).parent  # Directory containing the exe
    os.environ['DIVA_SELECTOR_WORK_DIR'] = str(work_dir)
else:
    # Running in development
    bundle_dir = Path(__file__).parent
    work_dir = bundle_dir

# Add backend to path
sys.path.insert(0, str(bundle_dir))

# Set up environment for the app
os.chdir(work_dir)

from app.main import main

if __name__ == "__main__":
    main()
