import dash
from dash import html, dcc, Input, Output
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from utils import load_data, filter_df

dash.register_page(__name__, path="/rotation")

df = load_data()

layout = html.Div([
    html.H2("Squad Rotation Analysis", style={"marginBottom": "24px", "fontWeight": 600}),
    html.Div(id="rotation-kpis", className="kpi-row"),
    html.Div([
        html.Div([
            html.Div([dcc.Graph(id="top-minutes")], className="chart-container"),
        ]),
        html.Div([
            html.Div([dcc.Graph(id="minutes-dist")], className="chart-container", style={"flex": "1"}),
            html.Div([dcc.Graph(id="sub-pattern")], className="chart-container", style={"flex": "1"}),
        ], style={"display": "flex", "flexWrap": "wrap", "gap": "16px"}),
        html.Div([
            html.Div([dcc.Graph(id="position-depth")], className="chart-container"),
        ]),
    ]),
])

@dash.callback(
    Output("rotation-kpis", "children"),
    Input("global-store", "data"),
)
def update_kpis(store):
    d = filter_df(df, store.get("team"), store.get("season"), store.get("competition"))
    started = d[d["is_substitute"] == False]
    subbed = d[d["is_substitute"] == True]
    avg_min = d[d["minutes_played"] > 0]["minutes_played"].mean()
    cards = [
        {"title": "Total Appearances", "value": f"{len(d):,}", "color": "#636EFA"},
        {"title": "Starts", "value": f"{len(started):,} ({started.shape[0]/len(d)*100:.0f}%)", "color": "#00BC8C"},
        {"title": "Sub Appearances", "value": f"{len(subbed):,} ({subbed.shape[0]/len(d)*100:.0f}%)", "color": "#FFA15A"},
        {"title": "Avg Minutes (when played)", "value": f"{avg_min:.0f}", "color": "#AB63FA"},
    ]
    return [html.Div([
        html.Div(c["title"], className="kpi-title"),
        html.Div(c["value"], className="kpi-value", style={"color": c["color"]}),
    ], className="kpi-card") for c in cards]

@dash.callback(
    Output("top-minutes", "figure"),
    Input("global-store", "data"),
)
def update_top_minutes(store):
    d = filter_df(df, store.get("team"), store.get("season"), store.get("competition"))
    player_min = d.groupby("player_name")["minutes_played"].sum().reset_index()
    top = player_min.sort_values("minutes_played", ascending=False).head(20)
    top["label"] = top["player_name"].str.slice(0, 18)
    fig = px.bar(top, x="minutes_played", y="label", orientation="h",
                 title="Top 20 Players by Total Minutes Played",
                 color="minutes_played", color_continuous_scale="Greens")
    fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", margin=dict(t=40, b=10, l=10, r=10),
                      xaxis_title="Total Minutes", yaxis_title="", yaxis=dict(autorange="reversed"))
    return fig

@dash.callback(
    Output("minutes-dist", "figure"),
    Input("global-store", "data"),
)
def update_minutes_dist(store):
    d = filter_df(df, store.get("team"), store.get("season"), store.get("competition"))
    played = d[d["minutes_played"] > 0]
    fig = px.histogram(played, x="minutes_played", nbins=20,
                       title="Distribution of Minutes Played Per Match",
                       color_discrete_sequence=["#636EFA"])
    fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", margin=dict(t=40, b=10, l=10, r=10),
                      xaxis_title="Minutes Played", yaxis_title="Count")
    return fig

@dash.callback(
    Output("sub-pattern", "figure"),
    Input("global-store", "data"),
)
def update_sub_pattern(store):
    d = filter_df(df, store.get("team"), store.get("season"), None)
    team_sub = d.groupby("player_team")["is_substitute"].mean().reset_index()
    team_sub = team_sub.sort_values("is_substitute", ascending=False).head(15)
    fig = px.bar(team_sub, x="player_team", y="is_substitute",
                 title="Substitution Rate by Team (Top 15)",
                 color="is_substitute", color_continuous_scale="Oranges",
                 labels={"is_substitute": "Sub Rate", "player_team": ""})
    fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", margin=dict(t=40, b=80, l=10, r=10))
    fig.update_xaxes(tickangle=45)
    fig.update_yaxes(tickformat=".0%")
    return fig

@dash.callback(
    Output("position-depth", "figure"),
    Input("global-store", "data"),
)
def update_position_depth(store):
    d = filter_df(df, store.get("team"), store.get("season"), store.get("competition"))
    pos_min = d.groupby(["position_group", "player_name"])["minutes_played"].sum().reset_index()
    pos_summary = pos_min.groupby("position_group").agg(
        total_minutes=("minutes_played", "sum"),
        unique_players=("player_name", "nunique"),
        avg_per_player=("minutes_played", "mean"),
    ).reset_index()
    fig = px.bar(pos_summary, x="position_group", y="total_minutes",
                 title="Total Minutes by Position Group",
                 color="unique_players", text="unique_players",
                 color_continuous_scale="Purples",
                 labels={"total_minutes": "Total Minutes", "unique_players": "Players Used",
                         "position_group": ""})
    fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", margin=dict(t=40, b=10, l=10, r=10))
    return fig
