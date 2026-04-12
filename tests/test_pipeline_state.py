from __future__ import annotations

from core.pipeline.state import (
    STATUS_COMPLETED,
    STATUS_PENDING,
    PipelineState,
)


def test_new_state_is_pending_with_zero_index():
    state = PipelineState(run_id="r1")
    assert state.status == STATUS_PENDING
    assert state.last_stage_index == 0
    assert state.completed_stages == []


def test_mark_stage_done_updates_index_and_names():
    state = PipelineState(run_id="r1")
    state.mark_stage_done(1, "dummy")
    state.mark_stage_done(2, "segmentation")

    assert state.last_stage_index == 2
    assert state.completed_stages == ["dummy", "segmentation"]


def test_mark_stage_done_does_not_duplicate_name():
    state = PipelineState(run_id="r1")
    state.mark_stage_done(1, "dummy")
    state.mark_stage_done(1, "dummy")

    assert state.completed_stages == ["dummy"]
    assert state.last_stage_index == 1


def test_to_dict_from_dict_roundtrip():
    state = PipelineState(run_id="r1")
    state.mark_stage_done(1, "dummy")
    state.mark_stage_done(2, "segmentation")
    state.status = STATUS_COMPLETED

    restored = PipelineState.from_dict(state.to_dict())

    assert restored == state


def test_from_dict_tolerates_missing_optional_fields():
    restored = PipelineState.from_dict({"run_id": "r1"})

    assert restored.run_id == "r1"
    assert restored.last_stage_index == 0
    assert restored.completed_stages == []
    assert restored.status == STATUS_PENDING
