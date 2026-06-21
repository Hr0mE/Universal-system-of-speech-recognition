"""Диалог просмотра и выбора модели с HuggingFace Hub.

Позволяет искать модели по типу (ASR/LID/диаризация) и языку,
просматривать результаты в таблице, а затем скачивать выбранную модель
или использовать её repo_id как параметр конфигурации.
"""

from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

_MONTH_RU_IDX: dict[str, int] = {
    "Янв": 1, "Фев": 2, "Мар": 3, "Апр": 4, "Май": 5, "Июн": 6,
    "Июл": 7, "Авг": 8, "Сен": 9, "Окт": 10, "Ноя": 11, "Дек": 12,
}


def _created_sort_key(s: str) -> int:
    """Converts "Окт 2024" → 202410 for numeric comparison, 0 if unknown."""
    if not s:
        return 0
    parts = s.split()
    if len(parts) != 2:
        return 0
    try:
        return int(parts[1]) * 100 + _MONTH_RU_IDX.get(parts[0], 0)
    except ValueError:
        return 0


class _SortableItem(QTableWidgetItem):
    """QTableWidgetItem that sorts by Qt.UserRole raw value, not display text."""

    def __lt__(self, other: "QTableWidgetItem") -> bool:
        a = self.data(Qt.ItemDataRole.UserRole)
        b = other.data(Qt.ItemDataRole.UserRole)
        if a is None:
            a = self.text()
        if b is None:
            b = other.text()
        try:
            return a < b  # type: ignore[operator]
        except TypeError:
            return str(a) < str(b)

from core.hf_catalog import CatalogModel
from ui.qt.hf_download_worker import TASK_TO_HF_TAG, HFDownloadWorker, HFSearchWorker
from ui.qt.scale_manager import load_hf_token, load_ui_scale

_log = logging.getLogger("ui.hf_browser")

_TYPE_LABELS: dict[str, str] = {
    "asr":         "Распознавание речи",
    "language":    "Определение языка",
    "diarization": "Разделение по голосам",
}

_COLS = ["Модель (repo_id)", "↓ Загрузок", "★ Рейтинг", "Параметры", "Вес", "Дата", "Языки", "Кэш"]

# column indices
_COL_REPO   = 0
_COL_DL     = 1
_COL_LIKES  = 2
_COL_PARAMS = 3
_COL_SIZE   = 4
_COL_DATE   = 5
_COL_LANGS  = 6
_COL_CACHE  = 7


def _fmt_count(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.0f}K"
    return str(n) if n else "—"


def _fmt_size(size_bytes: int) -> str:
    if size_bytes <= 0:
        return "—"
    gb = size_bytes / (1024 ** 3)
    if gb >= 1.0:
        return f"{gb:.1f} ГБ"
    mb = size_bytes / (1024 ** 2)
    return f"{mb:.0f} МБ"


def _fmt_langs(langs: list[str]) -> str:
    if not langs:
        return "—"
    if len(langs) > 3:
        return ", ".join(langs[:2]) + f" +{len(langs) - 2}"
    return ", ".join(langs)


class HFBrowserDialog(QDialog):
    """Диалог поиска и выбора модели с HuggingFace Hub.

    Пользователь выбирает тип задачи, фильтрует по языку, запускает поиск,
    выбирает строку в таблице (или вводит repo_id вручную) и нажимает
    «Использовать» или «Скачать».

    Args:
        initial_type: Ключ из ``{"asr", "language", "diarization"}`` —
            предвыбранный тип в комбобоксе.
        parent: Родительский виджет.

    Signals:
        model_selected: Эмитируется с ``repo_id``, когда пользователь
            нажимает «Использовать».
    """

    model_selected = Signal(str, str)   # repo_id, model_type

    def __init__(
        self,
        initial_type: str = "asr",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Обзор моделей HuggingFace")
        self.setMinimumSize(700, 540)
        self.resize(820, 600)
        self.setModal(True)

        self._token = load_hf_token()
        self._results: list[CatalogModel] = []
        self._search_worker: Optional[HFSearchWorker]   = None
        self._dl_worker:     Optional[HFDownloadWorker] = None

        self._build_ui(initial_type)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self, initial_type: str) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        # ── Search bar ──────────────────────────────────────────────
        search_row = QHBoxLayout()
        search_row.setSpacing(8)

        self._type_combo = QComboBox()
        for key, label in _TYPE_LABELS.items():
            self._type_combo.addItem(label, key)
        init_idx = list(_TYPE_LABELS.keys()).index(initial_type) if initial_type in _TYPE_LABELS else 0
        self._type_combo.setCurrentIndex(init_idx)
        self._type_combo.setMinimumWidth(210)
        search_row.addWidget(self._type_combo)

        self._lang_field = QLineEdit()
        self._lang_field.setPlaceholderText("Язык (ru, en…)")
        self._lang_field.setMaximumWidth(130)
        self._lang_field.returnPressed.connect(self._do_search)
        search_row.addWidget(self._lang_field)

        self._search_btn = QPushButton("Поиск")
        self._search_btn.setObjectName("run_btn")
        self._search_btn.setMinimumWidth(int(88 * load_ui_scale()))
        self._search_btn.clicked.connect(self._do_search)
        search_row.addWidget(self._search_btn)

        search_row.addStretch()
        root.addLayout(search_row)

        # ── Status hint ──────────────────────────────────────────────
        self._status_lbl = QLabel("Выберите тип модели и нажмите «Поиск»")
        self._status_lbl.setObjectName("muted")
        root.addWidget(self._status_lbl)

        # ── Results table ────────────────────────────────────────────
        self._table = QTableWidget(0, len(_COLS))
        self._table.setHorizontalHeaderLabels(_COLS)
        self._table.setObjectName("hf_results_table")
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(False)
        self._table.setShowGrid(False)
        self._table.verticalHeader().setVisible(False)
        hh = self._table.horizontalHeader()
        hh.setObjectName("hf_results_table")
        hh.setSortIndicatorShown(True)
        hh.setSectionsClickable(True)
        hh.setSectionResizeMode(_COL_REPO,   QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(_COL_DL,     QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(_COL_LIKES,  QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(_COL_PARAMS, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(_COL_SIZE,   QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(_COL_DATE,   QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(_COL_LANGS,  QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(_COL_CACHE,  QHeaderView.ResizeMode.Fixed)
        hh.resizeSection(_COL_CACHE, 36)
        self._table.itemSelectionChanged.connect(self._on_selection_changed)
        root.addWidget(self._table, stretch=1)

        # ── repo_id field ────────────────────────────────────────────
        repo_row = QHBoxLayout()
        repo_row.setSpacing(8)
        repo_lbl = QLabel("repo_id:")
        repo_lbl.setObjectName("muted")
        repo_lbl.setFixedWidth(60)
        repo_row.addWidget(repo_lbl)
        self._repo_field = QLineEdit()
        self._repo_field.setPlaceholderText("author/model-name  (или введите вручную)")
        self._repo_field.textChanged.connect(self._on_repo_text_changed)
        repo_row.addWidget(self._repo_field, stretch=1)
        root.addLayout(repo_row)

        # ── Download progress bar (indeterminate) ────────────────────
        self._dl_bar = QProgressBar()
        self._dl_bar.setRange(0, 0)
        self._dl_bar.setFixedHeight(4)
        self._dl_bar.setTextVisible(False)
        self._dl_bar.setObjectName("hf_dl_progress")
        self._dl_bar.hide()
        root.addWidget(self._dl_bar)

        # ── Action buttons ───────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_row.addStretch()

        self._dl_btn = QPushButton("Скачать")
        self._dl_btn.setEnabled(False)
        self._dl_btn.clicked.connect(self._do_download)
        btn_row.addWidget(self._dl_btn)

        self._accept_btn = QPushButton("Использовать")
        self._accept_btn.setObjectName("run_btn")
        self._accept_btn.setEnabled(False)
        self._accept_btn.clicked.connect(self._do_accept)
        btn_row.addWidget(self._accept_btn)

        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        root.addLayout(btn_row)

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def _do_search(self) -> None:
        if self._search_worker and self._search_worker.isRunning():
            return

        tag_key      = self._type_combo.currentData()
        pipeline_tag = TASK_TO_HF_TAG.get(tag_key, "automatic-speech-recognition")
        lang         = self._lang_field.text().strip()

        self._search_btn.setEnabled(False)
        self._table.setRowCount(0)
        self._status_lbl.setText("Поиск на HuggingFace Hub…")

        self._search_worker = HFSearchWorker(
            pipeline_tag=pipeline_tag,
            language=lang,
            token=self._token,
            parent=self,
        )
        self._search_worker.results_ready.connect(self._on_results_ready)
        self._search_worker.search_error.connect(self._on_search_error)
        self._search_worker.finished.connect(lambda: self._search_btn.setEnabled(True))
        self._search_worker.start()

    def _on_results_ready(self, results: list) -> None:
        self._results = results
        self._table.setSortingEnabled(False)   # disable during bulk insert
        self._table.setRowCount(0)

        for row_idx, m in enumerate(results):
            self._table.insertRow(row_idx)
            self._table.setRowHeight(row_idx, 32)

            def _item(text: str, sort_val=None, align: Qt.AlignmentFlag | None = None) -> _SortableItem:
                it = _SortableItem(text)
                it.setData(Qt.ItemDataRole.UserRole, sort_val if sort_val is not None else text)
                if align is not None:
                    it.setTextAlignment(align)
                return it

            _ra = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter

            self._table.setItem(row_idx, _COL_REPO,   _item(m.repo_id))
            self._table.setItem(row_idx, _COL_DL,     _item(_fmt_count(m.downloads),    m.downloads,       _ra))
            self._table.setItem(row_idx, _COL_LIKES,  _item(_fmt_count(m.likes),         m.likes,           _ra))
            self._table.setItem(row_idx, _COL_PARAMS, _item(_fmt_count(m.num_parameters), m.num_parameters, _ra))
            self._table.setItem(row_idx, _COL_SIZE,   _item(_fmt_size(m.size_bytes),     m.size_bytes,      _ra))
            self._table.setItem(row_idx, _COL_DATE,   _item(
                m.created_month or "—", _created_sort_key(m.created_month),
            ))
            self._table.setItem(row_idx, _COL_LANGS,  _item(_fmt_langs(m.languages), len(m.languages)))

            cache_text = "✓" if m.cached else "○"
            cache_item = _item(cache_text, int(m.cached), Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(row_idx, _COL_CACHE, cache_item)

        self._table.setSortingEnabled(True)    # re-enable; existing sort indicator applies
        count = len(results)
        self._status_lbl.setText(
            f"Найдено моделей: {count}" if count else "Ничего не найдено — попробуйте другой тип или язык"
        )

    def _on_search_error(self, err: str) -> None:
        self._status_lbl.setText(f"Ошибка поиска: {err}")

    # ------------------------------------------------------------------
    # Selection
    # ------------------------------------------------------------------

    def _on_selection_changed(self) -> None:
        rows = self._table.selectedItems()
        if rows:
            row     = self._table.currentRow()
            repo_id = self._table.item(row, _COL_REPO).text()
            self._repo_field.setText(repo_id)
            cached  = self._table.item(row, _COL_CACHE).text() == "✓"
            self._dl_btn.setEnabled(not cached and not self._is_downloading())

    def _on_repo_text_changed(self, text: str) -> None:
        has_text = bool(text.strip())
        self._accept_btn.setEnabled(has_text)
        if not self._table.selectedItems():
            self._dl_btn.setEnabled(has_text and not self._is_downloading())

    def _is_downloading(self) -> bool:
        return self._dl_worker is not None and self._dl_worker.isRunning()

    # ------------------------------------------------------------------
    # Download
    # ------------------------------------------------------------------

    def _do_download(self) -> None:
        repo_id = self._repo_field.text().strip()
        if not repo_id or self._is_downloading():
            return

        self._dl_btn.setEnabled(False)
        self._accept_btn.setEnabled(False)
        self._search_btn.setEnabled(False)
        self._dl_bar.show()
        self._status_lbl.setText(f"Скачивание {repo_id}…")

        self._dl_worker = HFDownloadWorker(
            repo_id=repo_id,
            token=self._token or None,
            parent=self,
        )
        self._dl_worker.finished_dl.connect(self._on_dl_finished)
        self._dl_worker.error_dl.connect(self._on_dl_error)
        self._dl_worker.start()

    def _on_dl_finished(self, repo_id: str) -> None:
        self._dl_bar.hide()
        self._search_btn.setEnabled(True)
        self._accept_btn.setEnabled(True)
        self._dl_btn.setEnabled(False)
        self._status_lbl.setText(f"✓ Модель {repo_id} скачана")
        # Обновить иконку кэша в таблице
        for row in range(self._table.rowCount()):
            if self._table.item(row, _COL_REPO).text() == repo_id:
                self._table.item(row, _COL_CACHE).setText("✓")
                break

    def _on_dl_error(self, repo_id: str, err: str) -> None:
        self._dl_bar.hide()
        self._search_btn.setEnabled(True)
        self._accept_btn.setEnabled(True)
        self._dl_btn.setEnabled(True)
        self._status_lbl.setText(f"Ошибка загрузки: {err}")

    # ------------------------------------------------------------------
    # Accept
    # ------------------------------------------------------------------

    def _do_accept(self) -> None:
        repo_id = self._repo_field.text().strip()
        if not repo_id:
            return
        model_type = self._type_combo.currentData() or "asr"
        self.model_selected.emit(repo_id, model_type)
        self.accept()

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def selected_repo_id(self) -> str:
        """Возвращает repo_id из поля ввода (или "" если пусто)."""
        return self._repo_field.text().strip()
