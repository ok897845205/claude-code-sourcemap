"""
Configuration — loads settings from config/.env with sensible defaults.
"""

from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

# ── Locate project root & load .env ─────────────────────────────────────────

ROOT_DIR = Path(__file__).resolve().parent.parent          # game-AI-platform/
CONFIG_DIR = ROOT_DIR / "config"
_env_file = CONFIG_DIR / ".env"
if _env_file.exists():
    load_dotenv(_env_file)

# ── Provider credentials ────────────────────────────────────────────────────

OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL: str | None = os.getenv("OPENAI_BASE_URL")

ANTHROPIC_API_KEY: str | None = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_BASE_URL: str | None = os.getenv("ANTHROPIC_BASE_URL")

MODEL_ID: str = os.getenv("MODEL_ID", "claude-sonnet-4-6")

# Which SDK path to use: OpenAI SDK takes priority when its key is set.
USE_OPENAI_SDK: bool = bool(OPENAI_API_KEY)

# ── LLM parameters ─────────────────────────────────────────────────────────

LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "8192"))
LLM_CODE_MAX_TOKENS: int = int(os.getenv("LLM_CODE_MAX_TOKENS", "8192"))
LLM_PLAN_MAX_TOKENS: int = int(os.getenv("LLM_PLAN_MAX_TOKENS", "4096"))
LLM_FALLBACK_MAX_TOKENS: int = int(os.getenv("LLM_FALLBACK_MAX_TOKENS", "16384"))
LLM_PARALLEL_FILES: int = int(os.getenv("LLM_PARALLEL_FILES", "3"))

_temp = os.getenv("LLM_TEMPERATURE")
LLM_TEMPERATURE: float | None = float(_temp) if _temp is not None else None

# ── Application ─────────────────────────────────────────────────────────────

APP_ENV: str = os.getenv("APP_ENV", "dev")
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FORMAT: str = os.getenv("LOG_FORMAT", "text")
API_PREFIX: str = os.getenv("API_PREFIX", "/api/v1")
DATA_ROOT: Path = ROOT_DIR / os.getenv("DATA_ROOT", "data")

# ── Template & output paths ─────────────────────────────────────────────────

TEMPLATES_DIR: Path = ROOT_DIR / "src" / "templates" / "web_game"
PROJECTS_DIR: Path = DATA_ROOT / "projects"
STATIC_DIR: Path = ROOT_DIR / "src" / "static"

# Ensure data directories exist
PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
