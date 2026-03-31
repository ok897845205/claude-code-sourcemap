"""
FastAPI application — REST API for the game-AI-platform.

Routes:
  POST   /api/v1/games          — create a new game
  GET    /api/v1/games          — list all games
  GET    /api/v1/games/{id}     — get project details
  POST   /api/v1/games/{id}/iterate — iterate on a game
  POST   /api/v1/games/{id}/preview — start preview server
  DELETE /api/v1/games/{id}/preview — stop preview server
  DELETE /api/v1/games/{id}     — delete a project
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from src import config, logger
from src.models import (
    CreateGameRequest, IterateGameRequest, ChatRequest,
    Project, ProjectSummary, ProjectStatus,
)
from src.server import store, preview
from src.pipeline import orchestrator

log = logger.get("server.app")

# SSE connections for live status updates
_sse_queues: dict[str, asyncio.Queue] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Game AI Platform starting (env=%s)", config.APP_ENV)
    yield
    preview.stop_all()
    log.info("Game AI Platform shutting down")


app = FastAPI(
    title="Game AI Platform",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — allow the frontend (dev mode on different port)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static frontend
static_dir = config.STATIC_DIR
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


# ── API Routes ──────────────────────────────────────────────────────────────

@app.get("/")
async def index():
    """Serve the frontend SPA."""
    index_file = static_dir / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "Game AI Platform API", "docs": "/docs"}


@app.post(f"{config.API_PREFIX}/games", response_model=ProjectSummary)
async def api_create_game(request: CreateGameRequest, bg: BackgroundTasks):
    """Start game creation pipeline in background."""
    from src.pipeline.assembler import make_dir_name

    # Determine the directory name immediately — it IS the project id
    dir_name = make_dir_name(request.engine)
    project = Project(id=dir_name, prompt=request.prompt, engine=request.engine)
    project.build_dir = str(config.PROJECTS_DIR / dir_name)
    store.put(project)

    # Create SSE queue for this project
    _sse_queues[project.id] = asyncio.Queue()

    bg.add_task(_run_pipeline, project, request)
    return ProjectSummary(
        id=project.id,
        prompt=project.prompt,
        engine=project.engine,
        status=project.status,
        created_at=project.created_at,
    )


@app.get(f"{config.API_PREFIX}/games")
async def api_list_games():
    """List all projects."""
    projects = store.list_all()
    return [
        ProjectSummary(
            id=p.id, prompt=p.prompt, engine=p.engine,
            status=p.status, created_at=p.created_at, error=p.error,
        )
        for p in projects
    ]


@app.get(f"{config.API_PREFIX}/games/{{project_id}}")
async def api_get_game(project_id: str):
    """Get project details."""
    project = store.get(project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    return project.model_dump()


@app.post(f"{config.API_PREFIX}/games/{{project_id}}/iterate")
async def api_iterate_game(project_id: str, request: IterateGameRequest, bg: BackgroundTasks):
    """Iterate on an existing game."""
    project = store.get(project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    if project.status not in (ProjectStatus.READY, ProjectStatus.FAILED):
        raise HTTPException(409, f"Project is {project.status.value}, cannot iterate now")

    bg.add_task(_run_iterate, project, request.feedback)
    return {"id": project_id, "status": "iterating"}


@app.post(f"{config.API_PREFIX}/games/{{project_id}}/chat")
async def api_chat(project_id: str, request: ChatRequest, bg: BackgroundTasks):
    """Multi-turn conversation for iterative game refinement."""
    project = store.get(project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    if project.status not in (ProjectStatus.READY, ProjectStatus.FAILED):
        raise HTTPException(409, f"Project is {project.status.value}, cannot chat now")

    # Create SSE queue for live updates
    _sse_queues[project_id] = asyncio.Queue()
    bg.add_task(_run_chat, project, request.message)
    return {"id": project_id, "status": "chatting"}


@app.get(f"{config.API_PREFIX}/games/{{project_id}}/conversation")
async def api_get_conversation(project_id: str):
    """Get conversation history for a project."""
    project = store.get(project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    return [msg.model_dump() for msg in project.conversation]


@app.get(f"{config.API_PREFIX}/games/{{project_id}}/logs")
async def api_get_logs(project_id: str):
    """Return the per-project log file content."""
    from src.logger import LOGS_DIR

    # Search logs directories (newest first) for {project_id}.log
    if LOGS_DIR.exists():
        for day_dir in sorted(LOGS_DIR.iterdir(), reverse=True):
            if not day_dir.is_dir():
                continue
            log_file = day_dir / f"{project_id}.log"
            if log_file.exists():
                return FileResponse(str(log_file), media_type="text/plain; charset=utf-8")
    raise HTTPException(404, "Log not found for this project")


@app.get(f"{config.API_PREFIX}/games/{{project_id}}/plan")
async def api_get_plan(project_id: str):
    """Return the plan.md content for real-time progress viewing."""
    from src.pipeline.plan_writer import get_content
    from fastapi.responses import PlainTextResponse

    content = get_content(project_id)
    if content is None:
        raise HTTPException(404, "Plan not found for this project")
    return PlainTextResponse(content, media_type="text/plain; charset=utf-8")


@app.post(f"{config.API_PREFIX}/games/{{project_id}}/preview")
async def api_start_preview(project_id: str):
    """Start a preview server for the game."""
    project = store.get(project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    if not project.build_dir:
        raise HTTPException(400, "Project has not been built yet")

    port = preview.start(project_id, Path(project.build_dir))
    project.preview_port = port
    store.put(project)
    return {"port": port, "url": f"http://localhost:{port}"}


@app.delete(f"{config.API_PREFIX}/games/{{project_id}}/preview")
async def api_stop_preview(project_id: str):
    preview.stop(project_id)
    return {"ok": True}


@app.delete(f"{config.API_PREFIX}/games/{{project_id}}")
async def api_delete_game(project_id: str):
    preview.stop(project_id)
    if store.delete(project_id):
        return {"ok": True}
    raise HTTPException(404, "Project not found")


@app.get(f"{config.API_PREFIX}/games/{{project_id}}/events")
async def api_game_events(project_id: str):
    """SSE endpoint for live pipeline status updates."""
    from starlette.responses import StreamingResponse

    queue = _sse_queues.get(project_id)
    if not queue:
        raise HTTPException(404, "No active pipeline for this project")

    async def stream():
        while True:
            data = await queue.get()
            yield f"data: {data}\n\n"
            if '"done":true' in data or '"status":"ready"' in data or '"status":"failed"' in data:
                break

    return StreamingResponse(stream(), media_type="text/event-stream")


# ── Background tasks ───────────────────────────────────────────────────────

def _run_pipeline(project: Project, request: CreateGameRequest) -> None:
    import json

    def on_status(status: ProjectStatus, msg: str):
        project.status = status
        store.put(project)
        q = _sse_queues.get(project.id)
        if q:
            try:
                q.put_nowait(json.dumps({"status": status.value, "message": msg}))
            except Exception:
                pass

    def on_progress(file_path: str, done: int, total: int):
        q = _sse_queues.get(project.id)
        if q:
            try:
                q.put_nowait(json.dumps({
                    "status": "generating", "file": file_path,
                    "done": done, "total": total,
                }))
            except Exception:
                pass

    result = orchestrator.create_game(
        request, on_status=on_status, on_progress=on_progress,
        project=project,
    )

    # The orchestrator mutates the project in-place; just persist final state
    store.put(project)

    # Signal completion
    q = _sse_queues.pop(project.id, None)
    if q:
        try:
            q.put_nowait(json.dumps({"status": project.status.value, "done": True}))
        except Exception:
            pass


def _run_iterate(project: Project, feedback: str) -> None:
    import json

    def on_status(status: ProjectStatus, msg: str):
        project.status = status
        store.put(project)

    orchestrator.iterate_game(project, feedback, on_status=on_status)
    store.put(project)


def _run_chat(project: Project, message: str) -> None:
    import json

    def on_status(status: ProjectStatus, msg: str):
        project.status = status
        store.put(project)
        q = _sse_queues.get(project.id)
        if q:
            try:
                q.put_nowait(json.dumps({"status": status.value, "message": msg}))
            except Exception:
                pass

    def on_progress(file_path: str, done: int, total: int):
        q = _sse_queues.get(project.id)
        if q:
            try:
                q.put_nowait(json.dumps({
                    "status": "generating", "file": file_path,
                    "done": done, "total": total,
                }))
            except Exception:
                pass

    try:
        reply, changed = orchestrator.chat_iterate(
            project, message, on_status=on_status, on_progress=on_progress,
        )
        store.put(project)

        q = _sse_queues.pop(project.id, None)
        if q:
            try:
                q.put_nowait(json.dumps({
                    "status": project.status.value,
                    "done": True,
                    "reply": reply,
                    "changed_files": changed,
                }))
            except Exception:
                pass
    except Exception as e:
        project.status = ProjectStatus.FAILED
        project.error = str(e)
        store.put(project)
        q = _sse_queues.pop(project.id, None)
        if q:
            try:
                q.put_nowait(json.dumps({"status": "failed", "done": True, "error": str(e)}))
            except Exception:
                pass
