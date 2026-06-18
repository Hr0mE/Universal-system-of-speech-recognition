"""Фоновые QThread-воркеры для транскрибации.

Изолируют ML-pipeline от главного потока Qt, передавая результаты через сигналы.
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from core.api.transcribe import (
    PipelineCancelled,
    TranscriptionResult,
    resume_transcription,
    transcribe,
)
from core.config.pipeline_config import PipelineConfig
from ui.qt.bus_bridge import BusToQtBridge

_log = logging.getLogger("ui.worker")


class TranscribeWorker(QThread):
    """Запускает :func:`transcribe` в фоновом потоке, отправляя сигналы по завершении.

    Signals:
        result_ready: Отправляется с :class:`TranscriptionResult` при успехе.
        failed: Отправляется с сообщением об ошибке при исключении.
    """

    result_ready = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        audio_path: Path,
        models_config: PipelineConfig,
        bridge: BusToQtBridge,
        runs_dir: Path,
    ) -> None:
        """Инициализирует воркер транскрибации.

        Args:
            audio_path (Path): Путь к WAV-файлу для транскрибации.
            models_config (PipelineConfig): Конфигурация пайплайна.
            bridge (BusToQtBridge): Мост EventBus → Qt сигналы.
            runs_dir (Path): Директория для хранения артефактов.
        """
        super().__init__()
        self.audio_path = audio_path
        self.models_config = models_config
        self.bridge = bridge
        self.runs_dir = runs_dir
        self.stop_requested = threading.Event()

    def run(self) -> None:
        """Выполняет транскрибацию и эмитирует result_ready или failed."""
        _log.info("TranscribeWorker: старт  audio=%s", self.audio_path)
        try:
            result = transcribe(
                self.audio_path,
                models_config=self.models_config,
                runs_dir=self.runs_dir,
                event_bus=self.bridge.bus,
                stop_requested=self.stop_requested,
            )
            _log.info("TranscribeWorker: завершён  run_id=%s", result.run_id)
            self.result_ready.emit(result)
        except PipelineCancelled:
            _log.info("TranscribeWorker: остановлен кооперативно после текущего сегмента")
        except Exception as exc:
            _log.error("TranscribeWorker: ОШИБКА  %s: %s", type(exc).__name__, exc, exc_info=True)
            self.failed.emit(str(exc))


class ResumeWorker(QThread):
    """Возобновляет прерванный запуск транскрибации с последнего чекпоинта.

    Signals:
        result_ready: Отправляется с :class:`TranscriptionResult` при успехе.
        failed: Отправляется с сообщением об ошибке при исключении.
    """

    result_ready = Signal(object)
    failed       = Signal(str)

    def __init__(
        self,
        run_dir: Path,
        models_config: PipelineConfig,
        bridge: BusToQtBridge,
    ) -> None:
        """Инициализирует воркер возобновления.

        Args:
            run_dir (Path): Директория прерванного запуска.
            models_config (PipelineConfig): Конфигурация пайплайна.
            bridge (BusToQtBridge): Мост EventBus → Qt сигналы.
        """
        super().__init__()
        self.run_dir        = run_dir
        self.models_config  = models_config
        self.bridge         = bridge
        self.stop_requested = threading.Event()

    def run(self) -> None:
        """Возобновляет транскрибацию и эмитирует result_ready или failed."""
        _log.info("ResumeWorker: старт  run_dir=%s", self.run_dir)
        try:
            result = resume_transcription(
                self.run_dir,
                self.models_config,
                event_bus=self.bridge.bus,
                stop_requested=self.stop_requested,
            )
            _log.info("ResumeWorker: завершён  run_id=%s", result.run_id)
            self.result_ready.emit(result)
        except PipelineCancelled:
            _log.info("ResumeWorker: остановлен кооперативно после текущего сегмента")
        except Exception as exc:
            _log.error("ResumeWorker: ОШИБКА  %s: %s", type(exc).__name__, exc, exc_info=True)
            self.failed.emit(str(exc))
