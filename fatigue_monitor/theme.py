DARK_CSS = """
<style>
    .stApp { background-color: #0e1117; }
    h1, h2, h3, h4, h5, h6 { color: #ffffff !important; }
    p, li, span, div { color: #e0e0e0; }
    .stMarkdown p { color: #e0e0e0; }

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

    .stSelectbox label { color: #8b949e !important; font-size: 13px; }
    .stSelectbox div[data-baseweb="select"] > div {
        background-color: #1c2128; border-color: #30363d; border-radius: 8px;
    }
    .block-container { padding-top: 1.5rem !important; }

    hr { border-color: #21262d !important; }
    .stTabs [data-baseweb="tab-list"] { background-color: #1a1d27; border-color: #2a2e3a; }
    .stTabs [data-baseweb="tab"] { color: #8a8f9d; }
    .stTabs [aria-selected="true"] { color: #00BC8C !important; }
    .stAlert { background-color: #1c2128; border: 1px solid #30363d; color: #c9d1d9; border-radius: 8px; }
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

    .risk-badge { display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }
    .risk-Low { background: #27ae60; color: white; }
    .risk-Medium { background: #f39c12; color: white; }
    .risk-High { background: #e74c3c; color: white; }
    .risk-Very\\ High { background: #8e44ad; color: white; }
    .flag-Monitor { background: #e74c3c; color: white; padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; }
    .flag-Clear { background: #27ae60; color: white; padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; }

    [data-testid="stToolbar"] { display: none; }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
</style>
"""
