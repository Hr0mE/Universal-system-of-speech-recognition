from __future__ import annotations

from core.events.bus import EventBus
from core.events.events import (
    PipelineFinished,
    PipelineStarted,
    StageFinished,
    StageSkipped,
    StageStarted,
)
from core.pipeline.engine import PipelineEngine
from core.pipeline.state import (
    STATUS_COMPLETED,
    PipelineState,
)


def collect_events(bus: EventBus) -> list:
    received: list = []
    for event_type in (
        PipelineStarted,
        PipelineFinished,
        StageStarted,
        StageFinished,
        StageSkipped,
    ):
        bus.subscribe(event_type, received.append)
    return received


def test_fresh_run_executes_all_stages_and_persists(
    run_manager, context, recording_stage_factory
):
    s1 = recording_stage_factory("dummy")
    s2 = recording_stage_factory("segmentation")
    bus = EventBus()
    events = collect_events(bus)

    engine = PipelineEngine(
        stages=[s1, s2], run_manager=run_manager, event_bus=bus
    )
    segments = engine.run(context)

    assert s1.calls == 1
    assert s2.calls == 1
    assert len(segments) == 2

    state = run_manager.load_state(context.run_dir)
    assert state.last_stage_index == 2
    assert state.completed_stages == ["dummy", "segmentation"]
    assert state.status == STATUS_COMPLETED

    stage2_disk = run_manager.load_stage_result(
        context.run_dir, 2, "segmentation"
    )
    assert len(stage2_disk) == 2

    assert any(isinstance(e, PipelineStarted) for e in events)
    assert any(isinstance(e, PipelineFinished) for e in events)
    started_indices = [
        e.stage_index for e in events if isinstance(e, StageStarted)
    ]
    assert started_indices == [1, 2]
    assert not any(isinstance(e, StageSkipped) for e in events)


def test_resume_after_first_stage_skips_first_only(
    run_manager, context, recording_stage_factory
):
    s1 = recording_stage_factory("dummy")
    s2 = recording_stage_factory("segmentation")

    initial_segments = [
        recording_stage_factory("seed").run([], context)[0]
    ]
    state = PipelineState(run_id=context.run_id)
    state.mark_stage_done(1, "dummy")

    bus = EventBus()
    events = collect_events(bus)

    engine = PipelineEngine(
        stages=[s1, s2], run_manager=run_manager, event_bus=bus
    )
    segments = engine.run(
        context, initial_segments=initial_segments, state=state
    )

    assert s1.calls == 0
    assert s2.calls == 1
    assert len(segments) == 2

    skipped = [e for e in events if isinstance(e, StageSkipped)]
    started = [e for e in events if isinstance(e, StageStarted)]
    assert [e.stage_index for e in skipped] == [1]
    assert [e.stage_index for e in started] == [2]

    final_state = run_manager.load_state(context.run_dir)
    assert final_state.last_stage_index == 2
    assert final_state.status == STATUS_COMPLETED


def test_resume_of_fully_completed_run_skips_everything(
    run_manager, context, recording_stage_factory
):
    s1 = recording_stage_factory("dummy")
    s2 = recording_stage_factory("segmentation")
    state = PipelineState(run_id=context.run_id)
    state.mark_stage_done(1, "dummy")
    state.mark_stage_done(2, "segmentation")

    bus = EventBus()
    events = collect_events(bus)

    engine = PipelineEngine(
        stages=[s1, s2], run_manager=run_manager, event_bus=bus
    )
    result = engine.run(context, initial_segments=[], state=state)

    assert s1.calls == 0
    assert s2.calls == 0
    assert result == []

    skipped = [e.stage_index for e in events if isinstance(e, StageSkipped)]
    assert skipped == [1, 2]
    assert not any(isinstance(e, StageStarted) for e in events)
    assert any(isinstance(e, PipelineFinished) for e in events)


def test_engine_works_without_run_manager(
    context, recording_stage_factory
):
    s1 = recording_stage_factory("dummy")
    engine = PipelineEngine(stages=[s1], run_manager=None)
    segments = engine.run(context)
    assert len(segments) == 1
    assert s1.calls == 1
