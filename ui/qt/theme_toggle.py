"""Animated pill toggle switch for theme selection.

Custom-painted QWidget that slides a thumb between
dark (moon ☾, left) and light (sun ☀, right) with 220 ms cubic easing.
"""

from __future__ import annotations

from PySide6.QtCore import (
    QAbstractAnimation,
    QEasingCurve,
    Property,
    QPropertyAnimation,
    QRectF,
    Qt,
    Signal,
)
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

# ── Color tokens (mirrors theme.py) ─────────────────────────────────────────

_C_DARK_TRACK   = QColor("#232329")          # BORDER
_C_DARK_BORDER  = QColor("#3F3F46")          # BORDER_LIGHT
_C_DARK_THUMB   = QColor("#3F3F46")          # ZINC_700
_C_DARK_ICON    = QColor("#A1A1AA")          # ZINC_400 — muted moon

_C_LIGHT_TRACK  = QColor(99, 102, 241, 30)   # ACCENT_TINT ≈ rgba(99,102,241,0.12)
_C_LIGHT_BORDER = QColor("#6366F1")          # ACCENT
_C_LIGHT_THUMB  = QColor("#FFFFFF")
_C_LIGHT_ICON   = QColor("#6366F1")          # ACCENT — vivid sun

_C_HOV_DARK     = QColor("#52525B")          # ZINC_600 — brighter on hover
_C_HOV_LIGHT    = QColor("#4F46E5")          # ACCENT_HOVER

_ANIM_MS    = 220
_ICON_DARK  = "☾"   # U+263E LAST QUARTER MOON
_ICON_LIGHT = "☀"   # U+2600 BLACK SUN WITH RAYS


# ── Helpers ──────────────────────────────────────────────────────────────────

def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _lerp_color(c1: QColor, c2: QColor, t: float) -> QColor:
    return QColor(
        int(_lerp(c1.red(),   c2.red(),   t)),
        int(_lerp(c1.green(), c2.green(), t)),
        int(_lerp(c1.blue(),  c2.blue(),  t)),
        int(_lerp(c1.alpha(), c2.alpha(), t)),
    )


# ── Widget ───────────────────────────────────────────────────────────────────

class ThemeToggleSwitch(QWidget):
    """Pill-shaped animated toggle: moon left (dark) ↔ sun right (light).

    Usage::

        toggle = ThemeToggleSwitch()
        toggle.set_mode("dark", animated=False)   # initial state
        toggle.toggled.connect(on_theme_toggled)  # no payload — caller reads state

    The widget handles its own animation on click.  Call ``set_mode`` from
    outside (e.g. keyboard shortcut) to drive it externally.
    """

    toggled = Signal()   # emitted after animation begins; no payload

    # Geometry constants (4px grid)
    _W   = 52    # track width
    _H   = 28    # track height
    _D   = 22    # thumb diameter  (H - 2*PAD = 28 - 6 = 22)
    _PAD = 3     # thumb-to-edge padding

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._is_light = False
        self._progress = 0.0    # 0.0 = dark/left  1.0 = light/right
        self._hovered  = False

        self.setFixedSize(self._W, self._H)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Переключить тему (Ctrl+Shift+L)")

        self._anim = QPropertyAnimation(self, b"progress", self)
        self._anim.setDuration(_ANIM_MS)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutCubic)

    # ── Animated property ────────────────────────────────────────────────────

    def _get_progress(self) -> float:
        return self._progress

    def _set_progress(self, value: float) -> None:
        self._progress = value
        self.update()

    progress = Property(float, _get_progress, _set_progress)

    # ── Public API ───────────────────────────────────────────────────────────

    def set_mode(self, mode: str, animated: bool = True) -> None:
        """Apply theme mode, optionally with animation.

        Safe to call while an animation is in progress — will not interrupt
        if the animation is already heading to the correct target.
        """
        target = 1.0 if mode == "light" else 0.0
        self._is_light = (mode == "light")

        # Skip if animation is already heading to the right target
        if (self._anim.state() == QAbstractAnimation.State.Running
                and self._anim.endValue() == target):
            return

        self._anim.stop()
        if animated:
            self._anim.setStartValue(self._progress)
            self._anim.setEndValue(target)
            self._anim.start()
        else:
            self._progress = target
            self.update()

    # ── Events ───────────────────────────────────────────────────────────────

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_light = not self._is_light
            target = 1.0 if self._is_light else 0.0
            self._anim.stop()
            self._anim.setStartValue(self._progress)
            self._anim.setEndValue(target)
            self._anim.start()
            self.toggled.emit()

    def enterEvent(self, event) -> None:  # type: ignore[override]
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # type: ignore[override]
        self._hovered = False
        self.update()
        super().leaveEvent(event)

    # ── Paint ────────────────────────────────────────────────────────────────

    def paintEvent(self, _event) -> None:  # type: ignore[override]
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        t   = self._progress
        W   = self._W
        H   = self._H
        D   = self._D
        PAD = self._PAD

        # ── Track ─────────────────────────────────────────────────────────
        track_bg     = _lerp_color(_C_DARK_TRACK,  _C_LIGHT_TRACK,  t)
        base_border  = _lerp_color(_C_DARK_BORDER, _C_LIGHT_BORDER, t)
        hover_border = _lerp_color(_C_HOV_DARK,    _C_HOV_LIGHT,    t)
        border_color = hover_border if self._hovered else base_border

        track_rect = QRectF(0.5, 0.5, W - 1, H - 1)
        radius = H / 2

        track_path = QPainterPath()
        track_path.addRoundedRect(track_rect, radius, radius)

        p.fillPath(track_path, track_bg)
        p.setPen(QPen(border_color, 1.5))
        p.drawPath(track_path)

        # ── Thumb ─────────────────────────────────────────────────────────
        thumb_x = PAD + (W - 2 * PAD - D) * t
        thumb_y = (H - D) / 2

        # Drop shadow (1.5 px below, semi-transparent)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0, 0, 0, 28))
        p.drawEllipse(QRectF(thumb_x, thumb_y + 1.5, D, D))

        # Thumb body
        thumb_bg = _lerp_color(_C_DARK_THUMB, _C_LIGHT_THUMB, t)
        p.setBrush(thumb_bg)
        thumb_rect = QRectF(thumb_x, thumb_y, D, D)
        p.drawEllipse(thumb_rect)

        # ── Icon ──────────────────────────────────────────────────────────
        icon       = _ICON_LIGHT if t >= 0.5 else _ICON_DARK
        icon_color = _lerp_color(_C_DARK_ICON, _C_LIGHT_ICON, t)

        font = QFont()
        font.setPixelSize(13)
        p.setFont(font)
        p.setPen(icon_color)
        p.drawText(thumb_rect, Qt.AlignmentFlag.AlignCenter, icon)

        p.end()
