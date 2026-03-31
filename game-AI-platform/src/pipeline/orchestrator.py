"""
Orchestrator — runs the full pipeline: analyze → plan → generate → assemble → build → (fix).

This is the top-level entry point for game creation.
"""

from __future__ import annotations

import time
from typing import Callable, Any

from src import logger
from src.models import (
    Project, ProjectStatus, CreateGameRequest,
    GeneratedFile,
)
from src.pipeline import analyzer, planner, code_gen, assembler, builder, fixer, plan_writer

log = logger.get("pipeline.orchestrator")

# Max build → fix → rebuild cycles
MAX_FIX_ROUNDS = 3


def create_game(
    request: CreateGameRequest,
    on_status: Callable[[ProjectStatus, str], None] | None = None,
    on_progress: Callable[[str, int, int], None] | None = None,
    project: Project | None = None,
) -> Project:
    """
    Run the full game creation pipeline.

    If *project* is supplied (with id already set to the dir name), it is
    used directly.  Otherwise a new Project is created with the dir name
    as its id.
    """
    if project is None:
        dir_name = assembler.make_dir_name(request.engine)
        project = Project(id=dir_name, prompt=request.prompt, engine=request.engine)
        project.build_dir = str(assembler.config.PROJECTS_DIR / dir_name)

    t_start = time.time()
    log_file = logger.attach_project_log(project.id)
    log.info("[%s] Project log → %s", project.id, log_file)
    log.info("[%s] Prompt: %s", project.id, request.prompt)

    # Initialise plan.md with the prompt
    engine_label = 'Phaser 2D' if request.engine.value == 'phaser2d' else 'Three.js 3D'
    plan_writer.write_init(project.id, request.prompt, engine_label)

    def _status(s: ProjectStatus, msg: str = ""):
        project.status = s
        log.info("[%s] %s %s", project.id, s.value, msg)
        if on_status:
            on_status(s, msg)

    try:
        # ── Step 1: Analyze ─────────────────────────────────────────────
        _status(ProjectStatus.ANALYZING, "Analyzing game description…")
        t0 = time.time()
        project.analysis = analyzer.analyze(request.prompt)
        project.engine = project.analysis.engine
        project.add_step("analyze", True,
                         f"title={project.analysis.title}",
                         duration_ms=int((time.time() - t0) * 1000))
        plan_writer.write_analysis(project.id, project.analysis)

        # ── Step 2: Plan ────────────────────────────────────────────────
        _status(ProjectStatus.PLANNING, "Planning file structure…")
        t0 = time.time()
        project.plan = planner.plan(project.analysis)
        project.add_step("plan", True,
                         f"{len(project.plan.files)} files planned",
                         duration_ms=int((time.time() - t0) * 1000))
        plan_writer.write_plan(project.id, project.plan)

        # ── Step 3: Generate ────────────────────────────────────────────
        _status(ProjectStatus.GENERATING, "Generating game code…")
        t0 = time.time()
        def _on_progress_wrapper(fp: str, done: int, total: int):
            plan_writer.write_generate_progress(project.id, fp, done, total)
            if on_progress:
                on_progress(fp, done, total)

        project.files = code_gen.generate_all(
            project.analysis, project.plan, on_progress=_on_progress_wrapper,
        )
        project.add_step("generate", True,
                         f"{len(project.files)} files generated",
                         duration_ms=int((time.time() - t0) * 1000))
        plan_writer.write_generate_done(project.id, len(project.files))

        # ── Step 4: Assemble ────────────────────────────────────────────
        _status(ProjectStatus.BUILDING, "Assembling project…")
        t0 = time.time()
        project_dir = assembler.assemble(project.id, project.engine, project.files)
        project.build_dir = str(project_dir)
        project.add_step("assemble", True, duration_ms=int((time.time() - t0) * 1000))
        plan_writer.write_assemble_done(project.id, project_dir.name)

        # ── Step 5: Build & Test ────────────────────────────────────────
        _status(ProjectStatus.TESTING, "Building & testing…")
        build_result = builder.build(project_dir)
        project.add_step("build", build_result.ok,
                         message="; ".join(build_result.errors[:3]) if not build_result.ok else "OK",
                         duration_ms=build_result.duration_ms)
        plan_writer.write_build_result(project.id, build_result.ok,
                                       build_result.errors if not build_result.ok else None)

        # ── Step 6: Fix loop ────────────────────────────────────────────
        fix_round = 0
        while not build_result.ok and fix_round < MAX_FIX_ROUNDS:
            fix_round += 1
            _status(ProjectStatus.FIXING, f"Fix round {fix_round}/{MAX_FIX_ROUNDS}…")
            t0 = time.time()

            fixed = fixer.fix_files(project_dir, build_result.errors, project.analysis)
            project.add_step(f"fix-{fix_round}", True,
                             f"{len(fixed)} files fixed",
                             duration_ms=int((time.time() - t0) * 1000))
            plan_writer.write_fix_round(project.id, fix_round, MAX_FIX_ROUNDS, len(fixed))

            _status(ProjectStatus.TESTING, f"Rebuild after fix {fix_round}…")
            build_result = builder.build(project_dir)
            project.add_step(f"rebuild-{fix_round}", build_result.ok,
                             message="; ".join(build_result.errors[:3]) if not build_result.ok else "OK",
                             duration_ms=build_result.duration_ms)

        if build_result.ok:
            _status(ProjectStatus.READY, "Game is ready!")
        else:
            project.error = "; ".join(build_result.errors[:3])
            _status(ProjectStatus.FAILED, project.error)

    except Exception as e:
        log.exception("Pipeline error")
        project.status = ProjectStatus.FAILED
        project.error = str(e)
        project.add_step("error", False, message=str(e))

    total_ms = int((time.time() - t_start) * 1000)
    plan_writer.write_final(project.id, project.status.value, total_ms)
    log.info("[%s] Pipeline finished: %s (%d ms total)", project.id, project.status.value, total_ms)
    logger.detach_project_log(project.id)
    return project


def iterate_game(
    project: Project,
    feedback: str,
    on_status: Callable[[ProjectStatus, str], None] | None = None,
    on_progress: Callable[[str, int, int], None] | None = None,
) -> Project:
    """
    Iterate on an existing game based on user feedback.
    Re-generates only files that need to change.
    """
    from src.llm import client, prompts
    from src.models import ProjectStatus, FilePlan
    from src import config
    from pathlib import Path
    import json

    if not project.analysis or not project.plan:
        project.error = "Cannot iterate — no analysis/plan available"
        project.status = ProjectStatus.FAILED
        return project

    logger.attach_project_log(project.id)
    log.info("[%s] Iterate feedback: %s", project.id, feedback)

    def _status(s: ProjectStatus, msg: str = ""):
        project.status = s
        log.info("[%s] %s %s", project.id, s.value, msg)
        if on_status:
            on_status(s, msg)

    try:
        # Determine what to change
        _status(ProjectStatus.PLANNING, "Analyzing feedback…")
        project_dir = Path(project.build_dir)
        src_dir = project_dir / "src"

        file_list = ""
        for gf in project.files:
            file_list += f"  - {gf.path}\n"

        system, user = prompts.iterate_plan(project.analysis, file_list, feedback)
        change_plan = client.chat_json(system, user, max_tokens=config.LLM_PLAN_MAX_TOKENS)

        files_to_update = change_plan.get("files_to_update", [])
        new_files = change_plan.get("new_files", [])

        # Add new files to plan
        for nf in new_files:
            project.plan.files.append(FilePlan(path=nf["path"], purpose=nf["purpose"]))

        # Re-generate changed files
        _status(ProjectStatus.GENERATING, f"Updating {len(files_to_update) + len(new_files)} files…")
        all_to_gen = files_to_update + new_files
        updated_files: list[GeneratedFile] = []
        for i, f_info in enumerate(all_to_gen):
            path = f_info["path"]
            purpose = f_info.get("purpose", f_info.get("reason", "updated"))
            gf = code_gen.generate_file(
                project.engine, path, purpose, project.analysis, project.plan,
            )
            # Write to disk
            dest = src_dir / gf.path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(gf.content, encoding="utf-8")
            updated_files.append(gf)
            if on_progress:
                on_progress(path, i + 1, len(all_to_gen))

        # Update project files list
        existing_paths = {gf.path for gf in updated_files}
        project.files = [f for f in project.files if f.path not in existing_paths] + updated_files

        # Rebuild
        _status(ProjectStatus.TESTING, "Rebuilding…")
        build_result = builder.build(project_dir)

        if build_result.ok:
            _status(ProjectStatus.READY)
        else:
            # One fix attempt
            _status(ProjectStatus.FIXING, "Fixing issues…")
            fixer.fix_files(project_dir, build_result.errors, project.analysis)
            build_result = builder.build(project_dir)

            if build_result.ok:
                _status(ProjectStatus.READY)
            else:
                project.error = "; ".join(build_result.errors[:3])
                _status(ProjectStatus.FAILED, project.error)

    except Exception as e:
        log.exception("Iterate error")
        project.status = ProjectStatus.FAILED
        project.error = str(e)

    logger.detach_project_log(project.id)
    return project


def chat_iterate(
    project: Project,
    user_message: str,
    on_status: Callable[[ProjectStatus, str], None] | None = None,
    on_progress: Callable[[str, int, int], None] | None = None,
) -> tuple[str, list[str]]:
    """
    Multi-turn conversation iteration.
    Appends user_message to project.conversation, calls LLM with full history,
    parses the action block, regenerates files, appends assistant reply.

    Returns:
        (assistant_reply_text, list_of_changed_file_paths)
    """
    from src.llm import client, prompts
    from src.models import ProjectStatus, FilePlan, ChatMessage
    from src import config
    from pathlib import Path
    import json, re, time as _time

    if not project.analysis or not project.plan:
        raise ValueError("Cannot iterate — no analysis/plan available")

    def _status(s: ProjectStatus, msg: str = ""):
        project.status = s
        if on_status:
            on_status(s, msg)

    logger.attach_project_log(project.id)
    log.info("[%s] Chat message: %s", project.id, user_message)

    # Record user message
    project.conversation.append(ChatMessage(
        role="user", content=user_message,
    ))

    # Build file list
    file_list = ", ".join(gf.path for gf in project.files)

    # Build system prompt with game context
    system = prompts.chat_system(project.analysis, file_list)

    # Build multi-turn messages for the LLM
    llm_messages = []
    for msg in project.conversation:
        llm_messages.append({"role": msg.role, "content": msg.content})

    _status(ProjectStatus.PLANNING, "AI 正在思考…")
    reply = client.chat_multi(system, llm_messages, max_tokens=config.LLM_MAX_TOKENS)

    # Parse <action>...</action> block
    action_match = re.search(r"<action>\s*(\{.*?\})\s*</action>", reply, re.DOTALL)
    changed_files: list[str] = []

    # Clean reply text (strip the action block for display)
    display_reply = re.sub(r"<action>.*?</action>", "", reply, flags=re.DOTALL).strip()

    if action_match:
        try:
            action = json.loads(action_match.group(1))
        except json.JSONDecodeError:
            action = {"no_change": True}

        if not action.get("no_change", False):
            files_to_update = action.get("files_to_update", [])
            new_files = action.get("new_files", [])

            # Add new files to plan
            for nf in new_files:
                project.plan.files.append(FilePlan(path=nf["path"], purpose=nf["purpose"]))

            all_to_gen = files_to_update + new_files
            if all_to_gen:
                _status(ProjectStatus.GENERATING, f"更新 {len(all_to_gen)} 个文件…")
                project_dir = Path(project.build_dir)
                src_dir = project_dir / "src"

                updated_files: list[GeneratedFile] = []
                for i, f_info in enumerate(all_to_gen):
                    path = f_info["path"]
                    purpose = f_info.get("purpose", f_info.get("reason", "updated"))
                    gf = code_gen.generate_file(
                        project.engine, path, purpose, project.analysis, project.plan,
                    )
                    dest = src_dir / gf.path
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_text(gf.content, encoding="utf-8")
                    updated_files.append(gf)
                    changed_files.append(path)
                    if on_progress:
                        on_progress(path, i + 1, len(all_to_gen))

                # Update project files list
                existing_paths = {gf.path for gf in updated_files}
                project.files = [f for f in project.files if f.path not in existing_paths] + updated_files

                # Rebuild
                _status(ProjectStatus.TESTING, "重新构建…")
                build_result = builder.build(project_dir)

                if not build_result.ok:
                    _status(ProjectStatus.FIXING, "修复问题…")
                    fixer.fix_files(project_dir, build_result.errors, project.analysis)
                    build_result = builder.build(project_dir)

                if build_result.ok:
                    _status(ProjectStatus.READY, "更新完成！")
                else:
                    project.error = "; ".join(build_result.errors[:3])
                    _status(ProjectStatus.READY, "构建有警告，但游戏已更新")
        else:
            _status(ProjectStatus.READY)
    else:
        _status(ProjectStatus.READY)

    # Record assistant reply
    project.conversation.append(ChatMessage(
        role="assistant", content=display_reply, changes_made=changed_files,
    ))

    log.info("[%s] Chat reply: %s (changed: %s)", project.id, display_reply[:100], changed_files)
    logger.detach_project_log(project.id)
    return display_reply, changed_files
