"""Боковая панель навигации приложения.

Отображает список проектов и кнопки навигации:
история запусков, модели, настройки.
"""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ui.qt.theme_toggle import ThemeToggleSwitch

from core.domain.project import Project

_STATUS_ICON = {
    "completed":  "✓",
    "processing": "▶",
    "stopped":    "◼",
    "failed":     "!",
    "empty":      "○",
}


def _relative_time(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso)
        diff = datetime.now() - dt
        seconds = int(diff.total_seconds())
        if seconds < 60:
            return "только что"
        if seconds < 3600:
            return f"{seconds // 60} мин. назад"
        if seconds < 86400:
            return f"{seconds // 3600} ч. назад"
        d = seconds // 86400
        if d == 1:
            return "вчера"
        if d < 30:
            return f"{d} дн. назад"
        if d < 365:
            return f"{d // 30} мес. назад"
        return f"{d // 365} г. назад"
    except Exception:
        return ""


class _ProjectNavItem(QPushButton):
    def __init__(self, project: Project, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.project_id = project.project_id
        self.setObjectName("nav_item")
        self.setCheckable(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        icon = _STATUS_ICON.get(project.status, "○")
        name = project.name
        if len(name) > 22:
            name = name[:19] + "…"
        age = _relative_time(project.created_at)

        self.setText(f"{icon}  {name}\n      {age}")
        self.setToolTip(project.audio_path)


class NavBar(QWidget):
    """Left navigation sidebar: title, new-project CTA, project list, v2 nav section."""

    new_project_requested = Signal()
    project_selected      = Signal(str)   # project_id
    projects_requested    = Signal()
    models_requested      = Signal()
    pipeline_requested    = Signal()
    settings_requested    = Signal()
    theme_toggle_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("nav_bar")
        self._items: dict[str, _ProjectNavItem] = {}
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        vbox = QVBoxLayout(self)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)

        # App title
        title = QLabel("Транскрипция")
        title.setObjectName("nav_title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vbox.addWidget(title)

        # New project button
        new_btn = QPushButton("+ Новый проект")
        new_btn.setObjectName("nav_new_btn")
        new_btn.clicked.connect(self.new_project_requested)
        vbox.addWidget(new_btn)

        # "ПРОЕКТЫ" section label
        proj_lbl = QLabel("ПРОЕКТЫ")
        proj_lbl.setObjectName("nav_section")
        proj_lbl.setContentsMargins(14, 10, 14, 4)
        vbox.addWidget(proj_lbl)

        # Scrollable project list
        scroll = QScrollArea()
        scroll.setObjectName("nav_scroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setFrameShape(scroll.Shape.NoFrame)

        self._list_widget = QWidget()
        self._list_widget.setObjectName("nav_list")
        self._list_layout = QVBoxLayout(self._list_widget)
        self._list_layout.setContentsMargins(8, 4, 8, 4)
        self._list_layout.setSpacing(2)
        self._list_layout.addStretch()

        scroll.setWidget(self._list_widget)
        vbox.addWidget(scroll, stretch=1)

        # ── v2 navigation section ──────────────────────────────────────
        divider = QFrame()
        divider.setObjectName("nav_divider")
        divider.setFixedHeight(1)
        vbox.addWidget(divider)

        nav_lbl = QLabel("НАВИГАЦИЯ")
        nav_lbl.setObjectName("nav_section")
        nav_lbl.setContentsMargins(14, 8, 14, 4)
        vbox.addWidget(nav_lbl)

        for label, signal in (
            ("Проекты",  self.projects_requested),
            ("Модели",   self.models_requested),
            ("Пайплайн", self.pipeline_requested),
        ):
            btn = QPushButton(label)
            btn.setObjectName("nav_item")
            btn.setCheckable(False)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            btn.clicked.connect(signal)
            vbox.addWidget(btn)

        # ── Theme toggle ───────────────────────────────────────────────
        divider2 = QFrame()
        divider2.setObjectName("nav_divider")
        divider2.setFixedHeight(1)
        vbox.addWidget(divider2)

        theme_row = QWidget()
        theme_row_layout = QHBoxLayout(theme_row)
        theme_row_layout.setContentsMargins(14, 6, 14, 6)
        theme_row_layout.setSpacing(0)

        theme_lbl = QLabel("Тема")
        theme_lbl.setObjectName("nav_section")

        self._toggle = ThemeToggleSwitch()
        self._toggle.toggled.connect(self.theme_toggle_requested)

        theme_row_layout.addWidget(theme_lbl)
        theme_row_layout.addStretch()
        theme_row_layout.addWidget(self._toggle)

        vbox.addWidget(theme_row)
        vbox.addSpacing(4)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_projects(self, projects: list[Project]) -> None:
        for item in list(self._items.values()):
            self._list_layout.removeWidget(item)
            item.deleteLater()
        self._items.clear()

        for i, project in enumerate(projects):
            item = _ProjectNavItem(project)
            item.clicked.connect(
                lambda checked=False, pid=project.project_id: self.project_selected.emit(pid)
            )
            self._list_layout.insertWidget(i, item)
            self._items[project.project_id] = item

    def mark_active(self, project_id: str | None) -> None:
        for pid, item in self._items.items():
            item.setChecked(pid == project_id)

    def update_theme_btn(self, mode: str) -> None:
        self._toggle.set_mode(mode, animated=True)
