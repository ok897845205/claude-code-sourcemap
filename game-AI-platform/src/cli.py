"""
CLI — command-line interface for the Game AI Platform.

Usage:
  # Start the web server (API + frontend)
  python -m src.cli serve

  # Create a game from command line
  python -m src.cli create "贪吃蛇游戏，复古像素风" --engine phaser2d

  # Iterate on an existing game
  python -m src.cli iterate <project_id> "加快移动速度"

  # List all projects
  python -m src.cli list
"""

from __future__ import annotations

import argparse
import sys
import json

from src import logger

log = logger.get("cli")


def cmd_serve(args):
    """Start the FastAPI server."""
    import uvicorn
    from src.config import API_PREFIX

    log.info("Starting Game AI Platform server on port %d …", args.port)
    uvicorn.run(
        "src.server.app:app",
        host=args.host,
        port=args.port,
        reload=(args.reload),
        log_level="info",
    )


def cmd_create(args):
    """Create a game from the command line."""
    from src.models import CreateGameRequest, EngineType, ProjectStatus
    from src.pipeline.orchestrator import create_game

    engine = EngineType(args.engine)
    request = CreateGameRequest(prompt=args.prompt, engine=engine)

    def on_status(status: ProjectStatus, msg: str):
        icon = {
            "analyzing": "🔍", "planning": "📋", "generating": "⚙️",
            "building": "🔨", "testing": "🧪", "fixing": "🔧",
            "ready": "🎉", "failed": "❌",
        }.get(status.value, "•")
        print(f"  {icon} {status.value}: {msg}")

    def on_progress(file_path: str, done: int, total: int):
        print(f"    📝 [{done}/{total}] {file_path}")

    print(f"🎮 创建游戏: {args.prompt}")
    print(f"   引擎: {engine.value}\n")

    project = create_game(request, on_status=on_status, on_progress=on_progress)

    print(f"\n{'='*60}")
    if project.status == ProjectStatus.READY:
        print(f"✅ 游戏创建成功!")
        print(f"   项目 ID: {project.id}")
        print(f"   目录: {project.build_dir}")
        print(f"\n   预览游戏:")
        print(f"     cd {project.build_dir}")
        print(f"     npm run preview")
    else:
        print(f"❌ 创建失败: {project.error}")

    # Save to store
    from src.server.store import put
    put(project)

    return project


def cmd_iterate(args):
    """Iterate on an existing game."""
    from src.server.store import get, put
    from src.pipeline.orchestrator import iterate_game
    from src.models import ProjectStatus

    project = get(args.project_id)
    if not project:
        print(f"❌ 项目 {args.project_id} 不存在")
        sys.exit(1)

    def on_status(status: ProjectStatus, msg: str):
        print(f"  • {status.value}: {msg}")

    print(f"🔄 迭代修改: {args.feedback}")
    project = iterate_game(project, args.feedback, on_status=on_status)
    put(project)

    if project.status == ProjectStatus.READY:
        print("✅ 迭代完成!")
    else:
        print(f"❌ 迭代失败: {project.error}")


def cmd_list(args):
    """List all projects."""
    from src.server.store import list_all
    import time

    projects = list_all()
    if not projects:
        print("还没有创建过游戏。")
        return

    for p in projects:
        age = time.time() - p.created_at
        if age < 3600:
            age_str = f"{int(age/60)}m ago"
        elif age < 86400:
            age_str = f"{int(age/3600)}h ago"
        else:
            age_str = f"{int(age/86400)}d ago"

        status_icon = {"ready": "✅", "failed": "❌"}.get(p.status.value, "⏳")
        print(f"  {status_icon} [{p.id}] {p.prompt[:50]}  ({p.engine.value}, {p.status.value}, {age_str})")


def main():
    parser = argparse.ArgumentParser(
        prog="game-ai-platform",
        description="🎮 AI 游戏创造平台 — 描述你想要的游戏，AI 自动完成一切",
    )
    subs = parser.add_subparsers(dest="command", required=True)

    # serve
    p_serve = subs.add_parser("serve", help="启动 Web 服务器")
    p_serve.add_argument("--host", default="0.0.0.0", help="绑定地址 (default: 0.0.0.0)")
    p_serve.add_argument("--port", type=int, default=8000, help="端口 (default: 8000)")
    p_serve.add_argument("--reload", action="store_true", help="开发模式自动重载")

    # create
    p_create = subs.add_parser("create", help="从命令行创建游戏")
    p_create.add_argument("prompt", help="游戏描述")
    p_create.add_argument("--engine", choices=["phaser2d", "threejs3d"], default="phaser2d")

    # iterate
    p_iter = subs.add_parser("iterate", help="迭代修改游戏")
    p_iter.add_argument("project_id", help="项目 ID")
    p_iter.add_argument("feedback", help="修改描述")

    # list
    subs.add_parser("list", help="列出所有项目")

    args = parser.parse_args()
    cmd_map = {"serve": cmd_serve, "create": cmd_create, "iterate": cmd_iterate, "list": cmd_list}
    cmd_map[args.command](args)


if __name__ == "__main__":
    main()
