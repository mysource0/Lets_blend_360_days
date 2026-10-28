"""Behavior checks for the Day 11 demo executor without a live model."""

from datetime import date
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import SimpleNamespace


AGENT_PATH = Path(__file__).resolve().parents[1] / "main.py"
spec = spec_from_file_location("day11_agent_under_test", AGENT_PATH)
agent = module_from_spec(spec)
spec.loader.exec_module(agent)


class FakeClient:
    def __init__(self, *steps):
        self.steps = iter(steps)

    def chat(self, **_kwargs):
        return SimpleNamespace(message=SimpleNamespace(content=next(self.steps)))


def action(name, payload):
    import json

    return f"Thought: Next check.\nAction: {name}\nAction Input: {json.dumps(payload)}"


FINAL = "Thought: Done.\nFinal Answer: I submitted the leave request."
TODAY = date(2026, 10, 26)
QUESTION = "My user ID is E103. Request leave for Pongal."


def test_printed_request_requires_verified_balance_and_reports_demo(capsys):
    model = FakeClient(
        action("get_available_leave_balance", {"user_id": "E103"}),
        action("create_leave_request", {"user": "E103", "date": "2027-01-14"}),
        FINAL,
    )
    answer = agent.run_agent(QUESTION, model_client=model, today=TODAY)
    assert "Demo leave request(s) printed for 2027-01-14" in answer
    assert "nothing was submitted" in answer
    assert "Demo leave request printed" in capsys.readouterr().out


def test_model_cannot_claim_success_without_action(capsys):
    answer = agent.run_agent(QUESTION, model_client=FakeClient(FINAL), today=TODAY)
    assert answer.startswith("No leave request was printed")
    assert "Demo leave request printed for E103" not in capsys.readouterr().out


def test_request_without_balance_check_is_rejected(capsys):
    model = FakeClient(action("create_leave_request", {"user": "E103", "date": "2027-01-14"}), FINAL)
    answer = agent.run_agent(QUESTION, model_client=model, today=TODAY)
    assert "Check this employee's leave balance" in answer
    assert "Demo leave request printed for E103" not in capsys.readouterr().out


def test_insufficient_balance_rejects_all_requested_days(capsys):
    question = "My user ID is E102. Request leave for Pongal."
    model = FakeClient(
        action("get_available_leave_balance", {"user_id": "E102"}),
        action("create_leave_request", {"user": "E102", "date": "2027-01-14"}),
        FINAL,
    )
    answer = agent.run_agent(question, model_client=model, today=TODAY)
    assert "Insufficient leave balance" in answer
    assert "Demo leave request printed for E102" not in capsys.readouterr().out


def test_unregistered_tool_never_executes(capsys):
    model = FakeClient(action("run_shell", {"command": "echo hello"}), FINAL)
    answer = agent.run_agent(QUESTION, model_client=model, today=TODAY)
    assert answer.startswith("No leave request was printed")
    assert "unknown or missing tool" in capsys.readouterr().out


def test_balance_tool_rejects_guessed_employee_id(capsys):
    model = FakeClient(
        action("get_available_leave_balance", {"user_id": "E101"}),
        "Thought: Done.\nFinal Answer: I checked the balance.",
    )
    agent.run_agent("What is the date of Pongal?", model_client=model, today=TODAY)
    assert "Use only an employee ID stated in the request" in capsys.readouterr().out
