import soccerdata as sd
import pandas as pd
import time
import os


### Already loaded ClubELO data from soccerdata

# # 1. CLUB ELO (Relative Difficulty Context)
# print("--- Fetching ClubELO Data ---")
# elo = sd.ClubElo()
# df_elo = elo.read_by_date()

# # Filter for the research window starting from the 21/22 season start
# start_date = '2021-08-01'
# try:
#     # SoccerData ClubElo typically has a MultiIndex (team, date)
#     df_elo_filtered = df_elo[df_elo.index.get_level_values('date') >= start_date]
# except Exception as e:
#     print(f"Filtering fallback: {e}")
#     df_elo_filtered = df_elo

# df_elo_filtered.to_csv("fixtureiq_elo_master.csv")
# print(f"Saved ELO data: {df_elo_filtered.shape}")


# 2. UNDERSTAT (xG and Match Quality)
print("--- Fetching Understat Data ---")
# SoccerData allows passing a list of seasons directly
# Seasons in soccerdata for Understat usually follow "YYYY" or "YY-YY" format
seasons_list = ["20-21", "21-22", "22-23", "23-24"]
try:
    us = sd.Understat(leagues="ENG-Premier League", seasons=seasons_list)
    df_understat = us.read_schedule()
    df_understat.to_csv("fixtureiq_understat_master.csv")
    print(f"Saved Understat data: {df_understat.shape}")
except Exception as e:
    print(f"Error in Understat: {e}")

print("\n=== FixtureIQ: Multi-Source Extraction Complete ===")