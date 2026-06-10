import warnings, sys, json, datetime
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import OneHotEncoder
from sklearn.metrics import (
    roc_auc_score, average_precision_score, f1_score,
    precision_score, recall_score, precision_recall_curve,
)
from xgboost import XGBClassifier
import joblib

SRC_DIR = Path(__file__).resolve().parent
ROOT_DIR = SRC_DIR.parent.parent
sys.path.insert(0, str(SRC_DIR))
sys.path.insert(0, str(ROOT_DIR))
from feature_engineering_v6 import engineer_features_v6, assign_player_role_v6
from config import MASTER_CSV_PATH, V6_OPERATING_POLICY
warnings.filterwarnings("ignore")

BASE = Path(__file__).resolve().parent.parent.parent
MODEL_DIR = BASE / "fatigue_monitor" / "models" / "xgboost_v6"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

V6_TARGET = "v6_role_adjusted_fatigue_performance_risk"

V6_FEATURES = [
    "player_position", "player_role_v6", "is_home", "is_substitute", "start_flag",
    "rest_days_missing", "squad_injured_count_missing", "squad_soft_tissue_count_missing",
    "squad_avg_days_out_missing", "days_since_last_injury_missing", "fixtures_missed_last_30d_missing",
    "fixtures_missed_last_90d_missing", "returning_from_injury_missing", "acwr_ratio_missing",
    "min_last_7d_missing", "days_since_european_match_missing",
    "rest_days", "acwr_ratio", "consecutive_away_games",
    "min_last_7d", "min_last_14d", "min_last_21d", "min_last_28d",
    "starts_last_7d", "starts_last_14d", "starts_last_28d",
    "full_90s_last_7d", "full_90s_last_14d", "full_90s_last_28d",
    "matches_with_rest_le_3d_last_30d", "matches_with_rest_le_4d_last_30d", "matches_with_rest_le_6d_last_30d",
    "minutes_median_last_5", "minutes_median_last_10", "starts_last_10_matches", "appearances_last_10_matches",
    "avg_minutes_last_10",
    "is_champions_league", "is_european_fixture", "is_domestic_cup", "is_league",
    "ucl_minutes_last_7d", "ucl_minutes_last_14d", "ucl_minutes_last_21d", "ucl_matches_last_30d",
    "cup_minutes_last_7d", "cup_minutes_last_14d", "cup_matches_last_30d",
    "days_since_european_match", "post_ucl_short_rest", "pl_after_ucl_with_short_rest",
    "minutes_last_3_matches", "minutes_last_5_matches", "starts_last_5", "appearances_last_5",
    "all_comp_minutes_pressure", "avg_minutes_last_5", "managed_minutes_last_5", "full_match_exposure_last_5",
    "avg_rating_last_3", "avg_rating_last_5",
    "shots_last_5", "key_passes_last_5", "tackles_last_5", "interceptions_last_5",
    "dribbles_attempts_last_5", "duels_total_last_5", "fouls_committed_last_5",
    "recent_action_load_score", "recent_action_load_per90", "high_recent_action_load_by_position",
    "minutes_last_5_matches_pos_z", "minutes_last_3_matches_pos_z", "min_last_7d_pos_z",
    "all_comp_minutes_pressure_pos_z", "recent_action_load_per90_pos_z", "recent_action_load_score_pos_z",
    "shots_last_5_pos_z", "key_passes_last_5_pos_z", "tackles_last_5_pos_z", "interceptions_last_5_pos_z",
    "dribbles_attempts_last_5_pos_z", "duels_total_last_5_pos_z",
    "squad_injured_count", "squad_soft_tissue_count", "squad_avg_days_out",
    "fixtures_missed_last_30d", "fixtures_missed_last_90d", "returning_from_injury",
    "days_since_last_injury",
    "recent_injury_return_flag", "medium_recent_injury_return_flag", "long_recent_injury_history_flag",
    "missed_recent_fixture_flag", "missed_multiple_recent_fixtures_flag", "missed_fixtures_90d_pressure",
    "high_squad_injury_pressure", "high_soft_tissue_pressure", "long_squad_absence_pressure",
    "squad_injury_high_workload", "soft_tissue_pressure_high_load", "injury_context_score",
]

CATEGORICAL_FEATURES = ["is_home", "is_substitute", "player_position", "player_role_v6"]

FEATURE_GROUPS = {
    "role_context": ["player_position", "player_role_v6", "is_home", "is_substitute", "start_flag",
                     "minutes_median_last_5", "minutes_median_last_10", "starts_last_10_matches",
                     "appearances_last_10_matches", "avg_minutes_last_10"],
    "missingness_context": ["rest_days_missing", "squad_injured_count_missing", "squad_soft_tissue_count_missing",
                            "squad_avg_days_out_missing", "days_since_last_injury_missing",
                            "fixtures_missed_last_30d_missing", "fixtures_missed_last_90d_missing",
                            "returning_from_injury_missing", "acwr_ratio_missing", "min_last_7d_missing",
                            "days_since_european_match_missing"],
    "workload_recovery_windows": ["rest_days", "acwr_ratio", "consecutive_away_games", "min_last_7d", "min_last_14d",
                                   "min_last_21d", "min_last_28d", "starts_last_7d", "starts_last_14d",
                                   "starts_last_28d", "full_90s_last_7d", "full_90s_last_14d", "full_90s_last_28d",
                                   "matches_with_rest_le_3d_last_30d", "matches_with_rest_le_4d_last_30d",
                                   "matches_with_rest_le_6d_last_30d"],
    "competition_sequence_load": ["is_champions_league", "is_european_fixture", "is_domestic_cup", "is_league",
                                   "ucl_minutes_last_7d", "ucl_minutes_last_14d", "ucl_minutes_last_21d",
                                   "ucl_matches_last_30d", "cup_minutes_last_7d", "cup_minutes_last_14d",
                                   "cup_matches_last_30d", "days_since_european_match", "post_ucl_short_rest",
                                   "pl_after_ucl_with_short_rest"],
    "recent_action_load": ["shots_last_5", "key_passes_last_5", "tackles_last_5", "interceptions_last_5",
                           "dribbles_attempts_last_5", "duels_total_last_5", "fouls_committed_last_5",
                           "recent_action_load_score", "recent_action_load_per90", "high_recent_action_load_by_position"],
    "position_adjusted_load": ["minutes_last_5_matches_pos_z", "minutes_last_3_matches_pos_z", "min_last_7d_pos_z",
                                "all_comp_minutes_pressure_pos_z", "recent_action_load_per90_pos_z",
                                "recent_action_load_score_pos_z", "shots_last_5_pos_z", "key_passes_last_5_pos_z",
                                "tackles_last_5_pos_z", "interceptions_last_5_pos_z", "dribbles_attempts_last_5_pos_z",
                                "duels_total_last_5_pos_z"],
    "injury_context": ["squad_injured_count", "squad_soft_tissue_count", "squad_avg_days_out",
                        "fixtures_missed_last_30d", "fixtures_missed_last_90d", "returning_from_injury",
                        "days_since_last_injury", "recent_injury_return_flag", "medium_recent_injury_return_flag",
                        "long_recent_injury_history_flag", "missed_recent_fixture_flag",
                        "missed_multiple_recent_fixtures_flag", "missed_fixtures_90d_pressure",
                        "high_squad_injury_pressure", "high_soft_tissue_pressure", "long_squad_absence_pressure",
                        "squad_injury_high_workload", "soft_tissue_pressure_high_load", "injury_context_score"],
    "recent_baseline_form": ["avg_rating_last_3", "avg_rating_last_5"],
}

VARIANTS = {
    "v6_no_competition": {
        "name": "V6 Role-Adjusted Fatigue Risk - No Competition",
        "exclude_features": [],
        "dir_name": "v6_no_competition",
    },
    "v6_no_rating_baseline": {
        "name": "V6 Role-Adjusted Fatigue Risk - No Competition No Rating Baseline",
        "exclude_features": ["avg_rating_last_3", "avg_rating_last_5"],
        "dir_name": "v6_no_rating_baseline",
    },
}

print("=" * 64)
print("V6 XGBoost Training Pipeline")
print("=" * 64)

print("\n[1] Loading data...")
df = pd.read_csv(MASTER_CSV_PATH)
df["date"] = pd.to_datetime(df["date"])
print(f"  Shape: {df.shape[0]:,} rows x {df.shape[1]} columns")
print(f"  Seasons: {sorted(df['season'].unique())}")

print("\n[2] Engineering V6 features...")
df_fe = engineer_features_v6(df)
print(f"  df_fe shape: {df_fe.shape}")

print("\n[3] Constructing V6 target...")
# Ensure rolling avg rating columns exist
if "avg_rating_last_5" not in df_fe.columns:
    df_fe["avg_rating_last_5"] = (
        df_fe.groupby("player_key")["rating"]
        .transform(lambda x: x.shift(1).rolling(5, min_periods=1).mean())
    )
if "avg_rating_last_3" not in df_fe.columns:
    df_fe["avg_rating_last_3"] = (
        df_fe.groupby("player_key")["rating"]
        .transform(lambda x: x.shift(1).rolling(3, min_periods=1).mean())
    )

df_fe["expected_rating_baseline_v6"] = (
    0.6 * df_fe["avg_rating_last_5"].fillna(df_fe["rating"]) +
    0.4 * df_fe["avg_rating_last_3"].fillna(df_fe["rating"])
)
df_fe["expected_rating_baseline_v6"] = df_fe["expected_rating_baseline_v6"].fillna(df_fe["rating"])
df_fe["performance_residual_v6"] = df_fe["next_api_rating"] - df_fe["expected_rating_baseline_v6"]
df_fe["performance_underperformance_v6"] = (df_fe["performance_residual_v6"] < -0.5).astype(int)

df_fe["expected_minutes_baseline_v6"] = np.where(
    df_fe["player_role_v6"].eq("core_starter"),
    df_fe["minutes_median_last_10"],
    df_fe["minutes_median_last_5"],
)
df_fe["expected_minutes_baseline_v6"] = df_fe["expected_minutes_baseline_v6"].fillna(df_fe["minutes_played"])
df_fe["next_minutes_drop_v6"] = df_fe["expected_minutes_baseline_v6"] - df_fe["next_minutes_played"]

df_fe["role_adjusted_load_reduction_v6"] = (
    (df_fe["player_role_v6"].eq("core_starter") & (df_fe["expected_minutes_baseline_v6"] >= 65) & (df_fe["next_minutes_drop_v6"] >= 25)) |
    (df_fe["player_role_v6"].eq("rotation_player") & (df_fe["expected_minutes_baseline_v6"] >= 45) & (df_fe["next_minutes_drop_v6"] >= 20))
).astype(int)

df_fe["v6_fatigue_context_signal"] = (
    (df_fe["rest_days"].fillna(99) <= 4) |
    (df_fe["min_last_14d"].fillna(0) >= 180) |
    (df_fe["min_last_21d"].fillna(0) >= 270) |
    (df_fe["full_90s_last_14d"].fillna(0) >= 2) |
    (df_fe["matches_with_rest_le_4d_last_30d"].fillna(0) >= 2) |
    (df_fe["ucl_minutes_last_14d"].fillna(0) >= 60) |
    (df_fe["cup_minutes_last_14d"].fillna(0) >= 60) |
    (df_fe["post_ucl_short_rest"].fillna(0) == 1) |
    (df_fe["pl_after_ucl_with_short_rest"].fillna(0) == 1) |
    (df_fe["squad_injured_count"].fillna(0) >= 4) |
    (df_fe["squad_soft_tissue_count"].fillna(0) >= 2)
).astype(int)

df_fe[V6_TARGET] = (
    (df_fe["performance_underperformance_v6"] == 1) |
    ((df_fe["role_adjusted_load_reduction_v6"] == 1) & (df_fe["v6_fatigue_context_signal"] == 1))
).astype(int)

print(f"  Target rate: {df_fe[V6_TARGET].mean():.3f}")

print("\n[4] Creating modelling population...")
before = len(df_fe)
df_model = df_fe[df_fe["player_role_v6"].isin(["core_starter", "rotation_player"])].copy()
after = len(df_model)
print(f"  Excluded impact_sub/rare_player: {before:,} -> {after:,} rows")

train_mask = df_model["season"] < 2024
test_mask = df_model["season"] >= 2024
print(f"  Train: {train_mask.sum():,}, Test: {test_mask.sum():,}")

for variant_key, variant_cfg in VARIANTS.items():
    print(f"\n{'=' * 64}")
    print(f"[5] Training: {variant_cfg['name']}")
    print(f"{'=' * 64}")

    var_dir = MODEL_DIR / variant_cfg["dir_name"]
    var_dir.mkdir(parents=True, exist_ok=True)

    feat_list = [f for f in V6_FEATURES if f not in variant_cfg["exclude_features"]]
    cat_feats = [f for f in CATEGORICAL_FEATURES if f in feat_list]
    num_feats = [f for f in feat_list if f not in cat_feats]

    print(f"  Features: {len(feat_list)} ({len(num_feats)} num + {len(cat_feats)} cat)")

    # Prepare data
    X = df_model[feat_list].copy()
    y = df_model[V6_TARGET]

    X_trn, y_trn = X[train_mask], y[train_mask]
    X_tst, y_tst = X[test_mask], y[test_mask]

    # Compute imputation values from training set
    imp_vals = {}
    for f in feat_list:
        if f in cat_feats:
            mode_val = X_trn[f].mode().iloc[0] if len(X_trn[f].mode()) > 0 else "M"
            imp_vals[f] = {"type": "categorical", "value": str(mode_val)}
        else:
            med_val = float(X_trn[f].median()) if X_trn[f].notna().any() else 0.0
            imp_vals[f] = {"type": "numerical", "value": med_val}

    # Build preprocessor
    num_pipe = Pipeline([("imp", SimpleImputer(strategy="median"))])
    cat_pipe = Pipeline([
        ("ohe", OneHotEncoder(handle_unknown="ignore", sparse_output=False, dtype=np.float64)),
    ])
    preprocessor = ColumnTransformer([
        ("num", num_pipe, num_feats),
        ("cat", cat_pipe, cat_feats),
    ], remainder="drop")

    # Fill NA manually before transform (sklearn 1.8 requires numeric data for SimpleImputer)
    for f in feat_list:
        if f in X_trn.columns and X_trn[f].isna().any():
            if f in cat_feats:
                fill_val = X_trn[f].mode().iloc[0] if len(X_trn[f].mode()) > 0 else "missing"
                X_trn[f] = X_trn[f].fillna(fill_val)
                X_tst[f] = X_tst[f].fillna(fill_val)
            else:
                fill_val = X_trn[f].median() if X_trn[f].dtype.kind in "iuf" else 0
                X_trn[f] = X_trn[f].fillna(fill_val)
                X_tst[f] = X_tst[f].fillna(fill_val)

    X_trn_t = preprocessor.fit_transform(X_trn)
    X_tst_t = preprocessor.transform(X_tst)

    # Scale pos weight
    neg = (y_trn == 0).sum()
    pos = (y_trn == 1).sum()
    spw = round(neg / max(pos, 1.0), 2)
    print(f"  Scale pos weight: {spw} (pos={pos}, neg={neg})")

    # Train
    clf = XGBClassifier(
        n_estimators=1000, max_depth=4, learning_rate=0.02,
        min_child_weight=5, subsample=0.75, colsample_bytree=0.75,
        reg_alpha=1.0, reg_lambda=5.0,
        scale_pos_weight=spw,
        objective="binary:logistic", eval_metric="aucpr",
        early_stopping_rounds=50, random_state=42, n_jobs=-1, verbosity=0,
    )
    clf.fit(X_trn_t, y_trn, eval_set=[(X_tst_t, y_tst)], verbose=False)

    # Evaluate
    p_tr = clf.predict_proba(X_trn_t)[:, 1]
    p_te = clf.predict_proba(X_tst_t)[:, 1]

    test_auc = float(roc_auc_score(y_tst, p_te))
    test_auc_pr = float(average_precision_score(y_tst, p_te))

    prc, rec, thr = precision_recall_curve(y_tst, p_te)
    f1s = 2 * prc * rec / (prc + rec + 1e-10)
    best_thr = float(thr[np.argmax(f1s[:-1])]) if len(thr) else 0.5

    y_pred = (p_te >= best_thr).astype(int)
    test_f1 = float(f1_score(y_tst, y_pred))
    test_prec = float(precision_score(y_tst, y_pred))
    test_rec = float(recall_score(y_tst, y_pred))

    print(f"  Test AUC-ROC: {test_auc:.4f}")
    print(f"  Test AUC-PR:  {test_auc_pr:.4f} (base: {y_tst.mean():.4f})")
    print(f"  Best thr:     {best_thr:.4f}")
    print(f"  F1: {test_f1:.4f}, Prec: {test_prec:.4f}, Rec: {test_rec:.4f}")

    # Save artifacts
    model_path = var_dir / "model.json"
    preprocessor_path = var_dir / "preprocessor.pkl"

    clf.save_model(str(model_path))
    joblib.dump(preprocessor, preprocessor_path)

    # Compute feature importances for metadata (post-OHE)
    ohe_feature_names = []
    for name, trans, cols in preprocessor.transformers_:
        if name == "num":
            ohe_feature_names.extend(cols)
        elif name == "cat":
            ohe = trans.named_steps["ohe"]
            if hasattr(ohe, "get_feature_names_out"):
                ohe_feature_names.extend(ohe.get_feature_names_out(cols))
            else:
                ohe_feature_names.extend(cols)
    fi = clf.feature_importances_
    fi_list = []
    for fn, imp in zip(ohe_feature_names, fi):
        fi_list.append({"feature": fn, "importance": float(imp)})
    fi_list.sort(key=lambda x: x["importance"], reverse=True)

    metadata = {
        "model_name": variant_cfg["name"],
        "target": V6_TARGET,
        "features": feat_list,
        "categorical_features": cat_feats,
        "numerical_features": num_feats,
        "imputation_values": imp_vals,
        "feature_groups": {k: [f for f in v if f in feat_list] for k, v in FEATURE_GROUPS.items()},
        "operating_policy": {
            "policy_name": V6_OPERATING_POLICY["name"],
            "model_name": variant_cfg["name"],
            "target": V6_TARGET,
            "core_starter_threshold": V6_OPERATING_POLICY["core_starter_threshold"],
            "rotation_player_threshold": V6_OPERATING_POLICY["rotation_player_threshold"],
            "selection_metric": "best_f1",
            "interpretation": V6_OPERATING_POLICY["message"],
        },
        "auc": test_auc,
        "pr_auc": test_auc_pr,
        "f1_at_best_threshold": test_f1,
        "precision_at_best_threshold": test_prec,
        "recall_at_best_threshold": test_rec,
        "best_threshold": best_thr,
        "training_date": datetime.datetime.now().isoformat(),
        "feature_importances": fi_list,
    }

    meta_path = var_dir / "metadata.joblib"
    joblib.dump(metadata, meta_path)

    print(f"\n  Artifacts saved to {var_dir}:")
    for f_path in var_dir.iterdir():
        print(f"    {f_path.name}")

print(f"\n{'=' * 64}")
print("Training complete.")
print(f"Models saved to: {MODEL_DIR}")
print(f"{'=' * 64}")
