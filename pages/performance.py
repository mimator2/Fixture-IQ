import dash
from dash import html, dcc, Input, Output
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from utils import load_data, filter_df, get_player_options

dash.register_page(__name__, path="/performance")

df = load_data()
players = get_player_options(df)

layout = html.Div([
    html.H2("Player Performance Analysis", style={"marginBottom": "24px", "fontWeight": 600}),
    html.Div([
        html.Div([
            html.Label("Search Player", style={"color": "#8a8f9d", "fontSize": "12px", "fontWeight": 500,
                                               "textTransform": "uppercase", "letterSpacing": "0.8px"}),
            dcc.Dropdown(id="player-search", options=[{"label": p, "value": p} for p in players],
                         placeholder="Type player name...", clearable=True, searchable=True),
        ], style={"width": "350px", "marginBottom": "20px"}),
    ]),
    html.Div(id="performance-kpis", className="kpi-row"),
    html.Div([
        html.Div([
            html.Div([dcc.Graph(id="player-rating-trend")], className="chart-container"),
        ]),
        html.Div([
            html.Div([dcc.Graph(id="player-position-perf")], className="chart-container", style={"flex": "1"}),
            html.Div([dcc.Graph(id="player-comp-perf")], className="chart-container", style={"flex": "1"}),
        ], style={"display": "flex", "flexWrap": "wrap", "gap": "16px"}),
        html.Div([
            html.Div([dcc.Graph(id="decline-analysis")], className="chart-container"),
        ]),
    ]),
])

@dash.callback(
    Output("performance-kpis", "children"),
    Output("player-rating-trend", "figure"),
    Output("player-position-perf", "figure"),
    Output("player-comp-perf", "figure"),
    Output("decline-analysis", "figure"),
    Input("player-search", "value"),
    Input("global-store", "data"),
)
def update_performance(player_name, store):
    d = filter_df(df, store.get("team"), store.get("season"), store.get("competition"))
    if player_name and player_name != "All":
        pd = d[d["player_name"] == player_name].sort_values("date")
        title_suffix = f" - {player_name}"
    else:
        pd = d
        title_suffix = ""

    kpis = _kpis(pd, player_name)
    trend_fig = _rating_trend(pd, player_name)
    pos_fig = _position_perf(d, player_name)
    comp_fig = _comp_perf(d, player_name)
    decline_fig = _decline_analysis(d, player_name)
    return kpis, trend_fig, pos_fig, comp_fig, decline_fig


def _kpis(pd, player_name):
    if player_name and len(pd) > 0:
        avg_rating = pd["rating"].mean()
        decline_rate = pd["is_decline"].mean() * 100
        avg_minutes = pd[pd["minutes_played"] > 0]["minutes_played"].mean()
        matches = len(pd)
        cards = [
            {"title": f"Matches ({player_name})", "value": f"{matches:,}", "color": "#636EFA"},
            {"title": "Avg Rating", "value": f"{avg_rating:.2f}", "color": "#00BC8C"},
            {"title": "Decline Rate", "value": f"{decline_rate:.1f}%", "color": "#E74C3C"},
            {"title": "Avg Minutes", "value": f"{avg_minutes:.0f}", "color": "#AB63FA"},
        ]
    else:
        cards = [
            {"title": "Total Matches", "value": f"{len(pd):,}", "color": "#636EFA"},
            {"title": "Avg Rating", "value": f"{pd['rating'].mean():.2f}", "color": "#00BC8C"},
            {"title": "Avg Decline Rate", "value": f"{pd['is_decline'].mean()*100:.1f}%", "color": "#E74C3C"},
            {"title": "Players", "value": f"{pd['player_name'].nunique():,}", "color": "#AB63FA"},
        ]
    return [html.Div([
        html.Div(c["title"], className="kpi-title"),
        html.Div(c["value"], className="kpi-value", style={"color": c["color"]}),
    ], className="kpi-card") for c in cards]


def _rating_trend(pd, player_name):
    if player_name and len(pd) > 0:
        trend = pd.groupby("date")["rating"].mean().reset_index()
        fig = px.line(trend, x="date", y="rating", title=f"Rating Trend{'' if not player_name else ' - '+player_name}",
                      markers=True)
        fig.add_hline(y=pd["rating"].mean(), line_dash="dash", line_color="#8a8f9d",
                      annotation_text=f"Avg: {pd['rating'].mean():.2f}")
    else:
        avg_by_date = pd.groupby("date")["rating"].mean().reset_index()
        fig = px.line(avg_by_date, x="date", y="rating", title="Average Rating Trend (All Players)",
                      color_discrete_sequence=["#00BC8C"])
        fig.add_hline(y=pd["rating"].mean(), line_dash="dash", line_color="#8a8f9d")
    fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", margin=dict(t=40, b=10, l=10, r=10))
    return fig


def _position_perf(d, player_name):
    if player_name:
        pdata = d[d["player_name"] == player_name]
    else:
        pdata = d
    pos_avg = pdata.groupby("position_group").agg(avg_rating=("rating", "mean"), count=("fixture_id", "count")
                                                  ).reset_index()
    fig = px.bar(pos_avg, x="position_group", y="avg_rating", color="count",
                 title="Performance by Position", text_auto=".2f",
                 color_continuous_scale="Viridis")
    fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", margin=dict(t=40, b=10, l=10, r=10),
                      xaxis_title="", yaxis_title="Avg Rating")
    return fig


def _comp_perf(d, player_name):
    if player_name:
        pdata = d[d["player_name"] == player_name]
    else:
        pdata = d
    comp_avg = pdata.groupby("competition").agg(avg_rating=("rating", "mean"), count=("fixture_id", "count")
                                                ).reset_index()
    fig = px.bar(comp_avg, x="competition", y="avg_rating", color="count",
                 title="Performance by Competition", text_auto=".2f",
                 color_continuous_scale="Plasma")
    fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", margin=dict(t=40, b=10, l=10, r=10),
                      xaxis_title="", yaxis_title="Avg Rating")
    return fig


def _decline_analysis(d, player_name):
    if player_name:
        pdata = d[d["player_name"] == player_name]
    else:
        pdata = d
    fig = px.scatter(pdata, x="rest_days", y="rating", color="is_decline",
                     title="Rating vs Rest Days (colored by decline flag)",
                     color_discrete_map={0: "#00BC8C", 1: "#E74C3C"},
                     labels={"is_decline": "Decline", "rest_days": "Rest Days", "rating": "Rating"},
                     opacity=0.6)
    fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", margin=dict(t=40, b=10, l=10, r=10),
                      legend=dict(font=dict(size=10)))
    return fig
