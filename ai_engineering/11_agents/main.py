"""Simple ReAct agent for leave requests, backed by a local Ollama model.

Setup:
    python -m pip install -r ../requirements.txt
    ollama pull qwen3:4b
    python main.py "My user ID is E103. Request leave for Pongal."

The leave and festival records below are demo data. `create_leave_request` only
prints a message; this is not an HR system integration.
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import date
from json import JSONDecoder, JSONDecodeError
from typing import Any, Callable

MODEL = os.getenv("OLLAMA_MODEL", "qwen3:4b")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
MAX_LOOPS = 10

# Demo leave data for three employees.
LEAVE_DATA: dict[str, dict[str, Any]] = {
    "E101": {"name": "Priya", "leave_balance": 3},
    "E102": {"name": "Rahul", "leave_balance": 0},
    "E103": {"name": "Anita", "leave_balance": 5},
}

# Demo festival dates. These should be verified before use in a real HR system.
FESTIVALS: dict[str, list[dict[str, str]]] = {
    "festivals": [
        {"name": "Diwali", "date": "2026-11-08"},
        {"name": "Dussehra", "date": "2026-10-20"},
        {"name": "Holi", "date": "2027-03-04"},
        {"name": "Onam", "date": "2026-08-26"},
        {"name": "Pongal", "date": "2027-01-14"},
    ]
}


def get_available_leave_balance(user_id: str) -> str:
    """Return the leave balance for a user ID."""
    user = LEAVE_DATA.get(user_id)
    if user is None:
        return f"No user found with ID {user_id}"
    return json.dumps(
        {
            "user_id": user_id,
            "name": user["name"],
            "leave_balance": user["leave_balance"],
        }
    )


def create_leave_request(user: str, date: str) -> str:
    """Demo action: print a leave request instead of writing to an HR system."""
    print(f"Demo leave request printed for {user} on {date}")
    return f"Demo leave request printed for {user} on {date}; nothing was submitted"


def get_festival_date(festival_name: str) -> str:
    """Return a festival date, matched case-insensitively."""
    for festival in FESTIVALS["festivals"]:
        if festival["name"].casefold() == festival_name.strip().casefold():
            return json.dumps(festival)
    return f"No festival named {festival_name} found"


TOOLS = {
    "get_available_leave_balance": get_available_leave_balance,
    "create_leave_request": create_leave_request,
    "get_festival_date": get_festival_date,
}

SYSTEM_PROMPT = """You are a leave assistant. Today's date is {today}.

Available tools and exact Action Input schemas:
- get_available_leave_balance: {"user_id": "E101"}
- get_festival_date: {"festival_name": "Diwali"}
- create_leave_request: {"user": "E101", "date": "YYYY-MM-DD"}

Rules:
- Use only one tool per step and wait for its Observation before continuing.
- Each requested festival needs one leave day.
- Check the employee's leave balance before creating any leave request.
- Never request leave for a date before today.
- Only create leave requests if the balance covers ALL requested future leave days.
- If the balance is insufficient, do not create any requests; explain why.
- Use the exact employee ID provided by the user. Never guess an ID.
- If the user asks only for a festival date, look up that date and finish. Do not check a leave balance.
- Check a leave balance only when the user supplied an employee ID.
- Tool inputs must be valid JSON. Do not use Markdown fences.
- Keep the Thought brief: state the next step, not a long explanation.

IMPORTANT: Every response must use one of the exact formats below. Do not answer in ordinary prose.

For a tool call, output exactly:
Thought: I need to check the employee's leave balance.
Action: get_available_leave_balance
Action Input: {"user_id": "E101"}

When finished, output exactly:
Thought: I have completed the checks.
Final Answer: Your leave request result is ...

Do not use Markdown code fences around Action Input. Use only one Action per response.
"""


def parse_step(text: str) -> tuple[str, str | None, dict[str, Any]]:
    """Parse a ReAct step, allowing minor formatting differences from the model."""
    # Qwen models sometimes include wrappers or leading whitespace. Extract labels
    # as whole lines, rather than requiring the entire response to be perfectly formatted.
    cleaned = text.strip().replace("```json", "```")
    thought_match = re.search(
        r"(?is)(?:^|\n)\s*Thought\s*:\s*(.*?)(?=\n\s*(?:Action|Final Answer)\s*:|$)",
        cleaned,
    )
    action_match = re.search(
        r"(?im)^\s*(?:[-*]\s*)?Action\s*:\s*([A-Za-z_][A-Za-z0-9_]*)\b",
        cleaned,
    )

    input_value: dict[str, Any] = {}
    input_match = re.search(r"(?im)^\s*Action Input\s*:\s*", cleaned)
    if input_match:
        raw_input = cleaned[input_match.end():].lstrip()
        if raw_input.startswith("```"):
            raw_input = raw_input[3:].lstrip()
            if raw_input.startswith("json"):
                raw_input = raw_input[4:].lstrip()
        try:
            parsed, _ = JSONDecoder().raw_decode(raw_input)
            if isinstance(parsed, dict):
                input_value = parsed
        except JSONDecodeError:
            input_value = {}

    thought = thought_match.group(1).strip() if thought_match else "(no thought given)"
    action = action_match.group(1) if action_match else None
    return thought, action, input_value


def _requested_future_dates(question: str, today: date) -> list[str]:
    """Infer the dates explicitly requested by festival names or ISO dates.

    This is a safety check, not an intent parser. Unknown/natural-language dates
    are not guessed; the agent must obtain a concrete ISO date before creating.
    """
    found: set[str] = set()
    question_folded = question.casefold()

    for festival in FESTIVALS["festivals"]:
        name = festival["name"]
        if re.search(rf"(?<!\w){re.escape(name.casefold())}(?!\w)", question_folded):
            try:
                festival_date = date.fromisoformat(festival["date"])
            except ValueError:
                continue
            if festival_date >= today:
                found.add(festival_date.isoformat())

    for match in re.finditer(r"\b(\d{4}-\d{2}-\d{2})\b", question):
        try:
            requested_date = date.fromisoformat(match.group(1))
        except ValueError:
            continue
        if requested_date >= today:
            found.add(requested_date.isoformat())

    return sorted(found)


def _is_leave_request(question: str) -> bool:
    has_action = re.search(r"\b(create|submit|apply|request|book)\b", question, re.I)
    has_leave = re.search(r"\b(leave|time off|day off|vacation)\b", question, re.I)
    return bool(has_action and has_leave)


def run_agent(
    question: str,
    *,
    model_client: Any | None = None,
    model: str | None = None,
    today: date | None = None,
    on_event: Callable[[str], None] | None = None,
) -> str:
    """Run the Thought -> Action -> Observation loop until a Final Answer."""
    if not question.strip():
        raise ValueError("Question cannot be empty")
    if model_client is None:
        from ollama import Client

        model_client = Client(host=OLLAMA_HOST)
    today = today or date.today()
    system_message = SYSTEM_PROMPT.replace("{today}", today.isoformat())
    messages: list[dict[str, str]] = [{"role": "user", "content": question}]

    # The executor keeps its own record of balance checks; the model cannot
    # bypass the precondition merely by claiming it already checked the balance.
    verified_balances: dict[str, int] = {}
    created_requests: set[tuple[str, str]] = set()
    is_request = _is_leave_request(question)
    planned_dates = _requested_future_dates(question, today)
    mentioned_ids = set(re.findall(r"\bE\d{3}\b", question, re.I))
    mentioned_ids = {employee_id.upper() for employee_id in mentioned_ids}
    last_observation = ""

    for loop in range(1, MAX_LOOPS + 1):
        print(f"\n===== Loop {loop} =====")
        if on_event:
            on_event(f"Waiting for the model (step {loop}/{MAX_LOOPS})")
        response = model_client.chat(
            model=model or MODEL,
            messages=[{"role": "system", "content": system_message}, *messages],
            # Qwen3 can emit a separate reasoning channel by default. Disable it
            # here because this simple agent expects structured labels in content.
            think=False,
            options={"num_predict": 180, "temperature": 0.0},
        )
        reply = response.message.content.strip()
        messages.append({"role": "assistant", "content": reply})

        thought, tool_name, tool_input = parse_step(reply)
        print(f"Reason:       {thought}")

        final_match = re.search(r"(?is)\bFinal Answer:\s*(.*)$", reply)
        if final_match:
            answer = final_match.group(1).strip()
            if is_request:
                if created_requests:
                    dates = ", ".join(sorted(day for _, day in created_requests))
                    answer = f"Demo leave request(s) printed for {dates}; nothing was submitted to an HR system."
                else:
                    detail = last_observation if last_observation.startswith("Error:") else "Check the dates and leave balance."
                    answer = f"No leave request was printed. {detail}"
            print(f"Final Answer: {answer}")
            if on_event:
                on_event("Finished")
            return answer

        # Never dispatch a missing/invalid tool name. Ask the model to retry in
        # the required format, and show the original response to make debugging easy.
        if tool_name is None:
            print("Could not parse a tool action. Raw model response:")
            print(reply or "<empty response>")
            messages.append({
                "role": "user",
                "content": (
                    "Your previous response was not in the required format. Retry now. "
                    "Return either exactly 'Thought: ...\nAction: TOOL_NAME\nAction Input: {JSON}' "
                    "or 'Thought: ...\nFinal Answer: ...'. Do not use Markdown fences."
                ),
            })
            continue

        print(f"Action:       {tool_name}")
        print(f"Action Input: {tool_input}")

        if tool_name not in TOOLS:
            observation = f"Error: unknown or missing tool. Use one of {list(TOOLS)}."
        else:
            try:
                if not isinstance(tool_input, dict):
                    raise ValueError("Action Input must be a JSON object")

                if tool_name == "get_available_leave_balance":
                    user_id = str(tool_input.get("user_id", "")).upper().strip()
                    if not user_id:
                        raise ValueError("Missing required field 'user_id'")
                    if user_id not in mentioned_ids:
                        raise ValueError("Use only an employee ID stated in the request")
                    observation = get_available_leave_balance(user_id)
                    try:
                        balance_result = json.loads(observation)
                        if isinstance(balance_result, dict) and "leave_balance" in balance_result:
                            verified_balances[user_id] = int(balance_result["leave_balance"])
                    except (JSONDecodeError, TypeError, ValueError):
                        pass

                elif tool_name == "get_festival_date":
                    festival_name = str(tool_input.get("festival_name", "")).strip()
                    if not festival_name:
                        raise ValueError("Missing required field 'festival_name'")
                    observation = get_festival_date(festival_name)

                else:  # create_leave_request: enforce the key rules outside the LLM.
                    user_id = str(tool_input.get("user", "")).upper().strip()
                    requested_date_raw = str(tool_input.get("date", "")).strip()
                    if not user_id or not requested_date_raw:
                        raise ValueError("Action Input needs both 'user' and 'date'")
                    if user_id not in LEAVE_DATA:
                        raise ValueError(f"No user found with ID {user_id}")
                    if len(mentioned_ids) != 1 or user_id not in mentioned_ids:
                        raise ValueError("State exactly one employee ID in the request before creating leave")
                    try:
                        requested_date = date.fromisoformat(requested_date_raw)
                    except ValueError as exc:
                        raise ValueError("'date' must be a valid YYYY-MM-DD date") from exc
                    if requested_date < today:
                        raise ValueError("Cannot create leave for a date before today")
                    if not is_request:
                        raise ValueError("The user's message does not clearly request a leave to be created")
                    if user_id not in verified_balances:
                        raise ValueError("Check this employee's leave balance before creating a request")
                    if not planned_dates:
                        raise ValueError(
                            "Could not verify all requested dates. Use a named festival or an explicit YYYY-MM-DD date"
                        )
                    if requested_date.isoformat() not in planned_dates:
                        raise ValueError("This date was not one of the future leave dates requested by the user")
                    if verified_balances[user_id] < len(planned_dates):
                        raise ValueError(
                            f"Insufficient leave balance: {verified_balances[user_id]} day(s) available, "
                            f"but {len(planned_dates)} future leave day(s) were requested. No request was created."
                        )
                    key = (user_id, requested_date.isoformat())
                    if key in created_requests:
                        raise ValueError("A request for this employee and date has already been created")
                    observation = create_leave_request(user=user_id, date=requested_date.isoformat())
                    created_requests.add(key)

            except Exception as exc:
                observation = f"Error: {exc}"

        print(f"Observation:  {observation}")
        if on_event:
            on_event(f"{tool_name}: {observation}")
        last_observation = observation
        messages.append({"role": "user", "content": f"Observation: {observation}"})

    return f"Stopped after {MAX_LOOPS} loops without a final answer. Review the last Observation and try again."


def main() -> int:
    question = " ".join(sys.argv[1:]).strip()
    if not question:
        question = "My user ID is E103. Request leave for Pongal."

    try:
        run_agent(question)
    except ValueError as exc:
        print(f"Invalid request: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(
            f"Could not reach Ollama model {MODEL!r} at {OLLAMA_HOST}.\n"
            f"Make sure Ollama is running and the model is installed:\n"
            f"  ollama pull {MODEL}\n"
            f"Details: {exc}",
            file=sys.stderr,
        )
        return 1
    print("\n----- Done -----")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
