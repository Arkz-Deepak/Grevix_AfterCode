import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DB_PATH = str(DATA_DIR / "aegisflow.db")
DEFAULT_PORT = 8000
HOST = "0.0.0.0"

# Agent & Resilience settings
DEFAULT_LATENCY_MS = 25
HEARTBEAT_INTERVAL_SEC = 2.0
STORE_AND_FORWARD_MAX_RETRIES = 5
EXPONENTIAL_BACKOFF_BASE = 1.5

# Dual-Mode Agent:
# If GEMINI_API_KEY or OPENAI_API_KEY is present, we can call it;
# otherwise uses the built-in deterministic heuristic agent engine with zero latency/cost.
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
USE_LOCAL_LLM_MOCK = True
