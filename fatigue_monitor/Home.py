import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
import pandas as pd

from fatigue_monitor.theme import DARK_CSS
from fatigue_monitor.src.config import MASTER_CSV_PATH
from fatigue_monitor.src.prediction import predict_fatigue_risk, load_artifacts
from fatigue_monitor.src.prediction_v6 import load_v6_artifacts, predict_v6


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


@st.cache_resource
def load_v6_no_comp():
    return load_v6_artifacts("no_competition")


@st.cache_resource
def load_v6_no_rating():
    return load_v6_artifacts("no_rating_baseline")


@st.cache_data
def run_predictions(df):
    model, preprocessor, num_feat, cat_feat = load_model()
    return predict_fatigue_risk(df, model, preprocessor, num_feat, cat_feat)


@st.cache_data
def run_v6_predictions(df):
    m1, meta1 = load_v6_no_comp()
    m2, meta2 = load_v6_no_rating()
    v6 = predict_v6(df, m1, meta1, suffix="_v6_perf")
    v6nr = predict_v6(df, m2, meta2, suffix="_v6_fatigue")
    merge_cols = ["fixture_id", "player_id", "date", "player_name", "player_team", "player_position"]
    v6_keep = merge_cols + [c for c in v6.columns if c not in merge_cols]
    v6nr_keep = merge_cols + [c for c in v6nr.columns if c not in merge_cols]
    merged = v6[v6_keep].merge(v6nr[v6nr_keep], on=merge_cols, how="outer", suffixes=("", "_nr"))
    return merged


# --------------------------------------------------
# AUTO LOAD DATA (NO BUTTONS, NO BLOCKING)
# --------------------------------------------------

if st.session_state.results_df is None:

    with st.spinner("Loading dataset and computing fatigue predictions..."):

        master = load_master()
        results = run_predictions(master)
        v6_results = run_v6_predictions(master)

        results = results.merge(
            v6_results,
            on=["fixture_id", "player_id", "date", "player_name", "player_team", "player_position"],
            how="left",
        )

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

    n_players = df["player_id"].nunique()
    n_teams = df["player_team"].nunique()
    n_matches = df["fixture_id"].nunique()
    n_comps = df["competition"].nunique()

    card_style = """
    background:#1a1d27;border:1px solid #2a2e3a;border-radius:12px;
    padding:20px;transition:border-color 0.2s;text-align:center;
    """

    c1, c2, c3, c4 = st.columns(4)
    for col, icon, value, label, sub in [
        (c1, "👥", f"{n_players:,}", "Players", "Across all teams"),
        (c2, "🏟️", f"{n_teams}", "Teams", "EPL clubs"),
        (c3, "📅", f"{n_matches:,}", "Matches", "All competitions"),
        (c4, "🏆", f"{n_comps}", "Competitions", "Domestic + Europe"),
    ]:
        with col:
            st.markdown(
                f'<div style="{card_style}">'
                f'<div style="font-size:24px;margin-bottom:8px">{icon}</div>'
                f'<div style="font-size:28px;font-weight:700;color:#e0e0e0">{value}</div>'
                f'<div style="font-size:13px;font-weight:500;color:#c9d1d9;margin-top:2px">{label}</div>'
                f'<div style="font-size:11px;color:#8a8f9d;margin-top:2px">{sub}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

st.markdown("---")

st.subheader("🎯 Project Objectives")

obj_icon_style = "display:inline-flex;align-items:center;justify-content:center;width:36px;height:36px;border-radius:10px;font-size:18px;margin-right:12px;flex-shrink:0;"
o1, o2, o3, o4, o5 = st.columns(5, vertical_alignment="center")
obj_data = [
    (o1, "📊", "bg-chart-3/10", "Quantity", "Fixture congestion via scheduling metrics"),
    (o2, "⚡", "bg-chart-5/10", "Analyse", "Fatigue impact on player performance"),
    (o3, "🔄", "bg-chart-4/10", "Measure", "Squad rotation strategies"),
    (o4, "⚠️", "bg-primary/10", "Identify", "High-risk workload periods"),
    (o5, "📋", "bg-accent/10", "Support", "Data-driven coaching decisions"),
]
for col, icon, bg, title, desc in obj_data:
    with col:
        st.markdown(
            f'<div style="background:#1a1d27;border:1px solid #2a2e3a;border-radius:10px;padding:14px;text-align:center;height:100%">'
            f'<div style="font-size:22px;margin-bottom:6px">{icon}</div>'
            f'<div style="font-size:13px;font-weight:600;color:#c9d1d9">{title}</div>'
            f'<div style="font-size:11px;color:#8a8f9d;margin-top:2px;line-height:1.3">{desc}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

st.markdown("---")

st.subheader("📚 Research Hypotheses")

h_statuses = {
    "H1": {"label": "Lower rest periods reduce performance.", "status": "Supported", "evidence": "Correlation between ≤4d rest and lower ratings (p<0.01)"},
    "H2": {"label": "Higher congestion increases squad rotation.", "status": "Supported", "evidence": "Rotation index +38% during congested periods"},
    "H3": {"label": "Clubs respond differently to congestion.", "status": "Partially Supported", "evidence": "Varies by European involvement and squad depth"},
    "H4": {"label": "Data-driven dashboards improve decision-making.", "status": "Pending", "evidence": "Requires longitudinal staff feedback study"},
}
status_colors = {
    "Supported": {"text": "#27ae60", "bg": "rgba(39,174,96,0.15)", "icon": "✅"},
    "Partially Supported": {"text": "#f39c12", "bg": "rgba(243,156,18,0.15)", "icon": "🟡"},
    "Pending": {"text": "#8a8f9d", "bg": "rgba(138,143,157,0.15)", "icon": "⏳"},
}

hc1, hc2 = st.columns(2, vertical_alignment="center")
for i, (hid, hinfo) in enumerate(h_statuses.items()):
    col = hc1 if i % 2 == 0 else hc2
    sc = status_colors[hinfo["status"]]
    with col:
        st.markdown(
            f'<div style="background:#1a1d27;border:1px solid #2a2e3a;border-radius:10px;padding:16px;margin-bottom:12px">'
            f'<div style="display:flex;align-items:flex-start;gap:10px;margin-bottom:8px">'
            f'<div style="width:32px;height:32px;border-radius:8px;background:{sc["bg"]};display:flex;align-items:center;justify-content:center;flex-shrink:0;font-size:16px">{sc["icon"]}</div>'
            f'<div style="flex:1">'
            f'<div style="display:flex;gap:8px;align-items:center;margin-bottom:4px">'
            f'<span style="font-size:11px;font-weight:700;color:#00BC8C;font-family:monospace">{hid}</span>'
            f'<span style="font-size:10px;font-weight:600;padding:1px 8px;border-radius:10px;background:{sc["bg"]};color:{sc["text"]}">{hinfo["status"]}</span>'
            f'</div>'
            f'<div style="font-size:13px;font-weight:500;color:#c9d1d9">{hinfo["label"]}</div>'
            f'</div>'
            f'</div>'
            f'<div style="font-size:11px;color:#8a8f9d;line-height:1.4;padding:8px 10px;background:rgba(138,143,157,0.06);border-radius:6px;border:1px solid #2a2e3a">{hinfo["evidence"]}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )