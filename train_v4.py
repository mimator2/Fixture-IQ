"""
Standalone training script: Model B v4b_no_competition
Reproduces the notebook pipeline and saves artifacts for the Streamlit dashboard.
"""
import warnings, sys
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import OneHotEncoder
from sklearn.metrics import (
    roc_auc_score, average_precision_score, f1_score,
    precision_recall_curve, mean_squared_error, mean_absolute_error,
)
from xgboost import XGBClassifier, XGBRegressor
import joblib

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fatigue_monitor.src.feature_engineering import engineer_features, assign_player_role

warnings.filterwarnings("ignore")

BASE = Path(__file__).resolve().parent
MASTER_PATH = BASE / "XgBoost_model" / "Fixture_IQ_Data_Seasons_2022-2025.csv"
MODEL_DIR = BASE / "fatigue_monitor" / "models" / "model_b_v4b"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

print("=" * 64)
print("Model B v4 — Training Pipeline")
print("=" * 64)

# ── 1. Load data ──────────────────────────────────────────────────────────────
print("\n[1] Loading data...")
df = pd.read_csv(MASTER_PATH)
df["date"] = pd.to_datetime(df["date"])
print(f"  Shape: {df.shape[0]:,} rows x {df.shape[1]} columns")

# ── 2. Feature engineering ────────────────────────────────────────────────────
print("\n[2] Engineering features...")
df_fe = engineer_features(df)
print(f"  df_fe shape: {df_fe.shape}")

# ── 3. Stage 1 — Context-only regressor for residuals ─────────────────────────
print("\n[3] Stage 1 — Context-only regressor...")
STAGE1_CAT = ["competition", "player_position", "player_team", "opponent_team",
              "home_team", "away_team", "result"]
STAGE1_NUM = ["is_home", "season", "goals_for", "goals_against", "points"]

df_b = df_fe[
    (df_fe["rating"] > 0)
    & df_fe["next_api_rating"].notna()
    & (df_fe["minutes_played"] >= 45)
    & (df_fe["next_minutes_played"].fillna(0) >= 45)
].copy()

TARGET_S1 = "next_api_rating"
X_s1 = df_b[STAGE1_CAT + STAGE1_NUM]
y_s1 = df_b[TARGET_S1]
print(f"  Stage 1 rows: {len(df_b):,}")

s1_train_mask = df_b["season"] == 2022
s1_val_mask = df_b["season"] == 2023
s1_test_mask = df_b["season"] == 2024

num_pipe_s1 = Pipeline([("imp", SimpleImputer(strategy="median"))])
cat_pipe_s1 = Pipeline([
    ("imp", SimpleImputer(strategy="most_frequent")),
    ("ohe", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
])
pre_s1 = ColumnTransformer([
    ("num", num_pipe_s1, STAGE1_NUM),
    ("cat", cat_pipe_s1, STAGE1_CAT),
])

stage1 = XGBRegressor(
    n_estimators=1000, max_depth=4, learning_rate=0.03,
    subsample=0.8, colsample_bytree=0.8,
    reg_alpha=0.1, reg_lambda=1.0,
    objective="reg:squarederror", eval_metric="rmse",
    early_stopping_rounds=50, random_state=42, n_jobs=-1,
)

X_s1_train_t = pre_s1.fit_transform(X_s1[s1_train_mask])
X_s1_val_t = pre_s1.transform(X_s1[s1_val_mask])
stage1.fit(X_s1_train_t, y_s1[s1_train_mask],
           eval_set=[(X_s1_val_t, y_s1[s1_val_mask])], verbose=False)

X_s1_all_t = pre_s1.transform(X_s1)
df_b["predicted_next_rating_s1"] = stage1.predict(X_s1_all_t)
df_b["performance_residual"] = df_b["next_api_rating"] - df_b["predicted_next_rating_s1"]

rmse_s1 = float(np.sqrt(mean_squared_error(y_s1[s1_test_mask], stage1.predict(pre_s1.transform(X_s1[s1_test_mask])))))
print(f"  Stage 1 test RMSE: {rmse_s1:.4f}")

# ── 4. v4 Step B — Role assignment and target ────────────────────────────────
print("\n[4] v4 Step B — Role and target construction...")
df_v4 = df_fe[
    (df_fe["player_position"] != "G")
    & (df_fe["minutes_played"] >= 45)
    & (df_fe["rating"] > 0)
    & (df_fe["next_minutes_played"].notna())
].copy()

df_v4 = df_v4.join(
    df_b[["performance_residual"]].rename(columns={"performance_residual": "_perf_res_v4"}),
    how="left",
)

df_v4["player_role_v4"] = assign_player_role(df_v4)

df_v4["performance_underperformance"] = (
    df_v4["_perf_res_v4"] < -0.5
).fillna(False).astype(int)

_m5 = df_v4["minutes_median_last_5"].fillna(0)
_m10 = df_v4["minutes_median_last_10"].fillna(0)
_next_min = df_v4["next_minutes_played"].fillna(0)
_next_sub = df_v4["next_is_substitute"].fillna(0).astype(int)

df_v4["role_adjusted_load_reduction"] = (
    ((_m5 >= 45) & (_next_min < (_m5 * 0.60)))
    | ((_m10 >= 60) & (_next_min < (_m10 * 0.55)))
    | ((_m10 >= 60) & (_next_sub == 1))
).astype(int)

TARGET_V4 = "fatigue_performance_risk_v4"
df_v4[TARGET_V4] = (
    (df_v4["performance_underperformance"] == 1)
    | (df_v4["role_adjusted_load_reduction"] == 1)
).astype(int)

_EXCLUDED_V4 = {"impact_sub", "rare_player"}
df_v4_model = df_v4[~df_v4["player_role_v4"].isin(_EXCLUDED_V4)].copy()

for _col, _fill in [("rest_days", 14), ("days_since_european_match", 14), ("squad_injured_count", 0)]:
    if _col in df_v4_model.columns:
        df_v4_model[f"{_col}_missing"] = df_v4_model[_col].isna().astype(int)
        df_v4_model[_col] = df_v4_model[_col].fillna(_fill)

print(f"  Modeling rows: {len(df_v4_model):,}")
print(f"  Target rate: {df_v4_model[TARGET_V4].mean():.3f}")

# ── 5. v4 Step C — Feature sets and preprocessing ────────────────────────────
print("\n[5] v4 Step C — Feature sets...")
_S2V4_NUM_CANDS = [
    "rest_days", "acwr_ratio", "consecutive_away_games", "high_congestion_flag",
    "matches_last_7d", "matches_last_14d", "matches_last_21d", "matches_last_28d",
    "min_last_7d", "min_last_14d", "min_last_21d", "min_last_28d",
    "starts_last_7d", "starts_last_14d", "starts_last_28d",
    "full_90s_last_7d", "full_90s_last_14d", "full_90s_last_28d",
    "short_rest_last_3_matches", "avg_rest_last_3_matches", "min_rest_last_3_matches",
    "matches_with_rest_le_3d_last_30d", "matches_with_rest_le_4d_last_30d", "matches_with_rest_le_6d_last_30d",
    "days_since_european_match", "matches_since_european_match",
    "duels_last_3_matches", "duels_last_14d",
    "tackles_last_3_matches", "tackles_last_14d",
    "fouls_last_3_matches", "fouls_last_14d",
    "dribbles_last_3_matches", "dribbles_last_14d",
    "cards_last_5_matches",
    "duels_total_position_z", "tackles_total_position_z",
    "fouls_committed_position_z", "minutes_played_position_z",
    "physical_load_index",
    "squad_injured_count", "squad_soft_tissue_count", "squad_avg_days_out",
    "returning_from_injury", "fixtures_missed_last_30d",
    "rest_days_missing", "days_since_european_match_missing", "squad_injured_count_missing",
    "ucl_minutes_last_7d", "ucl_minutes_last_14d", "ucl_minutes_last_21d",
    "ucl_starts_last_14d", "ucl_full90s_last_14d", "ucl_matches_last_30d",
    "days_since_last_ucl", "played_ucl_last_match",
    "cup_minutes_last_7d", "cup_minutes_last_14d", "cup_starts_last_14d",
    "cup_full90s_last_14d", "cup_matches_last_30d", "played_domestic_cup_last_match",
    "transition_ucl_to_pl", "transition_pl_to_ucl", "transition_cup_to_pl", "transition_pl_to_cup",
    "competition_switches_last_30d", "competitions_played_last_30d",
    "rest_days_after_ucl", "post_ucl_short_rest",
    "pl_after_ucl_with_short_rest", "ucl_full90_then_pl_short_rest",
    "minutes_last_21d_vs_player_avg", "minutes_last_21d_player_z",
    "full90_last_14d_vs_player_avg", "physical_load_last_14d_vs_player_avg",
    "starts_last_14d_vs_player_avg",
]

S2V4_NUM = [c for c in _S2V4_NUM_CANDS if c in df_v4_model.columns]
S2V4_CAT_B = [c for c in ["player_position"] if c in df_v4_model.columns]

print(f"  Numerical features: {len(S2V4_NUM)}")
print(f"  Categorical features: {S2V4_CAT_B}")

# Temporal splits
trn_v4 = df_v4_model["season"] == 2022
val_v4 = df_v4_model["season"] == 2023
tst_v4 = df_v4_model["season"] == 2024

y_v4_trn = df_v4_model.loc[trn_v4, TARGET_V4]
y_v4_val = df_v4_model.loc[val_v4, TARGET_V4]
y_v4_tst = df_v4_model.loc[tst_v4, TARGET_V4]

SPW_V4 = round(float((y_v4_trn == 0).sum()) / max(float((y_v4_trn == 1).sum()), 1.0), 2)

_num_pipe_v4 = Pipeline([("imp", SimpleImputer(strategy="median"))])
_cat_pipe_v4 = Pipeline([
    ("imp", SimpleImputer(strategy="most_frequent")),
    ("ohe", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
])

pre_s2v4b = ColumnTransformer([
    ("num", _num_pipe_v4, S2V4_NUM),
    ("cat", _cat_pipe_v4, S2V4_CAT_B),
], remainder="drop")

X_v4b_trn = df_v4_model.loc[trn_v4, S2V4_NUM + S2V4_CAT_B]
X_v4b_val = df_v4_model.loc[val_v4, S2V4_NUM + S2V4_CAT_B]
X_v4b_tst = df_v4_model.loc[tst_v4, S2V4_NUM + S2V4_CAT_B]

X_v4b_trn_t = pre_s2v4b.fit_transform(X_v4b_trn)
X_v4b_val_t = pre_s2v4b.transform(X_v4b_val)
X_v4b_tst_t = pre_s2v4b.transform(X_v4b_tst)

print(f"  Train: {trn_v4.sum():,}  Val: {val_v4.sum():,}  Test: {tst_v4.sum():,}")
print(f"  Risk rate train: {y_v4_trn.mean():.3f}  val: {y_v4_val.mean():.3f}  test: {y_v4_tst.mean():.3f}")
print(f"  scale_pos_weight: {SPW_V4}")

# ── 6. v4 Step D — Train v4b_no_competition ──────────────────────────────────
print("\n[6] v4 Step D — Training v4b_no_competition...")

clf = XGBClassifier(
    n_estimators=400, max_depth=4, learning_rate=0.05,
    min_child_weight=5, subsample=0.75, colsample_bytree=0.75,
    reg_alpha=1.0, reg_lambda=5.0,
    scale_pos_weight=SPW_V4,
    objective="binary:logistic", eval_metric="aucpr",
    early_stopping_rounds=50, random_state=42, n_jobs=-1, verbosity=0,
)

clf.fit(X_v4b_trn_t, y_v4_trn, eval_set=[(X_v4b_val_t, y_v4_val)], verbose=False)

p_tr = clf.predict_proba(X_v4b_trn_t)[:, 1]
p_va = clf.predict_proba(X_v4b_val_t)[:, 1]
p_te = clf.predict_proba(X_v4b_tst_t)[:, 1]

prc, rec, thr = precision_recall_curve(y_v4_tst, p_te)
f1s = 2 * prc * rec / (prc + rec + 1e-10)
best_thr = float(thr[np.argmax(f1s[:-1])]) if len(thr) else 0.5

test_auc = roc_auc_score(y_v4_tst, p_te)
test_auc_pr = average_precision_score(y_v4_tst, p_te)
test_base = float(y_v4_tst.mean())

print(f"  Test AUC-ROC: {test_auc:.3f}")
print(f"  Test AUC-PR:  {test_auc_pr:.3f}")
print(f"  Test base:    {test_base:.3f}")
print(f"  Best thr:     {best_thr:.3f}")

# ── 7. v4 Policy ──────────────────────────────────────────────────────────────
print("\n[7] Defining operating policy...")
OPERATING_POLICY_V4 = {
    "name": "balanced_monitoring",
    "core_starter_threshold": 0.45,
    "rotation_player_threshold": 0.50,
    "intent": "monitoring_support",
    "message": (
        "Flag indicates workload-associated risk for monitoring, "
        "not definitive fatigue diagnosis."
    ),
}

# ── 8. Save artifacts ─────────────────────────────────────────────────────────
print(f"\n[8] Saving artifacts to {MODEL_DIR}...")
joblib.dump(clf, MODEL_DIR / "xgb_model.pkl")
joblib.dump(pre_s2v4b, MODEL_DIR / "preprocessor.pkl")
joblib.dump(S2V4_NUM, MODEL_DIR / "num_features.pkl")
joblib.dump(S2V4_CAT_B, MODEL_DIR / "cat_features.pkl")
joblib.dump(OPERATING_POLICY_V4, MODEL_DIR / "policy.pkl")

# Metadata
import datetime
metadata = {
    "training_date": datetime.datetime.now().isoformat(),
    "model": "Model B v4b_no_competition",
    "test_auc_roc": float(test_auc),
    "test_auc_pr": float(test_auc_pr),
    "test_base_rate": float(test_base),
    "num_features": len(S2V4_NUM),
    "cat_features": S2V4_CAT_B,
    "policy": OPERATING_POLICY_V4,
}
with open(MODEL_DIR / "metadata.json", "w") as f:
    import json
    json.dump(metadata, f, indent=2, default=str)

print(f"\n{'=' * 64}")
print("Training complete. Artifacts saved:")
for f in MODEL_DIR.iterdir():
    print(f"  {f.name}")
print("=" * 64)
