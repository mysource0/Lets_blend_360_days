# Day 11 setup and running guide

Run these commands in PowerShell from the repository root.

```powershell
Set-Location ai_engineering/11_agents
py -3.11 -m venv .venv
& .\.venv\Scripts\Activate.ps1
python -m pip install -r ../requirements.txt
ollama list
ollama pull qwen3:4b
python main.py "My user ID is E103. Request leave for Pongal."
```

Ollama must be running for the live agent. `ollama pull` downloads the example model only when you run that command. You can select an installed model with `$env:OLLAMA_MODEL = "model-name"` and set `$env:OLLAMA_HOST` if Ollama is on another address.

To use the Hub, run this from `ai_engineering`:

```powershell
streamlit run hub/app.py
```

Select Day 11. The scripted demonstration needs no Ollama. The live mode uses the model and host configured in the Hub sidebar.

Run the local tests from `ai_engineering/11_agents`:

```powershell
python -m pytest tests -q
```

The script prints each step for learning. Its `create_leave_request` tool prints a demo record and does not submit or persist a leave request.
