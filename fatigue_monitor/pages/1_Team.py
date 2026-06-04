import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st
from fatigue_monitor.theme import DARK_CSS
from fatigue_monitor.views.team_overview import team_overview_page


st.set_page_config(
    page_title="Team Overview",
    page_icon="�",
    layout="wide",
)

st.markdown(DARK_CSS, unsafe_allow_html=True)

team_overview_page()
