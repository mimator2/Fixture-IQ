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
