"""
Logging — structured logger with level & format from config.

Supports per-project log files: call `attach_project_log(project_id)` to
route all log output into `logs/{date}/{project_id}.log`, and
`detach_project_log(project_id)` when the pipeline finishes.
"""

from __future__ import annotations

import logging
import sys
from datetime import date
from pathlib import Path

from src.config import LOG_LEVEL, LOG_FORMAT, ROOT_DIR

_FMT_TEXT = "%(asctime)s  %(levelname)-7s  %(name)s  %(message)s"
_FMT_JSON = '{"ts":"%(asctime)s","level":"%(levelname)s","name":"%(name)s","msg":"%(message)s"}'

LOGS_DIR = ROOT_DIR / "logs"

# Map project_id → handler so we can remove it later
_project_handlers: dict[str, logging.FileHandler] = {}


def _setup_root() -> None:
    fmt = _FMT_JSON if LOG_FORMAT == "json" else _FMT_TEXT
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter(fmt))
    root = logging.getLogger()
    root.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
    if not root.handlers:
        root.addHandler(handler)


_setup_root()


def get(name: str) -> logging.Logger:
    return logging.getLogger(name)


def attach_project_log(project_id: str) -> Path:
    """
    Add a file handler that writes all logs to
    logs/{YYYY-MM-DD}/{project_id}.log.
    Returns the log file path.
    """
    day_dir = LOGS_DIR / date.today().isoformat()
    day_dir.mkdir(parents=True, exist_ok=True)
    log_file = day_dir / f"{project_id}.log"

    fmt = _FMT_JSON if LOG_FORMAT == "json" else _FMT_TEXT
    fh = logging.FileHandler(str(log_file), encoding="utf-8")
    fh.setFormatter(logging.Formatter(fmt))
    fh.setLevel(logging.DEBUG)  # capture everything for the project log

    logging.getLogger().addHandler(fh)
    _project_handlers[project_id] = fh
    return log_file


def detach_project_log(project_id: str) -> None:
    """Remove the per-project file handler."""
    fh = _project_handlers.pop(project_id, None)
    if fh:
        fh.flush()
        fh.close()
        logging.getLogger().removeHandler(fh)
