from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PipelineEvent:
    """Base class for all pipeline events."""

    run_id: str


@dataclass(frozen=True)
class PipelineStarted(PipelineEvent):
    audio_path: Path
    total_stages: int
    resume_after: int


@dataclass(frozen=True)
class PipelineFinished(PipelineEvent):
    segments_count: int


@dataclass(frozen=True)
class PipelineFailed(PipelineEvent):
    error: str


@dataclass(frozen=True)
class StageStarted(PipelineEvent):
    stage_index: int
    stage_name: str


@dataclass(frozen=True)
class StageFinished(PipelineEvent):
    stage_index: int
    stage_name: str
    segments_count: int
    artifact: Path | None = None


@dataclass(frozen=True)
class StageSkipped(PipelineEvent):
    stage_index: int
    stage_name: str


@dataclass(frozen=True)
class ProgressUpdated(PipelineEvent):
    stage_index: int
    stage_name: str
    current: int
    total: int
    message: str = ""
