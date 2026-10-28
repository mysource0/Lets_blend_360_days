"""Day 05 — Document Chunking: upload or select sample docs, chunk interactively."""

import json
import importlib.util
import streamlit as st
from pathlib import Path

from config import DAY_DIRS


def _load_chunker():
    """Import parse-and-chunk.py despite the hyphenated filename."""
    script = DAY_DIRS[5] / "parse-and-chunk.py"
    if not script.exists():
        return None
    spec = importlib.util.spec_from_file_location("parse_and_chunk", str(script))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def render():
    st.caption("Parse documents and create structure-aware, retrieval-friendly chunks")

    samples_dir = DAY_DIRS[5] / "samples"
    outputs_dir = DAY_DIRS[5] / "outputs"

    # ── Load the chunker module ────────────────────────────────────────
    chunker = _load_chunker()
    if chunker is None:
        st.error(f"Cannot find `parse-and-chunk.py` in `{DAY_DIRS[5]}`")
        return

    # ── File selection ─────────────────────────────────────────────────
    col_src, col_opts = st.columns([2, 1])

    with col_src:
        st.subheader("📄 Select a Document")
        source = st.radio("Source", ["Sample files", "Upload a file"], horizontal=True, key="day05_src")

        if source == "Sample files":
            sample_files = sorted(samples_dir.glob("*")) if samples_dir.exists() else []
            sample_names = [f.name for f in sample_files if f.suffix in (".pdf", ".docx", ".txt", ".md", ".markdown")]
            if not sample_names:
                st.warning(f"No sample files found in `{samples_dir}`")
                return
            selected_name = st.selectbox("File", sample_names, key="day05_file")
            file_path = samples_dir / selected_name
        else:
            uploaded = st.file_uploader(
                "Upload a document",
                type=["pdf", "docx", "txt", "md"],
                key="day05_upload",
            )
            if uploaded is None:
                st.info("Upload a PDF, DOCX, TXT, or Markdown file to begin.")
                return
            # Save uploaded file temporarily
            tmp_dir = DAY_DIRS[5] / "outputs"
            tmp_dir.mkdir(exist_ok=True)
            file_path = tmp_dir / uploaded.name
            file_path.write_bytes(uploaded.getvalue())

    with col_opts:
        st.subheader("⚙️ Chunking Settings")
        method = st.selectbox("Method", ["structure", "character", "paragraph", "sentence", "recursive"], key="day05_method")
        chunk_size = st.slider("Chunk size (chars)", 200, 3000, 1000, 50, key="day05_size")
        overlap = st.slider("Overlap (chars)", 0, 500, 150, 25, key="day05_overlap")

    # ── Run chunking ───────────────────────────────────────────────────
    if st.button("✂️ Parse & Chunk", type="primary", width="stretch", key="day05_run"):
        try:
            with st.spinner("Parsing document…"):
                documents = chunker.parse_document(str(file_path))

            st.info(f"Parsed **{len(documents)}** document section(s) from `{file_path.name}`")

            with st.spinner("Chunking…"):
                all_chunks = []
                for doc in documents:
                    text = doc["text"]
                    metadata = doc.get("metadata", {})

                    if method == "structure" and hasattr(chunker, "chunk_by_structure"):
                        chunks = chunker.chunk_by_structure(text, chunk_size, overlap, metadata)
                    elif method == "character" and hasattr(chunker, "chunk_by_character"):
                        chunks = chunker.chunk_by_character(text, chunk_size, overlap, metadata)
                    elif method == "paragraph" and hasattr(chunker, "chunk_by_paragraph"):
                        chunks = chunker.chunk_by_paragraph(text, chunk_size, overlap, metadata)
                    elif method == "sentence" and hasattr(chunker, "chunk_by_sentence"):
                        chunks = chunker.chunk_by_sentence(text, chunk_size, overlap, metadata)
                    elif method == "recursive" and hasattr(chunker, "chunk_recursive"):
                        chunks = chunker.chunk_recursive(text, chunk_size, overlap, metadata)
                    elif hasattr(chunker, "chunk_by_structure"):
                        chunks = chunker.chunk_by_structure(text, chunk_size, overlap, metadata)
                    else:
                        st.error(f"Method `{method}` not found in chunker module.")
                        return

                    all_chunks.extend(chunks)

            # ── Results ────────────────────────────────────────────────
            st.divider()
            st.subheader(f"📊 Results: {len(all_chunks)} chunk(s)")

            # Metrics row
            col_m1, col_m2, col_m3, col_m4 = st.columns(4)
            sizes = [len(c.get("text", "")) for c in all_chunks]
            col_m1.metric("Chunks", len(all_chunks))
            col_m2.metric("Avg Size", f"{sum(sizes)/max(len(sizes),1):.0f} chars")
            col_m3.metric("Min Size", f"{min(sizes) if sizes else 0} chars")
            col_m4.metric("Max Size", f"{max(sizes) if sizes else 0} chars")

            # Show chunks
            for i, chunk in enumerate(all_chunks):
                label = f"Chunk {i+1}"
                chunk_id = chunk.get("chunk_id", "")
                if chunk_id:
                    label += f" ({chunk_id[:12]}…)"
                heading = chunk.get("heading_path") or chunk.get("metadata", {}).get("heading_path")
                if heading:
                    label += f" — {heading}"

                with st.expander(label, expanded=(i < 3)):
                    st.text(chunk.get("text", "")[:2000])
                    meta = {k: v for k, v in chunk.items() if k != "text"}
                    if meta:
                        st.json(meta)

            # ── Save output ────────────────────────────────────────────
            outputs_dir.mkdir(exist_ok=True)
            stem = file_path.stem.replace(" ", "_")
            output_file = outputs_dir / f"{stem}_{method}_chunked.json"
            output_data = {
                "experiment": {
                    "method": method,
                    "chunk_size": chunk_size,
                    "overlap": overlap,
                    "source": str(file_path),
                },
                "chunks": all_chunks,
            }
            output_file.write_text(json.dumps(output_data, indent=2, ensure_ascii=False), encoding="utf-8")
            st.success(f"💾 Saved to `{output_file.name}`")

        except Exception as exc:
            st.error(f"Chunking failed: {exc}")
            import traceback
            with st.expander("Stack trace"):
                st.code(traceback.format_exc())
