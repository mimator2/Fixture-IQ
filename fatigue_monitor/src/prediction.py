import numpy as np
import pandas as pd
import joblib
from fatigue_monitor.src.config import (
    MODEL_PATH, PREPROCESSOR_PATH, NUM_FEATURES_PATH,
    CAT_FEATURES_PATH, POLICY_PATH, OPERATING_POLICY,
    RISK_BANDS, RISK_LABELS,
)
from fatigue_monitor.src.feature_engineering import engineer_features, assign_player_role


def load_artifacts():
    model = joblib.load(MODEL_PATH)
    preprocessor = joblib.load(PREPROCESSOR_PATH)
    num_features = joblib.load(NUM_FEATURES_PATH)
    cat_features = joblib.load(CAT_FEATURES_PATH)
    return model, preprocessor, num_features, cat_features


def predict_fatigue_risk(df_raw, model=None, preprocessor=None, num_features=None, cat_features=None):
    if model is None:
        model, preprocessor, num_features, cat_features = load_artifacts()

    df = engineer_features(df_raw)

    df["player_position"] = df["player_position"].astype(str)
    df = df[df["player_position"] != "G"].copy()

    df["player_role_v4"] = assign_player_role(df)

    df_model = df[df["player_role_v4"].isin(["core_starter", "rotation_player"])].copy()

    available_num = [c for c in num_features if c in df_model.columns]
    available_cat = [c for c in cat_features if c in df_model.columns]
    missing_num = set(num_features) - set(available_num)
    missing_cat = set(cat_features) - set(available_cat)
    if missing_num:
        for c in missing_num:
            df_model[c] = np.nan
        available_num = num_features
    if missing_cat:
        for c in missing_cat:
            df_model[c] = ""
        available_cat = cat_features

    X = df_model[available_num + available_cat]
    X_t = preprocessor.transform(X)

    df_model["risk_score_v4"] = model.predict_proba(X_t)[:, 1]

    df_model["monitoring_threshold_v4"] = np.where(
        df_model["player_role_v4"] == "core_starter",
        OPERATING_POLICY["core_starter_threshold"],
        OPERATING_POLICY["rotation_player_threshold"],
    )

    df_model["monitoring_flag_v4"] = (
        df_model["risk_score_v4"] >= df_model["monitoring_threshold_v4"]
    ).astype(int)

    df_model["risk_band_v4"] = pd.cut(
        df_model["risk_score_v4"],
        bins=RISK_BANDS,
        labels=RISK_LABELS,
    )

    df_model["explanation_v4"] = _generate_explanations(df_model, model, num_features, cat_features)

    return df_model


def _generate_explanations(df, model, num_features, cat_features):
    n_features = len(num_features) + len(cat_features)
    importances = model.feature_importances_[:n_features]
    all_features = num_features + cat_features
    feat_imp = pd.Series(importances, index=all_features).sort_values(ascending=False)

    explanations = []
    for _, row in df.iterrows():
        reasons = []
        score = row["risk_score_v4"]

        for feat in feat_imp.head(10).index:
            if feat in row and not pd.isna(row[feat]):
                val = row[feat]
                if feat == "matches_with_rest_le_4d_last_30d" and val >= 3:
                    reasons.append(f"{int(val)} matches with ≤4d rest (last 30d)")
                elif feat == "matches_with_rest_le_6d_last_30d" and val >= 4:
                    reasons.append(f"{int(val)} matches with ≤6d rest (last 30d)")
                elif feat == "full_90s_last_14d" and val >= 3:
                    reasons.append(f"{int(val)} full-90s in last 14d")
                elif feat == "full_90s_last_28d" and val >= 5:
                    reasons.append(f"{int(val)} full-90s in last 28d")
                elif feat == "rest_days" and val <= 3:
                    reasons.append(f"Only {int(val)}d rest")
                elif feat == "starts_last_14d" and val >= 3:
                    reasons.append(f"{int(val)} starts in last 14d")
                elif feat == "ucl_matches_last_30d" and val >= 2:
                    reasons.append(f"{int(val)} UCL matches (last 30d)")
                elif feat == "ucl_minutes_last_14d" and val >= 90:
                    reasons.append(f"{int(val)} UCL minutes (last 14d)")
                elif feat == "pl_after_ucl_with_short_rest" and val == 1:
                    reasons.append("PL match after UCL with short rest")
                elif feat == "post_ucl_short_rest" and val == 1:
                    reasons.append("Post-UCL short rest")
                elif feat == "squad_injured_count" and val >= 3:
                    reasons.append(f"{int(val)} squad injuries")
                elif feat == "competition_switches_last_30d" and val >= 3:
                    reasons.append(f"{int(val)} competition switches (last 30d)")
                elif feat == "physical_load_index" and val >= 0.7:
                    reasons.append(f"High physical load ({val:.2f})")

        if not reasons:
            if score >= 0.45:
                reasons.append("Elevated workload pattern")
            else:
                reasons.append("Within normal range")

        explanations.append("; ".join(reasons[:5]))

    return explanations
