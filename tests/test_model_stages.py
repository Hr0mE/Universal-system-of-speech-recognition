from __future__ import annotations

from pathlib import Path

from core.models.base import ASRModel, DiarizationModel, LanguageModel
from core.models.dummy import DummyASR, DummyDiarization, DummyLanguageModel
from core.pipeline.context import PipelineContext, Segment
from core.pipeline.engine import PipelineEngine
from core.pipeline.stages import (
    ASRStage,
    DiarizationStage,
    FixedWindowSegmentationStage,
    LanguageDetectionStage,
)


def _ctx(duration: float = 60.0) -> PipelineContext:
    return PipelineContext(
        run_id="r1",
        audio_path=Path("/tmp/fake.wav"),
        run_dir=Path("/tmp/r1"),
        audio_duration=duration,
    )


class RecordingASR(ASRModel):
    name = "rec-asr"

    def __init__(self) -> None:
        self.calls: list[Segment] = []

    def transcribe(self, segment: Segment, context: PipelineContext) -> str:
        self.calls.append(segment)
        return f"text-{len(self.calls)}"


class RecordingLID(LanguageModel):
    name = "rec-lid"

    def __init__(self, language: str = "xx") -> None:
        self.language = language
        self.calls: list[Segment] = []

    def detect(self, segment: Segment, context: PipelineContext) -> str:
        self.calls.append(segment)
        return self.language


class RecordingDiarization(DiarizationModel):
    name = "rec-diar"

    def __init__(self) -> None:
        self.calls = 0

    def diarize(self, context: PipelineContext) -> list[Segment]:
        self.calls += 1
        return [
            Segment(start_time=0.0, end_time=10.0, speaker_id="A"),
            Segment(start_time=10.0, end_time=20.0, speaker_id="B"),
        ]


def test_dummy_asr_returns_string():
    segment = Segment(start_time=0.0, end_time=5.5)
    assert DummyASR().transcribe(segment, _ctx()) == "[dummy asr 0.0-5.5s]"


def test_dummy_language_model_returns_configured_code():
    segment = Segment(start_time=0.0, end_time=5.0)
    assert DummyLanguageModel().detect(segment, _ctx()) == "en"
    assert DummyLanguageModel(language="ru").detect(segment, _ctx()) == "ru"


def test_dummy_diarization_spans_whole_audio():
    ctx = _ctx(duration=42.5)
    result = DummyDiarization().diarize(ctx)
    assert len(result) == 1
    assert result[0].start_time == 0.0
    assert result[0].end_time == 42.5
    assert result[0].speaker_id == "S1"


def test_language_detection_stage_fills_language_without_mutating_input():
    model = RecordingLID(language="ru")
    stage = LanguageDetectionStage(model=model)
    original = [
        Segment(start_time=0.0, end_time=10.0),
        Segment(start_time=10.0, end_time=20.0),
    ]
    result = stage.run(original, _ctx())

    assert all(s.language == "ru" for s in result)
    assert [s.language for s in original] == [None, None]
    assert len(model.calls) == 2


def test_asr_stage_fills_text_without_mutating_input():
    model = RecordingASR()
    stage = ASRStage(model=model)
    original = [
        Segment(start_time=0.0, end_time=5.0, language="en"),
        Segment(start_time=5.0, end_time=10.0, language="en"),
    ]
    result = stage.run(original, _ctx())

    assert [s.text for s in result] == ["text-1", "text-2"]
    assert [s.language for s in result] == ["en", "en"]
    assert all(s.text is None for s in original)


def test_diarization_stage_discards_incoming_segments():
    model = RecordingDiarization()
    stage = DiarizationStage(model=model)
    stale = [Segment(start_time=0.0, end_time=999.0, speaker_id="STALE")]

    result = stage.run(stale, _ctx(duration=20.0))

    assert model.calls == 1
    assert [s.speaker_id for s in result] == ["A", "B"]


def test_pipeline_with_dummy_models_end_to_end(run_manager, context):
    stages = [
        FixedWindowSegmentationStage(window_seconds=15.0),
        LanguageDetectionStage(model=DummyLanguageModel(language="ru")),
        ASRStage(model=DummyASR()),
    ]
    engine = PipelineEngine(stages=stages, run_manager=run_manager)
    result = engine.run(context)

    assert len(result) == 4
    assert all(s.language == "ru" for s in result)
    assert all(s.text and s.text.startswith("[dummy asr") for s in result)

    asr_disk = run_manager.load_stage_result(context.run_dir, 3, "asr")
    assert [s.text for s in asr_disk] == [s.text for s in result]


def test_asr_model_swap_requires_no_pipeline_changes(run_manager, context):
    """Stage 5 acceptance: swap model, pipeline wiring stays identical."""

    class UpperCaseASR(ASRModel):
        name = "upper-asr"

        def transcribe(self, segment: Segment, context: PipelineContext) -> str:
            return "WORD"

    def build(asr: ASRModel):
        return [
            FixedWindowSegmentationStage(window_seconds=30.0),
            LanguageDetectionStage(model=DummyLanguageModel()),
            ASRStage(model=asr),
        ]

    engine_a = PipelineEngine(
        stages=build(DummyASR()), run_manager=run_manager
    )
    result_a = engine_a.run(context)

    engine_b = PipelineEngine(
        stages=build(UpperCaseASR()), run_manager=run_manager
    )
    result_b = engine_b.run(context)

    assert all(s.text and s.text.startswith("[dummy") for s in result_a)
    assert all(s.text == "WORD" for s in result_b)
