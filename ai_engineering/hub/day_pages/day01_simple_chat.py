"""Day 01 — Simple GenAI Chat with streaming and conversation memory."""

import streamlit as st
from config import get_ollama_client


# Same system instructions as original Day 01 app.py
SYSTEM_INSTRUCTIONS = "You are an AI assistant who helps employees with their queries. Give clear, accurate, and helpful answers."


def render():
    st.caption("Chat with a local Ollama model — streaming responses with conversation memory")

    model = st.session_state.get("ollama_model", "qwen2.5:3b")
    host = st.session_state.get("ollama_host", "http://localhost:11434")

    # ── Sidebar-like controls in a top row ─────────────────────────────
    col_info, col_clear = st.columns([3, 1])
    with col_info:
        st.info(f"🤖 Model: **{model}** • Host: `{host}`")
    with col_clear:
        if st.button("🗑️ Clear Chat", width="stretch", key="day01_clear"):
            st.session_state.day01_messages = []
            st.rerun()

    # ── Initialise conversation history ────────────────────────────────
    if "day01_messages" not in st.session_state:
        st.session_state.day01_messages = []

    # ── Display previous messages ──────────────────────────────────────
    for msg in st.session_state.day01_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # ── Chat input ─────────────────────────────────────────────────────
    if prompt := st.chat_input("Ask the AI assistant…"):
        # Show user message immediately
        st.session_state.day01_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Build full message list for the model (system + history)
        messages = [{"role": "system", "content": SYSTEM_INSTRUCTIONS}]
        messages.extend(
            {"role": m["role"], "content": m["content"]}
            for m in st.session_state.day01_messages
        )

        # Stream the response
        with st.chat_message("assistant"):
            try:
                client = get_ollama_client(host)
                response = client.chat(
                    model=model,
                    messages=messages,
                    stream=True,
                    options={"num_ctx": 2048},
                )
                full_response = st.write_stream(
                    chunk.message.content
                    for chunk in response
                    if chunk.message.content
                )
                st.session_state.day01_messages.append(
                    {"role": "assistant", "content": full_response}
                )
            except Exception as exc:
                st.error(f"⚠️ Could not reach Ollama: {exc}")
                st.info(
                    "Make sure Ollama is running and the model is pulled:\n"
                    f"```\nollama pull {model}\n```"
                )
