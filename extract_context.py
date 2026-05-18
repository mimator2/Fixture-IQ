import soccerdata as sd
import pandas as pd
from pathlib import Path
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

print("--- Fetching Multi-Competition Understat Data ---")

# Define the competitions supported by Understat where PL clubs compete
understat_leagues = [
    "ENG-Premier League",
    "Champions League",
    "Europa League"
]

# Ensure the season list aligns perfectly with your historical research window
seasons_list = ["21-22", "22-23", "23-24", "24-25"]

all_leagues_data = []

for league in understat_leagues:
    try:
        print(f"    -> Extracting schedules & intensity metrics for: {league}")
        # Instantiate Understat for the specific tournament layer
        us = sd.Understat(leagues=league, seasons=seasons_list)
        df_league = us.read_schedule()
        
        # Track the origin competition so you can filter or inspect later
        df_league['understat_competition'] = league
        all_leagues_data.append(df_league)
        
    except Exception as e:
        print(f"    [⚠️] League mapping skipped for {league}: {e}")

# Combine timelines across all leagues
if all_leagues_data:
    df_understat_master = pd.concat(all_leagues_data, ignore_index=False).reset_index()
    
    # Save the complete file
    output_file = Path("fixtureiq_understat_multi_comp.csv")
    df_understat_master.to_csv(output_file, index=False)
    print(f"\n[🚀] SUCCESS: Combined Understat matrix saved: {df_understat_master.shape}")
    print(f"    -> Location: {output_file}")
else:
    print("[❌] Processing failed. No Understat records were generated.")