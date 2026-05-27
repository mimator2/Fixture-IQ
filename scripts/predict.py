"""
CLI entry point for player fatigue risk inference.
"""
import sys
from pathlib import Path
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import json
import argparse
from src.models.predict import predict


def main():
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


if __name__ == '__main__':
    main()
