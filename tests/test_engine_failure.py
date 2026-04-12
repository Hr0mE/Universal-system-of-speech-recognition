from __future__ import annotations

import pytest

from core.events.bus import EventBus
from core.events.events import (
    PipelineFailed,
    PipelineFinished,
    StageFinished,
    StageStarted,
)
from core.pipeline.engine import PipelineEngine
from core.pipeline.state import STATUS_COMPLETED, STATUS_FAILED


def test_stage_exception_propagates_to_caller(
    run_manager, context, recording_stage_factory, boom_stage_factory
):
    stages = [recording_stage_factory("dummy"), boom_stage_factory("boom")]
    engine = PipelineEngine(stages=stages, run_manager=run_manager)

    with pytest.raises(RuntimeError, match="kaboom"):
        engine.run(context)


def test_state_is_persisted_as_failed_on_crash(
    run_manager, context, recording_stage_factory, boom_stage_factory
):
    stages = [recording_stage_factory("dummy"), boom_stage_factory("boom")]
    engine = PipelineEngine(stages=stages, run_manager=run_manager)

    with pytest.raises(RuntimeError):
        engine.run(context)

    state = run_manager.load_state(context.run_dir)
    assert state.status == STATUS_FAILED
    assert state.last_stage_index == 1
    assert state.completed_stages == ["dummy"]


def test_completed_stage_artifact_persists_when_later_stage_crashes(
    run_manager, context, recording_stage_factory, boom_stage_factory
):
    stages = [recording_stage_factory("dummy"), boom_stage_factory("boom")]
    engine = PipelineEngine(stages=stages, run_manager=run_manager)

    with pytest.raises(RuntimeError):
        engine.run(context)

    stage1_disk = run_manager.load_stage_result(
        context.run_dir, 1, "dummy"
    )
    assert len(stage1_disk) == 1

    stage2_file = context.run_dir / "stage_02_boom.json"
    assert not stage2_file.exists()


def test_pipeline_failed_event_is_published(
    run_manager, context, recording_stage_factory, boom_stage_factory
):
    bus = EventBus()
    failed_events: list[PipelineFailed] = []
    bus.subscribe(PipelineFailed, failed_events.append)
    finished_events: list[PipelineFinished] = []
    bus.subscribe(PipelineFinished, finished_events.append)

    stages = [recording_stage_factory("dummy"), boom_stage_factory("boom")]
    engine = PipelineEngine(
        stages=stages, run_manager=run_manager, event_bus=bus
    )

    with pytest.raises(RuntimeError):
        engine.run(context)

    assert len(failed_events) == 1
    assert "kaboom" in failed_events[0].error
    assert finished_events == []


def test_stage_started_emitted_but_finished_not_for_crashed_stage(
    run_manager, context, recording_stage_factory, boom_stage_factory
):
    bus = EventBus()
    started: list[StageStarted] = []
    finished: list[StageFinished] = []
    bus.subscribe(StageStarted, started.append)
    bus.subscribe(StageFinished, finished.append)

    stages = [recording_stage_factory("dummy"), boom_stage_factory("boom")]
    engine = PipelineEngine(
        stages=stages, run_manager=run_manager, event_bus=bus
    )

    with pytest.raises(RuntimeError):
        engine.run(context)

    assert [e.stage_index for e in started] == [1, 2]
    assert [e.stage_index for e in finished] == [1]


def test_resume_after_failure_continues_from_failed_stage(
    run_manager, context, recording_stage_factory, boom_stage_factory
):
    """Crash → fix the broken stage → resume runs only the tail."""
    first = recording_stage_factory("dummy")
    broken = boom_stage_factory("segmentation")
    engine = PipelineEngine(
        stages=[first, broken], run_manager=run_manager
    )

    with pytest.raises(RuntimeError):
        engine.run(context)

    persisted_state = run_manager.load_state(context.run_dir)
    assert persisted_state.status == STATUS_FAILED
    assert persisted_state.last_stage_index == 1

    fixed = recording_stage_factory("segmentation")
    initial_segments = run_manager.load_stage_result(
        context.run_dir, 1, "dummy"
    )
    engine2 = PipelineEngine(
        stages=[recording_stage_factory("dummy"), fixed],
        run_manager=run_manager,
    )
    segments = engine2.run(
        context,
        initial_segments=initial_segments,
        state=persisted_state,
    )

    assert fixed.calls == 1
    assert len(segments) == 2

    final_state = run_manager.load_state(context.run_dir)
    assert final_state.status == STATUS_COMPLETED
    assert final_state.last_stage_index == 2
    assert final_state.completed_stages == ["dummy", "segmentation"]
