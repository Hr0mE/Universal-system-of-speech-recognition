from __future__ import annotations

from core.models.base import ASRModel, DiarizationModel, LanguageModel
from core.pipeline.context import PipelineContext, Segment


class DummyASR(ASRModel):
    name = "dummy"

    def transcribe(self, segment: Segment, context: PipelineContext) -> str:
        return (
            f"[dummy asr {segment.start_time:.1f}-{segment.end_time:.1f}s]"
        )


class DummyLanguageModel(LanguageModel):
    name = "dummy"

    def __init__(self, language: str = "en") -> None:
        self.language = language

    def detect(self, segment: Segment, context: PipelineContext) -> str:
        return self.language


class DummyDiarization(DiarizationModel):
    name = "dummy"

    def diarize(self, context: PipelineContext) -> list[Segment]:
        return [
            Segment(
                start_time=0.0,
                end_time=context.audio_duration,
                speaker_id="S1",
            )
        ]
