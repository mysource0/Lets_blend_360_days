"""Sidebar component — day selector, model configuration, and status."""

import streamlit as st

from config import DEFAULT_MODEL, DEFAULT_HOST, get_available_models, check_ollama_connection

# ── Day catalogue with icons ──────────────────────────────────────────
DAYS = [
    ("💬", "Day 01", "Simple GenAI Chat"),
    ("🔬", "Day 02", "Context Level Comparison"),
    ("📋", "Day 03", "Structured Output & Validation"),
    ("🔧", "Day 04", "Task Management API"),
    ("✂️",  "Day 05", "Document Chunking"),
    ("🔢", "Day 06", "Embedding & Retrieval"),
    ("📚", "Day 07", "RAG Pipeline"),
    ("📊", "Day 08", "RAG Evaluation"),
    ("🏗️",  "Day 09", "Architecture Decisions"),
    ("🛠️",  "Day 10", "Tool Calling Agent"),
    ("🔁",  "Day 11", "Agents and ReAct"),
]


def render_sidebar() -> int:
    """Render the sidebar and return the selected day index (0-based)."""
    with st.sidebar:
        # ── Title ──────────────────────────────────────────────
        st.markdown(
            "<h2 style='text-align:center;'>🧠 AI Engineering Hub</h2>",
            unsafe_allow_html=True,
        )
        st.caption("11-Day Learning Journey • Powered by Ollama")
        st.divider()

        # ── Day selector ───────────────────────────────────────
        day_labels = [f"{icon}  {name} — {desc}" for icon, name, desc in DAYS]
        selected = st.radio(
            "📅 Select a Day",
            range(len(DAYS)),
            format_func=lambda i: day_labels[i],
            label_visibility="collapsed",
        )

        st.divider()

        # ── Model configuration ────────────────────────────────
        st.markdown("### ⚙️ Model Settings")

        host = st.text_input("Ollama Host", value=DEFAULT_HOST, key="cfg_host")

        # Fetch available models (cached 30 s)
        available = _cached_models(host)

        if available:
            default_idx = 0
            if DEFAULT_MODEL in available:
                default_idx = available.index(DEFAULT_MODEL)
            model = st.selectbox("Model", available, index=default_idx, key="cfg_model_select")
        else:
            model = st.text_input("Model (manual)", value=DEFAULT_MODEL, key="cfg_model_text")

        # Store in session state so every page can access it
        st.session_state["ollama_model"] = model
        st.session_state["ollama_host"] = host

        st.divider()

        # ── Connection status ──────────────────────────────────
        if available:
            st.success(f"✅ Connected — {len(available)} model(s)")
        else:
            st.error("❌ Ollama not reachable")
            st.caption("Start Ollama and refresh the page.")

        # ── Clear chat button ──────────────────────────────────
        if st.button("🗑️ Clear Chat History", width="stretch"):
            for key in list(st.session_state.keys()):
                if key.startswith("day"):
                    del st.session_state[key]
            st.rerun()

    return selected


@st.cache_data(ttl=30, show_spinner=False)
def _cached_models(host: str) -> list[str]:
    return get_available_models(host)
