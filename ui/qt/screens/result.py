"""Экран просмотра результата транскрибации.

Отображает сегменты с временными метками, спикерами и языком в формате HTML.
Предоставляет кнопки экспорта JSON, TXT и копирования в буфер обмена.
"""

from __future__ import annotations

import html
from pathlib import Path

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from core.api.transcribe import TranscriptionResult
from core.export import build_meeting_report, export_json, export_txt
from core.export.report import _fmt_time
from ui.qt.theme import TEXT_MUTED, current_theme_colors

_SPEAKER_COLORS = ["#818CF8", "#38BDF8", "#34D399", "#FBBF24", "#F87171", "#E879F9"]


class _ScaledTextBrowser(QTextBrowser):
    """QTextBrowser, синхронизирующий шрифт документа при изменении QSS-масштаба."""

    def changeEvent(self, event: QEvent) -> None:
        super().changeEvent(event)
        if event.type() in (QEvent.Type.FontChange, QEvent.Type.ApplicationFontChange):
            self.document().setDefaultFont(self.font())


def _render_report_html(result: TranscriptionResult) -> str:
    colors = current_theme_colors()
    muted = colors.text

    speaker_ids: list[str] = []
    for seg in result.segments:
        if seg.speaker_id and seg.speaker_id not in speaker_ids:
            speaker_ids.append(seg.speaker_id)
    speaker_color = {
        sid: _SPEAKER_COLORS[i % len(_SPEAKER_COLORS)]
        for i, sid in enumerate(speaker_ids)
    }

    parts = [
        '<html><body style="font-family:sans-serif;margin:4px;">'
    ]
    for seg in sorted(result.segments, key=lambda s: s.start_time):
        ts = (
            f'<span style="color:{muted};font-family:monospace;font-size:small">'
            f'{_fmt_time(seg.start_time)}&ndash;{_fmt_time(seg.end_time)}</span>'
        )
        spk_badge = ""
        if seg.speaker_id:
            color = speaker_color.get(seg.speaker_id, muted)
            spk_badge = (
                f'<span style="color:{color};font-weight:bold;font-size:small;'
                f'margin-right:6px">{html.escape(seg.speaker_id)}</span>'
            )
        lang_badge = ""
        if seg.language:
            lang_badge = (
                f'<span style="background-color:rgba(128,128,128,0.15);color:{muted};'
                f'font-size:x-small;border-radius:3px;padding:1px 4px;'
                f'margin-right:4px">{html.escape(seg.language)}</span>'
            )
        text = html.escape(seg.text or "")
        parts.append(
            f'<p style="margin:3px 0 3px 0;line-height:1.5">'
            f'{ts}&nbsp;&nbsp;{spk_badge}{lang_badge}{text}</p>'
        )
    parts.append("</body></html>")
    return "".join(parts)


class ResultScreen(QWidget):
    """Экран просмотра результата транскрибации с экспортом.

    Signals:
        back_requested: пользователь хочет вернуться на предыдущий экран.
        edit_requested: пользователь хочет открыть редактор транскрипта.
    """

    back_requested = Signal()
    edit_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        """Инициализирует экран и создаёт QTextBrowser и кнопки экспорта."""
        super().__init__(parent)
        self._last_result: TranscriptionResult | None = None
        self._build_ui()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def show_result(self, result: TranscriptionResult) -> None:
        """Отображает результат транскрибации в браузере.

        Args:
            result (TranscriptionResult): Результат работы pipeline.
        """
        self._last_result = result
        self._browser.document().setDefaultFont(self._browser.font())
        self._browser.setHtml(_render_report_html(result))
        self._meta_label.setText(
            f"run: {result.run_id}  ·  "
            f"{_fmt_time(result.duration_s)}  ·  "
            f"{len(result.segments)} сегм."
        )
        for btn in (self._copy_btn, self._json_btn, self._txt_btn, self._edit_btn):
            btn.setEnabled(True)

    def reset(self) -> None:
        """Очищает экран и деактивирует кнопки экспорта."""
        self._last_result = None
        self._browser.clear()
        self._meta_label.setText("")
        for btn in (self._copy_btn, self._json_btn, self._txt_btn, self._edit_btn):
            btn.setEnabled(False)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 32, 32, 32)
        outer.setSpacing(16)

        # Header: ← Назад · "Результат" · stretch · Редактировать
        # Mirrors models screen: QLabel title in same row as action button
        header_row = QHBoxLayout()
        header_row.setSpacing(12)
        back_btn = QPushButton("← Назад")
        back_btn.clicked.connect(self.back_requested)
        header_row.addWidget(back_btn)
        title = QLabel("Результат")
        title.setObjectName("screen_title")
        header_row.addWidget(title)
        header_row.addStretch()
        self._edit_btn = QPushButton("Редактировать")
        self._edit_btn.setObjectName("run_btn")
        self._edit_btn.setEnabled(False)
        self._edit_btn.clicked.connect(self.edit_requested)
        header_row.addWidget(self._edit_btn)
        outer.addLayout(header_row)

        self._browser = _ScaledTextBrowser()
        self._browser.setOpenLinks(False)
        outer.addWidget(self._browser, stretch=1)

        # Bottom: export actions left, meta info right
        bottom_row = QHBoxLayout()
        self._copy_btn = QPushButton("Копировать всё")
        self._copy_btn.setEnabled(False)
        self._copy_btn.clicked.connect(self._on_copy_all)
        self._json_btn = QPushButton("Сохранить JSON")
        self._json_btn.setEnabled(False)
        self._json_btn.clicked.connect(self._on_save_json)
        self._txt_btn = QPushButton("Сохранить TXT")
        self._txt_btn.setEnabled(False)
        self._txt_btn.clicked.connect(self._on_save_txt)
        bottom_row.addWidget(self._copy_btn)
        bottom_row.addWidget(self._json_btn)
        bottom_row.addWidget(self._txt_btn)
        bottom_row.addStretch()
        self._meta_label = QLabel("")
        self._meta_label.setObjectName("muted")
        bottom_row.addWidget(self._meta_label)
        outer.addLayout(bottom_row)

    # ------------------------------------------------------------------
    # Event handling
    # ------------------------------------------------------------------

    def changeEvent(self, event: QEvent) -> None:
        super().changeEvent(event)
        if event.type() == QEvent.Type.ApplicationPaletteChange and self._last_result:
            self._refresh_html()

    def _refresh_html(self) -> None:
        if self._last_result:
            self._browser.setHtml(_render_report_html(self._last_result))

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _on_copy_all(self) -> None:
        if not self._last_result:
            return
        lines: list[str] = []
        for seg in sorted(self._last_result.segments, key=lambda s: s.start_time):
            lang = f"[{seg.language}] " if seg.language else ""
            spk = f"{seg.speaker_id}: " if seg.speaker_id else ""
            lines.append(
                f"{_fmt_time(seg.start_time)} – {_fmt_time(seg.end_time)}  {spk}{lang}{seg.text or ''}"
            )
        QApplication.clipboard().setText("\n".join(lines))

    def _on_save_json(self) -> None:
        if not self._last_result:
            return
        default_name = f"transcript_{self._last_result.run_id}.json"
        path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить JSON", default_name, "JSON (*.json)"
        )
        if path:
            export_json(build_meeting_report(self._last_result), Path(path))

    def _on_save_txt(self) -> None:
        if not self._last_result:
            return
        default_name = f"transcript_{self._last_result.run_id}.txt"
        path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить TXT", default_name, "Text (*.txt)"
        )
        if path:
            export_txt(build_meeting_report(self._last_result), Path(path))
