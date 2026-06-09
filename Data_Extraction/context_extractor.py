"""
FixtureIQ - Contextual Data Extractor
======================================
Fetches ClubElo ratings and Understat xG data via the soccerdata library.
"""

import sys
import time
from pathlib import Path

_root = Path(__file__).resolve().parent.parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from src.config.paths import get_elo_path, get_understat_path

import soccerdata as sd
import pandas as pd


def extract_club_elo():
    print("--- Fetching ClubELO Data ---")
    elo = sd.ClubElo()
    df_elo = elo.read_by_date()

    start_date = '2021-08-01'
    try:
        df_elo_filtered = df_elo[df_elo.index.get_level_values('date') >= start_date]
    except Exception as e:
        print(f"Filtering fallback: {e}")
        df_elo_filtered = df_elo

    out_path = get_elo_path()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df_elo_filtered.to_csv(out_path)
    print(f"Saved ELO data: {df_elo_filtered.shape} -> {out_path}")


def extract_understat():
    print("--- Fetching Understat Data ---")
    seasons_list = ["22-23", "23-24", "24-25"]
    try:
        us = sd.Understat(leagues="ENG-Premier League", seasons=seasons_list)
        df_understat = us.read_schedule()
        out_path = get_understat_path()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        df_understat.to_csv(out_path)
        print(f"Saved Understat data: {df_understat.shape} -> {out_path}")
    except Exception as e:
        print(f"Error in Understat: {e}")


def main():
    extract_club_elo()
    extract_understat()
    print("\n=== FixtureIQ: Multi-Source Extraction Complete ===")


if __name__ == "__main__":
    main()
