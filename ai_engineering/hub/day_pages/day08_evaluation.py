"""Day 08 — RAG Evaluation: run test cases against the Day 07 pipeline."""

import json
import streamlit as st
from pathlib import Path

from config import DAY_DIRS, add_day_to_path


def _load_test_cases() -> list[dict]:
    """Load the Day 08 test cases JSON file."""
    cases_file = DAY_DIRS[8] / "test_inputs" / "day08_common_cases.json"
    if not cases_file.exists():
        return []
    return json.loads(cases_file.read_text(encoding="utf-8"))


def render():
    st.caption("Evaluate the RAG pipeline with versioned test cases")

    # ── Load test cases ────────────────────────────────────────────────
    cases = _load_test_cases()
    if not cases:
        st.error(f"No test cases found at `{DAY_DIRS[8] / 'test_inputs'}`")
        return

    # ── Display test cases ─────────────────────────────────────────────
    st.subheader(f"📋 {len(cases)} Test Cases")

    # Summary table
    table_data = []
    for case in cases:
        status_emoji = {"MISSING_FROM_CORPUS": "🔴", "SUPPORTED": "🟢"}.get(
            case.get("corpus_precondition", ""), "⚪"
        )
        table_data.append({
            "Case ID": case.get("case_id", "?"),
            "Type": case.get("case_type", "?"),
            "Corpus": f"{status_emoji} {case.get('corpus_precondition', '?')}",
            "Question": case.get("question", "")[:80],
        })

    st.dataframe(table_data, width="stretch", hide_index=True)

    st.divider()

    # ── Case details ───────────────────────────────────────────────────
    case_ids = [c.get("case_id", f"case_{i}") for i, c in enumerate(cases)]
    selected_case_id = st.selectbox("🔍 Inspect a case", case_ids, key="day08_case")
    selected_case = next(c for c in cases if c.get("case_id") == selected_case_id)

    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("### Question")
        st.info(selected_case.get("question", ""))
        st.markdown("### Expected Behavior")
        st.markdown(selected_case.get("expected_behavior", "N/A"))

    with col2:
        st.markdown("### Corpus Precondition")
        precond = selected_case.get("corpus_precondition", "?")
        if precond == "MISSING_FROM_CORPUS":
            st.error(f"🔴 {precond}")
        else:
            st.success(f"🟢 {precond}")

        st.markdown("### Expected Evidence")
        st.markdown(selected_case.get("expected_evidence_description", "N/A"))

        expected_ids = selected_case.get("expected_relevant_chunk_ids", [])
        if expected_ids:
            st.markdown("**Expected chunk IDs:**")
            for cid in expected_ids:
                st.code(cid)

        expected_cites = selected_case.get("expected_citations", [])
        if expected_cites:
            st.markdown("**Expected citations:**")
            for c in expected_cites:
                st.code(c)

    st.markdown("### Evaluation Notes")
    st.caption(selected_case.get("evaluation_notes", "N/A"))

    st.divider()

    # ── Run evaluation ─────────────────────────────────────────────────
    st.subheader("🚀 Run Evaluation")
    st.info(
        "Running the full evaluation requires Ollama + Day 06 index + Day 07 pipeline. "
        "Use the button below to attempt evaluation."
    )

    run_single = st.checkbox("Run only selected case", value=True, key="day08_single")

    if st.button("▶️ Run Evaluation", type="primary", width="stretch", key="day08_run"):
        try:
            add_day_to_path(8)
            add_day_to_path(7)  # Day 08 imports Day 07

            import importlib
            config_mod = importlib.import_module("src.config")
            eval_mod = importlib.import_module("src.evaluator")
            EvaluationConfig = config_mod.EvaluationConfig
            run_evaluation = eval_mod.run_evaluation

            config = EvaluationConfig.from_environment()

            case_filter = selected_case_id if run_single else None

            with st.spinner("Running evaluation…"):
                results, manifest = run_evaluation(config, case_id=case_filter)

            st.success(f"✅ Evaluation complete — {len(results)} case(s)")

            # Show results
            for r in results:
                status = r.get("status", "?")
                status_emoji = {
                    "PASS": "✅", "FAIL": "❌",
                    "BLOCKED_MISSING_SOURCE": "🚫",
                    "SKIPPED_RUNTIME_UNAVAILABLE": "⏭️",
                    "NEEDS_MANUAL_REVIEW": "👀",
                }.get(status, "❓")

                with st.expander(f"{status_emoji} {r.get('case_id', '?')} — {status}"):
                    if r.get("answer"):
                        st.markdown(f"**Answer:** {r['answer']}")
                    if r.get("primary_failure_stage"):
                        st.error(f"Primary failure: {r['primary_failure_stage']}")
                    if r.get("answer_checks"):
                        st.json(r["answer_checks"])

            # Manifest
            with st.expander("📋 Run Manifest"):
                st.json(manifest)

        except Exception as exc:
            st.error(f"Evaluation failed: {exc}")
            import traceback
            with st.expander("Stack trace"):
                st.code(traceback.format_exc())
