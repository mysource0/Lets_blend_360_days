"""Day 10 — Tool Calling Agent: controlled actions with human confirmation."""

import hashlib
import json
import time
import streamlit as st
from pathlib import Path

from config import DAY_DIRS, SHOW_TRACEBACKS, add_day_to_path, get_ollama_client


def render():
    st.caption("Enterprise Knowledge & Action Assistant with controlled tool execution")

    model = st.session_state.get("ollama_model", "qwen2.5:3b")
    host = st.session_state.get("ollama_host", "http://localhost:11434")

    # ── Controls ───────────────────────────────────────────────────────
    col_opts, col_info = st.columns([1, 1])

    with col_opts:
        st.markdown("### ⚙️ Agent Settings")
        allow_write = st.checkbox(
            "🔓 Allow write actions (create service requests)",
            value=False,
            key="day10_write",
        )
        use_mock = st.checkbox(
            "🎭 Use mock backend (no real Ollama needed)",
            value=True,
            key="day10_mock",
        )

    with col_info:
        st.markdown("### 🛠️ Available Tools")
        st.markdown("""
| Tool | Type | Description |
|---|---|---|
| `lookup_internal_knowledge` | 🔍 Read | Query Day 07 RAG pipeline |
| `create_service_request` | ✏️ Write | Create a service request (needs confirmation) |
        """)

    st.divider()

    # ── Initialize chat ────────────────────────────────────────────────
    if "day10_messages" not in st.session_state:
        st.session_state.day10_messages = []
    if "day10_pending_confirm" not in st.session_state:
        st.session_state.day10_pending_confirm = None

    # Display chat history
    for msg in st.session_state.day10_messages:
        role = msg.get("role", "assistant")
        with st.chat_message(role):
            st.markdown(msg["content"])
            if msg.get("tool_activity"):
                with st.expander("🔧 Tool Activity"):
                    st.json(msg["tool_activity"])

    # ── Chat input ─────────────────────────────────────────────────────
    if prompt := st.chat_input("Ask about policies or request an action…", key="day10_input"):
        st.session_state.day10_messages.append({"role": "user", "content": prompt})
        st.session_state.day10_pending_confirm = None
        with st.chat_message("user"):
            st.markdown(prompt)
        _respond(prompt, model, host, allow_write, use_mock)

    # ── Approval gate: a write runs only after the user approves this exact proposal ──
    pending = st.session_state.day10_pending_confirm
    if pending:
        with st.container(border=True):
            st.warning("⏸️ A write action is waiting for your approval. Nothing has been created yet.")
            st.code(pending["summary"], language="text")
            col_yes, col_no = st.columns(2)
            if col_yes.button("✅ Approve and create", type="primary", key="day10_approve", width="stretch"):
                st.session_state.day10_pending_confirm = None
                _respond(pending["message"], model, host, allow_write, use_mock, approved_digest=pending["digest"])
                st.rerun()
            if col_no.button("✖ Reject", key="day10_reject", width="stretch"):
                st.session_state.day10_pending_confirm = None
                st.session_state.day10_messages.append({
                    "role": "assistant",
                    "content": "Cancelled. No service request was created.",
                })
                st.rerun()

    # ── Clear button ───────────────────────────────────────────────────
    if st.button("🗑️ Clear Agent Chat", key="day10_clear"):
        st.session_state.day10_messages = []
        st.rerun()


def _respond(prompt, model, host, allow_write, use_mock, approved_digest=None):
    """Run one agent turn, render its reply, and store it in the chat history."""
    with st.chat_message("assistant"):
        try:
            if use_mock:
                result = _mock_handle(prompt, allow_write, approved_digest)
            else:
                result = _real_handle(prompt, model, host, allow_write, approved_digest)

            response_text = result.get("final_response", "No response")
            ok = result.get("ok", False)
            activity = result.get("tool_activity", [])
            if st.session_state.day10_pending_confirm:
                # The write was held back; the approval panel below decides what happens next.
                response_text = "⏸️ This action needs your approval. Review the proposal below."
                ok = True
                activity = []

            if ok:
                st.markdown(response_text)
            else:
                st.error(response_text)
                error = result.get("error", {})
                if error:
                    st.caption(f"Error code: `{error.get('code', '?')}`")

            if activity:
                with st.expander("🔧 Tool Activity", expanded=True):
                    for act in activity:
                        tool_name = act.get("tool_name", "?")
                        tool_result = act.get("result", {})
                        if tool_name == "lookup_internal_knowledge":
                            st.markdown(f"**🔍 {tool_name}** (Round {act.get('round', '?')})")
                            results_list = tool_result.get("results", [])
                            if results_list:
                                for r in results_list:
                                    st.markdown(f"- Score {_format_score(r.get('similarity'))}: {r.get('text', '')[:200]}…")
                            elif tool_result.get("no_results"):
                                st.caption("No results found")
                        elif tool_name == "create_service_request":
                            st.markdown(f"**✏️ {tool_name}** (Round {act.get('round', '?')})")
                            status = tool_result.get("status", "?")
                            if status == "created":
                                st.success(f"✅ Created: {tool_result.get('title', '')}")
                            elif status == "cancelled":
                                st.warning("⏹️ Cancelled by user")
                            elif status == "denied":
                                st.error(f"🚫 Denied: {tool_result.get('reason', '')}")
                            else:
                                st.json(tool_result)
                        else:
                            st.json(act)

            st.session_state.day10_messages.append({
                "role": "assistant",
                "content": response_text,
                "tool_activity": activity,
            })

        except Exception as exc:
            st.error(f"Agent error: {exc}")
            if SHOW_TRACEBACKS:
                import traceback
                with st.expander("Stack trace"):
                    st.code(traceback.format_exc())


def _format_score(value) -> str:
    """Format a similarity score, tolerating missing or non-numeric values."""
    try:
        return f"{float(value):.3f}"
    except (TypeError, ValueError):
        return "n/a"


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _request_approval(message: str, summary: str) -> None:
    """Hold a write proposal until the user approves this exact summary."""
    st.session_state.day10_pending_confirm = {
        "message": message,
        "summary": summary,
        "digest": _digest(summary),
    }


MOCK_WRITE_SUMMARY = (
    "Proposed service request (mock demo):\n"
    "  Title: Demo service request\n"
    "  Priority: normal\n"
    "  Description: Created from the mock backend demo."
)


def _mock_handle(message: str, allow_write: bool, approved_digest: str | None = None) -> dict:
    """Simulated tool calling for demo without Ollama."""
    msg_lower = message.lower()

    # ── Write actions ──────────────────────────────────────────────────
    if any(kw in msg_lower for kw in ["create", "request", "ticket", "service", "submit", "file a"]):
        if not allow_write:
            return {
                "ok": True,
                "correlation_id": "mock-demo",
                "final_response": "I attempted to create a service request, but the write permission is not enabled. Enable '🔓 Allow write actions' above.",
                "tool_activity": [{
                    "round": 1,
                    "call_id": "mock-write",
                    "tool_name": "create_service_request",
                    "result": {"status": "denied", "reason": "Actor does not have create permission"},
                }],
            }
        if approved_digest != _digest(MOCK_WRITE_SUMMARY):
            _request_approval(message, MOCK_WRITE_SUMMARY)
            return {"ok": True, "correlation_id": "mock-demo", "final_response": "Waiting for approval.", "tool_activity": []}
        return {
            "ok": True,
            "correlation_id": "mock-demo",
            "final_response": "Service request created (mock demo). Nothing was sent to a real system.",
            "tool_activity": [{
                "round": 1,
                "call_id": "mock-write",
                "tool_name": "create_service_request",
                "result": {"status": "created", "title": "Demo service request", "request_id": "mock-001"},
            }],
        }

    # ── Knowledge lookups (topic-based mock responses) ─────────────────
    # Each entry: (keywords, answer_text, evidence_text, heading, score)
    MOCK_KNOWLEDGE = [
        (
            ["leave", "vacation", "annual leave", "day off", "pto", "time off", "sick leave", "holiday"],
            (
                "Based on the internal knowledge lookup:\n\n"
                "- Employees are entitled to **20 days** of paid annual leave per calendar year.\n"
                "- **10 days** of sick leave are provided per year (non-cumulative).\n"
                "- Leave requests of **5 or more consecutive days** require manager approval at least 2 weeks in advance.\n"
                "- Unused annual leave may be carried over up to a maximum of **5 days** into the next year."
            ),
            "Employees receive 20 days of paid annual leave per calendar year. Sick leave is 10 days per year. Leave requests of 5 or more consecutive days require manager approval at least 2 weeks in advance. Up to 5 days of unused annual leave may carry over.",
            "Leave Policy",
            0.812,
        ),
        (
            ["expense", "receipt", "claim", "reimburse", "reimbursement"],
            (
                "Based on the internal knowledge lookup, a readable receipt is required "
                "for each expense of **500 currency units or more**. Expense claims must be "
                "submitted within 30 days of the transaction."
            ),
            "A readable receipt is required for each expense of 500 currency units or more. Expense claims must be submitted within 30 days.",
            "Expense Reimbursement",
            0.847,
        ),
        (
            ["travel", "trip", "business travel", "flight", "hotel", "per diem", "meal"],
            (
                "Based on the internal knowledge lookup:\n\n"
                "- Travel meals are reimbursed up to **50 currency units per day**.\n"
                "- International trips require **business-unit head approval** before booking.\n"
                "- All travel must be booked through the approved corporate travel portal."
            ),
            "Travel meals reimbursed up to 50 currency units per day. International trips require business-unit head approval. Use the corporate travel portal.",
            "Business Travel Policy",
            0.793,
        ),
        (
            ["salary", "pay", "compensation", "bonus", "raise", "increment"],
            (
                "Based on the internal knowledge lookup:\n\n"
                "- Salary reviews are conducted **annually** in Q1.\n"
                "- Performance bonuses are paid in **March** based on the previous year's appraisal.\n"
                "- Salary-related queries should be directed to the **HR Compensation team**."
            ),
            "Annual salary reviews in Q1. Performance bonuses paid in March. Contact HR Compensation for individual queries.",
            "Compensation & Benefits",
            0.776,
        ),
        (
            ["policy", "handbook", "guideline", "rule", "regulation", "compliance"],
            (
                "Based on the internal knowledge lookup:\n\n"
                "The employee handbook covers policies on:\n"
                "- **Leave** (annual, sick, parental)\n"
                "- **Expense reimbursement** and travel\n"
                "- **Code of conduct** and workplace behaviour\n"
                "- **Data security** and IT usage\n\n"
                "Ask about a specific policy for detailed information."
            ),
            "Employee handbook includes leave policies, expense reimbursement, travel, code of conduct, data security, and IT usage guidelines.",
            "Employee Handbook Overview",
            0.721,
        ),
    ]

    # Match against knowledge topics
    for keywords, answer, evidence, heading, score in MOCK_KNOWLEDGE:
        if any(kw in msg_lower for kw in keywords):
            return {
                "ok": True,
                "correlation_id": "mock-demo",
                "final_response": answer,
                "tool_activity": [{
                    "round": 1,
                    "call_id": "mock-lookup",
                    "tool_name": "lookup_internal_knowledge",
                    "result": {
                        "ok": True,
                        "backend": "mock",
                        "no_results": False,
                        "results": [{"similarity": score, "text": evidence, "heading_path": heading}],
                    },
                }],
            }

    # ── Fallback: attempt a generic lookup ─────────────────────────────
    return {
        "ok": True,
        "correlation_id": "mock-demo",
        "final_response": (
            f"I searched the internal knowledge base for **\"{message.strip()}\"** "
            "but did not find a specific match in the mock data.\n\n"
            "In **real mode** (uncheck 'Use mock backend'), the agent would query the "
            "Day 07 RAG pipeline against your actual employee policy documents.\n\n"
            "**Topics available in mock mode:**\n"
            "- 🏖️ Leave / vacation / sick leave\n"
            "- 💰 Expense claims / receipts\n"
            "- ✈️ Business travel / meals\n"
            "- 💵 Salary / compensation / bonuses\n"
            "- 📋 General policies / handbook\n"
            "- 🎫 Create service requests (enable write actions)"
        ),
        "tool_activity": [{
            "round": 1,
            "call_id": "mock-lookup",
            "tool_name": "lookup_internal_knowledge",
            "result": {
                "ok": True,
                "backend": "mock",
                "no_results": True,
                "results": [],
            },
        }],
    }


def _real_handle(message: str, model: str, host: str, allow_write: bool, approved_digest: str | None = None) -> dict:
    """Run the real Day 10 ControlledAssistant."""
    import os
    os.environ["OLLAMA_HOST"] = host
    os.environ["OLLAMA_MODEL"] = model
    os.environ["KNOWLEDGE_BACKEND"] = "mock"  # Use mock knowledge to avoid Day 06 dependency

    add_day_to_path(10)

    import importlib
    assistant_mod = importlib.import_module("src.assistant")
    config_mod = importlib.import_module("src.config")

    ControlledAssistant = assistant_mod.ControlledAssistant
    AppConfig = config_mod.AppConfig
    ActorContext = config_mod.ActorContext

    config = AppConfig.from_environment()
    actor = ActorContext("hub-user", allow_write)

    def streamlit_confirm(summary: str) -> bool:
        """Approve only the exact proposal the user already accepted; otherwise hold it for review."""
        if approved_digest and _digest(summary) == approved_digest:
            return True
        _request_approval(message, summary)
        return False

    assistant = ControlledAssistant(config)
    return assistant.handle(message, actor=actor, confirmation_handler=streamlit_confirm)
