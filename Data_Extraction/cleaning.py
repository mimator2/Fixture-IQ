"""
Data Cleaning Utilities
=======================
Common functions for standardizing and cleaning data across the project.
"""

import pandas as pd
import numpy as np


TEAM_NAME_MAP = {
    'arsenal': 'Arsenal',
    'aston villa': 'Aston Villa',
    'liverpool fc': 'Liverpool',
    'liverpool': 'Liverpool',
    'manchester city': 'Manchester City',
    'man city': 'Manchester City',
    'manchester united': 'Manchester United',
    'man united': 'Manchester United',
    'man utd': 'Manchester United',  # <-- Catches 'Manchester Utd'
    'newcastle united': 'Newcastle United',
    'newcastle': 'Newcastle United',
    'chelsea': 'Chelsea',
    'tottenham hotspur': 'Tottenham Hotspur',
    'tottenham': 'Tottenham Hotspur',
    'brighton & hove albion': 'Brighton',
    'brighton and hove albion': 'Brighton',
    'brighton': 'Brighton',
    'west ham united': 'West Ham United',
    'west ham': 'West Ham United',
    'wolverhampton wanderers': 'Wolverhampton',
    'wolverhampton': 'Wolverhampton',
    'wolves': 'Wolverhampton',
    'leicester city': 'Leicester City',
    'leicester': 'Leicester City',
    'ipswich town': 'Ipswich Town',
    'ipswich': 'Ipswich Town',
    'southampton': 'Southampton',
    'bournemouth': 'Bournemouth',
    'afc bournemouth': 'Bournemouth',
    'brentford': 'Brentford',
    'crystal palace': 'Crystal Palace',
    'everton': 'Everton',
    'fulham': 'Fulham',
    'nottingham forest': 'Nottingham Forest',
    "nott'ham forest": 'Nottingham Forest',
}

def clean_columns(df, camelcase_split=True):
    """
    Standardize dataframe column names:
    - Handle camelCase splitting (optional)
    - Lowercase
    - Strip spaces
    - Replace spaces/special chars with underscores
    - Remove repeated underscores
    
    Args:
        df: DataFrame to clean
        camelcase_split: If True, splits camelCase (xG → x_g, minutesPlayed → minutes_played)
    
    Returns:
        DataFrame with cleaned column names
    """
    df = df.copy()
    
    cols = df.columns
    
    if camelcase_split:
        # Split camelCase: xGperMatch → x_g_per_match
        cols = cols.str.replace(r'(?<=[a-z0-9])(?=[A-Z])', '_', regex=True)
        cols = cols.str.replace(r'(?<=[A-Z])(?=[A-Z][a-z])', '_', regex=True)
    
    # Standard cleaning
    cols = (cols
        .str.lower()
        .str.strip()
        .str.replace("-", "_", regex=False)
        .str.replace("/", "_", regex=False)
        .str.replace("%", "_pct", regex=False)
        .str.replace(" ", "_", regex=False)
        .str.replace(r"_+", "_", regex=True)  # Remove repeated underscores
        .str.strip('_')
    )
    
    df.columns = cols
    return df


def clean_player_names(df, player_col='player', inplace=False):
    """
    Standardize player names to lowercase for matching.
    
    Args:
        df: DataFrame containing player names
        player_col: Name of the player column (default: 'player')
        inplace: If True, modifies df in place
    
    Returns:
        DataFrame with cleaned player names (or None if inplace=True)
    """
    if not inplace:
        df = df.copy()
    
    if player_col in df.columns:
        df[player_col] = (df[player_col]
            .astype(str)
            .str.strip()
            .str.lower()
        )
    
    return None if inplace else df



def clean_team_names(df, team_col='team', inplace=False):
    """
    Standardize team names to a clean canonical string format for matching.
    Handles trailing context years, abbreviations (Utd, FC), and matches variations.
    """
    if not inplace:
        df = df.copy()
    
    if team_col in df.columns:
        # 1. Convert to lower case, strip whitespace
        cleaned_series = df[team_col].astype(str).str.strip().str.lower()
        
        # 2. Strip trailing multi-season indicators (e.g., ' 2024 2025')
        cleaned_series = cleaned_series.str.replace(r'\s+\d{4}[\s\-_]*\d{4}$', '', regex=True)
        
        # 3. Standardize text abbreviations for cleaner dictionary lookups
        cleaned_series = cleaned_series.str.replace(r'\butd\b', 'united', regex=True)  # utd -> united
        cleaned_series = cleaned_series.str.replace(r'\bfc\b', '', regex=True)         # remove fc
        cleaned_series = cleaned_series.str.strip()
        
        # 4. Route through map, falling back to .str.title() if team is unrecognized
        df[team_col] = cleaned_series.map(TEAM_NAME_MAP).fillna(df[team_col].astype(str).str.title())
        
    return None if inplace else df


def convert_dates(df, cols, format=None, errors='coerce', inplace=False):
    """
    Convert multiple columns to datetime.
    
    Args:
        df: DataFrame
        cols: Single column name or list of column names
        format: Optional strftime format
        errors: How to handle errors ('coerce', 'raise', 'ignore')
        inplace: If True, modifies df in place
    
    Returns:
        DataFrame with converted date columns
    """
    if not inplace:
        df = df.copy()
    
    if isinstance(cols, str):
        cols = [cols]
    
    for col in cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], format=format, errors=errors)
    
    return None if inplace else df


def convert_numeric(df, cols, fillna=0, inplace=False):
    """
    Convert multiple columns to numeric (handles percentages, commas, etc).
    
    Args:
        df: DataFrame
        cols: Single column name or list of column names
        fillna: Value to fill NaNs (default: 0)
        inplace: If True, modifies df in place
    
    Returns:
        DataFrame with converted numeric columns
    """
    if not inplace:
        df = df.copy()
    
    if isinstance(cols, str):
        cols = [cols]
    
    for col in cols:
        if col in df.columns:
            # Remove common non-numeric characters
            df[col] = (df[col]
                .astype(str)
                .str.replace(',', '', regex=False)
                .str.replace('%', '', regex=False)
                .str.strip()
            )
            df[col] = pd.to_numeric(df[col], errors='coerce')
            if fillna is not None:
                df[col] = df[col].fillna(fillna)
    
    return None if inplace else df



def standardize_position(pos_str, format_output='code'):
    """
    Convert ANY position format to standardized code.
    
    Handles:
    - Full names: Goalkeeper, Defender, Midfielder, Forward
    - FBref codes: GK, CB, DF, LB, RB, CM, DM, AM, MF, FW, ST
    - SofaScore: Goalkeepers, Defenders, Midfielders, Forwards
    - Multi-positions: "FW,MF", "MF,DF" → returns primary position
    
    Args:
        pos_str: Position string (any format)
        format_output: 'code' (GK, DF, MF, FW) or 'full' (Goalkeeper, Defender, etc)
    
    Returns:
        str: Standardized position code or name
    """
    
    # Handle None/NaN
    if pd.isna(pos_str):
        return 'Unknown'
    
    pos_str = str(pos_str).strip().lower()
    
    # If multi-position (e.g., "FW,MF"), use primary (first)
    if ',' in pos_str:
        pos_str = pos_str.split(',')[0].strip()
    
    # Map all variations to canonical codes
    POSITION_MAP = {
        # Goalkeepers
        'gk': 'GK',
        'goalkeeper': 'GK',
        'goalkeepers': 'GK',
        'gardien': 'GK',
        
        # Defenders
        'df': 'DF',
        'cb': 'DF',
        'lb': 'DF',
        'rb': 'DF',
        'defender': 'DF',
        'defenders': 'DF',
        'centre-back': 'DF',
        'left-back': 'DF',
        'right-back': 'DF',
        
        # Midfielders
        'mf': 'MF',
        'cm': 'MF',
        'dm': 'MF',
        'cdm': 'MF',
        'am': 'MF',
        'cam': 'MF',
        'lm': 'MF',
        'rm': 'MF',
        'midfielder': 'MF',
        'midfielders': 'MF',
        'centre-mid': 'MF',
        'centre-midfield': 'MF',
        'defensive-midfield': 'MF',
        'attacking-midfield': 'MF',
        
        # Forwards
        'fw': 'FW',
        'st': 'FW',
        'f': 'FW',
        'forward': 'FW',
        'forwards': 'FW',
        'striker': 'FW',
        'cf': 'FW',
        'centre-forward': 'FW',
        'winger': 'FW',  # Wingers are counted as forwards in terms of risk
    }
    
    # Get canonical code
    pos_code = POSITION_MAP.get(pos_str, 'Unknown')
    
    # Convert to full name if requested
    if format_output == 'full':
        CODE_TO_FULL = {
            'GK': 'Goalkeeper',
            'DF': 'Defender',
            'MF': 'Midfielder',
            'FW': 'Forward',
            'Unknown': 'Unknown'
        }
        return CODE_TO_FULL.get(pos_code, 'Unknown')
    
    return pos_code


def extract_primary_position(pos_str):
    """
    For players with multiple positions, extract primary (first) position.
    
    Args:
        pos_str: Position string, possibly multi-position like "FW,MF"
    
    Returns:
        str: Primary position
    """
    if pd.isna(pos_str):
        return 'Unknown'
    
    pos_str = str(pos_str).strip()
    
    # If multi-position, take first
    if ',' in pos_str:
        pos_str = pos_str.split(',')[0].strip()
    
    return standardize_position(pos_str, format_output='code')


def get_position_profile_group(pos_code):
    """
    Map position codes to SofaScore position_profiles directory groups.
    
    Returns which position profile file a player should match to:
    - DF/CB → "df_cb"
    - DM → "dm_cdm"
    - CM → "cm_mf"
    - AM/Winger → "wg_am"
    - FW/ST → "fw_st"
    - GK → "gk"
    
    Args:
        pos_code: Standardized position code (GK, DF, MF, FW)
    
    Returns:
        str: Position profile group name
    """
    PROFILE_GROUPS = {
        'GK': 'gk',
        'DF': 'df_cb',
        'MF': 'cm_mf',  # Note: Could be dm_cdm, cm_mf, or wg_am
        'FW': 'fw_st',
    }
    
    return PROFILE_GROUPS.get(pos_code, 'unknown')


def standardize_position_col(df, pos_col='position', inplace=False):
    """
    Standardize position column in a DataFrame.
    
    Handles:
    - Multi-positions → extracts primary
    - All formats → converts to canonical codes
    - Preserves unknown positions as 'Unknown'
    
    Args:
        df: DataFrame with position column
        pos_col: Name of position column
        inplace: If True, modifies df in place
    
    Returns:
        DataFrame with standardized positions
    """
    if not inplace:
        df = df.copy()
    
    if pos_col in df.columns:
        df[pos_col] = df[pos_col].apply(extract_primary_position)
    
    return None if inplace else df