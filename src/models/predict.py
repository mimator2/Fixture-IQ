"""
FixtureIQ - Player Fatigue Risk Predictor
==========================================
Given a player's pre-match context, predicts whether they are at
elevated fatigue/injury risk and need rest.
"""

import json
import pickle
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

_root = Path(__file__).resolve().parent.parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from src.config.paths import model_dir, data_dir

warnings.filterwarnings('ignore')


def load_artifacts():
    MODELS_DIR = model_dir()
    model_path = MODELS_DIR / 'fatigue_xgb_model.json'
    scaler_path = MODELS_DIR / 'preprocessor.pkl'
    feat_path = MODELS_DIR / 'feature_columns.json'
    threshold_path = MODELS_DIR / 'threshold.json'

    if not model_path.exists():
        print(f'ERROR: Model not found at {model_path}')
        print('Run train_model.py first.')
        sys.exit(1)

    import xgboost as xgb
    model = xgb.XGBClassifier()
    model.load_model(str(model_path))

    with open(scaler_path, 'rb') as f:
        artifacts = pickle.load(f)
    scaler = artifacts['scaler']
    feature_names = artifacts.get('feature_names', [])

    with open(feat_path) as f:
        feature_names = json.load(f)

    threshold = 0.5
    if threshold_path.exists():
        with open(threshold_path) as f:
            threshold = json.load(f).get('best_threshold', 0.5)

    return model, scaler, feature_names, threshold


def get_player_history(player_name, team_name=None, season='2024_2025'):
    path = data_dir() / '2024-2025' / 'sofascore_dynamic' / 'fixtureiq_dynamic_analytics_clean.csv'
    if not path.exists():
        path = Path(__file__).resolve().parent.parent.parent / 'Data_Dynamic' / 'fixtureiq_dynamic_analytics_clean.csv'
    if not path.exists():
        return None

    df = pd.read_csv(path)

    if team_name:
        mask = (df['name'].str.lower() == player_name.lower()) & \
               (df['teamName'].str.lower().str.contains(team_name.lower(), na=False))
    else:
        mask = df['name'].str.lower() == player_name.lower()

    player_data = df[mask].copy()
    if len(player_data) == 0:
        return None

    player_data = player_data.sort_values('match_date_str')
    return player_data


def compute_features_from_history(player_data):
    if player_data is None or len(player_data) == 0:
        return None

    latest = player_data.iloc[-1].to_dict()

    features = {
        'rest_days': latest.get('rest_days', 14),
        'high_congestion_flag': latest.get('high_congestion_flag', 0),
        'min_last_7d': latest.get('min_last_7d', 0),
        'min_last_3': None,
        'acwr_ratio': latest.get('acwr_ratio', 1.0),
        'consecutive_away_games': latest.get('consecutive_away_games', 0),
        'lineup_churn': latest.get('lineup_churn', 0),
        'rating': latest.get('rating', 7.0),
        'rating_rolling_avg_5': None,
        'rating_rolling_std_5': None,
        'elo': latest.get('elo', 1500),
        'team_xg': latest.get('team_xg', 0),
        'team_xga': latest.get('team_xga', 0),
        'is_away': latest.get('is_away', 0),
        'is_ucl_match': 1 if 'Champions' in str(latest.get('competition', '')) else 0,
        'is_pl_match': 1 if 'Premier' in str(latest.get('competition', '')) else 0,
        'is_cup_match': 0,
        'position_code': {'D': 0, 'M': 1, 'F': 2}.get(str(latest.get('position', '')), 1),
        'season_ordinal': 2,
        'is_ucl_team': 0,
    }

    ratings = player_data['rating'].dropna().values
    if len(ratings) > 0:
        features['rating_rolling_avg_5'] = float(np.mean(ratings[-5:])) if len(ratings) >= 5 else float(np.mean(ratings))
        features['rating_rolling_std_5'] = float(np.std(ratings[-5:])) if len(ratings) >= 5 else float(np.std(ratings))
    else:
        features['rating_rolling_avg_5'] = 7.0
        features['rating_rolling_std_5'] = 0.5

    minutes = player_data['minutesPlayed'].dropna().values
    if len(minutes) > 0:
        features['min_last_3'] = float(np.sum(minutes[-3:])) if len(minutes) >= 3 else float(np.sum(minutes))
    else:
        features['min_last_3'] = 0

    return features


def manual_features_to_df(features_dict, feature_names):
    pos_map = {'D': 0, 'M': 1, 'F': 2, 'G': 3,
               'DF': 0, 'MF': 1, 'FW': 2, 'GK': 3}

    row = {}
    for col in feature_names:
        if col == 'position_code' and 'position' in features_dict:
            row[col] = pos_map.get(str(features_dict['position']).upper(), 1)
        elif col in features_dict:
            row[col] = features_dict[col]
        else:
            row[col] = 0

    return pd.DataFrame([row])


def predict(player_name=None, team_name=None, season='2024_2025',
            features_dict=None, input_csv=None, verbose=True):
    model, scaler, feature_names, threshold = load_artifacts()

    if input_csv:
        df_input = pd.read_csv(input_csv)
        results = []
        for _, row in df_input.iterrows():
            feat_dict = row.to_dict()
            pred = predict(features_dict=feat_dict, verbose=False)
            results.append(pred)
        return results

    if features_dict:
        X = manual_features_to_df(features_dict, feature_names)
        source_info = 'manual features'
    elif player_name:
        player_data = get_player_history(player_name, team_name, season)
        if player_data is None or len(player_data) == 0:
            print(f'Player "{player_name}" not found in dataset.')
            return None

        features_dict = compute_features_from_history(player_data)
        if features_dict is None:
            print(f'Could not compute features for {player_name}.')
            return None

        X = manual_features_to_df(features_dict, feature_names)
        source_info = f'player "{player_name}" ({team_name or "any team"})'
    else:
        print('Provide either --player or --features.')
        return None

    for col in feature_names:
        if col not in X.columns:
            X[col] = 0
    X = X[feature_names]

    X_scaled = scaler.transform(X.fillna(0))
    proba = model.predict_proba(X_scaled)[0, 1]
    prediction = int(proba >= threshold)

    if proba >= 0.8:
        level = 'HIGH'
        icon = '[!]'
        recommendation = 'STRONGLY RECOMMEND REST - High fatigue/injury risk detected.'
    elif proba >= threshold:
        level = 'MODERATE'
        icon = '[-]'
        recommendation = 'Consider rest or reduced minutes. Monitor closely.'
    elif proba >= 0.3:
        level = 'LOW-MODERATE'
        icon = '[~]'
        recommendation = 'Manageable risk. Standard rotation advised.'
    else:
        level = 'LOW'
        icon = '[ok]'
        recommendation = 'Low fatigue risk. Player is well-rested.'

    result = {
        'player': player_name,
        'team': team_name,
        'season': season,
        'fatigue_risk_probability': round(float(proba), 4),
        'fatigue_risk_prediction': prediction,
        'risk_level': level,
        'recommendation': recommendation,
        'threshold': threshold,
        'signals': {},
    }

    fd = features_dict
    if fd:
        signal_acwr = 1 if (fd.get('acwr_ratio', 1) > 1.5 or fd.get('acwr_ratio', 1) < 0.5) else 0
        rating_drop = (fd.get('rating_rolling_avg_5', 7) or 7) - (fd.get('rating', 7) or 7)
        signal_decline = 1 if rating_drop > 1.0 else 0
        signal_congestion = fd.get('high_congestion_flag', 0)

        result['signals'] = {
            'acwr_danger': bool(signal_acwr),
            'acwr_value': round(fd.get('acwr_ratio', 0), 2),
            'performance_decline': bool(signal_decline),
            'rating_drop': round(rating_drop, 2),
            'high_congestion': bool(signal_congestion),
            'rest_days': fd.get('rest_days', 'N/A'),
            'recent_minutes_7d': fd.get('min_last_7d', 'N/A'),
        }

    if verbose:
        print('\n' + '=' * 60)
        print(f'FIXTURE IQ - FATIGUE RISK ASSESSMENT')
        print('=' * 60)
        if player_name:
            print(f'Player:   {player_name}')
        if team_name:
            print(f'Team:     {team_name}')
        print(f'Season:   {season}')
        print(f'Source:   {source_info}')
        print('-' * 60)
        print(f'Risk Score:     {proba:.1%}  {icon}')
        print(f'Risk Level:     {level}')
        print(f'Threshold:      {threshold:.1%}')
        print('-' * 60)
        if result['signals']:
            sig = result['signals']
            print('Signal Breakdown:')
            print(f'  ACWR ({sig.get("acwr_value", "N/A")}):      {"[!] DANGER" if sig.get("acwr_danger") else "[ok] Normal"}')
            print(f'  Rating drop ({sig.get("rating_drop", "N/A")}):  {"[!] DECLINE" if sig.get("performance_decline") else "[ok] Stable"}')
            print(f'  Congestion:   {"[!] HIGH" if sig.get("high_congestion") else "[ok] Normal"} ({sig.get("rest_days", "N/A")}d rest)')
            print(f'  Minutes (7d):  {sig.get("recent_minutes_7d", "N/A")}')
        print('-' * 60)
        print(f'>> {recommendation}')
        print('=' * 60)

    return result


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description='Predict player fatigue/injury risk using XGBoost model.'
    )
    parser.add_argument('--player', type=str, help='Player name')
    parser.add_argument('--team', type=str, default=None, help='Team name (optional)')
    parser.add_argument('--season', type=str, default='2024_2025', help='Season (default: 2024_2025)')
    parser.add_argument('--features', type=str, default=None,
                        help='JSON string with all features (bypasses data lookup)')
    parser.add_argument('--input', type=str, default=None, help='CSV file with player data')
    parser.add_argument('--json', action='store_true', help='Output as JSON only')

    args = parser.parse_args()

    features_dict = None
    if args.features:
        features_dict = json.loads(args.features)

    result = predict(
        player_name=args.player,
        team_name=args.team,
        season=args.season,
        features_dict=features_dict,
        input_csv=args.input,
        verbose=not args.json,
    )

    if args.json and result:
        if isinstance(result, list):
            print(json.dumps(result, indent=2))
        else:
            print(json.dumps(result, indent=2))
