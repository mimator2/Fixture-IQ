from pathlib import Path

MODEL_DIR = Path(__file__).resolve().parent.parent / "models" / "model_b_v4b"

MODEL_PATH = MODEL_DIR / "xgb_model.pkl"
PREPROCESSOR_PATH = MODEL_DIR / "preprocessor.pkl"
NUM_FEATURES_PATH = MODEL_DIR / "num_features.pkl"
CAT_FEATURES_PATH = MODEL_DIR / "cat_features.pkl"
POLICY_PATH = MODEL_DIR / "policy.pkl"

OPERATING_POLICY = {
    "name": "balanced_monitoring",
    "core_starter_threshold": 0.45,
    "rotation_player_threshold": 0.50,
    "intent": "monitoring_support",
    "message": (
        "Flag indicates workload-associated risk for monitoring, "
        "not definitive fatigue diagnosis."
    ),
}

RISK_BANDS = [0, 0.25, 0.45, 0.65, 1.01]
RISK_LABELS = ["Low", "Medium", "High", "Very High"]
RISK_COLORS = {"Low": "#27ae60", "Medium": "#f39c12", "High": "#e74c3c", "Very High": "#8e44ad"}

MONITORING_FLAG_COLOR = {0: "#27ae60", 1: "#e74c3c"}
MONITORING_FLAG_LABEL = {0: "Clear", 1: "Monitor"}

ROLE_COLORS = {
    "core_starter": "#00BC8C",
    "rotation_player": "#636EFA",
    "impact_sub": "#FFA15A",
    "rare_player": "#AB63FA",
}

MASTER_CSV_PATH = Path(__file__).resolve().parent.parent.parent / "XgBoost_model" / "Fixture_IQ_Data_Seasons_2022-2025.csv"
