"""
FixtureIQ - Feature Engineering
================================
Functions for computing player workload and fatigue features
from raw match data.
"""

import numpy as np
import pandas as pd

# PL teams that NEVER qualified for UCL across our seasons (for comparison group)
NON_UCL_TEAMS_2024_25 = {
    'Bournemouth', 'Brentford', 'Brighton', 'Crystal Palace', 'Everton',
    'Fulham', 'Ipswich Town', 'Leicester City', 'Nottingham Forest',
    'Southampton', 'Tottenham Hotspur', 'West Ham United', 'Wolverhampton'
}

# UCL-participant PL teams per season (ground truth)
UCL_TEAMS_BY_SEASON = {
    '2022_2023': {'Chelsea', 'Liverpool', 'Manchester City', 'Tottenham Hotspur'},
    '2023_2024': {'Arsenal', 'Manchester City', 'Manchester United', 'Newcastle United'},
    '2024_2025': {'Arsenal', 'Aston Villa', 'Liverpool', 'Manchester City'},
}

# Name mapping: SofaScore names -> canonical short names
TEAM_NAME_MAP = {
    'Arsenal': 'Arsenal',
    'Aston Villa': 'Aston Villa',
    'Liverpool FC': 'Liverpool',
    'Manchester City': 'Manchester City',
    'Manchester United': 'Manchester United',
    'Newcastle United': 'Newcastle United',
    'Chelsea': 'Chelsea',
    'Tottenham Hotspur': 'Tottenham Hotspur',
    'Tottenham': 'Tottenham Hotspur',
    'Liverpool': 'Liverpool',
    'Brighton & Hove Albion': 'Brighton',
    'Brighton': 'Brighton',
    'West Ham United': 'West Ham United',
    'West Ham': 'West Ham United',
    'Wolverhampton': 'Wolverhampton',
    'Wolves': 'Wolverhampton',
    'Leicester City': 'Leicester City',
    'Leicester': 'Leicester City',
    'Ipswich Town': 'Ipswich Town',
    'Southampton': 'Southampton',
    'Bournemouth': 'Bournemouth',
    'Brentford': 'Brentford',
    'Crystal Palace': 'Crystal Palace',
    'Everton': 'Everton',
    'Fulham': 'Fulham',
    'Nottingham Forest': 'Nottingham Forest',
    "Nott'ham Forest": 'Nottingham Forest',
}

# Position encoding
POS_MAP = {'D': 0, 'M': 1, 'F': 2, 'G': 3,
           'DF': 0, 'MF': 1, 'FW': 2, 'GK': 3,
           'CB': 0, 'LB': 0, 'RB': 0,
           'CM': 1, 'DM': 1, 'AM': 1, 'LM': 1, 'RM': 1}

SEASON_MAP = {'2022_2023': 0, '2023_2024': 1, '2024_2025': 2}


def compute_rest_days(match_dates):
    return match_dates.diff().dt.days


def compute_acwr(min_last_7d, min_last_28d):
    return np.where(
        min_last_28d > 0,
        min_last_7d / (min_last_28d / 4.0),
        0.5
    )


def flag_congestion(rest_days, threshold=3):
    return (rest_days <= threshold).astype(int)


def compute_rolling_stats(df, group_col, value_col, window=5):
    avg = df.groupby(group_col)[value_col].transform(
        lambda x: x.shift(1).rolling(window, min_periods=1).mean()
    )
    std = df.groupby(group_col)[value_col].transform(
        lambda x: x.shift(1).rolling(window, min_periods=1).std()
    )
    return avg, std


def engineer_features(df):
    df = df.copy()
    df = df.sort_values(['name', 'match_date']).reset_index(drop=True)

    if 'rating' not in df.columns:
        df['rating'] = np.nan
    fbref_mask = df['source'] == 'fbref'
    if fbref_mask.any():
        df.loc[fbref_mask, 'rating'] = df.loc[fbref_mask, 'rating'].fillna(7.0)

    if 'minutesPlayed' not in df.columns:
        df['minutesPlayed'] = 0
    if 'rest_days' not in df.columns:
        df['rest_days'] = df.groupby('name')['match_date'].transform(
            lambda x: compute_rest_days(x)
        )
    if 'high_congestion_flag' not in df.columns:
        df['high_congestion_flag'] = flag_congestion(df['rest_days']).fillna(0)

    if 'acwr_ratio' not in df.columns:
        df['min_last_7d'] = df.groupby('name')['minutesPlayed'].transform(
            lambda x: x.shift(1).rolling(7, min_periods=1).sum()
        )
        df['min_last_28d'] = df.groupby('name')['minutesPlayed'].transform(
            lambda x: x.shift(1).rolling(28, min_periods=1).sum()
        )
        df['acwr_ratio'] = compute_acwr(df['min_last_7d'], df['min_last_28d'])
        df['min_last_7d'] = df['min_last_7d'].fillna(0)
    else:
        if 'min_last_7d' in df.columns:
            df['min_last_7d'] = df['min_last_7d'].fillna(0)

    if 'is_away' not in df.columns:
        if 'venue_raw' in df.columns:
            df['is_away'] = (df['venue_raw'].str.lower() == 'away').astype(int)
        else:
            df['is_away'] = 0

    for col in ['consecutive_away_games', 'lineup_churn']:
        if col not in df.columns:
            df[col] = 0

    for col in ['team_xg', 'team_xga', 'elo']:
        if col not in df.columns:
            df[col] = np.nan

    df['season_ordinal'] = df['season'].map(SEASON_MAP).fillna(1)

    for col in ['is_ucl_team', 'is_non_ucl_team']:
        if col not in df.columns:
            df[col] = False

    if 'position' in df.columns:
        df['position_code'] = df['position'].map(POS_MAP).fillna(1).astype(int)
    else:
        df['position_code'] = 1

    df['rating_rolling_avg_5'], df['rating_rolling_std_5'] = compute_rolling_stats(
        df, 'name', 'rating', window=5
    )

    df['min_last_3'] = df.groupby('name')['minutesPlayed'].transform(
        lambda x: x.shift(1).rolling(3, min_periods=1).sum()
    )

    if 'competition' in df.columns:
        df['is_ucl_match'] = df['competition'].astype(str).str.contains(
            'Champions', case=False, na=False).astype(int)
        df['is_pl_match'] = df['competition'].astype(str).str.contains(
            'Premier', case=False, na=False).astype(int)
    elif 'competition_raw' in df.columns:
        df['is_ucl_match'] = df['competition_raw'].astype(str).str.contains(
            'Champions', case=False, na=False).astype(int)
        df['is_pl_match'] = df['competition_raw'].astype(str).str.contains(
            'Premier', case=False, na=False).astype(int)
    else:
        df['is_ucl_match'] = 0
        df['is_pl_match'] = 1

    df['is_cup_match'] = ((df['is_ucl_match'] == 0) & (df['is_pl_match'] == 0)).astype(int)

    fill_cols = ['rating', 'elo', 'team_xg', 'team_xga', 'rating_rolling_avg_5',
                 'rating_rolling_std_5', 'min_last_3', 'min_last_7d', 'acwr_ratio',
                 'high_congestion_flag']
    default_vals = {
        'rating': 7.0, 'elo': 1500, 'team_xg': 0, 'team_xga': 0,
        'rating_rolling_avg_5': 7.0, 'rating_rolling_std_5': 0.5,
        'min_last_3': 0, 'min_last_7d': 0, 'acwr_ratio': 1.0,
        'high_congestion_flag': 0,
    }
    for col in fill_cols:
        if col in df.columns:
            df[col] = df[col].fillna(default_vals.get(col, 0))

    return df
