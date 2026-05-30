import pandas as pd
import numpy as np

DF = None

def load_data():
    global DF
    if DF is not None:
        return DF
    df = pd.read_csv("XgBoost_model/Fixture_IQ_Data_Seasons_2022-2025.csv")
    df["date"] = pd.to_datetime(df["date"])
    df["month"] = df["date"].dt.month
    df["season_label"] = df["season"].astype(str)
    df["is_decline"] = df["api_rating_decline_flag"].astype(int)
    df["is_high_congestion"] = df["high_congestion_flag"].astype(int)
    df["is_win"] = (df["result"] == "Win").astype(int)
    df["is_loss"] = (df["result"] == "Loss").astype(int)
    df["is_draw"] = (df["result"] == "Draw").astype(int)
    position_map = {"G": "Goalkeeper", "D": "Defender", "M": "Midfielder", "F": "Forward"}
    df["position_group"] = df["player_position"].map(position_map).fillna("Other")
    df["rest_days"] = df["rest_days"].fillna(df["rest_days"].median())
    competition_colors = {
        "Premier League": "#636EFA", "Champions League": "#EF553B",
        "FA Cup": "#00CC96", "League Cup": "#AB63FA", "Community Shield": "#FFA15A"
    }
    df["comp_color"] = df["competition"].map(competition_colors).fillna("#636EFA")
    DF = df
    return df


def get_team_options(df):
    return sorted(df["player_team"].dropna().unique())


def get_player_options(df):
    return sorted(df["player_name"].dropna().unique())


def get_season_options(df):
    return sorted(df["season"].unique(), reverse=True)


def get_competition_options(df):
    return list(df["competition"].unique())


def filter_df(df, team=None, season=None, competition=None):
    d = df.copy()
    if team and team != "All":
        d = d[d["player_team"] == team]
    if season and season != "All":
        d = d[d["season"] == int(season)]
    if competition and competition != "All":
        d = d[d["competition"] == competition]
    return d


def kpi_card(title, value, suffix="", color="#00BC8C"):
    if suffix:
        display = f"{value}{suffix}"
    else:
        display = str(value)
    return {"title": title, "value": display, "color": color}
