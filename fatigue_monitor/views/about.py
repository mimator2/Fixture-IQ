import streamlit as st
import pandas as pd
from fatigue_monitor.src.config import OPERATING_POLICY


def about_page():
    st.markdown("## About Model B v4b")

    st.markdown("""
    ### Purpose

    Model B v4b is a **post-match / pre-next-match monitoring tool** for football staff.
    After each fixture, the app processes player-match data through the same feature-engineering
    pipeline used during training. It computes workload, rest, physical-effort, UCL/cup burden,
    player-role, and squad-context variables for each outfield player.

    The output is a **workload-associated risk score** interpreted as monitoring support,
    **not** as a definitive fatigue diagnosis.
    """)

    st.markdown("### Operating Policy")
    c1, c2, c3 = st.columns(3, vertical_alignment="center")
    with c1:
        st.metric("Policy Name", OPERATING_POLICY["name"])
    with c2:
        st.metric("Core Starter Threshold", f"{OPERATING_POLICY['core_starter_threshold']:.2f}")
    with c3:
        st.metric("Rotation Player Threshold", f"{OPERATING_POLICY['rotation_player_threshold']:.2f}")

    st.info(OPERATING_POLICY["message"])

    st.markdown("### Risk Bands")
    bands_df = pd.DataFrame({
        "Range": ["0.00 – 0.25", "0.25 – 0.45", "0.45 – 0.65", "> 0.65"],
        "Label": ["Low", "Medium", "High", "Very High"],
        "Core Starter": ["Clear", "Clear", "Monitor", "Monitor"],
        "Rotation Player": ["Clear", "Clear", "Clear", "Monitor"],
    })
    st.table(bands_df)

    st.markdown("### Model Performance")
    perf = pd.DataFrame({
        "Metric": ["Test AUC-ROC", "Test AUC-PR", "Base Rate", "Best Threshold", "Numerical Features", "Categorical Features"],
        "Value": ["0.627", "0.390", "0.286", "0.449", "77", "1 (player_position)"],
    })
    st.table(perf)

    st.markdown("### Top Contributing Features")
    st.markdown("""
    The model's leading features are workload-related, consistent with fatigue monitoring:

    1. `matches_with_rest_le_4d_last_30d` — matches with ≤4 days rest
    2. `matches_with_rest_le_6d_last_30d` — matches with ≤6 days rest
    3. `full_90s_last_14d` — full-90 appearances
    4. `full_90s_last_28d` — full-90 appearances (28d)
    5. `rest_days` — days since last match
    6. `starts_last_14d` — starts in last 14 days
    7. `ucl_matches_last_30d` — UCL matches
    """)

    with st.expander("Model Limitations & Usage Notes"):
        st.markdown("""
        - **Not a medical/fatigue diagnosis**: Model B v4b identifies workload patterns historically
          associated with reduced performance or managed minutes. It does **not** measure actual
          physiological fatigue.
        - **Moderate discriminative power**: Test AUC-ROC ≈ 0.62. Useful as a screening/ranking
          tool but not as a definitive classifier.
        - **Temporal generalization**: Trained on 2022-23, validated on 2023-24, tested on 2024-25.
          Performance may differ in future seasons.
        - **Data limitations**: Uses SofaScore/API ratings as a performance proxy. GPS tracking,
          heart rate, or subjective wellness data are not available.
        - **Role assignment**: Player roles are based on a 28-day rolling window. A player's role
          may shift during the season, which changes their monitoring threshold.
        """)

    st.markdown("### Technology Stack")
    st.markdown("""
    - **Model**: XGBoost Classifier (v4b_no_competition variant)
    - **Framework**: Streamlit + streamlit-echarts
    - **Artifacts**: joblib-serialised (model, preprocessor, feature lists, policy)
    - **Data**: SofaScore/Fbref match & player-event data (2022–2025)
    """)
