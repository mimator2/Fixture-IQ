#!/usr/bin/env python3
"""
Generic FBref match data pipeline.

This pipeline is designed to work for any team and any season as long as
the required FBref URL components are provided.
"""

from __future__ import annotations

import argparse
import re
import time
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import unquote, urljoin, urlparse, quote

import pandas as pd
import requests
import cloudscraper
import undetected_chromedriver as uc
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


def slugify(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9]+", "_", value.strip())
    return value.strip("_").lower()


def sanitize_filename(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_") or "unknown"


def parse_team_spec(team_spec: str) -> tuple[str, str]:
    """Parse a team spec formatted as '<squad_id>:<team_slug>' or '<squad_id>,<team_slug>'."""
    text = team_spec.strip()
    for sep in (":", ","):
        if sep in text:
            squad_id, team_slug = text.split(sep, 1)
            squad_id = squad_id.strip()
            team_slug = team_slug.strip()
            if squad_id and team_slug:
                return squad_id, team_slug
    raise ValueError(
        f"Invalid --team value '{team_spec}'. Use '<squad_id>:<team_slug>', "
        "for example '18bb7c10:Arsenal'."
    )


def parse_team_from_stats_url(url: str) -> tuple[str, str, str]:
    """Extract (squad_id, season, team_slug) from an FBref team Stats URL."""
    parsed = urlparse(url)
    segments = [seg for seg in parsed.path.split("/") if seg]

    # Expected base shapes:
    # /en/squads/<squad_id>/<season>/<team-slug>-Stats
    # /en/squads/<squad_id>/<season>/all_comps/<team-slug>-Stats-All-Competitions
    if "squads" not in segments:
        raise ValueError(f"URL does not look like a squad URL: {url}")

    idx = segments.index("squads")
    if len(segments) <= idx + 3:
        raise ValueError(f"URL is missing required squad/season/team segments: {url}")

    squad_id = segments[idx + 1]
    season = segments[idx + 2]
    page_slug = segments[idx + 3]

    # Handle all_comps URLs where the team slug is the next segment.
    if page_slug == "all_comps":
        if len(segments) <= idx + 4:
            raise ValueError(f"URL is missing team segment after all_comps: {url}")
        page_slug = segments[idx + 4]

    # Handles variations like:
    # Manchester-City-Stats
    # Liverpool-Stats-All-Competitions
    if page_slug.endswith("-Stats-All-Competitions"):
        team_slug = page_slug[: -len("-Stats-All-Competitions")]
    elif page_slug.endswith("-Stats"):
        team_slug = page_slug[: -len("-Stats")]
    else:
        # Fallback for uncommon pages such as roster paths
        team_slug = page_slug.replace("-Roster-Details", "")

    if not squad_id or not season or not team_slug:
        raise ValueError(f"Could not parse squad/team details from URL: {url}")

    return squad_id, season, team_slug


def extract_match_id(match_url: str) -> str:
    parsed = urlparse(match_url)
    parts = [p for p in parsed.path.split("/") if p]
    if len(parts) >= 3 and parts[0] == "en" and parts[1] == "matches":
        return parts[2]
    return "unknown_match"


def build_match_report_name(date: str, competition: str, opponent: str) -> str:
    """Build a readable, filesystem-safe match report name: Date_Competition_Opponent."""
    date_value = (date or "unknown_date").strip()
    comp_value = sanitize_filename(competition or "unknown_competition")
    opp_value = sanitize_filename(opponent or "unknown_opponent")
    return f"{date_value}_{comp_value}_{opp_value}"


class FbrefPipeline:
    def __init__(
        self,
        squad_id: str,
        season: str,
        team_slug: str,
        output_dir: Path,
        headless: bool = False,
        shooting_url: Optional[str] = None,
        roster_url: Optional[str] = None,
        scrape_do_token: Optional[str] = None,
    ) -> None:
        self.squad_id = squad_id
        self.season = season
        self.team_slug = team_slug
        self.base_prefix = f"{sanitize_filename(team_slug)}_{sanitize_filename(season)}"
        self.output_dir = output_dir / self.base_prefix
        self.headless = headless
        self.shooting_url = shooting_url
        self.roster_url = roster_url
        self.scrape_do_token = scrape_do_token
        self.incomplete_matches: List[Dict[str, str]] = []

        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.by_comp_dir = self.output_dir / "by_competition"
        self.by_comp_dir.mkdir(parents=True, exist_ok=True)

    def _build_driver(self) -> webdriver.Chrome:
        """Build undetected Chrome driver for Cloudflare bypass."""
        options = uc.ChromeOptions()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument(
            "user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        if self.headless:
            options.add_argument("--headless=new")
        
        try:
            driver = uc.Chrome(options=options, version_main=None)
            driver.set_page_load_timeout(45)
            return driver
        except Exception as e:
            print(f"  WARNING: undetected-chromedriver failed ({e}), falling back to standard Selenium")
            # Fallback to standard Chrome if undetected fails
            options_std = Options()
            options_std.add_argument("--no-sandbox")
            options_std.add_argument("--disable-dev-shm-usage")
            options_std.add_argument("--disable-blink-features=AutomationControlled")
            options_std.add_argument(
                "user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
            )
            if self.headless:
                options_std.add_argument("--headless=new")
            driver = webdriver.Chrome(
                service=ChromeService(ChromeDriverManager().install()),
                options=options_std,
            )
            driver.set_page_load_timeout(45)
            return driver

    def _load_html(self, url: str, wait_seconds: int = 30, max_retries: int = 5) -> str:
        """Load HTML using scrape.do if token provided, otherwise cloudscraper/Selenium."""
        print(f"\nLoading: {url}")
        
        # Primary method: scrape.do (if token provided)
        if self.scrape_do_token:
            print("  Attempting to load with scrape.do (paid proxy service)...")
            for attempt in range(1, max_retries + 1):
                try:
                    # Construct scrape.do API URL
                    scrape_do_url = f"http://api.scrape.do/?url={quote(url, safe='')}&token={self.scrape_do_token}"
                    
                    print(f"  Attempt {attempt}/{max_retries}...")
                    response = requests.get(scrape_do_url, timeout=60)
                    
                    if response.status_code == 200:
                        html = response.text
                        print(f"  ✓ Loaded via scrape.do ({len(html)} chars)")
                        
                        # Verify we have actual content
                        if "<table" in html and len(html) > 5000:
                            print(f"  ✓ HTML contains tables, returning")
                            return html
                        else:
                            print(f"  ⚠ No tables or insufficient content, retrying...")
                            if attempt < max_retries:
                                time.sleep(2 ** attempt)
                                continue
                    else:
                        print(f"  ✗ HTTP {response.status_code}, retrying...")
                        if attempt < max_retries:
                            time.sleep(2 ** attempt)
                            continue
                            
                except Exception as e:
                    print(f"  ✗ Error: {str(e)}")
                    if attempt < max_retries:
                        wait_time = 2 ** attempt
                        print(f"  Retrying in {wait_time}s...")
                        time.sleep(wait_time)
                        continue
            
            print("  scrape.do exhausted, falling back to cloudscraper...")
        
        # Secondary method: cloudscraper (designed for Cloudflare)
        print("  Attempting to load with cloudscraper...")
        for attempt in range(1, max_retries + 1):
            try:
                # Create a new scraper for each attempt
                scraper = cloudscraper.create_scraper(
                    browser='chrome',
                    delay=15 + (attempt * 5)  # Increasing delay per attempt
                )
                
                headers = {
                    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Referer': 'https://fbref.com/'
                }
                
                print(f"  Attempt {attempt}/{max_retries}...")
                response = scraper.get(url, headers=headers, timeout=60)
                
                if response.status_code == 200:
                    html = response.text
                    print(f"  ✓ Loaded ({len(html)} chars)")
                    
                    # Verify it's not a Cloudflare challenge page
                    if "Un momento" in html or len(html) < 5000:
                        print(f"  ⚠ Got Cloudflare challenge page, retrying...")
                        if attempt < max_retries:
                            wait_time = 2 ** attempt
                            print(f"  Waiting {wait_time}s before retry...")
                            time.sleep(wait_time)
                            continue
                    
                    # Verify we have tables
                    if "<table" in html:
                        print(f"  ✓ HTML contains tables, returning")
                        return html
                    else:
                        print(f"  ⚠ No tables found in HTML, retrying...")
                        if attempt < max_retries:
                            wait_time = 2 ** attempt
                            print(f"  Waiting {wait_time}s before retry...")
                            time.sleep(wait_time)
                            continue
                else:
                    print(f"  ✗ HTTP {response.status_code}, retrying...")
                    if attempt < max_retries:
                        time.sleep(2 ** attempt)
                        continue
                        
            except Exception as e:
                print(f"  ✗ Error: {str(e)}")
                if attempt < max_retries:
                    wait_time = 2 ** attempt
                    print(f"  Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    raise RuntimeError(f"cloudscraper failed after {max_retries} attempts: {str(e)}")
        
        # Fallback: Selenium as last resort
        print("  cloudscraper exhausted, trying Selenium fallback...")
        try:
            driver = self._build_driver()
            try:
                driver.get(url)
                time.sleep(45)
                for _ in range(20):
                    driver.execute_script("window.scrollBy(0, window.innerHeight);")
                    time.sleep(0.8)
                html = driver.page_source
                print(f"  ✓ Selenium loaded ({len(html)} chars)")
                if html and len(html) > 5000:
                    return html
            finally:
                driver.quit()
        except Exception as e:
            print(f"  Selenium failed: {str(e)}")
            raise RuntimeError(f"All methods failed to load: {str(e)}")

    def _extract_table_rows(self, html: str, table_id: str = "matchlogs") -> pd.DataFrame:
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table", {"id": table_id})

        if not table:
            for candidate in soup.find_all("table"):
                header_text = candidate.get_text(" ", strip=True).lower()
                if "opponent" in header_text and ("date" in header_text or "comp" in header_text):
                    table = candidate
                    break

        if not table:
            print("  WARNING: No suitable match log table found - checking for alternatives...")
            tables = soup.find_all("table")
            print(f"  Found {len(tables)} tables on page")
            # Debug: save HTML to file for inspection
            debug_file = self.output_dir / "debug_html.txt"
            debug_file.write_text(html[:5000], encoding="utf-8")
            print(f"  [DEBUG] Saved first 5000 chars of HTML to: {debug_file}")
            raise RuntimeError("No suitable match log table found in page HTML.")

        tbody = table.find("tbody")
        if not tbody:
            raise RuntimeError("Match log table has no tbody.")

        records: List[Dict[str, str]] = []
        for row in tbody.find_all("tr"):
            if "thead" in (row.get("class") or []):
                continue

            row_data: Dict[str, str] = {}

            th = row.find("th")
            if th and th.get("data-stat"):
                row_data[th.get("data-stat")] = th.get_text(strip=True)

            for td in row.find_all("td"):
                data_stat = td.get("data-stat")
                if not data_stat:
                    continue
                if data_stat == "match_report":
                    link = td.find("a", href=True)
                    if link:
                        row_data["match_report_url"] = urljoin("https://fbref.com", link["href"])
                row_data[data_stat] = td.get_text(strip=True)

            if row_data:
                records.append(row_data)

        if not records:
            raise RuntimeError("No match rows extracted from the table.")

        return pd.DataFrame(records)

    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        rename_map = {
            "date": "Date",
            "dayofweek": "Day",
            "venue": "Venue",
            "result": "Result",
            "opponent": "Opponent",
            "gf": "GF",
            "ga": "GA",
            "comp": "Competition",
            "round": "Round",
            "match_report": "Match_Report",
            "match_report_url": "Match_Report_URL",
            "goals": "Gls",
            "shots": "Sh",
            "shots_on_target": "SoT",
            "shots_on_target_pct": "SoT%",
            "goals_per_shot": "G/Sh",
            "goals_per_shot_on_target": "G/SoT",
            "pens_made": "PK",
            "pens_att": "PKatt",
        }
        available_map = {k: v for k, v in rename_map.items() if k in df.columns}
        normalized = df.rename(columns=available_map)
        return normalized

    def _save_main_tables(self, df_all: pd.DataFrame) -> None:
        all_file = self.output_dir / f"{self.base_prefix}_matches_all.csv"
        df_all.to_csv(all_file, index=False)
        print(f"Saved all matches: {all_file.name} ({len(df_all)} rows)")

        if "Competition" in df_all.columns:
            for comp_name, comp_df in df_all.groupby("Competition"):
                comp_file = self.by_comp_dir / (
                    f"{self.base_prefix}_{sanitize_filename(str(comp_name))}.csv"
                )
                comp_df.to_csv(comp_file, index=False)
                print(f"Saved competition table: by_competition/{comp_file.name} ({len(comp_df)} rows)")

        if "Opponent" in df_all.columns:
            opponents = (
                df_all[["Opponent"]]
                .dropna()
                .drop_duplicates()
                .sort_values("Opponent")
                .reset_index(drop=True)
            )
            opponents.insert(0, "team_id", range(1, len(opponents) + 1))
            opponents_file = self.output_dir / f"{self.base_prefix}_opponents.csv"
            opponents.to_csv(opponents_file, index=False)
            print(f"Saved opponents: {opponents_file.name} ({len(opponents)} rows)")

            teams = opponents.rename(columns={"Opponent": "club_name"})
            teams["stadium"] = "Unknown"
            teams["where_they_play"] = "Unknown"
            teams_file = self.output_dir / f"{self.base_prefix}_teams.csv"
            teams.to_csv(teams_file, index=False)
            print(f"Saved teams table: {teams_file.name} ({len(teams)} rows)")

    def _save_shooting_table(self) -> None:
        if not self.shooting_url:
            return

        html = self._load_html(self.shooting_url)
        df_shoot = self._extract_table_rows(html)
        df_shoot = self._normalize_columns(df_shoot)

        preferred_cols = [
            "Date",
            "Day",
            "Venue",
            "Result",
            "GF",
            "GA",
            "Opponent",
            "Gls",
            "Sh",
            "SoT",
            "SoT%",
            "G/Sh",
            "G/SoT",
            "PK",
            "PKatt",
        ]
        cols = [c for c in preferred_cols if c in df_shoot.columns]
        if cols:
            df_shoot = df_shoot[cols]

        shooting_file = self.output_dir / self._competition_file_name_from_url(self.shooting_url)
        df_shoot.to_csv(shooting_file, index=False)
        print(f"Saved shooting table: {shooting_file.name} ({len(df_shoot)} rows)")

    def _extract_roster_rows(self, html: str) -> pd.DataFrame:
        soup = BeautifulSoup(html, "html.parser")

        # FBref roster table id is typically 'roster'
        table = soup.find("table", {"id": re.compile(r"roster", re.I)})
        if not table:
            for candidate in soup.find_all("table"):
                header_text = candidate.get_text(" ", strip=True).lower()
                if "player" in header_text and "min" in header_text:
                    table = candidate
                    break

        if not table:
            raise RuntimeError("No roster table found in page HTML.")

        # Collect all unique data-stat keys from thead to preserve order
        thead = table.find("thead")
        stat_keys: List[str] = []
        if thead:
            for th in thead.find_all(["th", "td"]):
                key = th.get("data-stat")
                if key and key not in stat_keys:
                    stat_keys.append(key)

        tbody = table.find("tbody")
        if not tbody:
            raise RuntimeError("Roster table has no tbody.")

        records: List[Dict[str, str]] = []
        for row in tbody.find_all("tr"):
            if "thead" in (row.get("class") or []):
                continue
            row_data: Dict[str, str] = {}
            th = row.find("th")
            if th and th.get("data-stat"):
                row_data[th.get("data-stat")] = th.get_text(strip=True)
            for td in row.find_all("td"):
                ds = td.get("data-stat")
                if ds:
                    row_data[ds] = td.get_text(strip=True)
            if row_data:
                records.append(row_data)

        if not records:
            raise RuntimeError("No player rows extracted from roster table.")

        df = pd.DataFrame(records)
        # Reorder to match thead order where possible
        ordered = [k for k in stat_keys if k in df.columns]
        remaining = [c for c in df.columns if c not in ordered]
        return df[ordered + remaining]

    def _normalize_roster_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        # FBref uses prefixed data-stat names for grouped competition columns.
        # Common patterns: lg_*, dome_cup_*, intl_cup_*, all_*
        rename_map = {
            "player": "Player",
            "birth_year": "Birth_Year",
            "age": "Age",
            "nationality": "Country",
            "position": "Position",
            "squad": "Squad",
            # Domestic League
            "lg_games": "DL_MP",
            "lg_minutes": "DL_Min",
            "lg_goals": "DL_Gls",
            "lg_assists": "DL_Ast",
            # Domestic Cups
            "dome_cup_games": "DC_MP",
            "dome_cup_minutes": "DC_Min",
            "dome_cup_goals": "DC_Gls",
            "dome_cup_assists": "DC_Ast",
            # International Cups
            "intl_cup_games": "IC_MP",
            "intl_cup_minutes": "IC_Min",
            "intl_cup_goals": "IC_Gls",
            "intl_cup_assists": "IC_Ast",
            # All Competitions
            "all_games": "All_MP",
            "all_minutes": "All_Min",
            "all_goals": "All_Gls",
            "all_assists": "All_Ast",
        }
        available_map = {k: v for k, v in rename_map.items() if k in df.columns}
        return df.rename(columns=available_map)

    def _save_roster_table(self) -> None:
        url = self.roster_url
        if not url:
            # Auto-build from squad_id, season, team_slug
            url = (
                f"https://fbref.com/en/squads/{self.squad_id}/{self.season}/"
                f"roster/{self.team_slug}-Roster-Details"
            )
            print(f"No roster URL provided — using auto-built URL: {url}")

        html = self._load_html(url)
        df_roster = self._extract_roster_rows(html)
        df_roster = self._normalize_roster_columns(df_roster)

        roster_file = self.output_dir / f"{self.base_prefix}_roster.csv"
        df_roster.to_csv(roster_file, index=False)
        print(f"Saved roster table: {roster_file.name} ({len(df_roster)} rows, {len(df_roster.columns)} cols)")

    # ------------------------------------------------------------------
    # Player standard stats (all_comps page)
    # ------------------------------------------------------------------

    _PLAYER_STAT_RENAME: Dict[str, str] = {
        "player": "Player",
        "nationality": "Nation",
        "position": "Pos",
        "age": "Age",
        "games": "MP",
        "games_starts": "Starts",
        "minutes": "Min",
        "minutes_90s": "90s",
        "goals": "Gls",
        "assists": "Ast",
        "goals_assists": "G+A",
        "goals_pens": "G-PK",
        "pens_made": "PK",
        "pens_att": "PKatt",
        "cards_yellow": "CrdY",
        "cards_red": "CrdR",
        "goals_per90": "Gls_90",
        "assists_per90": "Ast_90",
        "goals_assists_per90": "G+A_90",
        "goals_pens_per90": "G-PK_90",
        "goals_assists_pens_per90": "G+A-PK_90",
        "matches": "Matches",
    }

    def _standard_stats_competition_map(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Map stats_standard table ids to competition labels using FBref tab controls."""
        mapping: Dict[str, str] = {}
        for node in soup.find_all(attrs={"data-show": True}):
            data_show = node.get("data-show", "")
            match = re.search(r"stats_standard_[A-Za-z0-9_]+", data_show)
            if not match:
                continue
            table_id = match.group(0)
            label = node.get_text(" ", strip=True)
            if label and table_id not in mapping:
                mapping[table_id] = label
        return mapping

    def _extract_standard_stats_table(self, table) -> pd.DataFrame:
        """Extract rows from a single stats_standard_* table element."""
        thead = table.find("thead")
        stat_keys: List[str] = []
        if thead:
            for th in thead.find_all(["th", "td"]):
                key = th.get("data-stat")
                if key and key not in stat_keys:
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
            th = row.find("th")
            if th and th.get("data-stat"):
                row_data[th.get("data-stat")] = th.get_text(strip=True)
            for td in row.find_all("td"):
                ds = td.get("data-stat")
                if ds:
                    row_data[ds] = td.get_text(strip=True)
            if row_data.get("player", "").strip().lower() in ("", "squad total", "opponent total"):
                continue
            if row_data:
                records.append(row_data)

        if not records:
            return pd.DataFrame()

        df = pd.DataFrame(records)
        ordered = [k for k in stat_keys if k in df.columns]
        remaining = [c for c in df.columns if c not in ordered]
        df = df[ordered + remaining]
        available = {k: v for k, v in self._PLAYER_STAT_RENAME.items() if k in df.columns}
        return df.rename(columns=available)

    def _save_player_stats_tables(self) -> None:
        url = (
            f"https://fbref.com/en/squads/{self.squad_id}/{self.season}/"
            f"all_comps/{self.team_slug}-Stats-All-Competitions"
        )
        print(f"\nLoading player standard stats from: {url}")
        html = self._load_html(url)
        soup = BeautifulSoup(html, "html.parser")

        player_stats_dir = self.output_dir / "player_stats"
        player_stats_dir.mkdir(parents=True, exist_ok=True)
        comp_map = self._standard_stats_competition_map(soup)

        tables = soup.find_all("table", {"id": re.compile(r"^stats_standard", re.I)})
        if not tables:
            print("  WARNING: No stats_standard tables found on all_comps page.")
            return

        used_slugs: set[str] = set()
        for table in tables:
            table_id: str = table.get("id", "")

            comp_label = comp_map.get(table_id, "")
            if not comp_label:
                if table_id.endswith("_combined"):
                    comp_label = "All Competitions"
                else:
                    comp_label = table_id.replace("stats_standard_", "")

            comp_label = re.sub(r"\s+", " ", comp_label).strip()
            comp_slug = sanitize_filename(comp_label)
            if not comp_slug:
                comp_slug = sanitize_filename(table_id) or "unknown_competition"

            # Guarantee unique file names even if FBref labels collide.
            if comp_slug in used_slugs:
                comp_slug = f"{comp_slug}_{sanitize_filename(table_id)}"
            used_slugs.add(comp_slug)

            df = self._extract_standard_stats_table(table)
            if df.empty:
                print(f"  Skipping empty table: {table_id}")
                continue

            out_file = player_stats_dir / f"{self.base_prefix}_players_{comp_slug}.csv"
            df.to_csv(out_file, index=False)
            print(f"  Saved: player_stats/{out_file.name} ({len(df)} players)  [{comp_label}]")

    def _extract_lineup_rows(
        self,
        lineup_table,
        team_display_name: str,
        match_meta: Dict[str, str],
    ) -> List[Dict[str, str]]:
        rows: List[Dict[str, str]] = []
        section = "Starter"
        formation = ""

        for tr in lineup_table.find_all("tr"):
            th = tr.find("th")
            tds = tr.find_all("td")

            if th and not tds:
                title = th.get_text(" ", strip=True)
                if title.lower() == "bench":
                    section = "Bench"
                    continue
                if "(" in title and ")" in title:
                    formation = title.split("(", 1)[1].split(")", 1)[0].strip()
                continue

            if len(tds) < 2:
                continue

            number = tds[0].get_text(" ", strip=True)
            player = tds[1].get_text(" ", strip=True)
            if not player:
                continue

            row = dict(match_meta)
            row.update(
                {
                    "Team": team_display_name,
                    "Formation": formation,
                    "Lineup_Section": section,
                    "Jersey_Number": number,
                    "Player": player,
                }
            )
            rows.append(row)

        return rows

    def _extract_stats_rows(self, table, match_meta: Dict[str, str], team_display_name: str) -> List[Dict[str, str]]:
        rows: List[Dict[str, str]] = []
        if not table:
            return rows

        thead = table.find("thead")
        stat_keys: List[str] = []
        if thead:
            for th in thead.find_all(["th", "td"]):
                key = th.get("data-stat")
                if key and key not in stat_keys:
                    stat_keys.append(key)

        tbody = table.find("tbody")
        if not tbody:
            return rows

        for tr in tbody.find_all("tr"):
            classes = tr.get("class") or []
            if "thead" in classes or "spacer" in classes or "partial_table" in classes:
                continue

            row_data: Dict[str, str] = {}
            th = tr.find("th")
            if th and th.get("data-stat"):
                row_data[th.get("data-stat")] = th.get_text(" ", strip=True)
            for td in tr.find_all("td"):
                ds = td.get("data-stat")
                if ds:
                    row_data[ds] = td.get_text(" ", strip=True)

            if not row_data:
                continue

            ordered_data: Dict[str, str] = {}
            for key in stat_keys:
                if key in row_data:
                    ordered_data[key] = row_data[key]
            for key, value in row_data.items():
                if key not in ordered_data:
                    ordered_data[key] = value

            row = dict(match_meta)
            row["Team"] = team_display_name
            row.update(ordered_data)
            rows.append(row)

        return rows

    def _save_match_report_tables(self, df_all: pd.DataFrame) -> None:
        if "Match_Report_URL" not in df_all.columns:
            print("No Match_Report_URL column found; skipping per-match report extraction.")
            return

        match_rows = (
            df_all[df_all["Match_Report_URL"].notna()]
            .drop_duplicates(subset=["Match_Report_URL"])
            .copy()
        )
        if match_rows.empty:
            print("No match report URLs found; skipping per-match report extraction.")
            return

        match_report_dir = self.output_dir / "match_reports"
        match_report_dir.mkdir(parents=True, exist_ok=True)

        player_rename_map = {k: v for k, v in self._PLAYER_STAT_RENAME.items()}
        keeper_rename_map = {
            "player": "Player",
            "nationality": "Nation",
            "age": "Age",
            "minutes": "Min",
            "shots_on_target_against": "SoTA",
            "goals_against_gk": "GA",
            "saves": "Saves",
            "save_pct": "Save%",
            "gk_shots_on_target_against": "SoTA",
            "gk_goals_against": "GA",
            "gk_saves": "Saves",
            "gk_save_pct": "Save%",
        }

        for idx, (_, row) in enumerate(match_rows.iterrows(), start=1):
            match_url = str(row.get("Match_Report_URL", "")).strip()
            if not match_url:
                continue

            print(f"  [{idx}/{len(match_rows)}] Match report: {match_url}")
            player_table = None
            keeper_table = None
            html = None
            
            for attempt in range(3):
                try:
                    html = self._load_html(match_url, max_retries=2)
                    break
                except Exception as e:
                    print(f"    Error loading page (attempt {attempt+1}): {str(e)}")
                    if attempt < 2:
                        time.sleep(2)
            
            if not html:
                print(f"    SKIP: Could not load match page")
                continue
            
            soup = BeautifulSoup(html, "html.parser")
            player_table = soup.find("table", {"id": f"stats_{self.squad_id}_summary"})
            keeper_table = soup.find("table", {"id": f"keeper_stats_{self.squad_id}"})

            if not player_table:
                for table in soup.find_all("table"):
                    t_id = table.get("id", "")
                    if "stats" in t_id and "summary" in t_id and "keeper" not in t_id:
                        player_table = table
                        break
            
            if not keeper_table:
                for table in soup.find_all("table"):
                    t_id = table.get("id", "")
                    if "keeper_stats" in t_id:
                        keeper_table = table
                        break

            if not player_table or not keeper_table:
                # Track incomplete matches for retry
                incomplete_data = {
                    "Match_Report_URL": match_url,
                    "Date": str(row.get("Date", "")),
                    "Competition": str(row.get("Competition", "")),
                    "Opponent": str(row.get("Opponent", "")),
                    "has_player_stats": player_table is not None,
                    "has_keeper_stats": keeper_table is not None,
                }
                self.incomplete_matches.append(incomplete_data)
                if not player_table and not keeper_table:
                    print(f"    WARNING: No team stats tables found (will retry later)")
                    continue
                else:
                    missing = []
                    if not player_table:
                        missing.append("player stats")
                    if not keeper_table:
                        missing.append("keeper stats")
                    print(f"    WARNING: Missing {', '.join(missing)} (will retry later)")

            team_display_name = self.team_slug.replace("-", " ")
            if player_table:
                caption = player_table.find("caption")
                if caption:
                    cap_text = caption.get_text(" ", strip=True)
                    team_display_name = cap_text.replace(" Player Stats Table", "").strip()

            match_meta = {
                "Match_ID": extract_match_id(match_url),
                "Match_Report_URL": match_url,
                "Date": str(row.get("Date", "")),
                "Competition": str(row.get("Competition", "")),
                "Round": str(row.get("Round", "")),
                "Venue": str(row.get("Venue", "")),
                "Opponent": str(row.get("Opponent", "")),
                "Result": str(row.get("Result", "")),
            }
            match_name = build_match_report_name(
                date=match_meta.get("Date", ""),
                competition=match_meta.get("Competition", ""),
                opponent=match_meta.get("Opponent", ""),
            )
            match_meta["Match_Report_Name"] = match_name

            per_match_dir = match_report_dir / match_name
            per_match_dir.mkdir(parents=True, exist_ok=True)

            # Find lineup table by exact team lineup header match.
            lineup_table = None
            for table in soup.find_all("table"):
                if table.get("id"):
                    continue
                head = table.find("th")
                if not head:
                    continue
                header_text = head.get_text(" ", strip=True)
                if header_text.startswith(f"{team_display_name} ("):
                    lineup_table = table
                    break

            match_lineup_rows: List[Dict[str, str]] = []
            if lineup_table:
                match_lineup_rows = self._extract_lineup_rows(lineup_table, team_display_name, match_meta)
            else:
                print(f"    WARNING: lineup table not found for team '{team_display_name}'")

            match_player_rows = self._extract_stats_rows(player_table, match_meta, team_display_name)
            match_keeper_rows = self._extract_stats_rows(keeper_table, match_meta, team_display_name)

            # Save per-match files using Date_Competition_Opponent naming for clarity.
            if match_lineup_rows:
                pd.DataFrame(match_lineup_rows).to_csv(
                    per_match_dir / f"{match_name}_lineups.csv",
                    index=False,
                )
            if match_player_rows:
                pd.DataFrame(match_player_rows).rename(columns=player_rename_map).to_csv(
                    per_match_dir / f"{match_name}_player_stats.csv",
                    index=False,
                )
            if match_keeper_rows:
                pd.DataFrame(match_keeper_rows).rename(columns=keeper_rename_map).to_csv(
                    per_match_dir / f"{match_name}_goalkeeper_stats.csv",
                    index=False,
                )

    def _retry_incomplete_matches(self, df_all: pd.DataFrame) -> None:
        """Retry extraction for matches with incomplete data using more aggressive strategies."""
        if not self.incomplete_matches:
            return
        
        print(f"\n=== RETRYING {len(self.incomplete_matches)} INCOMPLETE MATCHES ===")
        player_rename_map = {k: v for k, v in self._PLAYER_STAT_RENAME.items()}
        keeper_rename_map = {
            "player": "Player",
            "nationality": "Nation",
            "age": "Age",
            "minutes": "Min",
            "shots_on_target_against": "SoTA",
            "goals_against_gk": "GA",
            "saves": "Saves",
            "save_pct": "Save%",
            "gk_shots_on_target_against": "SoTA",
            "gk_goals_against": "GA",
            "gk_saves": "Saves",
            "gk_save_pct": "Save%",
        }
        
        match_report_dir = self.output_dir / "match_reports"
        successfully_retried = 0
        
        for retry_idx, incomplete in enumerate(self.incomplete_matches, start=1):
            match_url = incomplete["Match_Report_URL"]
            opponent = incomplete["Opponent"]
            competition = incomplete["Competition"]
            
            print(f"\n[RETRY {retry_idx}/{len(self.incomplete_matches)}] {opponent} ({competition})")
            print(f"  URL: {match_url}")
            
            player_table = None
            keeper_table = None
            html = None
            
            # Retry with more aggressive strategies: longer waits, more attempts
            try:
                html = self._load_html(match_url, wait_seconds=15, max_retries=4)
            except Exception as e:
                print(f"  FINAL SKIP: Could not load match page after 4 attempts: {str(e)}")
                continue
            
            if not html:
                print(f"  FINAL SKIP: No HTML retrieved")
                continue
            
            soup = BeautifulSoup(html, "html.parser")
            
            # Try primary table IDs first
            player_table = soup.find("table", {"id": f"stats_{self.squad_id}_summary"})
            keeper_table = soup.find("table", {"id": f"keeper_stats_{self.squad_id}"})
            
            # Fallback: scan all tables for stats tables
            if not player_table:
                for table in soup.find_all("table"):
                    t_id = table.get("id", "")
                    if "stats" in t_id and "summary" in t_id and "keeper" not in t_id:
                        player_table = table
                        print(f"  Found player table via fallback: {t_id}")
                        break
                    if not t_id and "Pos" in table.get_text():
                        # Alternative: look for table with position data
                        player_table = table
                        print(f"  Found player table via content match")
                        break
            
            if not keeper_table:
                for table in soup.find_all("table"):
                    t_id = table.get("id", "")
                    if "keeper_stats" in t_id:
                        keeper_table = table
                        print(f"  Found keeper table via ID: {t_id}")
                        break
                    if "keeper" in t_id.lower() or "gk" in t_id.lower():
                        keeper_table = table
                        print(f"  Found keeper table via keyword: {t_id}")
                        break
            
            # Prepare match metadata
            matching_rows = df_all[df_all["Match_Report_URL"] == match_url]
            if matching_rows.empty:
                print(f"  WARNING: Could not find match in main table")
                continue
            
            row = matching_rows.iloc[0]
            team_display_name = self.team_slug.replace("-", " ")
            
            if player_table:
                caption = player_table.find("caption")
                if caption:
                    cap_text = caption.get_text(" ", strip=True)
                    team_display_name = cap_text.replace(" Player Stats Table", "").strip()
            
            match_meta = {
                "Match_ID": extract_match_id(match_url),
                "Match_Report_URL": match_url,
                "Date": str(row.get("Date", "")),
                "Competition": str(row.get("Competition", "")),
                "Round": str(row.get("Round", "")),
                "Venue": str(row.get("Venue", "")),
                "Opponent": str(row.get("Opponent", "")),
                "Result": str(row.get("Result", "")),
            }
            match_name = build_match_report_name(
                date=match_meta.get("Date", ""),
                competition=match_meta.get("Competition", ""),
                opponent=match_meta.get("Opponent", ""),
            )
            match_meta["Match_Report_Name"] = match_name
            per_match_dir = match_report_dir / match_name
            per_match_dir.mkdir(parents=True, exist_ok=True)
            
            # Extract stats if tables found
            match_player_rows = self._extract_stats_rows(player_table, match_meta, team_display_name) if player_table else []
            match_keeper_rows = self._extract_stats_rows(keeper_table, match_meta, team_display_name) if keeper_table else []
            
            # Save extracted stats
            saved_count = 0
            if match_player_rows:
                pd.DataFrame(match_player_rows).rename(columns=player_rename_map).to_csv(
                    per_match_dir / f"{match_name}_player_stats.csv",
                    index=False,
                )
                print(f"  ✅ Saved player stats ({len(match_player_rows)} rows)")
                saved_count += 1
            
            if match_keeper_rows:
                pd.DataFrame(match_keeper_rows).rename(columns=keeper_rename_map).to_csv(
                    per_match_dir / f"{match_name}_goalkeeper_stats.csv",
                    index=False,
                )
                print(f"  ✅ Saved goalkeeper stats ({len(match_keeper_rows)} rows)")
                saved_count += 1
            
            if saved_count > 0:
                successfully_retried += 1
        
        print(f"\n=== RETRY SUMMARY ===")
        print(f"Retried: {len(self.incomplete_matches)}")
        print(f"Successfully completed: {successfully_retried}")
        print(f"Still incomplete: {len(self.incomplete_matches) - successfully_retried}")

    def _competition_file_name_from_url(self, url: str) -> str:
        parsed = urlparse(url)
        slug = Path(unquote(parsed.path)).name
        if not slug:
            return f"{self.base_prefix}_shooting.csv"

        # Keep the source naming, but align with requested style: Match_Logs
        slug = slug.replace("-Match-Logs-", "-Match_Logs-")
        return f"{slug}.csv"

    def validate_data(self) -> tuple[int, int, int, int]:
        """Return counts: (matches, competitions, reports, total_files)"""
        matches = 0
        comps = 0
        reports = 0
        main_f = list(self.output_dir.glob("*_matches_all.csv"))
        if main_f:
            matches = len(pd.read_csv(main_f[0]))
        comp_d = self.output_dir / "by_competition"
        if comp_d.exists():
            comps = len(list(comp_d.glob("*.csv")))
        mr_d = self.output_dir / "match_reports"
        if mr_d.exists():
            reports = len([d for d in mr_d.iterdir() if d.is_dir()])
        total = len(list(self.output_dir.rglob("*.csv")))
        return matches, comps, reports, total

    def run(self) -> None:
        all_matches_url = (
            f"https://fbref.com/en/squads/{self.squad_id}/{self.season}/"
            f"all_comps/{self.team_slug}-Stats-All-Competitions"
        )

        html = self._load_html(all_matches_url)
        df_all = self._extract_table_rows(html)
        df_all = self._normalize_columns(df_all)

        self._save_main_tables(df_all)
        self._save_shooting_table()
        self._save_player_stats_tables()
        self._save_match_report_tables(df_all)
        
        # Retry any matches with incomplete data
        self._retry_incomplete_matches(df_all)

        csv_files = sorted(self.output_dir.rglob("*.csv"))
        matches, comps, reports, total = self.validate_data()
        print(f"\n=== EXTRACTION VALIDATION ===")
        print(f"Matches: {matches} (expected: 57)")
        print(f"Competition tables: {comps} (expected: 6)")
        print(f"Match reports: {reports} (expected: 57)")
        print(f"Total files: {total}")
        if total > 150:
            print("✅ SUCCESSFUL - Full data extraction complete")
        else:
            print("⚠️ PARTIAL - Some data may be missing")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract and organize FBref match data for any team and season."
    )
    parser.add_argument(
        "--squad-id",
        required=False,
        help="FBref squad id, e.g. 18bb7c10 (single-team mode)",
    )
    parser.add_argument(
        "--season",
        required=True,
        help="FBref season segment, e.g. 2023-2024",
    )
    parser.add_argument(
        "--team-slug",
        required=False,
        help="FBref team slug used in URLs, e.g. Arsenal or Manchester-City (single-team mode)",
    )
    parser.add_argument(
        "--team",
        action="append",
        default=[],
        help=(
            "Repeatable multi-team input in format '<squad_id>:<team_slug>' "
            "or '<squad_id>,<team_slug>'."
        ),
    )
    parser.add_argument(
        "--team-url",
        action="append",
        default=[],
        help=(
            "Repeatable FBref team Stats URL. The script extracts squad_id and team_slug "
            "from each URL."
        ),
    )
    parser.add_argument(
        "--output-dir",
        default="Data",
        help="Output directory for generated tables (default: Data)",
    )
    parser.add_argument(
        "--shooting-url",
        default=None,
        help="Optional direct FBref shooting matchlogs URL to extract shot metrics.",
    )
    parser.add_argument(
        "--roster-url",
        default=None,
        help="Optional direct FBref roster URL to extract player roster details.",
    )
    parser.add_argument(
        "--scrape-do-token",
        default=None,
        help="Optional scrape.do API token for bypassing anti-bot protection (https://www.scrape.do)",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run Chrome in headless mode.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    teams: List[tuple[str, str]] = []

    # Multi-team mode from --team entries
    for team_spec in args.team:
        teams.append(parse_team_spec(team_spec))

    # Multi-team mode from --team-url entries
    for team_url in args.team_url:
        squad_id, season_from_url, team_slug = parse_team_from_stats_url(team_url)
        if season_from_url != args.season:
            raise ValueError(
                f"Season mismatch for URL '{team_url}'. "
                f"URL season is '{season_from_url}' but --season is '{args.season}'."
            )
        teams.append((squad_id, team_slug))

    # Single-team mode fallback
    if not teams:
        if not args.squad_id or not args.team_slug:
            raise ValueError(
                "Provide either single-team args (--squad-id and --team-slug), "
                "or multi-team args (--team and/or --team-url)."
            )
        teams.append((args.squad_id, args.team_slug))

    # De-duplicate while preserving order
    seen = set()
    unique_teams: List[tuple[str, str]] = []
    for squad_id, team_slug in teams:
        key = (squad_id, team_slug)
        if key not in seen:
            seen.add(key)
            unique_teams.append(key)

    for squad_id, team_slug in unique_teams:
        print(f"\n=== Running pipeline for {team_slug} ({squad_id}) - {args.season} ===")
        pipeline = FbrefPipeline(
            squad_id=squad_id,
            season=args.season,
            team_slug=team_slug,
            output_dir=Path(args.output_dir),
            headless=args.headless,
            shooting_url=args.shooting_url,
            roster_url=args.roster_url,
            scrape_do_token=args.scrape_do_token,
        )
        pipeline.run()


if __name__ == "__main__":
    main()
