#!/usr/bin/env python3
"""Entry point — keeps `python radar.py` working (CI/cron unchanged). All logic
lives in the gh_radar/ package; see gh_radar/__init__.py for the layout."""
from gh_radar.cli import main

if __name__ == "__main__":
    main()
