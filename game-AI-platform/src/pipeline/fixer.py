"""
Fixer — Step 6 of the pipeline.
When build or runtime tests fail, uses the LLM to fix the broken files.
Supports up to N retry rounds.
"""

from __future__ import annotations

import re
import time
from pathlib import Path

from src import logger, config
from src.llm import client, prompts
from src.models import GameAnalysis, GeneratedFile
from src.pipeline._text import strip_fences

log = logger.get("pipeline.fixer")

MAX_FIX_ROUNDS = 3


def fix_files(
    project_dir: Path,
    errors: list[str],
    analysis: GameAnalysis,
) -> list[GeneratedFile]:
    """
    Attempt to fix files based on error messages.
    Returns a list of corrected GeneratedFile objects.
    """
    log.info("Attempting to fix %d errors …", len(errors))
    t0 = time.time()

    # Identify which files are referenced in error messages
    src_dir = project_dir / "src"
    files_to_fix = _identify_files(src_dir, errors)

    # Collect all .js files in src/ for context
    all_project_files = sorted(
        str(p.relative_to(src_dir)).replace("\\", "/")
        for p in src_dir.rglob("*.js")
    )

    fixed: list[GeneratedFile] = []
    for rel_path in files_to_fix:
        file_path = src_dir / rel_path
        if not file_path.exists():
            log.warning("  Cannot fix %s — file not found", rel_path)
            continue

        current_code = file_path.read_text(encoding="utf-8")
        relevant_errors = "\n".join(e for e in errors if rel_path in e or _is_general_error(e))

        log.info("  Fixing %s …", rel_path)
        system, user = prompts.fix(rel_path, current_code, relevant_errors,
                                   project_files=all_project_files)
        new_code = client.chat(system, user, max_tokens=config.LLM_CODE_MAX_TOKENS)
        new_code = strip_fences(new_code)

        # Write back
        file_path.write_text(new_code, encoding="utf-8")
        fixed.append(GeneratedFile(path=rel_path, content=new_code))
        log.info("  ✓ %s fixed (%d chars)", rel_path, len(new_code))

    elapsed = int((time.time() - t0) * 1000)
    log.info("Fix round complete: %d files updated (%d ms)", len(fixed), elapsed)
    return fixed


def _identify_files(src_dir: Path, errors: list[str]) -> list[str]:
    """Extract file paths mentioned in error messages."""
    candidates: set[str] = set()
    for err in errors:
        # Match patterns like "entities/Player.js:42" or "src/scenes/GameScene.js"
        # Also handle Windows backslash paths
        normalized = err.replace("\\", "/")
        matches = re.findall(r"((?:[\w/]+/)?[\w]+\.js)", normalized)
        for m in matches:
            # Normalize: strip leading "src/"
            p = m.removeprefix("src/")
            if (src_dir / p).exists():
                candidates.add(p)

        # Handle "Could not resolve ... from ..." pattern
        resolve_match = re.search(
            r'Could not resolve ["\']([^"\']+)["\'] from ["\']([^"\']+)["\']',
            normalized,
        )
        if resolve_match:
            from_file = resolve_match.group(2).removeprefix("src/")
            if (src_dir / from_file).exists():
                candidates.add(from_file)

    # If no specific files found, target the main game files
    if not candidates:
        for fallback in ["scenes/BootScene.js", "scenes/GameScene.js",
                         "orchestrator/GameOrchestrator.js",
                         "core/Constants.js", "entities/Player.js"]:
            if (src_dir / fallback).exists():
                candidates.add(fallback)
                break

    return sorted(candidates)


def _is_general_error(err: str) -> bool:
    """Check if an error is general (not file-specific)."""
    return ".js" not in err
