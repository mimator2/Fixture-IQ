import dash
from dash import html, dcc, Input, Output
import plotly.express as px
from utils import load_data, filter_df, kpi_card

dash.register_page(__name__, path="/")

df = load_data()

SECTION_STYLE = {"marginBottom": "40px"}
CARD_STYLE = {
    "background": "linear-gradient(135deg, #1a1d27 0%, #222736 100%)",
    "border": "1px solid #2a2e3a",
    "borderRadius": "12px",
    "padding": "24px",
    "boxShadow": "0 4px 20px rgba(0,0,0,0.3)",
}


def _nav_card(icon, title, description, href, color):
    return html.Div([
        html.Div(icon, style={"fontSize": "28px", "marginBottom": "8px"}),
        html.H5(title, style={"color": color, "fontWeight": 600, "marginBottom": "6px"}),
        html.P(description, style={"color": "#8a8f9d", "fontSize": "12px", "lineHeight": "1.5"}),
        html.A("Explore →", href=href, style={"color": color, "fontSize": "12px", "fontWeight": 600,
                                               "textDecoration": "none", "marginTop": "8px", "display": "inline-block"}),
    ], style={"textAlign": "center"})


layout = html.Div([

    # ── HERO ──
    html.Div([
        html.H1("Fixture-IQ", style={"fontSize": "48px", "fontWeight": 700, "marginBottom": "8px"}),
        html.P("Quantifying the Impact of Fixture Congestion on Football Performance & Squad Management",
               style={"fontSize": "18px", "color": "#8a8f9d", "maxWidth": "720px", "lineHeight": "1.5"}),
        html.P("From perception to evidence — a data-driven analysis of Premier League clubs competing in Europe",
               style={"fontSize": "14px", "color": "#5a5f6d", "marginTop": "8px"}),
    ], style={"marginBottom": "32px", "borderBottom": "1px solid #2a2e3a", "paddingBottom": "24px"}),

    # ── KPI ROW ──
    html.Div(id="landing-kpis", className="kpi-row", style={"marginBottom": "32px"}),

    # ── PROJECT CONTEXT ──
    html.Div([
        html.H3("Project Context", className="section-title"),
        html.Div([
            html.Div([
                html.H4("🏢  Business Context", style={"color": "#636EFA", "marginBottom": "12px"}),
                html.P("Professional football has become a highly demanding industry in which clubs compete "
                       "simultaneously in domestic leagues, domestic cups, and international tournaments. "
                       "For Premier League clubs participating in UEFA competitions, the match calendar is "
                       "especially intense, creating periods where teams must play several games within "
                       "very short intervals.",
                       style={"color": "#c0c4d0", "lineHeight": "1.7", "fontSize": "14px"}),
                html.P("Fixture congestion is not only a sporting issue but also a business and "
                       "performance-management problem. Clubs invest heavily in players, coaching staff, "
                       "sports science departments, and performance analysts to optimize results. Managing "
                       "player availability, fatigue, recovery, and rotation is essential because poor "
                       "decisions during congested periods can affect league position, European progress, "
                       "and ultimately revenue and long-term success.",
                       style={"color": "#c0c4d0", "lineHeight": "1.7", "fontSize": "14px", "marginTop": "8px"}),
            ], style={**CARD_STYLE, "flex": "1", "minWidth": "300px"}),
            html.Div([
                html.H4("🔍  What This Reveals", style={"color": "#00BC8C", "marginBottom": "12px"}),
                html.P("This topic is relevant because fixture congestion is one of the most discussed "
                       "challenges in elite football, yet often debated through opinion rather than "
                       "structured evidence. This project reveals whether there is a measurable "
                       "relationship between:",
                       style={"color": "#c0c4d0", "lineHeight": "1.7", "fontSize": "14px"}),
                html.Ul([
                    html.Li("The density of match schedules"),
                    html.Li("The amount of squad rotation used by clubs"),
                    html.Li("Competitive performance under different scheduling conditions"),
                ], style={"color": "#c0c4d0", "lineHeight": "1.8", "fontSize": "14px", "paddingLeft": "20px"}),
                html.P("The project moves the discussion from perception to evidence.",
                       style={"color": "#8a8f9d", "fontStyle": "italic", "marginTop": "8px", "fontSize": "13px"}),
            ], style={**CARD_STYLE, "flex": "1", "minWidth": "300px"}),
        ], style={"display": "flex", "flexWrap": "wrap", "gap": "16px"}),
        html.Div([
            html.Div([
                html.H4("💰  Economic Interest", style={"color": "#FFA15A", "marginBottom": "12px"}),
                html.P("Competitive performance in elite football has direct financial consequences. "
                       "In the Premier League and UEFA competitions, performance affects:",
                       style={"color": "#c0c4d0", "lineHeight": "1.7", "fontSize": "14px"}),
                html.Div([
                    html.Span("Prize money  ·  ", style={"color": "#FFA15A", "fontWeight": 600}),
                    html.Span("UCL qualification revenue  ·  ", style={"color": "#FFA15A", "fontWeight": 600}),
                    html.Span("Broadcasting revenue  ·  ", style={"color": "#FFA15A", "fontWeight": 600}),
                    html.Span("Sponsorship visibility  ·  ", style={"color": "#FFA15A", "fontWeight": 600}),
                    html.Span("Player market value  ·  ", style={"color": "#FFA15A", "fontWeight": 600}),
                    html.Span("Club reputation", style={"color": "#FFA15A", "fontWeight": 600}),
                ], style={"lineHeight": "1.8", "fontSize": "13px", "marginTop": "8px"}),
                html.P("Even small performance differences translate into large financial consequences "
                       "over a season. A prototype identifying congested periods and linking them to "
                       "performance has practical value as a decision-support tool.",
                       style={"color": "#c0c4d0", "lineHeight": "1.7", "fontSize": "14px", "marginTop": "8px"}),
            ], style={**CARD_STYLE, "flex": "1", "minWidth": "300px"}),
            html.Div([
                html.H4("👤  Personal Motivation", style={"color": "#AB63FA", "marginBottom": "12px"}),
                html.P("The personal motivation for this topic comes from an interest in football analytics "
                       "and the application of data science to real competitive problems. Fixture congestion "
                       "combines tactical, physical, and strategic dimensions while being measurable through "
                       "publicly available data.",
                       style={"color": "#c0c4d0", "lineHeight": "1.7", "fontSize": "14px"}),
                html.P("The topic offers a balance between research and practical application — studying "
                       "an important question in sports performance analysis while developing a prototype "
                       "dashboard with clear real-world usefulness for analysts and coaching staff.",
                       style={"color": "#c0c4d0", "lineHeight": "1.7", "fontSize": "14px", "marginTop": "8px"}),
            ], style={**CARD_STYLE, "flex": "1", "minWidth": "300px"}),
        ], style={"display": "flex", "flexWrap": "wrap", "gap": "16px", "marginTop": "16px"}),
    ], style=SECTION_STYLE),

    # ── OBJECTIVES & HYPOTHESES ──
    html.Div([
        html.H3("Objectives & Hypotheses", className="section-title"),
        html.Div([
            html.Div([
                html.H4("Main Objective", style={"color": "#00BC8C", "marginBottom": "12px"}),
                html.P("To develop a data-driven framework that quantifies fixture congestion and evaluates "
                       "its relationship with competitive performance and squad rotation in Premier League "
                       "clubs competing in European competitions.",
                       style={"color": "#c0c4d0", "lineHeight": "1.7", "fontSize": "14px", "fontStyle": "italic"}),
                html.P("This includes both the analytical and practical sides — studying the phenomenon "
                       "and building a prototype that identifies congested periods and supports "
                       "football decision-making.",
                       style={"color": "#8a8f9d", "lineHeight": "1.6", "fontSize": "13px", "marginTop": "8px"}),
            ], style={**CARD_STYLE, "flex": "1.2", "minWidth": "300px"}),
            html.Div([
                html.H4("Specific Objectives", style={"color": "#636EFA", "marginBottom": "12px"}),
                html.Ol([
                    html.Li("Collect and integrate match, lineup, and performance data"),
                    html.Li("Compute congestion indicators (rest days, rolling windows, overlap)"),
                    html.Li("Analyse congestion vs performance (points, xG, results)"),
                    html.Li("Analyse congestion vs rotation (lineup changes, minutes distribution)"),
                    html.Li("Compare across congestion levels"),
                    html.Li("Build prototype dashboard for analysts and coaching staff"),
                ], style={"color": "#c0c4d0", "lineHeight": "2.0", "fontSize": "14px", "paddingLeft": "20px"}),
            ], style={**CARD_STYLE, "flex": "1", "minWidth": "300px"}),
        ], style={"display": "flex", "flexWrap": "wrap", "gap": "16px"}),
        html.Div([
            html.H4("Hypotheses", style={"color": "#ffffff", "marginBottom": "12px"}),
            html.Div([
                html.Div([
                    html.Span("H1", style={"fontWeight": 700, "color": "#E74C3C"}),
                    html.Span("  Lower rest days → lower performance", style={"color": "#c0c4d0"}),
                ], style={**CARD_STYLE, "padding": "12px 16px", "flex": "1", "minWidth": "200px"}),
                html.Div([
                    html.Span("H2", style={"fontWeight": 700, "color": "#F39C12"}),
                    html.Span("  Higher congestion → greater rotation", style={"color": "#c0c4d0"}),
                ], style={**CARD_STYLE, "padding": "12px 16px", "flex": "1", "minWidth": "200px"}),
                html.Div([
                    html.Span("H3", style={"fontWeight": 700, "color": "#AB63FA"}),
                    html.Span("  Clubs differ in rotation response", style={"color": "#c0c4d0"}),
                ], style={**CARD_STYLE, "padding": "12px 16px", "flex": "1", "minWidth": "200px"}),
                html.Div([
                    html.Span("H4", style={"fontWeight": 700, "color": "#00BC8C"}),
                    html.Span("  Dashboard effectively identifies congestion windows", style={"color": "#c0c4d0"}),
                ], style={**CARD_STYLE, "padding": "12px 16px", "flex": "1", "minWidth": "200px"}),
            ], style={"display": "flex", "flexWrap": "wrap", "gap": "12px"}),
        ], style={"marginTop": "16px"}),
    ], style=SECTION_STYLE),

    # ── DATA SOURCES ──
    html.Div([
        html.H3("Data Sources", className="section-title"),
        html.Div([
            html.Div([
                html.H4("📊  Performance & Workload", style={"color": "#636EFA", "marginBottom": "8px"}),
                html.P("FBRef and Opta-derived datasets capturing player minutes, expected goals (xG), "
                       "progressive actions, and per-match performance metrics.",
                       style={"color": "#c0c4d0", "fontSize": "13px", "lineHeight": "1.6"}),
            ], style={**CARD_STYLE, "flex": "1", "minWidth": "200px"}),
            html.Div([
                html.H4("📅  Fixture Calendar", style={"color": "#00BC8C", "marginBottom": "8px"}),
                html.P("Official match logs from the Premier League and UEFA to calculate precise "
                       "recovery windows — accounting for midweek travel and short-turnaround games.",
                       style={"color": "#c0c4d0", "fontSize": "13px", "lineHeight": "1.6"}),
            ], style={**CARD_STYLE, "flex": "1", "minWidth": "200px"}),
            html.Div([
                html.H4("🏥  Squad Context", style={"color": "#FFA15A", "marginBottom": "8px"}),
                html.P("Transfermarkt and injury databases to account for external variables like "
                       "injuries and suspensions — distinguishing tactical vs forced rotation.",
                       style={"color": "#c0c4d0", "fontSize": "13px", "lineHeight": "1.6"}),
            ], style={**CARD_STYLE, "flex": "1", "minWidth": "200px"}),
        ], style={"display": "flex", "flexWrap": "wrap", "gap": "16px"}),
    ], style=SECTION_STYLE),

    # ── DASHBOARD NAVIGATION ──
    html.Div([
        html.H3("Dashboard Sections", className="section-title"),
        html.P("Explore the analysis through the following sections:",
               style={"color": "#8a8f9d", "marginBottom": "16px", "fontSize": "14px"}),
        html.Div([
            html.Div(_nav_card("📊", "Congestion", "Rest days, ACWR distribution, high congestion analysis, away streaks", "/congestion", "#636EFA"), className="kpi-card", style={"cursor": "pointer"}),
            html.Div(_nav_card("⚡", "Performance", "Player search, rating trends, decline analysis by position and competition", "/performance", "#00BC8C"), className="kpi-card", style={"cursor": "pointer"}),
            html.Div(_nav_card("🩺", "Injury Risk", "Injury burden by team, risk signals, ACWR danger zones", "/injury-risk", "#E74C3C"), className="kpi-card", style={"cursor": "pointer"}),
            html.Div(_nav_card("🔄", "Rotation", "Minutes distribution, sub patterns, lineup depth by position", "/rotation", "#FFA15A"), className="kpi-card", style={"cursor": "pointer"}),
            html.Div(_nav_card("🤖", "Model Insights", "Feature importance, decline by rest/ACWR, UCL comparison", "/model-insights", "#AB63FA"), className="kpi-card", style={"cursor": "pointer"}),
            html.Div(_nav_card("⚔️", "Team Compare", "Side-by-side team radar charts and competition breakdown", "/team-compare", "#EF553B"), className="kpi-card", style={"cursor": "pointer"}),
        ], style={"display": "flex", "flexWrap": "wrap", "gap": "16px"}),
    ], style=SECTION_STYLE),

    # ── FOOTER ──
    html.Div([
        html.Hr(style={"borderColor": "#2a2e3a"}),
        html.P("Fixture-IQ  ·  Data Science for Football Analytics  ·  Seasons 2022-2025",
               style={"color": "#5a5f6d", "fontSize": "12px", "textAlign": "center", "padding": "16px 0"}),
    ]),
])


@dash.callback(
    Output("landing-kpis", "children"),
    Input("global-store", "data"),
)
def update_kpis(store):
    d = filter_df(df, store.get("team"), store.get("season"), store.get("competition"))
    cards = [
        kpi_card("Matches Analyzed", f"{len(d):,}", color="#636EFA"),
        kpi_card("Players Tracked", f"{d['player_name'].nunique():,}", color="#00BC8C"),
        kpi_card("Teams", f"{d['player_team'].nunique():,}", color="#EF553B"),
        kpi_card("Seasons", f"{d['season'].nunique()}", color="#AB63FA"),
        kpi_card("Avg Rest Days", f"{d['rest_days'].mean():.1f}", "d", color="#FFA15A"),
        kpi_card("Decline Rate", f"{d['is_decline'].mean()*100:.1f}", "%", color="#E74C3C"),
    ]
    return [html.Div([
        html.Div(c["title"], className="kpi-title"),
        html.Div(c["value"], className="kpi-value", style={"color": c["color"]}),
    ], className="kpi-card") for c in cards]
