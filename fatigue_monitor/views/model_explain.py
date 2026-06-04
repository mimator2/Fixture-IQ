import streamlit as st
import pandas as pd
import numpy as np
from streamlit_echarts import st_echarts
from fatigue_monitor.src.config import MODEL_PATH, OPERATING_POLICY


def model_explain_page():
    results = st.session_state.results_df
    if results is None:
        st.info("Load data first via the sidebar.")
        return

    latest = results.sort_values("date", ascending=False).groupby("player_name", as_index=False).first()

    from fatigue_monitor.src.prediction import load_artifacts
    model, preprocessor, num_features, cat_features = load_artifacts()

    cat_names = list(preprocessor.named_transformers_["cat"]["ohe"].get_feature_names_out(cat_features))
    all_feat_names = num_features + cat_names
    importances = model.feature_importances_[:len(all_feat_names)]
    fi = pd.DataFrame({"feature": all_feat_names, "importance": importances})
    fi = fi.sort_values("importance", ascending=False).reset_index(drop=True)

    st.markdown("### Top Global Features")

    top20 = fi.head(20).sort_values("importance")
    features_rev = list(top20["feature"])
    imp_rev = [round(v, 4) for v in top20["importance"]]

    q75 = top20["importance"].quantile(0.75)
    q50 = top20["importance"].quantile(0.5)
    feat_colors = [
        "#e74c3c" if v >= q75 else "#f39c12" if v >= q50 else "#00BC8C"
        for v in top20["importance"]
    ]

    st_echarts(
        options={
            "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
            "grid": {"left": "3%", "right": "4%", "bottom": "3%", "top": "10%", "containLabel": True},
            "xAxis": {"type": "value", "axisLabel": {"color": "#8b949e"}},
            "yAxis": {
                "type": "category",
                "data": features_rev,
                "axisLabel": {"color": "#c9d1d9", "fontSize": 11},
            },
            "series": [
                {
                    "type": "bar",
                    "data": [{"value": v, "itemStyle": {"color": c}} for v, c in zip(imp_rev, feat_colors)],
                    "label": {"show": True, "position": "right", "color": "#8b949e", "fontSize": 10},
                }
            ],
        },
        height="520px",
    )

    st.markdown("### Feature Category Breakdown")

    categories = {
        "Workload Volume": ["min_last", "matches_last", "starts_last", "full_90s"],
        "Rest & Recovery": ["rest_days", "short_rest", "rest_le_"],
        "UCL Burden": ["ucl_"],
        "Cup Burden": ["cup_"],
        "Competition Transitions": ["transition_", "pl_after_ucl", "post_ucl_"],
        "Physical Effort": ["duels_", "tackles_", "fouls_", "dribbles_", "cards_", "physical_load"],
        "Position Context": ["_position_z", "player_position"],
        "Squad Context": ["squad_", "returning_from", "fixtures_missed"],
        "Player-Relative": ["_vs_player_", "_player_z"],
    }

    cat_imp = {}
    for cat, keywords in categories.items():
        mask = fi["feature"].str.contains("|".join(keywords), regex=True, na=False)
        cat_imp[cat] = fi.loc[mask, "importance"].sum()

    cat_df = pd.DataFrame(list(cat_imp.items()), columns=["Category", "Total Importance"])
    cat_df = cat_df.sort_values("Total Importance", ascending=False)

    cat_names_ordered = list(cat_df["Category"])
    cat_vals_ordered = [round(v, 4) for v in cat_df["Total Importance"]]

    st_echarts(
        options={
            "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
            "grid": {"left": "3%", "right": "4%", "bottom": "3%", "top": "10%", "containLabel": True},
            "xAxis": {"type": "value", "axisLabel": {"color": "#8b949e"}},
            "yAxis": {
                "type": "category",
                "data": cat_names_ordered,
                "axisLabel": {"color": "#c9d1d9", "fontSize": 11},
            },
            "series": [
                {
                    "type": "bar",
                    "data": cat_vals_ordered,
                    "itemStyle": {
                        "color": {
                            "type": "linear",
                            "x": 0, "y": 0, "x2": 1, "y2": 0,
                            "colorStops": [
                                {"offset": 0, "color": "#1a6bff"},
                                {"offset": 1, "color": "#00BC8C"},
                            ],
                        }
                    },
                    "label": {"show": True, "position": "right", "color": "#8b949e", "fontSize": 10},
                }
            ],
        },
        height="360px",
    )

    st.markdown("### Per-Player Feature Drivers")

    player_list = sorted(latest["player_name"].unique())
    player = st.selectbox("Choose player", player_list, key="explain_player")

    prow = latest[latest["player_name"] == player]
    if len(prow) > 0:
        prow = prow.iloc[0]
        score = prow["risk_score_v4"]
        band = prow["risk_band_v4"]

        gc1, gc2, gc3 = st.columns([1, 2, 1], vertical_alignment="center")
        with gc2:
            st_echarts(
                options={
                    "series": [
                        {
                            "type": "gauge",
                            "startAngle": 210,
                            "endAngle": -30,
                            "min": 0,
                            "max": 1,
                            "center": ["50%", "55%"],
                            "radius": "80%",
                            "progress": {"show": True, "width": 10, "roundCap": True},
                            "axisLine": {
                                "lineStyle": {
                                    "width": 10,
                                    "color": [
                                        [0.25, "#27ae60"],
                                        [0.45, "#f39c12"],
                                        [0.65, "#e74c3c"],
                                        [1, "#8e44ad"],
                                    ],
                                }
                            },
                            "axisTick": {"show": False},
                            "splitLine": {"show": False},
                            "axisLabel": {"show": False},
                            "pointer": {"show": False},
                            "anchor": {"show": False},
                            "title": {"show": False},
                            "detail": {
                                "formatter": "{value}",
                                "fontSize": 22,
                                "fontWeight": "bold",
                                "color": "#e0e0e0",
                                "offsetCenter": [0, "35%"],
                            },
                            "data": [{"value": round(float(score), 3), "name": band}],
                        }
                    ]
                },
                height="180px",
            )

        top_feats = fi.head(15)
        contribs = []
        for _, frow in top_feats.iterrows():
            feat = frow["feature"]
            imp = frow["importance"]
            if feat in prow.index and not pd.isna(prow[feat]):
                val = prow[feat]
                contribs.append({
                    "Feature": feat,
                    "Importance": imp,
                    "Value": val,
                    "Direction": "↑" if val > 0 else "↓",
                })

        if contribs:
            cdf = pd.DataFrame(contribs).head(10)
            feat_labels = [
                f"{r['Feature']} = {r['Value']:.2f}" if isinstance(r['Value'], (int, float)) else f"{r['Feature']} = {r['Value']}"
                for _, r in cdf.iterrows()
            ][::-1]
            imp_vals = [round(v, 4) for v in cdf["Importance"].values][::-1]
            dir_colors = ["#e74c3c" if d == "↑" else "#00BC8C" for d in cdf["Direction"].values][::-1]

            st_echarts(
                options={
                    "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
                    "grid": {"left": "3%", "right": "4%", "bottom": "3%", "top": "10%", "containLabel": True},
                    "xAxis": {"type": "value", "axisLabel": {"color": "#8b949e"}},
                    "yAxis": {
                        "type": "category",
                        "data": feat_labels,
                        "axisLabel": {"color": "#c9d1d9", "fontSize": 10},
                    },
                    "series": [
                        {
                            "type": "bar",
                            "data": [{"value": v, "itemStyle": {"color": c}} for v, c in zip(imp_vals, dir_colors)],
                            "label": {"show": True, "position": "right", "color": "#8b949e", "fontSize": 10},
                        }
                    ],
                },
                height="320px",
            )

    st.markdown("### Threshold Policy")
    col1, col2, col3 = st.columns(3, vertical_alignment="center")
    with col1:
        st.metric("Core Starter Threshold", f"{OPERATING_POLICY['core_starter_threshold']:.2f}")
    with col2:
        st.metric("Rotation Player Threshold", f"{OPERATING_POLICY['rotation_player_threshold']:.2f}")
    with col3:
        st.metric("Policy Name", OPERATING_POLICY["name"])

    st.info(OPERATING_POLICY["message"])

    st.markdown("""
    #### Risk Bands
    | Range | Label |
    |---|---|
    | 0.00 - 0.25 | Low |
    | 0.25 - 0.45 | Medium |
    | 0.45 - 0.65 | High |
    | > 0.65 | Very High |
    """)

    with st.expander("Model Limitations & Usage Notes"):
        st.markdown("""
        - **Not a medical/fatigue diagnosis**: Model B v4b identifies workload patterns historically
          associated with reduced performance or managed minutes. It does **not** measure actual
          physiological fatigue.
        - **Moderate discriminative power**: Test AUC-ROC ≈ 0.62. The model is useful as a
          screening/ranking tool but not as a definitive classifier.
        - **Temporal generalization**: Trained on 2022-23, validated on 2023-24, tested on 2024-25.
          Performance may differ in future seasons.
        - **Data limitations**: The model uses SofaScore/API ratings as a performance proxy.
          Features like GPS tracking, heart rate, or subjective wellness are not available.
        - **Role assignment**: Player roles are based on a 28-day rolling window. A player's role
          may shift during the season, which changes their monitoring threshold.
        """)
