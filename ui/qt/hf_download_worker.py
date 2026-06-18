"""Фоновые QThread-воркеры для поиска и скачивания моделей с HuggingFace Hub.

Изолируют сетевые операции от главного потока Qt, передавая результаты
через сигналы. Используют ``core.hf_catalog`` для поиска.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QThread, Signal

from core.hf_catalog import CatalogModel, search_models

_log = logging.getLogger("ui.hf_worker")

# Маппинг UI-типа модели → HuggingFace pipeline_tag
TASK_TO_HF_TAG: dict[str, str] = {
    "asr":         "automatic-speech-recognition",
    "language":    "audio-classification",
    "diarization": "audio-classification",
}


class HFSearchWorker(QThread):
    """Ищет модели на HuggingFace Hub по pipeline_tag и языку.

    Signals:
        results_ready: Отправляется со списком :class:`~core.hf_catalog.CatalogModel`
            при успешном поиске.
        search_error: Отправляется со строкой ошибки при неудаче.
    """

    results_ready = Signal(list)   # list[CatalogModel]
    search_error  = Signal(str)

    def __init__(
        self,
        pipeline_tag: str,
        language: str = "",
        token: str = "",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.pipeline_tag = pipeline_tag
        self.language     = language.strip() or None
        self.token        = token.strip() or None

    def run(self) -> None:
        _log.info("HFSearchWorker: tag=%s lang=%s", self.pipeline_tag, self.language)
        try:
            results = search_models(
                pipeline_tag=self.pipeline_tag,
                language=self.language,
                token=self.token,
                limit=30,
            )
            self.results_ready.emit(results)
        except Exception as exc:
            _log.error("HFSearchWorker: error: %s", exc)
            self.search_error.emit(str(exc))


class HFDownloadWorker(QThread):
    """Скачивает snapshot модели с HuggingFace Hub в фоновом потоке.

    Сохраняет модель в стандартный кэш HuggingFace
    (``~/.cache/huggingface/hub``).

    Signals:
        started_dl:  Эмитируется с repo_id сразу перед началом скачивания.
        finished_dl: Эмитируется с repo_id при успешном завершении.
        error_dl:    Эмитируется с (repo_id, error_message) при ошибке.
    """

    started_dl  = Signal(str)        # repo_id
    finished_dl = Signal(str)        # repo_id
    error_dl    = Signal(str, str)   # repo_id, error_message
    progress_dl = Signal(str, int)   # repo_id, percent (0-100; -1 = indeterminate)

    def __init__(
        self,
        repo_id: str,
        token: Optional[str] = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.repo_id       = repo_id
        self.token         = token or None
        self._total_bytes  = 0
        self._stop_monitor = False

    def run(self) -> None:
        self.started_dl.emit(self.repo_id)
        _log.info("HFDownloadWorker: start  repo=%s", self.repo_id)
        self._stop_monitor = False
        monitor = threading.Thread(target=self._monitor_progress, daemon=True)
        try:
            from huggingface_hub import model_info as hf_model_info, snapshot_download
            try:
                info = hf_model_info(self.repo_id, token=self.token)
                self._total_bytes = sum((s.size or 0) for s in (info.siblings or []))
            except Exception:
                self._total_bytes = 0
            monitor.start()
            snapshot_download(repo_id=self.repo_id, token=self.token)
            _log.info("HFDownloadWorker: done   repo=%s", self.repo_id)
            self.progress_dl.emit(self.repo_id, 100)
            self.finished_dl.emit(self.repo_id)
        except Exception as exc:
            _log.error("HFDownloadWorker: error  repo=%s  err=%s", self.repo_id, exc)
            self.error_dl.emit(self.repo_id, str(exc))
        finally:
            self._stop_monitor = True
            if monitor.is_alive():
                monitor.join(timeout=2.0)

    def cancel(self) -> None:
        """Stop the monitor thread then forcefully terminate the download thread."""
        self._stop_monitor = True
        self.terminate()

    def _monitor_progress(self) -> None:
        """Polls the HF cache directory size every 500 ms and emits progress_dl."""
        while not self._stop_monitor:
            if self._total_bytes > 0:
                downloaded = self._get_downloaded_size()
                pct = min(99, int(100 * downloaded / self._total_bytes))
                self.progress_dl.emit(self.repo_id, pct)
            else:
                self.progress_dl.emit(self.repo_id, -1)
            time.sleep(0.5)

    def _get_downloaded_size(self) -> int:
        """Sum of bytes in the HF hub cache directory for this repo."""
        sanitized = self.repo_id.replace("/", "--")
        cache_dir = (
            Path.home() / ".cache" / "huggingface" / "hub" / f"models--{sanitized}"
        )
        total = 0
        try:
            for root, _, files in os.walk(cache_dir):
                for fname in files:
                    try:
                        total += os.path.getsize(os.path.join(root, fname))
                    except OSError:
                        pass
        except OSError:
            pass
        return total
