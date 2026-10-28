"""Day 11: inspect a bounded ReAct agent loop and its observations."""

from contextlib import redirect_stdout
from datetime import date
from importlib.util import module_from_spec, spec_from_file_location
from io import StringIO
from pathlib import Path
from types import SimpleNamespace

import streamlit as st

from config import DAY_DIRS, get_ollama_client


SAMPLE_QUESTION = "My user ID is E103. Request leave for Pongal."
MAX_RUNS_SHOWN = 20
SAMPLE_STEPS = [
    'Thought: Find the named festival date.\nAction: get_festival_date\nAction Input: {"festival_name": "Pongal"}',
    'Thought: Check the employee balance.\nAction: get_available_leave_balance\nAction Input: {"user_id": "E103"}',
    'Thought: Print the demo request.\nAction: create_leave_request\nAction Input: {"user": "E103", "date": "2027-01-14"}',
    "Thought: The checks are complete.\nFinal Answer: The demo request was printed.",
]


class ScriptedClient:
    """Fixed model responses for a clearly labelled offline walkthrough."""

    def __init__(self):
        self.steps = iter(SAMPLE_STEPS)

    def chat(self, **_kwargs):
        return SimpleNamespace(message=SimpleNamespace(content=next(self.steps)))


def _load_agent():
    path = Path(DAY_DIRS[11]) / "main.py"
    spec = spec_from_file_location("day11_agent", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {path}")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def render():
    st.caption("See how a model proposes one action, receives its observation, and repeats.")
    st.info("Leave balances and festival dates are demo data. A request is printed only; nothing is submitted to an HR system.")
    st.caption("Type a request and press Enter to use the Ollama model selected in the sidebar, or run the fixed offline example.")

    if "day11_runs" not in st.session_state:
        st.session_state.day11_runs = []
    for run in st.session_state.day11_runs:
        with st.chat_message("user"):
            st.markdown(run["question"])
        with st.chat_message("assistant"):
            if run["error"]:
                st.error(run["answer"])
            else:
                st.markdown(run["answer"])
            if run["trace"]:
                with st.expander("Thought, action, and observation trace"):
                    st.code(run["trace"], language="text")
            st.caption(run["mode"])

    demo_clicked = st.button("Run scripted example (no Ollama)", key="day11_demo")
    prompt = st.chat_input("Ask the leave agent…", key="day11_input")
    if not demo_clicked and not prompt:
        return

    scripted = demo_clicked
    question = SAMPLE_QUESTION if scripted else prompt.strip()
    trace = StringIO()
    error = False
    model_name = "scripted walkthrough" if scripted else st.session_state.get("ollama_model", "unknown model")
    status = st.status("Starting the agent…", expanded=True)
    try:
        agent = _load_agent()
        if scripted:
            model_client = ScriptedClient()
            run_date = date(2026, 10, 26)
        else:
            host = st.session_state.get("ollama_host")
            model_client = get_ollama_client(host)
            run_date = date.today()
        with redirect_stdout(trace):
            answer = agent.run_agent(
                question,
                model_client=model_client,
                model=model_name,
                today=run_date,
                on_event=status.write,
            )
        error = answer.startswith("Stopped after ")
        status.update(
            label="Agent stopped before answering" if error else "Agent finished",
            state="error" if error else "complete",
        )
    except Exception as exc:
        error = True
        answer = f"Agent could not finish: {exc}"
        status.update(label="Agent stopped with an error", state="error")

    st.session_state.day11_runs.append({
        "question": question,
        "answer": answer,
        "trace": trace.getvalue(),
        "mode": "Scripted example with fixed date 2026-10-26" if scripted else f"Live Ollama: {model_name}",
        "error": error,
    })
    del st.session_state.day11_runs[:-MAX_RUNS_SHOWN]
    st.rerun()
