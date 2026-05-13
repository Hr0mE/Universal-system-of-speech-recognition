from __future__ import annotations

from pathlib import Path

import pytest

from core.pipeline.context import PipelineContext, Segment
from core.pipeline.stages import (
    ASRStage,
    DiarizationStage,
    MinDurationFilterStage,
    FixedWindowSegmentationStage,
)


def _ctx() -> PipelineContext:
    return PipelineContext(
        run_id="r1",
        audio_path=Path("/tmp/fake.wav"),
        run_dir=Path("/tmp/r1"),
        audio_duration=60.0,
    )


def _seg(start: float, end: float, text: str = "") -> Segment:
    return Segment(start_time=start, end_time=end, text=text)


# ---------------------------------------------------------------------------
# MinDurationFilterStage
# ---------------------------------------------------------------------------


def test_filter_removes_short_segments():
    stage = MinDurationFilterStage(min_seconds=0.3)
    segments = [
        _seg(0.0, 0.1),   # 100 ms — drop
        _seg(0.1, 0.29),  # 190 ms — drop
        _seg(0.3, 0.6),   # 300 ms — keep
        _seg(1.0, 2.0),   # 1 s   — keep
    ]
    result = stage.run(segments, _ctx())
    assert len(result) == 2
    assert result[0] == _seg(0.3, 0.6)
    assert result[1] == _seg(1.0, 2.0)


def test_filter_keeps_segment_exactly_at_threshold():
    stage = MinDurationFilterStage(min_seconds=0.3)
    seg = _seg(0.0, 0.3)
    assert stage.run([seg], _ctx()) == [seg]


def test_filter_empty_input():
    assert MinDurationFilterStage().run([], _ctx()) == []


def test_filter_all_pass():
    stage = MinDurationFilterStage(min_seconds=0.1)
    segments = [_seg(0.0, 1.0), _seg(1.0, 2.0)]
    assert stage.run(segments, _ctx()) == segments


def test_filter_all_dropped():
    stage = MinDurationFilterStage(min_seconds=1.0)
    segments = [_seg(0.0, 0.1), _seg(0.1, 0.5)]
    assert stage.run(segments, _ctx()) == []


def test_filter_invalid_threshold():
    with pytest.raises(ValueError):
        MinDurationFilterStage(min_seconds=0.0)
    with pytest.raises(ValueError):
        MinDurationFilterStage(min_seconds=-1.0)


def test_filter_preserves_segment_fields():
    stage = MinDurationFilterStage(min_seconds=0.3)
    seg = Segment(
        start_time=0.0, end_time=1.0,
        speaker_id="SPEAKER_00", language="en", text="hello",
    )
    assert stage.run([seg], _ctx()) == [seg]


# ---------------------------------------------------------------------------
# ASRStage empty-text filter
# ---------------------------------------------------------------------------


class _ASRStub:
    def __init__(self, texts: list[str]) -> None:
        self._texts = iter(texts)

    def transcribe(self, segment, context):
        return next(self._texts)


def test_asr_drops_empty_text():
    model = _ASRStub(["hello", "", "world", ""])
    stage = ASRStage(model=model)
    segments = [_seg(0.0, 1.0)] * 4
    result = stage.run(segments, _ctx())
    assert len(result) == 2
    assert result[0].text == "hello"
    assert result[1].text == "world"


def test_asr_all_empty_returns_empty_list():
    model = _ASRStub(["", ""])
    stage = ASRStage(model=model)
    result = stage.run([_seg(0.0, 1.0), _seg(1.0, 2.0)], _ctx())
    assert result == []


def test_asr_no_empty_unchanged():
    model = _ASRStub(["a", "b"])
    stage = ASRStage(model=model)
    segs = [_seg(0.0, 1.0), _seg(1.0, 2.0)]
    result = stage.run(segs, _ctx())
    assert [s.text for s in result] == ["a", "b"]


# ---------------------------------------------------------------------------
# build_stages integration
# ---------------------------------------------------------------------------


def test_build_stages_inserts_filter_after_diarization():
    from core.config.models_config import ModelsConfig
    from core.models import default_registry
    from main import build_stages

    cfg = ModelsConfig.from_dict(
        {"asr": "dummy", "language_detection": "dummy", "diarization": "dummy"}
    )
    stages = build_stages(30.0, cfg, default_registry())
    assert isinstance(stages[0], DiarizationStage)
    assert isinstance(stages[1], MinDurationFilterStage)


def test_build_stages_no_filter_without_diarization():
    from core.config.models_config import ModelsConfig
    from core.models import default_registry
    from main import build_stages

    cfg = ModelsConfig.from_dict({"asr": "dummy", "language_detection": "dummy"})
    stages = build_stages(30.0, cfg, default_registry())
    assert isinstance(stages[0], FixedWindowSegmentationStage)
    assert not any(isinstance(s, MinDurationFilterStage) for s in stages)
