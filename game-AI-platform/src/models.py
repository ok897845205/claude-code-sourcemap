"""
Data models — Pydantic schemas for the game generation pipeline.
"""

from __future__ import annotations

from enum import Enum
from typing import Any
from pydantic import BaseModel, Field
import time
import uuid


# ── Engine ──────────────────────────────────────────────────────────────────

class EngineType(str, Enum):
    PHASER2D = "phaser2d"
    THREEJS3D = "threejs3d"


# ── Analysis ────────────────────────────────────────────────────────────────

class GameAnalysis(BaseModel):
    """Output of the analysis step — structured understanding of the request."""
    title: str = Field(description="Short game title")
    engine: EngineType = Field(description="Which engine template to use")
    genre: str = Field(description="Game genre, e.g. platformer, shooter, puzzle")
    description: str = Field(description="Expanded one-paragraph description")
    mechanics: list[str] = Field(description="Core game mechanics")
    entities: list[str] = Field(description="Key entities / objects in the game")
    visual_style: str = Field(description="Visual style, e.g. retro pixel, cartoon, sci-fi")
    difficulty: str = Field(default="medium", description="Target difficulty")


# ── Plan ────────────────────────────────────────────────────────────────────

class FilePlan(BaseModel):
    path: str = Field(description="Relative path inside src/, e.g. 'entities/Ball.js'")
    purpose: str = Field(description="One-line description of what this file does")


class GamePlan(BaseModel):
    """Output of the planning step — list of files to generate."""
    files: list[FilePlan] = Field(description="Files to generate/overwrite")
    constants_overrides: dict[str, Any] = Field(
        default_factory=dict,
        description="Key-value overrides for Constants.js",
    )
    extra_scenes: list[str] = Field(
        default_factory=list,
        description="Additional scene class names beyond Boot/Game/GameOver",
    )


# ── Generated file ─────────────────────────────────────────────────────────

class GeneratedFile(BaseModel):
    path: str
    content: str


# ── Project ─────────────────────────────────────────────────────────────────

class ProjectStatus(str, Enum):
    ANALYZING = "analyzing"
    PLANNING = "planning"
    GENERATING = "generating"
    BUILDING = "building"
    TESTING = "testing"
    FIXING = "fixing"
    READY = "ready"
    FAILED = "failed"


class StepResult(BaseModel):
    step: str
    ok: bool
    message: str = ""
    duration_ms: int = 0
    data: dict[str, Any] = Field(default_factory=dict)


class Project(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    prompt: str
    engine: EngineType = EngineType.PHASER2D
    status: ProjectStatus = ProjectStatus.ANALYZING
    analysis: GameAnalysis | None = None
    plan: GamePlan | None = None
    files: list[GeneratedFile] = Field(default_factory=list)
    steps: list[StepResult] = Field(default_factory=list)
    build_dir: str = ""
    preview_port: int = 0
    created_at: float = Field(default_factory=time.time)
    error: str = ""
    conversation: list[ChatMessage] = Field(
        default_factory=list,
        description="Multi-turn conversation history for iterative refinement",
    )

    def add_step(self, step: str, ok: bool, message: str = "",
                 duration_ms: int = 0, **data: Any) -> None:
        self.steps.append(StepResult(
            step=step, ok=ok, message=message,
            duration_ms=duration_ms, data=data,
        ))


# ── API request / response ──────────────────────────────────────────────────

class CreateGameRequest(BaseModel):
    prompt: str = Field(description="Natural language game description")
    engine: EngineType = Field(default=EngineType.PHASER2D)


class IterateGameRequest(BaseModel):
    feedback: str = Field(description="User feedback for iteration")


class ChatMessage(BaseModel):
    """A single conversation message for multi-turn iteration."""
    role: str = Field(description="'user' or 'assistant'")
    content: str
    timestamp: float = Field(default_factory=time.time)
    changes_made: list[str] = Field(
        default_factory=list,
        description="Files changed/created in this turn (assistant messages only)",
    )


class ChatRequest(BaseModel):
    message: str = Field(description="User's chat message for iterative refinement")


class ProjectSummary(BaseModel):
    id: str
    prompt: str
    engine: EngineType
    status: ProjectStatus
    created_at: float
    error: str = ""
