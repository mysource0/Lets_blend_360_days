"""Day 06 — Embedding & Retrieval: query the local vector index."""

import json
import streamlit as st
from pathlib import Path

from config import DAY_DIRS, add_day_to_path


def _find_indexes() -> list[Path]:
    """Find all built embedding indexes under Day 06 outputs."""
    embed_dir = DAY_DIRS[6] / "outputs" / "embeddings"
    if not embed_dir.exists():
        return []
    indexes = []
    for d in sorted(embed_dir.iterdir()):
        if d.is_dir() and (d / "vectors.npz").exists() and (d / "manifest.json").exists():
            indexes.append(d)
    return indexes


def render():
    st.caption("Query local vector embeddings built from Day 05 chunks")

    # ── Check for pre-built indexes ────────────────────────────────────
    indexes = _find_indexes()

    if not indexes:
        st.warning("⚠️ No embedding indexes found.")
        st.markdown(
            """
**Build an index first** by running Day 06's embedding builder:

```powershell
cd path\\to\\Lets_blend_360_days\\ai_engineering\\06_embedding_and_retrieval
python -m src.embeddings.build_embeddings --input ..\\05_document_chunking\\outputs\\employee_policy_md_chunked.json --output-dir outputs\\embeddings\\employee_policy_md_structure
```

Then refresh this page.
            """
        )
        return

    # ── Index selector ─────────────────────────────────────────────────
    col_idx, col_opts = st.columns([2, 1])

    with col_idx:
        index_names = [p.name for p in indexes]
        selected_name = st.selectbox("📂 Select Index", index_names, key="day06_idx")
        selected_path = indexes[index_names.index(selected_name)]

        # Show manifest info
        try:
            manifest = json.loads((selected_path / "manifest.json").read_text(encoding="utf-8"))
            c1, c2, c3 = st.columns(3)
            c1.metric("Model", manifest.get("model_id", "?").split("/")[-1])
            c2.metric("Dimension", manifest.get("vector_dimension", "?"))
            c3.metric("Chunks", manifest.get("chunk_count", "?"))
        except Exception:
            pass

    with col_opts:
        top_k = st.slider("🔝 Top-K results", 1, 20, 5, key="day06_topk")

    # ── Query input ────────────────────────────────────────────────────
    query = st.text_input("🔍 Search query", placeholder="What is the expense claim deadline?", key="day06_query")

    if st.button("🔎 Search", type="primary", width="stretch", key="day06_run"):
        if not query or not query.strip():
            st.warning("Enter a search query.")
            return

        try:
            add_day_to_path(6)
            import importlib
            search_mod = importlib.import_module("src.retrieval.search")
            search_index = search_mod.search_index

            with st.spinner("Searching embeddings…"):
                results = search_index(query.strip(), str(selected_path), k=top_k)

            st.divider()
            st.subheader(f"📊 Results ({len(results)} matches)")

            if not results:
                st.info("No results found.")
                return

            for r in results:
                score = r.get("similarity", 0)
                rank = r.get("rank", "?")
                chunk_id = r.get("chunk_id", "unknown")[:16]
                text = r.get("text", "")

                # Color-coded score badge
                if score >= 0.7:
                    badge = "🟢"
                elif score >= 0.4:
                    badge = "🟡"
                else:
                    badge = "🔴"

                with st.expander(f"{badge} Rank #{rank} — Score: {score:.4f} — `{chunk_id}…`"):
                    st.markdown(text[:1500])
                    meta = r.get("metadata", {})
                    if meta:
                        st.json(meta)

        except Exception as exc:
            st.error(f"Search failed: {exc}")
            import traceback
            with st.expander("Stack trace"):
                st.code(traceback.format_exc())
