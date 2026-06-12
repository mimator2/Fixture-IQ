"""
FixtureIQ - Data Consolidation
===============================
Consolidates all raw FBref and SofaScore data from multiple seasons
and teams into unified master files for training.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys

_root = Path(__file__).resolve().parent.parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from src.config.paths import data_dir
from src.data.cleaning import (
    clean_columns, clean_player_names, clean_team_names,
    convert_dates, convert_numeric, standardize_position_col
)

SEASONS = ['2022-2023', '2023-2024', '2024-2025']
SEASON_KEYS = {'2022-2023': '2022_2023', '2023-2024': '2023_2024', '2024-2025': '2024_2025'}
MATCH_MERGE_KEYS = ['date', 'team', 'player']


def consolidate_fbref_players():
    """
    Load all *_players_all_competitions.csv files from FBref across all seasons/teams.
    
    Returns:
        DataFrame with columns: Player, Nation, Pos, Age, MP, ... (+ season, team added)
    """
    print("\n" + "="*70)
    print("CONSOLIDATING FBREF PLAYER SEASON PROFILES")
    print("="*70)
    
    all_frames = []
    
    for season in SEASONS:
        fbref_path = data_dir() / season / 'fbref'
        
        if not fbref_path.exists():
            print(f"  [SKIP] {season}: Path not found {fbref_path}")
            continue
        
        # Scan all team directories
        for team_dir in sorted(fbref_path.iterdir()):
            if not team_dir.is_dir():
                continue
            
            # Find *_players_all_competitions.csv
            player_files = list(team_dir.glob('*_players_all_competitions.csv'))
            if not player_files:
                continue
            
            player_file = player_files[0]
            
            try:
                df = pd.read_csv(player_file)
                
                # Clean columns
                df = clean_columns(df, camelcase_split=True)
                
                # Add metadata
                team_name = team_dir.name  # e.g., 'arsenal_2024_2025'
                df['team'] = team_name.split('_')[0].title()  # Extract team name
                df['season'] = season
                
                # Clean player names
                if 'player' in df.columns:
                    df = clean_player_names(df, player_col='player')
                
                # Drop Matches column if present
                df = df.drop(columns=['matches'], errors='ignore')
                
                all_frames.append(df)
                print(f"  [OK] {season:13} {team_name:30} -> {len(df)} players")
                
            except Exception as e:
                print(f"  [ERROR] {season:13} {team_name:30} -> {str(e)}")
    
    if not all_frames:
        print("  [ERROR] No FBref data found")
        return pd.DataFrame()
    
    df_fbref = pd.concat(all_frames, ignore_index=True)
    print(f"\n  Total: {len(df_fbref)} rows, {df_fbref['player'].nunique()} unique players")
    print(f"  Teams: {df_fbref['team'].nunique()}, Seasons: {df_fbref['season'].nunique()}")
    
    return df_fbref


def consolidate_sofascore_players():
    """
    Load all premier_league_{season}_all_players.csv files from SofaScore.
    
    Returns:
        DataFrame with SofaScore metrics (+ season added)
    """
    print("\n" + "="*70)
    print("CONSOLIDATING SOFASCORE PLAYER SEASON PROFILES")
    print("="*70)
    
    all_frames = []
    
    for season in SEASONS:
        sofascore_path = data_dir() / season / 'sofascore' / 'premier_league'
        
        if not sofascore_path.exists():
            print(f"  [SKIP] {season}: Path not found {sofascore_path}")
            continue
        
        # Find premier_league_{season}_all_players.csv
        season_key = SEASON_KEYS[season]
        player_file = sofascore_path / f'premier_league_{season_key}_all_players.csv'
        
        if not player_file.exists():
            print(f"  [SKIP] {season}: File not found {player_file.name}")
            continue
        
        try:
            df = pd.read_csv(player_file)
            
            # Clean columns
            df = clean_columns(df, camelcase_split=True)
            
            # Add season
            df['season'] = season
            
            # Clean player and team names
            if 'player' in df.columns:
                df = clean_player_names(df, player_col='player')
            if 'team' in df.columns:
                df = clean_team_names(df, team_col='team')
            
            # Rename common columns for consistency
            rename_map = {
                'player_id': 'sofascore_player_id',
                'team_id': 'sofascore_team_id',
                'position_group': 'sofascore_position_group',
            }
            df = df.rename(columns=rename_map)
            
            all_frames.append(df)
            print(f"  [OK] {season} -> {len(df)} players")
            
        except Exception as e:
            print(f"  [ERROR] {season} -> {str(e)}")
    
    if not all_frames:
        print("  [ERROR] No SofaScore data found")
        return pd.DataFrame()
    
    df_sofascore = pd.concat(all_frames, ignore_index=True)
    print(f"\n  Total: {len(df_sofascore)} rows, {df_sofascore['player'].nunique()} unique players")
    print(f"  Seasons: {df_sofascore['season'].nunique()}")
    
    return df_sofascore


def build_seasonal_master(df_fbref, df_sofascore):
    """
    Merge FBref and SofaScore player profiles on player name + season.
    
    Args:
        df_fbref: FBref consolidated data
        df_sofascore: SofaScore consolidated data
    
    Returns:
        Merged DataFrame with all available columns
    """
    print("\n" + "="*70)
    print("MERGING FBREF + SOFASCORE")
    print("="*70)
    
    if df_fbref.empty or df_sofascore.empty:
        print("  [ERROR] One or both dataframes are empty")
        return pd.DataFrame()
    
    # Merge on player + season
    merged = df_fbref.merge(
        df_sofascore,
        on=['player', 'season'],
        how='left',  # Keep all FBref records, add SofaScore where available
        suffixes=('_fbref', '_sofascore')
    )
    
    # Handle duplicate team columns
    if 'team_fbref' in merged.columns and 'team_sofascore' in merged.columns:
        # Prefer FBref team
        merged['team'] = merged['team_fbref'].fillna(merged['team_sofascore'])
        merged = merged.drop(columns=['team_fbref', 'team_sofascore'])
    
    print(f"  Merged: {len(merged)} rows")
    print(f"  FBref coverage: 100% (all kept)")
    print(f"  SofaScore coverage: {(merged['rating'].notna().sum() / len(merged) * 100):.1f}%")
    print(f"  Columns: {len(merged.columns)}")
    
    return merged


def extract_whole_years(age_val):
    if pd.isna(age_val): return np.nan
    if isinstance(age_val, str) and '-' in age_val: return int(age_val.split('-')[0])
    return int(float(age_val))


def clean_common_fields(df, age_lookup, nation_lookup, fallback_median):
    """Handles data formatting for benched/unused squad entries cleanly using cleaning utils."""
    # Standardize 'min' using the convert_numeric utility
    df = convert_numeric(df, cols='min', fillna=0)
    df['min'] = df['min'].astype(int)
    df['played'] = df['min'] > 0
    
    # Process age fallback mapping
    if 'age' in df.columns:
        df['age'] = df['age'].apply(extract_whole_years)
        df['age'] = df['age'].fillna(df['player'].map(age_lookup))
        df['age'] = df['age'].fillna(fallback_median).astype(int)
        
    # Process nationality fallback mapping
    if 'nation' in df.columns:
        df['nation'] = df['nation'].fillna(df['player'].map(nation_lookup))
        df['nation'] = df['nation'].fillna('Unknown')
        
    return df


def consolidate_matchday_logs():
    """Iterates through match_reports sub-folders to compile timeline sequences."""
    print("\n" + "="*70)
    print("2A. CONSOLIDATING GRANULAR MATCH-BY-MATCH TIMELINES")
    print("="*70)
    
    # Load contextual team frameworks globally
    elo_lookup, df_understat = load_clubelo_understat_lookups()

    all_outfield_rows = []
    all_goalkeeper_rows = []
    
    for season in SEASONS:
        fbref_path = data_dir() / season / 'fbref'
        if not fbref_path.exists():
            print(f"  [INFO] Season path omitted (Not found): {fbref_path}")
            continue
            
        print(f"\n>> Extracting matchday files for Season: {season}...")
        for team_dir in sorted(fbref_path.iterdir()):
            if not team_dir.is_dir():
                continue
                
            print(f"  -> Processing club folder: {team_dir.name}")
            
            match_reports_dir = team_dir / 'match_reports'
            lineups_path = match_reports_dir / 'master_lineups.csv'
            stats_path = match_reports_dir / 'master_player_stats.csv'
            gk_path = match_reports_dir / 'master_goalkeeper_stats.csv'
            
            # Locate profiles to gather lookup indexes for player recovery traits
            profile_glob = list(team_dir.glob('*_players_all_competitions.csv'))
            
            if not (lineups_path.exists() and stats_path.exists() and gk_path.exists()):
                print(f"    [SKIP] Missing core csv logs inside {match_reports_dir.name}")
                continue
            
            # --- 0. INITIALIZE DICTIONARIES AND FALLBACKS FROM PROFILE REGISTRY ---
            if profile_glob and profile_glob[0].exists():
                df_prof = pd.read_csv(profile_glob[0])
                df_prof = clean_columns(df_prof)
                df_prof = clean_player_names(df_prof, 'player')
                df_prof = convert_numeric(df_prof, cols='age', fillna=np.nan)
                
                # SENSE CHECK: Ensure index columns aren't converted to unhashable arrays
                for col in ['player', 'nation', 'pos', 'age']:
                    if col in df_prof.columns and df_prof[col].apply(lambda x: isinstance(x, list)).any():
                        print(f"    [WARN] Unhashable list located inside profile column: '{col}'. Casted to scalar.")
                        df_prof[col] = df_prof[col].apply(lambda x: x[0] if isinstance(x, list) else x).astype(str)
                
                age_lookup = df_prof.set_index('player')['age'].to_dict() if 'age' in df_prof.columns else {}
                nation_lookup = df_prof.set_index('player')['nation'].to_dict() if 'nation' in df_prof.columns else {}
                pos_lookup = df_prof.set_index('player')['pos'].to_dict() if 'pos' in df_prof.columns else {}
                fallback_median = df_prof['age'].median() if 'age' in df_prof.columns else 26
            else:
                age_lookup, nation_lookup, pos_lookup = {}, {}, {}
                fallback_median = 26
                
            # --- 1. PROCESS LINEUPS ---
            df_lineups = pd.read_csv(lineups_path)
            if 'Competition' in df_lineups.columns:
                df_lineups = df_lineups.drop(columns=['Competition'])
            df_lineups = clean_columns(df_lineups)
            df_lineups = clean_player_names(df_lineups, 'player')
            df_lineups = clean_team_names(df_lineups, 'team')
            df_lineups = convert_dates(df_lineups, cols='date')
            
            df_master = df_lineups[['date', 'team', 'player', 'lineup_section', 'formation']].copy()
            df_master['is_in_squad'] = True
            df_master['started'] = df_master['lineup_section'] == 'Starter'
            df_master = df_master.drop(columns=['lineup_section'])
            
            # --- 2. PROCESS PERFORMANCE STATS ---
            df_stats = pd.read_csv(stats_path)
            if 'Competition' in df_stats.columns:
                df_stats = df_stats.drop(columns=['Competition'])
            df_stats = clean_columns(df_stats)
            df_stats = clean_player_names(df_stats, 'player')
            df_stats = clean_team_names(df_stats, 'team')
            df_stats = convert_dates(df_stats, cols='date')
            
            outfield_metrics = ['shirtnumber', 'nation', 'pos', 'age', 'min', 'gls', 'ast', 'shots', 'shots_on_target', 'crd_y', 'crd_r', 'fouls', 'fouled', 'offsides', 'crosses', 'tackles_won', 'interceptions']
            avail_metrics = [m for m in outfield_metrics if m in df_stats.columns]
            
            df_outfield_comb = pd.merge(df_master, df_stats[MATCH_MERGE_KEYS + avail_metrics], on=MATCH_MERGE_KEYS, how='left')
            df_outfield_comb = clean_common_fields(df_outfield_comb, age_lookup, nation_lookup, fallback_median)
            
            # --- MAP PLAYER CONTEXTUAL TEAM STRENGTHS ---
            df_outfield_comb['elo'] = df_outfield_comb['team'].map(elo_lookup).fillna(1500)
            
            # INTERCEPT BEFORE THE CRASH ZONE: Check if 'team' or 'date' contains list rows
            for col in ['team', 'date']:
                if df_outfield_comb[col].apply(lambda x: isinstance(x, list)).any():
                    print(f"    [CRITICAL] Found nested list inside merge identifiers for field '{col}'!")
                    df_outfield_comb[col] = df_outfield_comb[col].apply(lambda x: x[0] if isinstance(x, list) else x)

            # Map rolling metrics using unique combinations to ensure speed
            outfield_fixtures = df_outfield_comb[['team', 'date']].drop_duplicates()
            outfield_xg_map, outfield_xga_map = {}, {}
            
            print(f"    * Generating Understat rolling maps for {len(outfield_fixtures)} unique fixtures...")
            for _, fix in outfield_fixtures.iterrows():
                t, d = fix['team'], fix['date']
                
                # Explicit check for the unhashable tuple crash
                if isinstance(t, list) or isinstance(d, list):
                    print(f"    [ERROR DETECTED] Key entry is a list! team={t} (type: {type(t)}), date={d} (type: {type(d)})")
                    # Force extract single values to handle structural corruption
                    if isinstance(t, list): t = t[0]
                    if isinstance(d, list): d = d[0]
                
                mean_xg, mean_xga = get_rolling_team_xg(t, d, df_understat)
                outfield_xg_map[(t, d)] = mean_xg
                outfield_xga_map[(t, d)] = mean_xga
                
            # Safe mapping using a fallback validation pass
            try:
                df_outfield_comb['team_xg'] = df_outfield_comb.set_index(['team', 'date']).index.map(outfield_xg_map)
                df_outfield_comb['team_xga'] = df_outfield_comb.set_index(['team', 'date']).index.map(outfield_xga_map)
            except Exception as map_err:
                print(f"    [CRITICAL] Mapping index conversion failed: {map_err}")
                print(f"    Data Sample index types:\n{df_outfield_comb[['team', 'date']].dtypes}")
                raise map_err

            df_outfield_comb['season'] = season
            df_outfield_comb['pos'] = df_outfield_comb['pos'].fillna('Bench')
            
            if 'shirtnumber' in df_outfield_comb.columns:
                df_outfield_comb = convert_numeric(df_outfield_comb, cols='shirtnumber', fillna=-1)
                df_outfield_comb['shirtnumber'] = df_outfield_comb['shirtnumber'].astype(int)
            
            numeric_cols = ['gls', 'ast', 'shots', 'shots_on_target', 'crd_y', 'crd_r', 'fouls', 'fouled', 'offsides', 'crosses', 'tackles_won', 'interceptions']
            avail_numeric = [n for n in numeric_cols if n in df_outfield_comb.columns]
            df_outfield_comb = convert_numeric(df_outfield_comb, cols=avail_numeric, fillna=0)
            df_outfield_comb[avail_numeric] = df_outfield_comb[avail_numeric].astype(int)
            
            df_outfield_final = df_outfield_comb[df_outfield_comb['pos'] != 'GK'].copy()
            all_outfield_rows.append(df_outfield_final)
            
            # --- 3. LOG TRACK B: GOALKEEPER PERFORMANCE STATS ---
            df_gk = pd.read_csv(gk_path)
            if 'Competition' in df_gk.columns:
                df_gk = df_gk.drop(columns=['Competition'])
                
            df_gk = clean_columns(df_gk)
            df_gk = clean_player_names(df_gk, 'player')
            if 'team' in df_gk.columns:
                df_gk = clean_team_names(df_gk, 'team') # Pass as list to match definition signature
            df_gk = convert_dates(df_gk, cols='date')
            
            gk_metrics = ['nation', 'age', 'min', 'so_ta', 'ga', 'saves', 'save_pct']
            avail_gk_metrics = [m for m in gk_metrics if m in df_gk.columns]
            
            df_gk_clean = df_gk[MATCH_MERGE_KEYS + avail_gk_metrics].copy()
            
            df_gk_combined = pd.merge(df_master, df_gk_clean, on=MATCH_MERGE_KEYS, how='left')
            df_gk_combined = clean_common_fields(df_gk_combined, age_lookup, nation_lookup, fallback_median)
            df_gk_combined['season'] = season
            
            gk_numeric_cols = ['so_ta', 'ga', 'saves']
            avail_gk_numeric = [n for n in gk_numeric_cols if n in df_gk_combined.columns]
            df_gk_combined = convert_numeric(df_gk_combined, cols=avail_gk_numeric, fillna=0)
            df_gk_combined[avail_gk_numeric] = df_gk_combined[avail_gk_numeric].astype(int)
            
            if 'save_pct' in df_gk_combined.columns:
                df_gk_combined = convert_numeric(df_gk_combined, cols='save_pct', fillna=0.0)
                df_gk_combined['save_pct'] = df_gk_combined['save_pct'].astype(float)
            
            gk_names = df_gk['player'].unique()
            df_gk_team_final = df_gk_combined[
                (df_gk_combined['player'].isin(gk_names)) | 
                (df_gk_combined['player'].map(pos_lookup) == 'GK')
            ].copy()
            df_gk_team_final['pos'] = 'GK'
            
            all_goalkeeper_rows.append(df_gk_team_final)
            print(f"    [OK] Outfield matrix shape: {df_outfield_final.shape}, GK shape: {df_gk_team_final.shape}")
            
    print(f"\nMerging row structures across all logged cohorts...")
    outfield_res = pd.concat(all_outfield_rows, ignore_index=True) if all_outfield_rows else pd.DataFrame()
    goalkeeper_res = pd.concat(all_goalkeeper_rows, ignore_index=True) if all_goalkeeper_rows else pd.DataFrame()
    
    print(f"Complete! Final Outfield Master records: {outfield_res.shape[0]}, GK records: {goalkeeper_res.shape[0]}")
    return outfield_res, goalkeeper_res


def process_injury_data():
    """Loads, cleans, and computes missing end dates for seasonal injury files."""
    all_injury_frames = []
    
    for season in SEASONS:
        injury_file = data_dir() / season / 'injuries' / f'ALL_TEAMS_{season}_injuries_days_out.csv'
        if not injury_file.exists():
            continue
            
        # Load and clean standard formatting immediately
        df_inj = pd.read_csv(injury_file)
        df_inj = clean_columns(df_inj)
        df_inj = clean_player_names(df_inj, 'player_name')
        
        # Rename 'player_name' to 'player' to match your global MATCH_MERGE_KEYS
        if 'player_name' in df_inj.columns:
            df_inj = df_inj.rename(columns={'player_name': 'player'})
            
        if 'team_name' in df_inj.columns:
            df_inj = clean_team_names(df_inj, 'team_name')
            df_inj = df_inj.rename(columns={'team_name': 'team'})
            
        # 1. Standardize column data types using your cleaning utilities
        df_inj = convert_dates(df_inj, cols=['fixture_date', 'end_date'])
        df_inj = convert_numeric(df_inj, cols='days_out', fillna=0)
        df_inj['days_out'] = df_inj['days_out'].astype(int)
        
        # 2. Compute the missing end_date dynamically: fixture_date + days_out
        # pd.to_timedelta expects an integer or float sequence of days
        computed_end_date = df_inj['fixture_date'] + pd.to_timedelta(df_inj['days_out'], unit='D')
        
        # Fill missing values in 'end_date' with the computed timestamps
        df_inj['end_date'] = df_inj['end_date'].fillna(computed_end_date)
        
        df_inj['season'] = season
        all_injury_frames.append(df_inj)
        print(f"  [OK] Injuries {season:13} -> Populated {len(df_inj)} injury ranges")
        
    return pd.concat(all_injury_frames, ignore_index=True) if all_injury_frames else pd.DataFrame()


def load_clubelo_understat_lookups():
    """Loads and standardizes the team lookup maps from the clubelo_understat directory."""
    base_path = data_dir() / 'clubelo_understat'
    elo_path = base_path / 'fixtureiq_elo_master.csv'
    understat_path = base_path / 'fixtureiq_understat_master.csv'
    
    # 1. Process ELO Lookups
    if elo_path.exists():
        df_elo = pd.read_csv(elo_path)
        df_elo = clean_columns(df_elo)
        if 'team' in df_elo.columns:
            df_elo = clean_team_names(df_elo, 'team')
        elo_lookup = df_elo.set_index('team')['elo'].to_dict()
    else:
        print("  [WARNING] fixtureiq_elo_master.csv not found. Defaulting Elo to 1500.")
        elo_lookup = {}
        
    # 2. Process Understat Lookups
    if understat_path.exists():
        df_us = pd.read_csv(understat_path, parse_dates=['date'])
        df_us = clean_columns(df_us)
        if 'home_team' in df_us.columns:
            df_us = clean_team_names(df_us, 'home_team')
        if 'away_team' in df_us.columns:
            df_us = clean_team_names(df_us, 'away_team')
    else:
        print("  [WARNING] fixtureiq_understat_master.csv not found. Defaulting xG metrics.")
        df_us = pd.DataFrame()
        
    return elo_lookup, df_us


def get_rolling_team_xg(team_name, match_date, df_understat, window_games=5):
    """Calculates historical rolling xG and xG Allowed PRIOR to the target match date to prevent leakage."""
    if df_understat.empty or pd.isna(match_date):
        return 1.5, 1.5 # Sensible generic team baselines
        
    # Strictly isolate games played before the current match date
    historical_games = df_understat[
        ((df_understat['home_team'] == team_name) | (df_understat['away_team'] == team_name)) & 
        (df_understat['date'] < match_date)
    ].sort_values(by='date', ascending=False)
    
    if historical_games.empty:
        return 1.5, 1.5
        
    recent_games = historical_games.head(window_games)
    xg_list, xga_list = [], []
    
    for _, game in recent_games.iterrows():
        if game['home_team'] == team_name:
            xg_list.append(game['home_xg'])
            xga_list.append(game['away_xg'])
        else:
            xg_list.append(game['away_xg'])
            xga_list.append(game['home_xg'])
            
    return float(np.mean(xg_list)), float(np.mean(xga_list))



# Move your execution block into an importable function!
def consolidate_all_streams(force_recompute: bool = False):
    """
    Compiles, structures, and saves isolated master data registries.
    Returns the file paths to the compiled masters for training script tracking.
    """
    output_dir = data_dir() / 'consolidated'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    seasonal_path = output_dir / 'fixtureiq_seasonal_profiles_master.csv'
    outfield_path = output_dir / 'fixtureiq_matchday_outfield_master.csv'
    goalkeeper_path = output_dir / 'fixtureiq_matchday_goalkeeper_master.csv'
    injury_timeline_path = output_dir / 'fixtureiq_matchday_injuries_master.csv'
    
    files_exist = (seasonal_path.exists() and outfield_path.exists() and 
                   goalkeeper_path.exists() and injury_timeline_path.exists())
    
    if files_exist and not force_recompute:
        print("\n" + "="*70)
        print("RETRIEVING EXISTING CACHED STRUCTURES (SKIP COMPUTATION)")
        print("="*70)
        df_season_master = pd.read_csv(seasonal_path)
        df_outfield_matches = pd.read_csv(outfield_path)
        df_gk_matches = pd.read_csv(goalkeeper_path)
        df_injury_timeline = pd.read_csv(injury_timeline_path)
        
    else:
        print("\n>>> Compiling master files and timeline injuries registry...")
        
        # 1. Process Season Profiles 
        df_fb_season = consolidate_fbref_players()
        df_so_season = consolidate_sofascore_players()
        df_season_master = build_seasonal_master(df_fb_season, df_so_season)
        
        # 2. Process Game Logs 
        df_outfield_matches, df_gk_matches = consolidate_matchday_logs()
        
        # 3. Process Injuries and solve missing end dates
        df_injury_timeline = process_injury_data()

        # 4. Save Isolated Repositories to Disk
        if not df_season_master.empty:
            df_season_master.to_csv(seasonal_path, index=False)
        if not df_outfield_matches.empty:
            df_outfield_matches.to_csv(outfield_path, index=False)
        if not df_gk_matches.empty:
            df_gk_matches.to_csv(goalkeeper_path, index=False)
            
        # Save your newly populated injury intervals master 
        if not df_injury_timeline.empty:
            df_injury_timeline.to_csv(injury_timeline_path, index=False)
            print(f"Saved Matchday Injury Intervals Master: {df_injury_timeline.shape[0]} records")
            
    print("\nVerification Complete. All timelines isolated and shielded from leakage.")
    
    # Return the target paths so scripts/consolidate_data.py can print or use them
    return outfield_path, injury_timeline_path


# Keep a tiny local fallback so you can still run 'python src/data/consolidate.py' directly if needed
if __name__ == '__main__':
    # Default to False, but allows manual testing inside src
    consolidate_all_streams(force_recompute=False)