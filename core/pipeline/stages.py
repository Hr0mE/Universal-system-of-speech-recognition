from __future__ import annotations

import logging
from dataclasses import replace
from typing import TYPE_CHECKING

from core.events.events import ProgressUpdated
from core.pipeline.context import PipelineContext, Segment
from core.pipeline.retry import retry_on_error
from core.pipeline.stage import Stage

logger = logging.getLogger(__name__)

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


class MinDurationFilterStage(Stage):
    """Drops segments shorter than `min_seconds`.

    Placed after DiarizationStage to remove sub-word speaker turns that cause
    LID mis-detections and Whisper hallucinations.
    """

    name = "min_duration_filter"

    def __init__(self, min_seconds: float = 0.3) -> None:
        if min_seconds <= 0:
            raise ValueError("min_seconds must be > 0")
        self.min_seconds = min_seconds

    def run(
        self,
        segments: list[Segment],
        _context: PipelineContext,
    ) -> list[Segment]:
        return [s for s in segments if s.end_time - s.start_time >= self.min_seconds]


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
    """Fills `segment.language` for every segment using a LanguageModel.

    On failure, keeps the segment with language=None so ASR can still run
    it with the default model.
    """

    name = "language_detection"

    def __init__(self, model: "LanguageModel", retries: int = 3) -> None:
        self.model = model
        self.retries = retries

    def run(
        self,
        segments: list[Segment],
        context: PipelineContext,
    ) -> list[Segment]:
        result: list[Segment] = []
        for s in segments:
            lang = retry_on_error(
                lambda seg=s: self.model.detect(seg, context),
                retries=self.retries,
                logger=logger,
            )
            if lang is None:
                logger.warning(
                    "Language detection failed for segment [%.2f, %.2f], keeping with language=None",
                    s.start_time, s.end_time,
                )
            result.append(replace(s, language=lang))
        return result


class ASRStage(Stage):
    """Fills `segment.text` for every segment using an ASRModel.

    If `lang_models` is provided, segments are dispatched to the matching
    model by `segment.language`; unknown or None languages fall back to
    `model`.
    """

    name = "asr"

    def __init__(
        self,
        model: "ASRModel",
        lang_models: "dict[str, ASRModel] | None" = None,
        retries: int = 3,
    ) -> None:
        self.model = model
        self.lang_models: dict[str, "ASRModel"] = lang_models or {}
        self.retries = retries

    def run(
        self,
        segments: list[Segment],
        context: PipelineContext,
    ) -> list[Segment]:
        total = len(segments)
        result: list[Segment] = []
        for i, s in enumerate(segments, start=1):
            asr = self.lang_models.get(s.language or "", self.model)
            text = retry_on_error(
                lambda seg=s, m=asr: m.transcribe(seg, context),
                retries=self.retries,
                logger=logger,
            )
            if text is None:
                logger.warning(
                    "ASR failed for segment [%.2f, %.2f], skipping",
                    s.start_time, s.end_time,
                )
            elif text:
                result.append(replace(s, text=text))
            if context.event_bus is not None:
                context.event_bus.publish(
                    ProgressUpdated(
                        run_id=context.run_id,
                        stage_index=context.current_stage_index,
                        stage_name=self.name,
                        current=i,
                        total=total,
                    )
                )
        return result
