"""
Analyzer — Step 1 of the pipeline.
Takes a natural-language prompt and produces a structured GameAnalysis.
"""

from __future__ import annotations

import time

from src import logger
from src.llm import client, prompts
from src.models import GameAnalysis
from src import config

log = logger.get("pipeline.analyzer")


def analyze(user_prompt: str) -> GameAnalysis:
    """Analyse a user's game description and return a structured analysis."""
    log.info("Analyzing game description (%d chars)…", len(user_prompt))
    t0 = time.time()

    system, user = prompts.analyze(user_prompt)
    data = client.chat_json(system, user, max_tokens=config.LLM_MAX_TOKENS)

    # LLM may wrap response in an array — unwrap if needed
    if isinstance(data, list) and data:
        data = next((item for item in data if isinstance(item, dict)), data[0])
    if not isinstance(data, dict):
        raise ValueError(f"Expected dict from LLM, got {type(data).__name__}")

    analysis = GameAnalysis(**data)
    elapsed = int((time.time() - t0) * 1000)
    log.info("Analysis complete: title=%s engine=%s genre=%s (%d ms)",
             analysis.title, analysis.engine.value, analysis.genre, elapsed)
    return analysis
