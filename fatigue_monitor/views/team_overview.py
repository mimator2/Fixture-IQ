import streamlit as st
import pandas as pd
from streamlit_echarts import st_echarts


def team_overview_page():

    st.markdown("""
        ### Team Overview
                
        This page provides a comprehensive overview of player fatigue risk across the team. Use the filters to narrow down by team, position, role, risk band, or monitoring flag. Click on "View Detail" to jump to an individual player's detail page for deeper insights.
    """)


    results = st.session_state.results_df
    if results is None:
        st.info("No prediction data loaded. Use the data loader at the top of the page first.")
        return

    results = results.sort_values("date", ascending=False).groupby("player_name", as_index=False).first()
    results = results.reset_index(drop=True)

    with st.container(border=True):
        s1, s2 = st.columns([4, 1], vertical_alignment="center")
        with s1:
            player_list = sorted(results["player_name"].unique())
            sel_player = st.selectbox("Quick jump to player detail", player_list, index=None, placeholder="Select a player...", key="ov_player_sel")
        with s2:
            if sel_player and st.button("View Detail", type="primary", use_container_width=True, key="ov_go_btn"):
                st.session_state.selected_player = sel_player
                st.switch_page("pages/1_Player.py")

    with st.container(border=True):
        cols = st.columns([1, 1, 1, 1, 1], vertical_alignment="bottom")
        with cols[0]:
            teams = ["All"] + sorted(results["player_team"].unique())
            team_sel = st.selectbox("Team", teams)
        with cols[1]:
            positions = ["All"] + sorted(results["player_position"].unique())
            pos_sel = st.selectbox("Position", positions)
        with cols[2]:
            roles = ["All"] + sorted(results["player_role_v4"].unique())
            role_sel = st.selectbox("Role", roles)
        with cols[3]:
            bands = ["All"] + [b for b in ["Low", "Medium", "High", "Very High"] if b in results["risk_band_v4"].cat.categories]
            band_sel = st.selectbox("Risk Band", bands)
        with cols[4]:
            flags = ["All", "Monitor", "Clear"]
            flag_sel = st.selectbox("Monitoring Flag", flags)

    filtered = results.copy()
    if team_sel != "All":
        filtered = filtered[filtered["player_team"] == team_sel]
    if pos_sel != "All":
        filtered = filtered[filtered["player_position"] == pos_sel]
    if role_sel != "All":
        filtered = filtered[filtered["player_role_v4"] == role_sel]
    if band_sel != "All":
        filtered = filtered[filtered["risk_band_v4"] == band_sel]
    if flag_sel == "Monitor":
        filtered = filtered[filtered["monitoring_flag_v4"] == 1]
    elif flag_sel == "Clear":
        filtered = filtered[filtered["monitoring_flag_v4"] == 0]

    flagged = int(filtered["monitoring_flag_v4"].sum())
    total = len(filtered)
    avg_risk = filtered["risk_score_v4"].mean()
    high_risk = int((filtered["risk_band_v4"] == "High").sum())
    vhigh_risk = int((filtered["risk_band_v4"] == "Very High").sum())

    k1, k2, k3, k4, k5 = st.columns(5, vertical_alignment="center")
    k1.metric("Players", f"{total}")
    k2.metric("Flagged for Monitoring", f"{flagged}", delta=f"{flagged/total*100:.0f}%" if total else None)
    k3.metric("Avg Risk Score", f"{avg_risk:.3f}")
    k4.metric("High Risk", f"{high_risk}")
    k5.metric("Very High Risk", f"{vhigh_risk}")

    c1, c2 = st.columns([0.6, 0.4], vertical_alignment="center")

    with c1:
        band_counts = filtered["risk_band_v4"].value_counts().reindex(["Low", "Medium", "High", "Very High"])
        band_colors = {"Low": "#27ae60", "Medium": "#f39c12", "High": "#e74c3c", "Very High": "#8e44ad"}
        band_data = [{"value": int(v), "itemStyle": {"color": band_colors.get(k, "#636EFA")}} for k, v in band_counts.items()]
        st_echarts(
            options={
                "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
                "grid": {"left": "3%", "right": "4%", "bottom": "3%", "top": "15%", "containLabel": True},
                "xAxis": {"type": "category", "data": list(band_counts.index), "axisLabel": {"color": "#8b949e"}},
                "yAxis": {"type": "value", "axisLabel": {"color": "#8b949e"}},
                "series": [
                    {
                        "type": "bar",
                        "data": band_data,
                        "barWidth": "50%",
                        "label": {"show": True, "position": "top", "color": "#c9d1d9", "fontSize": 12},
                    }
                ],
            },
            height="320px",
        )

    with c2:
        role_counts = filtered.groupby("player_role_v4").agg(
            Count=("risk_score_v4", "count"),
            Flagged=("monitoring_flag_v4", "sum"),
        ).reset_index()
        roles_list = list(role_counts["player_role_v4"])
        st_echarts(
            options={
                "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
                "legend": {"data": ["Total", "Flagged"], "textStyle": {"color": "#8b949e"}, "top": 0},
                "grid": {"left": "3%", "right": "4%", "bottom": "3%", "top": "18%", "containLabel": True},
                "xAxis": {"type": "category", "data": roles_list, "axisLabel": {"color": "#8b949e"}},
                "yAxis": {"type": "value", "axisLabel": {"color": "#8b949e"}},
                "series": [
                    {
                        "name": "Total",
                        "type": "bar",
                        "data": [int(v) for v in role_counts["Count"]],
                        "itemStyle": {"color": "#636EFA"},
                    },
                    {
                        "name": "Flagged",
                        "type": "bar",
                        "data": [int(v) for v in role_counts["Flagged"]],
                        "itemStyle": {"color": "#e74c3c"},
                    },
                ],
            },
            height="320px",
        )

    st.markdown("### Player Risk Overview")
    display_cols = [
        "player_name", "player_team", "player_position", "player_role_v4",
        "risk_score_v4", "risk_band_v4", "monitoring_flag_v4", "monitoring_threshold_v4",
        "explanation_v4", "minutes_played", "rest_days",
        "min_last_14d", "full_90s_last_14d", "matches_with_rest_le_4d_last_30d",
        "ucl_minutes_last_14d", "cup_minutes_last_14d",
        "squad_injured_count", "physical_load_index",
    ]
    avail_cols = [c for c in display_cols if c in filtered.columns]
    tbl = filtered[avail_cols].sort_values("risk_score_v4", ascending=False).reset_index(drop=True)

    def _fmt_risk(r):
        c = {"Low": "#27ae60", "Medium": "#f39c12", "High": "#e74c3c", "Very High": "#8e44ad"}.get(r, "#636EFA")
        return f'<span style="color:{c};font-weight:700">{r}</span>'

    def _fmt_flag(f):
        return '<span class="flag-Monitor">Monitor</span>' if f else '<span class="flag-Clear">Clear</span>'

    rows_html = ""
    for _, row in tbl.head(50).iterrows():
        rows_html += "<tr>"
        rows_html += f'<td style="padding:6px 8px;font-weight:600;color:#00BC8C">{row["player_name"]}</td>'
        for c in avail_cols[1:]:
            if c == "risk_band_v4":
                rows_html += f'<td style="padding:6px 8px">{_fmt_risk(row[c])}</td>'
            elif c == "monitoring_flag_v4":
                rows_html += f'<td style="padding:6px 8px">{_fmt_flag(row[c])}</td>'
            elif c == "risk_score_v4":
                rows_html += f'<td style="padding:6px 8px">{row[c]:.3f}</td>'
            elif c in ("min_last_14d", "ucl_minutes_last_14d", "cup_minutes_last_14d"):
                rows_html += f'<td style="padding:6px 8px">{row[c]:.0f}</td>' if pd.notna(row[c]) else '<td style="padding:6px 8px">—</td>'
            elif c == "full_90s_last_14d":
                rows_html += f'<td style="padding:6px 8px">{int(row[c])}</td>' if pd.notna(row[c]) else '<td style="padding:6px 8px">—</td>'
            elif c == "explanation_v4":
                txt = str(row[c])[:80] + "..." if len(str(row[c])) > 80 else str(row[c])
                rows_html += f'<td style="padding:6px 8px;font-size:12px;color:#8a8f9d">{txt}</td>'
            elif row[c] is None or (isinstance(row[c], float) and pd.isna(row[c])):
                rows_html += '<td style="padding:6px 8px">—</td>'
            else:
                val = row[c]
                if isinstance(val, float):
                    rows_html += f'<td style="padding:6px 8px">{val:.1f}</td>'
                else:
                    rows_html += f'<td style="padding:6px 8px">{val}</td>'
        rows_html += "</tr>"

    header_cols = "".join(
        f'<th style="padding:8px;text-align:left;color:#8a8f9d;font-size:11px;text-transform:uppercase;letter-spacing:0.5px;border-bottom:1px solid #2a2e3a">{c}</th>'
        for c in avail_cols
    )
    table_html = f"""
    <div style="max-height:600px;overflow-y:auto;border:1px solid #2a2e3a;border-radius:8px;background:#1a1d27">
        <table style="width:100%;border-collapse:collapse;font-size:13px">
            <thead style="position:sticky;top:0;background:#222736;z-index:1">
                <tr>{header_cols}</tr>
            </thead>
            <tbody>{rows_html}</tbody>
        </table>
    </div>
    """
    st.markdown(table_html, unsafe_allow_html=True)
    st.caption(f"Showing top 50 by risk score of {len(tbl)} players.")
