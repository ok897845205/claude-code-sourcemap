"""
Assembler — Step 4 of the pipeline.
Copies the engine template into a fresh project directory and overlays
generated files.
"""

from __future__ import annotations

import shutil
import time
from datetime import date
from pathlib import Path

from src import logger, config
from src.models import EngineType, GeneratedFile

log = logger.get("pipeline.assembler")


def make_dir_name(engine: EngineType) -> str:
    """Build a directory name like ``2d_game_20260331`` or ``3d_game_20260331_2``."""
    prefix = "2d_game" if engine == EngineType.PHASER2D else "3d_game"
    today = date.today().strftime("%Y%m%d")
    base = f"{prefix}_{today}"

    # Handle duplicates: append _2, _3, … if the name already exists
    candidate = base
    seq = 1
    while (config.PROJECTS_DIR / candidate).exists():
        seq += 1
        candidate = f"{base}_{seq}"
    return candidate


def assemble(
    project_id: str,
    engine: EngineType,
    generated_files: list[GeneratedFile],
) -> Path:
    """
    Copy the template into data/projects/<project_id>/ and overlay generated files.
    The project_id IS the directory name (e.g. 2d_game_20260331).
    """
    t0 = time.time()
    template_dir = config.TEMPLATES_DIR / engine.value
    project_dir = config.PROJECTS_DIR / project_id

    # Clean previous build (if re-assembling)
    if project_dir.exists():
        shutil.rmtree(project_dir)

    # Copy template
    log.info("Copying %s template → %s", engine.value, project_dir)
    shutil.copytree(template_dir, project_dir)

    # Overlay generated files
    src_dir = project_dir / "src"
    for gf in generated_files:
        dest = src_dir / gf.path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(gf.content, encoding="utf-8")
        log.debug("  wrote %s (%d bytes)", gf.path, len(gf.content))

    elapsed = int((time.time() - t0) * 1000)
    log.info("Assembly complete: %d generated files overlaid (%d ms)", len(generated_files), elapsed)
    return project_dir
