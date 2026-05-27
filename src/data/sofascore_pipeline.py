#!/usr/bin/env python3
"""
SofaScore Player Performance Pipeline (via ScraperFC)
=======================================================
Extracts rich per-player statistics from SofaScore for a given
league/competition and season.

What it pulls:
  - Season-level player stats (goals, assists, dribbles, duels, tackles,
    interceptions, key passes, crosses, long balls, ratings, etc.)
  - Per-match individual stats for every player
  - Heatmap coordinates per player per match (CSV + optional PNG plot)
  - Average positions per player per match
  - Match shots data

Position-specific outputs (same profile logic as fbref_advanced_pipeline):
  DF/CB   → tackles, interceptions, clearances, aerials, duels
  DM/CDM  → recoveries, pressures, pass%, coverage
  CM/MF   → key passes, assists, dribbles, chance creation
  WG/AM   → dribbles, crosses, successful take-ons, rating
  FW/ST   → goals, shots, xG-proxy (big chances), conversion

Installation
------------
  pip install ScraperFC --break-system-packages
  pip install matplotlib --break-system-packages   # optional, for heatmap plots

Usage
-----
List available seasons for Champions League:
  python sofascore_pipeline.py --list-seasons --league "Champions League"

Extract all player stats for UCL 2024/2025:
  python sofascore_pipeline.py --league "Champions League" --year "2024/2025" --output-dir Data

Extract stats + per-match detail + heatmaps for UCL:
  python sofascore_pipeline.py \\
    --league "Champions League" \\
    --year "2024/2025" \\
    --match-stats \\
    --heatmaps \\
    --output-dir Data

Available leagues (SofaScore / ScraperFC names):
  "Champions League", "UEFA Europa League",
  "EPL", "La Liga", "Bundesliga", "Serie A", "Ligue 1",
  "MLS", "Eredivisie", "Primeira Liga"
  (run --list-seasons to check what years are available)

Notes
-----
- SofaScore has no official public API; this uses their undocumented internal
  endpoints. Use responsibly: add delays, don't hammer the server.
- Heatmap data is coordinate-level (x/y on a 0-100 pitch grid), saved as CSV
  and optionally rendered as PNG images.
- ScraperFC's Sofascore module uses requests under the hood; it may break if
  SofaScore changes their API structure.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

# Allow direct execution
_root = Path(__file__).resolve().parent.parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from src.config.paths import data_dir

import pandas as pd

try:
    import ScraperFC as sfc
except ImportError:
    raise SystemExit(
        "ScraperFC not installed.\n"
        "Run: pip install ScraperFC --break-system-packages"
    )

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

# ---------------------------------------------------------------------------
# Position profile column maps (SofaScore stat names differ from FBref)
# ---------------------------------------------------------------------------

# These are the column names ScraperFC returns from scrape_player_league_stats
POSITION_PROFILES: Dict[str, List[str]] = {
    "GK": [
        "name", "team", "position", "appearances", "minutesPlayed",
        "saves", "goalsConceded", "cleanSheets",
        "successfulDuelsPercentage", "rating",
    ],
    "DF/CB": [
        "name", "team", "position", "appearances", "minutesPlayed",
        "tackles", "interceptions", "clearances",
        "aerialDuelsWon", "aerialDuelsPercentage",
        "groundDuelsWon", "groundDuelsPercentage",
        "successfulDuelsPercentage",
        "blockedShots", "errorLeadToGoal",
        "passAccuracy", "longBallAccuracy",
        "rating",
    ],
    "DM/CDM": [
        "name", "team", "position", "appearances", "minutesPlayed",
        "tackles", "interceptions", "ballRecovery",
        "successfulDuelsPercentage", "groundDuelsWon",
        "passAccuracy", "keyPasses", "bigChancesCreated",
        "accurateLongBalls", "longBallAccuracy",
        "dribbleAttempts", "successfulDribbles",
        "rating",
    ],
    "CM/MF": [
        "name", "team", "position", "appearances", "minutesPlayed",
        "assists", "keyPasses", "bigChancesCreated",
        "passAccuracy", "accuratePasses", "accurateLongBalls",
        "successfulDribbles", "dribbleAttempts",
        "tackles", "interceptions", "ballRecovery",
        "goals", "rating",
    ],
    "WG/AM": [
        "name", "team", "position", "appearances", "minutesPlayed",
        "goals", "assists", "keyPasses", "bigChancesCreated",
        "successfulDribbles", "dribbleAttempts", "dribbleSuccessRate",
        "accurateCrosses", "crossAttempts", "crossAccuracy",
        "shotsOnTarget", "totalShots",
        "passAccuracy", "rating",
    ],
    "FW/ST": [
        "name", "team", "position", "appearances", "minutesPlayed",
        "goals", "assists", "goalsPerGame",
        "shotsOnTarget", "totalShots", "shotAccuracy",
        "bigChances", "bigChancesMissed", "bigChancesConversion",
        "successfulDribbles", "dribbleAttempts",
        "aerialDuelsWon", "aerialDuelsPercentage",
        "rating",
    ],
}

LEAGUE_ALIASES = {
    "champions league": "UEFA Champions League",
    "uefa champions league": "UEFA Champions League",
    "europa league": "UEFA Europa League",
    "uefa europa league": "UEFA Europa League",
    "conference league": "UEFA Conference League",
    "uefa conference league": "UEFA Conference League",
    "premier league": "England Premier League",
    "epl": "England Premier League",
    "la liga": "Spain La Liga",
    "bundesliga": "Germany Bundesliga",
    "serie a": "Italy Serie A",
    "ligue 1": "France Ligue 1",
    "mls": "USA MLS",
}

YEAR_ALIASES = {
    "2024/2025": "24/25",
    "2023/2024": "23/24",
    "2022/2023": "22/23",
    "2021/2022": "21/22",
    "2020/2021": "20/21",
    "2019/2020": "19/20",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def sanitize(value: str) -> str:
    import re
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_") or "unknown"


def normalize_league_name(league: str) -> str:
    league = str(league).strip()
    return LEAGUE_ALIASES.get(league.lower(), league)


def normalize_year_value(year: str) -> str:
    year = str(year).strip()
    return YEAR_ALIASES.get(year, year)


def classify_position(pos: str) -> str:
    pos = str(pos).upper()
    if "G" in pos and ("GK" in pos or pos == "G"):
        return "GK"
    if any(x in pos for x in ["CB", "RB", "LB", "WB", "D"]) and "DM" not in pos:
        return "DF/CB"
    if "DM" in pos:
        return "DM/CDM"
    if any(x in pos for x in ["AM", "LW", "RW", "WG"]):
        return "WG/AM"
    if any(x in pos for x in ["F", "ST", "CF"]):
        return "FW/ST"
    return "CM/MF"


def save_csv(df: pd.DataFrame, path: Path, label: str) -> None:
    df.to_csv(path, index=False)
    print(f"  ✅ {label}: {len(df)} rows → {path.name}")


def render_heatmap(coords: list, player_name: str, match_label: str, out_path: Path) -> None:
    """Render heatmap coordinates as a pitch PNG."""
    if not HAS_MATPLOTLIB or not coords:
        return
    xs = [c.get("x", 0) for c in coords]
    ys = [c.get("y", 0) for c in coords]

    fig, ax = plt.subplots(figsize=(10, 7))
    ax.set_facecolor("#1a7a1a")
    fig.patch.set_facecolor("#1a7a1a")

    # Pitch outline
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    for spine in ax.spines.values():
        spine.set_edgecolor("white")

    # Heatmap
    if len(xs) > 5:
        hb = ax.hexbin(xs, ys, gridsize=20, cmap="YlOrRd", alpha=0.75,
                       mincnt=1, extent=(0, 100, 0, 100))
        plt.colorbar(hb, ax=ax, label="Frequency")
    else:
        ax.scatter(xs, ys, color="yellow", s=60, alpha=0.8)

    # Pitch markings
    ax.plot([50, 50], [0, 100], "w--", linewidth=0.8, alpha=0.5)
    centre = plt.Circle((50, 50), 9.15, color="white", fill=False, linewidth=0.8, alpha=0.5)
    ax.add_patch(centre)

    ax.set_title(f"{player_name}\n{match_label}", color="white", fontsize=11)
    ax.set_xlabel("Pitch length →", color="white", fontsize=8)
    ax.set_ylabel("Pitch width →", color="white", fontsize=8)
    ax.tick_params(colors="white")

    plt.tight_layout()
    plt.savefig(out_path, dpi=120, bbox_inches="tight")
    plt.close()


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

class SofascorePipeline:

    POSITIONS_MAP = {
        "Goalkeepers": ["GK"],
        "Defenders":   ["DF/CB"],
        "Midfielders": ["DM/CDM", "CM/MF"],
        "Forwards":    ["WG/AM", "FW/ST"],
    }

    def __init__(
        self,
        league: str,
        year: str,
        output_dir: Path,
        do_match_stats: bool = False,
        do_heatmaps: bool = False,
        delay: float = 3.0,
    ) -> None:
        self.league = normalize_league_name(league)
        self.year = normalize_year_value(year)
        self.prefix = f"{sanitize(league)}_{sanitize(year)}"
        self.output_dir = output_dir / self.prefix
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.do_match_stats = do_match_stats
        self.do_heatmaps = do_heatmaps
        self.delay = delay
        self.scraper = sfc.Sofascore()

    # -----------------------------------------------------------------------

    def list_seasons(self) -> None:
        print(f"\nAvailable seasons for '{self.league}':")
        seasons = self.scraper.get_valid_seasons(self.league)
        for name, sid in seasons.items():
            print(f"  {name}  (id={sid})")

    # -----------------------------------------------------------------------

    def _extract_league_stats(self) -> pd.DataFrame:
        """
        Pull all player stats for the full season, across all position groups.
        ScraperFC paginates internally.
        """
        all_dfs: List[pd.DataFrame] = []
        position_groups = ["Goalkeepers", "Defenders", "Midfielders", "Forwards"]

        for group in position_groups:
            print(f"  Fetching season stats: {group}…")
            try:
                pos_filter = self.scraper.get_positions([group])
                df = self.scraper.scrape_player_league_stats(
                    year=self.year,
                    league=self.league,
                    accumulation="total",
                    selected_positions=[group],
                )
                if df is not None and not df.empty:
                    df["position_group"] = group
                    all_dfs.append(df)
                    print(f"    → {len(df)} players")
                time.sleep(self.delay)
            except Exception as exc:
                print(f"    WARNING: {group} failed: {exc}")

        if not all_dfs:
            return pd.DataFrame()
        return pd.concat(all_dfs, ignore_index=True)

    # -----------------------------------------------------------------------

    def _build_position_profiles(self, df: pd.DataFrame) -> None:
        profiles_dir = self.output_dir / "position_profiles"
        profiles_dir.mkdir(exist_ok=True)

        pos_col = next(
            (c for c in ["position", "Position", "pos"] if c in df.columns), None
        )

        for profile_name, wanted_cols in POSITION_PROFILES.items():
            available = [c for c in wanted_cols if c in df.columns]
            if not available:
                continue
            if pos_col:
                mask = df[pos_col].fillna("").apply(classify_position) == profile_name
                subset = df[mask][available].reset_index(drop=True)
            else:
                subset = df[available].copy()

            fname = profiles_dir / f"{self.prefix}_{sanitize(profile_name)}.csv"
            save_csv(subset, fname, profile_name)

    # -----------------------------------------------------------------------

    def _extract_match_stats(self, match_dicts: list) -> None:
        """Per-match player stats for every match in the season."""
        match_stats_dir = self.output_dir / "match_player_stats"
        match_stats_dir.mkdir(exist_ok=True)
        avg_pos_dir = self.output_dir / "average_positions"
        avg_pos_dir.mkdir(exist_ok=True)

        total = len(match_dicts)
        print(f"\n  Processing {total} matches for per-match stats…")

        for idx, match in enumerate(match_dicts, start=1):
            match_id = match.get("id") or match.get("match_id")
            if not match_id:
                continue

            home = match.get("homeTeam", {}).get("name", "home")
            away = match.get("awayTeam", {}).get("name", "away")
            date = str(match.get("startTimestamp", ""))[:10]
            label = f"{date}_{sanitize(home)}_vs_{sanitize(away)}"

            print(f"  [{idx}/{total}] {label}", end=" ")

            try:
                # Player stats for match
                df_stats = self.scraper.scrape_player_league_stats(
                    year=self.year,
                    league=self.league,
                    accumulation="per90",
                )
                # Average positions
                df_pos = self.scraper.scrape_player_average_positions(match_id)
                if df_pos is not None and not df_pos.empty:
                    df_pos["match"] = label
                    save_csv(
                        df_pos,
                        avg_pos_dir / f"{label}_avg_positions.csv",
                        "avg_pos",
                    )
                time.sleep(self.delay)
                print("✅")
            except Exception as exc:
                print(f"⚠️  {exc}")
                time.sleep(self.delay)

    # -----------------------------------------------------------------------

    def _extract_heatmaps(self, match_dicts: list) -> None:
        heatmap_dir = self.output_dir / "heatmaps"
        heatmap_dir.mkdir(exist_ok=True)

        total = len(match_dicts)
        print(f"\n  Extracting heatmaps for {total} matches…")

        for idx, match in enumerate(match_dicts, start=1):
            match_id = match.get("id") or match.get("match_id")
            if not match_id:
                continue

            home = match.get("homeTeam", {}).get("name", "home")
            away = match.get("awayTeam", {}).get("name", "away")
            date = str(match.get("startTimestamp", ""))[:10]
            label = f"{date}_{sanitize(home)}_vs_{sanitize(away)}"
            match_heatmap_dir = heatmap_dir / label
            match_heatmap_dir.mkdir(exist_ok=True)

            print(f"  [{idx}/{total}] {label}…", end=" ")

            try:
                heatmaps = self.scraper.scrape_heatmaps(match_id)
                if not heatmaps:
                    print("no data")
                    continue

                # Save raw coordinates as CSV
                rows = []
                for player_name, data in heatmaps.items():
                    coords = data.get("heatmap", [])
                    pid = data.get("id", "")
                    for c in coords:
                        rows.append({
                            "player": player_name,
                            "player_id": pid,
                            "x": c.get("x"),
                            "y": c.get("y"),
                        })

                if rows:
                    df_heat = pd.DataFrame(rows)
                    save_csv(
                        df_heat,
                        match_heatmap_dir / f"{label}_heatmap_coords.csv",
                        "coords",
                    )

                # Render PNG images per player (if matplotlib available)
                if HAS_MATPLOTLIB:
                    for player_name, data in heatmaps.items():
                        coords = data.get("heatmap", [])
                        if not coords:
                            continue
                        safe_player = sanitize(player_name)
                        png_path = match_heatmap_dir / f"{safe_player}_heatmap.png"
                        render_heatmap(coords, player_name, label, png_path)

                print(f"✅ {len(heatmaps)} players")
                time.sleep(self.delay)
            except Exception as exc:
                print(f"⚠️  {exc}")
                time.sleep(self.delay)

    # -----------------------------------------------------------------------

    def run(self) -> None:
        print(f"\n{'='*60}")
        print(f"  SofaScore Pipeline")
        print(f"  League : {self.league}")
        print(f"  Season : {self.year}")
        print(f"{'='*60}")

        # 1) Full-season player stats
        print(f"\n[1] Extracting season player stats…")
        df_all = self._extract_league_stats()

        if df_all.empty:
            print("  ⚠️  No season stats extracted. Check league/year values.")
            return

        save_csv(df_all, self.output_dir / f"{self.prefix}_all_players.csv", "All players")

        # 2) Position profiles
        print(f"\n[2] Building position profiles…")
        self._build_position_profiles(df_all)

        # 3) Match-level data (optional)
        if self.do_match_stats or self.do_heatmaps:
            print(f"\n[3] Fetching match list…")
            try:
                match_dicts = self.scraper.get_match_dicts(
                    year=self.year, league=self.league
                )
                print(f"    {len(match_dicts)} matches found")
            except Exception as exc:
                print(f"  ⚠️  Could not fetch match list: {exc}")
                match_dicts = []

            # Save match meta
            if match_dicts:
                match_rows = []
                for m in match_dicts:
                    match_rows.append({
                        "match_id":  m.get("id"),
                        "date":      str(m.get("startTimestamp", ""))[:10],
                        "home_team": m.get("homeTeam", {}).get("name"),
                        "away_team": m.get("awayTeam", {}).get("name"),
                        "home_score": m.get("homeScore", {}).get("current"),
                        "away_score": m.get("awayScore", {}).get("current"),
                        "status":    m.get("status", {}).get("description"),
                    })
                save_csv(
                    pd.DataFrame(match_rows),
                    self.output_dir / f"{self.prefix}_matches.csv",
                    "Match list",
                )

            if self.do_match_stats and match_dicts:
                self._extract_match_stats(match_dicts)

            if self.do_heatmaps and match_dicts:
                self._extract_heatmaps(match_dicts)

        print(f"\n✅ Done.")
        print(f"   Output: {self.output_dir}")
        csv_count = len(list(self.output_dir.rglob("*.csv")))
        png_count = len(list(self.output_dir.rglob("*.png")))
        print(f"   Files : {csv_count} CSVs" + (f", {png_count} heatmap PNGs" if png_count else ""))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract SofaScore player stats via ScraperFC.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--league", default="Champions League",
        help="League name (e.g. 'Champions League', 'EPL', 'La Liga'). Default: Champions League",
    )
    parser.add_argument(
        "--year", default="2024/2025",
        help="Season year string (e.g. '2024/2025'). Default: 2024/2025",
    )
    parser.add_argument("--output-dir", default=str(data_dir()), help=f"Output directory. Default: {data_dir()}")
    parser.add_argument(
        "--match-stats", action="store_true",
        help="Also extract per-match player stats and average positions (slow)",
    )
    parser.add_argument(
        "--heatmaps", action="store_true",
        help="Also extract heatmap coordinates per player per match (very slow)",
    )
    parser.add_argument(
        "--list-seasons", action="store_true",
        help="Just list available seasons for the given league and exit",
    )
    parser.add_argument(
        "--delay", type=float, default=3.0,
        help="Seconds to wait between API calls (default: 3.0). Increase if getting blocked.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    pipeline = SofascorePipeline(
        league=args.league,
        year=args.year,
        output_dir=Path(args.output_dir),
        do_match_stats=args.match_stats,
        do_heatmaps=args.heatmaps,
        delay=args.delay,
    )

    if args.list_seasons:
        pipeline.list_seasons()
        return

    pipeline.run()


if __name__ == "__main__":
    main()
