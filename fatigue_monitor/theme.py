DARK_CSS = """
<style>
    .stApp { background-color: #0e1117; }
    h1, h2, h3, h4, h5, h6 { color: #ffffff !important; }
    p, li, span, div { color: #e0e0e0; }
    .stMarkdown p { color: #e0e0e0; }

    /* ---- Metric containers ---- */
    div[data-testid="metric-container"] {
        background: linear-gradient(135deg, #1a1d27 0%, #222736 100%);
        border: 1px solid #2a2e3a;
        border-radius: 14px;
        padding: 16px 20px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    }
    div[data-testid="metric-container"] > label {
        font-size: 12px !important; font-weight: 500 !important;
        text-transform: uppercase !important; letter-spacing: 1px !important;
        color: #8a8f9d !important;
    }
    div[data-testid="metric-container"] > div[data-testid="metric-value"] {
        font-size: 28px !important; font-weight: 700 !important;
    }

    /* ---- Form controls ---- */
    .stSelectbox label { color: #8b949e !important; font-size: 13px; }
    .stSelectbox div[data-baseweb="select"] > div {
        background-color: #1c2128; border-color: #30363d; border-radius: 8px;
    }
    .block-container { padding-top: 1.5rem !important; }
    hr { border-color: #21262d !important; }

    /* ---- Tabs ---- */
    .stTabs [data-baseweb="tab-list"] { background-color: #1a1d27; border-color: #2a2e3a; }
    .stTabs [data-baseweb="tab"] { color: #8a8f9d; }
    .stTabs [aria-selected="true"] { color: #00BC8C !important; }

    /* ---- Alerts ---- */
    .stAlert { background-color: #1c2128; border: 1px solid #30363d; color: #c9d1d9; border-radius: 8px; }

    /* ---- Buttons ---- */
    .stButton button {
        background: linear-gradient(135deg, #00BC8C 0%, #009d73 100%);
        color: white; border: none; border-radius: 8px;
        font-weight: 600; font-size: 14px; padding: 6px 16px;
        transition: all 0.15s ease;
    }
    .stButton button:hover {
        background: linear-gradient(135deg, #00d496 0%, #00a37a 100%);
        color: white; box-shadow: 0 4px 12px rgba(0,188,140,0.3);
    }
    .stDownloadButton button {
        background: #21262d; border: 1px solid #30363d; color: #c9d1d9;
        border-radius: 8px; font-weight: 500;
    }
    .stDownloadButton button:hover { background: #30363d; border-color: #484f58; }
    .main .block-container {padding-top: 4rem; max-width: 1400px; }

    /* ---- Risk & flag badges ---- */
    .risk-badge { display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }
    .risk-Low { background: #27ae60; color: white; }
    .risk-Medium { background: #f39c12; color: white; }
    .risk-High { background: #e74c3c; color: white; }
    .risk-Very\\ High { background: #8e44ad; color: white; }
    .flag-Monitor { background: #e74c3c; color: white; padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; }
    .flag-Clear { background: #27ae60; color: white; padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; }

    /* ---- Section card ---- */
    .section-card {
        background: #1a1d27;
        border: 1px solid #2a2e3a;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 16px;
        transition: border-color 0.2s ease, box-shadow 0.2s ease;
    }
    .section-card:hover {
        border-color: #3a3e4a;
        box-shadow: 0 4px 24px rgba(0,0,0,0.25);
    }
    .section-card-accent-top {
        border-top: 3px solid #00BC8C;
    }
    .section-card-accent-v4 {
        border-top: 3px solid #636EFA;
    }
    .section-card-accent-fatigue {
        border-top: 3px solid #00BC8C;
    }
    .section-card-accent-perf {
        border-top: 3px solid #8e44ad;
    }

    /* ---- Stat block (icon + value + label) ---- */
    .stat-block {
        background: linear-gradient(135deg, #161b22 0%, #1c2128 100%);
        border: 1px solid #2a2e3a;
        border-radius: 10px;
        padding: 14px 16px;
        text-align: center;
        transition: border-color 0.2s ease, transform 0.15s ease;
    }
    .stat-block:hover {
        border-color: #3a3e4a;
        transform: translateY(-1px);
    }
    .stat-block .stat-icon { font-size: 22px; margin-bottom: 6px; }
    .stat-block .stat-value {
        font-size: 26px; font-weight: 700; color: #e0e0e0; line-height: 1.1;
    }
    .stat-block .stat-label {
        font-size: 12px; font-weight: 500; color: #8a8f9d; margin-top: 2px;
    }

    /* ---- Tag pill ---- */
    .tag-pill {
        display: inline-block;
        font-size: 11px; font-weight: 500;
        padding: 2px 10px; border-radius: 20px;
        margin-right: 5px; margin-bottom: 4px;
        border: 1px solid;
    }

    /* ---- Section divider ---- */
    .section-divider {
        height: 1px;
        background: linear-gradient(90deg, transparent, #2a2e3a, transparent);
        margin: 28px 0;
    }

    /* ---- Table improvements ---- */
    .data-table tbody tr {
        transition: background 0.15s ease;
    }
    .data-table tbody tr:hover {
        background: rgba(0,188,140,0.06) !important;
    }
    .data-table tbody tr:nth-child(even) {
        background: rgba(26,29,39,0.5);
    }

    /* ---- Hover lift for cards ---- */
    .hover-lift {
        transition: transform 0.15s ease, box-shadow 0.2s ease;
    }
    .hover-lift:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 30px rgba(0,0,0,0.3);
    }

    /* ---- Utility ---- */
    .fg-subtle { color: #8a8f9d; }
    .fg-muted { color: #8b949e; }
    .text-sm { font-size: 12px; }
    .text-xs { font-size: 11px; }

    /* ---- Hide toolbar ---- */
    [data-testid="stToolbar"] { display: none; }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }

    /* ---- Custom scrollbar ---- */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: #0e1117; }
    ::-webkit-scrollbar-thumb { background: #2a2e3a; border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: #3a3e4a; }
</style>
"""
