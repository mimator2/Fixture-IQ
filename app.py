import dash
from dash import Dash, html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
from utils import load_data, get_team_options, get_season_options, get_competition_options

df = load_data()
teams = ["All"] + get_team_options(df)
seasons = ["All"] + [str(s) for s in get_season_options(df)]
competitions = ["All"] + get_competition_options(df)

app = Dash(__name__, use_pages=True, external_stylesheets=[dbc.themes.DARKLY], suppress_callback_exceptions=True)
server = app.server

store = dcc.Store(id="global-store", data={"team": "All", "season": "All", "competition": "All"})

SIDEBAR_WIDTH_COLLAPSED = "60px"
SIDEBAR_WIDTH_EXPANDED = "260px"

sidebar = html.Div([
    html.Div([
        html.Button("☰", id="toggle-sidebar", n_clicks=0,
            style={"background": "none", "color": "white", "border": "none",
                   "fontSize": "20px", "cursor": "pointer", "padding": "4px 0 12px 0"}),
        html.Hr(style={"borderColor": "#2a2e3a", "margin": "8px 0"}),
        html.Div(id="sidebar-filters", children=[
            html.Span("TEAM", className="sidebar-filter-label"),
            dcc.Dropdown(id="team-filter", options=[{"label": t, "value": t} for t in teams],
                value="All", clearable=False, searchable=True),
            html.Span("SEASON", className="sidebar-filter-label"),
            dcc.Dropdown(id="season-filter", options=[{"label": s, "value": s} for s in seasons],
                value="All", clearable=False, searchable=True),
            html.Span("COMPETITION", className="sidebar-filter-label"),
            dcc.Dropdown(id="competition-filter", options=[{"label": c, "value": c} for c in competitions],
                value="All", clearable=False, searchable=True),
        ]),
        html.Hr(style={"borderColor": "#2a2e3a", "margin": "16px 0"}),
        dbc.Nav([
            dbc.NavLink("Overview", href="/", active="exact"),
            dbc.NavLink("Congestion", href="/congestion", active="exact"),
            dbc.NavLink("Performance", href="/performance", active="exact"),
            dbc.NavLink("Injury Risk", href="/injury-risk", active="exact"),
            dbc.NavLink("Rotation", href="/rotation", active="exact"),
            dbc.NavLink("Model Insights", href="/model-insights", active="exact"),
            dbc.NavLink("Team Compare", href="/team-compare", active="exact"),
        ], vertical=True, pills=True),
    ], style={"padding": "16px"}),
], id="sidebar", style={
    "position": "fixed", "top": 0, "left": 0, "bottom": 0,
    "width": SIDEBAR_WIDTH_EXPANDED,
    "backgroundColor": "#111111",
    "overflow": "hidden",
    "transition": "width 0.25s ease",
    "zIndex": 100,
})

content = html.Div(id="page-content", children=[
    html.Div(dash.page_container, style={"padding": "28px 32px", "maxWidth": "1400px", "margin": "0 auto"}),
], style={"marginLeft": SIDEBAR_WIDTH_EXPANDED, "transition": "margin-left 0.25s ease"})

app.layout = html.Div([store, sidebar, content])

@app.callback(
    Output("sidebar", "style"),
    Output("page-content", "style"),
    Output("sidebar-filters", "style"),
    Input("toggle-sidebar", "n_clicks"),
    State("sidebar", "style"),
    prevent_initial_call=True
)
def toggle_sidebar(n_clicks, sidebar_style):
    if sidebar_style["width"] == SIDEBAR_WIDTH_EXPANDED:
        return (
            {**sidebar_style, "width": SIDEBAR_WIDTH_COLLAPSED},
            {"marginLeft": SIDEBAR_WIDTH_COLLAPSED, "transition": "margin-left 0.25s ease"},
            {"display": "none"},
        )
    else:
        return (
            {**sidebar_style, "width": SIDEBAR_WIDTH_EXPANDED},
            {"marginLeft": SIDEBAR_WIDTH_EXPANDED, "transition": "margin-left 0.25s ease"},
            {"display": "block"},
        )

@app.callback(
    Output("global-store", "data"),
    Input("team-filter", "value"),
    Input("season-filter", "value"),
    Input("competition-filter", "value"),
    State("global-store", "data"),
)
def update_store(team, season, competition, current):
    return {**current, "team": team, "season": season, "competition": competition}

if __name__ == "__main__":
    app.run(debug=True)
