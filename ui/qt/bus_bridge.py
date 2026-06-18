"""Мост между EventBus pipeline и сигналами Qt.

Преобразует события из worker-потока в Qt-сигналы главного потока через
механизм QueuedConnection.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from core.events.bus import EventBus
from core.events.events import (
    ModelDownloadFinished,
    ModelDownloadStarted,
    PipelineFailed,
    PipelineFinished,
    PipelineStarted,
    ProgressUpdated,
    StageFinished,
    StageSkipped,
    StageStarted,
)


class BusToQtBridge(QObject):
    """Преобразует события EventBus (worker thread) в Qt-сигналы (main thread).

    Экземпляр живёт в главном потоке.  EventBus вызывает обработчики из
    worker-потока — Qt автоматически доставляет сигналы в главный поток
    через QueuedConnection, обеспечивая thread-safety без ручной синхронизации.

    Signals:
        pipeline_started: total_stages, resume_after.
        stage_started: stage_index, stage_name.
        stage_done: stage_index, stage_name, n_segments.
        stage_skipped: stage_index, stage_name.
        pipeline_done: n_segments.
        pipeline_failed: error_message.
        model_downloading: model_name, repo_id.
        model_ready: model_name.
        progress_updated: stage_index, current, total.
    """

    pipeline_started = Signal(int, int)   # total_stages, resume_after
    stage_started = Signal(int, str)      # index, name
    stage_done = Signal(int, str, int)    # index, name, n_segments
    stage_skipped = Signal(int, str)      # index, name
    pipeline_done = Signal(int)           # n_segments
    pipeline_failed = Signal(str)         # error message
    model_downloading = Signal(str, str)  # model_name, repo_id
    model_ready = Signal(str)             # model_name
    progress_updated = Signal(int, int, int)  # stage_index, current, total

    def __init__(self) -> None:
        """Инициализирует мост и подписывается на все события pipeline."""
        super().__init__()
        self.bus = EventBus()
        self.bus.subscribe(
            PipelineStarted,
            lambda e: self.pipeline_started.emit(e.total_stages, e.resume_after),
        )
        self.bus.subscribe(
            StageStarted,
            lambda e: self.stage_started.emit(e.stage_index, e.stage_name),
        )
        self.bus.subscribe(
            StageFinished,
            lambda e: self.stage_done.emit(e.stage_index, e.stage_name, e.segments_count),
        )
        self.bus.subscribe(
            StageSkipped,
            lambda e: self.stage_skipped.emit(e.stage_index, e.stage_name),
        )
        self.bus.subscribe(
            PipelineFinished,
            lambda e: self.pipeline_done.emit(e.segments_count),
        )
        self.bus.subscribe(
            PipelineFailed,
            lambda e: self.pipeline_failed.emit(e.error),
        )
        self.bus.subscribe(
            ModelDownloadStarted,
            lambda e: self.model_downloading.emit(e.model_name, e.repo_id),
        )
        self.bus.subscribe(
            ModelDownloadFinished,
            lambda e: self.model_ready.emit(e.model_name),
        )
        self.bus.subscribe(
            ProgressUpdated,
            lambda e: self.progress_updated.emit(e.stage_index, e.current, e.total),
        )
