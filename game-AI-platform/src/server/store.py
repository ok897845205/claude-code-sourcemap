"""
Project store — per-project ``project.json`` inside each game directory.

Each game lives in ``data/projects/<dir_name>/`` and its metadata is stored
in ``data/projects/<dir_name>/project.json``.
"""

from __future__ import annotations

import json
from pathlib import Path
from threading import Lock

from src import config, logger
from src.models import Project

log = logger.get("server.store")

_lock = Lock()
_projects: dict[str, Project] = {}
_loaded = False


def _project_json(project_id: str) -> Path:
    """Return the path to ``data/projects/<project_id>/project.json``."""
    return config.PROJECTS_DIR / project_id / "project.json"


def _load() -> None:
    """Scan all game directories and load their ``project.json``."""
    global _projects, _loaded
    if _loaded:
        return
    _loaded = True
    if not config.PROJECTS_DIR.exists():
        return
    for child in config.PROJECTS_DIR.iterdir():
        pj = child / "project.json"
        if child.is_dir() and pj.exists():
            try:
                raw = json.loads(pj.read_text(encoding="utf-8"))
                p = Project(**raw)
                _projects[p.id] = p
            except Exception:
                log.warning("Could not load %s", pj)
    log.info("Loaded %d projects from disk", len(_projects))


def _save_one(project: Project) -> None:
    """Persist a single project's ``project.json`` (only if game dir exists)."""
    game_dir = config.PROJECTS_DIR / project.id
    if not game_dir.exists():
        return  # directory not yet created by assembler; skip disk write
    pj = game_dir / "project.json"
    pj.write_text(
        json.dumps(project.model_dump(), default=str, indent=2),
        encoding="utf-8",
    )


def put(project: Project) -> None:
    with _lock:
        _load()
        _projects[project.id] = project
        _save_one(project)


def get(project_id: str) -> Project | None:
    with _lock:
        _load()
        return _projects.get(project_id)


def list_all() -> list[Project]:
    with _lock:
        _load()
        return sorted(_projects.values(), key=lambda p: p.created_at, reverse=True)


def delete(project_id: str) -> bool:
    with _lock:
        _load()
        if project_id in _projects:
            del _projects[project_id]
            pj = _project_json(project_id)
            if pj.exists():
                pj.unlink()
            return True
        return False
