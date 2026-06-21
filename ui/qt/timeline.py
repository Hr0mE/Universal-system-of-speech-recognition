"""Горизонтальная временная шкала DAW-стиля для сегментов транскрипта.

Отображает сегменты цветными полосами с поддержкой выбора, наведения,
перетаскиваемой плеголовки, зума и автоскроллинга dead-zone 60%.
Эмитирует ``segment_clicked`` и ``playhead_seek``.
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

_PAD_BASE     = 4
_BAR_TOP_BASE = 2
_BAR_H_BASE   = 32
_RULER_H_BASE = 20

_DEAD_ZONE_MARGIN = 0.20   # 20% отступ с каждой стороны → 60% безопасная зона


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
    """Horizontal DAW-style timeline: segments, drag-to-seek, zoom, dead-zone autoscroll."""

    segment_clicked = Signal(int)
    playhead_seek   = Signal(float)  # seconds — emitted on click or drag

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._segments: list[Segment] = []
        self._duration: float = 0.0
        self._color_map: dict[str | None, str] = {}
        self._selected: int = -1
        self._hover: int = -1
        self._playhead: float = -1.0   # <0 = hidden
        self._scale: float = 1.0
        self._zoom: float = 1.0        # 1.0 = full view, 8.0 = 8× zoom
        self._view_start: float = 0.0  # начало видимого окна (в секундах)
        self._dragging_playhead: bool = False
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
        self._view_start = 0.0
        self._color_map = self._build_color_map()
        self.update()

    def set_selected(self, idx: int) -> None:
        self._selected = idx
        self.update()

    def set_playhead(self, t: float) -> None:
        self._playhead = t
        if self._zoom > 1.0 and self._duration > 0:
            self._scroll_dead_zone(t)
        self.update()

    def set_scale(self, scale: float) -> None:
        self._scale = scale
        self._update_height()
        self.update()

    def set_zoom(self, factor: float) -> None:
        self._zoom = max(1.0, min(8.0, factor))
        if self._zoom <= 1.0:
            self._view_start = 0.0
        elif self._duration > 0:
            visible_dur = self._duration / self._zoom
            self._view_start = max(0.0, min(self._duration - visible_dur, self._view_start))
        self.update()

    def clear(self) -> None:
        self._segments = []
        self._duration = 0.0
        self._color_map = {}
        self._selected = -1
        self._hover = -1
        self._playhead = -1.0
        self._view_start = 0.0
        self._dragging_playhead = False
        self.update()

    # ------------------------------------------------------------------
    # Dead zone autoscroll
    # ------------------------------------------------------------------

    def _scroll_dead_zone(self, t: float) -> None:
        """Сдвигает _view_start так, чтобы t оставался в центральных 60%."""
        visible_dur = self._duration / self._zoom
        margin = visible_dur * _DEAD_ZONE_MARGIN
        safe_right = self._view_start + visible_dur - margin  # 80% позиция
        safe_left  = self._view_start + margin                # 20% позиция

        if t > safe_right:
            self._view_start = t - (visible_dur - margin)
        elif t < safe_left and self._view_start > 0:
            self._view_start = t - margin

        self._view_start = max(0.0, min(self._duration - visible_dur, self._view_start))

    # ------------------------------------------------------------------
    # Scale helpers
    # ------------------------------------------------------------------

    def _s(self, v: int) -> int:
        return max(1, int(v * self._scale))

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
        c = _theme.current_theme_colors()

        pad       = self._s(_PAD_BASE)
        bar_top   = self._s(_BAR_TOP_BASE)
        bar_h     = self._s(_BAR_H_BASE)
        ruler_top = bar_top + bar_h + pad

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

        visible_dur = self._duration / self._zoom
        view_start  = self._view_start

        # Segment bars
        for i, seg in enumerate(self._segments):
            x1, x2, bar_w = self._seg_coords(i, USABLE, visible_dur)
            # Skip segments fully outside the visible window
            if x2 < pad or x1 > W - pad:
                continue
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

        # Playhead — показывать только если находится в видимой зоне
        if self._playhead >= 0:
            rel = self._playhead - view_start
            if 0.0 <= rel <= visible_dur:
                px = pad + int(USABLE * rel / visible_dur)
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

        # Time ruler — стартует с view_start (абсолютное время)
        interval = _ruler_interval(visible_dur)
        font = QFont()
        font.setPointSize(max(6, int(8 * self._scale)))
        p.setFont(font)

        # Выровнять первый тик на кратную отметку
        first_tick = (int(view_start / interval)) * interval
        t = first_tick
        while t <= view_start + visible_dur + 0.01:
            if t >= view_start:
                rx = pad + int(USABLE * (t - view_start) / visible_dur)
                p.setPen(QColor(c.border))
                p.drawLine(rx, ruler_top, rx, ruler_top + self._s(5))
                p.setPen(QColor(c.text))
                p.drawText(rx + 2, ruler_top + self._s(16), _fmt_ruler(t))
            t += interval

    # ------------------------------------------------------------------
    # Mouse
    # ------------------------------------------------------------------

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            x = event.position().x()
            pad = self._s(_PAD_BASE)
            usable = self.width() - 2 * pad

            # Detect grab of playhead (within ±8px of its screen position)
            if self._playhead >= 0 and self._duration > 0 and usable > 0:
                visible_dur = self._duration / self._zoom
                rel = self._playhead - self._view_start
                if 0.0 <= rel <= visible_dur:
                    px = pad + int(usable * rel / visible_dur)
                    if abs(x - px) <= self._s(8):
                        self._dragging_playhead = True
                        return

            # Standard click: select segment + seek
            idx = self._idx_at(x)
            if idx >= 0:
                self.segment_clicked.emit(idx)
            if usable > 0 and self._duration > 0:
                visible_dur = self._duration / self._zoom
                t = self._view_start + (x - pad) / usable * visible_dur
                self.playhead_seek.emit(max(0.0, min(self._duration, t)))

    def mouseMoveEvent(self, event) -> None:
        x = event.position().x()
        pad = self._s(_PAD_BASE)
        usable = self.width() - 2 * pad

        # Playhead drag
        if self._dragging_playhead and self._duration > 0 and usable > 0:
            visible_dur = self._duration / self._zoom
            t = self._view_start + (x - pad) / usable * visible_dur
            t = max(0.0, min(self._duration, t))
            self._playhead = t
            self.playhead_seek.emit(t)
            self.update()
            return

        # Cursor: show SizeHor near playhead
        if self._playhead >= 0 and self._duration > 0 and usable > 0:
            visible_dur = self._duration / self._zoom
            rel = self._playhead - self._view_start
            if 0.0 <= rel <= visible_dur:
                px = pad + int(usable * rel / visible_dur)
                if abs(x - px) <= self._s(8):
                    self.setCursor(Qt.CursorShape.SizeHorCursor)
                else:
                    self.setCursor(Qt.CursorShape.PointingHandCursor)

        # Segment hover
        idx = self._idx_at(x)
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

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging_playhead = False

    def leaveEvent(self, _event) -> None:
        self._hover = -1
        self._dragging_playhead = False
        self.update()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _seg_coords(self, idx: int, usable_w: int, visible_dur: float) -> tuple[int, int, int]:
        seg = self._segments[idx]
        pad = self._s(_PAD_BASE)
        x1 = pad + int(usable_w * (seg.start_time - self._view_start) / visible_dur)
        x2 = pad + int(usable_w * (seg.end_time   - self._view_start) / visible_dur)
        return x1, x2, max(1, x2 - x1)

    def _idx_at(self, x: float) -> int:
        if not self._segments or self._duration <= 0:
            return -1
        pad = self._s(_PAD_BASE)
        usable = self.width() - 2 * pad
        if usable <= 0:
            return -1
        visible_dur = self._duration / self._zoom
        t = self._view_start + (x - pad) / usable * visible_dur
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
