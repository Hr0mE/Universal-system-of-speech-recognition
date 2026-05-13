from __future__ import annotations

from pathlib import Path

import pytest

from core.pipeline.context import PipelineContext, Segment
from core.pipeline.stage import Stage
from core.storage.run_manager import RunManager


class RecordingStage(Stage):
    """Stage that appends a synthetic segment and records how many times it ran."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.calls = 0
        self.skipped_calls = 0

    def run(
        self,
        segments: list[Segment],
        context: PipelineContext,
    ) -> list[Segment]:
        self.calls += 1
        return [
            *segments,
            Segment(
                start_time=float(len(segments)),
                end_time=float(len(segments) + 1),
                speaker_id=self.name,
            ),
        ]

    def on_stage_skipped(self, context: PipelineContext) -> None:
        self.skipped_calls += 1


class BoomStage(Stage):
    """Stage that always raises — used to simulate crashes mid-pipeline."""

    def __init__(self, name: str = "boom", exc: Exception | None = None) -> None:
        self.name = name
        self.exc = exc or RuntimeError("kaboom")
        self.calls = 0

    def run(
        self,
        segments: list[Segment],
        context: PipelineContext,
    ) -> list[Segment]:
        self.calls += 1
        raise self.exc


@pytest.fixture
def run_manager(tmp_path: Path) -> RunManager:
    return RunManager(runs_root=tmp_path / "runs")


@pytest.fixture
def run_dir(run_manager: RunManager) -> Path:
    return run_manager.create_run("run_test_0001")


@pytest.fixture
def context(run_dir: Path) -> PipelineContext:
    return PipelineContext(
        run_id="run_test_0001",
        audio_path=Path("/tmp/fake.wav"),
        run_dir=run_dir,
        audio_duration=60.0,
    )


@pytest.fixture
def recording_stage_factory():
    return RecordingStage


@pytest.fixture
def boom_stage_factory():
    return BoomStage
