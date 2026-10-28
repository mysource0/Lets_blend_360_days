# Day 11 — Agents and the ReAct loop

Day 10 introduced controlled, single tool requests. Day 11 shows an agent choosing a sequence of steps: **Thought → Action → Observation → Final Answer**. The local Ollama model chooses which tool to ask for next; Python parses and executes only three named demo tools.

The example is a leave assistant with hard-coded employee balances and festival dates. It can read a balance, look up a festival date, and **print** a leave request. It does not change an HR system or save a request. These records are teaching data and must not be used as current HR policy or holiday dates.

## Agent loop

```text
User request → Ollama proposes one Action → Python validates it
             → Python runs the named demo tool → Observation returns to Ollama
             → repeat, up to 10 steps → Final Answer
```

The executor checks the employee ID, verified balance, requested dates, duplicate requests, and whether a date is in the past before printing a request. It reports the actual printed actions instead of trusting a model claim of success. A missing or malformed action does not dispatch a tool.

This is a teaching example, not a production leave workflow. It has no authentication, persistent balance updates, manager approval, or human confirmation. Day 10's `ControlledAssistant` remains the example for permission checks, confirmation, and audit logging on actions.

## Run

See [SETUP.md](SETUP.md) for Windows commands. From this directory:

```powershell
python main.py "My user ID is E103. Request leave for Pongal."
```

The default model is `qwen3:4b`. Set `OLLAMA_MODEL` and `OLLAMA_HOST` to use another local model or server. The top-level [requirements.txt](../requirements.txt) already contains `ollama` and `pytest`; this day has no extra package requirements.

You can also select **Day 11** in the Streamlit Hub. Its scripted demonstration runs without Ollama and is labelled as a mock. The live option uses the selected Ollama model.

The [sample trace](sample_thought_chain.txt) illustrates one possible path; model steps can vary. The fixed festival dates will eventually be in the past, so use an explicit future `YYYY-MM-DD` date when running the live example later.
