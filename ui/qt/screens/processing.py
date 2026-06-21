"""Экран обработки аудио с отображением прогресса pipeline.

Управляет запуском TranscribeWorker и ResumeWorker через QThread,
отображает прогресс по стадиям и сегментам через BusToQtBridge.
"""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt, Signal
from PySide6.QtWidgets import (
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.config.pipeline_config import PipelineConfig
from ui.qt.bus_bridge import BusToQtBridge
from ui.qt.scale_manager import load_ui_scale
from ui.qt.worker import ResumeWorker, TranscribeWorker

_log = logging.getLogger("ui.processing")


class _StageTimeline(QWidget):
    """Горизонтальный таймлайн этапов пайплайна.

    Этапы создаются через setup(count), имена уточняются через update_name(index, name).
    Активный этап получает тихий opacity-pulse (SineCurve, 900 мс).
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._hbox = QHBoxLayout(self)
        self._hbox.setContentsMargins(0, 4, 0, 4)
        self._hbox.setSpacing(4)
        self._pills: list[QLabel] = []
        self._active_anim: QPropertyAnimation | None = None
        self._active_effect: QGraphicsOpacityEffect | None = None

    # ── public API ──────────────────────────────────────────────────────

    def setup(self, count: int) -> None:
        """Создаёт count безымянных pill-ов; имена обновляются через update_name."""
        self._clear()
        for i in range(count):
            if i > 0:
                sep = QLabel("→")
                sep.setObjectName("stage_sep")
                self._hbox.addWidget(sep)
            pill = QLabel(f"○  Этап {i + 1}")
            pill.setObjectName("stage_pill")
            pill.setProperty("stage_state", "pending")
            self._hbox.addWidget(pill)
            self._pills.append(pill)
        self._hbox.addStretch()

    def update_name(self, index: int, name: str) -> None:
        """Обновить текст pill-а (1-based). Сохраняет текущий state-префикс."""
        if not (0 < index <= len(self._pills)):
            return
        pill = self._pills[index - 1]
        state = pill.property("stage_state") or "pending"
        prefix = {"done": "✓", "active": "▶", "error": "⚠"}.get(state, "○")
        pill.setText(f"{prefix}  {name}")

    def mark_active(self, index: int) -> None:
        """Пометить этап активным + запустить тихий opacity-pulse."""
        self._stop_anim()
        if not (0 < index <= len(self._pills)):
            return
        pill = self._pills[index - 1]
        self._set_pill_prefix(pill, "▶", "active")
        effect = QGraphicsOpacityEffect(pill)
        pill.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity", self)
        anim.setDuration(900)
        anim.setStartValue(1.0)
        anim.setEndValue(0.35)
        anim.setEasingCurve(QEasingCurve.Type.SineCurve)
        anim.setLoopCount(-1)
        anim.start()
        self._active_anim = anim
        self._active_effect = effect

    def mark_done(self, index: int) -> None:
        """Завершить этап. Останавливает pulse если был активен."""
        self._stop_anim()
        if not (0 < index <= len(self._pills)):
            return
        pill = self._pills[index - 1]
        pill.setGraphicsEffect(None)
        self._set_pill_prefix(pill, "✓", "done")

    def mark_error(self) -> None:
        """Отметить текущий активный этап как ошибочный."""
        self._stop_anim()
        for pill in self._pills:
            if pill.property("stage_state") == "active":
                pill.setGraphicsEffect(None)
                self._set_pill_prefix(pill, "⚠", "error")
                break

    def mark_all_done(self) -> None:
        """Пометить все этапы завершёнными (pipeline_done)."""
        self._stop_anim()
        for pill in self._pills:
            pill.setGraphicsEffect(None)
            self._set_pill_prefix(pill, "✓", "done")

    def freeze(self) -> None:
        """Остановить pulse-анимацию, зафиксировав активный pill в ярком положении."""
        self._stop_anim()

    def reset(self) -> None:
        """Сбросить все pill-ы в pending."""
        self._stop_anim()
        for pill in self._pills:
            pill.setGraphicsEffect(None)
            self._set_pill_prefix(pill, "○", "pending")

    # ── private ─────────────────────────────────────────────────────────

    def _clear(self) -> None:
        self._stop_anim()
        while self._hbox.count():
            item = self._hbox.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()
        self._pills.clear()

    @staticmethod
    def _set_pill_prefix(pill: QLabel, prefix: str, state: str) -> None:
        text = pill.text()
        parts = text.split("  ", 1)
        name = parts[1] if len(parts) == 2 else text
        pill.setText(f"{prefix}  {name}")
        pill.setProperty("stage_state", state)
        pill.style().unpolish(pill)
        pill.style().polish(pill)

    def _stop_anim(self) -> None:
        if self._active_anim:
            self._active_anim.stop()
            self._active_anim = None
        if self._active_effect:
            self._active_effect.setOpacity(1.0)
            self._active_effect = None


class ProcessingScreen(QWidget):
    """Экран отображения прогресса транскрибации.

    Запускает TranscribeWorker или ResumeWorker в QThread,
    соединяет BusToQtBridge с индикаторами прогресса по стадиям и сегментам.

    Signals:
        processing_finished: TranscriptionResult — pipeline завершился успешно.
        back_requested: пользователь хочет вернуться к экрану приветствия.
        resume_requested: audio_path — MainWindow должен переключиться на возобновление.
        error_occurred: worker завершился с исключением.
        user_stopped: пользователь нажал кнопку «Остановить».
    """

    processing_finished = Signal(object)  # TranscriptionResult → Step 3
    back_requested      = Signal()        # пользователь → show_welcome()
    resume_requested    = Signal(Path)    # audio_path — просьба возобновить из MainWindow
    error_occurred      = Signal()        # worker упал с исключением
    user_stopped        = Signal()        # пользователь нажал «Остановить»

    def __init__(self, parent: QWidget | None = None) -> None:
        """Инициализирует экран обработки и создаёт виджеты прогресса."""
        super().__init__(parent)
        self._worker: TranscribeWorker | None = None
        self._bridge: BusToQtBridge | None = None
        self._stage_names: list[str] = []
        self._stages_done: set[int] = set()
        self._current_stage: int = 0
        self._last_result = None
        self._current_audio_path: Path | None = None
        self._stop_btn_is_resume: bool = False
        self._build_ui()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self, audio_path: Path, models_config: PipelineConfig) -> None:
        """Запускает новую транскрибацию аудиофайла."""
        self._current_audio_path = audio_path
        self._header_label.setText(audio_path.name)
        self._reset_widgets()
        self._set_status("Запуск…", "running")
        self._reset_stop_btn()
        self._stop_btn.setEnabled(True)
        self._back_btn.setVisible(False)

        self._bridge = BusToQtBridge()
        self._connect_bridge(self._bridge)

        self._worker = TranscribeWorker(audio_path, models_config, self._bridge, Path("runs"))
        self._worker.result_ready.connect(self._on_worker_finished)
        self._worker.failed.connect(self._on_worker_failed)
        self._worker.start()

    def start_resume(self, run_dir: Path, audio_path: Path, models_config: PipelineConfig) -> None:
        """Возобновляет прерванный запуск из директории run_dir."""
        self._current_audio_path = audio_path
        self._header_label.setText(audio_path.name)
        self._reset_widgets()
        self._set_status("Возобновление…", "running")
        self._reset_stop_btn()
        self._stop_btn.setEnabled(True)
        self._back_btn.setVisible(False)

        self._bridge = BusToQtBridge()
        self._connect_bridge(self._bridge)

        self._worker = ResumeWorker(run_dir, models_config, self._bridge)
        self._worker.result_ready.connect(self._on_worker_finished)
        self._worker.failed.connect(self._on_worker_failed)
        self._worker.start()

    def reset(self) -> None:
        """Сбрасывает экран в начальное состояние без остановки воркера."""
        if self._worker and self._worker.isRunning():
            _log.info(
                "reset: worker запущен — terminate() НЕ вызываем "
                "(pthread_cancel ломает C-расширения). Воркер завершится сам."
            )
        self._worker = None
        self._bridge = None
        self._reset_widgets()
        self._reset_stop_btn()
        self._stop_btn.setEnabled(False)
        self._back_btn.setVisible(False)
        self._current_audio_path = None
        self._header_label.setText("")

    def _reset_stop_btn(self) -> None:
        self._stop_btn.setText("■ Остановить")
        self._stop_btn.setObjectName("stop_btn")
        self._stop_btn.style().unpolish(self._stop_btn)
        self._stop_btn.style().polish(self._stop_btn)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _connect_bridge(self, bridge: BusToQtBridge) -> None:
        bridge.pipeline_started.connect(self._on_pipeline_started)
        bridge.stage_started.connect(self._on_stage_started)
        bridge.stage_done.connect(self._on_stage_done)
        bridge.stage_skipped.connect(self._on_stage_skipped)
        bridge.progress_updated.connect(self._on_progress)
        bridge.pipeline_done.connect(self._on_pipeline_done)
        bridge.pipeline_failed.connect(self._on_pipeline_failed)
        bridge.model_downloading.connect(self._on_model_downloading)
        bridge.model_ready.connect(self._on_model_ready)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(12)

        # Header: filename + stop button
        header_row = QHBoxLayout()
        self._header_label = QLabel()
        self._header_label.setObjectName("screen_title")
        header_row.addWidget(self._header_label, stretch=1)
        self._stop_btn = QPushButton("■ Остановить")
        self._stop_btn.setObjectName("stop_btn")
        self._stop_btn.setEnabled(False)
        self._stop_btn.clicked.connect(self._on_stop_or_resume_clicked)
        header_row.addWidget(self._stop_btn)
        outer.addLayout(header_row)

        # Model download label with slow opacity pulse (replaces indeterminate QProgressBar)
        self._download_label = QLabel("")
        self._download_label.setObjectName("proc_download_label")
        self._download_label.setVisible(False)
        outer.addWidget(self._download_label)
        self._dl_effect = QGraphicsOpacityEffect(self._download_label)
        self._download_label.setGraphicsEffect(self._dl_effect)
        self._dl_anim = QPropertyAnimation(self._dl_effect, b"opacity", self)
        self._dl_anim.setDuration(1100)
        self._dl_anim.setStartValue(1.0)
        self._dl_anim.setEndValue(0.25)
        self._dl_anim.setEasingCurve(QEasingCurve.Type.SineCurve)
        self._dl_anim.setLoopCount(-1)

        # Status
        self._status_label = QLabel("Ожидание…")
        self._status_label.setObjectName("status_label")
        outer.addWidget(self._status_label)

        # Stage timeline (replaces _stage_bar + _stage_steps_label)
        self._timeline = _StageTimeline()
        outer.addWidget(self._timeline)

        # Segment progress (hidden until first _on_progress with real data)
        seg_row = QHBoxLayout()
        seg_lbl = QLabel("Сегменты:")
        seg_lbl.setObjectName("muted")
        seg_lbl.setMinimumWidth(int(72 * load_ui_scale()))
        seg_row.addWidget(seg_lbl)
        self._seg_bar = QProgressBar()
        self._seg_bar.setObjectName("seg_bar")
        self._seg_bar.setFormat("%v / %m сегм.")
        self._seg_bar.setVisible(False)
        seg_row.addWidget(self._seg_bar, stretch=1)
        outer.addLayout(seg_row)

        # Log
        self._log_edit = QTextEdit()
        self._log_edit.setObjectName("proc_log")
        self._log_edit.setReadOnly(True)
        self._log_edit.setMinimumHeight(80)
        outer.addWidget(self._log_edit)

        outer.addStretch()

        # Nav row (hidden in RUNNING, visible in STOPPED/FAILED)
        nav_row = QHBoxLayout()
        self._back_btn = QPushButton("← Назад")
        self._back_btn.setVisible(False)
        self._back_btn.clicked.connect(self.back_requested)
        nav_row.addWidget(self._back_btn)
        nav_row.addStretch()
        outer.addLayout(nav_row)

    def _reset_widgets(self) -> None:
        self._stage_names.clear()
        self._stages_done.clear()
        self._current_stage = 0
        self._last_result = None
        self._stopped_by_user = False
        self._stop_btn_is_resume = False
        self._timeline.reset()
        self._seg_bar.setValue(0)
        self._seg_bar.setMaximum(0)
        self._seg_bar.setVisible(False)
        self._download_label.setVisible(False)
        self._dl_anim.stop()
        self._dl_effect.setOpacity(1.0)
        self._log_edit.clear()
        self._status_label.setText("Ожидание…")
        self._status_label.setProperty("status", "")
        self._status_label.style().unpolish(self._status_label)
        self._status_label.style().polish(self._status_label)

    # ------------------------------------------------------------------
    # Stop / Resume
    # ------------------------------------------------------------------

    def _on_stop_or_resume_clicked(self) -> None:
        if self._stop_btn_is_resume:
            if self._current_audio_path:
                self.resume_requested.emit(self._current_audio_path)
        else:
            self._do_stop()

    def _do_stop(self) -> None:
        _log.info("_do_stop: кнопка 'Остановить' нажата")
        self._stopped_by_user = True
        self.user_stopped.emit()
        if self._worker and self._worker.isRunning():
            if hasattr(self._worker, "stop_requested"):
                self._worker.stop_requested.set()
                _log.info(
                    "_do_stop: stop_requested установлен — pipeline остановится после "
                    "завершения текущего 30-секундного сегмента"
                )
            else:
                _log.warning("_do_stop: worker не имеет stop_requested (старый тип воркера)")
        else:
            _log.info("_do_stop: worker не запущен")
        self._download_label.setVisible(False)
        self._dl_anim.stop()
        self._dl_effect.setOpacity(1.0)
        self._timeline.freeze()

        stage_info = ""
        if self._current_stage and self._stage_names and self._current_stage <= len(self._stage_names):
            stage_info = f" на этапе [{self._current_stage}] {self._stage_names[self._current_stage - 1]}"
        self._set_status(f"Остановлено{stage_info}", "")
        self._log("> Остановлено пользователем")
        self._back_btn.setVisible(True)

        from core.api.transcribe import find_resumable_run
        import json as _json
        _run_dir = find_resumable_run(Path("runs"), str(self._current_audio_path)) if self._current_audio_path else None
        if _run_dir is not None:
            _sf = _run_dir / "state.json"
            if _sf.exists():
                try:
                    _d = _json.loads(_sf.read_text(encoding="utf-8"))
                    _d["status"] = "stopped"
                    _sf.write_text(_json.dumps(_d, ensure_ascii=False, indent=2), encoding="utf-8")
                except Exception:
                    pass
            self._stop_btn_is_resume = True
            self._stop_btn.setText("▶  Возобновить")
            self._stop_btn.setObjectName("run_btn")
            self._stop_btn.style().unpolish(self._stop_btn)
            self._stop_btn.style().polish(self._stop_btn)
        else:
            self._stop_btn.setEnabled(False)

    # ------------------------------------------------------------------
    # EventBus slots
    # ------------------------------------------------------------------

    def _on_pipeline_started(self, total_stages: int, resume_after: int) -> None:
        self._timeline.setup(total_stages)
        # Не помечаем resume-этапы здесь — stage_skipped(index, name) придёт с именами
        msg = f"Обработка запущена: {total_stages} этапов"
        if resume_after:
            msg += f" (возобновление с этапа {resume_after + 1})"
        self._log(msg)

    def _on_stage_started(self, index: int, name: str) -> None:
        while len(self._stage_names) < index:
            self._stage_names.append("")
        self._stage_names[index - 1] = name
        self._current_stage = index
        self._timeline.update_name(index, name)
        self._timeline.mark_active(index)
        self._set_status(f"Этап [{index}] {name}…", "running")
        self._seg_bar.setValue(0)
        self._seg_bar.setMaximum(0)
        self._seg_bar.setVisible(False)
        self._log(f"Этап [{index}] {name}: начало")

    def _on_stage_done(self, index: int, name: str, n_segs: int) -> None:
        self._stages_done.add(index)
        self._timeline.mark_done(index)
        self._log(f"Этап [{index}] {name}: готово ({n_segs} сегм.)")

    def _on_stage_skipped(self, index: int, name: str) -> None:
        self._stages_done.add(index)
        while len(self._stage_names) < index:
            self._stage_names.append("")
        self._stage_names[index - 1] = name
        self._timeline.update_name(index, name)
        self._timeline.mark_done(index)
        self._log(f"Этап [{index}] {name}: пропущена (уже выполнена)")

    def _on_progress(self, _stage_index: int, current: int, total: int) -> None:
        if self._seg_bar.maximum() != total:
            self._seg_bar.setMaximum(total)
        self._seg_bar.setValue(current)
        if not self._seg_bar.isVisible():
            self._seg_bar.setVisible(True)

    def _on_pipeline_done(self, n_segs: int) -> None:
        self._timeline.mark_all_done()
        self._set_status(f"Готово — {n_segs} сегментов", "success")
        self._log(f"Обработка завершена: {n_segs} сегментов")
        self._stop_btn.setEnabled(False)

    def _on_pipeline_failed(self, error: str) -> None:
        self._timeline.mark_error()
        self._set_status("Ошибка!", "error")
        self._download_label.setVisible(False)
        self._dl_anim.stop()
        self._dl_effect.setOpacity(1.0)
        self._log(f"ОШИБКА: {error}")
        self._stop_btn.setEnabled(False)
        self._back_btn.setVisible(True)

    def _on_model_downloading(self, name: str, repo_id: str) -> None:
        self._download_label.setText(f"Загрузка модели {name}…")
        self._download_label.setVisible(True)
        self._dl_anim.start()
        self._set_status(f"Загрузка модели {name}…", "running")
        self._log(f"Загрузка: {name} ({repo_id})")

    def _on_model_ready(self, name: str) -> None:
        self._download_label.setVisible(False)
        self._dl_anim.stop()
        self._dl_effect.setOpacity(1.0)
        self._log(f"Модель готова: {name}")

    def _on_worker_finished(self, result) -> None:
        stale = self.sender() is not self._worker
        _log.info(
            "_on_worker_finished: run_id=%s  stopped_by_user=%s  stale_worker=%s",
            result.run_id, self._stopped_by_user, stale,
        )
        self._last_result = result
        self._stop_btn.setEnabled(False)
        if stale:
            _log.info("_on_worker_finished: старый воркер завершился после reset — эмитим для сохранения проекта")
        self.processing_finished.emit(result)

    def _on_worker_failed(self, msg: str) -> None:
        stale = self.sender() is not self._worker
        _log.info("_on_worker_failed: msg=%r  stale=%s", msg, stale)
        if stale:
            return
        self._set_status(f"Ошибка: {msg}", "error")
        self._download_label.setVisible(False)
        self._dl_anim.stop()
        self._dl_effect.setOpacity(1.0)
        self._log(f"ОШИБКА: {msg}")
        self._stop_btn.setEnabled(False)
        self._back_btn.setVisible(True)
        self.error_occurred.emit()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _set_status(self, text: str, status: str) -> None:
        self._status_label.setText(text)
        self._status_label.setProperty("status", status)
        self._status_label.style().unpolish(self._status_label)
        self._status_label.style().polish(self._status_label)

    def _log(self, text: str) -> None:
        self._log_edit.append(text)
