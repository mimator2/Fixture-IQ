import dash
from dash import html, dcc, Input, Output
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from utils import load_data, get_team_options

dash.register_page(__name__, path="/team-compare")

df = load_data()
teams = get_team_options(df)

layout = html.Div([
    html.H2("Team Comparison", style={"marginBottom": "24px", "fontWeight": 600}),
    html.Div([
        html.Div([
            html.Label("Team A", style={"color": "#8a8f9d", "fontSize": "12px", "fontWeight": 500,
                                        "textTransform": "uppercase", "letterSpacing": "0.8px"}),
            dcc.Dropdown(id="team-a", options=[{"label": t, "value": t} for t in teams],
                         value=teams[0] if teams else None, clearable=False),
        ], style={"width": "300px", "display": "inline-block", "marginRight": "20px"}),
        html.Div([
            html.Label("Team B", style={"color": "#8a8f9d", "fontSize": "12px", "fontWeight": 500,
                                        "textTransform": "uppercase", "letterSpacing": "0.8px"}),
            dcc.Dropdown(id="team-b", options=[{"label": t, "value": t} for t in teams],
                         value=teams[1] if len(teams) > 1 else None, clearable=False),
        ], style={"width": "300px", "display": "inline-block"}),
    ]),
    html.Div(id="compare-kpis", className="kpi-row", style={"marginTop": "20px"}),
    html.Div([
        html.Div([
            html.Div([dcc.Graph(id="radar-compare")], className="chart-container"),
        ]),
        html.Div([
            html.Div([dcc.Graph(id="competition-breakdown-compare")], className="chart-container"),
        ]),
    ]),
])

@dash.callback(
    Output("compare-kpis", "children"),
    Output("radar-compare", "figure"),
    Output("competition-breakdown-compare", "figure"),
    Input("team-a", "value"),
    Input("team-b", "value"),
    Input("global-store", "data"),
)
def update_compare(team_a, team_b, store):
    if not team_a or not team_b:
        return [], go.Figure(), go.Figure()

    season = store.get("season") if store.get("season") != "All" else None
    competition = store.get("competition") if store.get("competition") != "All" else None

    da = df[df["player_team"] == team_a].copy()
    db = df[df["player_team"] == team_b].copy()

    if season:
        da = da[da["season"] == int(season)]
        db = db[db["season"] == int(season)]
    if competition:
        da = da[da["competition"] == competition]
        db = db[db["competition"] == competition]

    kpis = _compare_kpis(da, db, team_a, team_b)
    radar = _radar_chart(da, db, team_a, team_b)
    comp_breakdown = _comp_breakdown(da, db, team_a, team_b)
    return kpis, radar, comp_breakdown


def _compare_kpis(da, db, ta, tb):
    def team_stats(d):
        return {
            "matches": len(d),
            "players": d["player_name"].nunique(),
            "avg_rating": d["rating"].mean(),
            "avg_rest": d["rest_days"].mean(),
            "decline_rate": d["is_decline"].mean() * 100,
            "win_rate": d["is_win"].mean() * 100 if "is_win" in d.columns else 0,
            "avg_minutes": d[d["minutes_played"] > 0]["minutes_played"].mean(),
        }
    sa, sb = team_stats(da), team_stats(db)
    metrics = [
        ("Matches", "matches", "#636EFA"),
        ("Players Used", "players", "#00BC8C"),
        ("Avg Rating", "avg_rating", "#AB63FA"),
        ("Avg Rest (d)", "avg_rest", "#FFA15A"),
        ("Decline %", "decline_rate", "#E74C3C"),
        ("Win %", "win_rate", "#2ECC71"),
    ]
    cards = []
    for label, key, color in metrics:
        va, vb = sa[key], sb[key]
        diff = va - vb
        diff_str = f"{'+' if diff > 0 else ''}{diff:.2f}" if isinstance(diff, float) else ""
        cards.append(html.Div([
            html.Div(label, className="kpi-title"),
            html.Div([
                html.Span(f"{va:.2f}" if isinstance(va, float) else f"{va:,}", style={"color": color, "fontWeight": 600}),
                html.Span(" vs ", style={"color": "#555", "margin": "0 6px"}),
                html.Span(f"{vb:.2f}" if isinstance(vb, float) else f"{vb:,}", style={"color": color, "fontWeight": 600}),
            ], style={"fontSize": "16px"}),
            html.Div(diff_str, className="kpi-subtitle"),
        ], className="kpi-card"))
    return cards


def _radar_chart(da, db, ta, tb):
    def team_radar(d):
        return {
            "Avg Rating": d["rating"].mean(),
            "Avg Rest Days": min(d["rest_days"].mean() / 3, 100),
            "Win Rate": d["is_win"].mean() * 100 if "is_win" in d.columns else 0,
            "Avg Minutes": d[d["minutes_played"] > 0]["minutes_played"].mean() / 9,
            "Pass Accuracy": d["passes_accuracy"].mean() / 1.5 if "passes_accuracy" in d.columns else 50,
            "Duel Win %": (d["duels_won"].sum() / max(d["duels_total"].sum(), 1)) * 100,
        }
    ra, rb = team_radar(da), team_radar(db)
    categories = list(ra.keys())
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=list(ra.values()), theta=categories, fill="toself",
                                  name=ta, line_color="#636EFA", fillcolor="rgba(99, 110, 250, 0.2)"))
    fig.add_trace(go.Scatterpolar(r=list(rb.values()), theta=categories, fill="toself",
                                  name=tb, line_color="#EF553B", fillcolor="rgba(239, 85, 59, 0.2)"))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                      title=f"Team Radar: {ta} vs {tb}",
                      template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", margin=dict(t=40, b=10, l=10, r=10),
                      legend=dict(font=dict(size=10)))
    return fig


def _comp_breakdown(da, db, ta, tb):
    def team_comp(d, name):
        comp = d.groupby("competition").agg(
            matches=("fixture_id", "count"),
            avg_rating=("rating", "mean"),
        ).reset_index()
        comp["team"] = name
        return comp
    ca = team_comp(da, ta)
    cb = team_comp(db, tb)
    combined = pd.concat([ca, cb])
    fig = px.bar(combined, x="competition", y="matches", color="team",
                 barmode="group", title="Match Count by Competition",
                 color_discrete_map={ta: "#636EFA", tb: "#EF553B"})
    fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", margin=dict(t=40, b=10, l=10, r=10),
                      xaxis_title="", yaxis_title="Matches", legend=dict(font=dict(size=10)))
    return fig
