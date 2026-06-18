"""Горизонтальная временная шкала DAW-стиля для сегментов транскрипта.

Отображает сегменты цветными полосами с поддержкой выбора, наведения и
позиции воспроизведения. Эмитирует ``segment_clicked`` и ``playhead_seek``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QEvent, QPoint, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPolygon
from PySide6.QtWidgets import QToolTip, QWidget

if TYPE_CHECKING:
    from core.pipeline.context import Segment

_SPEAKER_COLORS = ["#818CF8", "#38BDF8", "#34D399", "#FBBF24", "#F87171", "#E879F9"]
_NO_SPEAKER_COLOR = "#64748b"

import ui.qt.theme as _theme
from ui.qt.scale_manager import load_ui_scale

_PAD_BASE     = 4
_BAR_TOP_BASE = 4
_BAR_H_BASE   = 56
_RULER_H_BASE = 22


def _fmt_ruler(seconds: float) -> str:
    s = int(seconds)
    if s < 3600:
        m, sec = divmod(s, 60)
        return f"{m}:{sec:02d}"
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{h}:{m:02d}:{sec:02d}"


def _ruler_interval(duration: float) -> float:
    for step in (10, 30, 60, 120, 300, 600, 1200, 3600):
        if duration / step <= 15:
            return float(step)
    return 3600.0


def _fmt_seg_time(start: float, end: float) -> str:
    return f"{_fmt_ruler(start)} – {_fmt_ruler(end)}"


class TimelineWidget(QWidget):
    """Horizontal DAW-style timeline: segments as color-coded bars, click to select."""

    segment_clicked = Signal(int)
    playhead_seek   = Signal(float)  # seconds — emitted on click anywhere in bar area

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._segments: list[Segment] = []
        self._duration: float = 0.0
        self._color_map: dict[str | None, str] = {}
        self._selected: int = -1
        self._hover: int = -1
        self._playhead: float = -1.0  # <0 = hidden
        self._update_height()
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load(self, segments: list[Segment], total_duration: float) -> None:
        self._segments = segments
        self._duration = max(total_duration, 0.0)
        self._selected = -1
        self._hover = -1
        self._color_map = self._build_color_map()
        self.update()

    def set_selected(self, idx: int) -> None:
        self._selected = idx
        self.update()

    def set_playhead(self, t: float) -> None:
        self._playhead = t
        self.update()

    def clear(self) -> None:
        self._segments = []
        self._duration = 0.0
        self._color_map = {}
        self._selected = -1
        self._hover = -1
        self._playhead = -1.0
        self.update()

    # ------------------------------------------------------------------
    # Scale helpers
    # ------------------------------------------------------------------

    def _s(self, v: int) -> int:
        return max(1, int(v * load_ui_scale()))

    def _update_height(self) -> None:
        bar_top   = self._s(_BAR_TOP_BASE)
        bar_h     = self._s(_BAR_H_BASE)
        ruler_top = bar_top + bar_h + self._s(_PAD_BASE)
        total_h   = ruler_top + self._s(_RULER_H_BASE)
        self.setFixedHeight(total_h)

    def changeEvent(self, event: QEvent) -> None:
        super().changeEvent(event)
        if event.type() == QEvent.Type.StyleChange:
            self._update_height()
            self.update()

    # ------------------------------------------------------------------
    # Paint
    # ------------------------------------------------------------------

    def paintEvent(self, _event) -> None:
        c = _theme.current_theme_colors()   # read at paint time — theme-aware

        pad       = self._s(_PAD_BASE)
        bar_top   = self._s(_BAR_TOP_BASE)
        bar_h     = self._s(_BAR_H_BASE)
        ruler_top = bar_top + bar_h + pad
        ruler_h   = self._s(_RULER_H_BASE)

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        W = self.width()
        USABLE = W - 2 * pad

        # Background
        p.fillRect(self.rect(), QColor(c.bg))

        # Top border
        p.setPen(QColor(c.border))
        p.drawLine(0, 0, W, 0)

        if not self._segments or self._duration <= 0 or USABLE <= 0:
            p.setPen(QColor(c.text))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Нет данных")
            return

        # Segment bars
        for i, seg in enumerate(self._segments):
            x1, x2, bar_w = self._seg_coords(i, USABLE)
            color = QColor(self._color_map.get(seg.speaker_id, _NO_SPEAKER_COLOR))

            if i == self._selected:
                color.setAlpha(220)
                p.fillRect(x1, bar_top, bar_w, bar_h, color)
                pen = QPen(QColor(c.accent), 2)
                p.setPen(pen)
                p.drawRect(x1, bar_top, bar_w - 1, bar_h - 1)
            elif i == self._hover:
                color.setAlpha(180)
                p.fillRect(x1, bar_top, bar_w, bar_h, color)
            else:
                color.setAlpha(110)
                p.fillRect(x1, bar_top, bar_w, bar_h, color)

            # 1px separator on the left edge of each bar
            if bar_w > 1:
                p.setPen(QColor(c.bg_base))
                p.drawLine(x1, bar_top, x1, bar_top + bar_h)

        # Playhead
        if self._playhead >= 0:
            px = pad + int(USABLE * min(self._playhead, self._duration) / self._duration)
            p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            p.setPen(QPen(QColor(c.error), 2))
            p.drawLine(px, bar_top, px, ruler_top + self._s(8))
            p.setBrush(QColor(c.error))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawPolygon(QPolygon([
                QPoint(px - self._s(4), 0),
                QPoint(px + self._s(4), 0),
                QPoint(px, bar_top + self._s(6)),
            ]))
            p.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        # Time ruler
        interval = _ruler_interval(self._duration)
        font = QFont()
        font.setPointSize(max(6, int(8 * load_ui_scale())))
        p.setFont(font)

        t = 0.0
        while t <= self._duration + 0.01:
            rx = pad + int(USABLE * t / self._duration)
            p.setPen(QColor(c.border))
            p.drawLine(rx, ruler_top, rx, ruler_top + self._s(5))
            p.setPen(QColor(c.text))
            p.drawText(rx + 2, ruler_top + self._s(16), _fmt_ruler(t))
            t += interval

    # ------------------------------------------------------------------
    # Mouse
    # ------------------------------------------------------------------

    def mouseMoveEvent(self, event) -> None:
        idx = self._idx_at(event.position().x())
        if idx != self._hover:
            self._hover = idx
            self.update()
        if idx >= 0:
            seg = self._segments[idx]
            spk = seg.speaker_id or "—"
            preview = (seg.text or "")[:80]
            tip = f"{_fmt_seg_time(seg.start_time, seg.end_time)}\n{spk}: {preview}"
            QToolTip.showText(event.globalPosition().toPoint(), tip, self)
        else:
            QToolTip.hideText()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            x = event.position().x()
            idx = self._idx_at(x)
            if idx >= 0:
                self.segment_clicked.emit(idx)
            pad = self._s(_PAD_BASE)
            usable = self.width() - 2 * pad
            if usable > 0 and self._duration > 0:
                t = (x - pad) / usable * self._duration
                self.playhead_seek.emit(max(0.0, t))

    def leaveEvent(self, _event) -> None:
        self._hover = -1
        self.update()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _seg_coords(self, idx: int, usable_w: int) -> tuple[int, int, int]:
        seg = self._segments[idx]
        pad = self._s(_PAD_BASE)
        x1 = pad + int(usable_w * seg.start_time / self._duration)
        x2 = pad + int(usable_w * seg.end_time / self._duration)
        return x1, x2, max(1, x2 - x1)

    def _idx_at(self, x: float) -> int:
        if not self._segments or self._duration <= 0:
            return -1
        pad = self._s(_PAD_BASE)
        usable = self.width() - 2 * pad
        if usable <= 0:
            return -1
        t = (x - pad) / usable * self._duration
        for i, seg in enumerate(self._segments):
            if seg.start_time <= t <= seg.end_time:
                return i
        return -1

    def _build_color_map(self) -> dict[str | None, str]:
        mapping: dict[str | None, str] = {}
        for seg in self._segments:
            sid = seg.speaker_id
            if sid not in mapping:
                mapping[sid] = _SPEAKER_COLORS[len(mapping) % len(_SPEAKER_COLORS)]
        return mapping
