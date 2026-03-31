"""
Plan writer — generates and updates ``plan.md`` inside the game directory.

The file is written/updated at every pipeline stage so the user can
follow progress in real time via the frontend.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from src import config
from src.logger import LOGS_DIR

if TYPE_CHECKING:
    from src.models import GameAnalysis, GamePlan, Project


def _plan_path(project_id: str) -> Path:
    """Store plan.md in ``logs/{YYYY-MM-DD}/{project_id}_plan.md``."""
    from datetime import date as _date
    day_dir = LOGS_DIR / _date.today().isoformat()
    day_dir.mkdir(parents=True, exist_ok=True)
    return day_dir / f"{project_id}_plan.md"


def _ts() -> str:
    return datetime.now().strftime("%H:%M:%S")


# ── Public API ──────────────────────────────────────────────────────────────

def write_init(project_id: str, prompt: str, engine: str) -> None:
    """Write the initial plan.md with just the user prompt."""
    path = _plan_path(project_id)
    lines = [
        f"# 🎮 游戏生成方案",
        f"",
        f"> 创建时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"",
        f"---",
        f"",
        f"## 📝 用户描述",
        f"",
        f"{prompt}",
        f"",
        f"**引擎**: {engine}",
        f"",
        f"---",
        f"",
        f"## ⏳ 流水线状态",
        f"",
        f"- [ ] 🔍 分析游戏描述",
        f"- [ ] 📋 规划文件结构",
        f"- [ ] ⚙️ 生成游戏代码",
        f"- [ ] 🔨 组装项目",
        f"- [ ] 🧪 构建 & 测试",
        f"- [ ] ✅ 完成",
        f"",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def write_analysis(project_id: str, analysis: GameAnalysis) -> None:
    """Append analysis results to plan.md."""
    path = _plan_path(project_id)
    if not path.exists():
        return

    content = path.read_text(encoding="utf-8")
    # Update checklist
    content = content.replace(
        "- [ ] 🔍 分析游戏描述",
        f"- [x] 🔍 分析游戏描述 ✅ ({_ts()})",
    )

    content += "\n".join([
        f"## 🔍 游戏分析",
        f"",
        f"| 属性 | 内容 |",
        f"|------|------|",
        f"| 标题 | {analysis.title} |",
        f"| 类型 | {analysis.genre} |",
        f"| 引擎 | {analysis.engine.value} |",
        f"| 视觉风格 | {analysis.visual_style} |",
        f"| 难度 | {analysis.difficulty} |",
        f"",
        f"### 游戏描述",
        f"",
        f"{analysis.description}",
        f"",
        f"### 核心机制",
        f"",
    ])
    for m in analysis.mechanics:
        content += f"- {m}\n"
    content += f"\n### 主要实体\n\n"
    for e in analysis.entities:
        content += f"- {e}\n"
    content += "\n"

    path.write_text(content, encoding="utf-8")


def write_plan(project_id: str, plan: GamePlan) -> None:
    """Append file plan to plan.md."""
    path = _plan_path(project_id)
    if not path.exists():
        return

    content = path.read_text(encoding="utf-8")
    content = content.replace(
        "- [ ] 📋 规划文件结构",
        f"- [x] 📋 规划文件结构 ✅ ({_ts()})",
    )

    content += "\n".join([
        f"## 📋 文件规划",
        f"",
        f"共 **{len(plan.files)}** 个文件:",
        f"",
        f"| 文件路径 | 用途 |",
        f"|----------|------|",
    ])
    content += "\n"
    for f in plan.files:
        content += f"| `{f.path}` | {f.purpose} |\n"

    if plan.extra_scenes:
        content += f"\n**额外场景**: {', '.join(plan.extra_scenes)}\n"
    if plan.constants_overrides:
        content += f"\n**常量覆盖**:\n```json\n"
        import json
        content += json.dumps(plan.constants_overrides, indent=2, ensure_ascii=False)
        content += "\n```\n"
    content += "\n"

    path.write_text(content, encoding="utf-8")


def write_generate_progress(project_id: str, file_path: str, done: int, total: int) -> None:
    """Update the generating status line (called per file, lightweight)."""
    path = _plan_path(project_id)
    if not path.exists():
        return

    content = path.read_text(encoding="utf-8")
    # Update the checklist item with progress
    old = None
    for line in content.split("\n"):
        if "⚙️ 生成游戏代码" in line and "- [" in line:
            old = line
            break
    if old:
        new = f"- [ ] ⚙️ 生成游戏代码 ({done}/{total}) `{file_path}`"
        content = content.replace(old, new)
        path.write_text(content, encoding="utf-8")


def write_generate_done(project_id: str, total: int) -> None:
    """Mark generate step as completed."""
    path = _plan_path(project_id)
    if not path.exists():
        return

    content = path.read_text(encoding="utf-8")
    for line in content.split("\n"):
        if "⚙️ 生成游戏代码" in line and "- [" in line:
            content = content.replace(
                line,
                f"- [x] ⚙️ 生成游戏代码 — {total} 个文件 ✅ ({_ts()})",
            )
            break
    path.write_text(content, encoding="utf-8")


def write_assemble_done(project_id: str, build_dir: str) -> None:
    """Mark assemble step as completed."""
    path = _plan_path(project_id)
    if not path.exists():
        return

    content = path.read_text(encoding="utf-8")
    content = content.replace(
        "- [ ] 🔨 组装项目",
        f"- [x] 🔨 组装项目 → `{build_dir}` ✅ ({_ts()})",
    )
    path.write_text(content, encoding="utf-8")


def write_build_result(project_id: str, ok: bool, errors: list[str] | None = None) -> None:
    """Mark build/test step."""
    path = _plan_path(project_id)
    if not path.exists():
        return

    content = path.read_text(encoding="utf-8")
    if ok:
        content = content.replace(
            "- [ ] 🧪 构建 & 测试",
            f"- [x] 🧪 构建 & 测试 ✅ ({_ts()})",
        )
    else:
        err_summary = "; ".join(errors[:3]) if errors else "unknown error"
        content = content.replace(
            "- [ ] 🧪 构建 & 测试",
            f"- [ ] 🧪 构建 & 测试 ⚠️ ({_ts()}) — {err_summary}",
        )
    path.write_text(content, encoding="utf-8")


def write_fix_round(project_id: str, round_num: int, max_rounds: int, fixed_count: int) -> None:
    """Append fix round info."""
    path = _plan_path(project_id)
    if not path.exists():
        return

    content = path.read_text(encoding="utf-8")
    content += f"- 🔧 修复第 {round_num}/{max_rounds} 轮 — 修复 {fixed_count} 个文件 ({_ts()})\n"
    path.write_text(content, encoding="utf-8")


def write_final(project_id: str, status: str, total_ms: int) -> None:
    """Write final status."""
    path = _plan_path(project_id)
    if not path.exists():
        return

    content = path.read_text(encoding="utf-8")
    if status == "ready":
        content = content.replace(
            "- [ ] ✅ 完成",
            f"- [x] ✅ 完成 🎉 ({_ts()})",
        )
        content += f"\n---\n\n## 🎉 完成\n\n游戏已就绪！总耗时 **{total_ms / 1000:.1f}** 秒\n"
    else:
        content = content.replace(
            "- [ ] ✅ 完成",
            f"- [x] ❌ 失败 ({_ts()})",
        )
        content += f"\n---\n\n## ❌ 失败\n\n总耗时 **{total_ms / 1000:.1f}** 秒\n"
    path.write_text(content, encoding="utf-8")


def get_content(project_id: str) -> str | None:
    """Read and return plan.md content, searching across date directories."""
    if not LOGS_DIR.exists():
        return None
    for day_dir in sorted(LOGS_DIR.iterdir(), reverse=True):
        if not day_dir.is_dir():
            continue
        p = day_dir / f"{project_id}_plan.md"
        if p.exists():
            return p.read_text(encoding="utf-8")
    return None
