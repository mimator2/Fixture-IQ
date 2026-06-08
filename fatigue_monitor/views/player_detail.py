import streamlit as st
import pandas as pd
import math
from streamlit_echarts import st_echarts


def _sc(title, content_html, accent_class="section-card-accent-top"):
    return f'<div class="section-card {accent_class}"><div style="font-size:15px;font-weight:600;color:#c9d1d9;margin-bottom:12px">{title}</div>{content_html}</div>'


def _sb(icon, value, label, sub=""):
    sub_html = f'<div style="font-size:10px;color:#5a5f6d;margin-top:1px">{sub}</div>' if sub else ""
    return f'<div class="stat-block"><div class="stat-icon">{icon}</div><div class="stat-value">{value}</div><div class="stat-label">{label}</div>{sub_html}</div>'


def _pill(text, color="#636EFA"):
    return f'<span class="tag-pill" style="background:{color}18;color:{color};border-color:{color}33">{text}</span>'


def player_detail_page():

    st.title("Player Detail View")

    st.markdown("""
        <div class="fg-subtle" style="font-size:13px;margin-bottom:20px">
        In-depth fatigue risk assessment for a single player across all three models.
        </div>
    """, unsafe_allow_html=True)

    # --------------------------------------------------
    # SAFE SESSION ACCESS
    # --------------------------------------------------

    results = st.session_state.get("results_df", None)

    if results is None:
        st.warning("Data is loading... please return to Home or refresh.")
        st.stop()

    # --------------------------------------------------
    # BACK BUTTON
    # --------------------------------------------------

    if st.button("← Back to Overview"):
        st.session_state.selected_player = None
        st.switch_page("Home.py")

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
    # PLAYER HEADER
    # --------------------------------------------------

    st.markdown(
        f'<div style="display:flex;align-items:center;gap:16px;margin:20px 0 24px 0">'
        f'<div style="width:48px;height:48px;border-radius:12px;background:linear-gradient(135deg,#00BC8C,#009d73);display:flex;align-items:center;justify-content:center;font-size:24px">👤</div>'
        f'<div><div style="font-size:22px;font-weight:700;color:#e0e0e0">{player}</div>'
        f'<div style="font-size:13px;color:#8a8f9d">{prow.get("player_team","—")} · {prow.get("player_position","—")}</div></div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # --------------------------------------------------
    # A. V4 SECTION
    # --------------------------------------------------

    v4_html = f"""
    <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin-bottom:14px">
        {_sb("📊",f"{prow.get('risk_score_v4',0):.3f}","Risk Score")}
        {_sb("🏷️",prow.get('risk_band_v4','—'),"Risk Band")}
        {_sb("🎯",prow.get('player_role_v4','—'),"Role")}
        {_sb("⚡",f"{prow.get('monitoring_threshold_v4',0):.2f}","Threshold")}
        {_sb("📅",f"{prow.get('rest_days',0):.0f}","Rest Days")}
    </div>
    """
    expl_v4 = prow.get("explanation_v4", "")
    if expl_v4:
        items = [x.strip() for x in expl_v4.split(";") if x.strip()]
        v4_html += '<div style="margin-top:8px">' + "".join(_pill(it, "#636EFA") for it in items) + "</div>"

    st.markdown(_sc("A. V4 (XGBoost) — Workload-Associated Risk", v4_html, "section-card-accent-v4"), unsafe_allow_html=True)

    # --------------------------------------------------
    # B. V6 FATIGUE SECTION
    # --------------------------------------------------

    has_v6_fatigue = "risk_score_v6_fatigue" in prow.index
    if has_v6_fatigue:
        v6f_html = f"""
        <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin-bottom:14px">
            {_sb("📊",f"{prow['risk_score_v6_fatigue']:.3f}","Risk Score")}
            {_sb("🏷️",prow.get('risk_band_v6_fatigue','—'),"Risk Band")}
            {_sb("🎯",prow.get('player_role_v6','—'),"Role")}
            {_sb("⚡",f"{prow.get('monitoring_threshold_v6_fatigue',0):.2f}","Threshold")}
            {_sb("📅",f"{prow.get('rest_days',0):.0f}","Rest Days")}
        </div>
        """
        v6_reasons = prow.get("main_risk_reasons_v6_fatigue", "")
        if v6_reasons:
            items = [x.strip() for x in v6_reasons.split(",") if x.strip()]
            v6f_html += '<div style="margin-top:8px">' + "".join(_pill(it, "#00BC8C") for it in items) + "</div>"
        st.markdown(_sc("B. V6 (CatBoost) — Fatigue / Workload Score", v6f_html, "section-card-accent-fatigue"), unsafe_allow_html=True)

    # --------------------------------------------------
    # C. V6 PERFORMANCE-RISK SECTION
    # --------------------------------------------------

    has_v6_perf = "risk_score_v6_perf" in prow.index
    if has_v6_perf:
        v6p_html = f"""
        <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin-bottom:14px">
            {_sb("📊",f"{prow['risk_score_v6_perf']:.3f}","Risk Score")}
            {_sb("🏷️",prow.get('risk_band_v6_perf','—'),"Risk Band")}
            {_sb("🎯",prow.get('player_role_v6','—'),"Role")}
            {_sb("⚡",f"{prow.get('monitoring_threshold_v6_perf',0):.2f}","Threshold")}
            {_sb("📅",f"{prow.get('rest_days',0):.0f}","Rest Days")}
        </div>
        """
        st.markdown(_sc("C. V6 (CatBoost) — Performance-Risk Score", v6p_html, "section-card-accent-perf"), unsafe_allow_html=True)

    # --------------------------------------------------
    # GAUGE CHARTS
    # --------------------------------------------------

    g1, g2, g3 = st.columns(3, vertical_alignment="center")

    def _safe_score(val):
        if val is None or (isinstance(val, float) and math.isnan(val)):
            return 0.0
        return float(val)

    scores = [
        ("V4 Risk", _safe_score(prow.get("risk_score_v4", 0))),
    ]
    if has_v6_fatigue:
        scores.append(("V6 Fatigue", _safe_score(prow["risk_score_v6_fatigue"])))
    if has_v6_perf:
        scores.append(("V6 Performance", _safe_score(prow["risk_score_v6_perf"])))

    gauge_html = ""
    for col, (label, score) in zip([g1, g2, g3][:len(scores)], scores):
        with col:
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
                            "data": [{"value": score, "name": label}],
                            "detail": {
                                "formatter": "{value}",
                                "fontSize": 22,
                            },
                            "title": {
                                "show": True,
                                "offsetCenter": [0, "85%"],
                                "fontSize": 13,
                                "color": "#c9d1d9",
                            },
                        }
                    ]
                },
                height="270px",
            )

    # --------------------------------------------------
    # WORKLOAD RADAR + CONTEXT
    # --------------------------------------------------

    st.markdown(
        '<div class="section-card section-card-accent-top" style="margin-top:8px">'
        '<div style="font-size:15px;font-weight:600;color:#c9d1d9;margin-bottom:12px">Workload Context</div>',
        unsafe_allow_html=True,
    )

    def _normalize(val, cap, invert=False):
        v = min(float(val) if val and not (isinstance(val, float) and math.isnan(val)) else 0, cap)
        n = v / cap
        return 1 - n if invert else n

    m14 = prow.get("min_last_14d", 0)
    f90 = prow.get("full_90s_last_14d", 0)
    rest = prow.get("rest_days", 14)
    acwr = prow.get("acwr_ratio", 0)
    inj = prow.get("squad_injured_count", 0)
    starts = prow.get("starts_last_14d", 0)

    radar_indicators = [
        {"name": "Min Last 14d", "max": 1},
        {"name": "Full 90s", "max": 1},
        {"name": "Rest Days ↓", "max": 1},
        {"name": "ACWR", "max": 1},
        {"name": "Squad Inj", "max": 1},
        {"name": "Starts", "max": 1},
    ]

    radarc, metc = st.columns([0.45, 0.55], vertical_alignment="center")
    with radarc:
        rdata = [
            _normalize(m14, 270),
            _normalize(f90, 5),
            _normalize(rest, 10, invert=True),
            _normalize(acwr, 2),
            _normalize(inj, 8),
            _normalize(starts, 5),
        ]
        st_echarts(
            options={
                "tooltip": {
                    "formatter": """function(p){var v=Math.round(p.value*100);return '<div style="font-weight:600;font-size:13px">'+p.name+'</div><div style="font-size:12px;color:#8a8f9d">Score: '+v+'/100</div>';}""",
                },
                "radar": {
                    "indicator": radar_indicators,
                    "center": ["50%", "50%"],
                    "radius": "65%",
                    "axisName": {"color": "#c9d1d9", "fontSize": 11},
                    "splitArea": {"areaStyle": {"color": ["rgba(39,174,96,0.02)", "rgba(243,156,18,0.02)", "rgba(231,76,60,0.02)"]}},
                    "splitLine": {"lineStyle": {"color": "#2a2e3a"}},
                    "axisLine": {"lineStyle": {"color": "#2a2e3a"}},
                },
                "series": [
                    {
                        "type": "radar",
                        "data": [{"value": rdata, "name": "Player", "areaStyle": {"color": "rgba(0,188,140,0.2)"}, "lineStyle": {"color": "#00BC8C", "width": 2}, "itemStyle": {"color": "#00BC8C"}}],
                        "symbol": "circle",
                        "symbolSize": 6,
                    }
                ],
            },
            height="280px",
        )

    with metc:
        wcs = st.columns(2)
        wcs[0].markdown(_sb("⏱️", f"{m14:.0f}" if pd.notna(m14) else "—", "Minutes Last 14d"), unsafe_allow_html=True)
        wcs[1].markdown(_sb("📅", f"{prow.get('min_last_28d', 0):.0f}" if pd.notna(prow.get('min_last_28d')) else "—", "Minutes Last 28d"), unsafe_allow_html=True)
        wcs = st.columns(2)
        wcs[0].markdown(_sb("🏁", f"{int(f90)}" if pd.notna(f90) else "—", "Full 90s Last 14d"), unsafe_allow_html=True)
        wcs[1].markdown(_sb("🎯", f"{int(starts)}" if pd.notna(starts) else "—", "Starts Last 14d"), unsafe_allow_html=True)
        wcs = st.columns(2)
        wcs[0].markdown(_sb("💤", f"{rest:.0f}" if pd.notna(rest) else "—", "Rest Days"), unsafe_allow_html=True)
        wcs[1].markdown(_sb("📈", f"{acwr:.2f}" if pd.notna(acwr) else "—", "ACWR Ratio"), unsafe_allow_html=True)
        wcs = st.columns(2)
        wcs[0].markdown(_sb("🏥", f"{int(inj)}" if pd.notna(inj) else "—", "Squad Injuries"), unsafe_allow_html=True)
        wcs[1].markdown(_sb("⚡", f"{prow.get('recent_action_load_per90',0):.1f}" if pd.notna(prow.get('recent_action_load_per90')) else "—", "Action Load Per90"), unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)
