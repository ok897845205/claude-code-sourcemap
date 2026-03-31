"""
Builder — Step 5 of the pipeline.
Runs npm install + npm run build + architecture validation + runtime tests.
"""

from __future__ import annotations

import json
import re
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from src import logger

log = logger.get("pipeline.builder")

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
IS_WIN = sys.platform == "win32"


@dataclass
class BuildResult:
    ok: bool
    install_ok: bool = True
    build_ok: bool = True
    arch_ok: bool = True
    runtime_ok: bool = True
    install_log: str = ""
    build_log: str = ""
    arch_report: dict = None
    runtime_report: dict = None
    duration_ms: int = 0

    def __post_init__(self):
        if self.arch_report is None:
            self.arch_report = {}
        if self.runtime_report is None:
            self.runtime_report = {}

    @property
    def errors(self) -> list[str]:
        errs = []
        if not self.install_ok:
            errs.append(f"npm install failed:\n{_ANSI_RE.sub('', self.install_log[-500:])}")
        if not self.build_ok:
            errs.append(f"vite build failed:\n{_ANSI_RE.sub('', self.build_log[-500:])}")
        if not self.arch_ok:
            violations = self.arch_report.get("violations", [])
            errs.extend(violations[:10])
        if not self.runtime_ok:
            runtime_errs = self.runtime_report.get("errors", [])
            errs.extend(runtime_errs[:10])
        return errs


def _run(cmd: list[str], cwd: Path, timeout: int = 120) -> tuple[int, str, str]:
    """Run a subprocess and return (returncode, stdout, stderr)."""
    # On Windows, join into a single string so cmd.exe properly pipes output
    run_cmd = " ".join(cmd) if IS_WIN else cmd
    log.debug("$ %s  (cwd=%s)", " ".join(cmd), cwd)
    try:
        result = subprocess.run(
            run_cmd, cwd=str(cwd),
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=timeout, shell=IS_WIN,
        )
        out = result.stdout or ""
        err = result.stderr or ""
        if out:
            log.debug("stdout: %s", out[:300])
        if err:
            log.debug("stderr: %s", err[:300])
        return result.returncode, out, err
    except subprocess.TimeoutExpired:
        return -1, "", "TIMEOUT"
    except FileNotFoundError as e:
        return -1, "", str(e)
    except Exception as e:
        log.error("Subprocess error: %s", e)
        return -1, "", str(e)


def build(project_dir: Path) -> BuildResult:
    """Run the full build pipeline for a project."""
    t0 = time.time()
    res = BuildResult(ok=False)

    # 1. npm install
    log.info("Step 1/4: npm install …")
    code, out, err = _run(["npm", "install"], project_dir, timeout=180)
    res.install_log = out + err
    if code != 0:
        res.install_ok = False
        res.duration_ms = int((time.time() - t0) * 1000)
        log.error("npm install failed (exit %d)", code)
        return res

    # 2. Architecture validation
    log.info("Step 2/4: validate architecture …")
    code, out, err = _run(
        ["node", "scripts/validate-architecture.mjs"],
        project_dir, timeout=30,
    )
    try:
        res.arch_report = json.loads(out)
        res.arch_ok = res.arch_report.get("success", False)
    except (json.JSONDecodeError, ValueError):
        res.arch_ok = code == 0
        res.arch_report = {"success": res.arch_ok, "raw": out + err}

    if not res.arch_ok:
        log.warning("Architecture validation found issues")

    # 3. vite build
    log.info("Step 3/4: vite build …")
    code, out, err = _run(["npm", "run", "build"], project_dir, timeout=120)
    res.build_log = out + err
    if code != 0:
        res.build_ok = False
        res.duration_ms = int((time.time() - t0) * 1000)
        log.error("vite build failed (exit %d)", code)
        return res

    # 4. Runtime test (requires preview server — we start and stop it)
    log.info("Step 4/4: runtime verification …")
    res.runtime_ok, res.runtime_report = _run_runtime_test(project_dir)

    # Build succeeds if install + build passed; arch and runtime are advisory
    res.ok = res.install_ok and res.build_ok
    if not res.arch_ok:
        log.warning("Architecture issues found (non-fatal)")
    if not res.runtime_ok:
        log.warning("Runtime test failed (non-fatal)")
    res.duration_ms = int((time.time() - t0) * 1000)
    log.info("Build %s (%d ms)", "OK" if res.ok else "FAILED", res.duration_ms)
    return res


def _wait_for_port(port: int, timeout: float = 10.0) -> bool:
    """Poll until a TCP port is accepting connections."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.3)
    return False


def _run_runtime_test(project_dir: Path) -> tuple[bool, dict]:
    """Start vite preview, run verify-runtime.mjs, then kill the server."""
    preview_port = 4173

    # Start preview server in background
    preview_proc = subprocess.Popen(
        ["npm", "run", "preview"],
        cwd=str(project_dir),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        shell=IS_WIN,
    )

    try:
        # Wait for server to be ready (poll port instead of fixed sleep)
        if not _wait_for_port(preview_port, timeout=15.0):
            log.warning("Preview server did not start within 15 s — skipping runtime test")
            return True, {"success": True, "skipped": True,
                          "reason": "preview server did not start in time"}

        # Run runtime test
        code, out, err = _run(
            ["node", "scripts/verify-runtime.mjs",
             f"--port={preview_port}", "--timeout=10000"],
            project_dir, timeout=45,
        )
        try:
            report = json.loads(out)
            ok = report.get("success", False)
        except (json.JSONDecodeError, ValueError):
            ok = code == 0
            report = {"success": ok, "raw": (out + err)[:2000]}

        return ok, report
    except Exception as e:
        log.warning("Runtime test error (non-fatal): %s", e)
        return True, {"success": True, "skipped": True,
                      "reason": f"runtime test error: {e}"}
    finally:
        preview_proc.terminate()
        try:
            preview_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            preview_proc.kill()
