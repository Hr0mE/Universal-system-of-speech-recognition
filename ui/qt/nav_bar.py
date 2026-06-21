"""Боковая панель навигации приложения.

Отображает глобальную навигацию сверху, список проектов в центре,
переключатель темы снизу.
"""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt, QSize, Signal
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

from ui.qt.icon_utils import svg_icon
from ui.qt.scale_manager import load_ui_scale
from ui.qt.theme_toggle import ThemeToggleSwitch

from core.domain.project import Project

_NAV_ICON_MAP = {
    "projects": "folder",
    "models":   "server",
    "pipeline": "settings",
}
_ICON_COLOR_DARK  = "#E1E1E6"
_ICON_COLOR_LIGHT = "#18181B"


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


class _ProjectNavItem(QFrame):
    """Кликабельный элемент списка проектов с dot-бейджем статуса."""

    clicked = Signal()

    def __init__(self, project: Project, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.project_id = project.project_id
        self.setObjectName("nav_item")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        dot = QLabel()
        dot.setObjectName("nav_status_dot")
        dot.setFixedSize(8, 8)
        dot.setProperty("status", project.status)

        name = project.name if len(project.name) <= 22 else project.name[:19] + "…"
        name_lbl = QLabel(name)
        name_lbl.setObjectName("nav_item_name")

        age_lbl = QLabel(_relative_time(project.created_at))
        age_lbl.setObjectName("nav_item_age")

        text_col = QVBoxLayout()
        text_col.setContentsMargins(0, 0, 0, 0)
        text_col.setSpacing(1)
        text_col.addWidget(name_lbl)
        text_col.addWidget(age_lbl)

        row = QHBoxLayout(self)
        row.setContentsMargins(10, 6, 10, 6)
        row.setSpacing(8)
        row.addWidget(dot, 0, Qt.AlignmentFlag.AlignVCenter)
        row.addLayout(text_col)
        row.addStretch()

        self.setToolTip(project.audio_path)

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        self.clicked.emit()
        super().mousePressEvent(event)

    def setChecked(self, active: bool) -> None:
        self.setProperty("checked", active)
        self.style().polish(self)


class NavBar(QWidget):
    """Left navigation sidebar: title, global nav, project list, theme toggle."""

    new_project_requested  = Signal()
    project_selected       = Signal(str)   # project_id
    projects_requested     = Signal()
    models_requested       = Signal()
    pipeline_requested     = Signal()
    settings_requested     = Signal()
    theme_toggle_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("nav_bar")
        self._items: dict[str, _ProjectNavItem] = {}
        self._main_btns: dict[str, QPushButton] = {}
        self._add_project_btn: QPushButton | None = None
        self._current_scale: float = load_ui_scale()
        self._current_theme: str = "dark"
        self._build_ui()
        self._update_icons("dark")

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        vbox = QVBoxLayout(self)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)

        # App title
        title = QLabel("Расшифровка")
        title.setObjectName("nav_title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vbox.addWidget(title)

        # Global navigation
        for key, label in (
            ("projects", "Проекты"),
            ("models",   "Модели"),
            ("pipeline", "Обработка"),
        ):
            btn = QPushButton(label)
            btn.setObjectName("nav_main_item")
            btn.setCheckable(True)
            btn.setIconSize(QSize(16, 16))
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            self._main_btns[key] = btn

            if key == "projects":
                # Wrap "Проекты" + "+" in a row
                row_w = QWidget()
                row_w.setObjectName("nav_main_item_row")
                row_l = QHBoxLayout(row_w)
                row_l.setContentsMargins(0, 0, 0, 0)
                row_l.setSpacing(0)
                row_l.addWidget(btn, stretch=1)

                add_btn = QPushButton()
                add_btn.setObjectName("nav_add_btn")
                add_btn.setToolTip("Новый проект")
                add_btn.setFixedWidth(int(32 * self._current_scale))
                add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                add_btn.clicked.connect(self.new_project_requested)
                row_l.addWidget(add_btn)
                self._add_project_btn = add_btn

                vbox.addWidget(row_w)
            else:
                vbox.addWidget(btn)

        self._main_btns["projects"].clicked.connect(self.projects_requested)
        self._main_btns["models"].clicked.connect(self.models_requested)
        self._main_btns["pipeline"].clicked.connect(self.pipeline_requested)

        # Divider between nav and project list
        div1 = QFrame()
        div1.setObjectName("nav_divider")
        div1.setFixedHeight(1)
        vbox.addWidget(div1)

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

        # Divider before theme toggle
        div2 = QFrame()
        div2.setObjectName("nav_divider")
        div2.setFixedHeight(1)
        vbox.addWidget(div2)

        # Theme toggle row
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
                lambda pid=project.project_id: self.project_selected.emit(pid)
            )
            self._list_layout.insertWidget(i, item)
            self._items[project.project_id] = item

    def mark_active(self, project_id: str | None) -> None:
        for pid, item in self._items.items():
            item.setChecked(pid == project_id)

    def mark_section(self, section: str | None) -> None:
        for key, btn in self._main_btns.items():
            btn.setChecked(key == section)

    def _update_icons(self, theme: str) -> None:
        scale = self._current_scale
        nav_size = max(14, int(16 * scale))
        add_size = max(12, int(14 * scale))
        color = _ICON_COLOR_DARK if theme == "dark" else _ICON_COLOR_LIGHT
        for key, btn in self._main_btns.items():
            btn.setIconSize(QSize(nav_size, nav_size))
            btn.setIcon(svg_icon(_NAV_ICON_MAP[key], color, nav_size))
        if self._add_project_btn is not None:
            self._add_project_btn.setIconSize(QSize(add_size, add_size))
            self._add_project_btn.setIcon(svg_icon("plus", color, add_size))

    def update_theme_btn(self, mode: str) -> None:
        self._current_theme = mode
        self._toggle.set_mode(mode, animated=True)
        self._update_icons(mode)

    def set_scale(self, scale: float) -> None:
        self._current_scale = scale
        self._update_icons(self._current_theme)
