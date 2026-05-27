"""
FixtureIQ - XGBoost Model Training
===================================
Trains an XGBoost classifier using all available data (2022-23 to 2024-25)
with real injury records as the ground-truth target.
"""

import json
import pickle
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

import xgboost as xgb

_root = Path(__file__).resolve().parent.parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from src.config.paths import data_dir, model_dir, results_dir
from src.features.engineering import engineer_features, TEAM_NAME_MAP, UCL_TEAMS_BY_SEASON, SEASON_MAP
from src.features.target import define_target, load_injury_data, merge_injury_target
from src.models.evaluate import evaluate_model

warnings.filterwarnings("ignore")

BASE = Path(__file__).resolve().parent.parent.parent

SEASONS = ["2022-2023", "2023-2024", "2024-2025"]
SEASON_KEYS = {"2022-2023": "2022_2023", "2023-2024": "2023_2024", "2024-2025": "2024_2025"}

CORE_FEATURES = [
    "rest_days", "high_congestion_flag", "min_last_7d", "acwr_ratio",
    "minutesPlayed", "consecutive_away_games", "lineup_churn",
    "is_away", "position_code", "season_ordinal",
]

PERF_FEATURES = [
    "rating", "totalPass", "accuratePass", "totalTackle", "wonTackle",
    "duelWon", "duelLost", "aerialWon", "aerialLost",
    "expectedGoals", "expectedAssists", "keyPass",
    "totalShots", "onTargetScoringAttempt", "fouls", "wasFouled",
    "touches", "dispossessed", "bigChanceCreated",
]

CONTEXT_FEATURES = [
    "elo", "team_xg", "team_xga", "is_ucl_match", "is_pl_match",
    "is_ucl_team",
]


def load_master_csv(season: str) -> pd.DataFrame | None:
    path = data_dir() / season / "sofascore_dynamic" / "fixtureiq_dynamic_master.csv"
    if not path.exists():
        print(f"  [SKIP] {season}: {path} not found")
        return None
    df = pd.read_csv(path, low_memory=False)
    df["season_tag"] = season
    df["season_key"] = SEASON_KEYS[season]
    df["season"] = df["season_key"]
    print(f"  [OK]   {season}: {len(df)} rows, {df['name'].nunique()} players, {df['teamName'].nunique()} teams")
    return df


def standardise_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "match_date_str" not in df.columns and "date" in df.columns:
        df.rename(columns={"date": "match_date_str"}, inplace=True)
    df["match_date"] = pd.to_datetime(df["match_date_str"], errors="coerce")
    df["source"] = "sofascore_dynamic"

    cols_rename = {}
    if "teamName" not in df.columns and "team_name" in df.columns:
        cols_rename["team_name"] = "teamName"
    df.rename(columns=cols_rename, inplace=True)

    df["team_name"] = df["teamName"].map(TEAM_NAME_MAP).fillna(df["teamName"])
    df["is_ucl_team"] = df["team_name"].isin(UCL_TEAMS_BY_SEASON.get(df["season_key"].iloc[0] if len(df) else "", set()))

    if "rating" in df.columns:
        df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
    if "minutesPlayed" in df.columns:
        df["minutesPlayed"] = pd.to_numeric(df["minutesPlayed"], errors="coerce").fillna(0)
    if "elo" in df.columns:
        df["elo"] = pd.to_numeric(df["elo"], errors="coerce")
    if "team_xg" in df.columns:
        df["team_xg"] = pd.to_numeric(df["team_xg"], errors="coerce")
    if "team_xga" in df.columns:
        df["team_xga"] = pd.to_numeric(df["team_xga"], errors="coerce")

    if "competition" in df.columns:
        df["is_ucl_match"] = df["competition"].astype(str).str.contains("Champions", case=False, na=False).astype(int)
        df["is_pl_match"] = df["competition"].astype(str).str.contains("Premier", case=False, na=False).astype(int)
    else:
        df["is_ucl_match"] = 0
        df["is_pl_match"] = 1

    if "position" in df.columns:
        pos_map = {"D": 0, "M": 1, "F": 2, "G": 3, "DF": 0, "MF": 1, "FW": 2, "GK": 3}
        df["position_code"] = df["position"].map(pos_map).fillna(1).astype(int)
    else:
        df["position_code"] = 1

    for col in ["rating", "elo", "team_xg", "team_xga"]:
        if col in df.columns:
            df[col] = df[col].fillna(0)

    return df


def load_all_data() -> pd.DataFrame:
    print("=" * 70)
    print("LOADING ALL AVAILABLE DATA")
    print("=" * 70)

    all_frames = []
    for season in SEASONS:
        df = load_master_csv(season)
        if df is not None:
            df = standardise_columns(df)
            all_frames.append(df)

    if not all_frames:
        print("ERROR: No master CSV data found.")
        return pd.DataFrame()

    df_all = pd.concat(all_frames, ignore_index=True, sort=False)
    print(f"\nTotal: {len(df_all)} rows across {len(all_frames)} seasons")
    print(f"Players: {df_all['name'].nunique()}, Teams: {df_all['team_name'].nunique()}")
    return df_all


def prepare_model_matrix(df):
    feature_cols = CORE_FEATURES + PERF_FEATURES + CONTEXT_FEATURES
    available = [c for c in feature_cols if c in df.columns]
    missing = set(feature_cols) - set(available)
    if missing:
        print(f"  [INFO] Missing features (filled with 0): {sorted(missing)}")
        for c in missing:
            df[c] = 0
            available.append(c)

    X = df[available].copy()
    X = X.fillna(0)

    y_proxy = df["fatigue_risk"].values if "fatigue_risk" in df.columns else np.zeros(len(df))
    y_injury = df["injury_flag"].values if "injury_flag" in df.columns else np.zeros(len(df))

    return X, y_proxy, y_injury, available


def train_xgboost(X, y, feature_names, scale_pos_weight=None):
    print("\n" + "=" * 70)
    print("XGBOOST MODEL TRAINING")
    print("=" * 70)

    if scale_pos_weight is None:
        scale_pos_weight = (y == 0).sum() / max((y == 1).sum(), 1)
    print(f"  scale_pos_weight: {scale_pos_weight:.2f}  (pos class: {y.mean()*100:.1f}%)")

    n_train = int(len(X) * 0.65)
    n_val = int(len(X) * 0.15)

    X_train, y_train = X.iloc[:n_train], y[:n_train]
    X_val, y_val = X.iloc[n_train:n_train + n_val], y[n_train:n_train + n_val]
    X_test, y_test = X.iloc[n_train + n_val:], y[n_train + n_val:]

    print(f"  Train: {len(X_train)} samples ({y_train.mean()*100:.1f}% positive)")
    print(f"  Val:   {len(X_val)} samples ({y_val.mean()*100:.1f}% positive)")
    print(f"  Test:  {len(X_test)} samples ({y_test.mean()*100:.1f}% positive)")

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)
    X_test_scaled = scaler.transform(X_test)

    model = xgb.XGBClassifier(
        objective="binary:logistic",
        scale_pos_weight=scale_pos_weight,
        n_estimators=500,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_alpha=0.1,
        reg_lambda=1.0,
        eval_metric="aucpr",
        early_stopping_rounds=30,
        random_state=42,
        verbosity=0,
        use_label_encoder=False,
    )

    model.fit(
        X_train_scaled, y_train,
        eval_set=[(X_val_scaled, y_val)],
        verbose=False,
    )

    best_iter = model.best_iteration + 1 if hasattr(model, "best_iteration") else model.get_booster().best_iteration
    print(f"\n  Best iteration: {best_iter}")

    return model, scaler, (X_train_scaled, X_val_scaled, X_test_scaled), (y_train, y_val, y_test)


def main():
    print("\n" + "=" * 70)
    print("FIXTURE IQ - FATIGUE/INJURY RISK MODEL")
    print("=" * 70)

    df_raw = load_all_data()
    if len(df_raw) == 0:
        print("ERROR: No data loaded. Exiting.")
        sys.exit(1)

    print("\n--- Feature Engineering ---")
    df = engineer_features(df_raw)

    print("\n--- Proxy Target (fatigue_risk) ---")
    df = define_target(df)
    print(f"  fatigue_risk rate: {df['fatigue_risk'].mean()*100:.1f}%")

    print("\n--- Injury Target ---")
    inj = load_injury_data(data_dir())
    print(f"  Injury records loaded: {len(inj)} ({inj['is_injury'].sum()} genuine)")
    df = merge_injury_target(df, inj, window_days=14)
    print(f"  injury_flag rate: {df['injury_flag'].mean()*100:.2f}%")
    print(f"  Players with >=1 injury: {df[df['injury_flag']==1]['name'].nunique()}")

    X, y_proxy, y_injury, feature_names = prepare_model_matrix(df)
    print(f"\nModel matrix: {X.shape}, features: {len(feature_names)}")
    print(f"Features: {feature_names}")

    print("\n" + "=" * 70)
    print("TRAINING WITH INJURY TARGET (ground truth)")
    print("=" * 70)
    model_injury, scaler_injury, X_sets_inj, y_sets_inj = train_xgboost(X, y_injury, feature_names)

    X_train_scaled, X_val_scaled, X_test_scaled = X_sets_inj
    test_start_idx = len(X_train_scaled) + len(X_val_scaled)
    df_test = df.iloc[test_start_idx:].copy()

    print("\n" + "=" * 70)
    print("EVALUATION - INJURY TARGET MODEL")
    print("=" * 70)
    evaluate_model(model_injury, scaler_injury, X_sets_inj, y_sets_inj, feature_names, df_test, target_name="injury")

    print("\n" + "=" * 70)
    print("TRAINING WITH PROXY TARGET (fatigue_risk - for comparison)")
    print("=" * 70)
    model_proxy, scaler_proxy, X_sets_proxy, y_sets_proxy = train_xgboost(X, y_proxy, feature_names)

    print("\n" + "=" * 70)
    print("EVALUATION - PROXY TARGET MODEL")
    print("=" * 70)
    evaluate_model(model_proxy, scaler_proxy, X_sets_proxy, y_sets_proxy, feature_names, df_test, target_name="fatigue")

    MODELS_DIR = model_dir()
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR = results_dir()
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    model_path = MODELS_DIR / "fatigue_xgb_model.json"
    model_injury.save_model(str(model_path))
    print(f"\nModel (injury target) saved: {model_path}")

    scaler_path = MODELS_DIR / "preprocessor.pkl"
    with open(scaler_path, "wb") as f:
        pickle.dump({"scaler": scaler_injury, "feature_names": feature_names}, f)
    print(f"Scaler saved: {scaler_path}")

    feat_path = MODELS_DIR / "feature_columns.json"
    with open(feat_path, "w") as f:
        json.dump(feature_names, f, indent=2)
    print(f"Feature columns saved: {feat_path}")

    from sklearn.metrics import precision_recall_curve
    precisions, recalls, thresholds = precision_recall_curve(y_sets_inj[2], model_injury.predict_proba(X_sets_inj[2])[:, 1])
    f1_scores = 2 * (precisions * recalls) / (precisions + recalls + 1e-10)
    best_idx = np.argmax(f1_scores[:-1])
    best_threshold = thresholds[best_idx]

    print(f"\n  Best threshold (max F1): {best_threshold:.3f}")
    print(f"  F1: {f1_scores[best_idx]:.4f}, Precision: {precisions[best_idx]:.4f}, Recall: {recalls[best_idx]:.4f}")

    threshold_info = {"best_threshold": float(best_threshold)}
    with open(MODELS_DIR / "threshold.json", "w") as f:
        json.dump(threshold_info, f, indent=2)

    print("\n" + "=" * 70)
    print("DONE")
    print("=" * 70)


if __name__ == "__main__":
    main()
