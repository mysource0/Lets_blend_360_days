"""Day 02 — Context Level Comparison: baseline vs instructions vs grounded."""

import time
import streamlit as st
from config import get_ollama_client


# Same system instructions as the original Day 02 context_experiments.py
SYSTEM_INSTRUCTIONS = """
    You are an AI assistant who helps employees with their queries.

    - Give clear, accurate, and helpful answers.
    - Do not invent facts or present guesses as confirmed information.
    - If you do not know an answer, clearly say so.
    - wrong answer might cause global warming.
    - If a question is ambiguous, ask for clarification.
    - Keep answers concise but sufficiently detailed.
    - Use only supplied context for internal company information.
    - If the context does not contain the answer, say so.
    """

SAMPLE_CONTEXTS = {
    "(none)": "",
    "Leave Policy": (
        "Employees receive 12 sick leave days per year. "
        "Leave requests must be submitted to their manager at least 3 days in advance. "
        "Unused sick leave does not carry over to the next calendar year."
    ),
    "Expense Policy": (
        "A readable receipt is required for each expense of 500 currency units or more. "
        "Expense claims must be submitted within 30 days of the transaction. "
        "Travel meals are reimbursed up to 50 currency units per day."
    ),
}


def _stream_version(client, model, messages, label):
    """Run one version and return (response_text, elapsed_seconds)."""
    start = time.time()
    try:
        response = client.chat(
            model=model,
            messages=messages,
            stream=True,
            options={"num_ctx": 2048},
        )
        full = st.write_stream(
            chunk.message.content
            for chunk in response
            if chunk.message.content
        )
        elapsed = time.time() - start
        st.caption(f"⏱️ {elapsed:.1f}s")
        return full, elapsed
    except Exception as exc:
        st.error(f"Error: {exc}")
        return None, 0.0


def render():
    st.caption("Compare three prompting strategies side-by-side on the same question")

    model = st.session_state.get("ollama_model", "qwen2.5:3b")
    host = st.session_state.get("ollama_host", "http://localhost:11434")

    # ── Inputs ─────────────────────────────────────────────────────────
    question = st.text_area(
        "❓ Your Question",
        placeholder="Enter your employee query here…",
        help="This question is sent to all three versions.",
        key="day02_question",
    )

    col_ctx_select, col_ctx_text = st.columns([1, 2])
    with col_ctx_select:
        preset = st.selectbox("📄 Context preset", list(SAMPLE_CONTEXTS.keys()), key="day02_preset")
    with col_ctx_text:
        context = st.text_area(
            "Context (Version C only)",
            value=SAMPLE_CONTEXTS[preset],
            placeholder="Paste context here when the test case provides it…",
            help="This context will only be given to Version C.",
            key="day02_context",
        )

    # ── Run button ─────────────────────────────────────────────────────
    if st.button("🚀 Compare All 3 Versions", type="primary", width="stretch", key="day02_run"):
        if not question or not question.strip():
            st.warning("Please enter a question first.")
            return

        try:
            client = get_ollama_client(host)
        except Exception as exc:
            st.error(f"Cannot connect to Ollama: {exc}")
            return

        tab_a, tab_b, tab_c = st.tabs([
            "🅰️ Version A — Baseline",
            "🅱️ Version B — With Instructions",
            "🅲 Version C — Instructions + Context",
        ])

        # Version A: Baseline — no system prompt
        with tab_a:
            st.markdown("**No system instructions** — raw model response")
            msgs_a = [{"role": "user", "content": question.strip()}]
            _stream_version(client, model, msgs_a, "A")

        # Version B: With system instructions
        with tab_b:
            st.markdown("**System instructions added** — guides behaviour")
            msgs_b = [
                {"role": "system", "content": SYSTEM_INSTRUCTIONS},
                {"role": "user", "content": question.strip()},
            ]
            _stream_version(client, model, msgs_b, "B")

        # Version C: Instructions + grounded context
        with tab_c:
            st.markdown("**System instructions + supplied context** — grounded answers")
            if context and context.strip():
                user_msg = (
                    f"Context:\n{context}\n\n"
                    f"Question:\n{question.strip()}\n\n"
                    "Use the supplied context for your answer.\n"
                    "If the answer is missing from the context, say you do not know."
                )
            else:
                user_msg = question.strip()
                st.warning("No context supplied — Version C will behave like Version B.")
            msgs_c = [
                {"role": "system", "content": SYSTEM_INSTRUCTIONS},
                {"role": "user", "content": user_msg},
            ]
            _stream_version(client, model, msgs_c, "C")
