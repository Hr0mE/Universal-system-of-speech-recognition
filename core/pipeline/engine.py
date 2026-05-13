from __future__ import annotations

from typing import TYPE_CHECKING, Iterable

from core.events.bus import EventBus
from core.events.events import (
    PipelineFailed,
    PipelineFinished,
    PipelineStarted,
    StageFinished,
    StageSkipped,
    StageStarted,
)
from core.pipeline.context import PipelineContext, Segment
from core.pipeline.stage import Stage
from core.pipeline.state import (
    STATUS_COMPLETED,
    STATUS_FAILED,
    STATUS_RUNNING,
    PipelineState,
)

if TYPE_CHECKING:
    from core.storage.run_manager import RunManager


class PipelineEngine:
    def __init__(
        self,
        stages: Iterable[Stage],
        run_manager: "RunManager | None" = None,
        event_bus: EventBus | None = None,
    ):
        self.stages: list[Stage] = list(stages)
        self.run_manager = run_manager
        self.event_bus = event_bus or EventBus()

    def run(
        self,
        context: PipelineContext,
        initial_segments: list[Segment] | None = None,
        state: PipelineState | None = None,
    ) -> list[Segment]:
        if state is None:
            state = PipelineState(run_id=context.run_id)
        state.status = STATUS_RUNNING

        segments: list[Segment] = list(initial_segments or [])
        resume_after = state.last_stage_index

        self.event_bus.publish(
            PipelineStarted(
                run_id=context.run_id,
                audio_path=context.audio_path,
                total_stages=len(self.stages),
                resume_after=resume_after,
            )
        )

        if self.run_manager is not None:
            self.run_manager.save_state(context.run_dir, state)

        context.event_bus = self.event_bus

        try:
            for index, stage in enumerate(self.stages, start=1):
                if index <= resume_after:
                    stage.on_stage_skipped(context)
                    self.event_bus.publish(
                        StageSkipped(
                            run_id=context.run_id,
                            stage_index=index,
                            stage_name=stage.name,
                        )
                    )
                    continue

                self.event_bus.publish(
                    StageStarted(
                        run_id=context.run_id,
                        stage_index=index,
                        stage_name=stage.name,
                    )
                )

                context.current_stage_index = index
                segments = stage.run(segments, context)

                state.mark_stage_done(index, stage.name)
                artifact_path = None
                if self.run_manager is not None:
                    artifact_path = self.run_manager.save_stage_result(
                        context.run_dir, index, stage.name, segments
                    )
                    self.run_manager.save_state(context.run_dir, state)

                self.event_bus.publish(
                    StageFinished(
                        run_id=context.run_id,
                        stage_index=index,
                        stage_name=stage.name,
                        segments_count=len(segments),
                        artifact=artifact_path,
                    )
                )

            state.status = STATUS_COMPLETED
        except Exception as exc:
            state.status = STATUS_FAILED
            self.event_bus.publish(
                PipelineFailed(run_id=context.run_id, error=repr(exc))
            )
            raise
        finally:
            if self.run_manager is not None:
                self.run_manager.save_state(context.run_dir, state)

        self.event_bus.publish(
            PipelineFinished(
                run_id=context.run_id, segments_count=len(segments)
            )
        )
        return segments
