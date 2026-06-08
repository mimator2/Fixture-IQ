import streamlit as st
import pandas as pd
import numpy as np
import math
from streamlit_echarts import st_echarts
from fatigue_monitor.src.config import MODEL_PATH, OPERATING_POLICY


def model_explain_page():
    results = st.session_state.results_df
    if results is None:
        st.info("Load data first via the sidebar.")
        return

    latest = results.sort_values("date", ascending=False).groupby("player_name", as_index=False).first()

    # --------------------------------------------------
    # V4 (XGBoost) Feature Importance
    # --------------------------------------------------

    from fatigue_monitor.src.prediction import load_artifacts
    model, preprocessor, num_features, cat_features = load_artifacts()

    cat_names = list(preprocessor.named_transformers_["cat"]["ohe"].get_feature_names_out(cat_features))
    all_feat_names = num_features + cat_names
    importances = model.feature_importances_[:len(all_feat_names)]
    fi = pd.DataFrame({"feature": all_feat_names, "importance": importances})
    fi = fi.sort_values("importance", ascending=False).reset_index(drop=True)

    st.markdown(
        '<div class="section-card section-card-accent-v4">'
        '<div style="font-size:15px;font-weight:600;color:#c9d1d9;margin-bottom:12px">V4 (XGBoost) — Top Global Features</div>',
        unsafe_allow_html=True,
    )

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

    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown(
        '<div class="section-card section-card-accent-v4">'
        '<div style="font-size:15px;font-weight:600;color:#c9d1d9;margin-bottom:12px">V4 — Feature Category Breakdown</div>',
        unsafe_allow_html=True,
    )

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

    st.markdown("</div>", unsafe_allow_html=True)

    # --------------------------------------------------
    # V6 (CatBoost) Feature Importance
    # --------------------------------------------------

    has_v6 = "risk_score_v6_fatigue" in results.columns
    if has_v6:
        st.markdown(
            '<div class="section-card section-card-accent-fatigue">'
            '<div style="font-size:15px;font-weight:600;color:#c9d1d9;margin-bottom:12px">V6 (CatBoost No Rating Baseline) — Top Global Features</div>',
            unsafe_allow_html=True,
        )

        from fatigue_monitor.src.config import V6_NR_METADATA_PATH
        import joblib
        import json

        v6_meta = joblib.load(V6_NR_METADATA_PATH)
        if isinstance(v6_meta, dict):
            v6_fi = v6_meta.get("feature_importances", None)
        else:
            v6_fi = getattr(v6_meta, "feature_importances_", None)

        if v6_fi is not None:
            v6_feats = v6_meta.get("features", []) if isinstance(v6_meta, dict) else v6_meta.get("features", [])
            v6_fi_df = pd.DataFrame({"feature": v6_feats, "importance": v6_fi})
            v6_fi_df = v6_fi_df.sort_values("importance", ascending=False).reset_index(drop=True)
            v6_top = v6_fi_df.head(20).sort_values("importance")
            v6_features_rev = list(v6_top["feature"])
            v6_imp_rev = [round(v, 4) for v in v6_top["importance"]]
            v6_q75 = v6_top["importance"].quantile(0.75)
            v6_q50 = v6_top["importance"].quantile(0.5)
            v6_feat_colors = [
                "#e74c3c" if v >= v6_q75 else "#f39c12" if v >= v6_q50 else "#00BC8C"
                for v in v6_top["importance"]
            ]
            st_echarts(
                options={
                    "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
                    "grid": {"left": "3%", "right": "4%", "bottom": "3%", "top": "10%", "containLabel": True},
                    "xAxis": {"type": "value", "axisLabel": {"color": "#8b949e"}},
                    "yAxis": {
                        "type": "category",
                        "data": v6_features_rev,
                        "axisLabel": {"color": "#c9d1d9", "fontSize": 11},
                    },
                    "series": [
                        {
                            "type": "bar",
                            "data": [{"value": v, "itemStyle": {"color": c}} for v, c in zip(v6_imp_rev, v6_feat_colors)],
                            "label": {"show": True, "position": "right", "color": "#8b949e", "fontSize": 10},
                        }
                    ],
                },
                height="520px",
            )

        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown(
            '<div class="section-card section-card-accent-fatigue">'
            '<div style="font-size:15px;font-weight:600;color:#c9d1d9;margin-bottom:12px">V6 — Feature Group Breakdown</div>',
            unsafe_allow_html=True,
        )

        if v6_fi is not None:
            v6_groups = v6_meta.get("feature_groups", {}) if isinstance(v6_meta, dict) else {}
            if v6_groups:
                v6_group_imp = []
                for grp_name, grp_feats in v6_groups.items():
                    mask = v6_fi_df["feature"].isin(grp_feats)
                    total = v6_fi_df.loc[mask, "importance"].sum()
                    v6_group_imp.append({"Group": grp_name, "Total Importance": total})
                v6_gdf = pd.DataFrame(v6_group_imp).sort_values("Total Importance", ascending=False)
                v6_grp_names = list(v6_gdf["Group"])
                v6_grp_vals = [round(v, 4) for v in v6_gdf["Total Importance"]]

                st_echarts(
                    options={
                        "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
                        "grid": {"left": "3%", "right": "4%", "bottom": "3%", "top": "10%", "containLabel": True},
                        "xAxis": {"type": "value", "axisLabel": {"color": "#8b949e"}},
                        "yAxis": {
                            "type": "category",
                            "data": v6_grp_names,
                            "axisLabel": {"color": "#c9d1d9", "fontSize": 11},
                        },
                        "series": [
                            {
                                "type": "bar",
                                "data": v6_grp_vals,
                                "itemStyle": {
                                    "color": {
                                        "type": "linear",
                                        "x": 0, "y": 0, "x2": 1, "y2": 0,
                                        "colorStops": [
                                            {"offset": 0, "color": "#8e44ad"},
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

        st.markdown("</div>", unsafe_allow_html=True)

    # --------------------------------------------------
    # V6 Performance Metrics
    # --------------------------------------------------

    if has_v6:
        v6_auc = v6_meta.get("auc", "—") if isinstance(v6_meta, dict) else "—"
        v6_prauc = v6_meta.get("pr_auc", "—") if isinstance(v6_meta, dict) else "—"
        v6_f1 = v6_meta.get("f1_at_0_50", "—") if isinstance(v6_meta, dict) else "—"
        v6_prec = v6_meta.get("precision_at_0_50", "—") if isinstance(v6_meta, dict) else "—"
        v6_rec = v6_meta.get("recall_at_0_50", "—") if isinstance(v6_meta, dict) else "—"
        v6_ba = v6_meta.get("balanced_accuracy_at_0_50", "—") if isinstance(v6_meta, dict) else "—"
        v6_nfeats = len(v6_meta.get("features", [])) if isinstance(v6_meta, dict) else "—"

        metric_items = [
            ("📈", f"{v6_auc:.4f}" if isinstance(v6_auc, (int, float)) else v6_auc, "AUROC"),
            ("🎯", f"{v6_f1:.4f}" if isinstance(v6_f1, (int, float)) else v6_f1, "F1@0.50"),
            ("📊", f"{v6_prauc:.4f}" if isinstance(v6_prauc, (int, float)) else v6_prauc, "PR-AUC"),
            ("⚡", f"{v6_prec:.4f}" if isinstance(v6_prec, (int, float)) else v6_prec, "Precision@0.50"),
            ("🧩", f"{v6_nfeats}", "Features"),
            ("🔄", f"{v6_rec:.4f}" if isinstance(v6_rec, (int, float)) else v6_rec, "Recall@0.50"),
        ]

        perf_grid = '<div style="display:grid;grid-template-columns:repeat(6,1fr);gap:10px">'
        for icon, val, label in metric_items:
            perf_grid += f'<div class="stat-block"><div class="stat-icon">{icon}</div><div class="stat-value" style="font-size:22px">{val}</div><div class="stat-label">{label}</div></div>'
        perf_grid += "</div>"

        st.markdown(
            f'<div class="section-card section-card-accent-fatigue">'
            f'<div style="font-size:15px;font-weight:600;color:#c9d1d9;margin-bottom:12px">V6 Model Performance</div>'
            f'{perf_grid}</div>',
            unsafe_allow_html=True,
        )

    # --------------------------------------------------
    # V4 vs V6 Radar Comparison
    # --------------------------------------------------

    if has_v6:
        st.markdown(
            '<div class="section-card section-card-accent-top">'
            '<div style="font-size:15px;font-weight:600;color:#c9d1d9;margin-bottom:12px">Model Comparison Radar</div>',
            unsafe_allow_html=True,
        )

        from fatigue_monitor.src.config import V6_NC_METADATA_PATH

        v6_nc_meta = joblib.load(V6_NC_METADATA_PATH)
        v6_nc_data = v6_nc_meta if isinstance(v6_nc_meta, dict) else {}

        def _safe(v, default=0):
            return float(v) if isinstance(v, (int, float)) and not (isinstance(v, float) and math.isnan(v)) else default

        v4_metrics = {"AUROC": 0.62, "F1@0.50": 0.35, "Bal Acc": 0.56, "Prec@0.50": 0.30, "Recall@0.50": 0.42}
        v6_fat_metrics = {
            "AUROC": _safe(v6_meta.get("auc")),
            "F1@0.50": _safe(v6_meta.get("f1_at_0_50")),
            "Bal Acc": _safe(v6_meta.get("balanced_accuracy_at_0_50")),
            "Prec@0.50": _safe(v6_meta.get("precision_at_0_50")),
            "Recall@0.50": _safe(v6_meta.get("recall_at_0_50")),
        }
        v6_nc_metrics = {
            "AUROC": _safe(v6_nc_data.get("auc")),
            "F1@0.50": _safe(v6_nc_data.get("f1_at_0_50")),
            "Bal Acc": _safe(v6_nc_data.get("balanced_accuracy_at_0_50")),
            "Prec@0.50": _safe(v6_nc_data.get("precision_at_0_50")),
            "Recall@0.50": _safe(v6_nc_data.get("recall_at_0_50")),
        }

        radar_ind = [{"name": k, "max": 1} for k in v4_metrics.keys()]
        v4_vals = list(v4_metrics.values())
        v6f_vals = list(v6_fat_metrics.values())
        v6c_vals = list(v6_nc_metrics.values())

        st_echarts(
            options={
                "tooltip": {
                    "formatter": """function(p){return '<div style="font-weight:600;font-size:13px">'+p.name+'</div><div style="font-size:12px;color:#8a8f9d">'+p.seriesName+': '+(p.value*100).toFixed(1)+'%</div>';}""",
                },
                "legend": {
                    "data": ["V4 XGBoost", "V6 Fatigue", "V6 Perf-Risk"],
                    "textStyle": {"color": "#8b949e"},
                    "top": 0,
                },
                "radar": {
                    "indicator": radar_ind,
                    "center": ["50%", "58%"],
                    "radius": "65%",
                    "axisName": {"color": "#c9d1d9", "fontSize": 11},
                    "splitArea": {"areaStyle": {"color": ["rgba(99,110,250,0.02)", "rgba(46,213,115,0.02)"]}},
                    "splitLine": {"lineStyle": {"color": "#2a2e3a"}},
                    "axisLine": {"lineStyle": {"color": "#2a2e3a"}},
                },
                "series": [
                    {
                        "type": "radar",
                        "data": [
                            {"value": v4_vals, "name": "V4 XGBoost", "areaStyle": {"color": "rgba(99,110,250,0.15)"}, "lineStyle": {"color": "#636EFA", "width": 2}, "itemStyle": {"color": "#636EFA"}},
                            {"value": v6f_vals, "name": "V6 Fatigue", "areaStyle": {"color": "rgba(0,188,140,0.15)"}, "lineStyle": {"color": "#00BC8C", "width": 2}, "itemStyle": {"color": "#00BC8C"}},
                            {"value": v6c_vals, "name": "V6 Perf-Risk", "areaStyle": {"color": "rgba(142,68,173,0.15)"}, "lineStyle": {"color": "#8e44ad", "width": 2}, "itemStyle": {"color": "#8e44ad"}},
                        ],
                        "symbol": "circle",
                        "symbolSize": 5,
                    }
                ],
            },
            height="400px",
        )

        st.markdown("</div>", unsafe_allow_html=True)

    # --------------------------------------------------
    # Per-Player Feature Drivers (V4)
    # --------------------------------------------------

    st.markdown(
        '<div class="section-card section-card-accent-v4">'
        '<div style="font-size:15px;font-weight:600;color:#c9d1d9;margin-bottom:12px">Per-Player Feature Drivers (V4)</div>',
        unsafe_allow_html=True,
    )

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

    st.markdown("</div>", unsafe_allow_html=True)

    # --------------------------------------------------
    # Threshold Policies + Risk Bands
    # --------------------------------------------------

    st.markdown(
        '<div class="section-card section-card-accent-top">'
        '<div style="font-size:15px;font-weight:600;color:#c9d1d9;margin-bottom:12px">Threshold Policies &amp; Risk Bands</div>',
        unsafe_allow_html=True,
    )

    p1, p2 = st.columns(2, vertical_alignment="center")
    with p1:
        st.markdown(
            f'<div style="background:#161b22;border:1px solid #2a2e3a;border-radius:10px;padding:16px">'
            f'<div style="font-size:13px;font-weight:600;color:#636EFA;margin-bottom:10px">V4 Policy</div>'
            f'<div style="display:flex;gap:16px;margin-bottom:8px">'
            f'<div class="stat-block" style="flex:1"><div style="font-size:20px;font-weight:700;color:#e0e0e0">{OPERATING_POLICY["core_starter_threshold"]:.2f}</div><div style="font-size:11px;color:#8a8f9d">Core Starter Threshold</div></div>'
            f'<div class="stat-block" style="flex:1"><div style="font-size:20px;font-weight:700;color:#e0e0e0">{OPERATING_POLICY["rotation_player_threshold"]:.2f}</div><div style="font-size:11px;color:#8a8f9d">Rotation Threshold</div></div>'
            f'</div>'
            f'<div style="font-size:12px;color:#8a8f9d;background:rgba(99,110,250,0.08);padding:8px 12px;border-radius:6px;border:1px solid rgba(99,110,250,0.15)">{OPERATING_POLICY["message"]}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with p2:
        if has_v6:
            v6_policy = v6_meta.get("operating_policy", {}) if isinstance(v6_meta, dict) else {}
            interp = v6_policy.get("interpretation", "V6 monitoring flag indicates workload context for review.")
            st.markdown(
                f'<div style="background:#161b22;border:1px solid #2a2e3a;border-radius:10px;padding:16px">'
                f'<div style="font-size:13px;font-weight:600;color:#00BC8C;margin-bottom:10px">V6 Policy</div>'
                f'<div style="display:flex;gap:16px;margin-bottom:8px">'
                f'<div class="stat-block" style="flex:1"><div style="font-size:20px;font-weight:700;color:#e0e0e0">{v6_policy.get("core_starter_threshold", 0.5):.2f}</div><div style="font-size:11px;color:#8a8f9d">Core Starter Threshold</div></div>'
                f'<div class="stat-block" style="flex:1"><div style="font-size:20px;font-weight:700;color:#e0e0e0">{v6_policy.get("rotation_player_threshold", 0.5):.2f}</div><div style="font-size:11px;color:#8a8f9d">Rotation Threshold</div></div>'
                f'</div>'
                f'<div style="font-size:12px;color:#8a8f9d;background:rgba(0,188,140,0.08);padding:8px 12px;border-radius:6px;border:1px solid rgba(0,188,140,0.15)">{interp}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    bands_html = """
    <div style="overflow-x:auto;margin-top:12px">
        <table style="width:100%;border-collapse:collapse;font-size:13px" class="data-table">
            <thead><tr>
                <th style="padding:8px 12px;text-align:left;color:#8a8f9d;font-size:11px;text-transform:uppercase;letter-spacing:0.5px;border-bottom:1px solid #2a2e3a">Range</th>
                <th style="padding:8px 12px;text-align:left;color:#8a8f9d;font-size:11px;text-transform:uppercase;letter-spacing:0.5px;border-bottom:1px solid #2a2e3a">Label</th>
                <th style="padding:8px 12px;text-align:left;color:#8a8f9d;font-size:11px;text-transform:uppercase;letter-spacing:0.5px;border-bottom:1px solid #2a2e3a">Core Starter</th>
                <th style="padding:8px 12px;text-align:left;color:#8a8f9d;font-size:11px;text-transform:uppercase;letter-spacing:0.5px;border-bottom:1px solid #2a2e3a">Rotation Player</th>
            </tr></thead>
            <tbody>
                <tr style="background:rgba(26,29,39,0.5)"><td style="padding:8px 12px;border-bottom:1px solid #1c2128">0.00 – 0.25</td><td style="padding:8px 12px;border-bottom:1px solid #1c2128"><span class="risk-badge risk-Low">Low</span></td><td style="padding:8px 12px;border-bottom:1px solid #1c2128"><span class="flag-Clear">Clear</span></td><td style="padding:8px 12px;border-bottom:1px solid #1c2128"><span class="flag-Clear">Clear</span></td></tr>
                <tr><td style="padding:8px 12px;border-bottom:1px solid #1c2128">0.25 – 0.45</td><td style="padding:8px 12px;border-bottom:1px solid #1c2128"><span class="risk-badge risk-Medium">Medium</span></td><td style="padding:8px 12px;border-bottom:1px solid #1c2128"><span class="flag-Clear">Clear</span></td><td style="padding:8px 12px;border-bottom:1px solid #1c2128"><span class="flag-Clear">Clear</span></td></tr>
                <tr style="background:rgba(26,29,39,0.5)"><td style="padding:8px 12px;border-bottom:1px solid #1c2128">0.45 – 0.65</td><td style="padding:8px 12px;border-bottom:1px solid #1c2128"><span class="risk-badge risk-High">High</span></td><td style="padding:8px 12px;border-bottom:1px solid #1c2128"><span class="flag-Monitor">Monitor</span></td><td style="padding:8px 12px;border-bottom:1px solid #1c2128"><span class="flag-Monitor">Monitor</span></td></tr>
                <tr><td style="padding:8px 12px;border-bottom:1px solid #1c2128">&gt; 0.65</td><td style="padding:8px 12px;border-bottom:1px solid #1c2128"><span class="risk-badge risk-Very\\ High">Very High</span></td><td style="padding:8px 12px;border-bottom:1px solid #1c2128"><span class="flag-Monitor">Monitor</span></td><td style="padding:8px 12px;border-bottom:1px solid #1c2128"><span class="flag-Monitor">Monitor</span></td></tr>
            </tbody>
        </table>
    </div>
    """
    st.markdown(bands_html, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    with st.expander("Model Limitations & Usage Notes"):
        st.markdown("""
        - **Not a medical/fatigue diagnosis**: Both models identify workload patterns historically
          associated with reduced performance or managed minutes. They do **not** measure actual
          physiological fatigue.
        - **V4 (XGBoost)**: Test AUC-ROC ≈ 0.62. Useful as a screening/ranking tool.
        - **V6 No Rating Baseline**: Test AUC-ROC ≈ 0.61, balanced accuracy ≈ 0.57 — clean fatigue signal.
        - **V6 No Competition**: Test AUC-ROC ≈ 0.68, balanced accuracy ≈ 0.62 — includes rating regression signal.
        - **Temporal generalization**: Trained on 2022-23, validated on 2023-24, tested on 2024-25.
        - **Data limitations**: Uses SofaScore/API ratings as a performance proxy.
          GPS tracking, heart rate, or subjective wellness data are not available.
        """)
