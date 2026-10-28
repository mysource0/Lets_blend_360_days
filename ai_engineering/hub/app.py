"""
AI Engineering Hub — Unified Streamlit application for Days 01–11.

Launch:
    cd ai_engineering
    streamlit run hub/app.py
"""

import sys
from pathlib import Path

# ── Make hub/ importable ───────────────────────────────────────────────
HUB_DIR = Path(__file__).resolve().parent
if str(HUB_DIR) not in sys.path:
    sys.path.insert(0, str(HUB_DIR))

import importlib
import streamlit as st

# ── Page config (must be first Streamlit call) ─────────────────────────
st.set_page_config(
    page_title="AI Engineering Hub",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Premium CSS ────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Global font: uses a locally installed font, with no external request */
    html, body, [class*="css"] {
        font-family: 'Inter', 'Segoe UI', system-ui, -apple-system, sans-serif;
    }

    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
    }
    [data-testid="stSidebar"] [data-testid="stMarkdown"],
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] .stRadio label,
    [data-testid="stSidebar"] .stCaption,
    [data-testid="stSidebar"] span {
        color: #e0e0e0 !important;
    }
    [data-testid="stSidebar"] hr {
        border-color: rgba(255,255,255,0.1);
    }

    /* Radio button highlight */
    [data-testid="stSidebar"] [role="radiogroup"] label[data-checked="true"] {
        background: rgba(108, 99, 255, 0.25);
        border-radius: 8px;
        padding: 2px 8px;
    }

    /* Main header gradient */
    .hub-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        color: white;
    }
    .hub-header h1 {
        margin: 0;
        font-size: 1.8rem;
        font-weight: 700;
    }
    .hub-header p {
        margin: 0.3rem 0 0 0;
        opacity: 0.9;
        font-size: 0.95rem;
    }

    /* Card containers */
    .info-card {
        background: rgba(108, 99, 255, 0.08);
        border: 1px solid rgba(108, 99, 255, 0.2);
        border-radius: 10px;
        padding: 1.2rem;
        margin-bottom: 1rem;
    }

    /* Metric cards */
    [data-testid="stMetric"] {
        background: rgba(108, 99, 255, 0.06);
        border: 1px solid rgba(108, 99, 255, 0.15);
        border-radius: 10px;
        padding: 0.8rem;
    }

    /* Button styling */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border: none;
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    .stButton > button[kind="primary"]:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
    }

    /* Chat message styling */
    [data-testid="stChatMessage"] {
        border-radius: 12px;
        margin-bottom: 0.5rem;
    }

    /* Expander styling */
    .streamlit-expanderHeader {
        font-weight: 600;
        border-radius: 8px;
    }

    /* Divider */
    hr {
        opacity: 0.3;
    }

    /* Tab styling */
    .stTabs [data-baseweb="tab"] {
        font-weight: 500;
        border-radius: 8px 8px 0 0;
    }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ────────────────────────────────────────────────────────────
from components.sidebar import render_sidebar, DAYS
from config import SHOW_TRACEBACKS
selected_day = render_sidebar()

# ── Page header ────────────────────────────────────────────────────────
icon, name, desc = DAYS[selected_day]
st.markdown(
    f"""<div class="hub-header">
        <h1>{icon} {name} — {desc}</h1>
        <p>AI Engineering • 11-Day Learning Journey</p>
    </div>""",
    unsafe_allow_html=True,
)

# ── Dynamic page loading ──────────────────────────────────────────────
PAGE_MODULES = [
    "day_pages.day01_simple_chat",
    "day_pages.day02_context_levels",
    "day_pages.day03_structured_output",
    "day_pages.day04_task_api",
    "day_pages.day05_chunking",
    "day_pages.day06_embeddings",
    "day_pages.day07_rag",
    "day_pages.day08_evaluation",
    "day_pages.day09_architecture",
    "day_pages.day10_tool_calling",
    "day_pages.day11_agents",
]

try:
    page_module = importlib.import_module(PAGE_MODULES[selected_day])
    page_module.render()
except Exception as exc:
    st.error(f"Failed to load page: {exc}")
    if SHOW_TRACEBACKS:
        with st.expander("Stack trace"):
            import traceback
            st.code(traceback.format_exc())
    else:
        st.caption("Set HUB_SHOW_TRACEBACKS=1 to see the stack trace.")
