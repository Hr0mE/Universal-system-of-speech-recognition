from __future__ import annotations

import json
import logging

from core.pipeline.context import PipelineContext, Segment
from core.pipeline.stage import Stage

logger = logging.getLogger(__name__)


class DummyStage(Stage):
    name = "dummy"

    def run(
        self,
        segments: list[Segment],
        context: PipelineContext,
    ) -> list[Segment]:
        logger.info("DummyStage: passing through %d segments", len(segments))
        return segments


class FixedWindowSegmentationStage(Stage):
    """Cuts the audio timeline into fixed-length windows.

    Stage 1: produces only time intervals — the audio file itself is not sliced.
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

        out_path = context.run_dir / "segments.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps(
                [s.to_dict() for s in result], indent=2, ensure_ascii=False
            ),
            encoding="utf-8",
        )
        logger.info(
            "Segmentation produced %d segments → %s", len(result), out_path
        )
        return result
