import numpy as np
import pandas as pd
import warnings


def _add_player_key(df):
    if "player_key" not in df.columns:
        df["player_key"] = (
            df["player_name"].str.lower().str.strip()
            + "__"
            + df["player_team"].str.lower().str.strip()
        )
    return df


def _add_rest_days_features(df):
    df = _add_player_key(df)
    _s = df.sort_values(["player_key", "date"])
    _s["_prev_date"] = _s.groupby("player_key")["date"].shift(1)
    _s["rest_days"] = (
        (pd.to_datetime(_s["date"]) - pd.to_datetime(_s["_prev_date"]))
        .dt.days.fillna(14)
        .astype(float)
    )
    _s["high_congestion_flag"] = (_s["rest_days"] <= 3).astype(float)
    for c in ["rest_days", "high_congestion_flag"]:
        df[c] = _s[c]
    df.sort_index(inplace=True)
    return df


def _add_consecutive_away_games(df):
    df = _add_player_key(df)
    _s = df.sort_values(["player_key", "date"]).copy()
    if "is_away" not in _s.columns:
        _s["is_away"] = (~_s.get("is_home", pd.Series(False, index=_s.index))).astype(int)
    _s["_away_run"] = _s.groupby("player_key")["is_away"].diff().ne(0).cumsum()
    _s["consecutive_away_games"] = _s.groupby(["player_key", "_away_run"]).cumcount() + 1
    _s.loc[_s["is_away"] == 0, "consecutive_away_games"] = 0
    df["consecutive_away_games"] = _s["consecutive_away_games"]
    return df


def _add_acwr_ratio(df):
    _m7 = df.get("min_last_7d", pd.Series(np.nan, index=df.index))
    _m28 = df.get("min_last_28d", pd.Series(np.nan, index=df.index))
    df["acwr_ratio"] = _m7 / (_m28 / 4.0).replace(0, np.nan)
    return df


def _add_rolling_windows(df):
    """Matches, minutes, starts, full_90s in [7,14,21,28]d windows."""
    df = _add_player_key(df)
    _s = df.sort_values(["player_key", "date"]).copy()
    _s["_seq"] = np.arange(len(_s))
    _dts = _s["date"].values.astype("datetime64[ns]")
    _mins = _s["minutes_played"].fillna(0).values.astype(float)
    _subs = _s["is_substitute"].fillna(0).astype(bool).values

    _out = {}
    windows = [7, 14, 21, 28]
    for w in windows:
        delta = np.timedelta64(w, "D")
        _out[f"matches_last_{w}d"] = np.zeros(len(_s), dtype=float)
        _out[f"min_last_{w}d"] = np.zeros(len(_s), dtype=float)
        _out[f"starts_last_{w}d"] = np.zeros(len(_s), dtype=float)
        _out[f"full_90s_last_{w}d"] = np.zeros(len(_s), dtype=float)

    for pk, grp in _s.groupby("player_key", sort=False):
        g = grp.sort_values("date")
        pos = g["_seq"].values
        n = len(pos)
        dt_g = _dts[pos]
        mn_g = _mins[pos]
        sb_g = _subs[pos]

        for i in range(1, n):
            p = pos[i]
            for w in windows:
                delta = np.timedelta64(w, "D")
                m = (dt_g < dt_g[i]) & (dt_g >= dt_g[i] - delta)
                _out[f"matches_last_{w}d"][p] = m.sum()
                _out[f"min_last_{w}d"][p] = mn_g[m].sum()
                _out[f"starts_last_{w}d"][p] = (~sb_g[m]).sum()
                _out[f"full_90s_last_{w}d"][p] = (mn_g[m] >= 85).sum()

    for col, arr in _out.items():
        df.loc[_s.index, col] = arr
    return df


def _add_short_rest_features(df):
    df = _add_player_key(df)
    _s = df.sort_values(["player_key", "date"]).copy()
    _s["_seq"] = np.arange(len(_s))
    _rd = _s["rest_days"].fillna(14).values.astype(float)

    _out = {}
    for k in [
        "short_rest_last_3_matches", "avg_rest_last_3_matches", "min_rest_last_3_matches",
        "matches_with_rest_le_3d_last_30d", "matches_with_rest_le_4d_last_30d",
        "matches_with_rest_le_6d_last_30d",
    ]:
        _out[k] = np.zeros(len(_s), dtype=float)

    for pk, grp in _s.groupby("player_key", sort=False):
        g = grp.sort_values("date")
        pos = g["_seq"].values
        n = len(pos)
        rd_g = _rd[pos]
        dt_g = _s["date"].values.astype("datetime64[ns]")[pos]

        for i in range(1, n):
            p = pos[i]
            _3 = rd_g[max(0, i - 3):i]
            _out["short_rest_last_3_matches"][p] = np.sum(_3 <= 3)
            _out["avg_rest_last_3_matches"][p] = np.nanmean(_3) if len(_3) > 0 else np.nan
            _out["min_rest_last_3_matches"][p] = np.nanmin(_3) if len(_3) > 0 else np.nan

            d30 = dt_g[i] - np.timedelta64(30, "D")
            m30 = (dt_g[:i] >= d30)
            r30 = rd_g[:i][m30]
            r30 = r30[~np.isnan(r30)]
            _out["matches_with_rest_le_3d_last_30d"][p] = np.sum(r30 <= 3)
            _out["matches_with_rest_le_4d_last_30d"][p] = np.sum(r30 <= 4)
            _out["matches_with_rest_le_6d_last_30d"][p] = np.sum(r30 <= 6)

    for col, arr in _out.items():
        df.loc[_s.index, col] = arr
    return df


def _add_position_z_scores(df):
    for col in ["duels_total", "tackles_total", "fouls_committed", "minutes_played"]:
        _m = df.groupby("player_position")[col].transform("mean")
        _s = df.groupby("player_position")[col].transform("std").replace(0, 1.0)
        df[f"{col}_position_z"] = (df[col] - _m) / _s
    return df


def _add_physical_load_index(df):
    def _mm(s):
        lo, hi = s.min(), s.max()
        return (s - lo) / (hi - lo) if hi > lo else pd.Series(0.5, index=s.index)

    df["physical_load_index"] = (
        0.30 * _mm(df["minutes_played"])
        + 0.20 * _mm(df.get("duels_total", pd.Series(0, index=df.index)))
        + 0.15 * _mm(df.get("tackles_total", pd.Series(0, index=df.index)))
        + 0.10 * _mm(df.get("tackles_blocks", pd.Series(0, index=df.index)))
        + 0.10 * _mm(df.get("fouls_committed", pd.Series(0, index=df.index)))
        + 0.10 * _mm(df.get("dribbles_attempts", pd.Series(0, index=df.index)))
        + 0.05 * _mm(df.get("tackles_interceptions", pd.Series(0, index=df.index)))
    )
    return df


def _add_action_load(df):
    df = _add_player_key(df)
    _s = df.sort_values(["player_key", "date"]).copy()
    _s["_seq"] = np.arange(len(_s))

    _SRCS = [
        ("duels_total", "duels"),
        ("tackles_total", "tackles"),
        ("fouls_committed", "fouls"),
        ("dribbles_attempts", "dribbles"),
    ]

    _out = {}
    for _, sh in _SRCS:
        _out[f"{sh}_last_3_matches"] = np.zeros(len(_s), dtype=np.float32)
        _out[f"{sh}_last_14d"] = np.zeros(len(_s), dtype=np.float32)
    _out["cards_last_5_matches"] = np.zeros(len(_s), dtype=np.float32)

    _cy = _s.get("cards_yellow", pd.Series(0, index=_s.index)).fillna(0).values.astype(np.float32)
    _cr = _s.get("cards_red", pd.Series(0, index=_s.index)).fillna(0).values.astype(np.float32)
    _cards_arr = _cy + _cr

    for pk, grp in _s.groupby("player_key", sort=False):
        g = grp.sort_values("date")
        pos = g["_seq"].values
        n = len(pos)
        _dts = _s["date"].values.astype("datetime64[ns]")[pos]
        _cv = _cards_arr[pos]

        for rc, sh in _SRCS:
            if rc not in _s.columns:
                continue
            _v = _s[rc].fillna(0).values.astype(np.float32)[pos]
            _r3 = _out[f"{sh}_last_3_matches"]
            _r14 = _out[f"{sh}_last_14d"]
            for i in range(1, n):
                p = pos[i]
                _r3[p] = _v[max(0, i - 3):i].sum()
                _cut = _dts[i] - np.timedelta64(14, "D")
                _r14[p] = _v[:i][_dts[:i] >= _cut].sum()

        _r5c = _out["cards_last_5_matches"]
        for i in range(1, n):
            _r5c[pos[i]] = _cv[max(0, i - 5):i].sum()

    for col, arr in _out.items():
        df.loc[_s.index, col] = arr
    return df


def _add_competition_features(df):
    df = _add_player_key(df)
    _s = df.sort_values(["player_key", "date"]).copy()
    _s["_seq"] = np.arange(len(_s))
    _n_all = len(_s)

    _out = {}
    for c in [
        "ucl_minutes_last_7d", "ucl_minutes_last_14d", "ucl_minutes_last_21d",
        "ucl_starts_last_14d", "ucl_full90s_last_14d", "ucl_matches_last_30d",
        "days_since_last_ucl", "played_ucl_last_match",
        "cup_minutes_last_7d", "cup_minutes_last_14d",
        "cup_starts_last_14d", "cup_full90s_last_14d", "cup_matches_last_30d",
        "played_domestic_cup_last_match",
        "transition_ucl_to_pl", "transition_pl_to_ucl", "transition_cup_to_pl",
        "transition_pl_to_cup",
        "competition_switches_last_30d", "competitions_played_last_30d",
        "rest_days_after_ucl", "post_ucl_short_rest", "pl_after_ucl_with_short_rest",
        "ucl_full90_then_pl_short_rest",
        "days_since_european_match", "matches_since_european_match",
    ]:
        _out[c] = np.zeros(_n_all, dtype=np.float32)

    _comp = _s.get("competition", pd.Series("", index=_s.index)).astype(str).str.lower()
    _is_ucl = _comp.str.contains("champions|ucl|uefa champions", regex=True, na=False).values
    _is_pl = _comp.str.contains("premier league|epl", regex=True, na=False).values
    _is_cup = _comp.str.contains(
        "fa cup|league cup|efl cup|carabao|community shield", regex=True, na=False
    ).values

    _mins = _s["minutes_played"].fillna(0).values.astype(np.float32)
    _is_sub = _s["is_substitute"].fillna(0).astype(bool).values
    _starts = (~_is_sub).astype(np.float32)
    _f90 = (_mins >= 89.5).astype(np.float32)
    _dts = _s["date"].values.astype("datetime64[ns]")
    _eu_set = _is_ucl.copy()

    for pk, grp in _s.groupby("player_key", sort=False):
        g = grp.sort_values("date")
        pos = g["_seq"].values
        n = len(pos)
        _dt_g = _dts[pos]
        _mn_g = _mins[pos]
        _st_g = _starts[pos]
        _f9_g = _f90[pos]
        _ucl = _is_ucl[pos]
        _cup = _is_cup[pos]
        _eu = _eu_set[pos]

        _last_ucl_idx = -1

        for i in range(1, n):
            p = pos[i]
            _d_now = _dt_g[i]
            _m7 = _dt_g[:i] >= (_d_now - np.timedelta64(7, "D"))
            _m14 = _dt_g[:i] >= (_d_now - np.timedelta64(14, "D"))
            _m21 = _dt_g[:i] >= (_d_now - np.timedelta64(21, "D"))
            _m30 = _dt_g[:i] >= (_d_now - np.timedelta64(30, "D"))

            _out["ucl_minutes_last_7d"][p] = float((_mn_g[:i] * _ucl[:i])[_m7].sum())
            _out["ucl_minutes_last_14d"][p] = float((_mn_g[:i] * _ucl[:i])[_m14].sum())
            _out["ucl_minutes_last_21d"][p] = float((_mn_g[:i] * _ucl[:i])[_m21].sum())
            _out["ucl_starts_last_14d"][p] = float((_st_g[:i] * _ucl[:i])[_m14].sum())
            _out["ucl_full90s_last_14d"][p] = float((_f9_g[:i] * _ucl[:i])[_m14].sum())
            _out["ucl_matches_last_30d"][p] = float((_ucl[:i] & _m30).sum())

            _out["cup_minutes_last_7d"][p] = float((_mn_g[:i] * _cup[:i])[_m7].sum())
            _out["cup_minutes_last_14d"][p] = float((_mn_g[:i] * _cup[:i])[_m14].sum())
            _out["cup_starts_last_14d"][p] = float((_st_g[:i] * _cup[:i])[_m14].sum())
            _out["cup_full90s_last_14d"][p] = float((_f9_g[:i] * _cup[:i])[_m14].sum())
            _out["cup_matches_last_30d"][p] = float((_cup[:i] & _m30).sum())

            _out["played_ucl_last_match"][p] = float(_ucl[i - 1])
            _out["played_domestic_cup_last_match"][p] = float(_cup[i - 1])

            _out["transition_ucl_to_pl"][p] = float(_ucl[i - 1] and _is_pl[pos[i]])
            _out["transition_pl_to_ucl"][p] = float(_is_pl[pos[i - 1]] and _ucl[i])
            _out["transition_cup_to_pl"][p] = float(_cup[i - 1] and _is_pl[pos[i]])
            _out["transition_pl_to_cup"][p] = float(_is_pl[pos[i - 1]] and _cup[i])

            _past_comp = _comp.iloc[g.index[:i]].values
            _past_comp_30 = _past_comp[_m30[:i]]
            if len(_past_comp_30) > 1:
                _out["competition_switches_last_30d"][p] = float(
                    np.sum(_past_comp_30[1:] != _past_comp_30[:-1])
                )
                _out["competitions_played_last_30d"][p] = float(
                    pd.Series(_past_comp_30).nunique()
                )

            if _last_ucl_idx >= 0:
                _dse = (_d_now - _dt_g[_last_ucl_idx]) / np.timedelta64(1, "D")
                _out["days_since_last_ucl"][p] = float(_dse)
                _out["rest_days_after_ucl"][p] = float(_dse)
                _out["post_ucl_short_rest"][p] = float(_dse <= 4)
                _out["pl_after_ucl_with_short_rest"][p] = float(
                    _is_pl[pos[i]] and (_dse <= 3)
                )
                _out["ucl_full90_then_pl_short_rest"][p] = float(
                    _is_pl[pos[i]] and (_dse <= 3) and (_f9_g[_last_ucl_idx] == 1)
                )

            if _ucl[i]:
                _last_ucl_idx = i

        _e_idx = np.where(_eu)[0]
        for i in range(1, n):
            p = pos[i]
            _past_eu = _e_idx[_e_idx < i]
            if len(_past_eu) > 0:
                _last_eu = _past_eu[-1]
                _out["days_since_european_match"][p] = float(
                    (_dt_g[i] - _dt_g[_last_eu]) / np.timedelta64(1, "D")
                )
                _out["matches_since_european_match"][p] = float(i - _last_eu - 1)

    for col, arr in _out.items():
        df.loc[_s.index, col] = arr
    return df


def _add_player_avg_deviations(df):
    group_cols = ["player_key"] + (["season"] if "season" in df.columns else [])
    for _base, _delta, _z in [
        ("min_last_21d", "minutes_last_21d_vs_player_avg", "minutes_last_21d_player_z"),
        ("full_90s_last_14d", "full90_last_14d_vs_player_avg", None),
        ("physical_load_index", "physical_load_last_14d_vs_player_avg", None),
        ("starts_last_14d", "starts_last_14d_vs_player_avg", None),
    ]:
        if _base in df.columns:
            _gm = df.groupby(group_cols)[_base].transform("mean")
            df[_delta] = df[_base] - _gm
            if _z is not None:
                _gs = df.groupby(group_cols)[_base].transform("std").replace(0, np.nan)
                df[_z] = ((df[_base] - _gm) / _gs).fillna(0)
    return df


def _add_injury_features(df):
    df["returning_from_injury"] = (
        df.get("fixtures_missed_last_30d", pd.Series(0, index=df.index)).fillna(0) > 0
    ).astype(float)
    for c in ["squad_injured_count", "squad_soft_tissue_count", "squad_avg_days_out",
              "fixtures_missed_last_30d"]:
        if c not in df.columns:
            df[c] = np.nan
    df["squad_injured_count"] = df["squad_injured_count"].fillna(np.nan)
    df["squad_soft_tissue_count"] = df["squad_soft_tissue_count"].fillna(np.nan)
    df["squad_avg_days_out"] = df["squad_avg_days_out"].fillna(np.nan)
    df["fixtures_missed_last_30d"] = df["fixtures_missed_last_30d"].fillna(np.nan)

    _rd_m = df.get("rest_days", pd.Series(np.nan, index=df.index)).isna()
    _eu_m = df.get("days_since_european_match", pd.Series(np.nan, index=df.index)).isna()
    _si_m = df.get("squad_injured_count", pd.Series(np.nan, index=df.index)).isna()
    df["rest_days_missing"] = _rd_m.astype(float)
    df["days_since_european_match_missing"] = _eu_m.astype(float)
    df["squad_injured_count_missing"] = _si_m.astype(float)

    return df


def assign_player_role_v4b(df):
    # Calculate temporary metrics safely
    avg_min_last_28d = (
        df["min_last_28d"].fillna(0) / df["matches_last_28d"].fillna(1).clip(lower=1)
    )
    start_rate_last_28d = (
        df["starts_last_28d"].fillna(0) / df["matches_last_28d"].fillna(1).clip(lower=1)
    )
    
    _core = (
        (df["starts_last_28d"].fillna(0) >= 3)
        & (start_rate_last_28d >= 0.70)
        & (avg_min_last_28d >= 65)
    )
    _impact = (
        (df["matches_last_28d"].fillna(0) >= 3)
        & (df["starts_last_28d"].fillna(0) < 2)
        & (avg_min_last_28d < 35)
    )
    _rare = df["matches_last_28d"].fillna(0) <= 2
    _rotation = (
        (df["matches_last_28d"].fillna(0) >= 3)
        & (~_core)
        & (avg_min_last_28d >= 35)
    )
    
    # Return JUST the numpy array of strings so it maps neatly into a single column
    return np.select(
        [_core, _rotation, _impact, _rare],
        ["core_starter", "rotation_player", "impact_sub", "rare_player"],
        default="rotation_player",
    )


def engineer_features_v4b(df_raw):
    _V4B_CHECK = "rest_days"
    if _V4B_CHECK in df_raw.columns:
        pass
    
    df = df_raw.copy()

    df = _add_player_key(df)
    df = _add_rest_days_features(df)
    df = _add_consecutive_away_games(df)
    df = _add_rolling_windows(df)
    df = _add_short_rest_features(df)
    df = _add_position_z_scores(df)
    df = _add_physical_load_index(df)
    df = _add_acwr_ratio(df)
    df = _add_action_load(df)
    df = _add_competition_features(df)
    df = _add_player_avg_deviations(df)
    df = _add_injury_features(df)

    _MODEL_FEATS = {
        "rest_days", "acwr_ratio", "consecutive_away_games", "high_congestion_flag",
        "matches_last_7d", "matches_last_14d", "matches_last_21d", "matches_last_28d",
        "min_last_7d", "min_last_14d", "min_last_21d", "min_last_28d",
        "starts_last_7d", "starts_last_14d", "starts_last_28d",
        "full_90s_last_7d", "full_90s_last_14d", "full_90s_last_28d",
        "short_rest_last_3_matches", "avg_rest_last_3_matches", "min_rest_last_3_matches",
        "matches_with_rest_le_3d_last_30d", "matches_with_rest_le_4d_last_30d",
        "matches_with_rest_le_6d_last_30d",
        "days_since_european_match", "matches_since_european_match",
        "duels_last_3_matches", "duels_last_14d", "tackles_last_3_matches",
        "tackles_last_14d", "fouls_last_3_matches", "fouls_last_14d",
        "dribbles_last_3_matches", "dribbles_last_14d", "cards_last_5_matches",
        "duels_total_position_z", "tackles_total_position_z",
        "fouls_committed_position_z", "minutes_played_position_z",
        "physical_load_index",
        "squad_injured_count", "squad_soft_tissue_count", "squad_avg_days_out",
        "returning_from_injury", "fixtures_missed_last_30d",
        "ucl_minutes_last_7d", "ucl_minutes_last_14d", "ucl_minutes_last_21d",
        "ucl_starts_last_14d", "ucl_full90s_last_14d", "ucl_matches_last_30d",
        "days_since_last_ucl", "played_ucl_last_match",
        "cup_minutes_last_7d", "cup_minutes_last_14d",
        "cup_starts_last_14d", "cup_full90s_last_14d", "cup_matches_last_30d",
        "played_domestic_cup_last_match",
        "transition_ucl_to_pl", "transition_pl_to_ucl",
        "transition_cup_to_pl", "transition_pl_to_cup",
        "competition_switches_last_30d", "competitions_played_last_30d",
        "rest_days_after_ucl", "post_ucl_short_rest",
        "pl_after_ucl_with_short_rest", "ucl_full90_then_pl_short_rest",
        "minutes_last_21d_vs_player_avg", "minutes_last_21d_player_z",
        "full90_last_14d_vs_player_avg", "physical_load_last_14d_vs_player_avg",
        "starts_last_14d_vs_player_avg",
    }

    for f in _MODEL_FEATS:
        if f not in df.columns:
            df[f] = np.nan

    # CRITICAL ADDITION: Run the role assignment step right here
    df["player_role_v4b"] = assign_player_role_v4b(df)

    return df