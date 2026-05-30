import dash
from dash import html, dcc, Input, Output
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from utils import load_data, filter_df

dash.register_page(__name__, path="/injury-risk")

df = load_data()

layout = html.Div([
    html.H2("Injury & Fatigue Risk Analysis", style={"marginBottom": "24px", "fontWeight": 600}),
    html.Div(id="injury-kpis", className="kpi-row"),
    html.Div([
        html.Div([
            html.Div([dcc.Graph(id="injury-burden")], className="chart-container"),
        ]),
        html.Div([
            html.Div([dcc.Graph(id="risk-signals")], className="chart-container", style={"flex": "1"}),
            html.Div([dcc.Graph(id="risk-by-pos")], className="chart-container", style={"flex": "1"}),
        ], style={"display": "flex", "flexWrap": "wrap", "gap": "16px"}),
        html.Div([
            html.Div([dcc.Graph(id="acwr-danger")], className="chart-container"),
        ]),
    ]),
])

@dash.callback(
    Output("injury-kpis", "children"),
    Input("global-store", "data"),
)
def update_kpis(store):
    d = filter_df(df, store.get("team"), store.get("season"), store.get("competition"))
    injury_related = d[d["returning_from_injury"] == 1]
    high_acwr = d[d["acwr_ratio"] > 1.5]
    low_rest = d[d["rest_days"] <= 3]
    decline = d[d["is_decline"] == 1]
    cards = [
        {"title": "Matches Studied", "value": f"{len(d):,}", "color": "#636EFA"},
        {"title": "Returning from Injury", "value": f"{len(injury_related):,} ({injury_related.shape[0]/len(d)*100:.1f}%)", "color": "#E74C3C"},
        {"title": "High ACWR (>1.5)", "value": f"{len(high_acwr):,} ({high_acwr.shape[0]/len(d)*100:.1f}%)", "color": "#FFA15A"},
        {"title": "Performance Declines", "value": f"{len(decline):,} ({decline.shape[0]/len(d)*100:.1f}%)", "color": "#EF553B"},
    ]
    return [html.Div([
        html.Div(c["title"], className="kpi-title"),
        html.Div(c["value"], className="kpi-value", style={"color": c["color"]}),
    ], className="kpi-card") for c in cards]

@dash.callback(
    Output("injury-burden", "figure"),
    Input("global-store", "data"),
)
def update_injury_burden(store):
    d = filter_df(df, store.get("team"), store.get("season"), None)
    if "squad_injured_count" not in d.columns:
        return go.Figure()
    team_inj = d.groupby("player_team").agg(
        avg_injured=("squad_injured_count", "mean"),
        avg_days_out=("squad_avg_days_out", "mean"),
        matches=("fixture_id", "count"),
    ).reset_index()
    team_inj = team_inj[team_inj["matches"] > 50].sort_values("avg_injured", ascending=False).head(15)
    fig = px.bar(team_inj, x="player_team", y="avg_injured",
                 title="Average Squad Injured Count by Team",
                 color="avg_days_out", color_continuous_scale="Reds",
                 labels={"avg_injured": "Avg Players Injured", "player_team": ""})
    fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", margin=dict(t=40, b=80, l=10, r=10))
    fig.update_xaxes(tickangle=45)
    return fig

@dash.callback(
    Output("risk-signals", "figure"),
    Input("global-store", "data"),
)
def update_risk_signals(store):
    d = filter_df(df, store.get("team"), store.get("season"), store.get("competition"))
    signals = pd.DataFrame({
        "signal": ["High Congestion", "Low Rest (≤3d)", "High ACWR (>1.5)", "Low ACWR (<0.5)",
                    "Return from Injury", "Consecutive Away (3+)"],
        "count": [
            d["is_high_congestion"].sum(),
            (d["rest_days"] <= 3).sum(),
            (d["acwr_ratio"] > 1.5).sum(),
            (d["acwr_ratio"] < 0.5).sum(),
            d["returning_from_injury"].sum(),
            (d["consecutive_away_games"] >= 3).sum(),
        ]
    })
    signals["pct"] = (signals["count"] / len(d) * 100).round(1)
    colors = ["#E74C3C" if p > 20 else "#F39C12" if p > 10 else "#27AE60" for p in signals["pct"]]
    fig = px.bar(signals, x="signal", y="count", text=signals["pct"].apply(lambda x: f"{x}%"),
                 title="Risk Signal Frequency", color=signals["signal"],
                 color_discrete_sequence=px.colors.qualex.Set3)
    fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", showlegend=False,
                      margin=dict(t=40, b=10, l=10, r=10), xaxis_title="")
    return fig

@dash.callback(
    Output("risk-by-pos", "figure"),
    Input("global-store", "data"),
)
def update_risk_by_pos(store):
    d = filter_df(df, store.get("team"), store.get("season"), store.get("competition"))
    pos_risk = d.groupby("position_group").agg(
        decline_rate=("is_decline", "mean"),
        avg_acwr=("acwr_ratio", "mean"),
        avg_rest=("rest_days", "mean"),
        count=("fixture_id", "count"),
    ).reset_index()
    fig = px.scatter(pos_risk, x="avg_rest", y="decline_rate", size="count",
                     color="position_group", text="position_group",
                     title="Decline Risk by Position (size = match count)",
                     labels={"avg_rest": "Avg Rest Days", "decline_rate": "Decline Rate"},
                     color_discrete_sequence=px.colors.qualex.Set2)
    fig.update_traces(textposition="top center")
    fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", margin=dict(t=40, b=10, l=10, r=10))
    return fig

@dash.callback(
    Output("acwr-danger", "figure"),
    Input("global-store", "data"),
)
def update_acwr_danger(store):
    d = filter_df(df, store.get("team"), store.get("season"), store.get("competition"))
    d = d[d["acwr_ratio"] > 0].copy()
    d["danger_zone"] = pd.cut(d["acwr_ratio"],
                              bins=[0, 0.5, 0.8, 1.2, 1.5, 10],
                              labels=["Very Low (<0.5)", "Low (0.5-0.8)", "Optimal (0.8-1.2)",
                                      "Elevated (1.2-1.5)", "Danger (>1.5)"])
    zone_colors = ["#3498DB", "#2ECC71", "#00BC8C", "#F39C12", "#E74C3C"]
    danger = d.groupby("danger_zone").agg(
        count=("fixture_id", "count"),
        decline_rate=("is_decline", "mean"),
    ).reset_index()
    fig = go.Figure()
    fig.add_trace(go.Bar(name="Count", x=danger["danger_zone"], y=danger["count"],
                         marker_color=zone_colors, yaxis="y"))
    fig.add_trace(go.Scatter(name="Decline Rate", x=danger["danger_zone"], y=danger["decline_rate"] * 100,
                             marker_color="#ffffff", yaxis="y2", mode="lines+markers", line=dict(width=3)))
    fig.update_layout(title="ACWR Danger Zones: Volume vs Decline Rate",
                      template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", margin=dict(t=40, b=10, l=10, r=10),
                      yaxis=dict(title="Match Count"), yaxis2=dict(title="Decline Rate %", overlaying="y", side="right"),
                      legend=dict(font=dict(size=10)))
    return fig
