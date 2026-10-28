"""Day 07 — RAG Pipeline: retrieval → context → generation → citation validation."""

import json
import time
import streamlit as st
from pathlib import Path

from config import DAY_DIRS, add_day_to_path


def _default_index_dir() -> Path:
    """Return the default Day 06 structure index path."""
    return DAY_DIRS[6] / "outputs" / "embeddings" / "employee_policy_md_structure"


def render():
    st.caption("End-to-end Retrieval-Augmented Generation with citation validation")

    model = st.session_state.get("ollama_model", "qwen2.5:3b")
    host = st.session_state.get("ollama_host", "http://localhost:11434")

    # ── Check prerequisites ────────────────────────────────────────────
    index_dir = _default_index_dir()
    if not index_dir.exists():
        st.warning("⚠️ No Day 06 embedding index found.")
        st.markdown(
            """
**The RAG pipeline requires a pre-built embedding index from Day 06.**

Build one first:
```powershell
cd path\\to\\Lets_blend_360_days\\ai_engineering\\06_embedding_and_retrieval
python -m src.embeddings.build_embeddings --input ..\\05_document_chunking\\outputs\\employee_policy_md_chunked.json --output-dir outputs\\embeddings\\employee_policy_md_structure
```
            """
        )
        return

    # ── Controls ───────────────────────────────────────────────────────
    col_q, col_opts = st.columns([2, 1])

    with col_q:
        question = st.text_area(
            "❓ Ask about employee policies",
            placeholder="What is the expense receipt threshold?",
            key="day07_q",
        )

    with col_opts:
        top_k = st.slider("🔝 Top-K retrieval", 1, 10, 5, key="day07_topk")
        max_ctx = st.slider("📏 Max context (chars)", 2000, 10000, 6000, 500, key="day07_ctx")
        show_debug = st.checkbox("🐛 Show debug info", key="day07_debug")

    # ── Run RAG ────────────────────────────────────────────────────────
    if st.button("📚 Run RAG Pipeline", type="primary", width="stretch", key="day07_run"):
        if not question or not question.strip():
            st.warning("Enter a question.")
            return

        try:
            add_day_to_path(7)

            # Set environment for Ollama config
            import os
            os.environ["OLLAMA_HOST"] = host
            os.environ["OLLAMA_MODEL"] = model

            from rag.pipeline import run_rag

            start = time.time()
            with st.spinner("Retrieving → Building context → Generating answer…"):
                result = run_rag(
                    question.strip(),
                    index_dir=str(index_dir),
                    top_k=top_k,
                    max_context_chars=max_ctx,
                    include_debug=show_debug,
                )
            elapsed = time.time() - start

            st.divider()

            # ── Answer ─────────────────────────────────────────────────
            col_ans, col_meta = st.columns([2, 1])

            with col_ans:
                st.subheader("💬 Answer")
                answer = result.get("answer", "No answer generated")
                insufficient = result.get("insufficient_evidence", False)

                if insufficient:
                    st.warning("⚠️ Insufficient evidence in the corpus")
                st.markdown(answer)

                # Citations
                citations = result.get("citations", [])
                if citations:
                    st.subheader("📎 Citations")
                    for c in citations:
                        st.code(c)

                # Sources
                sources = result.get("sources", [])
                if sources:
                    st.subheader("📄 Sources")
                    for s in sources:
                        st.markdown(f"- {s}")

            with col_meta:
                st.metric("⏱️ Latency", f"{elapsed:.1f}s")
                st.metric("📎 Citations", len(citations))
                if result.get("verified_citations") is not None:
                    st.metric("✅ Verified", result["verified_citations"])

                # Pipeline flow
                st.markdown("### 🔗 Pipeline")
                st.markdown("""
1. 🔍 **Retrieve** top-K chunks
2. 📝 **Build** evidence context
3. 🤖 **Generate** grounded answer
4. ✅ **Validate** citations
                """)

            # ── Debug ──────────────────────────────────────────────────
            if show_debug and "debug" in result:
                with st.expander("🐛 Debug Info"):
                    st.json(result["debug"])

            # Full result JSON
            with st.expander("📋 Full Response JSON"):
                st.json(result)

        except Exception as exc:
            st.error(f"RAG pipeline failed: {exc}")
            import traceback
            with st.expander("Stack trace"):
                st.code(traceback.format_exc())
