#!/usr/bin/env python3
"""
SofaScore Direct API Pipeline — FixtureIQ (No ScraperFC required)
==================================================================
Calls SofaScore's internal API directly using requests + Playwright for
Cloudflare bypass. Zero library dependency on ScraperFC or sofascore-wrapper.

How it works
------------
SofaScore serves all its data from a documented-by-the-community JSON API:
  https://api.sofascore.com/api/v1/...

The endpoints used here:
  /unique-tournament/{tid}/season/{sid}/statistics
    → Season-level player stats (goals, dribbles, tackles, key passes, rating…)
  /unique-tournament/{tid}/seasons
    → List all seasons for a tournament (to find the right season_id)
  /unique-tournament/{tid}/season/{sid}/events/last/{page}
    → Paginated match list for a season
  /player/{pid}/unique-tournament/{tid}/season/{sid}/heatmap/overall
    → Full-season heatmap per player (optional)
  /player/{pid}/unique-tournament/{tid}/season/{sid}/statistics/overall
    → Full-season player statistics per player (optional)

Cloudflare bypass
-----------------
SofaScore uses Cloudflare. Raw `requests` gets 403'd.
We use Playwright (headless Chromium) to load the first page and steal real
browser cookies + headers, then reuse them for all subsequent requests.
This is the same strategy that sofascore-wrapper 1.1.x uses internally.

Install
-------
  pip install playwright requests pandas matplotlib --break-system-packages
  python -m playwright install chromium

Known tournament IDs (hardcoded for convenience)
-------------------------------------------------
  UEFA Champions League  : 7
  UEFA Europa League     : 679
  UEFA Conference League : 17
  England Premier League : 17 (EPL unique-tournament id = 17)
  Spain La Liga          : 8
  Germany Bundesliga     : 35
  Italy Serie A          : 23
  France Ligue 1         : 34

PL teams in UCL 2024/25 (hardcoded)
-------------------------------------
  Arsenal        team_id = 9
  Liverpool      team_id = 44
  Manchester City team_id = 17
  Chelsea        team_id = 38
  Aston Villa    team_id = 40

Per-team fatigue variables computed in match context
-----------------------------------------------------
  days_since_last_match   — rest since previous fixture
  cumulative_matches      — running total of matches played this season
  matches_last_7d         — congestion: #matches in rolling 7-day window
  matches_last_14d        — congestion: #matches in rolling 14-day window
  is_away                 — 1 if away fixture, 0 if home
  away_leg_sequence       — consecutive running count of away fixtures
                             (resets to 0 on a home match)
  home_away_alternation_rate — rolling(5) fraction of H↔A switches
                                (proxy: travel / scheduling stress)
  rest_category           — well_rested | normal | congested | season_opener

Usage
-----
  # Season stats for all PL UCL teams (fast, ~5 min)
  python sofascore_direct.py --output-dir Data

  # Single team
  python sofascore_direct.py --team Arsenal --output-dir Data

  # With per-player full-season heatmaps (slow)
  python sofascore_direct.py --heatmaps --output-dir Data

  # Different competition
  python sofascore_direct.py --tournament-id 17 --season-year "24/25" --output-dir Data

  # List seasons for a tournament
  python sofascore_direct.py --list-seasons --tournament-id 7

  # Dry run: inspect what would run, no network calls
  python sofascore_direct.py --dry-run

  # Force fresh extraction (purge disk cache)
  python sofascore_direct.py --clear-cache
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import random
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

try:
    import requests
except ImportError:
    raise SystemExit("Install requests: pip install requests --break-system-packages")

try:
    from playwright.sync_api import sync_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False
    print("WARNING: Playwright not installed. Install: pip install playwright --break-system-packages")
    print("         Then: python -m playwright install chromium")

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    level=logging.INFO,
)
log = logging.getLogger("fixtureiq.sofascore")

# ---------------------------------------------------------------------------
# Tournament & team constants
# ---------------------------------------------------------------------------

TOURNAMENTS: Dict[str, int] = {
    "UEFA Champions League":  7,
    "UEFA Europa League":     679,
    "UEFA Conference League": 17,
    "England Premier League": 17,   # NOTE: EPL uses tid=17 for league, UCL uses 7
    "Spain La Liga":          8,
    "Germany Bundesliga":     35,
    "Italy Serie A":          23,
    "France Ligue 1":         34,
}

# PL teams competing in UCL 2024/25 with their SofaScore team IDs
PL_UCL_TEAMS: Dict[str, int] = {
    "Arsenal":          9,
    "Liverpool":        44,
    "Manchester City":  17,
    "Chelsea":          38,
    "Aston Villa":      40,
}

# SofaScore position group filters for the stats endpoint
POSITION_GROUPS = ["Goalkeepers", "Defenders", "Midfielders", "Forwards"]

# Fields to request per position group
# These match the field names returned by the SofaScore stats endpoint
POSITION_FIELDS: Dict[str, List[str]] = {
    "Goalkeepers": [
        "name", "team", "position", "appearances", "minutesPlayed",
        "saves", "goalsConceded", "cleanSheets",
        "successfulDuelsPercentage", "rating",
    ],
    "Defenders": [
        "name", "team", "position", "appearances", "minutesPlayed",
        "tackles", "interceptions", "clearances",
        "aerialDuelsWon", "aerialDuelsWonPercentage",
        "groundDuelsWon", "groundDuelsWonPercentage",
        "successfulDuelsPercentage", "blockedShots", "errorLeadToGoal",
        "accuratePassesPercentage", "longBallsWonPercentage", "rating",
    ],
    "Midfielders": [
        "name", "team", "position", "appearances", "minutesPlayed",
        "goals", "goalAssist", "keyPasses", "bigChancesCreated",
        "accuratePassesPercentage", "accurateLongBallsPercentage",
        "successfulDribblesPercentage", "tackles", "interceptions",
        "ballRecovery", "rating",
    ],
    "Forwards": [
        "name", "team", "position", "appearances", "minutesPlayed",
        "goals", "goalAssist", "goalsPerGame",
        "shotsOnTarget", "totalShots", "successfulShotsPercentage",
        "bigChances", "bigChancesMissed",
        "successfulDribblesPercentage", "totalDribbles",
        "aerialDuelsWon", "aerialDuelsWonPercentage", "rating",
    ],
}

# ---------------------------------------------------------------------------
# Cloudflare bypass — steal cookies from a real browser session
# ---------------------------------------------------------------------------

SOFASCORE_BASE = "https://api.sofascore.com/api/v1"
SOFASCORE_HOME = "https://www.sofascore.com"

# Rotating user agents
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
]


def _get_browser_cookies_and_headers() -> tuple[dict, dict]:
    """
    Launch headless Chromium via Playwright, visit SofaScore,
    extract real cookies and headers.
    Returns (cookies_dict, headers_dict).
    """
    if not HAS_PLAYWRIGHT:
        raise RuntimeError(
            "Playwright required for Cloudflare bypass.\n"
            "Install: pip install playwright --break-system-packages\n"
            "        python -m playwright install chromium"
        )

    log.info("  Launching headless browser to obtain SofaScore session...")
    cookies: dict = {}
    ua = random.choice(USER_AGENTS)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=ua,
            viewport={"width": 1280, "height": 800},
            locale="en-GB",
        )
        page = context.new_page()
        page.goto(SOFASCORE_HOME, wait_until="networkidle", timeout=30_000)
        time.sleep(2)

        # Grab all cookies from the context
        for cookie in context.cookies():
            cookies[cookie["name"]] = cookie["value"]

        browser.close()

    headers = {
        "User-Agent": ua,
        "Accept": "application/json",
        "Accept-Language": "en-GB,en;q=0.9",
        "Referer": "https://www.sofascore.com/",
        "Origin": "https://www.sofascore.com",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
    }
    log.info(f"  Got {len(cookies)} cookies from browser session.")
    return cookies, headers


# ---------------------------------------------------------------------------
# Disk cache
# ---------------------------------------------------------------------------

def _cache_key(s: str) -> str:
    return hashlib.md5(s.encode()).hexdigest()[:14]


class DiskCache:
    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        cache_dir.mkdir(parents=True, exist_ok=True)

    def get(self, key: str) -> Optional[Any]:
        p = self.cache_dir / f"{_cache_key(key)}.json"
        if p.exists():
            try:
                return json.loads(p.read_text())
            except Exception:
                pass
        return None

    def set(self, key: str, value: Any) -> None:
        p = self.cache_dir / f"{_cache_key(key)}.json"
        try:
            p.write_text(json.dumps(value, default=str))
        except Exception:
            pass


# ---------------------------------------------------------------------------
# HTTP client with retry + jitter
# ---------------------------------------------------------------------------

class SofaScoreClient:
    """
    Thin HTTP client for the SofaScore internal API.
    Handles: cookie session, retries, exponential backoff, disk caching.
    """

    def __init__(self, cache: DiskCache, base_delay: float = 5.0, max_retries: int = 5):
        self.cache = cache
        self.base_delay = base_delay
        self.max_retries = max_retries
        self.session = requests.Session()
        self._cookies: dict = {}
        self._headers: dict = {}
        self._session_ready = False

    def _init_session(self) -> None:
        if self._session_ready:
            return
        self._cookies, self._headers = _get_browser_cookies_and_headers()
        self.session.cookies.update(self._cookies)
        self.session.headers.update(self._headers)
        self._session_ready = True

    def _jitter(self) -> None:
        time.sleep(self.base_delay * random.uniform(0.6, 1.4))

    def get(self, endpoint: str, params: dict = None, cache_key: str = "") -> Optional[dict]:
        """
        GET /api/v1/<endpoint> with caching and retry.
        Returns parsed JSON dict or None on failure.
        """
        ck = cache_key or endpoint + str(params)
        cached = self.cache.get(ck)
        if cached is not None:
            log.debug(f"    [cache] {endpoint[:60]}")
            return cached

        self._init_session()
        url = f"{SOFASCORE_BASE}/{endpoint}"

        for attempt in range(1, self.max_retries + 1):
            try:
                resp = self.session.get(url, params=params, timeout=30)
                if resp.status_code == 200:
                    data = resp.json()
                    self.cache.set(ck, data)
                    self._jitter()
                    return data
                elif resp.status_code in (429, 503):
                    backoff = self.base_delay * (2 ** attempt) + random.uniform(1, 4)
                    log.warning(f"    Rate limited {resp.status_code} (attempt {attempt}/{self.max_retries}). "
                                f"Waiting {backoff:.1f}s...")
                    time.sleep(backoff)
                    # Refresh session cookies after a long block
                    if attempt >= 2:
                        log.info("    Refreshing browser session...")
                        self._session_ready = False
                        self._init_session()
                elif resp.status_code == 403:
                    log.warning(f"    403 Forbidden — refreshing session (attempt {attempt})...")
                    self._session_ready = False
                    self._init_session()
                    time.sleep(self.base_delay * attempt)
                else:
                    log.warning(f"    HTTP {resp.status_code} for {url}")
                    time.sleep(self.base_delay)
            except Exception as exc:
                log.warning(f"    Request error (attempt {attempt}): {exc}")
                time.sleep(self.base_delay * attempt)

        log.error(f"    FAILED after {self.max_retries} attempts: {url}")
        return None

# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def sanitize(v: str) -> str:
    v = str(v).strip().lower()
    v = re.sub(r"[^a-z0-9]+", "_", v)
    return v.strip("_") or "unknown"


def save_csv(df: pd.DataFrame, path: Path, label: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    tag = f"[{label}] " if label else ""
    log.info(f"  SAVED {tag}{path.name}  ({len(df)} rows × {len(df.columns)} cols)")


class SofaScorePipeline:

    def __init__(
        self,
        tournament_id: int,
        season_year: str,
        output_dir: Path,
        teams_filter: Optional[List[str]] = None,
        do_heatmaps: bool = False,
        base_delay: float = 5.0,
    ) -> None:
        self.tid = tournament_id
        self.season_year = season_year  # e.g. "24/25"
        self.teams_filter = [t.lower() for t in teams_filter] if teams_filter else None
        self.do_heatmaps = do_heatmaps

        tid_name = {v: k for k, v in TOURNAMENTS.items()}.get(tournament_id, str(tournament_id))
        self.prefix = f"{sanitize(tid_name)}_{sanitize(season_year)}"
        self.output_dir = output_dir / self.prefix
        self.output_dir.mkdir(parents=True, exist_ok=True)

        cache_dir = self.output_dir / "_cache"
        self.cache = DiskCache(cache_dir)
        self.client = SofaScoreClient(self.cache, base_delay=base_delay)

        self._season_id: Optional[int] = None

    # -----------------------------------------------------------------------
    # Season discovery
    # -----------------------------------------------------------------------

    def _get_season_id(self) -> int:
        if self._season_id:
            return self._season_id

        data = self.client.get(
            f"unique-tournament/{self.tid}/seasons",
            cache_key=f"seasons_{self.tid}",
        )
        if not data:
            raise RuntimeError(f"Could not fetch seasons for tournament {self.tid}")

        for season in data.get("seasons", []):
            if season.get("year") == self.season_year:
                self._season_id = season["id"]
                log.info(f"  Found season '{self.season_year}' → id={self._season_id}")
                return self._season_id

        # List available seasons to help user
        available = [s.get("year") for s in data.get("seasons", [])]
        raise ValueError(
            f"Season '{self.season_year}' not found for tournament {self.tid}.\n"
            f"Available: {available}"
        )

    def list_seasons(self) -> None:
        data = self.client.get(
            f"unique-tournament/{self.tid}/seasons",
            cache_key=f"seasons_{self.tid}",
        )
        if not data:
            log.error("Could not fetch seasons.")
            return
        print(f"\nAvailable seasons for tournament {self.tid}:")
        for s in data.get("seasons", []):
            print(f"  year={s.get('year'):10s}  id={s.get('id')}")

    # -----------------------------------------------------------------------
    # Season player stats (paginated)
    # -----------------------------------------------------------------------

    def _fetch_player_stats_page(
        self,
        season_id: int,
        position_group: str,
        accumulation: str,
        offset: int,
    ) -> dict:
        """
        GET /unique-tournament/{tid}/season/{sid}/statistics
        Paginated: 100 players per page, use 'offset' param.
        """
        # Build the fields string — SofaScore accepts a comma-separated list
        # We request all available fields, SofaScore returns what it has
        all_fields = [
            "goals", "goalAssist", "goalsPerGame",
            "appearances", "minutesPlayed",
            "rating", "position",
            # Shooting
            "shotsOnTarget", "totalShots", "successfulShotsPercentage",
            "bigChances", "bigChancesMissed",
            # Passing
            "keyPasses", "bigChancesCreated",
            "accuratePassesPercentage", "accurateLongBallsPercentage",
            # Dribbling / possession
            "successfulDribblesPercentage", "totalDribbles",
            # Defense
            "tackles", "interceptions", "clearances", "blockedShots",
            "errorLeadToGoal",
            # Duels
            "aerialDuelsWon", "aerialDuelsWonPercentage",
            "groundDuelsWon", "groundDuelsWonPercentage",
            "successfulDuelsPercentage",
            # Goalkeeper
            "saves", "goalsConceded", "cleanSheets",
            # Misc
            "ballRecovery", "yellowCards", "redCards",
        ]
        fields_str = "%2C".join(all_fields)

        # Position group filter
        pos_map = {
            "Goalkeepers": "G",
            "Defenders":   "D",
            "Midfielders": "M",
            "Forwards":    "F",
        }
        pos_param = pos_map.get(position_group, "M")

        endpoint = f"unique-tournament/{self.tid}/season/{season_id}/statistics"
        params = {
            "limit":        "100",
            "order":        "-rating",
            "offset":       str(offset),
            "accumulation": accumulation,
            "fields":       fields_str,
            "filters":      f"position.in.{pos_param}",
        }
        ck = f"stats_{self.tid}_{season_id}_{position_group}_{accumulation}_{offset}"
        return self.client.get(endpoint, params=params, cache_key=ck) or {}

    def _extract_player_stats(self, accumulation: str = "total") -> pd.DataFrame:
        season_id = self._get_season_id()
        all_rows: List[dict] = []

        for group in POSITION_GROUPS:
            log.info(f"  Fetching {group}...")
            offset = 0
            page = 0
            while True:
                page += 1
                data = self._fetch_player_stats_page(season_id, group, accumulation, offset)
                results = data.get("results", [])
                if not results:
                    break

                for item in results:
                    player = item.get("player", {})
                    team   = item.get("team", {})
                    stats  = item.get("statistics", {})

                    row = {
                        "player_id":   player.get("id"),
                        "name":        player.get("name"),
                        "position":    player.get("position", ""),
                        "position_group": group,
                        "team":        team.get("name", ""),
                        "team_id":     team.get("id"),
                        **stats,
                    }
                    all_rows.append(row)

                log.info(f"    page {page}: {len(results)} players (total so far: {len(all_rows)})")

                # If fewer than 100 results, we're on the last page
                if len(results) < 100:
                    break
                offset += 100

        if not all_rows:
            return pd.DataFrame()

        df = pd.DataFrame(all_rows)

        # Filter to selected teams
        if self.teams_filter:
            mask = df["team"].str.lower().apply(
                lambda t: any(f in t for f in self.teams_filter)
            )
            df = df[mask]

        return df.reset_index(drop=True)

    # -----------------------------------------------------------------------
    # Match list
    # -----------------------------------------------------------------------

    def _fetch_matches(self) -> pd.DataFrame:
        season_id = self._get_season_id()
        all_events: List[dict] = []
        page = 0

        log.info("  Fetching match list...")
        while True:
            data = self.client.get(
                f"unique-tournament/{self.tid}/season/{season_id}/events/last/{page}",
                cache_key=f"events_{self.tid}_{season_id}_p{page}",
            )
            if not data:
                break
            events = data.get("events", [])
            if not events:
                break
            all_events.extend(events)
            log.info(f"    page {page}: {len(events)} matches")
            if not data.get("hasNextPage", False):
                break
            page += 1

        if not all_events:
            return pd.DataFrame()

        rows = []
        for e in all_events:
            rows.append({
                "match_id":   e.get("id"),
                "date":       pd.to_datetime(e.get("startTimestamp", 0), unit="s", utc=True).date(),
                "round":      e.get("roundInfo", {}).get("round"),
                "home_team":  e.get("homeTeam", {}).get("name"),
                "home_team_id": e.get("homeTeam", {}).get("id"),
                "away_team":  e.get("awayTeam", {}).get("name"),
                "away_team_id": e.get("awayTeam", {}).get("id"),
                "home_score": e.get("homeScore", {}).get("current"),
                "away_score": e.get("awayScore", {}).get("current"),
                "status":     e.get("status", {}).get("description"),
            })

        df = pd.DataFrame(rows)
        df["date"] = pd.to_datetime(df["date"])
        return df.sort_values("date").reset_index(drop=True)

    # -----------------------------------------------------------------------
    # Fatigue / contextual variables
    # -----------------------------------------------------------------------

    def _build_match_context(self, df_matches: pd.DataFrame) -> pd.DataFrame:
        """Expand matches to long form and compute fatigue + travel variables.

        Features added per team per match:
          days_since_last_match   — rest since previous fixture
          cumulative_matches      — running total of matches played this season
          matches_last_7d         — congestion: #matches in rolling 7-day window
          matches_last_14d        — longer congestion: rolling 14-day window
          is_away                 — 1 if away fixture, 0 if home
          away_leg_sequence       — count of consecutive away matches up to this point
          home_away_alternation_rate — rolling(5) fraction of H-A switches (travel stress proxy)
          rest_category           — well_rested | normal | congested | season_opener
        """
        long_rows = []
        for _, row in df_matches.iterrows():
            for side, opp in [("home", "away"), ("away", "home")]:
                long_rows.append({
                    "match_id":   row["match_id"],
                    "date":       row["date"],
                    "round":      row.get("round"),
                    "team":       row[f"{side}_team"],
                    "team_id":    row.get(f"{side}_team_id"),
                    "opponent":   row[f"{opp}_team"],
                    "is_away":    int(side == "away"),
                    "gf":         row.get(f"{side}_score"),
                    "ga":         row.get(f"{opp}_score"),
                })

        df_long = pd.DataFrame(long_rows).dropna(subset=["team"])

        if self.teams_filter:
            df_long = df_long[
                df_long["team"].str.lower().apply(
                    lambda t: any(f in t for f in self.teams_filter)
                )
            ]

        enriched: List[pd.DataFrame] = []
        for team, grp in df_long.groupby("team"):
            grp = grp.sort_values("date").copy()
            grp["days_since_last_match"] = grp["date"].diff().dt.days
            grp["cumulative_matches"] = range(1, len(grp) + 1)
            grp["is_away"] = grp["is_away"].astype(int)

            # --- Rolling congestion windows ---
            grp = grp.set_index("date")
            grp["matches_last_7d"]  = (grp["match_id"].rolling("7D",
                                        min_periods=1).count() - 1).clip(lower=0).astype(int)
            grp["matches_last_14d"] = (grp["match_id"].rolling("14D",
                                        min_periods=1).count() - 1).clip(lower=0).astype(int)

            # --- Travel / away-leg features ---
            # away_leg_sequence: consecutive running count of away fixtures.
            # Resets to 0 on a home match.
            grp["away_leg_sequence"] = (
                grp["is_away"]
                .groupby((grp["is_away"] != grp["is_away"].shift()).cumsum())
                .cumsum()
            ) * grp["is_away"]

            # home_away_alternation_rate: rolling fraction of H↔A switches
            # over the last 5 matches (proxy for travel stress).
            grp["venue_changed"] = grp["is_away"].ne(grp["is_away"].shift()).astype(int)
            grp["home_away_alternation_rate"] = (
                grp["venue_changed"].rolling(5, min_periods=2).mean().round(3)
            )

            grp = grp.reset_index()

            def rest_cat(d):
                if pd.isna(d):  return "season_opener"
                if d <= 3:      return "congested"
                if d <= 6:      return "normal"
                return "well_rested"

            grp["rest_category"] = grp["days_since_last_match"].apply(rest_cat)
            enriched.append(grp)

        return pd.concat(enriched, ignore_index=True) if enriched else pd.DataFrame()

    def _build_team_fatigue_summary(self, df_context: pd.DataFrame) -> None:
        if df_context.empty:
            return
        required = {
            "team", "days_since_last_match", "matches_last_7d",
            "rest_category", "away_leg_sequence", "home_away_alternation_rate",
        }
        if not required.issubset(df_context.columns):
            return

        summary = df_context.groupby("team").agg(
            total_matches              = ("match_id", "count"),
            avg_days_rest              = ("days_since_last_match", "mean"),
            min_days_rest              = ("days_since_last_match", "min"),
            congested_matches          = ("rest_category", lambda x: (x == "congested").sum()),
            well_rested_matches        = ("rest_category", lambda x: (x == "well_rested").sum()),
            away_matches               = ("is_away", "sum"),
            max_consecutive_away       = ("away_leg_sequence", "max"),
            avg_alternation_rate       = ("home_away_alternation_rate", "mean"),
            total_matches_last7d       = ("matches_last_7d", "sum"),
        ).reset_index()
        summary["congestion_rate"]       = (summary["congested_matches"] / summary["total_matches"]).round(3)
        summary["avg_days_rest"]         = summary["avg_days_rest"].round(1)
        summary["avg_alternation_rate"]  = summary["avg_alternation_rate"].round(3)

        save_csv(summary, self.output_dir / f"{self.prefix}_team_fatigue_summary.csv", "Team fatigue")

    # -----------------------------------------------------------------------
    # Heatmaps (optional — per-player full-season)
    # -----------------------------------------------------------------------

    def _render_heatmap(self, xs, ys, player_name: str, out_path: Path) -> None:
        if not HAS_MATPLOTLIB:
            return
        fig, ax = plt.subplots(figsize=(10, 7))
        ax.set_facecolor("#1a7a1a")
        fig.patch.set_facecolor("#1a7a1a")
        ax.set_xlim(0, 100)
        ax.set_ylim(0, 100)
        for s in ax.spines.values():
            s.set_edgecolor("white")
        if len(xs) > 5:
            hb = ax.hexbin(xs, ys, gridsize=22, cmap="YlOrRd", alpha=0.80,
                           mincnt=1, extent=(0, 100, 0, 100))
            plt.colorbar(hb, ax=ax, label="Frequency")
        else:
            ax.scatter(xs, ys, color="yellow", s=60, alpha=0.8)
        ax.plot([50, 50], [0, 100], "w--", lw=0.8, alpha=0.5)
        ax.add_patch(plt.Circle((50, 50), 9.15, color="white", fill=False, lw=0.8, alpha=0.5))
        ax.add_patch(plt.Rectangle((0, 21), 16, 58, fill=False, edgecolor="white", lw=0.6, alpha=0.4))
        ax.add_patch(plt.Rectangle((84, 21), 16, 58, fill=False, edgecolor="white", lw=0.6, alpha=0.4))
        ax.set_title(player_name, color="white", fontsize=12)
        ax.tick_params(colors="white")
        plt.tight_layout()
        plt.savefig(out_path, dpi=120, bbox_inches="tight")
        plt.close()

    def _extract_heatmaps(self, df_players: pd.DataFrame) -> None:
        season_id = self._get_season_id()
        heatmap_dir = self.output_dir / "heatmaps"
        heatmap_dir.mkdir(exist_ok=True)

        player_ids = df_players[["player_id", "name", "team"]].dropna(subset=["player_id"])
        total = len(player_ids)
        log.info(f"  Extracting full-season heatmaps for {total} players...")

        for idx, (_, row) in enumerate(player_ids.iterrows(), start=1):
            pid   = int(row["player_id"])
            pname = row["name"]
            team  = sanitize(row.get("team", "unknown"))

            done_marker = heatmap_dir / f"{team}_{sanitize(pname)}.done"
            if done_marker.exists():
                log.info(f"  [{idx}/{total}] {pname} — cached, skipping")
                continue

            log.info(f"  [{idx}/{total}] {pname} ({team})...")

            data = self.client.get(
                f"player/{pid}/unique-tournament/{self.tid}/season/{season_id}/heatmap/overall",
                cache_key=f"heatmap_{pid}_{self.tid}_{season_id}",
            )
            if not data:
                log.warning(f"    no data")
                continue

            points = data.get("heatmap", [])
            if not points:
                log.info("    empty heatmap")
                continue

            xs = [p.get("x", 0) for p in points]
            ys = [p.get("y", 0) for p in points]

            # Save CSV
            df_heat = pd.DataFrame({"x": xs, "y": ys})
            df_heat["player"] = pname
            df_heat["player_id"] = pid
            df_heat["team"] = row.get("team", "")
            save_csv(df_heat, heatmap_dir / f"{team}_{sanitize(pname)}_heatmap.csv", "heatmap")

            # Render PNG
            if HAS_MATPLOTLIB:
                self._render_heatmap(xs, ys, pname, heatmap_dir / f"{team}_{sanitize(pname)}_heatmap.png")

            done_marker.touch()
            log.info(f"    OK — {len(points)} points")

    # -----------------------------------------------------------------------
    # Position profiles
    # -----------------------------------------------------------------------

    def _build_position_profiles(self, df: pd.DataFrame) -> None:
        profiles_dir = self.output_dir / "position_profiles"
        profiles_dir.mkdir(exist_ok=True)

        for group, wanted_cols in POSITION_FIELDS.items():
            available = [c for c in wanted_cols if c in df.columns]
            if not available:
                continue
            subset = df[df["position_group"] == group][available].copy()
            if subset.empty:
                continue
            if "rating" in subset.columns:
                subset = subset.sort_values("rating", ascending=False)
            save_csv(subset, profiles_dir / f"{self.prefix}_{sanitize(group)}.csv", group)

    # -----------------------------------------------------------------------
    # Run
    # -----------------------------------------------------------------------

    def run(self) -> None:
        log.info(f"\n{'='*60}")
        log.info(f"  SofaScore Direct Pipeline — FixtureIQ")
        log.info(f"  Tournament ID : {self.tid}")
        log.info(f"  Season        : {self.season_year}")
        log.info(f"  Teams filter  : {self.teams_filter or 'all'}")
        log.info(f"  Heatmaps      : {'yes' if self.do_heatmaps else 'no'}")
        log.info(f"{'='*60}")

        # 1 — Discover season
        self._get_season_id()

        # 2 — Player stats
        log.info("\n[1/5] Extracting season player stats...")
        df_players = self._extract_player_stats(accumulation="total")
        if not df_players.empty:
            save_csv(df_players, self.output_dir / f"{self.prefix}_all_players.csv", "All players")
            log.info("\n[2/5] Building position profiles...")
            self._build_position_profiles(df_players)
        else:
            log.warning("  No player data extracted.")

        # 3 — Matches + fatigue
        log.info("\n[3/5] Fetching match list & computing fatigue variables...")
        df_matches = self._fetch_matches()
        if not df_matches.empty:
            save_csv(df_matches, self.output_dir / f"{self.prefix}_matches.csv", "Matches")
            df_context = self._build_match_context(df_matches)
            if not df_context.empty:
                save_csv(df_context, self.output_dir / f"{self.prefix}_match_context.csv", "Match context")
                self._build_team_fatigue_summary(df_context)
        else:
            log.warning("  No match data extracted.")

        # 4 — Heatmaps
        if self.do_heatmaps and not df_players.empty:
            log.info("\n[4/5] Extracting full-season player heatmaps...")
            self._extract_heatmaps(df_players)
        else:
            log.info("\n[4/5] Heatmaps skipped (use --heatmaps to enable)")

        # 5 — Summary
        log.info(f"\n{'='*60}")
        log.info(f"  DONE — {self.output_dir}")
        log.info(f"  CSVs : {len(list(self.output_dir.rglob('*.csv')))}")
        log.info(f"  PNGs : {len(list(self.output_dir.rglob('*.png')))}")
        log.info(f"{'='*60}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="SofaScore Direct Pipeline — no ScraperFC needed.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    p.add_argument(
        "--tournament-id", type=int, default=7,
        help="SofaScore unique-tournament ID. Default: 7 (UEFA Champions League)\n"
             "Other IDs: EPL=17, La Liga=8, Bundesliga=35, Serie A=23, Ligue1=34",
    )
    p.add_argument(
        "--season-year", default="24/25",
        help="Season year as shown on SofaScore. Default: '24/25'\n"
             "Use --list-seasons to see available values.",
    )
    p.add_argument(
        "--team", nargs="+", dest="teams", default=None, metavar="TEAM",
        help="Filter to specific teams, e.g. --team Arsenal Liverpool\n"
             "Default (no flag): Arsenal, Liverpool, Manchester City, Chelsea, Aston Villa\n"
             "(the 5 PL clubs competing in the UEFA Champions League)",
    )
    p.add_argument("--output-dir", default="Data", help="Output directory. Default: Data")
    p.add_argument(
        "--heatmaps", action="store_true",
        help="Extract full-season heatmap per player (~1 req per player, slow).",
    )
    p.add_argument(
        "--delay", type=float, default=5.0,
        help="Base delay in seconds between API calls. Default: 5.0\n"
             "Increase to 10+ if you keep getting blocked.",
    )
    p.add_argument(
        "--list-seasons", action="store_true",
        help="Print available seasons for the given tournament-id and exit.",
    )
    p.add_argument(
        "--clear-cache", action="store_true",
        help="Delete the disk cache before running (forces fresh extraction).",
    )
    p.add_argument(
        "--dry-run", action="store_true",
        help="Print what would be extracted without making any HTTP requests.",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    teams = args.teams if args.teams else list(PL_UCL_TEAMS.keys())

    pipeline = SofaScorePipeline(
        tournament_id=args.tournament_id,
        season_year=args.season_year,
        output_dir=Path(args.output_dir),
        teams_filter=teams,
        do_heatmaps=args.heatmaps,
        base_delay=args.delay,
    )

    if args.clear_cache:
        import shutil
        cache_dir = pipeline.output_dir / "_cache"
        if cache_dir.exists():
            shutil.rmtree(cache_dir)
            log.info("Cache purged.")
        else:
            log.info("No cache to purge.")

    if args.dry_run:
        # Minimal session init to discover season, then exit without fetching
        log.info("=== DRY RUN — no data will be fetched ===")
        try:
            sid = pipeline._get_season_id()
            log.info(f"  Would fetch season id={sid} for tid={pipeline.tid} "
                     f"({pipeline.season_year})")
            log.info(f"  Teams filter : {teams}")
            log.info(f"  Heatmaps     : {'yes' if args.heatmaps else 'no'}")
            log.info(f"  Output dir   : {pipeline.output_dir}")
        except Exception as exc:
            log.error(f"  Could not resolve season info: {exc}")
        return

    if args.list_seasons:
        pipeline.list_seasons()
        return

    pipeline.run()


if __name__ == "__main__":
    main()
