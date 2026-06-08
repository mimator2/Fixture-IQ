import streamlit as st
import pandas as pd
import joblib
from fatigue_monitor.src.config import OPERATING_POLICY, V6_OPERATING_POLICY, V6_NR_METADATA_PATH


def about_page():
    st.markdown("## About the Fatigue Monitor — Dual-Score System")

    # --------------------------------------------------
    # PURPOSE CARD
    # --------------------------------------------------

    st.markdown(
        '<div class="section-card section-card-accent-top">'
        '<div style="font-size:15px;font-weight:600;color:#c9d1d9;margin-bottom:12px">Purpose</div>'
        '<div style="font-size:13px;color:#e0e0e0;line-height:1.6">'
        "This dashboard integrates <strong>three models</strong> for post-match / pre-next-match monitoring:"
        "</div>",
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns(3, vertical_alignment="center")
    with c1:
        st.markdown(
            '<div class="stat-block" style="min-height:120px">'
            '<div class="stat-icon">📊</div>'
            '<div class="stat-value" style="font-size:15px">V4 (XGBoost)</div>'
            '<div class="stat-label">Legacy workload risk</div>'
            '</div>',
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            '<div class="stat-block" style="min-height:120px;border-top-color:#00BC8C">'
            '<div class="stat-icon">🟢</div>'
            '<div class="stat-value" style="font-size:15px">V6 Fatigue</div>'
            '<div class="stat-label">No Rating Baseline</div>'
            '</div>',
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            '<div class="stat-block" style="min-height:120px;border-top-color:#8e44ad">'
            '<div class="stat-icon">🟣</div>'
            '<div class="stat-value" style="font-size:15px">V6 Perf-Risk</div>'
            '<div class="stat-label">No Competition</div>'
            '</div>',
            unsafe_allow_html=True,
        )

    st.markdown(
        '<div style="font-size:12px;color:#8a8f9d;margin-top:8px;line-height:1.5">'
        "All models process the same player-match data through their respective feature-engineering "
        "pipelines. Outputs are <strong>workload-associated risk scores</strong> intended as monitoring support, "
        "<strong>not</strong> as definitive fatigue diagnoses."
        "</div>",
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

    # --------------------------------------------------
    # TWO-SCORE SYSTEM
    # --------------------------------------------------

    st.markdown(
        '<div class="section-card section-card-accent-top">'
        '<div style="font-size:15px;font-weight:600;color:#c9d1d9;margin-bottom:12px">Two-Score System</div>'
        '<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">',
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2, vertical_alignment="center")
    with col1:
        st.markdown(
            '<div style="background:#161b22;border:1px solid #2a2e3a;border-radius:10px;padding:16px;border-left:3px solid #00BC8C">'
            '<div style="font-size:13px;font-weight:600;color:#00BC8C;margin-bottom:8px">Fatigue/Workload Score</div>'
            '<div style="font-size:11px;color:#8a8f9d;line-height:1.5">V6 No Rating Baseline — Primary coach-facing metric. Pure fatigue-workload-action-load-injury signal. Excludes rating/form.</div>'
            '<div style="margin-top:8px;font-size:12px;color:#c9d1d9">AUROC: 0.606 · F1@0.5: 0.381</div>'
            '</div>',
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            '<div style="background:#161b22;border:1px solid #2a2e3a;border-radius:10px;padding:16px;border-left:3px solid #8e44ad">'
            '<div style="font-size:13px;font-weight:600;color:#8e44ad;margin-bottom:8px">Performance-Risk Score</div>'
            '<div style="font-size:11px;color:#8a8f9d;line-height:1.5">V6 No Competition — Analyst/secondary metric. Includes rating baseline to detect form regression risk.</div>'
            '<div style="margin-top:8px;font-size:12px;color:#c9d1d9">AUROC: 0.678 · F1@0.5: 0.449</div>'
            '</div>',
            unsafe_allow_html=True,
        )

    st.markdown("</div></div>", unsafe_allow_html=True)

    # --------------------------------------------------
    # OPERATING POLICIES
    # --------------------------------------------------

    st.markdown(
        '<div class="section-card section-card-accent-top">'
        '<div style="font-size:15px;font-weight:600;color:#c9d1d9;margin-bottom:12px">Operating Policies</div>'
        '<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">',
        unsafe_allow_html=True,
    )

    p1, p2 = st.columns(2, vertical_alignment="center")
    with p1:
        st.markdown(
            f'<div style="background:#161b22;border:1px solid #2a2e3a;border-radius:10px;padding:16px">'
            f'<div style="font-size:12px;font-weight:600;color:#636EFA;margin-bottom:8px">V4 Policy</div>'
            f'<div style="display:flex;gap:10px;margin-bottom:8px">'
            f'<div class="stat-block" style="flex:1;padding:10px"><div style="font-size:18px;font-weight:700;color:#e0e0e0">{OPERATING_POLICY["core_starter_threshold"]:.2f}</div><div style="font-size:10px;color:#8a8f9d">Core Starter</div></div>'
            f'<div class="stat-block" style="flex:1;padding:10px"><div style="font-size:18px;font-weight:700;color:#e0e0e0">{OPERATING_POLICY["rotation_player_threshold"]:.2f}</div><div style="font-size:10px;color:#8a8f9d">Rotation</div></div>'
            f'</div>'
            f'<div style="font-size:11px;color:#8a8f9d;background:rgba(99,110,250,0.06);padding:6px 10px;border-radius:6px">{OPERATING_POLICY["message"]}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with p2:
        st.markdown(
            f'<div style="background:#161b22;border:1px solid #2a2e3a;border-radius:10px;padding:16px">'
            f'<div style="font-size:12px;font-weight:600;color:#00BC8C;margin-bottom:8px">V6 Policy (both variants)</div>'
            f'<div style="display:flex;gap:10px;margin-bottom:8px">'
            f'<div class="stat-block" style="flex:1;padding:10px"><div style="font-size:18px;font-weight:700;color:#e0e0e0">{V6_OPERATING_POLICY["core_starter_threshold"]:.2f}</div><div style="font-size:10px;color:#8a8f9d">Core Starter</div></div>'
            f'<div class="stat-block" style="flex:1;padding:10px"><div style="font-size:18px;font-weight:700;color:#e0e0e0">{V6_OPERATING_POLICY["rotation_player_threshold"]:.2f}</div><div style="font-size:10px;color:#8a8f9d">Rotation</div></div>'
            f'</div>'
            f'<div style="font-size:11px;color:#8a8f9d;background:rgba(0,188,140,0.06);padding:6px 10px;border-radius:6px">{V6_OPERATING_POLICY["message"]}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.markdown("</div></div>", unsafe_allow_html=True)

    # --------------------------------------------------
    # RISK BANDS TABLE
    # --------------------------------------------------

    st.markdown(
        '<div class="section-card section-card-accent-top">'
        '<div style="font-size:15px;font-weight:600;color:#c9d1d9;margin-bottom:12px">Risk Bands (shared)</div>',
        unsafe_allow_html=True,
    )

    bands_html = """
    <div style="overflow-x:auto">
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

    # --------------------------------------------------
    # MODEL PERFORMANCE
    # --------------------------------------------------

    st.markdown(
        '<div class="section-card section-card-accent-v4">'
        '<div style="font-size:15px;font-weight:600;color:#c9d1d9;margin-bottom:12px">V4 Model Performance</div>',
        unsafe_allow_html=True,
    )

    v4_table = """
    <div style="overflow-x:auto">
        <table style="width:100%;border-collapse:collapse;font-size:13px" class="data-table">
            <thead><tr>
                <th style="padding:8px 12px;text-align:left;color:#8a8f9d;font-size:11px;text-transform:uppercase;letter-spacing:0.5px;border-bottom:1px solid #2a2e3a">Metric</th>
                <th style="padding:8px 12px;text-align:left;color:#8a8f9d;font-size:11px;text-transform:uppercase;letter-spacing:0.5px;border-bottom:1px solid #2a2e3a">Value</th>
            </tr></thead>
            <tbody>
                <tr style="background:rgba(26,29,39,0.5)"><td style="padding:8px 12px;border-bottom:1px solid #1c2128">Test AUC-ROC</td><td style="padding:8px 12px;border-bottom:1px solid #1c2128;font-weight:600;color:#c9d1d9">0.627</td></tr>
                <tr><td style="padding:8px 12px;border-bottom:1px solid #1c2128">Test AUC-PR</td><td style="padding:8px 12px;border-bottom:1px solid #1c2128;font-weight:600;color:#c9d1d9">0.390</td></tr>
                <tr style="background:rgba(26,29,39,0.5)"><td style="padding:8px 12px;border-bottom:1px solid #1c2128">Base Rate</td><td style="padding:8px 12px;border-bottom:1px solid #1c2128;font-weight:600;color:#c9d1d9">0.286</td></tr>
                <tr><td style="padding:8px 12px;border-bottom:1px solid #1c2128">Best Threshold</td><td style="padding:8px 12px;border-bottom:1px solid #1c2128;font-weight:600;color:#c9d1d9">0.449</td></tr>
                <tr style="background:rgba(26,29,39,0.5)"><td style="padding:8px 12px;border-bottom:1px solid #1c2128">Numerical Features</td><td style="padding:8px 12px;border-bottom:1px solid #1c2128;font-weight:600;color:#c9d1d9">77</td></tr>
                <tr><td style="padding:8px 12px;border-bottom:1px solid #1c2128">Categorical Features</td><td style="padding:8px 12px;border-bottom:1px solid #1c2128;font-weight:600;color:#c9d1d9">1 (player_position)</td></tr>
            </tbody>
        </table>
    </div>
    """
    st.markdown(v4_table, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    try:
        v6_meta = joblib.load(V6_NR_METADATA_PATH)
        if isinstance(v6_meta, dict):
            st.markdown(
                '<div class="section-card section-card-accent-fatigue">'
                '<div style="font-size:15px;font-weight:600;color:#c9d1d9;margin-bottom:12px">V6 No Rating Baseline Performance</div>',
                unsafe_allow_html=True,
            )

            v6_perf_rows = [
                ("AUROC", f"{v6_meta.get('auc', '—'):.4f}" if isinstance(v6_meta.get('auc'), (int, float)) else '—'),
                ("PR-AUC", f"{v6_meta.get('pr_auc', '—'):.4f}" if isinstance(v6_meta.get('pr_auc'), (int, float)) else '—'),
                ("F1@0.50", f"{v6_meta.get('f1_at_0_50', '—'):.4f}" if isinstance(v6_meta.get('f1_at_0_50'), (int, float)) else '—'),
                ("Precision@0.50", f"{v6_meta.get('precision_at_0_50', '—'):.4f}" if isinstance(v6_meta.get('precision_at_0_50'), (int, float)) else '—'),
                ("Recall@0.50", f"{v6_meta.get('recall_at_0_50', '—'):.4f}" if isinstance(v6_meta.get('recall_at_0_50'), (int, float)) else '—'),
                ("Balanced Accuracy", f"{v6_meta.get('balanced_accuracy_at_0_50', '—'):.4f}" if isinstance(v6_meta.get('balanced_accuracy_at_0_50'), (int, float)) else '—'),
                ("Features", str(len(v6_meta.get('features', [])))),
            ]
            v6_rows_html = ""
            for i, (metric, val) in enumerate(v6_perf_rows):
                bg = ' style="background:rgba(26,29,39,0.5)"' if i % 2 == 0 else ""
                v6_rows_html += f'<tr{bg}><td style="padding:8px 12px;border-bottom:1px solid #1c2128">{metric}</td><td style="padding:8px 12px;border-bottom:1px solid #1c2128;font-weight:600;color:#c9d1d9">{val}</td></tr>'

            st.markdown(
                f'<div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;font-size:13px" class="data-table">'
                f'<thead><tr><th style="padding:8px 12px;text-align:left;color:#8a8f9d;font-size:11px;text-transform:uppercase;letter-spacing:0.5px;border-bottom:1px solid #2a2e3a">Metric</th>'
                f'<th style="padding:8px 12px;text-align:left;color:#8a8f9d;font-size:11px;text-transform:uppercase;letter-spacing:0.5px;border-bottom:1px solid #2a2e3a">Value</th></tr></thead>'
                f'<tbody>{v6_rows_html}</tbody></table></div>',
                unsafe_allow_html=True,
            )
            st.markdown("</div>", unsafe_allow_html=True)
    except Exception:
        pass

    # --------------------------------------------------
    # TOP FEATURES
    # --------------------------------------------------

    st.markdown(
        '<div class="section-card section-card-accent-v4">'
        '<div style="font-size:15px;font-weight:600;color:#c9d1d9;margin-bottom:12px">V4 Top Contributing Features</div>'
        '<div style="font-size:12px;color:#8a8f9d;margin-bottom:10px">The V4 model\'s leading features are workload-related, consistent with fatigue monitoring:</div>'
        '<div style="display:flex;flex-wrap:wrap;gap:6px">',
        unsafe_allow_html=True,
    )

    v4_feats = [
        ("matches_with_rest_le_4d_last_30d", "Matches with ≤4 days rest", "#e74c3c"),
        ("matches_with_rest_le_6d_last_30d", "Matches with ≤6 days rest", "#f39c12"),
        ("full_90s_last_14d", "Full-90 appearances (14d)", "#636EFA"),
        ("full_90s_last_28d", "Full-90 appearances (28d)", "#636EFA"),
        ("rest_days", "Days since last match", "#00BC8C"),
        ("starts_last_14d", "Starts in last 14 days", "#636EFA"),
        ("ucl_matches_last_30d", "UCL matches (30d)", "#8e44ad"),
    ]
    for feat, desc, color in v4_feats:
        st.markdown(
            f'<span class="tag-pill" style="background:{color}15;color:{color};border-color:{color}33;font-size:12px;padding:4px 12px">'
            f'<span style="font-weight:600">{feat}</span> — {desc}</span>',
            unsafe_allow_html=True,
        )

    st.markdown("</div></div>", unsafe_allow_html=True)

    st.markdown(
        '<div class="section-card section-card-accent-fatigue">'
        '<div style="font-size:15px;font-weight:600;color:#c9d1d9;margin-bottom:12px">V6 Feature Groups</div>',
        unsafe_allow_html=True,
    )
    try:
        v6_meta_l = v6_meta if isinstance(v6_meta, dict) else {}
        v6_groups = v6_meta_l.get("feature_groups", {})
        st.markdown(
            '<div style="font-size:12px;color:#8a8f9d;margin-bottom:10px">The V6 model organises features into these groups:</div>',
            unsafe_allow_html=True,
        )
        group_colors = ["#636EFA", "#00BC8C", "#f39c12", "#e74c3c", "#8e44ad", "#27ae60", "#1a6bff"]
        for i, (gname, gfeats) in enumerate(v6_groups.items()):
            c = group_colors[i % len(group_colors)]
            st.markdown(
                f'<span class="tag-pill" style="background:{c}15;color:{c};border-color:{c}33;font-size:12px;padding:4px 12px">'
                f'<span style="font-weight:600">{gname}</span> ({len(gfeats)} features)</span>',
                unsafe_allow_html=True,
            )
    except Exception:
        default_groups = ["role_context", "missingness_context", "workload_recovery_windows", "competition_sequence_load", "recent_action_load", "position_adjusted_load", "injury_context"]
        group_colors = ["#636EFA", "#00BC8C", "#f39c12", "#e74c3c", "#8e44ad", "#27ae60", "#1a6bff"]
        for i, gname in enumerate(default_groups):
            c = group_colors[i % len(group_colors)]
            st.markdown(
                f'<span class="tag-pill" style="background:{c}15;color:{c};border-color:{c}33;font-size:12px;padding:4px 12px">'
                f'<span style="font-weight:600">{gname}</span></span>',
                unsafe_allow_html=True,
            )

    st.markdown("</div>", unsafe_allow_html=True)

    # --------------------------------------------------
    # DATA SOURCES
    # --------------------------------------------------

    st.markdown(
        '<div class="section-card section-card-accent-top">'
        '<div style="font-size:15px;font-weight:600;color:#c9d1d9;margin-bottom:12px">Data Sources</div>',
        unsafe_allow_html=True,
    )

    def _data_card(title, summary, tags):
        tag_html = "".join(
            f'<span class="tag-pill" style="background:{c}22;color:{c};border-color:{c}33;font-size:10px;padding:1px 8px;margin-right:4px;margin-bottom:4px;display:inline-block">{t}</span>'
            for t, c in tags
        )
        st.markdown(
            f'<div class="hover-lift" style="background:#161b22;border:1px solid #2a2e3a;border-radius:10px;padding:16px;margin-bottom:10px">'
            f'<div style="font-weight:600;font-size:14px;color:#c9d1d9;margin-bottom:4px">{title}</div>'
            f'<div style="font-size:12px;color:#8a8f9d;margin-bottom:8px;line-height:1.4">{summary}</div>'
            f'<div>{tag_html}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    _data_card(
        "Match & Player Event Data",
        "SofaScore/Fbref match logs, player appearances, substitutions, minutes played, action counts, and ratings for all competitions (PL, UCL, Cup) from 2022–2025 seasons.",
        [("1,200+ matches", "#636EFA"), ("36 players", "#00BC8C"), ("152 features (V6)", "#f39c12")],
    )
    _data_card(
        "Fixture Schedule",
        "Upcoming and historical fixture calendar used to compute rest days, short-rest windows, competition sequences, and fixture congestion metrics.",
        [("Rest ≤4d flags", "#e74c3c"), ("Competition transitions", "#8e44ad"), ("Cup/UCL burden", "#27ae60")],
    )
    _data_card(
        "Player Role Context",
        "28-day (V4) and 5-match (V6) rolling role assignments (core starter, rotation, squad, impact sub). Position-adjusted Z-scores for physical effort metrics.",
        [("Rolling windows", "#636EFA"), ("Position Z-scores", "#00BC8C")],
    )
    _data_card(
        "Injury & Availability",
        "Squad injury counts, returning-from-injury flags, injury context scores based on recent minutes dips and missed fixtures.",
        [("11 injury context flags", "#e74c3c"), ("Context score", "#f39c12")],
    )
    st.markdown("</div>", unsafe_allow_html=True)

    # --------------------------------------------------
    # TECHNOLOGY STACK
    # --------------------------------------------------

    st.markdown(
        '<div class="section-card section-card-accent-top">'
        '<div style="font-size:15px;font-weight:600;color:#c9d1d9;margin-bottom:12px">Technology Stack</div>'
        '<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px">',
        unsafe_allow_html=True,
    )

    techs = [
        ("📊", "V4 Model", "XGBoost Classifier\nv4b_no_competition"),
        ("🟢", "V6 Models", "CatBoost Classifier\nv6_no_competition, v6_no_rating_baseline"),
        ("⚡", "Framework", "Streamlit + streamlit-echarts"),
        ("💾", "Artifacts", "joblib, .cbm, .pkl"),
        ("📁", "Data", "SofaScore/Fbref\n2022–2025"),
        ("🔧", "Pipeline", "Custom feature engineering\nV4 + V6 variants"),
    ]
    for icon, title, desc in techs:
        st.markdown(
            f'<div class="stat-block" style="padding:14px;min-height:90px">'
            f'<div class="stat-icon">{icon}</div>'
            f'<div class="stat-value" style="font-size:13px">{title}</div>'
            f'<div class="stat-label" style="font-size:10px;white-space:pre-line">{desc}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.markdown("</div></div>", unsafe_allow_html=True)

    # --------------------------------------------------
    # LIMITATIONS
    # --------------------------------------------------

    with st.expander("Model Limitations & Usage Notes"):
        st.markdown("""
        - **Not a medical/fatigue diagnosis**: All models identify workload patterns historically
          associated with reduced performance or managed minutes. They do **not** measure actual
          physiological fatigue.
        - **V4 (XGBoost)**: Test AUC-ROC ≈ 0.62. Useful as a screening/ranking tool.
        - **V6 No Rating Baseline**: Test AUC-ROC ≈ 0.61 — cleaner fatigue signal.
        - **V6 No Competition**: Test AUC-ROC ≈ 0.68 — includes rating regression signal.
        - **Temporal generalization**: Trained on 2022-23, validated on 2023-24, tested on 2024-25.
          Performance may differ in future seasons.
        - **Data limitations**: Uses SofaScore/API ratings as a performance proxy. GPS tracking,
          heart rate, or subjective wellness data are not available.
        - **Role assignment**: V4 roles are based on a 28-day rolling window; V6 roles use a 5-match
          window. A player's role may shift during the season.
        """)
