import dash
from dash import html, dcc, Input, Output
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from utils import load_data, filter_df

dash.register_page(__name__, path="/congestion")

df = load_data()

layout = html.Div([
    html.H2("Fixture Congestion Analysis", style={"marginBottom": "24px", "fontWeight": 600}),

    html.Div(id="congestion-kpis", className="kpi-row"),
    html.Div([
        html.Div([
            html.Div([dcc.Graph(id="rest-days-box")], className="chart-container"),
        ]),
        html.Div([
            html.Div([dcc.Graph(id="acwr-dist")], className="chart-container", style={"flex": "1", "minWidth": "300px"}),
            html.Div([dcc.Graph(id="congestion-flag-bar")], className="chart-container", style={"flex": "1", "minWidth": "300px"}),
        ], style={"display": "flex", "flexWrap": "wrap", "gap": "16px"}),
        html.Div([
            html.Div([dcc.Graph(id="away-streak")], className="chart-container"),
        ]),
    ]),
])

@dash.callback(
    Output("congestion-kpis", "children"),
    Input("global-store", "data"),
)
def update_kpis(store):
    d = filter_df(df, store.get("team"), store.get("season"), store.get("competition"))
    high_cong = d[d["is_high_congestion"] == 1]
    low_rest = d[d["rest_days"] <= 3]
    high_acwr = d[d["acwr_ratio"] > 1.5]
    cards = [
        {"title": "Avg Rest Days", "value": f"{d['rest_days'].mean():.1f}d", "color": "#636EFA"},
        {"title": "High Congestion Matches", "value": f"{len(high_cong):,}", "color": "#EF553B"},
        {"title": "Matches ≤3d Rest", "value": f"{len(low_rest):,} ({low_rest.shape[0]/len(d)*100:.1f}%)", "color": "#E74C3C"},
        {"title": "High ACWR (>1.5)", "value": f"{len(high_acwr):,}", "color": "#FFA15A"},
    ]
    return [html.Div([
        html.Div(c["title"], className="kpi-title"),
        html.Div(c["value"], className="kpi-value", style={"color": c["color"]}),
    ], className="kpi-card") for c in cards]

@dash.callback(
    Output("rest-days-box", "figure"),
    Input("global-store", "data"),
)
def update_rest_days_box(store):
    d = filter_df(df, store.get("team"), store.get("season"), None)
    top_teams = d.groupby("player_team")["rest_days"].mean().sort_values().head(12).index
    d = d[d["player_team"].isin(top_teams)]
    fig = px.box(d, x="player_team", y="rest_days", title="Rest Days Distribution by Team (Top 12)",
                 color="player_team", color_discrete_sequence=px.colors.qualitative.Alphabet)
    fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", showlegend=False,
                      margin=dict(t=40, b=80, l=10, r=10))
    fig.update_xaxes(tickangle=45)
    fig.add_hline(y=3, line_dash="dash", line_color="#E74C3C", annotation_text="Danger (<3d)")
    return fig

@dash.callback(
    Output("acwr-dist", "figure"),
    Input("global-store", "data"),
)
def update_acwr_dist(store):
    d = filter_df(df, store.get("team"), store.get("season"), store.get("competition"))
    d = d[d["acwr_ratio"] > 0].copy()
    d["acwr_bin"] = pd.cut(d["acwr_ratio"], bins=[0, 0.5, 0.8, 1.0, 1.2, 1.5, 2.0, 10],
                           labels=["<0.5", "0.5-0.8", "0.8-1.0", "1.0-1.2", "1.2-1.5", "1.5-2.0", ">2.0"])
    counts = d["acwr_bin"].value_counts().reset_index()
    counts.columns = ["range", "count"]
    colors = ["#27AE60", "#2ECC71", "#00BC8C", "#F1C40F", "#E67E22", "#E74C3C", "#C0392B"]
    fig = px.bar(counts, x="range", y="count", title="ACWR Distribution (Acute:Chronic Workload)",
                 color="range", color_discrete_sequence=colors)
    fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", showlegend=False,
                      margin=dict(t=40, b=10, l=10, r=10),
                      xaxis_title="ACWR Range", yaxis_title="Count")
    fig.add_vline(x=3.5, line_dash="dash", line_color="#E74C3C", annotation_text="Danger >1.5")
    return fig

@dash.callback(
    Output("congestion-flag-bar", "figure"),
    Input("global-store", "data"),
)
def update_congestion_flag(store):
    d = filter_df(df, store.get("team"), store.get("season"), None)
    if store.get("team") and store.get("team") != "All":
        d = d[d["player_team"] == store["team"]]
    flag_counts = d.groupby(["player_team", "is_high_congestion"]).size().reset_index(name="count")
    flag_counts["congestion_label"] = flag_counts["is_high_congestion"].map({0: "Normal", 1: "High Congestion"})
    fig = px.bar(flag_counts, x="player_team", y="count", color="congestion_label",
                 title="High Congestion Flag by Team",
                 color_discrete_map={"Normal": "#2ECC71", "High Congestion": "#E74C3C"},
                 barmode="stack")
    fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", margin=dict(t=40, b=80, l=10, r=10),
                      legend=dict(font=dict(size=10)), xaxis_title="")
    fig.update_xaxes(tickangle=45)
    return fig

@dash.callback(
    Output("away-streak", "figure"),
    Input("global-store", "data"),
)
def update_away_streak(store):
    d = filter_df(df, store.get("team"), store.get("season"), store.get("competition"))
    streak_counts = d["consecutive_away_games"].value_counts().sort_index().reset_index()
    streak_counts.columns = ["consecutive_away", "count"]
    streak_counts["consecutive_away"] = streak_counts["consecutive_away"].astype(int)
    fig = px.bar(streak_counts, x="consecutive_away", y="count",
                 title="Consecutive Away Games Distribution",
                 color="count", color_continuous_scale="Reds")
    fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", margin=dict(t=40, b=10, l=10, r=10),
                      xaxis=dict(dtick=1), xaxis_title="Consecutive Away Games", yaxis_title="Count")
    return fig
