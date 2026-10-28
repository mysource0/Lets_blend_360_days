"""Shared configuration and utilities for the AI Engineering Hub."""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# ── Paths ──────────────────────────────────────────────────────────────
HUB_DIR = Path(__file__).resolve().parent
AI_ENGINEERING_DIR = HUB_DIR.parent
PROJECT_ROOT = AI_ENGINEERING_DIR.parent

# Load .env from project root (where the user keeps OLLAMA_MODEL, etc.)
for env_path in [PROJECT_ROOT / ".env", AI_ENGINEERING_DIR / ".env"]:
    if env_path.exists():
        load_dotenv(env_path, override=False)

# ── Defaults ───────────────────────────────────────────────────────────
# Set HUB_SHOW_TRACEBACKS=1 to show stack traces in the UI (useful when debugging).
SHOW_TRACEBACKS = os.getenv("HUB_SHOW_TRACEBACKS", "0").strip() == "1"
DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b").strip().strip('"')
DEFAULT_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434").strip().strip('"')

# ── Day directory map ──────────────────────────────────────────────────
DAY_DIRS = {
    1:  AI_ENGINEERING_DIR / "01_simple_genAI",
    2:  AI_ENGINEERING_DIR / "02_with_context_level",
    3:  AI_ENGINEERING_DIR / "03_structured_output",
    4:  AI_ENGINEERING_DIR / "04_enhanced_dev_codex",
    5:  AI_ENGINEERING_DIR / "05_document_chunking",
    6:  AI_ENGINEERING_DIR / "06_embedding_and_retrieval",
    7:  AI_ENGINEERING_DIR / "07_rag",
    8:  AI_ENGINEERING_DIR / "08_rag_evaluation",
    9:  AI_ENGINEERING_DIR / "09_fine_tuning",
    10: AI_ENGINEERING_DIR / "10_tool_calling",
    11: AI_ENGINEERING_DIR / "11_agents",
}


def add_day_to_path(day_num: int):
    """Insert a day's directory at the front of sys.path for imports,
    and clear any cached 'src' modules from sys.modules to prevent cross-day collisions."""
    day_dir = str(DAY_DIRS[day_num])
    if day_dir in sys.path:
        sys.path.remove(day_dir)
    sys.path.insert(0, day_dir)

    # Purge any cached 'src' or 'src.*' modules from other days
    for mod_name in list(sys.modules.keys()):
        if mod_name == "src" or mod_name.startswith("src."):
            del sys.modules[mod_name]


def get_ollama_client(host: str | None = None):
    """Create and return an Ollama client."""
    import ollama
    return ollama.Client(host=host or DEFAULT_HOST, timeout=120.0)


def get_available_models(host: str | None = None) -> list[str]:
    """Return a list of model names available on the Ollama server."""
    try:
        client = get_ollama_client(host)
        response = client.list()
        if hasattr(response, "models"):
            return [m.model for m in response.models]
        return []
    except Exception:
        return []


def check_ollama_connection(host: str | None = None) -> bool:
    """Quick connectivity check — True if Ollama is reachable."""
    try:
        client = get_ollama_client(host)
        client.list()
        return True
    except Exception:
        return False
