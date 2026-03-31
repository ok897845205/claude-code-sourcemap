"""
Planner — Step 2 of the pipeline.
Takes a GameAnalysis and produces a GamePlan (list of files to generate).
"""

from __future__ import annotations

import time

from src import logger, config
from src.llm import client, prompts
from src.models import GameAnalysis, GamePlan

log = logger.get("pipeline.planner")

# Files that must always be in the plan
_REQUIRED_PHASER = [
    "core/Constants.js",
    "core/GameState.js",
    "sprites/GameSprites.js",
    "audio/sfx.js",
    "entities/Player.js",
    "scenes/GameScene.js",
    "scenes/GameOverScene.js",
]

_REQUIRED_THREE = [
    "core/Constants.js",
    "core/GameState.js",
    "sprites/GameSprites.js",
    "audio/sfx.js",
    "entities/Player.js",
    "orchestrator/GameOrchestrator.js",
    "systems/LevelBuilder.js",
]


def plan(analysis: GameAnalysis) -> GamePlan:
    """Plan which files need to be generated for this game."""
    log.info("Planning file structure for '%s'…", analysis.title)
    t0 = time.time()

    system, user = prompts.plan(analysis)
    data = client.chat_json(system, user, max_tokens=config.LLM_PLAN_MAX_TOKENS)

    game_plan = GamePlan(**data)

    # Ensure required files are present
    required = _REQUIRED_PHASER if analysis.engine.value == "phaser2d" else _REQUIRED_THREE
    existing_paths = {f.path for f in game_plan.files}
    for path in required:
        if path not in existing_paths:
            from src.models import FilePlan
            game_plan.files.append(FilePlan(path=path, purpose=f"Required: {path}"))

    elapsed = int((time.time() - t0) * 1000)
    log.info("Plan ready: %d files to generate (%d ms)", len(game_plan.files), elapsed)
    return game_plan
