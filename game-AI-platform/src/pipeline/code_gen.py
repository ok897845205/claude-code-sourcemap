"""
Code Generator — Step 3 of the pipeline.
Generates JavaScript source files by calling the LLM for each file in the plan.
Supports parallel generation controlled by LLM_PARALLEL_FILES.
"""

from __future__ import annotations

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Callable

from src import logger, config
from src.llm import client, prompts
from src.models import (
    EngineType, GameAnalysis, GamePlan, GeneratedFile,
)

log = logger.get("pipeline.code_gen")


def generate_file(
    engine: EngineType,
    file_path: str,
    purpose: str,
    analysis: GameAnalysis,
    plan: GamePlan,
) -> GeneratedFile:
    """Generate a single source file."""
    log.info("  Generating %s …", file_path)
    t0 = time.time()

    # Choose prompt template based on file type
    if file_path == "sprites/GameSprites.js":
        system, user = prompts.sprite_gen(analysis)
    elif file_path == "audio/sfx.js":
        system, user = prompts.audio_gen(analysis)
    else:
        system, user = prompts.codegen(engine, file_path, purpose, analysis, plan)

    code = client.chat(system, user, max_tokens=config.LLM_CODE_MAX_TOKENS)
    code = _strip_fences(code)

    # Post-process: ensure GameSprites.js has a default export
    if file_path == "sprites/GameSprites.js":
        code = _ensure_default_export(code)

    # Post-process: ensure Constants.js uses named exports
    if file_path == "core/Constants.js":
        code = _ensure_named_exports_constants(code)

    elapsed = int((time.time() - t0) * 1000)
    log.info("  ✓ %s  (%d chars, %d ms)", file_path, len(code), elapsed)
    return GeneratedFile(path=file_path, content=code)


def generate_all(
    analysis: GameAnalysis,
    plan: GamePlan,
    on_progress: Callable[[str, int, int], None] | None = None,
) -> list[GeneratedFile]:
    """
    Generate all files in the plan.
    Uses ThreadPoolExecutor for parallel generation.
    """
    files_to_gen = plan.files
    total = len(files_to_gen)
    log.info("Generating %d files (parallel=%d)…", total, config.LLM_PARALLEL_FILES)
    t0 = time.time()

    results: list[GeneratedFile] = []
    done_count = 0

    def _gen(fp):
        nonlocal done_count
        result = generate_file(analysis.engine, fp.path, fp.purpose, analysis, plan)
        done_count += 1
        if on_progress:
            on_progress(fp.path, done_count, total)
        return result

    if config.LLM_PARALLEL_FILES <= 1:
        # Serial
        for fp in files_to_gen:
            results.append(_gen(fp))
    else:
        # Parallel
        with ThreadPoolExecutor(max_workers=config.LLM_PARALLEL_FILES) as pool:
            futures = [pool.submit(_gen, fp) for fp in files_to_gen]
            for f in futures:
                results.append(f.result())

    elapsed = int((time.time() - t0) * 1000)
    log.info("All %d files generated (%d ms total)", total, elapsed)
    return results


def _strip_fences(text: str) -> str:
    """Remove markdown code fences if the LLM wrapped the output."""
    text = text.strip()
    # Strip opening fence (```js / ```javascript / ```)
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]  # drop ```{lang} line
        text = "\n".join(lines).strip()
    # Strip trailing fence
    if text.endswith("```"):
        text = text[:-3].rstrip()
    return text


def _ensure_default_export(code: str) -> str:
    """Ensure GameSprites.js has a default export aggregating all named exports."""
    import re
    if "export default" in code:
        return code
    # Find all named exports: export const FOO = ...
    names = re.findall(r"export\s+const\s+(\w+)\s*=", code)
    if not names:
        return code
    exports_obj = ", ".join(names)
    code = code.rstrip() + f"\n\nexport default {{ {exports_obj} }};\n"
    log.info("  Added default export to GameSprites.js with %d entries", len(names))
    return code


def _ensure_named_exports_constants(code: str) -> str:
    """Convert Constants.js from default export style to named exports if needed.

    The template's GameConfig.js expects: import { CANVAS_WIDTH } from './Constants.js'
    If the LLM generates: const Constants = { ... }; export default Constants;
    we convert it to: export const CANVAS_WIDTH = ...; export const ... = ...;
    """
    import re

    # If already using named exports, nothing to do
    if re.search(r"export\s+const\s+\w+\s*=", code):
        # Ensure CANVAS_WIDTH and CANVAS_HEIGHT are present
        if "CANVAS_WIDTH" not in code:
            code = code.rstrip() + "\nexport const CANVAS_WIDTH = 800;\n"
        if "CANVAS_HEIGHT" not in code:
            code = code.rstrip() + "\nexport const CANVAS_HEIGHT = 600;\n"
        if "PHYSICS_GRAVITY" not in code:
            code = code.rstrip() + "\nexport const PHYSICS_GRAVITY = 0;\n"
        return code

    # Try to convert: const Constants = { KEY: val, ... }; export default Constants;
    obj_match = re.search(
        r"(?:const|let|var)\s+\w+\s*=\s*\{([^}]+)\}",
        code, re.DOTALL,
    )
    if obj_match:
        body = obj_match.group(1)
        pairs = re.findall(r"(\w+)\s*:\s*([^,\n]+)", body)
        if pairs:
            lines = [
                "/**\n * Constants — all magic numbers, colours, speeds.\n */",
            ]
            for key, val in pairs:
                lines.append(f"export const {key} = {val.strip()};")
            # Ensure required constants
            exported_keys = {k for k, _ in pairs}
            if "CANVAS_WIDTH" not in exported_keys:
                lines.append("export const CANVAS_WIDTH = 800;")
            if "CANVAS_HEIGHT" not in exported_keys:
                lines.append("export const CANVAS_HEIGHT = 600;")
            if "PHYSICS_GRAVITY" not in exported_keys:
                lines.append("export const PHYSICS_GRAVITY = 0;")
            new_code = "\n".join(lines) + "\n"
            log.info("  Converted Constants.js from default export to %d named exports", len(pairs))
            return new_code

    # Fallback: prepend required exports if missing
    if "CANVAS_WIDTH" not in code:
        code = "export const CANVAS_WIDTH = 800;\nexport const CANVAS_HEIGHT = 600;\nexport const PHYSICS_GRAVITY = 0;\n\n" + code
    return code
