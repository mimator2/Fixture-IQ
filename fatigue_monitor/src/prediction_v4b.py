import json
import numpy as np
import pandas as pd
import joblib

from fatigue_monitor.src.config import (
    V4B_MODEL_PATH, V4B_PREPROCESSOR_PATH,
    V4B_NUM_FEATURES_PATH, V4B_CAT_FEATURES_PATH, V4B_METADATA_PATH,
    V4B_OPERATING_POLICY, V4B_RISK_BANDS, V4B_RISK_LABELS,
)
from fatigue_monitor.src.feature_engineering_v4b import engineer_features_v4b, assign_player_role_v4b


def load_v4b_artifacts():
    model = joblib.load(V4B_MODEL_PATH)
    preprocessor = joblib.load(V4B_PREPROCESSOR_PATH)
    num_features = joblib.load(V4B_NUM_FEATURES_PATH)
    cat_features = joblib.load(V4B_CAT_FEATURES_PATH)
    with open(V4B_METADATA_PATH) as f:
        raw_meta = json.load(f)
    feat_info = raw_meta.get("features", {})
    metadata = {
        "features": num_features + cat_features,
        "categorical_features": cat_features,
        "numerical_features": num_features,
        "imputation_values": {},
        "operating_policy": raw_meta.get("operating_policy", V4B_OPERATING_POLICY),
        "raw_metadata": raw_meta,
    }
    return model, preprocessor, metadata


def predict_v4b(df_raw, model, preprocessor, metadata):
    df = engineer_features_v4b(df_raw)

    df = df[df["player_position"] != "G"].copy()
    df["player_role_v4b"] = assign_player_role_v4b(df)
    df_model = df.copy()

    num_feats = metadata["numerical_features"]
    cat_feats = metadata["categorical_features"]
    feat_list = metadata["features"]

    for f in feat_list:
        if f not in df_model.columns:
            df_model[f] = np.nan

    X = df_model[feat_list].copy()
    X_t = preprocessor.transform(X)
    risk_vals = model.predict_proba(X_t)[:, 1]

    minutes_col = "minutes_played"
    if minutes_col in df_model.columns:
        short_mask = df_model[minutes_col].fillna(0) < 45
        n_guarded = int(short_mask.sum())
        if n_guarded:
            risk_vals = risk_vals.copy()
            risk_vals[short_mask.values] = 0.0
            print(f"  predict_v4b: minute guard set risk=0 for {n_guarded:,} rows (< 45 min)")

    policy = V4B_OPERATING_POLICY
    thresh_vals = np.where(
        df_model["player_role_v4b"] == "core_starter",
        policy.get("core_starter_threshold", 0.45),
        policy.get("rotation_player_threshold", 0.50),
    )

    flag_vals = (risk_vals >= thresh_vals).astype(int)
    band_vals = pd.cut(risk_vals, bins=V4B_RISK_BANDS, labels=V4B_RISK_LABELS, right=False)

    _result = pd.DataFrame({
        "risk_score": risk_vals,
        "monitoring_threshold": thresh_vals,
        "monitoring_flag": flag_vals,
        "risk_band": band_vals,
        "main_risk_reasons": _generate_v4b_reasons(df_model, risk_vals),
    }, index=df_model.index)
    df_model = pd.concat([df_model, _result], axis=1)

    return df_model


def _generate_v4b_reasons(df, risk_vals):
    reasons_list = []
    for i, (_, row) in enumerate(df.iterrows()):
        reasons = []
        score = risk_vals[i]

        if row.get("min_last_14d", 0) >= 180:
            reasons.append(f"high minutes in last 14 days ({row['min_last_14d']:.0f})")
        if row.get("min_last_21d", 0) >= 270:
            reasons.append(f"high minutes in last 21 days ({row['min_last_21d']:.0f})")
        if row.get("matches_with_rest_le_4d_last_30d", 0) >= 3:
            reasons.append("multiple short-rest matches in last 30 days")
        if row.get("matches_with_rest_le_3d_last_30d", 0) >= 2:
            reasons.append("consecutive short-rest matches")
        if row.get("full_90s_last_14d", 0) >= 3:
            reasons.append("multiple full-match exposures in last 14 days")
        if row.get("starts_last_14d", 0) >= 3:
            reasons.append("multiple starts in last 14 days")
        if row.get("rest_days", 99) <= 3:
            reasons.append(f"short rest ({row['rest_days']:.0f}d)")
        if row.get("ucl_minutes_last_14d", 0) >= 90:
            reasons.append("recent Champions League load")
        if row.get("cup_minutes_last_14d", 0) >= 90:
            reasons.append("recent domestic cup load")
        if row.get("post_ucl_short_rest", 0) == 1:
            reasons.append("post-European short rest")
        if row.get("minutes_played_position_z", 0) > 1.0:
            reasons.append("high minutes burden for position")
        if row.get("returning_from_injury", 0) == 1:
            reasons.append("returning from injury")
        if row.get("squad_injured_count", 0) >= 4:
            reasons.append("high squad injury pressure")
        if row.get("physical_load_last_14d_vs_player_avg", 0) > 0:
            reasons.append("physical load above season average")
        if row.get("minutes_last_21d_player_z", 0) > 1.0:
            reasons.append("minutes load well above personal average")
        if row.get("full90_last_14d_vs_player_avg", 0) > 0:
            reasons.append("full-match exposure above season average")

        role = row.get("player_role_v4b", "")
        if role == "rotation_player" and score >= 0.5:
            reasons.append("rotation player exceeding threshold")

        if not reasons:
            if score >= 0.65:
                reasons.append("high risk — accumulated load across multiple signals")
            elif score >= 0.45:
                reasons.append("elevated workload pattern")
            elif score >= 0.35:
                reasons.append("moderate workload indicators")
            else:
                reasons.append("within normal range")

        reasons_list.append(", ".join(reasons[:6]))

    return reasons_list
