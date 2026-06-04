import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
import pandas as pd

from fatigue_monitor.theme import DARK_CSS
from fatigue_monitor.src.config import MASTER_CSV_PATH
from fatigue_monitor.src.prediction import predict_fatigue_risk, load_artifacts


# --------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------

st.set_page_config(
    page_title="Fixture-IQ | Fatigue Monitor",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(DARK_CSS, unsafe_allow_html=True)


# --------------------------------------------------
# SESSION STATE INIT (IMPORTANT FIX)
# --------------------------------------------------

for key in [
    "results_df",
    "source_df",
    "data_source",
    "selected_player"
]:
    if key not in st.session_state:
        st.session_state[key] = None


# --------------------------------------------------
# CACHE DATA FUNCTIONS
# --------------------------------------------------

@st.cache_data
def load_master():
    df = pd.read_csv(MASTER_CSV_PATH)
    df["date"] = pd.to_datetime(df["date"])
    return df


@st.cache_resource
def load_model():
    return load_artifacts()


@st.cache_data
def run_predictions(df):
    model, preprocessor, num_feat, cat_feat = load_model()
    return predict_fatigue_risk(df, model, preprocessor, num_feat, cat_feat)


# --------------------------------------------------
# AUTO LOAD DATA (NO BUTTONS, NO BLOCKING)
# --------------------------------------------------

if st.session_state.results_df is None:

    with st.spinner("Loading dataset and computing fatigue predictions..."):

        master = load_master()
        results = run_predictions(master)

        st.session_state.source_df = master
        st.session_state.results_df = results
        st.session_state.data_source = "master"


# --------------------------------------------------
# HOME PAGE CONTENT (IMPORTANT: PURE INFO PAGE)
# --------------------------------------------------

st.title("⚽ Fixture-IQ")

st.markdown("""
### Fixture Congestion & Fatigue Analytics in Elite Football

This platform analyses how fixture congestion impacts:
- Player workload
- Squad rotation
- Competitive performance

The system integrates match schedules, player minutes, and performance metrics to detect fatigue risk patterns in elite football.
""")

st.markdown("---")

df = st.session_state.source_df
res = st.session_state.results_df

if df is not None:

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Players", df["player_id"].nunique())
    col2.metric("Teams", df["player_team"].nunique())
    col3.metric("Matches", df["fixture_id"].nunique())
    col4.metric("Competitions", df["competition"].nunique())

st.markdown("---")

st.subheader("🎯 Project Objectives")

st.markdown("""
- Quantify fixture congestion using scheduling metrics
- Analyse fatigue impact on performance
- Measure squad rotation strategies
- Identify high-risk workload periods
- Support data-driven coaching decisions
""")

st.subheader("📚 Research Hypotheses")

st.markdown("""
**H1:** Lower rest periods reduce performance.

**H2:** Higher congestion increases squad rotation.

**H3:** Clubs respond differently to congestion.

**H4:** Data-driven dashboards improve decision-making.
""")