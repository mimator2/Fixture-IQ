"""
FixtureIQ - Target Variable Definition
=======================================
Defines both the composite fatigue_risk proxy target and
the ground-truth injury_flag target from injury records.
"""

import pandas as pd
import numpy as np
from pathlib import Path


GENUINE_INJURY_REASONS = {
    "Abdominal strain", "Achilles Tendon Injury", "Ankle Injury", "Arm Injury",
    "Back Injury", "Broken Leg", "Calf Injury", "Concussion", "Eye injury",
    "Face Injury", "Finger Injury", "Foot Injury", "Groin Injury",
    "Hamstring Injury", "Hand Injury", "Head Injury", "Heel Injury",
    "Hip Injury", "Illness", "Injury", "Knee Injury", "Knock",
    "Leg Injury", "Lower Back Injury", "Muscle Injury", "Pelvis Injury",
    "Shoulder Injury", "Thigh Injury", "Toe Injury", "Wrist Injury",
}

NON_INJURY_REASONS = {
    "Inactive", "Suspended", "Red Card", "Yellow Cards",
    "Coach's decision", "Loan agreement", "Personal Reasons",
    "Rest", "Health problems", "Convalescence", "Lacking Match Fitness",
}


def load_injury_data(data_root: Path) -> pd.DataFrame:
    rows = []
    for season_dir in ["2022-2023", "2023-2024", "2024-2025"]:
        path = data_root / season_dir / "injuries"
        if not path.exists():
            continue
        for f in sorted(path.iterdir()):
            if f.name.endswith("_injuries_days_out.csv"):
                df = pd.read_csv(f)
                rows.append(df)
    if not rows:
        return pd.DataFrame()
    inj = pd.concat(rows, ignore_index=True)
    inj["fixture_date"] = pd.to_datetime(inj["fixture_date"], errors="coerce")
    inj["last_name"] = inj["player_name"].str.split().str[-1].str.lower().str.strip()
    inj["is_injury"] = inj["reason"].isin(GENUINE_INJURY_REASONS)
    return inj


def merge_injury_target(df: pd.DataFrame, inj: pd.DataFrame, window_days: int = 14) -> pd.DataFrame:
    if inj.empty:
        df["injury_flag"] = 0
        return df

    df = df.copy()
    df["last_name"] = df["name"].str.split().str[-1].str.lower().str.strip()
    df["match_date"] = pd.to_datetime(df["match_date_str"])

    inj_clean = inj[inj["is_injury"]].copy()
    inj_clean = inj_clean.rename(columns={"team_name": "team_name_inj"})

    merged = df.merge(
        inj_clean,
        left_on=["last_name", "teamName"],
        right_on=["last_name", "team_name_inj"],
        how="left",
        suffixes=("", "_inj"),
    )
    merged["days_diff"] = (merged["fixture_date"] - merged["match_date"]).dt.days
    merged["injury_window"] = (merged["days_diff"] >= 0) & (merged["days_diff"] <= window_days)

    injury_hits = merged[merged["injury_window"]].groupby(["match_id", "name"]).size().reset_index(name="injury_count")
    injury_hits["injury_flag"] = (injury_hits["injury_count"] > 0).astype(int)

    df = df.merge(injury_hits[["match_id", "name", "injury_flag"]], on=["match_id", "name"], how="left")
    df["injury_flag"] = df["injury_flag"].fillna(0).astype(int)
    df.drop(columns=["last_name"], inplace=True, errors="ignore")
    return df


def define_target(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["signal_acwr"] = ((df["acwr_ratio"] > 1.5) | (df["acwr_ratio"] < 0.5)).astype(int)

    df["rating_drop"] = df["rating_rolling_avg_5"] - df["rating"]
    df["signal_decline"] = (df["rating_drop"] > 1.0).astype(int)

    if "high_congestion_flag" in df.columns:
        df["signal_congestion"] = df["high_congestion_flag"].fillna(0).astype(int)
    else:
        df["signal_congestion"] = (df["rest_days"] <= 3).fillna(0).astype(int)

    df["n_signals"] = df["signal_acwr"] + df["signal_decline"] + df["signal_congestion"]
    df["fatigue_risk"] = (df["n_signals"] >= 2).astype(int)
    return df
