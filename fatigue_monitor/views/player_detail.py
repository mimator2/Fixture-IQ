import streamlit as st
import pandas as pd
from streamlit_echarts import st_echarts


def player_detail_page():


    st.title("Player Detail View")

    st.markdown("""
                
        This page provides an in-depth look at individual player fatigue risk assessments.
         - **Risk Score**: A numerical value between 0 and 1 indicating fatigue risk.
         - **Risk Band**: Categorical risk level (Low, Medium, High).
         - **Role**: Player's position or role in the team.
         - **Threshold**: The risk score threshold for monitoring.
         - **Rest Days**: Recommended rest days based on current risk.
         - **Risk Drivers**: Key factors contributing to the player's fatigue risk.
         - **Gauge Chart**: Visual representation of the player's current risk score.
    """)

    # --------------------------------------------------
    # SAFE SESSION ACCESS (FIX YOUR ERROR)
    # --------------------------------------------------

    results = st.session_state.get("results_df", None)

    if results is None:
        st.warning("⚠ Data is loading... please return to Home or refresh.")
        st.stop()

    # --------------------------------------------------
    # BACK BUTTON
    # --------------------------------------------------

    if st.button("← Back to Overview"):
        st.session_state.selected_player = None
        st.switch_page("app.py")  # adjust if needed

    st.markdown("---")

    # --------------------------------------------------
    # DATA PREP
    # --------------------------------------------------

    latest = (
        results.sort_values("date", ascending=False)
        .groupby("player_name", as_index=False)
        .first()
    )

    player_list = sorted(latest["player_name"].unique())

    selected_player = st.session_state.get("selected_player", None)

    if selected_player in player_list:
        default_index = player_list.index(selected_player)
    else:
        default_index = 0

    player = st.selectbox(
        "Select Player",
        player_list,
        index=default_index
    )

    st.session_state.selected_player = player

    prow = latest[latest["player_name"] == player]

    if prow.empty:
        st.warning("No data for selected player.")
        return

    prow = prow.iloc[0]

    # --------------------------------------------------
    # METRICS
    # --------------------------------------------------

    st.markdown("### A. Current Risk Assessment")

    c1, c2, c3, c4, c5 = st.columns(5)

    c1.metric("Risk Score", f"{prow['risk_score_v4']:.3f}")
    c2.metric("Risk Band", prow["risk_band_v4"])
    c3.metric("Role", prow["player_role_v4"])
    c4.metric("Threshold", f"{prow['monitoring_threshold_v4']:.2f}")
    c5.metric("Rest Days", f"{prow.get('rest_days', 0):.0f}")

    # --------------------------------------------------
    # GAUGE CHART
    # --------------------------------------------------

    import math

    score_raw = prow.get("risk_score_v4", 0)

    # safe conversion (VERY IMPORTANT)
    if score_raw is None or (isinstance(score_raw, float) and math.isnan(score_raw)):
        score = 0.0
    else:
        score = float(score_raw)


    st_echarts(
        options={
            "series": [
                {
                    "type": "gauge",
                    "min": 0,
                    "max": 1,
                    "startAngle": 210,
                    "endAngle": -30,
                    "progress": {"show": True},
                    "data": [{"value": score}],
                    "detail": {
                        "formatter": "{value}",
                        "fontSize": 28
                    }
                }
            ]
        },
        height="250px"
    )

    # --------------------------------------------------
    # DRIVERS
    # --------------------------------------------------

    st.markdown("### Risk Drivers")

    expl = prow.get("explanation_v4", "")

    if expl:
        for item in expl.split(";"):
            st.markdown(f"- {item}")