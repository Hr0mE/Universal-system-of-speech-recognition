"""Экран приветствия для импорта аудиофайла.

Показывается при создании нового проекта или когда проекты ещё отсутствуют.
Поддерживает drag-and-drop и выбор файла через диалог.
"""

from __future__ import annotations

import wave
from pathlib import Path

from PySide6.QtCore import QMimeData, QSettings, Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ui.qt.theme import ACCENT, TEXT_MUTED, WARNING

_AUDIO_EXTENSIONS = frozenset({".wav", ".mp3", ".m4a", ".ogg", ".flac"})


def _format_size(n_bytes: int) -> str:
    if n_bytes >= 1_073_741_824:
        return f"{n_bytes / 1_073_741_824:.1f} ГБ"
    return f"{n_bytes / 1_048_576:.1f} МБ"


def _format_duration(seconds: float) -> str:
    s = int(seconds)
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{sec:02d}"
    return f"{m}:{sec:02d}"


def _read_wav_duration(path: Path) -> float | None:
    try:
        with wave.open(str(path)) as wf:
            return wf.getnframes() / wf.getframerate()
    except Exception:
        return None


class WelcomeScreen(QWidget):
    """Начальный экран импорта файла с зоной drag-and-drop.

    Signals:
        file_accepted: путь к выбранному аудиофайлу (новый запуск).
        resume_requested: путь к файлу для возобновления прерванного запуска.
        settings_requested: запрос открытия диалога настроек.
        back_requested: запрос возврата на предыдущий экран.
    """

    file_accepted      = Signal(Path)
    resume_requested   = Signal(Path)
    settings_requested = Signal()
    back_requested     = Signal()

    def __init__(self, parent=None) -> None:
        """Инициализирует экран приветствия с drag-and-drop зоной."""
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._settings = QSettings("USSR-Diplom", "Transcription")
        self._audio_path: Path | None = None
        self._in_resume_mode: bool = False

        outer = QVBoxLayout(self)
        outer.setContentsMargins(40, 40, 40, 40)
        outer.addStretch()

        self._inner_stack = QStackedWidget()
        self._inner_stack.addWidget(self._build_drop_zone())  # 0 — empty
        self._inner_stack.addWidget(self._build_file_card())  # 1 — selected

        outer.addWidget(self._inner_stack, alignment=Qt.AlignmentFlag.AlignHCenter)
        outer.addStretch()

        self._last_dir = self._settings.value("last_audio_dir", "")

    # ------------------------------------------------------------------
    # Build sub-widgets
    # ------------------------------------------------------------------

    def _build_drop_zone(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("drop_zone")
        frame.setMinimumSize(400, 240)
        frame.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        vbox = QVBoxLayout(frame)
        vbox.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vbox.setSpacing(16)

        hint = QLabel("Перетащите аудио сюда")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setStyleSheet(f"font-size: 16px; color: {TEXT_MUTED}; background: transparent;")
        vbox.addWidget(hint)

        or_label = QLabel("или")
        or_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        or_label.setStyleSheet(f"font-size: 12px; color: {TEXT_MUTED}; background: transparent;")
        vbox.addWidget(or_label)

        browse_btn = QPushButton("Выбрать файл")
        browse_btn.setMinimumWidth(160)
        browse_btn.clicked.connect(self._on_browse)
        vbox.addWidget(browse_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        return frame

    def _build_file_card(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("file_card")
        frame.setMinimumSize(400, 260)
        frame.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )

        vbox = QVBoxLayout(frame)
        vbox.setContentsMargins(28, 20, 28, 24)
        vbox.setSpacing(6)

        # Status banner — shown only in resume mode
        self._status_banner = QLabel()
        self._status_banner.setVisible(False)
        self._status_banner.setStyleSheet(
            f"font-size: 12px; color: {WARNING}; background: rgba(251,191,36,0.12);"
            " border: 1px solid rgba(251,191,36,0.35); border-radius: 5px;"
            " padding: 5px 10px;"
        )
        self._status_banner.setWordWrap(True)
        vbox.addWidget(self._status_banner)

        self._filename_label = QLabel()
        self._filename_label.setStyleSheet(
            "font-size: 16px; font-weight: bold; background: transparent;"
        )
        self._filename_label.setWordWrap(True)
        vbox.addWidget(self._filename_label)

        self._meta_label = QLabel()
        self._meta_label.setStyleSheet(
            f"font-size: 13px; color: {TEXT_MUTED}; background: transparent;"
        )
        vbox.addWidget(self._meta_label)

        vbox.addStretch()

        hint_row = QHBoxLayout()
        self._hint_lbl = QLabel("Используются рекомендуемые настройки")
        self._hint_lbl.setStyleSheet(f"font-size: 12px; color: {TEXT_MUTED}; background: transparent;")
        change_btn = QPushButton("Изменить")
        change_btn.setFlat(True)
        change_btn.setStyleSheet(
            f"font-size: 12px; color: {ACCENT}; background: transparent;"
            " border: none; padding: 0; min-height: 0;"
        )
        change_btn.clicked.connect(self.settings_requested)
        hint_row.addWidget(self._hint_lbl)
        hint_row.addWidget(change_btn)
        hint_row.addStretch()
        vbox.addLayout(hint_row)

        vbox.addSpacing(12)

        btn_row = QHBoxLayout()
        self._start_btn = QPushButton("▶  Начать обработку")
        self._start_btn.setObjectName("run_btn")
        self._start_btn.setMinimumWidth(210)
        self._start_btn.clicked.connect(self._on_start)
        back_btn = QPushButton("← Назад")
        back_btn.clicked.connect(self.back_requested)
        btn_row.addWidget(self._start_btn)
        btn_row.addWidget(back_btn)
        btn_row.addStretch()
        vbox.addLayout(btn_row)

        return frame

    # ------------------------------------------------------------------
    # State transitions
    # ------------------------------------------------------------------

    def _show_drop_zone(self) -> None:
        self._audio_path = None
        self._inner_stack.setCurrentIndex(0)

    def _show_file_card(self, path: Path) -> None:
        self._audio_path = path
        self._filename_label.setText(path.name)

        size_str = _format_size(path.stat().st_size)
        dur = _read_wav_duration(path)
        dur_str = _format_duration(dur) if dur is not None else "—"
        self._meta_label.setText(f"{dur_str}  ·  {size_str}")

        # Reset to normal (non-resume) mode
        self._in_resume_mode = False
        self._status_banner.setVisible(False)
        self._start_btn.setText("▶  Начать обработку")

        self._inner_stack.setCurrentIndex(1)
        self._settings.setValue("last_audio_dir", str(path.parent))

    # ------------------------------------------------------------------
    # Event handlers
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
        self._show_file_card(path)

    def _on_browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите аудиофайл",
            self._last_dir,
            "Аудио (*.wav *.mp3 *.m4a *.ogg *.flac);;Все файлы (*)",
        )
        if path:
            self._show_file_card(Path(path))

    def _on_start(self) -> None:
        if self._audio_path:
            if self._in_resume_mode:
                self.resume_requested.emit(self._audio_path)
            else:
                self.file_accepted.emit(self._audio_path)

    def set_config_hint(self, text: str) -> None:
        self._hint_lbl.setText(text)

    def show_file(self, path: Path) -> None:
        """Programmatically select a file (e.g. when re-opening a project)."""
        self._show_file_card(path)

    def show_resume(self, path: Path, status: str = "stopped") -> None:
        """Show file card in resume mode.

        status: 'stopped' (user interrupted) or 'failed' (error).
        """
        self._show_file_card(path)
        self._in_resume_mode = True
        if status == "stopped":
            msg = "⚠  Предыдущий запуск был остановлен. Нажмите «Возобновить», чтобы продолжить с последнего этапа."
        else:
            msg = "⚠  Предыдущий запуск завершился с ошибкой. Нажмите «Возобновить», чтобы попробовать снова."
        self._status_banner.setText(msg)
        self._status_banner.setVisible(True)
        self._start_btn.setText("▶  Возобновить")

