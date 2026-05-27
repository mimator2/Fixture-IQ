"""
FixtureIQ - FBref Data Extraction Orchestrator
===============================================
Consolidates the previous 4 season-specific run scripts into one CLI entry point.

Usage:
    python scripts/extract_fbref.py --season 2024-2025 --teams arsenal,liverpool,man_city,aston_villa
    python scripts/extract_fbref.py --season 2024-2025 --all-ucl-teams
    python scripts/extract_fbref.py --season 2022-2023 --teams man_city,liverpool --headless
"""

import subprocess
import sys
import time
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from src.config.paths import data_dir
from dotenv import load_dotenv
load_dotenv(_root / '.env')

import os
import argparse

# UCL-participant PL teams per season (squad_id:team_slug)
UCL_TEAMS = {
    '2021-2022': {
        'Manchester-City': ('b8fd03ef', 'Manchester-City'),
        'Manchester-United': ('19538871', 'Manchester-United'),
        'Liverpool': ('822bd0ba', 'Liverpool'),
        'Chelsea': ('cff3d9bb', 'Chelsea'),
    },
    '2022-2023': {
        'Manchester-City': ('b8fd03ef', 'Manchester-City'),
        'Liverpool': ('822bd0ba', 'Liverpool'),
        'Chelsea': ('cff3d9bb', 'Chelsea'),
        'Tottenham-Hotspur': ('361ca564', 'Tottenham-Hotspur'),
    },
    '2023-2024': {
        'Manchester-City': ('b8fd03ef', 'Manchester-City'),
        'Arsenal': ('18bb7c10', 'Arsenal'),
        'Manchester-United': ('19538871', 'Manchester-United'),
        'Newcastle-United': ('b2b47a98', 'Newcastle-United'),
    },
    '2024-2025': {
        'Manchester-City': ('b8fd03ef', 'Manchester-City'),
        'Arsenal': ('18bb7c10', 'Arsenal'),
        'Liverpool': ('822bd0ba', 'Liverpool'),
        'Aston-Villa': ('8602292d', 'Aston-Villa'),
    },
}


def run_team_extraction(team_slug, squad_id, season, headless=False, scrape_do_token=None):
    pipeline_script = _root / 'src' / 'data' / 'fbref_pipeline.py'
    cmd = [
        sys.executable, str(pipeline_script),
        '--squad-id', squad_id,
        '--team-slug', team_slug,
        '--season', season,
        '--output-dir', str(data_dir()),
    ]
    if headless:
        cmd.append('--headless')
    if scrape_do_token:
        cmd.extend(['--scrape-do-token', scrape_do_token])

    print(f"\n{'='*70}")
    print(f"Starting extraction: {team_slug} ({season})")
    print(f"{'='*70}")

    try:
        result = subprocess.run(cmd, capture_output=False, text=True, timeout=3600)
        status = 'SUCCESS' if result.returncode == 0 else f'FAILED ({result.returncode})'
        print(f"\n{'✅' if result.returncode == 0 else '❌'} {team_slug}: {status}")
        return (team_slug, status)
    except subprocess.TimeoutExpired:
        print(f"\n⏱️ {team_slug}: TIMEOUT")
        return (team_slug, 'TIMEOUT')
    except Exception as e:
        print(f"\n❌ {team_slug}: ERROR - {e}")
        return (team_slug, f'ERROR: {e}')


def main():
    parser = argparse.ArgumentParser(description='Extract FBref data for UCL-participant PL teams.')
    parser.add_argument('--season', required=True, choices=list(UCL_TEAMS.keys()),
                        help='Season to extract (e.g. 2024-2025)')
    parser.add_argument('--teams', type=str, default=None,
                        help='Comma-separated team slugs (e.g. Arsenal,Manchester-City)')
    parser.add_argument('--all-ucl-teams', action='store_true',
                        help='Extract all UCL-participant teams for the season')
    parser.add_argument('--headless', action='store_true', help='Run Chrome headless')
    parser.add_argument('--delay', type=int, default=10, help='Delay between teams (seconds)')
    args = parser.parse_args()

    teams = UCL_TEAMS[args.season]

    if args.teams:
        selected = {t.strip(): teams[t.strip()] for t in args.teams.split(',') if t.strip() in teams}
        if not selected:
            print(f"Error: No valid teams found in {args.teams}. Available: {list(teams.keys())}")
            sys.exit(1)
        teams = selected
    elif args.all_ucl_teams:
        pass
    else:
        print(f"Extracting all {len(teams)} UCL teams for {args.season}")

    scrape_do_token = os.environ.get('SCRAPE_DO_TOKEN')

    print(f"\nSeason: {args.season}")
    print(f"Teams: {', '.join(teams.keys())}")
    print(f"Output: {data_dir()}")
    print(f"Headless: {args.headless}")
    print(f"Scrape.do: {'Yes' if scrape_do_token else 'No'}")
    print()

    results = {}
    for idx, (team_name, (squad_id, team_slug)) in enumerate(teams.items()):
        if idx > 0:
            print(f"\nWaiting {args.delay}s before next team...")
            time.sleep(args.delay)
        team_name, status = run_team_extraction(team_slug, squad_id, args.season,
                                                 headless=args.headless,
                                                 scrape_do_token=scrape_do_token)
        results[team_name] = status

    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    for team, status in sorted(results.items()):
        symbol = '✅' if status == 'SUCCESS' else '❌'
        print(f"  {symbol} {team:25s} {status}")

    success = sum(1 for s in results.values() if s == 'SUCCESS')
    print(f"\n{success}/{len(results)} teams succeeded")
    return 0 if success == len(results) else 1


if __name__ == '__main__':
    sys.exit(main())
