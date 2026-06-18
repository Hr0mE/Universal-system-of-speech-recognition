"""Toast-уведомления — всплывающие сообщения в правом нижнем углу окна.

Архитектура:
    ToastLevel  — уровень важности (SUCCESS / INFO / WARNING / ERROR)
    _ToastItem  — единичный виджет-пилюля, позиционируется абсолютно
    ToastManager— управляет стеком, таймерами и перепозиционированием

Использование (один раз в MainWindow.__init__ после _build_ui):
    self._toast = ToastManager(self)

Вызов из любого места:
    self._toast.show("Пайплайн сохранён", ToastLevel.SUCCESS)
    self._toast.show("Ошибка загрузки модели", ToastLevel.ERROR)
    self._toast.show("Загружаю модель…", ToastLevel.INFO, duration_ms=0)
"""

from __future__ import annotations

from enum import Enum

from PySide6.QtCore import QEvent, QObject, QTimer, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QWidget,
)

from ui.qt.scale_manager import load_ui_scale
from ui.qt.theme import ACCENT, ERROR, SUCCESS, WARNING

# ── Layout constants (4px grid) ──────────────────────────────────────────────
_TOAST_WIDTH   = 304   # 76 × 4px
_MARGIN_RIGHT  = 24    #  6 × 4px
_MARGIN_BOTTOM = 24    #  6 × 4px
_ITEM_SPACING  = 8     #  2 × 4px


# ── Level metadata ────────────────────────────────────────────────────────────

class ToastLevel(Enum):
    SUCCESS = "success"
    INFO    = "info"
    WARNING = "warning"
    ERROR   = "error"


# (icon, icon_color, left_accent_color)
_LEVEL_META: dict[ToastLevel, tuple[str, str, str]] = {
    ToastLevel.SUCCESS: ("✓", SUCCESS, "#059669"),
    ToastLevel.INFO:    ("i", ACCENT,  "#4338CA"),
    ToastLevel.WARNING: ("!", WARNING, "#D97706"),
    ToastLevel.ERROR:   ("x", ERROR,   "#DC2626"),
}

_DEFAULT_DURATION_MS: dict[ToastLevel, int] = {
    ToastLevel.SUCCESS: 2500,
    ToastLevel.INFO:    3000,
    ToastLevel.WARNING: 4000,
    ToastLevel.ERROR:   5000,
}


# ── Toast item ────────────────────────────────────────────────────────────────

class _ToastItem(QFrame):
    """Один toast-виджет. Не добавляется в layout — позиционируется через move()."""

    def __init__(
        self,
        message: str,
        level: ToastLevel,
        on_close: object,  # callable(_ToastItem)
        parent: QWidget,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("toast_item")
        self.setProperty("toast_level", level.value)  # used by QSS in theme.py
        self.setFixedWidth(int(_TOAST_WIDTH * load_ui_scale()))
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        icon_char, icon_color, _ = _LEVEL_META[level]

        row = QHBoxLayout(self)
        row.setContentsMargins(16, 12, 12, 12)
        row.setSpacing(12)

        icon_lbl = QLabel(icon_char)
        icon_lbl.setObjectName("toast_icon")
        icon_lbl.setFixedWidth(16)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        # Only color — font-size lives in global QSS and scales automatically
        icon_lbl.setStyleSheet(f"color: {icon_color};")
        row.addWidget(icon_lbl)

        msg_lbl = QLabel(message)
        msg_lbl.setObjectName("toast_msg")
        msg_lbl.setWordWrap(True)
        row.addWidget(msg_lbl, stretch=1)

        close_btn = QPushButton("×")
        close_btn.setObjectName("toast_close_btn")
        close_btn.clicked.connect(lambda: on_close(self))
        row.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignTop)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setOffset(0, 6)
        shadow.setColor(QColor(0, 0, 0, 90))
        self.setGraphicsEffect(shadow)

        self.adjustSize()


# ── Toast manager ─────────────────────────────────────────────────────────────

class ToastManager(QObject):
    """Управляет стеком toast-уведомлений.

    Тосты складываются снизу вверх в правом нижнем углу centralWidget окна.
    Новый тост появляется внизу; старые уходят вверх.
    Автоматически перепозиционируется при изменении размера окна.
    """

    def __init__(self, window: QMainWindow) -> None:
        super().__init__(window)
        self._window  = window
        self._active: list[_ToastItem] = []
        self._timers: dict[int, QTimer] = {}   # id(item) → QTimer
        window.installEventFilter(self)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def show(
        self,
        message: str,
        level: ToastLevel = ToastLevel.INFO,
        *,
        duration_ms: int | None = None,
    ) -> None:
        """Показать toast.

        Args:
            message:     Текст уведомления.
            level:       Уровень важности (ToastLevel).
            duration_ms: Время показа в мс. None — использовать дефолт по уровню.
                         0 — не скрывать автоматически (нужен ручной dismiss).
        """
        parent = self._window.centralWidget()
        if parent is None:
            return

        item = _ToastItem(message, level, self._dismiss, parent)
        item.show()
        self._active.append(item)
        self._reposition_all()

        ms = _DEFAULT_DURATION_MS[level] if duration_ms is None else duration_ms
        if ms > 0:
            timer = QTimer(self)
            timer.setSingleShot(True)
            timer.setInterval(ms)
            timer.timeout.connect(lambda t=item: self._dismiss(t))
            timer.start()
            self._timers[id(item)] = timer

    def dismiss_all(self) -> None:
        """Немедленно скрыть все активные тосты."""
        for item in list(self._active):
            self._dismiss(item)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _dismiss(self, item: _ToastItem) -> None:
        if item not in self._active:
            return
        key = id(item)
        if key in self._timers:
            self._timers[key].stop()
            del self._timers[key]
        self._active.remove(item)
        item.deleteLater()
        self._reposition_all()

    def _reposition_all(self) -> None:
        parent = self._window.centralWidget()
        if parent is None:
            return
        pw = parent.width()
        ph = parent.height()
        y = ph - _MARGIN_BOTTOM
        # newest → bottom; reversed итерация: последний добавленный — ближе к низу
        for item in reversed(self._active):
            item.adjustSize()
            h = item.height()
            y -= h
            x = pw - _TOAST_WIDTH - _MARGIN_RIGHT
            item.move(x, y)
            item.raise_()
            y -= _ITEM_SPACING

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if obj is self._window and event.type() == QEvent.Type.Resize:
            self._reposition_all()
        return False
