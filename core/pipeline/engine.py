from __future__ import annotations

import logging
from typing import Iterable

from core.pipeline.context import PipelineContext, Segment
from core.pipeline.stage import Stage

logger = logging.getLogger(__name__)


class PipelineEngine:
    def __init__(self, stages: Iterable[Stage]):
        self.stages: list[Stage] = list(stages)

    def run(
        self,
        context: PipelineContext,
        initial_segments: list[Segment] | None = None,
    ) -> list[Segment]:
        segments: list[Segment] = list(initial_segments or [])
        logger.info(
            "Pipeline started: run_id=%s, audio=%s",
            context.run_id,
            context.audio_path,
        )
        for stage in self.stages:
            logger.info("Stage start: %s", stage.name)
            segments = stage.run(segments, context)
            logger.info(
                "Stage done:  %s (segments=%d)", stage.name, len(segments)
            )
        logger.info("Pipeline finished: run_id=%s", context.run_id)
        return segments
