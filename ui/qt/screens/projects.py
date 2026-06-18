"""Экран проектов — объединённый список всех запусков с фильтрацией.

Источник данных: RunHistoryService (файлы runs/).
Карточка включает прогресс по стадиям пайплайна и кнопку «Возобновить».
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QMimeData, Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from core.storage.run_history_service import RunHistoryService, RunSummary
from ui.qt.scale_manager import load_ui_scale
from ui.qt.theme import ERROR, STOPPED, SUCCESS, TEXT_MUTED, WARNING

_AUDIO_EXTENSIONS = frozenset({".wav", ".mp3", ".m4a", ".ogg", ".flac"})

_STATUS_ICON = {
    "completed": ("✓",  SUCCESS),
    "failed":    ("⚠",  ERROR),
    "stopped":   ("◼",  STOPPED),
    "running":   ("▶",  WARNING),
    "pending":   ("○",  TEXT_MUTED),
}

_STATUS_LABEL = {
    "completed": "Завершён",
    "failed":    "Ошибка",
    "stopped":   "Остановлено",
    "running":   "Выполняется",
    "pending":   "Ожидает",
}

_STAGE_LABELS: dict[str, str] = {
    "segmentation":        "Сегментация",
    "diarization":         "Диаризация",
    "min_duration_filter": "Фильтрация",
    "language_detection":  "Определение языка",
    "asr":                 "Распознавание",
}

_FILTER_ALL        = "all"
_FILTER_COMPLETED  = "completed"
_FILTER_INCOMPLETE = "incomplete"


def _pipeline_stages(diarization: bool) -> list[str]:
    if diarization:
        return ["diarization", "min_duration_filter", "language_detection", "asr"]
    return ["segmentation", "language_detection", "asr"]


def _fmt_duration(seconds: float) -> str:
    if seconds <= 0:
        return "—"
    s = int(seconds)
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m}:{sec:02d}"


def _fmt_date(iso: str) -> str:
    if not iso:
        return "—"
    try:
        dt = datetime.fromisoformat(iso)
        return dt.strftime("%-d %b %Y, %H:%M")
    except Exception:
        return iso


class _RunCard(QFrame):
    clicked          = Signal(str)  # run_id — open result
    resume_requested = Signal(str)  # run_id — resume interrupted run

    def __init__(self, summary: RunSummary, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.run_id = summary.run_id
        self.setObjectName("run_card")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        if summary.has_result:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._build(summary)

    def _build(self, s: RunSummary) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 10, 16, 10)
        outer.setSpacing(6)

        hbox = QHBoxLayout()
        hbox.setContentsMargins(0, 0, 0, 0)
        hbox.setSpacing(12)

        # Status icon column
        icon_char, _ = _STATUS_ICON.get(s.status, ("○", TEXT_MUTED))
        icon_lbl = QLabel(icon_char)
        icon_lbl.setObjectName("run_status_icon")
        icon_lbl.setProperty("run_status", s.status)
        hbox.addWidget(icon_lbl)

        # Left: file name + model/duration info
        info_col = QVBoxLayout()
        info_col.setSpacing(2)

        name_lbl = QLabel(s.audio_name)
        name_lbl.setObjectName("card_name")
        info_col.addWidget(name_lbl)

        sub_parts = [p for p in [s.asr_model, _fmt_duration(s.audio_duration)] if p]
        sub_lbl = QLabel("  ·  ".join(sub_parts))
        sub_lbl.setObjectName("muted")
        info_col.addWidget(sub_lbl)
        hbox.addLayout(info_col, stretch=1)

        # Right: status label + date
        right_col = QVBoxLayout()
        right_col.setSpacing(2)
        right_col.setAlignment(Qt.AlignmentFlag.AlignRight)

        status_text = _STATUS_LABEL.get(s.status, s.status)
        status_lbl = QLabel(status_text)
        status_lbl.setObjectName("run_status_text")
        status_lbl.setProperty("run_status", s.status)
        status_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        right_col.addWidget(status_lbl)

        date_lbl = QLabel(_fmt_date(s.created_at))
        date_lbl.setObjectName("muted")
        date_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        right_col.addWidget(date_lbl)
        hbox.addLayout(right_col)

        outer.addLayout(hbox)

        expected = s.stages if s.stages else _pipeline_stages(s.diarization)
        done_set = set(s.completed_stages)
        stage_row = QHBoxLayout()
        stage_row.setContentsMargins(28, 0, 0, 0)
        stage_row.setSpacing(6)

        counter = QLabel(f"{len(done_set)}/{len(expected)}")
        counter.setObjectName("run_stage_counter")
        stage_row.addWidget(counter)

        parts = []
        for name in expected:
            done = name in done_set
            icon = "✓" if done else "○"
            color = SUCCESS if done else TEXT_MUTED
            parts.append(
                f'<span style="color:{color};">{icon} {_STAGE_LABELS.get(name, name)}</span>'
            )
        arrow = f' <span style="color:{TEXT_MUTED};">→</span> '
        stages_lbl = QLabel(arrow.join(parts))
        stages_lbl.setObjectName("run_stages_label")
        stage_row.addWidget(stages_lbl)
        stage_row.addStretch()
        outer.addLayout(stage_row)

        if s.is_resumable:
            btn_row = QHBoxLayout()
            btn_row.setContentsMargins(28, 0, 0, 0)
            resume_btn = QPushButton("▶  Возобновить")
            resume_btn.setObjectName("run_btn")
            resume_btn.clicked.connect(lambda: self.resume_requested.emit(self.run_id))
            btn_row.addWidget(resume_btn)
            btn_row.addStretch()
            outer.addLayout(btn_row)

    def mousePressEvent(self, event) -> None:
        self.clicked.emit(self.run_id)
        super().mousePressEvent(event)


class ProjectsScreen(QWidget):
    """Экран проектов: список запусков с фильтрацией и кнопкой «Новый проект»."""

    new_project_requested = Signal()
    file_accepted         = Signal(Path)  # drag-and-drop audio
    run_selected          = Signal(str)   # run_id — open result
    resume_run_requested  = Signal(str)   # run_id — resume interrupted run

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._service = RunHistoryService()
        self._all_summaries: list[RunSummary] = []
        self._active_filter = _FILTER_ALL
        self._build_ui()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def refresh(self, runs_dir: Path) -> None:
        """Перечитывает запуски из директории и обновляет список."""
        self._all_summaries = self._service.load_all(runs_dir)
        self._apply_filter()

    def run_count(self) -> int:
        return len(self._all_summaries)

    # ------------------------------------------------------------------
    # Drag-and-drop
    # ------------------------------------------------------------------

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        md: QMimeData = event.mimeData()
        if md.hasUrls():
            url = md.urls()[0]
            if url.isLocalFile():
                suffix = Path(url.toLocalFile()).suffix.lower()
                if suffix in _AUDIO_EXTENSIONS:
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        path = Path(event.mimeData().urls()[0].toLocalFile())
        self.file_accepted.emit(path)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 32, 32, 32)
        outer.setSpacing(16)

        # Header row
        header = QHBoxLayout()
        title = QLabel("Проекты")
        title.setObjectName("screen_title")
        header.addWidget(title)
        header.addStretch()
        new_btn = QPushButton("+ Новый проект")
        new_btn.setObjectName("run_btn")
        new_btn.clicked.connect(self.new_project_requested)
        header.addWidget(new_btn)
        outer.addLayout(header)

        # Filter bar
        filter_row = QHBoxLayout()
        filter_row.setSpacing(8)
        self._filter_btns: dict[str, QPushButton] = {}
        for key, label in (
            (_FILTER_ALL,        "Все"),
            (_FILTER_COMPLETED,  "Завершённые"),
            (_FILTER_INCOMPLETE, "Незавершённые"),
        ):
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setObjectName("filter_btn")
            btn.setChecked(key == self._active_filter)
            btn.clicked.connect(lambda checked=False, k=key: self._set_filter(k))
            filter_row.addWidget(btn)
            self._filter_btns[key] = btn
        filter_row.addStretch()
        outer.addLayout(filter_row)

        # Stacked: 0 = empty state, 1 = list
        self._stack = QStackedWidget()
        self._stack.addWidget(self._build_empty_state())
        self._stack.addWidget(self._build_list_container())
        outer.addWidget(self._stack, stretch=1)

    def _build_empty_state(self) -> QWidget:
        w = QWidget()
        vbox = QVBoxLayout(w)
        vbox.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vbox.setSpacing(12)

        self._empty_msg = QLabel("Ещё нет проектов")
        self._empty_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_msg.setObjectName("run_empty_title")
        vbox.addWidget(self._empty_msg)

        self._empty_hint = QLabel("Создайте первый проект, чтобы начать работу")
        self._empty_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_hint.setObjectName("muted")
        vbox.addWidget(self._empty_hint)

        vbox.addSpacing(8)

        self._empty_new_btn = QPushButton("+ Новый проект")
        self._empty_new_btn.setObjectName("run_btn")
        self._empty_new_btn.setMinimumWidth(int(200 * load_ui_scale()))
        self._empty_new_btn.clicked.connect(self.new_project_requested)
        vbox.addWidget(self._empty_new_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        drop_hint = QLabel("или перетащите аудиофайл сюда")
        drop_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        drop_hint.setObjectName("muted")
        vbox.addWidget(drop_hint)

        return w

    def _build_list_container(self) -> QWidget:
        w = QWidget()
        vbox = QVBoxLayout(w)
        vbox.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(scroll.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._list_widget = QWidget()
        self._list_layout = QVBoxLayout(self._list_widget)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(6)
        self._list_layout.addStretch()

        scroll.setWidget(self._list_widget)
        vbox.addWidget(scroll)
        return w

    # ------------------------------------------------------------------
    # Filtering & rendering
    # ------------------------------------------------------------------

    def _set_filter(self, key: str) -> None:
        self._active_filter = key
        for k, btn in self._filter_btns.items():
            btn.setChecked(k == key)
        self._apply_filter()

    def _apply_filter(self) -> None:
        if self._active_filter == _FILTER_COMPLETED:
            visible = [s for s in self._all_summaries if s.status == "completed"]
        elif self._active_filter == _FILTER_INCOMPLETE:
            visible = [
                s for s in self._all_summaries
                if s.status in ("failed", "stopped", "running", "pending")
            ]
        else:
            visible = list(self._all_summaries)

        self._update_empty_state()
        self._populate(visible)

    def _update_empty_state(self) -> None:
        if self._active_filter == _FILTER_COMPLETED:
            self._empty_msg.setText("Нет завершённых проектов")
            self._empty_hint.setText("Завершённые запуски появятся здесь")
            self._empty_new_btn.hide()
        elif self._active_filter == _FILTER_INCOMPLETE:
            self._empty_msg.setText("Нет незавершённых проектов")
            self._empty_hint.setText("Прерванные и неудачные запуски появятся здесь")
            self._empty_new_btn.hide()
        else:
            self._empty_msg.setText("Ещё нет проектов")
            self._empty_hint.setText("Создайте первый проект, чтобы начать работу")
            self._empty_new_btn.show()

    def _populate(self, summaries: list[RunSummary]) -> None:
        while self._list_layout.count() > 1:
            item = self._list_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

        if not summaries:
            self._stack.setCurrentIndex(0)
            return

        self._stack.setCurrentIndex(1)
        for i, s in enumerate(summaries):
            card = _RunCard(s)
            if s.has_result:
                card.clicked.connect(self.run_selected)
            if s.is_resumable:
                card.resume_requested.connect(self.resume_run_requested)
            self._list_layout.insertWidget(i, card)
