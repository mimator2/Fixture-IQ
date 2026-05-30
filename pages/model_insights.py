import dash
from dash import html, dcc, Input, Output
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from utils import load_data, filter_df

dash.register_page(__name__, path="/model-insights")

df = load_data()

layout = html.Div([
    html.H2("Model Insights & Interpretability", style={"marginBottom": "8px", "fontWeight": 600}),
    html.P("Understanding what drives performance decline predictions",
           style={"color": "#8a8f9d", "marginBottom": "24px", "fontSize": "14px"}),
    html.Div(id="model-kpis", className="kpi-row"),
    html.Div([
        html.Div([
            html.Div([dcc.Graph(id="feature-importance")], className="chart-container"),
        ]),
        html.Div([
            html.Div([dcc.Graph(id="decline-by-feature")], className="chart-container", style={"flex": "1"}),
            html.Div([dcc.Graph(id="decline-threshold")], className="chart-container", style={"flex": "1"}),
        ], style={"display": "flex", "flexWrap": "wrap", "gap": "16px"}),
        html.Div([
            html.Div([dcc.Graph(id="ucl-comparison")], className="chart-container"),
        ]),
    ]),
])

FEATURE_IMPORTANCE = {
    "rest_days": 0.185, "acwr_ratio": 0.152, "min_last_7d": 0.128,
    "rating": 0.098, "minutes_played": 0.085, "high_congestion_flag": 0.072,
    "consecutive_away_games": 0.058, "passes_accuracy": 0.045,
    "duels_won": 0.038, "touches": 0.032, "fouls_drawn": 0.028,
    "shots_on_target": 0.024, "goals": 0.020, "key_passes": 0.018,
    "position": 0.017,
}

@dash.callback(
    Output("model-kpis", "children"),
    Input("global-store", "data"),
)
def update_kpis(store):
    d = filter_df(df, store.get("team"), store.get("season"), store.get("competition"))
    scorable = d[(d["rating"] > 0) & (d["minutes_played"] >= 45)]
    cards = [
        {"title": "Total Samples", "value": f"{len(d):,}", "color": "#636EFA"},
        {"title": "Scorable Matches (≥45min)", "value": f"{len(scorable):,}", "color": "#00BC8C"},
        {"title": "Decline Rate (scorable)", "value": f"{scorable['is_decline'].mean()*100:.1f}%", "color": "#E74C3C"},
        {"title": "Avg Rest Days", "value": f"{d['rest_days'].mean():.1f}d", "color": "#AB63FA"},
    ]
    return [html.Div([
        html.Div(c["title"], className="kpi-title"),
        html.Div(c["value"], className="kpi-value", style={"color": c["color"]}),
    ], className="kpi-card") for c in cards]

@dash.callback(
    Output("feature-importance", "figure"),
    Input("global-store", "data"),
)
def update_feature_importance(store):
    fi = pd.DataFrame(list(FEATURE_IMPORTANCE.items()), columns=["feature", "importance"])
    fi = fi.sort_values("importance")
    colors = ["#E74C3C" if i >= fi["importance"].quantile(0.75) else
              "#F39C12" if i >= fi["importance"].quantile(0.5) else "#00BC8C"
              for i in fi["importance"]]
    fig = px.bar(fi, x="importance", y="feature", orientation="h",
                 title="Feature Importance (from XGBoost Model A)",
                 color=colors, color_discrete_map="identity")
    fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", margin=dict(t=40, b=10, l=10, r=10),
                      xaxis_title="Importance (Gain)", yaxis_title="", showlegend=False)
    return fig

@dash.callback(
    Output("decline-by-feature", "figure"),
    Input("global-store", "data"),
)
def update_decline_by_feature(store):
    d = filter_df(df, store.get("team"), store.get("season"), store.get("competition"))
    d = d[d["rest_days"] <= 14].copy()
    d["rest_bin"] = pd.cut(d["rest_days"], bins=[0, 1, 2, 3, 4, 5, 6, 7, 14],
                           labels=["0-1", "2", "3", "4", "5", "6", "7", "8-14"])
    decline_by_rest = d.groupby("rest_bin", observed=True).agg(
        decline_rate=("is_decline", "mean"),
        count=("fixture_id", "count"),
    ).reset_index()
    fig = go.Figure()
    fig.add_trace(go.Bar(name="Sample Count", x=decline_by_rest["rest_bin"].astype(str),
                         y=decline_by_rest["count"], marker_color="#636EFA", opacity=0.6, yaxis="y"))
    fig.add_trace(go.Scatter(name="Decline Rate", x=decline_by_rest["rest_bin"].astype(str),
                             y=decline_by_rest["decline_rate"] * 100,
                             marker_color="#E74C3C", yaxis="y2", mode="lines+markers",
                             line=dict(width=3)))
    fig.update_layout(title="Decline Rate by Rest Days (bars=count, line=% decline)",
                      template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", margin=dict(t=40, b=10, l=10, r=10),
                      xaxis_title="Rest Days", yaxis_title="Count",
                      yaxis2=dict(title="Decline Rate %", overlaying="y", side="right", range=[0, 50]),
                      legend=dict(font=dict(size=10)))
    return fig

@dash.callback(
    Output("decline-threshold", "figure"),
    Input("global-store", "data"),
)
def update_decline_threshold(store):
    d = filter_df(df, store.get("team"), store.get("season"), store.get("competition"))
    d = d[(d["rating"] > 0) & (d["minutes_played"] >= 45)].copy()
    d["acwr_bin"] = pd.cut(d["acwr_ratio"], bins=[0, 0.5, 0.8, 1.0, 1.2, 1.5, 2.0, 10],
                           labels=["<0.5", "0.5-0.8", "0.8-1.0", "1.0-1.2", "1.2-1.5", "1.5-2.0", ">2.0"])
    acwr_decline = d.groupby("acwr_bin", observed=True).agg(
        decline_rate=("is_decline", "mean"),
        count=("fixture_id", "count"),
    ).reset_index()
    fig = go.Figure()
    fig.add_trace(go.Bar(name="Count", x=acwr_decline["acwr_bin"].astype(str),
                         y=acwr_decline["count"], marker_color="#AB63FA", opacity=0.6, yaxis="y"))
    fig.add_trace(go.Scatter(name="Decline Rate", x=acwr_decline["acwr_bin"].astype(str),
                             y=acwr_decline["decline_rate"] * 100,
                             marker_color="#E74C3C", yaxis="y2", mode="lines+markers",
                             line=dict(width=3)))
    fig.update_layout(title="Decline Rate by ACWR Range (bars=count, line=% decline)",
                      template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", margin=dict(t=40, b=10, l=10, r=10),
                      xaxis_title="ACWR Range", yaxis_title="Count",
                      yaxis2=dict(title="Decline Rate %", overlaying="y", side="right", range=[0, 50]),
                      legend=dict(font=dict(size=10)))
    return fig

@dash.callback(
    Output("ucl-comparison", "figure"),
    Input("global-store", "data"),
)
def update_ucl_comparison(store):
    d = filter_df(df, store.get("team"), store.get("season"), None)
    team_ucl = d[d["competition"] == "Champions League"]["player_team"].unique()
    d["is_ucl_team"] = d["player_team"].isin(team_ucl).astype(int)
    comp = d.groupby("is_ucl_team").agg(
        avg_rest=("rest_days", "mean"),
        avg_acwr=("acwr_ratio", "mean"),
        decline_rate=("is_decline", "mean"),
        avg_rating=("rating", "mean"),
        matches=("fixture_id", "count"),
    ).reset_index()
    comp["label"] = comp["is_ucl_team"].map({0: "Non-UCL Teams", 1: "UCL Teams"})
    metrics = ["avg_rest", "avg_acwr", "decline_rate", "avg_rating"]
    metric_labels = ["Avg Rest Days", "Avg ACWR", "Decline Rate", "Avg Rating"]
    fig = go.Figure()
    for i, (m, ml) in enumerate(zip(metrics, metric_labels)):
        fig.add_trace(go.Bar(name=ml, x=comp["label"], y=comp[m] if m != "decline_rate" else comp[m] * 100,
                             text=comp[m].round(2) if m != "decline_rate" else (comp[m] * 100).round(1),
                             visible=(i == 0)))
    fig.update_layout(title="UCL vs Non-UCL Team Comparison",
                      template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", margin=dict(t=40, b=10, l=10, r=10),
                      updatemenus=[dict(buttons=[
                          dict(label=ml, method="update", args=[{"visible": [j == i for j in range(len(metrics))]}])
                          for i, ml in enumerate(metric_labels)
                      ], direction="down", showactive=True, x=0.8, y=1.15)])
    return fig
