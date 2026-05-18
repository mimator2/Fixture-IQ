#!/usr/bin/env python3
"""
FBref Advanced Player Performance Pipeline
============================================
Extracts rich per-player statistics for Champions League (or any competition) teams.

Covers position-specific metrics:
  - Defenders   : tackles, interceptions, clearances, aerials, blocks
  - Midfielders : key passes, progressive passes, pass accuracy, ball recoveries
  - DMs/CDMs    : defensive coverage, pressing, duels won, recoveries
  - Wingers     : dribbles (take-ons), progressive carries, touches in final third
  - Forwards    : shots, xG, goals, shot accuracy

Stat tables extracted per player:
  stats_standard   → appearances, goals, assists, xG, xAG, progressive actions
  stats_shooting   → shots, SoT, xG, np:xG, distance
  stats_passing    → passes, key passes, progressive passes, pass%, xA
  stats_passing_types → pass types (live, dead, switches, crosses, corners)
  stats_gca        → shot-creating actions, goal-creating actions
  stats_defense    → tackles, pressures, blocks, interceptions, clearances
  stats_possession → dribbles, carries, progressive carries, miscontrols, touches
  stats_misc       → fouls, aerials won/lost, recoveries, offsides

Usage
-----
Single team:
  python fbref_advanced_pipeline.py \\
    --squad-id 8602292d --team-slug Real-Madrid --season 2024-2025 --output-dir Data

Multiple teams:
  python fbref_advanced_pipeline.py \\
    --team "8602292d:Real-Madrid" \\
    --team "b8fd03ef:Manchester-City" \\
    --team "19686d73:Arsenal" \\
    --season 2024-2025 --output-dir Data --headless

From URL:
  python fbref_advanced_pipeline.py \\
    --team-url "https://fbref.com/en/squads/8602292d/2024-2025/Real-Madrid-Stats" \\
    --season 2024-2025 --output-dir Data
"""

from __future__ import annotations

import argparse
import re
import time
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse

import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def sanitize_filename(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_") or "unknown"


def parse_team_spec(team_spec: str) -> tuple[str, str]:
    """Parse '<squad_id>:<team_slug>' or '<squad_id>,<team_slug>'."""
    text = team_spec.strip()
    for sep in (":", ","):
        if sep in text:
            squad_id, team_slug = text.split(sep, 1)
            squad_id, team_slug = squad_id.strip(), team_slug.strip()
            if squad_id and team_slug:
                return squad_id, team_slug
    raise ValueError(
        f"Invalid --team value '{team_spec}'. Use '<squad_id>:<team_slug>', "
        "e.g. '8602292d:Real-Madrid'."
    )


def parse_team_from_stats_url(url: str) -> tuple[str, str, str]:
    """Extract (squad_id, season, team_slug) from an FBref Stats URL."""
    parsed = urlparse(url)
    segments = [s for s in parsed.path.split("/") if s]
    if "squads" not in segments:
        raise ValueError(f"URL does not look like a squad URL: {url}")
    idx = segments.index("squads")
    if len(segments) <= idx + 3:
        raise ValueError(f"URL missing required segments: {url}")
    squad_id = segments[idx + 1]
    season = segments[idx + 2]
    page_slug = segments[idx + 3]
    if page_slug == "all_comps":
        page_slug = segments[idx + 4]
    if page_slug.endswith("-Stats-All-Competitions"):
        team_slug = page_slug[: -len("-Stats-All-Competitions")]
    elif page_slug.endswith("-Stats"):
        team_slug = page_slug[: -len("-Stats")]
    else:
        team_slug = page_slug
    return squad_id, season, team_slug


# ---------------------------------------------------------------------------
# Stat table definitions
# ---------------------------------------------------------------------------

# Each entry: (table_suffix, readable_label, position_groups_it_matters_for)
STAT_TABLES = [
    ("stats_standard",      "Standard",       ["ALL"]),
    ("stats_shooting",      "Shooting",       ["FW", "ST"]),
    ("stats_passing",       "Passing",        ["MF", "CM", "DM"]),
    ("stats_passing_types", "PassTypes",      ["MF", "CM"]),
    ("stats_gca",           "GoalCreating",   ["FW", "MF", "WG"]),
    ("stats_defense",       "Defense",        ["DF", "CB", "DM"]),
    ("stats_possession",    "Possession",     ["WG", "MF", "FW"]),
    ("stats_misc",          "Misc",           ["ALL"]),
]

# Human-readable column renames applied after merging all tables
COLUMN_RENAME: Dict[str, str] = {
    # Identity
    "player":                       "Player",
    "nationality":                  "Nation",
    "position":                     "Position",
    "age":                          "Age",
    "squad":                        "Squad",
    # Standard
    "games":                        "MP",
    "games_starts":                 "Starts",
    "minutes":                      "Min",
    "minutes_90s":                  "90s",
    "goals":                        "Gls",
    "assists":                      "Ast",
    "goals_assists":                "G+A",
    "goals_pens":                   "G-PK",
    "pens_made":                    "PK",
    "pens_att":                     "PKatt",
    "cards_yellow":                 "YC",
    "cards_red":                    "RC",
    "xg":                           "xG",
    "npxg":                         "npxG",
    "xg_assist":                    "xAG",
    "npxg_xg_assist":               "npxG+xAG",
    "progressive_carries":          "ProgC",
    "progressive_passes":           "ProgP",
    "progressive_passes_received":  "ProgR",
    # Shooting
    "shots":                        "Sh",
    "shots_on_target":              "SoT",
    "shots_on_target_pct":          "SoT%",
    "shots_per90":                  "Sh/90",
    "shots_on_target_per90":        "SoT/90",
    "goals_per_shot":               "G/Sh",
    "goals_per_shot_on_target":     "G/SoT",
    "average_shot_distance":        "AvgShotDist",
    "shots_free_kicks":             "ShFK",
    "pens_made_shots":              "PK_Sh",
    "npxg_per_shot":                "npxG/Sh",
    "xg_net":                       "G-xG",
    "npxg_net":                     "npG-npxG",
    # Passing
    "passes_completed":             "PassCmp",
    "passes":                       "PassAtt",
    "passes_pct":                   "Pass%",
    "passes_total_distance":        "PassDist",
    "passes_progressive_distance":  "PassProgDist",
    "passes_completed_short":       "ShortCmp",
    "passes_short":                 "ShortAtt",
    "passes_pct_short":             "Short%",
    "passes_completed_medium":      "MedCmp",
    "passes_medium":                "MedAtt",
    "passes_pct_medium":            "Med%",
    "passes_completed_long":        "LongCmp",
    "passes_long":                  "LongAtt",
    "passes_pct_long":              "Long%",
    "assisted_shots":               "KeyPass",
    "passes_into_final_third":      "PassFin3",
    "passes_into_penalty_area":     "PassPen",
    "crosses_into_penalty_area":    "CrsPen",
    # Pass types
    "passes_live":                  "PassLive",
    "passes_dead":                  "PassDead",
    "passes_free_kicks":            "PassFK",
    "through_balls":                "Through",
    "passes_switches":              "Switch",
    "crosses":                      "Crs",
    "throw_ins":                    "ThrowIn",
    "corner_kicks":                 "CK",
    "corner_kicks_in":              "CK_In",
    "corner_kicks_out":             "CK_Out",
    "corner_kicks_straight":        "CK_Str",
    "passes_offsides":              "PassOff",
    "passes_blocked":               "PassBlk",
    # Goal/Shot creating actions
    "sca":                          "SCA",
    "sca_per90":                    "SCA/90",
    "sca_passes_live":              "SCA_PassLive",
    "sca_passes_dead":              "SCA_PassDead",
    "sca_take_ons":                 "SCA_Drib",
    "sca_shots":                    "SCA_Sh",
    "sca_fouled":                   "SCA_Fld",
    "sca_defense":                  "SCA_Def",
    "gca":                          "GCA",
    "gca_per90":                    "GCA/90",
    "gca_passes_live":              "GCA_PassLive",
    "gca_passes_dead":              "GCA_PassDead",
    "gca_take_ons":                 "GCA_Drib",
    "gca_shots":                    "GCA_Sh",
    "gca_fouled":                   "GCA_Fld",
    "gca_defense":                  "GCA_Def",
    # Defense
    "tackles":                      "Tkl",
    "tackles_won":                  "TklWon",
    "tackles_def_3rd":              "Tkl_Def3",
    "tackles_mid_3rd":              "Tkl_Mid3",
    "tackles_att_3rd":              "Tkl_Att3",
    "challenge_tackles":            "DribTkl",
    "challenges":                   "DribAtt",
    "challenge_tackles_pct":        "DribTkl%",
    "challenges_lost":              "DribLost",
    "blocks":                       "Blk",
    "blocked_shots":                "BlkSh",
    "blocked_passes":               "BlkPass",
    "interceptions":                "Int",
    "tackles_interceptions":        "Tkl+Int",
    "clearances":                   "Clr",
    "errors":                       "Err",
    "pressures":                    "Press",
    "pressure_regains":             "PressSucc",
    "pressure_regain_pct":          "Press%",
    "pressures_def_3rd":            "Press_Def3",
    "pressures_mid_3rd":            "Press_Mid3",
    "pressures_att_3rd":            "Press_Att3",
    # Possession
    "touches":                      "Touches",
    "touches_def_pen_area":         "Touch_DefPen",
    "touches_def_3rd":              "Touch_Def3",
    "touches_mid_3rd":              "Touch_Mid3",
    "touches_att_3rd":              "Touch_Att3",
    "touches_att_pen_area":         "Touch_AttPen",
    "touches_live_ball":            "Touch_Live",
    "take_ons":                     "DribAtt_Poss",
    "take_ons_won":                 "DribSucc",
    "take_ons_won_pct":             "Drib%",
    "take_ons_tackled":             "DribTkld",
    "take_ons_tackled_pct":         "DribTkld%",
    "carries":                      "Carries",
    "carries_distance":             "CarryDist",
    "carries_progressive_distance": "CarryProgDist",
    "carries_progressive":          "ProgCarries",
    "carries_into_final_third":     "Carry_Fin3",
    "carries_into_penalty_area":    "Carry_Pen",
    "miscontrols":                  "Mis",
    "dispossessed":                 "Dis",
    "passes_received":              "Rec",
    # Misc
    "cards_yellow_red":             "YR",
    "fouls":                        "Fls",
    "fouled":                       "Fld",
    "offsides":                     "Off",
    "pens_won":                     "PKwon",
    "pens_conceded":                "PKcon",
    "own_goals":                    "OG",
    "ball_recoveries":              "Recov",
    "aerials_won":                  "AerWon",
    "aerials_lost":                 "AerLost",
    "aerials_won_pct":              "Aer%",
}

# Position profile groupings for the summary sheet
POSITION_PROFILES: Dict[str, List[str]] = {
    "GK": ["Player", "Nation", "Position", "Age", "MP", "Starts", "Min"],
    "DF/CB": [
        "Player", "Nation", "Position", "Age", "MP", "Min",
        "Tkl", "TklWon", "Tkl_Def3", "Int", "Tkl+Int", "Clr", "Blk", "BlkSh",
        "Press", "Press%", "AerWon", "Aer%", "Recov", "Err",
        "ProgP", "PassCmp", "Pass%", "xG", "Gls", "Ast",
    ],
    "DM/CDM": [
        "Player", "Nation", "Position", "Age", "MP", "Min",
        "Tkl", "TklWon", "Int", "Tkl+Int", "Press", "Press%", "Recov",
        "PassCmp", "Pass%", "KeyPass", "ProgP", "Through",
        "Touches", "Touch_Mid3", "Carries", "ProgCarries",
        "SCA", "GCA", "xG", "Gls", "Ast",
    ],
    "CM/MF": [
        "Player", "Nation", "Position", "Age", "MP", "Min",
        "PassCmp", "Pass%", "KeyPass", "ProgP", "PassFin3", "Through",
        "SCA", "SCA/90", "GCA",
        "Carries", "ProgCarries", "Carry_Fin3", "Touch_Mid3", "Touch_Att3",
        "DribSucc", "Drib%", "Tkl", "Int", "Recov",
        "xG", "xAG", "Gls", "Ast",
    ],
    "WG/AM": [
        "Player", "Nation", "Position", "Age", "MP", "Min",
        "DribAtt_Poss", "DribSucc", "Drib%",
        "Carries", "ProgCarries", "Carry_Fin3", "Carry_Pen",
        "Touch_Att3", "Touch_AttPen",
        "SCA", "SCA/90", "GCA", "GCA/90",
        "KeyPass", "ProgP", "PassFin3", "PassPen", "CrsPen",
        "Sh", "SoT", "SoT%", "xG", "npxG", "Gls", "Ast", "xAG",
    ],
    "FW/ST": [
        "Player", "Nation", "Position", "Age", "MP", "Min",
        "Gls", "Ast", "G+A", "G-PK", "xG", "npxG", "G-xG",
        "Sh", "SoT", "SoT%", "Sh/90", "SoT/90", "G/Sh", "G/SoT", "AvgShotDist",
        "GCA", "GCA/90", "SCA",
        "DribSucc", "Drib%", "Touch_AttPen", "Carry_Pen",
        "AerWon", "Aer%",
    ],
}


# ---------------------------------------------------------------------------
# Main pipeline class
# ---------------------------------------------------------------------------

class FbrefAdvancedPipeline:

    def __init__(
        self,
        squad_id: str,
        season: str,
        team_slug: str,
        output_dir: Path,
        headless: bool = False,
    ) -> None:
        self.squad_id = squad_id
        self.season = season
        self.team_slug = team_slug
        self.base_prefix = f"{sanitize_filename(team_slug)}_{sanitize_filename(season)}"
        self.output_dir = output_dir / self.base_prefix
        self.headless = headless
        self.output_dir.mkdir(parents=True, exist_ok=True)

    # -----------------------------------------------------------------------
    # Browser helpers
    # -----------------------------------------------------------------------

    def _build_driver(self) -> webdriver.Chrome:
        options = Options()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument(
            "user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        if self.headless:
            options.add_argument("--headless=new")
        driver = webdriver.Chrome(
            service=ChromeService(ChromeDriverManager().install()),
            options=options,
        )
        driver.set_page_load_timeout(60)
        return driver

    def _load_html(self, url: str, wait_seconds: int = 10, max_retries: int = 3) -> str:
        """Load a page with Selenium, scroll to trigger JS rendering, return HTML."""
        for attempt in range(1, max_retries + 1):
            try:
                print(f"  Loading: {url}" + (f" (attempt {attempt})" if attempt > 1 else ""))
                driver = self._build_driver()
                try:
                    driver.get(url)
                    time.sleep(wait_seconds)
                    # Scroll to load lazy content
                    for _ in range(10):
                        driver.execute_script("window.scrollBy(0, window.innerHeight);")
                        time.sleep(0.3)
                    html = driver.page_source
                    if html and len(html) > 2000:
                        return html
                    raise RuntimeError("Page HTML suspiciously small")
                finally:
                    driver.quit()
            except Exception as exc:
                print(f"    ERROR attempt {attempt}: {exc}")
                if attempt < max_retries:
                    backoff = 2 ** attempt
                    print(f"    Retrying in {backoff}s…")
                    time.sleep(backoff)
                else:
                    raise

    # -----------------------------------------------------------------------
    # HTML parsing
    # -----------------------------------------------------------------------

    def _find_stats_table(self, soup: BeautifulSoup, table_suffix: str) -> Optional[object]:
        """
        FBref wraps some tables inside HTML comments; try both the live DOM
        and comment-unwrapped HTML.
        """
        # 1) Try live DOM (some pages render all tables)
        table = soup.find("table", {"id": re.compile(table_suffix, re.I)})
        if table:
            return table

        # 2) Unwrap HTML comments (FBref hides extra tables in comments)
        raw_html = str(soup)
        comments = re.findall(r"<!--(.*?)-->", raw_html, re.DOTALL)
        for comment in comments:
            if table_suffix in comment:
                comment_soup = BeautifulSoup(comment, "html.parser")
                table = comment_soup.find("table", {"id": re.compile(table_suffix, re.I)})
                if table:
                    return table
        return None

    def _parse_table(self, table) -> pd.DataFrame:
        """Parse an FBref stats table into a DataFrame, skipping sub-header rows."""
        if table is None:
            return pd.DataFrame()

        # Collect column keys from thead
        thead = table.find("thead")
        stat_keys: List[str] = []
        if thead:
            # Use the LAST header row (FBref uses multi-row headers)
            header_rows = thead.find_all("tr")
            last_row = header_rows[-1] if header_rows else None
            if last_row:
                for th in last_row.find_all(["th", "td"]):
                    key = th.get("data-stat", "")
                    stat_keys.append(key)

        tbody = table.find("tbody")
        if not tbody:
            return pd.DataFrame()

        records: List[Dict[str, str]] = []
        for row in tbody.find_all("tr"):
            classes = row.get("class") or []
            if "thead" in classes or "spacer" in classes or "partial_table" in classes:
                continue
            row_data: Dict[str, str] = {}
            for cell in row.find_all(["th", "td"]):
                ds = cell.get("data-stat")
                if ds:
                    # For player name cells, also try to get the clean text
                    text = cell.get_text(strip=True)
                    row_data[ds] = text
            if row_data and row_data.get("player"):
                records.append(row_data)

        if not records:
            return pd.DataFrame()

        df = pd.DataFrame(records)
        return df

    # -----------------------------------------------------------------------
    # Core extraction
    # -----------------------------------------------------------------------

    def _extract_all_stat_tables(self, html: str) -> Dict[str, pd.DataFrame]:
        """Extract all stat tables from a single all-competitions page."""
        soup = BeautifulSoup(html, "html.parser")
        results: Dict[str, pd.DataFrame] = {}

        for suffix, label, _ in STAT_TABLES:
            print(f"    Extracting: {label} ({suffix})…", end=" ")
            table = self._find_stats_table(soup, suffix)
            if table is None:
                print("NOT FOUND")
                results[suffix] = pd.DataFrame()
            else:
                df = self._parse_table(table)
                print(f"{len(df)} rows")
                results[suffix] = df

        return results

    def _merge_tables(self, tables: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        Merge all stat tables on player identity columns.
        Uses outer join so players with partial data are preserved.
        """
        # Identity columns present in multiple tables — keep from standard only
        identity_cols = {"player", "nationality", "position", "age", "squad", "games",
                         "games_starts", "minutes", "minutes_90s", "team"}

        base_suffixes = ["stats_standard", "stats_shooting", "stats_passing",
                         "stats_passing_types", "stats_gca", "stats_defense",
                         "stats_possession", "stats_misc"]

        merged: Optional[pd.DataFrame] = None

        for suffix in base_suffixes:
            df = tables.get(suffix, pd.DataFrame())
            if df.empty:
                continue

            if merged is None:
                merged = df
                continue

            # Drop duplicate identity cols from right side (keep from left)
            right_drop = [c for c in identity_cols if c in df.columns and c != "player"]
            df_right = df.drop(columns=right_drop, errors="ignore")

            # Suffix duplicated non-identity columns
            overlap = set(merged.columns) & set(df_right.columns) - {"player"}
            if overlap:
                df_right = df_right.rename(
                    columns={c: f"{c}__{suffix.replace('stats_', '')}" for c in overlap}
                )

            merged = pd.merge(merged, df_right, on="player", how="outer")

        if merged is None or merged.empty:
            return pd.DataFrame()

        # Clean up: drop completely empty rows, reset index
        merged = merged[merged["player"].notna() & (merged["player"] != "")].reset_index(drop=True)
        return merged

    def _rename_and_clean(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply human-readable column names and drop FBref internal columns."""
        # Drop rank/match columns we don't need
        drop_patterns = ["ranker", "matches", "comp_level"]
        df = df.drop(columns=[c for c in df.columns if any(p in c for p in drop_patterns)], errors="ignore")

        # Apply rename map (only columns that exist)
        rename = {k: v for k, v in COLUMN_RENAME.items() if k in df.columns}
        df = df.rename(columns=rename)
        return df

    def _build_position_profiles(self, df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """
        Create position-specific DataFrames with only the relevant columns.
        Assigns each player to a profile based on their Position value.
        """
        def classify(pos: str) -> str:
            pos = str(pos).upper()
            if "GK" in pos:
                return "GK"
            if any(x in pos for x in ["CB", "RB", "LB", "WB"]):
                return "DF/CB"
            if "DM" in pos or pos == "DM":
                return "DM/CDM"
            if any(x in pos for x in ["CM", "MF"]) and "AM" not in pos:
                return "CM/MF"
            if any(x in pos for x in ["AM", "LW", "RW", "WG", "SS"]):
                return "WG/AM"
            if any(x in pos for x in ["FW", "ST", "CF", "SS"]):
                return "FW/ST"
            # Generic MF fallback
            if "MF" in pos or "MID" in pos:
                return "CM/MF"
            return "CM/MF"  # default

        profiles: Dict[str, pd.DataFrame] = {}
        pos_col = "Position" if "Position" in df.columns else None

        for profile_name, wanted_cols in POSITION_PROFILES.items():
            if profile_name == "GK":
                if pos_col:
                    mask = df[pos_col].fillna("").str.upper().str.contains("GK")
                    subset = df[mask].copy()
                else:
                    subset = pd.DataFrame()
            else:
                if pos_col:
                    mask = df[pos_col].fillna("").apply(classify) == profile_name
                    subset = df[mask].copy()
                else:
                    subset = df.copy()

            # Keep only columns that exist in the merged df
            available = [c for c in wanted_cols if c in df.columns]
            if subset.empty or not available:
                profiles[profile_name] = pd.DataFrame(columns=available)
            else:
                profiles[profile_name] = subset[available].reset_index(drop=True)

        return profiles

    # -----------------------------------------------------------------------
    # Save helpers
    # -----------------------------------------------------------------------

    def _save(self, df: pd.DataFrame, filename: str) -> None:
        path = self.output_dir / filename
        df.to_csv(path, index=False)
        print(f"    ✅ Saved: {filename} ({len(df)} rows, {len(df.columns)} cols)")

    # -----------------------------------------------------------------------
    # Public run method
    # -----------------------------------------------------------------------

    def run(self) -> None:
        team_display = self.team_slug.replace("-", " ")
        print(f"\n{'='*60}")
        print(f"  {team_display} | {self.season}")
        print(f"{'='*60}")

        # FBref all-competitions squad stats page
        all_comps_url = (
            f"https://fbref.com/en/squads/{self.squad_id}/{self.season}/all_comps/"
            f"{self.team_slug}-Stats-All-Competitions"
        )

        print(f"\n[1/4] Loading FBref all-competitions page…")
        html = self._load_html(all_comps_url)

        print(f"\n[2/4] Extracting stat tables…")
        tables = self._extract_all_stat_tables(html)

        print(f"\n[3/4] Merging and cleaning data…")
        merged = self._merge_tables(tables)

        if merged.empty:
            print("  ⚠️  No data extracted. Check squad_id / team_slug / season.")
            return

        merged_clean = self._rename_and_clean(merged)

        # Save full merged CSV
        self._save(merged_clean, f"{self.base_prefix}_players_all_stats.csv")

        print(f"\n[4/4] Building position-specific profiles…")
        profiles_dir = self.output_dir / "position_profiles"
        profiles_dir.mkdir(exist_ok=True)

        profiles = self._build_position_profiles(merged_clean)
        for profile_name, profile_df in profiles.items():
            safe_name = sanitize_filename(profile_name)
            filename = f"{self.base_prefix}_{safe_name}.csv"
            filepath = profiles_dir / filename
            profile_df.to_csv(filepath, index=False)
            print(f"    ✅ {profile_name}: {len(profile_df)} players → position_profiles/{filename}")

        # Also save a compact summary (key metrics across all positions)
        summary_cols = [
            "Player", "Nation", "Position", "Age", "MP", "Min",
            "Gls", "Ast", "G+A", "xG", "xAG",
            "Sh", "SoT%",
            "PassCmp", "Pass%", "KeyPass", "ProgP",
            "DribSucc", "Drib%", "ProgCarries",
            "Tkl", "Int", "Clr", "Press", "Recov",
            "AerWon", "Aer%",
        ]
        summary_available = [c for c in summary_cols if c in merged_clean.columns]
        summary_df = merged_clean[summary_available].copy()
        self._save(summary_df, f"{self.base_prefix}_players_summary.csv")

        print(f"\n✅ Done: {team_display}")
        print(f"   Output: {self.output_dir}")
        print(f"   Files : {len(list(self.output_dir.rglob('*.csv')))} CSVs total")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract rich per-player FBref statistics for football teams.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("--squad-id",  help="FBref squad ID, e.g. 8602292d")
    parser.add_argument("--season",    required=True, help="Season, e.g. 2024-2025")
    parser.add_argument("--team-slug", help="Team slug, e.g. Real-Madrid")
    parser.add_argument(
        "--team", action="append", default=[],
        help="Multi-team: '<squad_id>:<team_slug>' (repeatable)",
    )
    parser.add_argument(
        "--team-url", action="append", default=[],
        help="FBref team Stats URL (repeatable)",
    )
    parser.add_argument("--output-dir", default="Data", help="Output directory (default: Data)")
    parser.add_argument("--headless", action="store_true", help="Run Chrome headless")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    teams: List[tuple[str, str]] = []

    for spec in args.team:
        teams.append(parse_team_spec(spec))

    for url in args.team_url:
        squad_id, season_from_url, team_slug = parse_team_from_stats_url(url)
        if season_from_url != args.season:
            raise ValueError(
                f"Season mismatch: URL has '{season_from_url}' but --season is '{args.season}'"
            )
        teams.append((squad_id, team_slug))

    if not teams:
        if not args.squad_id or not args.team_slug:
            raise ValueError(
                "Provide --squad-id and --team-slug (single team), "
                "or --team / --team-url (multiple teams)."
            )
        teams.append((args.squad_id, args.team_slug))

    # De-duplicate
    seen: set = set()
    unique: List[tuple[str, str]] = []
    for item in teams:
        if item not in seen:
            seen.add(item)
            unique.append(item)

    output_dir = Path(args.output_dir)

    for squad_id, team_slug in unique:
        pipeline = FbrefAdvancedPipeline(
            squad_id=squad_id,
            season=args.season,
            team_slug=team_slug,
            output_dir=output_dir,
            headless=args.headless,
        )
        pipeline.run()


if __name__ == "__main__":
    main()
