from pathlib import Path

MODELS_DIR = Path(__file__).resolve().parent.parent / "models" 

V4B_MODEL_DIR = MODELS_DIR / "xgboost_v4b"
V4B_MODEL_PATH = V4B_MODEL_DIR / "xgboost_model_b_v4b_final.pkl"
V4B_PREPROCESSOR_PATH = V4B_MODEL_DIR / "xgboost_model_b_v4b_preprocessor.pkl"
V4B_NUM_FEATURES_PATH = V4B_MODEL_DIR / "xgboost_model_b_v4b_numeric_features.pkl"
V4B_CAT_FEATURES_PATH = V4B_MODEL_DIR / "xgboost_model_b_v4b_categorical_features.pkl"
V4B_METADATA_PATH = V4B_MODEL_DIR / "xgboost_model_b_v4b_metadata.json"
V4B_POLICY_PATH = V4B_MODEL_DIR / "xgboost_model_b_v4b_operating_policy.json"

V4B_OPERATING_POLICY = {
    "name": "balanced_monitoring",
    "core_starter_threshold": 0.45,
    "rotation_player_threshold": 0.50,
    "intent": "monitoring_support",
    "message": (
        "Flag indicates workload-associated risk for monitoring, "
        "not definitive fatigue diagnosis."
    ),
}

V4B_RISK_BANDS = [0, 0.35, 0.45, 0.55, 1.01]
V4B_RISK_LABELS = ["Low", "Medium", "High", "Very High"]
V4B_RISK_COLORS = {"Low": "#27ae60", "Medium": "#f39c12", "High": "#e74c3c", "Very High": "#8e44ad"}

MONITORING_FLAG_COLOR = {0: "#27ae60", 1: "#e74c3c"}
MONITORING_FLAG_LABEL = {0: "Clear", 1: "Monitor"}

ROLE_COLORS = {
    "core_starter": "#00BC8C",
    "rotation_player": "#636EFA",
    "impact_sub": "#FFA15A",
    "rare_player": "#AB63FA",
}

V4B_FEATURE_GROUPS = {
    "workload_recovery_windows": [
        "rest_days",
        "acwr_ratio",
        "consecutive_away_games",
        "min_last_7d",
        "min_last_14d",
        "min_last_21d",
        "min_last_28d",
        "starts_last_7d",
        "starts_last_14d",
        "starts_last_28d",
        "full_90s_last_7d",
        "full_90s_last_14d",
        "full_90s_last_28d",
        "short_rest_last_3_matches",
        "avg_rest_last_3_matches",
        "min_rest_last_3_matches",
        "matches_with_rest_le_3d_last_30d",
        "matches_with_rest_le_4d_last_30d",
        "matches_with_rest_le_6d_last_30d",
        "matches_last_7d",
        "matches_last_14d",
        "matches_last_21d",
        "matches_last_28d",
        "high_congestion_flag",
    ],
    "competition_sequence_load": [
        "ucl_minutes_last_7d",
        "ucl_minutes_last_14d",
        "ucl_minutes_last_21d",
        "ucl_starts_last_14d",
        "ucl_full90s_last_14d",
        "ucl_matches_last_30d",
        "days_since_last_ucl",
        "played_ucl_last_match",
        "cup_minutes_last_7d",
        "cup_minutes_last_14d",
        "cup_starts_last_14d",
        "cup_full90s_last_14d",
        "cup_matches_last_30d",
        "played_domestic_cup_last_match",
        "transition_ucl_to_pl",
        "transition_pl_to_ucl",
        "transition_cup_to_pl",
        "transition_pl_to_cup",
        "competition_switches_last_30d",
        "competitions_played_last_30d",
        "rest_days_after_ucl",
        "post_ucl_short_rest",
        "pl_after_ucl_with_short_rest",
        "ucl_full90_then_pl_short_rest",
        "days_since_european_match",
        "matches_since_european_match",
    ],
    "recent_action_load": [
        "duels_last_3_matches",
        "duels_last_14d",
        "tackles_last_3_matches",
        "tackles_last_14d",
        "fouls_last_3_matches",
        "fouls_last_14d",
        "dribbles_last_3_matches",
        "dribbles_last_14d",
        "cards_last_5_matches",
        "duels_total_position_z",
        "tackles_total_position_z",
        "fouls_committed_position_z",
        "minutes_played_position_z",
        "physical_load_index",
        "minutes_last_21d_vs_player_avg",
        "minutes_last_21d_player_z",
        "full90_last_14d_vs_player_avg",
        "physical_load_last_14d_vs_player_avg",
        "starts_last_14d_vs_player_avg",
    ],
    "injury_context": [
        "squad_injured_count",
        "squad_soft_tissue_count",
        "squad_avg_days_out",
        "returning_from_injury",
        "fixtures_missed_last_30d",
        "high_squad_injury_pressure",
        "soft_tissue_pressure_high_load",
        "squad_injury_high_workload",
        "injury_context_score",
    ],
    "role_context": [
        "player_position",
        "player_role_v4b",
        "is_home",
        "is_substitute",
    ],
    "missingness_context": [
        "rest_days_missing",
        "squad_injured_count_missing",
        "squad_soft_tissue_count_missing",
        "squad_avg_days_out_missing",
        "days_since_last_injury_missing",
        "fixtures_missed_last_30d_missing",
        "fixtures_missed_last_90d_missing",
        "returning_from_injury_missing",
        "acwr_ratio_missing",
        "min_last_7d_missing",
        "days_since_european_match_missing",
    ],
    "recent_baseline_form": [
        "avg_rating_last_3",
        "avg_rating_last_5",
    ],
}

MASTER_CSV_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "Fixture_IQ_Data_Seasons_2022-2025.csv"

# --------------------------------------------------
# V6 XGBoost paths and constants
# --------------------------------------------------

V6_BASE_DIR = MODELS_DIR / "xgboost_v6"
V6_NO_COMP_DIR = V6_BASE_DIR / "v6_no_competition"
V6_NO_RATING_DIR = V6_BASE_DIR / "v6_no_rating_baseline"

V6_MODEL_PATH = V6_NO_COMP_DIR / "model.json"
V6_PREPROCESSOR_PATH = V6_NO_COMP_DIR / "preprocessor.pkl"
V6_METADATA_PATH = V6_NO_COMP_DIR / "metadata.joblib"
V6_NR_MODEL_PATH = V6_NO_RATING_DIR / "model.json"
V6_NR_PREPROCESSOR_PATH = V6_NO_RATING_DIR / "preprocessor.pkl"
V6_NR_METADATA_PATH = V6_NO_RATING_DIR / "metadata.joblib"

V6_OPERATING_POLICY = {
    "name": "v6_balanced_role_aware_monitoring",
    "core_starter_threshold": 0.5,
    "rotation_player_threshold": 0.5,
    "intent": "monitoring_support",
    "message": (
        "V6 flag indicates workload-associated risk for review, "
        "not definitive fatigue diagnosis."
    ),
}

V6_RISK_BANDS = [0, 0.25, 0.45, 0.65, 1.01]
V6_RISK_LABELS = ["Low", "Medium", "High", "Very High"]
V6_RISK_COLORS = {"Low": "#27ae60", "Medium": "#f39c12", "High": "#e74c3c", "Very High": "#8e44ad"}

V6_ROLE_COLORS = {
    "core_starter": "#00BC8C",
    "rotation_player": "#636EFA",
}
