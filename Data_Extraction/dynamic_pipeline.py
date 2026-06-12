#!/usr/bin/env python3
"""
FixtureIQ Dynamic Congestion Pipeline (Baseline-Expanded Edition)
========================================================================
End-to-end pipeline that builds a player-level fatigue dataset for a given
season by:

  1. Discovering all Premier League teams (+ UCL participants) via SoccerData
  2. Building a unified fixture calendar (PL + UCL matches involving PL teams)
  3. Fetching per-match player stats from SofaScore (with local disk caching)
  4. Engineering fatigue/workload features:
       - rest_days, high_congestion_flag, min_last_7d, acwr_ratio
       - lineup_churn, squad_age_average, player_historical_intensity_28d
       - is_away, consecutive_away_games, match_type (Domestic/European)
  5. Merging ClubElo ratings (opponent strength) and Understat xG data

Outputs (to the chosen output directory):
  - raw_pl_centric_player_matches_{season}.csv  — raw SofaScore player-match tables
    (intermediate export, no feature engineering — subsumes the former
    standalone raw_downloader module)
  - fixtureiq_dynamic_master.csv                — full feature matrix
  - fixtureiq_dynamic_analytics_clean.csv       — ML-ready subset (no GKs, selected features)

Usage:
    python src/data/dynamic_pipeline.py --year 24/25 --output-dir data/2024-2025/sofascore_dynamic
    python src/data/dynamic_pipeline.py --year 22/23 --output-dir data/2022-2023/sofascore_dynamic
    python scripts/extract_dynamic.py --year 24/25
========================================================================
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path
import pandas as pd
import numpy as np

# Allow direct execution
_root = Path(__file__).resolve().parent.parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from src.config.paths import data_dir, get_understat_path

# Optional Edge executable override (set via EDGE_PATH env var if needed)
edge_path = os.environ.get("EDGE_PATH", r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
if Path(edge_path).exists():
    os.environ["BOTASAURUS_CHROME_EXECUTABLE_PATH"] = edge_path

try:
    import ScraperFC
    import soccerdata as sd
except ImportError as e:
    print(f"[-] Missing dependencies. Run: pip install ScraperFC soccerdata pandas numpy. Error: {e}")
    sys.exit(1)


class FixtureIQDynamicPipeline:
    # A complete pool of target competitions involving English top-flight clubs
    COMPETITIONS_POOL = [
        "England Premier League",
        "UEFA Champions League"
    ]

    def __init__(self, year_sofascore: str, output_dir: str = None, delay: float = 3.0):
        self.year_ss = year_sofascore  # Format: "23/24" or "24/25"
        self.delay = delay
        season_name = f"20{year_sofascore.split('/')[0]}-{20+int(year_sofascore.split('/')[1]):02d}" if '/' in year_sofascore else year_sofascore
        if output_dir is None:
            output_dir = str(data_dir() / season_name / 'sofascore_dynamic')
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Anti-ban cache directory initialization
        self.cache_dir = data_dir() / 'cache' / 'fixtureiq_cache'
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        print("[*] Initializing ScraperFC Automation Engine...")
        self.scraper = ScraperFC.Sofascore()

    def discover_pl_teams(self) -> tuple[set[str], set[str]]:
        """
        Uses soccerdata to dynamically discover all Premier League teams 
        and the European Elite cohort to bypass broken ScraperFC season keys.
        """
        print(f"\n[*] STEP 1: Discovering league-wide baseline and elite cohort for Season {self.year_ss}...")
        
        # Translate Sofascore string format "23/24" -> SoccerData format "2023"
        sd_year = f"20{self.year_ss.split('/')[0]}"
        
        try:
            print("    -> Extracting Premier League member directory via SoccerData...")
            # Use the MatchHistory scraper from soccerdata to read the season timeline safely
            mh_pl = sd.MatchHistory(leagues="ENG-Premier League", seasons=sd_year)
            df_pl = mh_pl.read_games()
            
            pl_teams = set(df_pl['home_team'].unique()) | set(df_pl['away_team'].unique())
            
            print("    -> Extracting Champions League directory via SoccerData...")
            mh_ucl = sd.MatchHistory(leagues="INT-Champions League", seasons=sd_year)
            df_ucl = mh_ucl.read_games()
            ucl_teams = set(df_ucl['home_team'].unique()) | set(df_ucl['away_team'].unique())
            
            elite_cohort = pl_teams & ucl_teams
            if not elite_cohort:
                elite_cohort = {"Manchester City", "Arsenal", "Manchester United", "Newcastle United"}
                
            print(f"[✅] Successfully mapped entire league baseline ({len(pl_teams)} teams total).")
            print(f"    -> Isolated Elite Cohort: {list(elite_cohort)}")
            return pl_teams, elite_cohort

        except Exception as e:
            print(f"    [⚠️] SoccerData fallback layer engaged. Reason: {e}")
            fallback_pl = {"Manchester City", "Arsenal", "Liverpool", "Aston Villa", "Manchester United", "Newcastle United", "Tottenham", "Chelsea", "Everton", "Fulham", "Brighton", "Brentford", "West Ham", "Bournemouth", "Crystal Palace", "Wolves", "Nottingham Forest", "Luton Town", "Burnley", "Sheffield United"}
            fallback_elite = {"Manchester City", "Arsenal", "Manchester United", "Newcastle United"}
            return fallback_pl, fallback_elite

    def build_universal_fixtures(self, pl_baseline: set[str], elite_cohort: set[str]) -> list[dict]:
        """
        Compiles the calendar via SoccerData and converts game details into the 
        dictionary structure expected by your processing loop, bypassing 'seasons' errors.
        """
        print("\n[*] STEP 2: Scanning competitions with baseline-expanded split filtering...")
        universal_fixtures = []
        sd_year = f"20{self.year_ss.split('/')[0]}"
        
        # Map human competition names to SoccerData league IDs
        comp_mapping = {
            "England Premier League": "ENG-Premier League",
            "UEFA Champions League": "INT-Champions League"
        }
        
        for comp_name, sd_league in comp_mapping.items():
            try:
                print(f"    -> Pulling calendar fixtures for '{comp_name}'...")
                mh = sd.MatchHistory(leagues=sd_league, seasons=sd_year)
                df_games = mh.read_games().reset_index()
                
                comp_matches_count = 0
                for _, row in df_games.iterrows():
                    h_team = row.get('home_team')
                    a_team = row.get('away_team')
                    
                    # Apply your multi-tier comparative logic
                    keep_match = False
                    if comp_name == "England Premier League":
                        keep_match = True
                    elif comp_name == "UEFA Champions League":
                        if h_team in pl_baseline or a_team in pl_baseline:
                            keep_match = True
                            
                    if keep_match:
                        # Reconstruct the SofaScore dictionary structure your Step 3 loop relies on
                        # Note: SofaScore match IDs from soccerdata index keys are extracted safely
                        m_id = row.get('game_id') if 'game_id' in row else row.get('match_id')
                        if pd.isna(m_id) or not m_id:
                            # Fallback dummy tracking index if ID is hidden
                            m_id = hash(f"{h_team}_{a_team}_{row.get('date')}")
                        
                        # Convert timestamp to standard seconds Unix format
                        game_date = pd.to_datetime(row.get('date'))
                        unix_ts = int(game_date.timestamp())
                        
                        match_dict = {
                            "id": int(abs(m_id)) % 10000000, # Normalize to clean integer space
                            "homeTeam": {"name": h_team},
                            "awayTeam": {"name": a_team},
                            "startTimestamp": unix_ts,
                            "_target_competition": comp_name
                        }
                        universal_fixtures.append(match_dict)
                        comp_matches_count += 1
                        
                print(f"       [+] Retained {comp_matches_count} contextual fixtures from {comp_name}")
            except Exception as e:
                print(f"       [⚠️] Failed to load calendar for '{comp_name}' via SoccerData: {e}")

        universal_fixtures = sorted(universal_fixtures, key=lambda x: x.get('startTimestamp', 0))
        print(f"[✅] Completed integration: Isolated {len(universal_fixtures)} total matches for comparative analytics.")
        return universal_fixtures


    def fetch_match_player_stats_with_cache(self, match_id: int) -> pd.DataFrame | None:
        """
        Reads local cache to save time and avoid API blocks.
        Falls back to scraping player stats, tactical average positions, and match shots if missing.
        """
        cache_file = self.cache_dir / f"match_{match_id}.csv"
        cache_pos_file = self.cache_dir / f"match_{match_id}_positions.csv"
        cache_shots_file = self.cache_dir / f"match_{match_id}_shots.csv"
        
        if cache_file.exists():
            return pd.read_csv(cache_file)
            
        try:
            print(f"    -> [🌐 Scrape] Fetching expanded live match data for ID: {match_id}")
            time.sleep(self.delay)
            
            # 1. Performance Statistics Scrape
            df_match = self.scraper.scrape_player_match_stats(match_id)
            if df_match is not None and not df_match.empty:
                df_match = df_match.reset_index(drop=True)
                df_match = df_match.loc[:, ~df_match.columns.duplicated()].copy()
                df_match.to_csv(cache_file, index=False)
            else:
                return None
                
            # 2. Tactical Average Positions (Centro de Gravedad Táctico)
            try:
                time.sleep(self.delay)
                df_pos = self.scraper.scrape_player_average_positions(match_id)
                if df_pos is not None:
                    if isinstance(df_pos, pd.DataFrame) and not df_pos.empty:
                        df_pos.to_csv(cache_pos_file, index=False)
                    elif isinstance(df_pos, dict) and df_pos:
                        pd.DataFrame(df_pos).to_csv(cache_pos_file, index=False)
            except Exception as e_pos:
                print(f"      [⚠️] Tactical positions profile skipped/failed for Match {match_id}: {e_pos}")

            # 3. Completion Mapping & Shot xG Values
            try:
                time.sleep(self.delay)
                df_shots = self.scraper.scrape_match_shots(match_id)
                if df_shots is not None:
                    if isinstance(df_shots, pd.DataFrame) and not df_shots.empty:
                        df_shots.to_csv(cache_shots_file, index=False)
                    elif isinstance(df_shots, dict) and df_shots:
                        pd.DataFrame(df_shots).to_csv(cache_shots_file, index=False)
            except Exception as e_shots:
                print(f"      [⚠️] Match shots mapping profile skipped/failed for Match {match_id}: {e_shots}")
                
            return df_match
            
        except Exception as e:
            print(f"      [⚠️] Scraping exception on Match ID {match_id}: {e}")
        return None

    def execute_pipeline(self) -> pd.DataFrame:
        # Step 1: Discover complete baseline map and tracking cohort
        pl_baseline, elite_cohort = self.discover_pl_teams()
        if not pl_baseline:
            return pd.DataFrame()
            
        # Step 2: Grab the balanced multi-league fixture calendar
        fixtures = self.build_universal_fixtures(pl_baseline, elite_cohort)
        if not fixtures:
            return pd.DataFrame()
            
        all_compiled_records = []
        print("\n[*] STEP 3: Processing player performance matrix match-by-match...")
        
        for idx, match in enumerate(fixtures):
            match_id = match.get('id')
            comp = match.get('_target_competition')
            home_team = match.get('homeTeam', {}).get('name', 'Unknown')
            away_team = match.get('awayTeam', {}).get('name', 'Unknown')
            
            ts = match.get('startTimestamp') or match.get('status', {}).get('startTimestamp', 0)
            match_date = pd.to_datetime(ts, unit='s').strftime('%Y-%m-%d')
            
            print(f"    [{idx+1}/{len(fixtures)}] [{comp}] {match_date} | {home_team} vs {away_team}")
            
            df_match = self.fetch_match_player_stats_with_cache(match_id)
            if df_match is None or df_match.empty:
                continue
                
            df_match['match_id'] = match_id
            df_match['match_date_str'] = match_date
            df_match['competition'] = comp
            df_match['home_team_name'] = home_team
            df_match['away_team_name'] = away_team
            
            all_compiled_records.append(df_match)
            
        if not all_compiled_records:
            return pd.DataFrame()
            
        df_master = pd.concat(all_compiled_records, ignore_index=True)
        df_master['date'] = pd.to_datetime(df_master['match_date_str'])

        # Export raw intermediate — subsumes the former standalone raw_downloader module
        season_str = self.year_ss.replace("/", "_")
        raw_file = self.output_dir / f"raw_pl_centric_player_matches_{season_str}.csv"
        df_master.to_csv(raw_file, index=False)
        print(f"    [💾] Raw match-level data exported to {raw_file}")

        player_col = next((c for c in ['player_name', 'player', 'name'] if c in df_master.columns), df_master.columns[0])
        
        # --- STEP 4: Advanced Cross-Competition Feature Engineering ---
        print("\n[*] STEP 4: Engineering time-series fatigue workloads and categorical classifications...")
        df_master = df_master.sort_values(by=[player_col, 'date']).reset_index(drop=True)
        
        # A. Inject Categorical Slicing Fields for Easy Comparative Analysis
        df_master['match_type'] = np.where(df_master['competition'] == "UEFA Champions League", "European", "Domestic")
        df_master['cohort_group'] = np.where(df_master['teamName'].isin(elite_cohort), "Elite", "Baseline")
        
        # B. Fatigue Workload Calculations
        df_master['rest_days'] = df_master.groupby(player_col)['date'].diff().dt.days
        df_master['rest_days'] = df_master['rest_days'].fillna(14).astype(int)
        df_master['high_congestion_flag'] = np.where(df_master['rest_days'] <= 3, 1, 0)
        
        df_master.set_index('date', inplace=True)
        if 'minutesPlayed' in df_master.columns:
            df_master['minutesPlayed'] = df_master['minutesPlayed'].fillna(0).astype(int)
            df_master['min_last_7d'] = df_master.groupby(player_col)['minutesPlayed'].rolling('7D', closed='left').sum().reset_index(0, drop=True)
            df_master['min_last_28d'] = df_master.groupby(player_col)['minutesPlayed'].rolling('28D', closed='left').sum().reset_index(0, drop=True)
        df_master.reset_index(inplace=True)
        
        df_master['min_last_7d'] = df_master['min_last_7d'].fillna(0).astype(int)
        df_master['min_last_28d'] = df_master['min_last_28d'].fillna(0).astype(int)
        
        df_master['acwr_ratio'] = np.where(
            df_master['min_last_28d'] > 0, 
            df_master['min_last_7d'] / (df_master['min_last_28d'] / 4.0), 
            0.0
        )

        # C. Travel and Rotational Centroids
        df_master['is_away'] = np.where(df_master['teamName'] == df_master['away_team_name'], 1, 0)
        df_master['consecutive_away_games'] = df_master.groupby(player_col)['is_away'].transform(lambda x: x.groupby((x != x.shift()).cumsum()).cumsum())

        if 'duelsWon' in df_master.columns and 'duelsLost' in df_master.columns:
            total_duels = df_master['duelsWon'].fillna(0) + df_master['duelsLost'].fillna(0)
            df_master['match_intensity_proxy'] = np.where(df_master['minutesPlayed'] > 0, total_duels / df_master['minutesPlayed'], 0.0)
            df_master.set_index('date', inplace=True)
            df_master['player_historical_intensity_28d'] = df_master.groupby(player_col)['match_intensity_proxy'].rolling('28D', closed='left').mean().reset_index(0, drop=True)
            df_master.reset_index(inplace=True)
            df_master['player_historical_intensity_28d'] = df_master['player_historical_intensity_28d'].fillna(0)

        if 'age' in df_master.columns:
            df_master['squad_age_average'] = df_master.groupby(['match_id', 'teamName'])['age'].transform('mean')

        # Lineup Rotation Matrix (Churn)
        match_lineups = df_master[df_master['minutesPlayed'] > 0].groupby(['teamName', 'match_id'])['name'].apply(set).reset_index()
        match_lineups = match_lineups.merge(df_master[['match_id', 'match_date_str']].drop_duplicates(), on='match_id')
        match_lineups = match_lineups.sort_values(by=['teamName', 'match_date_str'])
        
        match_lineups['prev_lineup'] = match_lineups.groupby('teamName')['name'].shift(1)
        match_lineups['lineup_churn'] = match_lineups.apply(
            lambda r: len(r['name'] - r['prev_lineup']) if isinstance(r['prev_lineup'], set) else 0, axis=1
        )
        
        df_master = pd.merge(df_master, match_lineups[['match_id', 'teamName', 'lineup_churn']], on=['match_id', 'teamName'], how='left')
        df_master['lineup_churn'] = df_master['lineup_churn'].fillna(0).astype(int)

        # --- STEP 5: SoccerData Context Matching & Understat Integration ---
        print("\n[*] STEP 5: Stitching contextual data via SoccerData & Understat...")
        
        team_map = {
            "Brighton & Hove Albion": "Brighton", "Newcastle United": "Newcastle", "Liverpool FC": "Liverpool",
            "Nottingham Forest": "Nottingham Forest", "Brentford": "Brentford", "West Ham United": "West Ham",
            "Bournemouth": "Bournemouth", "Leicester City": "Leicester", "Chelsea": "Chelsea",
            "Wolverhampton": "Wolves", "Southampton": "Southampton", "Crystal Palace": "Crystal Palace",
            "Ipswich Town": "Ipswich", "Manchester City": "Man City", "Fulham": "Fulham",
            "Everton": "Everton", "Tottenham Hotspur": "Tottenham", "Manchester United": "Man United",
            "Aston Villa": "Aston Villa", "Arsenal": "Arsenal"
        }
        df_master['teamName_standardized'] = df_master['teamName'].replace(team_map)
        df_master['home_team_standardized'] = df_master['home_team_name'].replace(team_map)

        # A. Club Elo Matching
        try:
            elo_client = sd.ClubElo()
            df_elo = elo_client.read_by_date().reset_index()
            df_elo.columns = [str(c).lower() for c in df_elo.columns]
            
            df_elo['from'] = pd.to_datetime(df_elo['from'])
            df_elo['to'] = pd.to_datetime(df_elo['to'])
            df_master['elo'] = np.nan
            
            for unique_team in df_master['teamName_standardized'].unique():
                team_elo_hist = df_elo[df_elo['team'] == unique_team]
                if team_elo_hist.empty: continue
                
                master_team_mask = df_master['teamName_standardized'] == unique_team
                team_match_dates = pd.to_datetime(df_master.loc[master_team_mask, 'match_date_str'])
                
                elo_values = []
                for m_date in team_match_dates:
                    matched_row = team_elo_hist[(team_elo_hist['from'] <= m_date) & (team_elo_hist['to'] >= m_date)]
                    if not matched_row.empty:
                        elo_values.append(matched_row['elo'].values[0])
                    else:
                        closest_row = team_elo_hist.iloc[(team_elo_hist['from'] - m_date).abs().argsort()[:1]]
                        elo_values.append(closest_row['elo'].values[0] if not closest_row.empty else np.nan)
                        
                df_master.loc[master_team_mask, 'elo'] = elo_values
            print("    [✅] ClubELO data integrated via temporal windows.")
        except Exception as e:
            print(f"    [⚠️] ClubELO integration failed: {e}")

        # B. Understat Matching
        understat_file = get_understat_path()
        if understat_file.exists():
            try:
                print("    -> Merging multi-competition Understat tactical load metrics...")
                df_us = pd.read_csv(understat_file)
                df_us['date'] = pd.to_datetime(df_us['date'])
                df_master['date_dt'] = pd.to_datetime(df_master['match_date_str'])
                
                df_us['home_team'] = df_us['home_team'].replace({"Manchester Utd": "Man United", "Tottenham": "Tottenham"})
                
                us_cols = ['date', 'home_team', 'home_xg', 'away_xg']
                valid_us_cols = [c for c in us_cols if c in df_us.columns]
                
                df_master = pd.merge(
                    df_master,
                    df_us[valid_us_cols],
                    left_on=['date_dt', 'home_team_standardized'],
                    right_on=['date', 'home_team'],
                    how='left',
                    suffixes=('', '_us_raw')
                )
                
                if 'home_xg' in df_master.columns and 'away_xg' in df_master.columns:
                    df_master['team_xg'] = np.where(df_master['is_away'] == 0, df_master['home_xg'], df_master['away_xg'])
                    df_master['team_xga'] = np.where(df_master['is_away'] == 0, df_master['away_xg'], df_master['home_xg'])
                    df_master['xg_difference'] = df_master['team_xg'] - df_master['team_xga']
                
                print("    [✅] Understat target and load features stitched successfully.")
            except Exception as e:
                print(f"    [⚠️] Understat merge failed: {e}")
        else:
            print("    [⚠️] fixtureiq_understat_master.csv not found. Skipping tactical metrics.")

        drop_cols = ['teamName_standardized', 'home_team_standardized', 'date_dt', 'date_us_raw', 'home_team_us_raw']
        df_master = df_master.drop(columns=[c for c in drop_cols if c in df_master.columns], errors='ignore')

        return df_master

    def export(self, df: pd.DataFrame):
        if df.empty: return
        
        df.to_csv(self.output_dir / "fixtureiq_dynamic_master.csv", index=False)
        
        # DATA MODELING LAYER: Categorized and optimized for Machine Learning Models
        features = [
            # Sorting Identity Parameters
            'match_date_str', 'match_id', 'competition', 'teamName', 'player_name', 'name', 'position', 'rating', 'elo',
            
            # The Newly Configured Categorical Slits for On-the-Fly Baseline Comparisons
            'match_type', 'cohort_group',
            
            # Logistic and Travel Context
            'is_away', 'consecutive_away_games',
            
            # Mechanical Fatigue Predictors (X - Stressors)
            'minutesPlayed', 'rest_days', 'high_congestion_flag', 'min_last_7d', 'acwr_ratio',
            'lineup_churn', 'squad_age_average', 'player_historical_intensity_28d',
            
            # Individual Functional Performance Indicators (Y - Target Track 1)
            'duel_success_pct', 'turnovers_per_90min',
            
            # Team Tactical Performance Matrix (Y - Target Track 2)
            'team_xg', 'team_xga', 'xg_difference'
        ]
        
        valid_features = [f for f in features if f in df.columns]
        df_clean = df[valid_features]
        
        # Exclude Goalkeepers to prevent skewed field physical fatigue distributions
        if 'position' in df_clean.columns:
            df_clean = df_clean[df_clean['position'] != 'G']
            
        df_clean.to_csv(self.output_dir / "fixtureiq_dynamic_analytics_clean.csv", index=False)
        print(f"\n[🚀] SUCCESSFUL DYNAMIC GENERATION WITH BASELINE-EXPANDED DATA MODEL!")
        print(f"    -> Analytics Layer Location: {self.output_dir / 'fixtureiq_dynamic_analytics_clean.csv'}")
        print(f"    -> Full Feature Matrix Shape: {df_clean.shape}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FixtureIQ Fully Dynamic Season Baseline Mapper")
    parser.add_argument("--year", default="24/25", help="SofaScore short season code (e.g. 24/25)")
    parser.add_argument("--output-dir", default=None, help="Export folder (defaults to data/<season>/sofascore_dynamic/)")
    args = parser.parse_args()
    
    pipeline = FixtureIQDynamicPipeline(year_sofascore=args.year, output_dir=args.output_dir)
    master_df = pipeline.execute_pipeline()
    pipeline.export(master_df)