from pathlib import Path

import numpy as np
import pandas as pd
import catboost
import joblib

from fatigue_monitor.src.config import (
    V6_MODEL_PATH, V6_METADATA_PATH,
    V6_NR_MODEL_PATH, V6_NR_METADATA_PATH,
    V6_OPERATING_POLICY,
    V6_RISK_BANDS, V6_RISK_LABELS,
)
from fatigue_monitor.src.feature_engineering_v6 import (
    engineer_features_v6, assign_player_role_v6,
)


def load_v6_artifacts(variant="no_competition"):
    if variant == "no_competition":
        model_path = V6_MODEL_PATH
        meta_path = V6_METADATA_PATH
    elif variant == "no_rating_baseline":
        model_path = V6_NR_MODEL_PATH
        meta_path = V6_NR_METADATA_PATH
    else:
        raise ValueError(f"Unknown V6 variant: {variant}")

    model = catboost.CatBoostClassifier()
    model.load_model(str(model_path))
    metadata = joblib.load(meta_path)
    return model, metadata


def predict_v6(df_raw, model, metadata, suffix=""):
    df = engineer_features_v6(df_raw)

    df = df[df["player_position"] != "G"].copy()
    df["player_role_v6"] = assign_player_role_v6(df)

    df_model = df[df["player_role_v6"].isin(["core_starter", "rotation_player"])].copy()

    feat_list = metadata["features"]
    cat_feats = metadata["categorical_features"]
    imp_vals = metadata["imputation_values"]

    for f in feat_list:
        if f not in df_model.columns:
            df_model[f] = np.nan

    for f, imp in imp_vals.items():
        if f not in feat_list:
            continue
        if imp["type"] == "numerical":
            df_model[f] = df_model[f].fillna(imp["value"])
        else:
            df_model[f] = df_model[f].fillna(imp["value"])

    for f in cat_feats:
        df_model[f] = df_model[f].astype(str)

    X = df_model[feat_list]
    risk_col = f"risk_score{suffix}"
    df_model[risk_col] = model.predict_proba(X)[:, 1]

    policy = metadata.get("operating_policy", V6_OPERATING_POLICY)
    thresh_col = f"monitoring_threshold{suffix}"
    df_model[thresh_col] = np.where(
        df_model["player_role_v6"] == "core_starter",
        policy.get("core_starter_threshold", 0.5),
        policy.get("rotation_player_threshold", 0.5),
    )

    flag_col = f"monitoring_flag{suffix}"
    df_model[flag_col] = (
        df_model[risk_col] >= df_model[thresh_col]
    ).astype(int)

    band_col = f"risk_band{suffix}"
    df_model[band_col] = pd.cut(
        df_model[risk_col],
        bins=V6_RISK_BANDS,
        labels=V6_RISK_LABELS,
    )

    reason_col = f"main_risk_reasons{suffix}"
    df_model[reason_col] = _generate_v6_reasons(df_model, metadata, risk_col)

    return df_model


def _generate_v6_reasons(df, metadata, risk_col="risk_score"):
    feature_groups = metadata.get("feature_groups", {})
    reasons_list = []

    for _, row in df.iterrows():
        reasons = []
        score = row[risk_col]

        wl_group = feature_groups.get("workload_recovery_windows", [])
        for f in ["min_last_14d", "matches_with_rest_le_3d_last_30d",
                   "matches_with_rest_le_4d_last_30d", "full_90s_last_14d",
                   "full_90s_last_28d", "starts_last_14d", "rest_days"]:
            if f not in row or pd.isna(row[f]):
                continue
            v = row[f]
            if f == "min_last_14d" and v >= 180:
                reasons.append(f"high minutes in last 14 days ({v:.0f})")
            elif f == "matches_with_rest_le_3d_last_30d" and v >= 2:
                reasons.append(f"multiple short-rest matches in last 30 days")
            elif f == "matches_with_rest_le_4d_last_30d" and v >= 3:
                reasons.append(f"multiple short-rest matches in last 30 days")
            elif f == "full_90s_last_14d" and v >= 3:
                reasons.append(f"multiple full-match exposures in last 14 days")
            elif f == "full_90s_last_28d" and v >= 5:
                reasons.append(f"high full-match exposure in last 28 days")
            elif f == "starts_last_14d" and v >= 3:
                reasons.append(f"multiple starts in last 14 days")
            elif f == "rest_days" and v <= 3:
                reasons.append(f"short rest ({v:.0f}d)")

        comp_group = feature_groups.get("competition_sequence_load", [])
        if row.get("ucl_minutes_last_14d", 0) >= 90:
            reasons.append("recent Champions League load")
        if row.get("cup_minutes_last_14d", 0) >= 90:
            reasons.append("recent domestic cup load")
        if row.get("post_ucl_short_rest", 0) == 1:
            reasons.append("post-European short rest")
        if row.get("pl_after_ucl_with_short_rest", 0) == 1:
            reasons.append("league match after European fixture with short rest")

        pos_group = feature_groups.get("position_adjusted_load", [])
        if row.get("recent_action_load_per90_pos_z", 0) > 1.0:
            reasons.append("high action load relative to position")
        elif row.get("minutes_last_5_matches_pos_z", 0) > 1.0:
            reasons.append("high minutes relative to position")
        elif row.get("min_last_7d_pos_z", 0) > 1.0:
            reasons.append("high weekly minutes relative to position")

        inj_group = feature_groups.get("injury_context", [])
        if row.get("high_squad_injury_pressure", 0) == 1:
            reasons.append("high squad injury pressure")
        if row.get("returning_from_injury", 0) == 1:
            reasons.append("returning from injury")
        if row.get("high_soft_tissue_pressure", 0) == 1:
            reasons.append("high soft tissue injury pressure in squad")
        if row.get("missed_recent_fixture_flag", 0) == 1:
            reasons.append("recent missed fixtures")

        role_label = row.get("player_role_v6", "")
        if role_label == "rotation_player" and score >= 0.5:
            reasons.append("rotation player exceeding threshold")

        if not reasons:
            if score >= 0.45:
                reasons.append("elevated workload pattern")
            else:
                reasons.append("within normal range")

        reasons_list.append(", ".join(reasons[:6]))

    return reasons_list
