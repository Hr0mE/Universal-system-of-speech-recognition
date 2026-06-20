"""Двухпанельный редактор транскрипта.

Левая панель — прокручиваемый список сегментов, правая — форма редактирования текста,
языка и спикера. Синхронизирован с AudioPlayerWidget и TimelineWidget.
"""

from __future__ import annotations

import copy
from pathlib import Path

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QComboBox,
    QLineEdit,
    QFormLayout,
)

from core.api.transcribe import TranscriptionResult, save_run_result
from core.export import build_meeting_report, export_json, export_txt
from core.export.report import _fmt_time
from core.pipeline.context import Segment
from ui.qt.audio_player import AudioPlayerWidget
from ui.qt.theme import TEXT_MUTED
from ui.qt.timeline import TimelineWidget

_SPEAKER_COLORS = ["#818CF8", "#38BDF8", "#34D399", "#FBBF24", "#F87171", "#E879F9"]


class _ScaledTextEdit(QPlainTextEdit):
    """QPlainTextEdit, синхронизирующий шрифт документа при изменении QSS-масштаба."""

    def changeEvent(self, event: QEvent) -> None:
        super().changeEvent(event)
        if event.type() in (QEvent.Type.FontChange, QEvent.Type.ApplicationFontChange):
            self.document().setDefaultFont(self.font())


def _fmt_range(start: float, end: float) -> str:
    return f"{_fmt_time(start)} – {_fmt_time(end)}"


def _truncate(text: str | None, n: int = 45) -> str:
    if not text:
        return "—"
    return text if len(text) <= n else text[:n - 1] + "…"


def _speaker_color(speaker_id: str | None, all_speakers: list[str]) -> str:
    if not speaker_id or speaker_id not in all_speakers:
        return TEXT_MUTED
    return _SPEAKER_COLORS[all_speakers.index(speaker_id) % len(_SPEAKER_COLORS)]


class _SegItem(QFrame):
    clicked = Signal()

    def __init__(
        self,
        idx: int,
        seg: Segment,
        all_speakers: list[str],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.seg_idx = idx
        self._checked = False
        self.setObjectName("seg_item")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        vbox = QVBoxLayout(self)
        vbox.setContentsMargins(10, 8, 10, 8)
        vbox.setSpacing(3)

        self._hdr = QLabel()
        self._hdr.setObjectName("seg_item_header")
        vbox.addWidget(self._hdr)

        self._preview = QLabel()
        self._preview.setObjectName("seg_item_preview")
        self._preview.setWordWrap(True)
        vbox.addWidget(self._preview)

        self._refresh(seg, all_speakers)

    def _refresh(self, seg: Segment, all_speakers: list[str]) -> None:
        spk = seg.speaker_id or "—"
        time_str = _fmt_range(seg.start_time, seg.end_time)
        color = _speaker_color(seg.speaker_id, all_speakers)
        self._hdr.setText(f"{time_str}  ·  {spk}")
        self._hdr.setStyleSheet(
            f"color: {color}; font-size: 11px; background: transparent;"
        )
        self._preview.setText(seg.text or "")
        self.setToolTip(
            f"Участник: {spk} | Язык: {seg.language or '—'} | {time_str}"
        )

    def setChecked(self, checked: bool) -> None:
        self._checked = checked
        self.setProperty("checked", "true" if checked else "false")
        self.style().unpolish(self)
        self.style().polish(self)

    def isChecked(self) -> bool:
        return self._checked

    def setCheckable(self, _: bool) -> None:
        pass

    def mousePressEvent(self, event) -> None:
        super().mousePressEvent(event)
        self.clicked.emit()


class _SpeakerLegend(QWidget):
    """Компактная легенда спикеров: 2 элемента в колонке, несколько колонок."""

    _ROWS = 2

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._grid = QHBoxLayout(self)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setSpacing(16)

    def refresh(self, speakers: list[str]) -> None:
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not speakers:
            return

        for col_start in range(0, len(speakers), self._ROWS):
            col_w = QWidget()
            col_v = QVBoxLayout(col_w)
            col_v.setContentsMargins(0, 0, 0, 0)
            col_v.setSpacing(2)
            for row in range(self._ROWS):
                idx = col_start + row
                if idx >= len(speakers):
                    break
                spk = speakers[idx]
                color = _SPEAKER_COLORS[idx % len(_SPEAKER_COLORS)]
                row_w = QWidget()
                row_h = QHBoxLayout(row_w)
                row_h.setContentsMargins(0, 0, 0, 0)
                row_h.setSpacing(4)
                dot = QLabel("●")
                dot.setStyleSheet(
                    f"color: {color}; font-size: 9px; background: transparent;"
                )
                name_lbl = QLabel(_truncate(spk, 16))
                name_lbl.setObjectName("muted")
                name_lbl.setStyleSheet("font-size: 11px;")
                row_h.addWidget(dot)
                row_h.addWidget(name_lbl)
                col_v.addWidget(row_w)
            self._grid.addWidget(col_w)


class TranscriptEditorScreen(QWidget):
    """Two-panel transcript editor: segment list (left) + detail editor (right)."""

    back_requested = Signal()
    saved = Signal(object)  # emits updated TranscriptionResult

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._result: TranscriptionResult | None = None
        self._segments: list[Segment] = []
        self._selected_idx: int | None = None
        self._dirty: bool = False
        self._updating_fields: bool = False  # guard against recursive signals
        self._playback_select: bool = False  # True while auto-selecting from playback position
        self._build_ui()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load(self, result: TranscriptionResult) -> None:
        """Load a result for editing. Makes a deep copy of segments."""
        self._result = result
        self._segments = copy.deepcopy(result.segments)
        self._selected_idx = None
        self._dirty = False
        self._rebuild_list()
        self._show_placeholder()
        self._update_header()
        self._timeline.load(self._segments, result.duration_s)
        audio = Path(result.audio_path) if result.audio_path else None
        if audio and audio.exists():
            self._audio_player.load_file(audio)
            self._audio_player.setVisible(True)
        else:
            self._audio_player.clear()
            self._audio_player.setVisible(False)

    def set_theme(self, mode: str) -> None:
        self._audio_player.set_theme(mode)

    def set_scale(self, scale: float) -> None:
        self._timeline.set_scale(scale)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Header bar
        header_bar = QWidget()
        header_bar.setObjectName("editor_header")
        header_layout = QHBoxLayout(header_bar)
        header_layout.setContentsMargins(16, 0, 16, 0)
        header_layout.setSpacing(12)

        back_btn = QPushButton("← Результат")
        back_btn.clicked.connect(self._on_back)
        header_layout.addWidget(back_btn)

        header_layout.addStretch()

        self._revert_btn = QPushButton("Отменить изменения")
        self._revert_btn.setObjectName("stop_btn")
        self._revert_btn.setEnabled(False)
        self._revert_btn.clicked.connect(self._revert)
        header_layout.addWidget(self._revert_btn)

        save_btn = QPushButton("Сохранить")
        save_btn.setObjectName("run_btn")
        save_btn.clicked.connect(self._save)

        self._dirty_badge = QLabel("● несохранённые")
        self._dirty_badge.setObjectName("dirty_badge")
        self._dirty_badge.setVisible(False)
        self._dirty_badge.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        save_wrap = QWidget()
        save_wrap.setStyleSheet("background: transparent;")
        save_vbox = QVBoxLayout(save_wrap)
        save_vbox.setContentsMargins(0, 0, 0, 0)
        save_vbox.setSpacing(1)
        save_vbox.addWidget(save_btn)
        save_vbox.addWidget(self._dirty_badge)
        header_layout.addWidget(save_wrap)

        outer.addWidget(header_bar)

        # Main split: left list + right editor
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setObjectName("editor_splitter")
        splitter.setChildrenCollapsible(False)

        # Left: segment list
        left = QWidget()
        left.setObjectName("editor_seg_list")
        left_vbox = QVBoxLayout(left)
        left_vbox.setContentsMargins(0, 0, 0, 0)
        left_vbox.setSpacing(0)

        seg_header = QLabel("Сегменты")
        seg_header.setObjectName("nav_section")
        seg_header.setContentsMargins(14, 10, 14, 4)
        left_vbox.addWidget(seg_header)

        self._seg_scroll = QScrollArea()
        self._seg_scroll.setObjectName("nav_scroll")
        self._seg_scroll.setWidgetResizable(True)
        self._seg_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._seg_scroll.setFrameShape(self._seg_scroll.Shape.NoFrame)

        self._list_widget = QWidget()
        self._list_widget.setObjectName("nav_list")
        self._list_layout = QVBoxLayout(self._list_widget)
        self._list_layout.setContentsMargins(8, 4, 8, 8)
        self._list_layout.setSpacing(2)
        self._list_layout.addStretch()
        self._seg_scroll.setWidget(self._list_widget)
        left_vbox.addWidget(self._seg_scroll, stretch=1)
        splitter.addWidget(left)

        # Right: editor stack (placeholder / editor panel)
        right = QWidget()
        right_vbox = QVBoxLayout(right)
        right_vbox.setContentsMargins(24, 24, 24, 0)
        right_vbox.setSpacing(12)

        self._placeholder = self._build_placeholder()
        right_vbox.addWidget(self._placeholder)

        self._editor_panel = self._build_editor_panel()
        self._editor_panel.setVisible(False)
        right_vbox.addWidget(self._editor_panel, stretch=1)

        splitter.addWidget(right)
        splitter.setSizes([280, 800])

        outer.addWidget(splitter, stretch=1)

        # Создаём оба виджета, затем добавляем в DAW-порядке: дорожки ↑, транспорт ↓
        self._audio_player = AudioPlayerWidget()

        self._timeline = TimelineWidget()
        self._timeline.segment_clicked.connect(self._select)
        self._timeline.playhead_seek.connect(self._audio_player.seek)
        self._audio_player.position_changed.connect(self._timeline.set_playhead)
        self._audio_player.position_changed.connect(self._on_playback_position)
        outer.addWidget(self._timeline)
        outer.addWidget(self._audio_player)
        self._audio_player.zoom_changed.connect(self._timeline.set_zoom)

        # Footer: action buttons + reference info
        footer_widget = QWidget()
        footer_widget.setObjectName("editor_footer")
        footer_layout = QHBoxLayout(footer_widget)
        footer_layout.setContentsMargins(16, 0, 16, 0)
        footer_layout.setSpacing(8)

        self._copy_btn = QPushButton("Копировать всё")
        self._copy_btn.clicked.connect(self._on_copy_all)
        footer_layout.addWidget(self._copy_btn)

        export_menu = QMenu()
        export_menu.addAction("Сохранить JSON", self._on_save_json)
        export_menu.addAction("Сохранить TXT", self._on_save_txt)
        self._export_btn = QToolButton()
        self._export_btn.setText("Экспорт")
        self._export_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self._export_btn.setMenu(export_menu)
        footer_layout.addWidget(self._export_btn)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet(f"color: {TEXT_MUTED};")
        footer_layout.addWidget(sep)

        self._footer_stats = QLabel("")
        self._footer_stats.setObjectName("muted")
        footer_layout.addWidget(self._footer_stats)

        footer_layout.addStretch()

        self._speaker_legend = _SpeakerLegend()
        footer_layout.addWidget(self._speaker_legend)

        outer.addWidget(footer_widget)

    def _build_placeholder(self) -> QWidget:
        w = QWidget()
        vbox = QVBoxLayout(w)
        vbox.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vbox.setSpacing(8)
        icon_lbl = QLabel("✎")
        icon_lbl.setObjectName("editor_placeholder_icon")
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vbox.addWidget(icon_lbl)
        lbl = QLabel("Выберите сегмент из списка слева")
        lbl.setObjectName("editor_placeholder_label")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vbox.addWidget(lbl)
        return w

    def _build_editor_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("editor_panel")
        vbox = QVBoxLayout(panel)
        vbox.setContentsMargins(16, 16, 16, 16)
        vbox.setSpacing(12)

        # Text edit
        text_lbl = QLabel("Текст")
        text_lbl.setObjectName("muted")
        vbox.addWidget(text_lbl)

        self._text_edit = _ScaledTextEdit()
        self._text_edit.setMinimumHeight(120)
        self._text_edit.textChanged.connect(self._on_text_changed)
        vbox.addWidget(self._text_edit, stretch=1)

        # Metadata form
        form = QFormLayout()
        form.setSpacing(8)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._time_label = QLabel("—")
        self._time_label.setObjectName("muted")
        form.addRow("Время:", self._time_label)

        self._lang_combo = QComboBox()
        self._lang_combo.setEditable(True)
        self._lang_combo.setInsertPolicy(QComboBox.InsertPolicy.InsertAtTop)
        self._lang_combo.currentTextChanged.connect(self._on_lang_changed)
        form.addRow("Язык:", self._lang_combo)

        vbox.addLayout(form)

        # Speaker rename block
        spk_frame = QFrame()
        spk_frame.setObjectName("editor_spk_frame")
        spk_vbox = QVBoxLayout(spk_frame)
        spk_vbox.setContentsMargins(12, 10, 12, 10)
        spk_vbox.setSpacing(6)

        spk_hdr = QLabel("Участник")
        spk_hdr.setObjectName("muted")
        spk_vbox.addWidget(spk_hdr)

        spk_row = QHBoxLayout()
        self._speaker_edit = QLineEdit()
        self._speaker_edit.setPlaceholderText("Имя участника")
        self._speaker_edit.textChanged.connect(self._on_speaker_edit_changed)
        spk_row.addWidget(self._speaker_edit, stretch=1)

        apply_btn = QPushButton("Применить")
        apply_btn.clicked.connect(self._apply_speaker)
        spk_row.addWidget(apply_btn)
        spk_vbox.addLayout(spk_row)

        self._rename_all_cb = QCheckBox("Переименовать всех")
        self._rename_all_cb.setChecked(True)
        spk_vbox.addWidget(self._rename_all_cb)

        vbox.addWidget(spk_frame)
        return panel

    # ------------------------------------------------------------------
    # List management
    # ------------------------------------------------------------------

    def _all_speakers(self) -> list[str]:
        seen: list[str] = []
        for seg in self._segments:
            if seg.speaker_id and seg.speaker_id not in seen:
                seen.append(seg.speaker_id)
        return seen

    def _all_languages(self) -> list[str]:
        seen: list[str] = []
        for seg in self._segments:
            if seg.language and seg.language not in seen:
                seen.append(seg.language)
        return seen

    def _rebuild_list(self) -> None:
        # Remove old items
        while self._list_layout.count() > 1:
            item = self._list_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

        speakers = self._all_speakers()
        for i, seg in enumerate(self._segments):
            item = _SegItem(i, seg, speakers)
            item.clicked.connect(
                lambda idx=i: self._on_list_item_clicked(idx)
            )
            if i == self._selected_idx:
                item.setChecked(True)
            self._list_layout.insertWidget(i, item)

        self._update_footer()
        # Refresh timeline (speaker colors may have changed)
        if self._result is not None:
            self._timeline.load(self._segments, self._result.duration_s)
            if self._selected_idx is not None:
                self._timeline.set_selected(self._selected_idx)

    # ------------------------------------------------------------------
    # Segment selection
    # ------------------------------------------------------------------

    def _on_list_item_clicked(self, idx: int) -> None:
        """Called when user explicitly clicks a segment in the list."""
        self._select(idx)
        if self._audio_player.isVisible():
            self._audio_player.seek(self._segments[idx].start_time)

    def _on_playback_position(self, t: float) -> None:
        """Auto-select the segment currently playing. Does not trigger audio seek."""
        if not self._segments:
            return
        for i, seg in enumerate(self._segments):
            if seg.start_time <= t < seg.end_time:
                if i != self._selected_idx:
                    self._playback_select = True
                    try:
                        self._select(i)
                    finally:
                        self._playback_select = False
                break

    def _select(self, idx: int) -> None:
        # Flush current text edit changes before switching
        if self._selected_idx is not None and not self._updating_fields:
            self._flush_text()

        self._selected_idx = idx

        # Update checked state in list and scroll to show selected item
        for i in range(self._list_layout.count() - 1):
            item = self._list_layout.itemAt(i)
            if item and isinstance(item.widget(), _SegItem):
                w = item.widget()
                w.setChecked(w.seg_idx == idx)
                if w.seg_idx == idx:
                    self._seg_scroll.ensureWidgetVisible(w)

        seg = self._segments[idx]
        self._populate_fields(seg)
        self._placeholder.setVisible(False)
        self._editor_panel.setVisible(True)
        self._timeline.set_selected(idx)

    def _populate_fields(self, seg: Segment) -> None:
        self._updating_fields = True
        try:
            self._text_edit.setPlainText(seg.text or "")
            self._time_label.setText(_fmt_range(seg.start_time, seg.end_time))
            self._speaker_edit.setText(seg.speaker_id or "")
            self._rename_all_cb.setText(
                f"Переименовать всех [{seg.speaker_id or '—'}]"
            )

            langs = self._all_languages()
            self._lang_combo.blockSignals(True)
            self._lang_combo.clear()
            for lang in langs:
                self._lang_combo.addItem(lang)
            if seg.language and seg.language not in langs:
                self._lang_combo.addItem(seg.language)
            if seg.language:
                self._lang_combo.setCurrentText(seg.language)
            self._lang_combo.blockSignals(False)
        finally:
            self._updating_fields = False

    def _flush_text(self) -> None:
        if self._selected_idx is None:
            return
        new_text = self._text_edit.toPlainText()
        seg = self._segments[self._selected_idx]
        if seg.text != new_text:
            seg.text = new_text
            self._mark_dirty()
            self._refresh_list_item(self._selected_idx)

    def _refresh_list_item(self, idx: int) -> None:
        item = self._list_layout.itemAt(idx)
        if item and isinstance(item.widget(), _SegItem):
            item.widget()._refresh(self._segments[idx], self._all_speakers())

    # ------------------------------------------------------------------
    # Field change handlers
    # ------------------------------------------------------------------

    def _on_text_changed(self) -> None:
        if self._updating_fields or self._selected_idx is None:
            return
        self._mark_dirty()

    def _on_lang_changed(self, text: str) -> None:
        if self._updating_fields or self._selected_idx is None:
            return
        self._segments[self._selected_idx].language = text.strip() or None
        self._mark_dirty()

    def _on_speaker_edit_changed(self, text: str) -> None:
        if self._selected_idx is None:
            return
        old = self._segments[self._selected_idx].speaker_id or "—"
        self._rename_all_cb.setText(f"Переименовать всех [{old}]")

    def _apply_speaker(self) -> None:
        if self._selected_idx is None:
            return
        new_name = self._speaker_edit.text().strip() or None
        old_name = self._segments[self._selected_idx].speaker_id
        self._segments[self._selected_idx].speaker_id = new_name
        if self._rename_all_cb.isChecked() and old_name:
            for seg in self._segments:
                if seg.speaker_id == old_name:
                    seg.speaker_id = new_name
        self._mark_dirty()
        saved_idx = self._selected_idx
        self._rebuild_list()
        self._select(saved_idx)

    # ------------------------------------------------------------------
    # Header / dirty state
    # ------------------------------------------------------------------

    def _mark_dirty(self) -> None:
        if not self._dirty:
            self._dirty = True
            self._update_header()

    def _update_header(self) -> None:
        self._dirty_badge.setVisible(self._dirty)
        self._revert_btn.setEnabled(self._dirty)

    def _update_footer(self) -> None:
        if self._result:
            self._footer_stats.setText(
                f"run: {self._result.run_id}  ·  "
                f"{len(self._segments)} сегм.  ·  "
                f"{_fmt_time(self._result.duration_s)}"
            )
        self._speaker_legend.refresh(self._all_speakers())

    # ------------------------------------------------------------------
    # Save / revert
    # ------------------------------------------------------------------

    def _save(self) -> None:
        if not self._result:
            return
        self._flush_text()
        updated = TranscriptionResult(
            segments=list(self._segments),
            run_id=self._result.run_id,
            run_dir=self._result.run_dir,
            audio_path=self._result.audio_path,
            duration_s=self._result.duration_s,
        )
        save_run_result(updated)
        self._result = updated
        self._dirty = False
        self._update_header()
        self.saved.emit(updated)

    def _revert(self) -> None:
        if self._dirty:
            reply = QMessageBox.question(
                self,
                "Отменить изменения?",
                "Несохранённые изменения будут потеряны.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        if self._result:
            self._segments = copy.deepcopy(self._result.segments)
            self._dirty = False
            self._selected_idx = None
            self._rebuild_list()
            self._show_placeholder()
            self._update_header()

    def _show_placeholder(self) -> None:
        self._placeholder.setVisible(True)
        self._editor_panel.setVisible(False)
        self._timeline.set_selected(-1)

    def _on_back(self) -> None:
        if self._dirty:
            reply = QMessageBox.question(
                self,
                "Есть несохранённые изменения",
                "Вернуться без сохранения?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        self.back_requested.emit()

    # ------------------------------------------------------------------
    # Export (operates on working copy)
    # ------------------------------------------------------------------

    def _current_as_result(self) -> TranscriptionResult | None:
        if not self._result:
            return None
        self._flush_text()
        return TranscriptionResult(
            segments=list(self._segments),
            run_id=self._result.run_id,
            run_dir=self._result.run_dir,
            audio_path=self._result.audio_path,
            duration_s=self._result.duration_s,
        )

    def _on_copy_all(self) -> None:
        result = self._current_as_result()
        if not result:
            return
        report = build_meeting_report(result)
        lines: list[str] = []
        for grp in report.speakers:
            spk = grp.speaker_id or "Unknown"
            lines.append(
                f"── {spk} ({_fmt_time(grp.total_duration)}, {len(grp.segments)} сегм.) ──"
            )
            for seg in grp.segments:
                lang = f"[{seg.language}] " if seg.language else ""
                lines.append(
                    f"  {_fmt_time(seg.start_time)} – {_fmt_time(seg.end_time)}"
                    f"  {lang}{seg.text or ''}"
                )
        QApplication.clipboard().setText("\n".join(lines))

    def _on_save_json(self) -> None:
        result = self._current_as_result()
        if not result:
            return
        default_name = f"transcript_{result.run_id}.json"
        path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить JSON", default_name, "JSON (*.json)"
        )
        if path:
            export_json(build_meeting_report(result), Path(path))

    def _on_save_txt(self) -> None:
        result = self._current_as_result()
        if not result:
            return
        default_name = f"transcript_{result.run_id}.txt"
        path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить TXT", default_name, "Text (*.txt)"
        )
        if path:
            export_txt(build_meeting_report(result), Path(path))
