from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, call

import pytest

from core.pipeline.context import PipelineContext, Segment
from core.pipeline.stages import ASRStage, LanguageDetectionStage


def _ctx() -> PipelineContext:
    return PipelineContext(
        run_id="r1",
        audio_path=Path("/tmp/fake.wav"),
        run_dir=Path("/tmp/r1"),
        audio_duration=60.0,
    )


def _seg(start: float = 0.0, end: float = 1.0) -> Segment:
    return Segment(start_time=start, end_time=end)


# ---------------------------------------------------------------------------
# retry_on_error utility
# ---------------------------------------------------------------------------


def test_retry_succeeds_on_first_try():
    from core.pipeline.retry import retry_on_error

    fn = MagicMock(return_value="ok")
    assert retry_on_error(fn, retries=3) == "ok"
    fn.assert_called_once()


def test_retry_succeeds_on_second_try():
    from core.pipeline.retry import retry_on_error

    fn = MagicMock(side_effect=[RuntimeError("boom"), "ok"])
    assert retry_on_error(fn, retries=3) == "ok"
    assert fn.call_count == 2


def test_retry_returns_none_after_all_failed():
    from core.pipeline.retry import retry_on_error

    fn = MagicMock(side_effect=RuntimeError("boom"))
    assert retry_on_error(fn, retries=3) is None


def test_retry_calls_fn_n_times_on_failure():
    from core.pipeline.retry import retry_on_error

    fn = MagicMock(side_effect=RuntimeError("boom"))
    retry_on_error(fn, retries=3)
    assert fn.call_count == 3


def test_retry_zero_retries_raises():
    from core.pipeline.retry import retry_on_error

    with pytest.raises(ValueError, match="retries"):
        retry_on_error(MagicMock(), retries=0)


# ---------------------------------------------------------------------------
# ASRStage — retry + skip on failure
# ---------------------------------------------------------------------------


class _RaisingASR:
    """Always raises on transcribe."""
    def transcribe(self, segment, context):
        raise RuntimeError("model error")


class _FlakyASR:
    """Raises on first call, succeeds on second."""
    def __init__(self, success_text: str = "hello"):
        self._calls = 0
        self._text = success_text

    def transcribe(self, segment, context):
        self._calls += 1
        if self._calls == 1:
            raise RuntimeError("first attempt failed")
        return self._text


class _GoodASR:
    def __init__(self, text: str):
        self._text = text

    def transcribe(self, segment, context):
        return self._text


def test_asr_skips_segment_on_persistent_failure():
    stage = ASRStage(model=_RaisingASR(), retries=3)
    result = stage.run([_seg()], _ctx())
    assert result == []


def test_asr_retries_and_succeeds():
    stage = ASRStage(model=_FlakyASR("hello"), retries=3)
    result = stage.run([_seg()], _ctx())
    assert len(result) == 1
    assert result[0].text == "hello"


def test_asr_other_segments_unaffected_by_one_failure():
    class _SelectiveASR:
        def __init__(self):
            self._calls = 0

        def transcribe(self, segment, context):
            self._calls += 1
            if segment.start_time == 0.0:
                raise RuntimeError("bad segment")
            return "good"

    stage = ASRStage(model=_SelectiveASR(), retries=1)
    segments = [_seg(0.0, 1.0), _seg(1.0, 2.0), _seg(2.0, 3.0)]
    result = stage.run(segments, _ctx())
    assert len(result) == 2
    assert all(s.text == "good" for s in result)


def test_asr_retries_configurable():
    fn = MagicMock(side_effect=RuntimeError("boom"))

    class _TrackingASR:
        def transcribe(self, segment, context):
            return fn()

    stage = ASRStage(model=_TrackingASR(), retries=1)
    stage.run([_seg()], _ctx())
    assert fn.call_count == 1


# ---------------------------------------------------------------------------
# LanguageDetectionStage — retry + keep with language=None on failure
# ---------------------------------------------------------------------------


class _RaisingLID:
    def detect(self, segment, context):
        raise RuntimeError("lid error")


class _FlakyLID:
    def __init__(self, lang: str = "en"):
        self._calls = 0
        self._lang = lang

    def detect(self, segment, context):
        self._calls += 1
        if self._calls == 1:
            raise RuntimeError("first attempt failed")
        return self._lang


class _GoodLID:
    def __init__(self, lang: str):
        self._lang = lang

    def detect(self, segment, context):
        return self._lang


def test_lid_keeps_segment_on_failure():
    stage = LanguageDetectionStage(model=_RaisingLID(), retries=3)
    result = stage.run([_seg()], _ctx())
    assert len(result) == 1
    assert result[0].language is None


def test_lid_retries_and_succeeds():
    stage = LanguageDetectionStage(model=_FlakyLID("ru"), retries=3)
    result = stage.run([_seg()], _ctx())
    assert len(result) == 1
    assert result[0].language == "ru"


def test_lid_other_segments_unaffected():
    class _SelectiveLID:
        def detect(self, segment, context):
            if segment.start_time == 0.0:
                raise RuntimeError("bad segment")
            return "en"

    stage = LanguageDetectionStage(model=_SelectiveLID(), retries=1)
    segments = [_seg(0.0, 1.0), _seg(1.0, 2.0), _seg(2.0, 3.0)]
    result = stage.run(segments, _ctx())
    assert len(result) == 3
    assert result[0].language is None
    assert result[1].language == "en"
    assert result[2].language == "en"
