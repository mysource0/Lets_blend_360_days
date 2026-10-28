"""Day 03 — Structured Output with Pydantic validation and retry loop."""

import json
import time
import streamlit as st
from pydantic import BaseModel, Field, StrictStr, ValidationError
from typing import Literal

from config import get_ollama_client


# ── Output contract (same as original reliability.py) ──────────────────
class AIResponse(BaseModel):
    status: Literal["success", "needs_clarification"]
    answer: StrictStr = Field(min_length=1)

    class Config:
        extra = "forbid"


def _get_schema():
    if hasattr(AIResponse, "model_json_schema"):
        return AIResponse.model_json_schema()
    return AIResponse.schema()


def _validate(raw: str) -> AIResponse:
    parsed = json.loads(raw)
    if hasattr(AIResponse, "model_validate"):
        return AIResponse.model_validate(parsed)
    return AIResponse.parse_obj(parsed)


def _to_dict(result: AIResponse) -> dict:
    if hasattr(result, "model_dump"):
        return result.model_dump()
    return result.dict()


# Same contract instructions as original structured_validation.py
CONTRACT_INSTRUCTIONS = """
    You are an AI assistant helping employees.

    Return exactly one JSON object matching the supplied schema.
    Do not include Markdown code fences or text outside the JSON.

    Use status="success" when you have enough information to answer.
    Use status="needs_clarification" when more information is required.

    The answer field must contain the user-facing answer or a
    concise clarification question.

    Do not invent facts. If supplied context lacks the information
    needed to answer, do not guess. Ask for clarification or explain
    what information is missing.
    """

# Same system instructions as original
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


def render():
    st.caption("JSON schema enforcement with Pydantic validation and automatic retry")

    model = st.session_state.get("ollama_model", "qwen2.5:3b")
    host = st.session_state.get("ollama_host", "http://localhost:11434")

    # ── Controls ───────────────────────────────────────────────────────
    col_q, col_opts = st.columns([2, 1])

    with col_q:
        question = st.text_area(
            "❓ Your Question",
            placeholder="Enter your employee query here…",
            key="day03_question",
        )
        context = st.text_area(
            "📄 Context (optional)",
            placeholder="Paste relevant context here…",
            key="day03_context",
        )

    with col_opts:
        max_attempts = st.slider("🔄 Max retry attempts", 1, 5, 2, key="day03_attempts")
        temperature = st.slider("🌡️ Temperature", 0.0, 1.0, 0.0, 0.05, key="day03_temp")

        with st.expander("📋 Output Schema"):
            st.json(_get_schema())

    # ── Run button ─────────────────────────────────────────────────────
    if st.button("🚀 Generate Structured Response", type="primary", width="stretch", key="day03_run"):
        if not question or not question.strip():
            st.warning("Please enter a question.")
            return

        try:
            client = get_ollama_client(host)
        except Exception as exc:
            st.error(f"Cannot connect to Ollama: {exc}")
            return

        # Build messages
        combined_instructions = CONTRACT_INSTRUCTIONS + "\n\nAdditional instructions:\n" + SYSTEM_INSTRUCTIONS

        messages = [{"role": "system", "content": combined_instructions}]

        if context and context.strip():
            user_msg = (
                f"Context:\n{context}\n\n"
                f"Question:\n{question.strip()}\n\n"
                "Use the supplied context for your answer.\n"
                "If the answer is missing from the context, say you do not know.\n"
                "Follow the JSON output contract."
            )
        else:
            user_msg = question.strip()

        messages.append({"role": "user", "content": user_msg})

        working_messages = list(messages)
        last_error = "No response was produced."
        result = None

        # ── Retry loop ─────────────────────────────────────────────────
        progress = st.progress(0, text="Starting…")
        attempt_container = st.container()

        start = time.time()

        for attempt in range(1, max_attempts + 1):
            progress.progress(
                attempt / max_attempts,
                text=f"Attempt {attempt}/{max_attempts}",
            )

            with attempt_container.expander(
                f"Attempt {attempt}", expanded=(attempt == 1)
            ):
                try:
                    with st.spinner(f"Generating (attempt {attempt})…"):
                        response = client.chat(
                            model=model,
                            messages=working_messages,
                            format=_get_schema(),
                            stream=False,
                            options={
                                "temperature": temperature,
                                "num_ctx": 2048,
                            },
                        )

                    raw = response.message.content or ""
                    st.code(raw, language="json")

                    try:
                        result = _validate(raw)
                        st.success(f"✅ Schema validation passed on attempt {attempt}")
                        break

                    except (json.JSONDecodeError, ValidationError, TypeError, ValueError) as exc:
                        last_error = f"{type(exc).__name__}: {exc}"
                        st.error(f"❌ Validation failed: {last_error}")

                        if attempt < max_attempts:
                            working_messages.extend([
                                {"role": "assistant", "content": raw},
                                {
                                    "role": "user",
                                    "content": (
                                        "Your previous response failed JSON "
                                        "parsing or schema validation. Return "
                                        "one corrected JSON object matching "
                                        "the required schema. Do not add "
                                        "surrounding text."
                                    ),
                                },
                            ])

                except Exception as exc:
                    last_error = f"{type(exc).__name__}: {exc}"
                    st.error(f"❌ Request error: {last_error}")
                    break

        elapsed = time.time() - start
        progress.empty()

        # ── Display result ─────────────────────────────────────────────
        st.divider()

        if result is not None:
            col_json, col_answer = st.columns([1, 1])

            with col_json:
                st.subheader("📋 Validated JSON")
                st.json(_to_dict(result))

            with col_answer:
                st.subheader("💬 Answer")
                if result.status == "success":
                    st.success("Status: **success**")
                    st.markdown(result.answer)
                else:
                    st.info("Status: **needs_clarification**")
                    st.markdown(result.answer)

            st.metric("⏱️ Total time", f"{elapsed:.1f}s")
        else:
            st.error("The AI could not produce a valid response after all attempts.")
            with st.expander("Developer diagnostics"):
                st.code(last_error)
