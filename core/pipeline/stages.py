from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from core.pipeline.context import PipelineContext, Segment
from core.pipeline.stage import Stage

if TYPE_CHECKING:
    from core.models.base import (
        ASRModel,
        DiarizationModel,
        LanguageModel,
    )


class DummyStage(Stage):
    name = "dummy"

    def run(
        self,
        segments: list[Segment],
        context: PipelineContext,
    ) -> list[Segment]:
        return segments


class FixedWindowSegmentationStage(Stage):
    """Cuts the audio timeline into fixed-length windows.

    Pure transformation: produces time intervals only. Persistence is handled
    by the engine via RunManager.
    """

    name = "segmentation"

    def __init__(self, window_seconds: float = 30.0):
        if window_seconds <= 0:
            raise ValueError("window_seconds must be > 0")
        self.window_seconds = window_seconds

    def run(
        self,
        segments: list[Segment],
        context: PipelineContext,
    ) -> list[Segment]:
        duration = context.audio_duration
        if duration <= 0:
            raise ValueError(
                "PipelineContext.audio_duration must be set before segmentation"
            )

        result: list[Segment] = []
        start = 0.0
        while start < duration:
            end = min(start + self.window_seconds, duration)
            result.append(Segment(start_time=start, end_time=end))
            start = end

        return result


class DiarizationStage(Stage):
    """Produces initial speaker-labelled segments via a DiarizationModel.

    Discards any incoming segments — diarization is a source, not a filter.
    """

    name = "diarization"

    def __init__(self, model: "DiarizationModel") -> None:
        self.model = model

    def run(
        self,
        segments: list[Segment],
        context: PipelineContext,
    ) -> list[Segment]:
        return self.model.diarize(context)


class LanguageDetectionStage(Stage):
    """Fills `segment.language` for every segment using a LanguageModel."""

    name = "language_detection"

    def __init__(self, model: "LanguageModel") -> None:
        self.model = model

    def run(
        self,
        segments: list[Segment],
        context: PipelineContext,
    ) -> list[Segment]:
        return [
            replace(s, language=self.model.detect(s, context))
            for s in segments
        ]


class ASRStage(Stage):
    """Fills `segment.text` for every segment using an ASRModel."""

    name = "asr"

    def __init__(self, model: "ASRModel") -> None:
        self.model = model

    def run(
        self,
        segments: list[Segment],
        context: PipelineContext,
    ) -> list[Segment]:
        return [
            replace(s, text=self.model.transcribe(s, context))
            for s in segments
        ]
