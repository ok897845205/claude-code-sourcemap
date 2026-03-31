"""
Preview server — manages vite preview processes for built games.
"""

from __future__ import annotations

import subprocess
import sys
import time
import socket
from pathlib import Path
from threading import Lock

from src import logger

log = logger.get("server.preview")

IS_WIN = sys.platform == "win32"

_lock = Lock()
_processes: dict[str, subprocess.Popen] = {}
_ports: dict[str, int] = {}


def _find_free_port(start: int = 5000, end: int = 6000) -> int:
    """Find an available TCP port."""
    for port in range(start, end):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError(f"No free port in range {start}-{end}")


def start(project_id: str, project_dir: Path) -> int:
    """Start a vite preview server and return the port."""
    with _lock:
        # Already running?
        if project_id in _processes:
            proc = _processes[project_id]
            if proc.poll() is None:
                return _ports[project_id]
            # Dead process — clean up
            _processes.pop(project_id, None)
            _ports.pop(project_id, None)

        port = _find_free_port()
        log.info("Starting preview for %s on port %d", project_id, port)
        proc = subprocess.Popen(
            ["npm", "run", "preview", "--", "--port", str(port), "--host"],
            cwd=str(project_dir),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            shell=IS_WIN,
        )
        _processes[project_id] = proc
        _ports[project_id] = port

        # Wait a moment for the server to start
        time.sleep(2)
        return port


def stop(project_id: str) -> None:
    """Stop a preview server."""
    with _lock:
        proc = _processes.pop(project_id, None)
        _ports.pop(project_id, None)
        if proc:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
            log.info("Stopped preview for %s", project_id)


def get_port(project_id: str) -> int | None:
    with _lock:
        return _ports.get(project_id)


def stop_all() -> None:
    with _lock:
        for pid in list(_processes):
            proc = _processes.pop(pid)
            proc.terminate()
        _ports.clear()
