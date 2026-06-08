import numpy as np
import pandas as pd
from fatigue_monitor.src.feature_engineering import engineer_features, _add_player_key


def _add_missingness_indicators(df):
    cols = [
        "rest_days", "squad_injured_count", "squad_soft_tissue_count",
        "squad_avg_days_out", "days_since_last_injury", "fixtures_missed_last_30d",
        "fixtures_missed_last_90d", "returning_from_injury", "acwr_ratio",
        "min_last_7d", "days_since_european_match",
    ]
    for c in cols:
        if c in df.columns:
            df[f"{c}_missing"] = df[c].isna().astype(int)
        else:
            df[f"{c}_missing"] = 1
    return df


def _add_competition_flags(df):
    comp = df["competition"].astype(str).str.lower()
    df["is_champions_league"] = comp.str.contains("champions|uefa", regex=True, na=False).astype(int)
    df["is_european_fixture"] = comp.str.contains("europa|conference|champions|uefa", regex=True, na=False).astype(int)
    df["is_domestic_cup"] = comp.str.contains(
        "fa cup|league cup|efl cup|carabao|community shield", regex=True, na=False
    ).astype(int)
    df["is_league"] = (
        (~df["is_champions_league"].astype(bool))
        & (~df["is_european_fixture"].astype(bool))
        & (~df["is_domestic_cup"].astype(bool))
    ).astype(int)
    return df


def _add_v6_rolling_features(df):
    df_fe = df.copy()
    df_fe.sort_values(["player_key", "date"], inplace=True)

    idx_arr = df_fe.index.values
    pk_arr = df_fe["player_key"].values
    dates = df_fe["date"].values.astype("datetime64[ns]")
    mins = df_fe["minutes_played"].fillna(0).values.astype(np.float64)
    sub = df_fe["is_substitute"].fillna(0).values.astype(bool)
    rating = df_fe.get("rating", pd.Series(np.nan, index=df_fe.index)).fillna(np.nan).values.astype(np.float64)

    action_cols = [
        ("shots_total", "shots_last_5"),
        ("passes_key", "key_passes_last_5"),
        ("tackles_total", "tackles_last_5"),
        ("tackles_interceptions", "interceptions_last_5"),
        ("dribbles_attempts", "dribbles_attempts_last_5"),
        ("duels_total", "duels_total_last_5"),
        ("fouls_committed", "fouls_committed_last_5"),
    ]
    action_vals = {}
    for src, _ in action_cols:
        if src in df_fe.columns:
            action_vals[src] = df_fe[src].fillna(0).values.astype(np.float64)
        else:
            action_vals[src] = np.zeros(len(df_fe), dtype=np.float64)

    n = len(df_fe)
    out = {}
    out["starts_last_5"] = np.zeros(n, dtype=np.float64)
    out["appearances_last_5"] = np.zeros(n, dtype=np.float64)
    out["starts_last_10_matches"] = np.zeros(n, dtype=np.float64)
    out["appearances_last_10_matches"] = np.zeros(n, dtype=np.float64)
    out["minutes_last_3_matches"] = np.zeros(n, dtype=np.float64)
    out["minutes_last_5_matches"] = np.zeros(n, dtype=np.float64)
    out["avg_minutes_last_5"] = np.zeros(n, dtype=np.float64)
    out["avg_minutes_last_10"] = np.zeros(n, dtype=np.float64)
    out["managed_minutes_last_5"] = np.zeros(n, dtype=np.float64)
    out["full_match_exposure_last_5"] = np.zeros(n, dtype=np.float64)
    out["avg_rating_last_3"] = np.full(n, np.nan)
    out["avg_rating_last_5"] = np.full(n, np.nan)
    for _, dst in action_cols:
        out[dst] = np.zeros(n, dtype=np.float64)

    start = 0
    for _end in range(1, n + 1):
        if _end < n and pk_arr[_end] == pk_arr[start]:
            continue
        grp = slice(start, _end)
        g_len = _end - start
        g_mins = mins[grp]
        g_sub = sub[grp]
        g_rating = rating[grp]

        g_action = {}
        for src, _ in action_cols:
            g_action[src] = action_vals[src][grp]

        for i in range(1, g_len):
            idx_global = idx_arr[start + i]
            p5 = max(0, i - 5)
            p10 = max(0, i - 10)
            p3 = max(0, i - 3)

            past5_mins = g_mins[p5:i]
            past10_mins = g_mins[p10:i]
            past5_sub = g_sub[p5:i]
            past5_mins_bool = past5_mins > 0

            out["starts_last_5"][idx_global] = float((~past5_sub).sum())
            out["appearances_last_5"][idx_global] = float(past5_mins_bool.sum())
            out["starts_last_10_matches"][idx_global] = float((~g_sub[p10:i]).sum())
            out["appearances_last_10_matches"][idx_global] = float((g_mins[p10:i] > 0).sum())
            out["minutes_last_3_matches"][idx_global] = float(g_mins[p3:i].sum())
            out["minutes_last_5_matches"][idx_global] = float(past5_mins.sum())

            if past5_mins_bool.sum() > 0:
                out["avg_minutes_last_5"][idx_global] = float(past5_mins[past5_mins_bool].mean())
            if (g_mins[p10:i] > 0).sum() > 0:
                out["avg_minutes_last_10"][idx_global] = float(g_mins[p10:i][g_mins[p10:i] > 0].mean())

            out["managed_minutes_last_5"][idx_global] = float(((past5_mins > 0) & (past5_mins < 60)).sum())
            out["full_match_exposure_last_5"][idx_global] = float((past5_mins >= 85).sum())

            if i >= 3:
                r3 = g_rating[max(0, i - 3):i]
                if np.isnan(r3).sum() < len(r3):
                    out["avg_rating_last_3"][idx_global] = float(np.nanmean(r3))
            if i >= 5:
                r5 = g_rating[p5:i]
                if np.isnan(r5).sum() < len(r5):
                    out["avg_rating_last_5"][idx_global] = float(np.nanmean(r5))

            for src, dst in action_cols:
                out[dst][idx_global] = float(g_action[src][p5:i].sum())

        start = _end

    out_df = pd.DataFrame(out, index=df_fe.index)
    return out_df


def _add_v6_composite_scores(df):
    app5 = df["appearances_last_5"].clip(lower=1)
    df["all_comp_minutes_pressure"] = df["minutes_last_5_matches"] / (app5 * 90.0)
    df["all_comp_minutes_pressure"] = df["all_comp_minutes_pressure"].clip(0, 2)

    action_sum_cols = [
        "shots_last_5", "key_passes_last_5", "tackles_last_5",
        "interceptions_last_5", "dribbles_attempts_last_5",
        "duels_total_last_5", "fouls_committed_last_5",
    ]
    df["recent_action_load_score"] = df[action_sum_cols].sum(axis=1)

    min5 = df["minutes_last_5_matches"].replace(0, np.nan)
    df["recent_action_load_per90"] = df["recent_action_load_score"] / min5 * 90.0
    df["recent_action_load_per90"] = df["recent_action_load_per90"].fillna(0)

    df["high_recent_action_load_by_position"] = 0
    return df


def _add_position_z_scores(df):
    pos_features = [
        "minutes_last_5_matches", "minutes_last_3_matches", "min_last_7d",
        "all_comp_minutes_pressure", "recent_action_load_per90",
        "recent_action_load_score",
        "shots_last_5", "key_passes_last_5", "tackles_last_5",
        "interceptions_last_5", "dribbles_attempts_last_5",
        "duels_total_last_5",
    ]
    out_names = [f + "_pos_z" for f in pos_features]

    for feat, out_name in zip(pos_features, out_names):
        if feat not in df.columns:
            df[out_name] = 0.0
            continue
        means = df.groupby("player_position")[feat].transform("mean")
        stds = df.groupby("player_position")[feat].transform("std").replace(0, 1.0)
        df[out_name] = ((df[feat] - means) / stds).fillna(0)

    if "high_recent_action_load_by_position" in df.columns:
        df["high_recent_action_load_by_position"] = (
            df["recent_action_load_per90_pos_z"] > 1.0
        ).astype(int)
    return df


def _add_injury_context_flags(df):
    df["recent_injury_return_flag"] = (
        (df["days_since_last_injury"].fillna(999) <= 14)
        & (df["days_since_last_injury"].fillna(999) > 0)
    ).astype(int)

    df["medium_recent_injury_return_flag"] = (
        (df["days_since_last_injury"].fillna(999) > 14)
        & (df["days_since_last_injury"].fillna(999) <= 30)
    ).astype(int)

    df["long_recent_injury_history_flag"] = (
        df["fixtures_missed_last_90d"].fillna(0) >= 5
    ).astype(int)

    df["missed_recent_fixture_flag"] = (
        df["fixtures_missed_last_30d"].fillna(0) >= 1
    ).astype(int)

    df["missed_multiple_recent_fixtures_flag"] = (
        df["fixtures_missed_last_30d"].fillna(0) >= 2
    ).astype(int)

    df["missed_fixtures_90d_pressure"] = (
        df["fixtures_missed_last_90d"].fillna(0) >= 3
    ).astype(int)

    df["high_squad_injury_pressure"] = (
        df["squad_injured_count"].fillna(0) >= 4
    ).astype(int)

    df["high_soft_tissue_pressure"] = (
        df["squad_soft_tissue_count"].fillna(0) >= 2
    ).astype(int)

    df["long_squad_absence_pressure"] = (
        df["squad_avg_days_out"].fillna(0) >= 60
    ).astype(int)

    df["squad_injury_high_workload"] = (
        (df["squad_injured_count"].fillna(0) >= 3)
        & (df["squad_avg_days_out"].fillna(0) >= 30)
    ).astype(int)

    df["soft_tissue_pressure_high_load"] = (
        (df["squad_soft_tissue_count"].fillna(0) >= 2)
        & (df["squad_avg_days_out"].fillna(0) >= 20)
    ).astype(int)

    injury_flag_cols = [
        "recent_injury_return_flag", "medium_recent_injury_return_flag",
        "long_recent_injury_history_flag", "missed_recent_fixture_flag",
        "missed_multiple_recent_fixtures_flag", "missed_fixtures_90d_pressure",
        "high_squad_injury_pressure", "high_soft_tissue_pressure",
        "long_squad_absence_pressure", "squad_injury_high_workload",
        "soft_tissue_pressure_high_load",
    ]
    df["injury_context_score"] = df[injury_flag_cols].sum(axis=1)

    return df


def assign_player_role_v6(df):
    core = (
        (df["starts_last_5"].fillna(0) >= 3)
        & (df["avg_minutes_last_5"].fillna(0) >= 70)
    )
    return np.where(core, "core_starter", "rotation_player")


def engineer_features_v6(df):
    df = engineer_features(df)
    df = _add_player_key(df)

    df["start_flag"] = (~df["is_substitute"].astype(bool)).astype(int)

    df = _add_missingness_indicators(df)
    df = _add_competition_flags(df)

    roll_df = _add_v6_rolling_features(df)
    for c in roll_df.columns:
        df[c] = roll_df[c].values

    df = _add_v6_composite_scores(df)
    df = _add_position_z_scores(df)
    df = _add_injury_context_flags(df)

    df["player_role_v6"] = assign_player_role_v6(df)

    return df
