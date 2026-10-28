"""Day 09 — Architecture Decisions: interactive scenario explorer and decision cards."""

import json
import streamlit as st
from pathlib import Path

from config import DAY_DIRS


ARCHITECTURE_DESCRIPTIONS = {
    "PROMPT_CONTEXT": "Bounded transformation with supplied context in the prompt",
    "RAG": "Retrieval-Augmented Generation for current/private knowledge",
    "FINE_TUNING": "Persistent specialized behaviour from reviewed examples",
    "COMBINATION": "RAG + fine-tuning for knowledge + behaviour",
    "NO_LLM": "Deterministic code for exact, reproducible business rules",
    "DECISION_DEFERRED": "Essential facts are unknown — discovery is required",
}

ARCHITECTURE_ICONS = {
    "PROMPT_CONTEXT": "💬",
    "RAG": "📚",
    "FINE_TUNING": "🎯",
    "COMBINATION": "🔗",
    "NO_LLM": "⚙️",
    "DECISION_DEFERRED": "⏸️",
}


def _load_scenarios() -> list[dict]:
    path = DAY_DIRS[9] / "data" / "architecture_scenarios.json"
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def _load_decision_cards() -> list[dict]:
    path = DAY_DIRS[9] / "data" / "reference_decision_cards.json"
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def render():
    st.caption("Choose the simplest defensible architecture for a business requirement")

    scenarios = _load_scenarios()
    if not scenarios:
        st.error("No scenario data found.")
        return

    decision_cards = _load_decision_cards()
    cards_by_id = {c.get("scenario_id"): c for c in decision_cards} if decision_cards else {}

    # ── Architecture overview ──────────────────────────────────────────
    with st.expander("🏗️ Architecture Options Reference", expanded=False):
        for arch, desc in ARCHITECTURE_DESCRIPTIONS.items():
            icon = ARCHITECTURE_ICONS.get(arch, "")
            st.markdown(f"**{icon} `{arch}`** — {desc}")

    st.divider()

    # ── Scenario selector ──────────────────────────────────────────────
    st.subheader("📋 Scenarios")

    # Summary table
    table_rows = []
    for s in scenarios:
        ref_arch = s.get("reference_architecture", "?")
        icon = ARCHITECTURE_ICONS.get(ref_arch, "")
        table_rows.append({
            "ID": s.get("scenario_id", "?"),
            "Title": s.get("title", "?"),
            "Reference": f"{icon} {ref_arch}",
            "Rejected": s.get("rejected_alternative", "?"),
        })

    st.dataframe(table_rows, width="stretch", hide_index=True)

    st.divider()

    # ── Scenario detail ────────────────────────────────────────────────
    scenario_ids = [s.get("scenario_id", f"S{i}") for i, s in enumerate(scenarios)]
    selected_id = st.selectbox("🔍 Select a scenario to explore", scenario_ids, key="day09_scenario")
    selected = next(s for s in scenarios if s.get("scenario_id") == selected_id)

    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown(f"### {selected.get('title', 'Untitled')}")
        st.markdown(f"**Business situation:** {selected.get('business_situation', 'N/A')}")
        st.markdown(f"**Primary need:** {selected.get('primary_need', 'N/A')}")

        ref_arch = selected.get("reference_architecture", "?")
        ref_icon = ARCHITECTURE_ICONS.get(ref_arch, "")
        st.success(f"✅ **Recommended:** {ref_icon} `{ref_arch}`")

        rejected = selected.get("rejected_alternative", "?")
        rej_icon = ARCHITECTURE_ICONS.get(rejected, "")
        st.error(f"❌ **Rejected:** {rej_icon} `{rejected}`")

    with col2:
        st.markdown("### Decision Rationale")
        rationale = selected.get("rationale", selected.get("justification", "N/A"))
        st.markdown(rationale)

        assumptions = selected.get("assumptions_that_could_change", selected.get("assumptions", []))
        if assumptions:
            st.markdown("### ⚠️ Assumptions That Could Change")
            if isinstance(assumptions, list):
                for a in assumptions:
                    st.markdown(f"- {a}")
            else:
                st.markdown(assumptions)

        staged = selected.get("staged_approach")
        if staged:
            st.markdown("### 📊 Staged Approach")
            if isinstance(staged, list):
                for i, step in enumerate(staged, 1):
                    st.markdown(f"{i}. {step}")
            else:
                st.markdown(staged)

    # ── Rubric keywords ────────────────────────────────────────────────
    rubric = selected.get("rubric_keywords", {})
    if rubric:
        with st.expander("🏷️ Rubric Keywords"):
            st.json(rubric)

    # ── Reference decision card ────────────────────────────────────────
    card = cards_by_id.get(selected_id)
    if card:
        with st.expander(f"📇 Reference Decision Card — {selected_id}"):
            st.json(card)

    st.divider()

    # ── Interactive decision wizard ────────────────────────────────────
    st.subheader("🧙 Quick Decision Wizard")
    st.caption("Answer these questions to get an architecture recommendation")

    q1 = st.radio(
        "Is the knowledge source small and rarely changing?",
        ["Yes", "No", "Not sure"],
        key="day09_q1", horizontal=True,
    )
    q2 = st.radio(
        "Do you need citations back to source documents?",
        ["Yes", "No", "Not sure"],
        key="day09_q2", horizontal=True,
    )
    q3 = st.radio(
        "Are exact, reproducible results required (no creativity)?",
        ["Yes", "No", "Not sure"],
        key="day09_q3", horizontal=True,
    )
    q4 = st.radio(
        "Do you have reviewed training examples with consistent patterns?",
        ["Yes", "No", "Not sure"],
        key="day09_q4", horizontal=True,
    )

    if st.button("🎯 Get Recommendation", type="primary", key="day09_wizard"):
        if q3 == "Yes":
            rec = "NO_LLM"
        elif q1 == "Yes" and q2 == "No":
            rec = "PROMPT_CONTEXT"
        elif q2 == "Yes":
            if q4 == "Yes":
                rec = "COMBINATION"
            else:
                rec = "RAG"
        elif q4 == "Yes":
            rec = "FINE_TUNING"
        elif "Not sure" in [q1, q2, q3, q4]:
            rec = "DECISION_DEFERRED"
        else:
            rec = "PROMPT_CONTEXT"

        icon = ARCHITECTURE_ICONS.get(rec, "")
        desc = ARCHITECTURE_DESCRIPTIONS.get(rec, "")
        st.success(f"### {icon} Recommendation: `{rec}`\n\n{desc}")
