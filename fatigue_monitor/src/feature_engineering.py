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


def _add_rolling_features(df):
    df = _add_player_key(df)
    df_fe = df.copy()
    df_fe.sort_values(["player_key", "date"], inplace=True)

    def _per_player_rolling(grp):
        idx = grp.index
        dates = grp["date"].values.astype("datetime64[ns]")
        mins = grp["minutes_played"].values.astype(float)
        subs = grp["is_substitute"].values.astype(bool)
        rest = grp["rest_days"].values.astype(float)
        comps = grp["competition"].values
        n = len(dates)
        out = {}

        for w in [7, 14, 21, 28]:
            delta = np.timedelta64(w, "D")
            cnt = np.zeros(n, dtype=float)
            min_s = np.zeros(n, dtype=float)
            starts = np.zeros(n, dtype=float)
            f90s = np.zeros(n, dtype=float)
            for i in range(n):
                mask = (dates < dates[i]) & (dates >= dates[i] - delta)
                cnt[i] = mask.sum()
                min_s[i] = mins[mask].sum()
                starts[i] = (~subs[mask]).sum()
                f90s[i] = (mins[mask] >= 85).sum()
            out[f"matches_last_{w}d"] = cnt
            if w > 7:
                out[f"min_last_{w}d"] = min_s
            out[f"starts_last_{w}d"] = starts
            out[f"full_90s_last_{w}d"] = f90s

        lr = np.full((n, 3), np.nan)
        for i in range(n):
            if i >= 1:
                lr[i, 0] = rest[i - 1]
            if i >= 2:
                lr[i, 1] = rest[i - 2]
            if i >= 3:
                lr[i, 2] = rest[i - 3]

        out["short_rest_last_3_matches"] = np.nansum(lr <= 3, axis=1).astype(float)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            out["avg_rest_last_3_matches"] = np.nanmean(lr, axis=1)
            _min_lr = np.nanmin(lr, axis=1)
        out["min_rest_last_3_matches"] = np.where(np.all(np.isnan(lr), axis=1), np.nan, _min_lr)

        d30 = np.timedelta64(30, "D")
        le3 = np.zeros(n, dtype=float)
        le4 = np.zeros(n, dtype=float)
        le6 = np.zeros(n, dtype=float)
        for i in range(n):
            m30 = (dates < dates[i]) & (dates >= dates[i] - d30)
            r30 = rest[m30]
            r30 = r30[~np.isnan(r30)]
            le3[i] = (r30 <= 3).sum()
            le4[i] = (r30 <= 4).sum()
            le6[i] = (r30 <= 6).sum()
        out["matches_with_rest_le_3d_last_30d"] = le3
        out["matches_with_rest_le_4d_last_30d"] = le4
        out["matches_with_rest_le_6d_last_30d"] = le6

        eu_set = {"Champions League"}
        cup_set = {"FA Cup", "League Cup", "Community Shield"}
        prev = np.concatenate([[""], comps[:-1]])

        out["played_europe_last_match"] = np.isin(prev, list(eu_set)).astype(float)
        out["played_domestic_cup_last_match"] = np.isin(prev, list(cup_set)).astype(float)
        out["competition_switch"] = ((prev != comps) & (prev != "")).astype(float)
        out["pl_after_ucl"] = ((comps == "Premier League") & np.isin(prev, list(eu_set))).astype(float)
        out["pl_after_cup"] = ((comps == "Premier League") & np.isin(prev, list(cup_set))).astype(float)
        out["ucl_after_pl"] = ((comps == "Champions League") & (prev == "Premier League")).astype(float)

        eu_mask = np.isin(comps, list(eu_set))
        dse = np.full(n, np.nan)
        mse = np.full(n, np.nan)
        for i in range(n):
            past_eu = np.where(eu_mask[:i])[0]
            if len(past_eu) > 0:
                last_i = past_eu[-1]
                dse[i] = (dates[i] - dates[last_i]) / np.timedelta64(1, "D")
                mse[i] = float(i - last_i - 1)
        out["days_since_european_match"] = dse
        out["matches_since_european_match"] = mse

        return pd.DataFrame({k: pd.Series(v, index=idx) for k, v in out.items()})

    fe_frames = []
    for _pk, _grp in df_fe.groupby("player_key"):
        fe_frames.append(_per_player_rolling(_grp))
    fe_df = pd.concat(fe_frames)
    for col in fe_df.columns:
        df_fe[col] = fe_df[col]

    for _col in ["duels_total", "tackles_total", "fouls_committed", "minutes_played"]:
        _pos_mean = df_fe.groupby("player_position")[_col].transform("mean")
        _pos_std = df_fe.groupby("player_position")[_col].transform("std").replace(0, 1.0)
        df_fe[f"{_col}_position_z"] = (df_fe[_col] - _pos_mean) / _pos_std

    def _minmax(s):
        lo, hi = s.min(), s.max()
        return (s - lo) / (hi - lo) if hi > lo else pd.Series(0.5, index=s.index)

    df_fe["physical_load_index"] = (
        0.30 * _minmax(df_fe["minutes_played"])
        + 0.20 * _minmax(df_fe["duels_total"])
        + 0.15 * _minmax(df_fe["tackles_total"])
        + 0.10 * _minmax(df_fe["tackles_blocks"])
        + 0.10 * _minmax(df_fe["fouls_committed"])
        + 0.10 * _minmax(df_fe["dribbles_attempts"])
        + 0.05 * _minmax(df_fe["tackles_interceptions"])
    )

    df_fe.sort_index(inplace=True)
    return df_fe


def _add_burden_features(df):
    _V3B_CHECK = "duels_last_3_matches"
    if _V3B_CHECK in df.columns:
        return df

    _SRCS = [
        ("duels_total", "duels"),
        ("tackles_total", "tackles"),
        ("fouls_committed", "fouls"),
        ("dribbles_attempts", "dribbles"),
    ]
    _df_s = df.sort_values(["player_key", "date"]).copy()
    _df_s["_seq"] = range(len(_df_s))
    _N = len(_df_s)
    _14D = np.timedelta64(14, "D")

    _out = {}
    for _, _sh in _SRCS:
        _out[f"{_sh}_last_3_matches"] = np.zeros(_N, dtype=np.float32)
        _out[f"{_sh}_last_14d"] = np.zeros(_N, dtype=np.float32)
    _out["cards_last_5_matches"] = np.zeros(_N, dtype=np.float32)

    _cy = _df_s["cards_yellow"].fillna(0) if "cards_yellow" in _df_s.columns else pd.Series(0.0, index=_df_s.index)
    _cr = _df_s["cards_red"].fillna(0) if "cards_red" in _df_s.columns else pd.Series(0.0, index=_df_s.index)
    _cards_arr = (_cy + _cr).values.astype(np.float32)

    for _pk, _grp_df in _df_s.groupby("player_key", sort=False):
        _g = _grp_df.sort_values("date")
        _pos = _g["_seq"].values
        _dts = _g["date"].values.astype("datetime64[ns]")
        _n = len(_pos)
        _cv = _cards_arr[_pos]

        for _rc, _sh in _SRCS:
            if _rc not in _g.columns:
                continue
            _v = _g[_rc].fillna(0).values.astype(np.float32)
            _r3 = _out[f"{_sh}_last_3_matches"]
            _r14 = _out[f"{_sh}_last_14d"]
            for _i in range(1, _n):
                _p = _pos[_i]
                _r3[_p] = _v[max(0, _i - 3):_i].sum()
                _cut = _dts[_i] - _14D
                _r14[_p] = _v[:_i][_dts[:_i] >= _cut].sum()

        _r5c = _out["cards_last_5_matches"]
        for _i in range(1, _n):
            _r5c[_pos[_i]] = _cv[max(0, _i - 5):_i].sum()

    _orig_idx = _df_s.index.values
    for _col, _arr in _out.items():
        df.loc[_orig_idx, _col] = _arr
    return df


def _add_v4_features(df):
    _df_s = df.sort_values(["player_key", "date"]).copy()
    _df_s["_seq"] = np.arange(len(_df_s))
    _n_all = len(_df_s)

    _out = {}
    for _c in [
        "ucl_minutes_last_7d", "ucl_minutes_last_14d", "ucl_minutes_last_21d",
        "ucl_starts_last_14d", "ucl_full90s_last_14d", "ucl_matches_last_30d",
        "days_since_last_ucl", "played_ucl_last_match",
        "cup_minutes_last_7d", "cup_minutes_last_14d",
        "cup_starts_last_14d", "cup_full90s_last_14d", "cup_matches_last_30d",
        "played_domestic_cup_last_match",
        "transition_ucl_to_pl", "transition_pl_to_ucl", "transition_cup_to_pl", "transition_pl_to_cup",
        "competition_switches_last_30d", "competitions_played_last_30d",
        "rest_days_after_ucl", "post_ucl_short_rest", "pl_after_ucl_with_short_rest", "ucl_full90_then_pl_short_rest",
        "minutes_median_last_5", "minutes_median_last_10",
    ]:
        _out[_c] = np.zeros(_n_all, dtype=np.float32)

    _comp = _df_s.get("competition", pd.Series("", index=_df_s.index)).astype(str).str.lower()
    _is_ucl_all = _comp.str.contains("champions|ucl|uefa champions", regex=True, na=False).values
    _is_pl_all = _comp.str.contains("premier league|epl", regex=True, na=False).values
    _is_cup_all = _comp.str.contains("fa cup|league cup|efl cup|carabao|community shield", regex=True, na=False).values

    _min_all = _df_s.get("minutes_played", pd.Series(0, index=_df_s.index)).fillna(0).values.astype(np.float32)
    _st_all = _df_s.get("start", pd.Series(0, index=_df_s.index)).fillna(0).values.astype(np.float32)
    if "is_starting" in _df_s.columns:
        _st_all = _df_s["is_starting"].fillna(0).astype(float).values.astype(np.float32)
    _f90_all = (_min_all >= 89.5).astype(np.float32)
    _dts_all = _df_s["date"].values.astype("datetime64[ns]")

    for _pk, _grp in _df_s.groupby("player_key", sort=False):
        _g = _grp.sort_values("date")
        _pos = _g["_seq"].values
        _dts = _dts_all[_pos]
        _n = len(_pos)

        _mins = _min_all[_pos]
        _sts = _st_all[_pos]
        _f90s = _f90_all[_pos]
        _is_ucl = _is_ucl_all[_pos]
        _is_pl = _is_pl_all[_pos]
        _is_cup = _is_cup_all[_pos]

        _last_ucl_idx = -1

        for _i in range(_n):
            _p = _pos[_i]
            if _i == 0:
                continue

            _past_dts = _dts[:_i]
            _past_mins = _mins[:_i]
            _past_sts = _sts[:_i]
            _past_f90s = _f90s[:_i]
            _past_ucl = _is_ucl[:_i]
            _past_cup = _is_cup[:_i]

            _d_now = _dts[_i]

            _m7 = _past_dts >= (_d_now - np.timedelta64(7, "D"))
            _m14 = _past_dts >= (_d_now - np.timedelta64(14, "D"))
            _m21 = _past_dts >= (_d_now - np.timedelta64(21, "D"))
            _m30 = _past_dts >= (_d_now - np.timedelta64(30, "D"))

            _out["ucl_minutes_last_7d"][_p] = float(_past_mins[_past_ucl & _m7].sum())
            _out["ucl_minutes_last_14d"][_p] = float(_past_mins[_past_ucl & _m14].sum())
            _out["ucl_minutes_last_21d"][_p] = float(_past_mins[_past_ucl & _m21].sum())
            _out["ucl_starts_last_14d"][_p] = float(_past_sts[_past_ucl & _m14].sum())
            _out["ucl_full90s_last_14d"][_p] = float(_past_f90s[_past_ucl & _m14].sum())
            _out["ucl_matches_last_30d"][_p] = float((_past_ucl & _m30).sum())

            _out["cup_minutes_last_7d"][_p] = float(_past_mins[_past_cup & _m7].sum())
            _out["cup_minutes_last_14d"][_p] = float(_past_mins[_past_cup & _m14].sum())
            _out["cup_starts_last_14d"][_p] = float(_past_sts[_past_cup & _m14].sum())
            _out["cup_full90s_last_14d"][_p] = float(_past_f90s[_past_cup & _m14].sum())
            _out["cup_matches_last_30d"][_p] = float((_past_cup & _m30).sum())

            _out["played_ucl_last_match"][_p] = float(_is_ucl[_i - 1])
            _out["played_domestic_cup_last_match"][_p] = float(_is_cup[_i - 1])

            _out["transition_ucl_to_pl"][_p] = float(_is_ucl[_i - 1] and _is_pl[_i])
            _out["transition_pl_to_ucl"][_p] = float(_is_pl[_i - 1] and _is_ucl[_i])
            _out["transition_cup_to_pl"][_p] = float(_is_cup[_i - 1] and _is_pl[_i])
            _out["transition_pl_to_cup"][_p] = float(_is_pl[_i - 1] and _is_cup[_i])

            _past_comp = _comp.iloc[_g.index[:_i]].values
            _past_comp_30 = _past_comp[_m30]
            if len(_past_comp_30) > 1:
                _out["competition_switches_last_30d"][_p] = float(np.sum(_past_comp_30[1:] != _past_comp_30[:-1]))
                _out["competitions_played_last_30d"][_p] = float(pd.Series(_past_comp_30).nunique())

            if _last_ucl_idx >= 0:
                _days_since_ucl = (_d_now - _dts[_last_ucl_idx]) / np.timedelta64(1, "D")
                _out["days_since_last_ucl"][_p] = float(_days_since_ucl)
                _out["rest_days_after_ucl"][_p] = float(_days_since_ucl)
                _out["post_ucl_short_rest"][_p] = float(_days_since_ucl <= 4)
                _out["pl_after_ucl_with_short_rest"][_p] = float(_is_pl[_i] and (_days_since_ucl <= 3))
                _out["ucl_full90_then_pl_short_rest"][_p] = float(_is_pl[_i] and (_days_since_ucl <= 3) and (_f90s[_last_ucl_idx] == 1))

            _out["minutes_median_last_5"][_p] = float(np.median(_past_mins[max(0, _i - 5):_i]))
            _out["minutes_median_last_10"][_p] = float(np.median(_past_mins[max(0, _i - 10):_i]))

            if _is_ucl[_i]:
                _last_ucl_idx = _i

    for _k, _arr in _out.items():
        df.loc[_df_s.index, _k] = _arr

    _group_cols = ["player_key"] + (["season"] if "season" in df.columns else [])
    for _base_col, _new_delta, _new_z in [
        ("min_last_21d", "minutes_last_21d_vs_player_avg", "minutes_last_21d_player_z"),
        ("full_90s_last_14d", "full90_last_14d_vs_player_avg", None),
        ("physical_load_index", "physical_load_last_14d_vs_player_avg", None),
        ("starts_last_14d", "starts_last_14d_vs_player_avg", None),
    ]:
        if _base_col in df.columns:
            _gmean = df.groupby(_group_cols)[_base_col].transform("mean")
            df[_new_delta] = df[_base_col] - _gmean
            if _new_z is not None:
                _gstd = df.groupby(_group_cols)[_base_col].transform("std").replace(0, np.nan)
                df[_new_z] = ((df[_base_col] - _gmean) / _gstd).fillna(0)

    df["next_is_substitute"] = (
        (df["next_minutes_played"].fillna(0) > 0) & (df["next_minutes_played"].fillna(0) < 30)
    ).astype(int)

    return df


def assign_player_role(df):
    df["avg_min_last_28d"] = (
        df["min_last_28d"].fillna(0) / df["matches_last_28d"].fillna(1).clip(lower=1)
    )
    df["start_rate_last_28d"] = (
        df["starts_last_28d"].fillna(0) / df["matches_last_28d"].fillna(1).clip(lower=1)
    )

    _core = (
        (df["starts_last_28d"].fillna(0) >= 3)
        & (df["start_rate_last_28d"] >= 0.70)
        & (df["avg_min_last_28d"] >= 65)
    )
    _impact = (
        (df["matches_last_28d"].fillna(0) >= 3)
        & (df["starts_last_28d"].fillna(0) < 2)
        & (df["avg_min_last_28d"] < 35)
    )
    _rare = df["matches_last_28d"].fillna(0) <= 2
    _rotation = (
        (df["matches_last_28d"].fillna(0) >= 3) & (~_core) & (df["avg_min_last_28d"] >= 35)
    )

    return np.select(
        [_core, _rotation, _impact, _rare],
        ["core_starter", "rotation_player", "impact_sub", "rare_player"],
        default="rotation_player",
    )


def engineer_features(df):
    df = _add_player_key(df.copy())
    df = _add_rolling_features(df)
    df = _add_burden_features(df)
    df = _add_v4_features(df)
    return df
