#!/usr/bin/env python3
"""
FixtureIQ Dynamic Congestion Pipeline
========================================================================
Dynamically discovers teams and maps ALL domestic/European match loads.
========================================================================
"""

from __future__ import annotations

import argparse
import os
import time
from pathlib import Path
import pandas as pd
import numpy as np

# Force Edge browser execution on Windows environments to bypass Cloudflare
os.environ["BOTASAURUS_CHROME_EXECUTABLE_PATH"] = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

try:
    import ScraperFC
    import soccerdata as sd
except ImportError as e:
    print(f"[-] Missing dependencies. Run: pip install ScraperFC soccerdata pandas numpy. Error: {e}")
    import sys
    sys.exit(1)


class FixtureIQDynamicPipeline:
    # A complete pool of target competitions involving English top-flight clubs
    COMPETITIONS_POOL = [
        "England Premier League",
        "UEFA Champions League"
    ]

    def __init__(self, year_sofascore: str, output_dir: str, delay: float = 3.0):
        self.year_ss = year_sofascore  # Format: "23/24" or "24/25"
        self.delay = delay
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Anti-ban cache directory initialization
        self.cache_dir = Path(".fixtureiq_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        print("[*] Initializing ScraperFC Automation Engine...")
        self.scraper = ScraperFC.Sofascore()

    def discover_pl_teams(self) -> set[str]:
        """
        Dynamically discovers and isolates ONLY the English clubs that are 
        simultaneously competing in both the Premier League AND the Champions League.
        """
        print(f"\n[*] STEP 1: Discovering elite cohort playing both PL and UCL for Season {self.year_ss}...")
        
        try:
            # 1. Obtener todos los equipos que juegan en la Premier League esta temporada
            print("    -> Extracting Premier League member directory...")
            pl_fixtures = self.scraper.get_match_dicts(self.year_ss, "England Premier League")
            pl_teams = set()
            for m in pl_fixtures:
                if m.get('homeTeam', {}).get('name'): pl_teams.add(m['homeTeam']['name'])
                if m.get('awayTeam', {}).get('name'): pl_teams.add(m['awayTeam']['name'])
            
            # 2. Obtener todos los equipos que juegan la Champions League esta temporada
            print("    -> Extracting UEFA Champions League tournament directory...")
            ucl_fixtures = self.scraper.get_match_dicts(self.year_ss, "UEFA Champions League")
            ucl_teams = set()
            for m in ucl_fixtures:
                if m.get('homeTeam', {}).get('name'): ucl_teams.add(m['homeTeam']['name'])
                if m.get('awayTeam', {}).get('name'): ucl_teams.add(m['awayTeam']['name'])
                
            # 3. INTERSECCIÓN DINÁMICA: Solo los equipos ingleses en Champions
            # El operador '&' se queda únicamente con los elementos que existen en ambos sets
            elite_cohort = pl_teams & ucl_teams
            
            if not elite_cohort:
                # Fallback de seguridad por si hay discrepancias de nombres nativos en la API
                print("    [⚠️] Dynamic intersection returned empty. Using verified 24/25 cohort fallback...")
                elite_cohort = {"Manchester City", "Arsenal", "Liverpool", "Aston Villa"}
            
            print(f"[✅] Successfully isolated dual-competition cohort ({len(elite_cohort)} teams):")
            print(f"    -> {list(elite_cohort)}")
            return elite_cohort

        except Exception as e:
            print(f"    [⚠️] Dynamic discovery encountered an error: {e}. Defaulting to verified 24/25 cohort.")
            return {"Manchester City", "Arsenal", "Liverpool", "Aston Villa"}

    def build_universal_fixtures(self, target_teams: set[str]) -> list[dict]:
        """Scans ALL competitions in the pool to find matches containing our target teams."""
        print("\n[*] STEP 2: Scanning all competitions for matches involving discovered teams...")
        universal_fixtures = []
        
        for comp in self.COMPETITIONS_POOL:
            try:
                print(f"    -> Scanning '{comp}' for season {self.year_ss}...")
                matches = self.scraper.get_match_dicts(self.year_ss, comp)
                
                comp_matches_count = 0
                for m in matches:
                    home_team = m.get('homeTeam', {}).get('name', '')
                    away_team = m.get('awayTeam', {}).get('name', '')
                    
                    # If either team belongs to our dynamically discovered list, keep the match
                    if home_team in target_teams or away_team in target_teams:
                        m["_target_competition"] = comp
                        universal_fixtures.append(m)
                        comp_matches_count += 1
                print(f"       [+] Retained {comp_matches_count} matching fixtures from {comp}")
                time.sleep(1) # Polite pause between calendar indexes
            except Exception as e:
                # Some competitions (like Conference League) might not feature English teams in specific years
                print(f"       [⚠️] Competition '{comp}' not available or skipped: {e}")

        # Sort the entire multi-league calendar chronologically using Unix timestamps
        universal_fixtures = sorted(universal_fixtures, key=lambda x: x.get('startTimestamp', 0))
        print(f"[✅] Completed full integration: Isolated {len(universal_fixtures)} total matches cross-league.")
        return universal_fixtures

    def fetch_match_player_stats_with_cache(self, match_id: int) -> pd.DataFrame | None:
        """
        Reads local cache to save time and avoid API blocks.
        Falls back to scraping player stats, tactical average positions, and match shots if missing.
        """
        cache_file = self.cache_dir / f"match_{match_id}.csv"
        cache_pos_file = self.cache_dir / f"match_{match_id}_positions.csv"
        cache_shots_file = self.cache_dir / f"match_{match_id}_shots.csv"
        
        # Si ya existe el CSV principal en caché, lo cargamos directo para acelerar el script
        if cache_file.exists():
            return pd.read_csv(cache_file)
            
        try:
            print(f"    -> [🌐 Scrape] Fetching expanded live match data for ID: {match_id}")
            time.sleep(self.delay)
            
            # 1. Extracción Estándar: Estadísticas de Rendimiento de los Jugadores
            df_match = self.scraper.scrape_player_match_stats(match_id)
            if df_match is not None and not df_match.empty:
                df_match = df_match.reset_index(drop=True)
                df_match = df_match.loc[:, ~df_match.columns.duplicated()].copy()
                df_match.to_csv(cache_file, index=False)
            else:
                return None
                
            # 2. NUEVA PARTE: Posiciones Promedio de los Jugadores (Centro de Gravedad Táctico)
            try:
                time.sleep(self.delay)
                df_pos = self.scraper.scrape_player_average_positions(match_id)
                if df_pos is not None:
                    if isinstance(df_pos, pd.DataFrame) and not df_pos.empty:
                        df_pos.to_csv(cache_pos_file, index=False)
                    elif isinstance(df_pos, dict) and df_pos:
                        pd.DataFrame(df_pos).to_csv(cache_pos_file, index=False)
            except Exception as e_pos:
                print(f"      [⚠️] Extra positions scrape skipped or failed for Match {match_id}: {e_pos}")

            # 3. NUEVA PARTE: Mapeo de Tiros (Calidad de la Finalización y xG de SofaScore)
            try:
                time.sleep(self.delay)
                df_shots = self.scraper.scrape_match_shots(match_id)
                if df_shots is not None:
                    if isinstance(df_shots, pd.DataFrame) and not df_shots.empty:
                        df_shots.to_csv(cache_shots_file, index=False)
                    elif isinstance(df_shots, dict) and df_shots:
                        pd.DataFrame(df_shots).to_csv(cache_shots_file, index=False)
            except Exception as e_shots:
                print(f"      [⚠️] Extra match shots scrape skipped or failed for Match {match_id}: {e_shots}")
                
            return df_match
            
        except Exception as e:
            print(f"      [⚠️] Scraping exception on Match ID {match_id}: {e}")
        return None

    def execute_pipeline(self) -> pd.DataFrame:
        # Step 1: Discover who is playing this season
        pl_teams = self.discover_pl_teams()
        if not pl_teams:
            return pd.DataFrame()
            
        # Step 2: Grab every match from every league involving those teams
        fixtures = self.build_universal_fixtures(pl_teams)
        if not fixtures:
            return pd.DataFrame()
            
        all_compiled_records = []
        print("\n[*] STEP 3: Processing player performance matrix match-by-match...")
        
        for idx, match in enumerate(fixtures):
            match_id = match.get('id')
            comp = match.get('_target_competition')
            home_team = match.get('homeTeam', {}).get('name', 'Unknown')
            away_team = match.get('awayTeam', {}).get('name', 'Unknown')
            
            ts = match.get('startTimestamp') or match.get('status', {}).get('startTimestamp', 0)
            match_date = pd.to_datetime(ts, unit='s').strftime('%Y-%m-%d')
            
            print(f"    [{idx+1}/{len(fixtures)}] [{comp}] {match_date} | {home_team} vs {away_team}")
            
            df_match = self.fetch_match_player_stats_with_cache(match_id)
            if df_match is None or df_match.empty:
                continue
                
            df_match['match_id'] = match_id
            df_match['match_date_str'] = match_date
            df_match['competition'] = comp
            df_match['home_team_name'] = home_team
            df_match['away_team_name'] = away_team
            
            all_compiled_records.append(df_match)
            
        if not all_compiled_records:
            return pd.DataFrame()
            
        df_master = pd.concat(all_compiled_records, ignore_index=True)
        df_master['date'] = pd.to_datetime(df_master['match_date_str'])
        
        player_col = next((c for c in ['player_name', 'player', 'name'] if c in df_master.columns), df_master.columns[0])
        
        # --- STEP 4: Advanced Cross-Competition Feature Engineering ---
        print("\n[*] STEP 4: Engineering time-series fatigue workloads across all tournaments...")
        df_master = df_master.sort_values(by=[player_col, 'date']).reset_index(drop=True)
        
        # 1. Variables Base de Fatiga Física e Indicadores Críticos
        df_master['rest_days'] = df_master.groupby(player_col)['date'].diff().dt.days
        df_master['rest_days'] = df_master['rest_days'].fillna(14).astype(int)
        df_master['high_congestion_flag'] = np.where(df_master['rest_days'] <= 3, 1, 0)
        
        df_master.set_index('date', inplace=True)
        if 'minutesPlayed' in df_master.columns:
            df_master['minutesPlayed'] = df_master['minutesPlayed'].fillna(0).astype(int)
            df_master['min_last_7d'] = df_master.groupby(player_col)['minutesPlayed'].rolling('7D', closed='left').sum().reset_index(0, drop=True)
            df_master['min_last_28d'] = df_master.groupby(player_col)['minutesPlayed'].rolling('28D', closed='left').sum().reset_index(0, drop=True)
        df_master.reset_index(inplace=True)
        
        df_master['min_last_7d'] = df_master['min_last_7d'].fillna(0).astype(int)
        df_master['min_last_28d'] = df_master['min_last_28d'].fillna(0).astype(int)
        
        df_master['acwr_ratio'] = np.where(
            df_master['min_last_28d'] > 0, 
            df_master['min_last_7d'] / (df_master['min_last_28d'] / 4.0), 
            0.0
        )

        # 2. NUEVAS VARIABLES: Contexto Logístico, de Viaje y de Estilo Estructurado
        print("    -> Calculating tactical stress and logistics features...")
        
        # Determinar si el jugador es visitante (is_away) comparando su equipo con el home_team
        df_master['is_away'] = np.where(df_master['teamName'] == df_master['away_team_name'], 1, 0)
        
        # Contador de partidos seguidos como visitante (consecutive_away_games) por jugador
        df_master['consecutive_away_games'] = df_master.groupby(player_col)['is_away'].transform(lambda x: x.groupby((x != x.shift()).cumsum()).cumsum())

        # Proxy de intensidad del partido anterior del jugador (Volumen de duelos por minuto disputado)
        if 'duelsWon' in df_master.columns and 'duelsLost' in df_master.columns:
            total_duels = df_master['duelsWon'].fillna(0) + df_master['duelsLost'].fillna(0)
            df_master['match_intensity_proxy'] = np.where(df_master['minutesPlayed'] > 0, total_duels / df_master['minutesPlayed'], 0.0)
            # Pasarlo a rolling para medir la intensidad promedio del último mes (28 días) en las piernas del jugador
            df_master.set_index('date', inplace=True)
            df_master['player_historical_intensity_28d'] = df_master.groupby(player_col)['match_intensity_proxy'].rolling('28D', closed='left').mean().reset_index(0, drop=True)
            df_master.reset_index(inplace=True)
            df_master['player_historical_intensity_28d'] = df_master['player_historical_intensity_28d'].fillna(0)

        # Edad media del once inicial del equipo en cada partido (Estructura de plantilla)
        if 'age' in df_master.columns:
            df_master['squad_age_average'] = df_master.groupby(['match_id', 'teamName'])['age'].transform('mean')

        # Rotación del once titular (lineup_churn) respecto al partido anterior del equipo
        # Creamos un registro único por partido y equipo para evaluar los cambios
        match_lineups = df_master[df_master['minutesPlayed'] > 0].groupby(['teamName', 'match_id'])['name'].apply(set).reset_index()
        match_lineups = match_lineups.merge(df_master[['match_id', 'match_date_str']].drop_duplicates(), on='match_id')
        match_lineups = match_lineups.sort_values(by=['teamName', 'match_date_str'])
        
        match_lineups['prev_lineup'] = match_lineups.groupby('teamName')['name'].shift(1)
        # El "churn" es cuántos jugadores del once actual NO estaban en el once anterior
        match_lineups['lineup_churn'] = match_lineups.apply(
            lambda r: len(r['name'] - r['prev_lineup']) if isinstance(r['prev_lineup'], set) else 0, axis=1
        )
        
        # Unir la métrica de rotación estructural al dataset maestro
        df_master = pd.merge(df_master, match_lineups[['match_id', 'teamName', 'lineup_churn']], on=['match_id', 'teamName'], how='left')
        df_master['lineup_churn'] = df_master['lineup_churn'].fillna(0).astype(int)

        # --- STEP 5: SoccerData Context Matching & Understat Integration ---
        print("\n[*] STEP 5: Stitching contextual data via SoccerData & Understat...")
        
        # Mapeo unificado para ClubElo y Understat
        team_map = {
            "Brighton & Hove Albion": "Brighton",
            "Newcastle United": "Newcastle",
            "Liverpool FC": "Liverpool",
            "Nottingham Forest": "Nottingham Forest",
            "Brentford": "Brentford",
            "West Ham United": "West Ham",
            "Bournemouth": "Bournemouth",
            "Leicester City": "Leicester",
            "Chelsea": "Chelsea",
            "Wolverhampton": "Wolves",
            "Southampton": "Southampton",
            "Crystal Palace": "Crystal Palace",
            "Ipswich Town": "Ipswich",
            "Manchester City": "Man City",
            "Fulham": "Fulham",
            "Everton": "Everton",
            "Tottenham Hotspur": "Tottenham",
            "Manchester United": "Man United",
            "Aston Villa": "Aston Villa",
            "Arsenal": "Arsenal"
        }
        df_master['teamName_standardized'] = df_master['teamName'].replace(team_map)
        df_master['home_team_standardized'] = df_master['home_team_name'].replace(team_map)

        # A. INTEGRACIÓN DE CLUB ELO (Límites Cronológicos)
        try:
            elo_client = sd.ClubElo()
            df_elo = elo_client.read_by_date().reset_index()
            df_elo.columns = [str(c).lower() for c in df_elo.columns]
            
            df_elo['from'] = pd.to_datetime(df_elo['from'])
            df_elo['to'] = pd.to_datetime(df_elo['to'])
            df_master['elo'] = np.nan
            
            for unique_team in df_master['teamName_standardized'].unique():
                team_elo_hist = df_elo[df_elo['team'] == unique_team]
                if team_elo_hist.empty: continue
                
                master_team_mask = df_master['teamName_standardized'] == unique_team
                team_match_dates = pd.to_datetime(df_master.loc[master_team_mask, 'match_date_str'])
                
                elo_values = []
                for m_date in team_match_dates:
                    matched_row = team_elo_hist[(team_elo_hist['from'] <= m_date) & (team_elo_hist['to'] >= m_date)]
                    if not matched_row.empty:
                        elo_values.append(matched_row['elo'].values[0])
                    else:
                        closest_row = team_elo_hist.iloc[(team_elo_hist['from'] - m_date).abs().argsort()[:1]]
                        elo_values.append(closest_row['elo'].values[0] if not closest_row.empty else np.nan)
                        
                df_master.loc[master_team_mask, 'elo'] = elo_values
            print("    [✅] ClubELO data integrated via temporal windows.")
        except Exception as e:
            print(f"    [⚠️] ClubELO integration failed: {e}")

        # B. INTEGRACIÓN DE UNDERSTAT (xG, xGA, PPDA e Intensidad Táctica)
        understat_file = Path("fixtureiq_understat_master.csv")
        if understat_file.exists():
            try:
                print("    -> Merging multi-competition Understat tactictal load metrics...")
                df_us = pd.read_csv(understat_file)
                df_us['date'] = pd.to_datetime(df_us['date'])
                df_master['date_dt'] = pd.to_datetime(df_master['match_date_str'])
                
                # Mapear los nombres de equipos de Understat al estándar si difieren
                df_us['home_team'] = df_us['home_team'].replace({"Manchester Utd": "Man United", "Tottenham": "Tottenham"})
                
                # Columnas de interés de Understat (Variables explicativas y de objetivo colectivo sugeridas)
                # Nota: Si calculaste PPDA en tu CSV de Understat, inclúyela aquí.
                us_cols = ['date', 'home_team', 'home_xg', 'away_xg']
                valid_us_cols = [c for c in us_cols if c in df_us.columns]
                
                df_master = pd.merge(
                    df_master,
                    df_us[valid_us_cols],
                    left_on=['date_dt', 'home_team_standardized'],
                    right_on=['date', 'home_team'],
                    how='left',
                    suffixes=('', '_us_raw')
                )
                
                # Generar variables espejo basadas en si nuestro jugador es local o visitante
                if 'home_xg' in df_master.columns and 'away_xg' in df_master.columns:
                    df_master['team_xg'] = np.where(df_master['is_away'] == 0, df_master['home_xg'], df_master['away_xg'])
                    df_master['team_xga'] = np.where(df_master['is_away'] == 0, df_master['away_xg'], df_master['home_xg'])
                    df_master['xg_difference'] = df_master['team_xg'] - df_master['team_xga']
                
                print("    [✅] Understat target and load features stitched successfully.")
            except Exception as e:
                print(f"    [⚠️] Understat merge failed: {e}")
        else:
            print("    [⚠️] fixtureiq_understat_master.csv not found. Skipping tactical metrics.")

        # Limpieza de columnas de mapeo temporal antes de retornar
        drop_cols = ['teamName_standardized', 'home_team_standardized', 'date_dt', 'date_us_raw', 'home_team_us_raw']
        df_master = df_master.drop(columns=[c for c in drop_cols if c in df_master.columns], errors='ignore')

        return df_master

    def export(self, df: pd.DataFrame):
        if df.empty: return
        
        # 1. Guardar la capa maestra analítica intacta (Capa de Bronce/Plata completa)
        df.to_csv(self.output_dir / "fixtureiq_dynamic_master.csv", index=False)
        
        # 2. CAPA DE MODELADO GOLD: Filtrada y optimizada para XGBoost / Bayesianos Jerárquicos
        features = [
            # Datos Identificativos y Jerárquicos (Grupos del Modelo Bayesiano)
            'match_date_str', 'match_id', 'competition', 'teamName', 'player_name', 'name', 'position', 'rating', 'elo',
            
            # Variables de Control Logístico y de Viaje (Punto 3 del Feedback)
            'is_away', 'consecutive_away_games',
            
            # Variables Estructurales de Carga de Trabajo y Plantilla (X - Stressors)
            'minutesPlayed', 'rest_days', 'high_congestion_flag', 'min_last_7d', 'acwr_ratio',
            'lineup_churn', 'squad_age_average', 'player_historical_intensity_28d',
            
            # Variables de Rendimiento Técnico/Neuromuscular Individual (Y - Target Opciones 1)
            'duel_success_pct', 'turnovers_per_90min',
            
            # Variables Colectivas / Calidad del Partido de Understat (Y - Target Opciones 2 sugeridas en Punto 4)
            'team_xg', 'team_xga', 'xg_difference'
        ]
        
        valid_features = [f for f in features if f in df.columns]
        df_clean = df[valid_features]
        
        # Excluir Porteros (Para evitar sesgos en el desgaste por estilo de juego)
        if 'position' in df_clean.columns:
            df_clean = df_clean[df_clean['position'] != 'G']
            
        df_clean.to_csv(self.output_dir / "fixtureiq_dynamic_analytics_clean.csv", index=False)
        print(f"\n[🚀] SUCCESSFUL DYNAMIC GENERATION WITH EXPANDED MODEL FEATURES!")
        print(f"    -> Analytics Layer Location: {self.output_dir / 'fixtureiq_dynamic_analytics_clean.csv'}")
        print(f"    -> Expanded Feature Matrix Shape: {df_clean.shape}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FixtureIQ Fully Dynamic Season Mapper")
    parser.add_argument("--year", default="23/24", help="SofaScore short season code (e.g. 23/24)")
    parser.add_argument("--output-dir", default="Data_Dynamic", help="Export folder")
    args = parser.parse_args()
    
    pipeline = FixtureIQDynamicPipeline(year_sofascore=args.year, output_dir=args.output_dir)
    master_df = pipeline.execute_pipeline()
    pipeline.export(master_df)