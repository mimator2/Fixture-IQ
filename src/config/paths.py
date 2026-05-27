from pathlib import Path


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def src_dir() -> Path:
    return project_root() / 'src'


def data_dir() -> Path:
    return project_root() / 'data'


def season_dir(season: str) -> Path:
    return data_dir() / season


def model_dir() -> Path:
    return project_root() / 'models'


def results_dir() -> Path:
    return project_root() / 'results'


def cache_dir() -> Path:
    return data_dir() / 'cache'


def get_dynamic_path(season: str) -> Path:
    return season_dir(season) / 'sofascore_dynamic'


def get_fbref_path(season: str, team: str = None) -> Path:
    base = season_dir(season) / 'fbref'
    return base / team if team else base


def get_sofascore_path(season: str, competition: str = None) -> Path:
    base = season_dir(season) / 'sofascore'
    return base / competition if competition else base


def get_injuries_path(season: str) -> Path:
    return season_dir(season) / 'injuries'


def get_raw_pl_centric_path(season: str) -> Path:
    return season_dir(season) / 'sofascore_raw_pl_centric'


def notebooks_dir() -> Path:
    return project_root() / 'notebooks'


def scripts_dir() -> Path:
    return project_root() / 'scripts'


def docs_dir() -> Path:
    return project_root() / 'docs'


def get_elo_path() -> Path:
    return data_dir() / 'clubelo_understat' / 'fixtureiq_elo_master.csv'


def get_understat_path() -> Path:
    return data_dir() / 'clubelo_understat' / 'fixtureiq_understat_master.csv'


from dotenv import load_dotenv
load_dotenv(project_root() / '.env')
