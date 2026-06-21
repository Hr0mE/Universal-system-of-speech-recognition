"""Экран просмотра доступных и установленных ML-моделей.

Группирует ModelOption по типу (asr, language, diarization) из плагинов
и отображает их полноширинными строками с поиском и фильтрацией по типу.
Кнопка «Добавить модель» открывает :class:`~ui.qt.hf_browser_dialog.HFBrowserDialog`
для поиска и загрузки произвольных моделей.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from core.hf_catalog import is_cached, list_cached_hf_repos
from plugins.manifest import ModelOption, PluginManifest
from ui.qt.hf_download_worker import HFDownloadWorker
from ui.qt.scale_manager import (
    load_custom_models,
    load_hf_token,
    load_ui_scale,
    save_custom_models,
    save_hf_token,
)

_TYPE_LABEL = {
    "asr":         "Распознавание речи",
    "language":    "Определение языка",
    "diarization": "Разделение по голосам",
    "stage":       "Этапы обработки",
}

_TYPE_ORDER = ["asr", "language", "diarization", "stage"]

_TYPE_COLOR = {
    "asr":         "#6366F1",
    "language":    "#FBBF24",
    "diarization": "#34D399",
    "stage":       "#71717A",
}


_FILTER_LABELS = [
    ("all",         "Все"),
    ("asr",         "Речь"),
    ("language",    "Язык"),
    ("diarization", "Голоса"),
    ("stage",       "Этапы"),
]

# По одной "рекомендуемой" модели на каждый тип задачи
_RECOMMENDED_REPOS: frozenset[str] = frozenset({
    "openai/whisper-large-v3",
    "pyannote/speaker-diarization-3.1",
    "facebook/mms-lid-256",
})


def _fmt_size(mb: int) -> str:
    if mb >= 1024:
        return f"{mb / 1024:.1f} ГБ"
    if mb > 0:
        return f"{mb} МБ"
    return "—"


def _speed_tag(size_mb: int) -> tuple[str, str]:
    """Returns (label, objectName) for speed tag based on model size."""
    if size_mb <= 0:
        return "", ""
    if size_mb < 200:
        return "Быстро", "speed_fast"
    if size_mb <= 1500:
        return "Средне", "speed_medium"
    return "Медленно", "speed_slow"


def _guess_model_type(repo_id: str) -> str:
    """Guess model_type from repo_id for models discovered outside the app."""
    lower = repo_id.lower()
    if any(x in lower for x in ("diarization", "speaker", "pyannote")):
        return "diarization"
    if any(x in lower for x in ("lid", "language-id", "language_id", "lang-detect", "mms-lid")):
        return "language"
    return "asr"


def _parse_dl_error(err: str) -> str:
    """Convert raw exception string to a user-readable error reason."""
    e = err.lower()
    if "401" in e or "unauthorized" in e or "credentials" in e:
        return "Токен не настроен или неверный — проверьте HF токен"
    if "no space" in e or "disk" in e or "enospc" in e:
        return "Нет свободного места на диске"
    if "connection" in e or "timeout" in e or "network" in e:
        return "Нет соединения с интернетом"
    if "404" in e or "not found" in e:
        return "Репозиторий не найден на HuggingFace"
    return f"Ошибка загрузки: {err[:80]}" if err else "Неизвестная ошибка загрузки"


# ---------------------------------------------------------------------------
# Model row
# ---------------------------------------------------------------------------

class _ModelRow(QFrame):
    """Полноширинная строка одной модели с цветным маркером, мета-тегами и статус-чипом."""

    download_requested = Signal(str)   # repo_id
    cancel_requested   = Signal(str)   # repo_id
    remove_requested   = Signal(str)   # repo_id (custom models only)

    def __init__(
        self,
        option: ModelOption,
        type_key: str,
        is_custom: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("model_row")
        self._option    = option
        self._type_key  = type_key
        self._is_custom = is_custom
        self._cached    = bool(option.hf_repo and is_cached(option.hf_repo))

        self._status_chip:  Optional[QLabel]       = None
        self._progress_bar: Optional[QProgressBar] = None
        self._dl_btn:       Optional[QPushButton]  = None
        self._cancel_btn:   Optional[QPushButton]  = None

        self._build()

    def _build(self) -> None:
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 12, 0)
        row.setSpacing(0)

        # ── Left accent strip (color-coded by model type) ──────────────
        color = _TYPE_COLOR.get(self._type_key, "#71717A")
        strip = QFrame()
        strip.setFixedWidth(4)
        strip.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        strip.setStyleSheet(
            f"QFrame {{ background: {color}; border-radius: 2px; min-height: 0; }}"
        )
        row.addWidget(strip)
        row.addSpacing(12)

        # ── Name + tags column ────────────────────────────────────────
        name_col = QVBoxLayout()
        name_col.setContentsMargins(0, 4, 0, 4)
        name_col.setSpacing(3)

        # Name row (model title + optional "Своя" badge)
        name_row = QHBoxLayout()
        name_row.setContentsMargins(0, 0, 0, 0)
        name_row.setSpacing(6)

        name_lbl = QLabel(self._option.display_name)
        name_lbl.setObjectName("model_row_name")
        name_row.addWidget(name_lbl)

        if self._is_custom:
            custom_badge = QLabel("Своя")
            custom_badge.setObjectName("custom_badge")
            name_row.addWidget(custom_badge)

        name_row.addStretch()
        name_col.addLayout(name_row)

        # Tags row: speed · languages · recommended
        tags_row = QHBoxLayout()
        tags_row.setContentsMargins(0, 0, 0, 0)
        tags_row.setSpacing(4)

        speed_label, speed_name = _speed_tag(self._option.size_mb)
        if speed_label:
            spd = QLabel(speed_label)
            spd.setObjectName(speed_name)
            tags_row.addWidget(spd)

        langs = self._option.languages
        if not langs or langs == ["all"]:
            if self._option.size_mb > 0:
                lt = QLabel("Мультиязычная")
                lt.setObjectName("lang_tag")
                tags_row.addWidget(lt)
        else:
            for lang in langs[:3]:
                lt = QLabel(lang.upper())
                lt.setObjectName("lang_tag")
                tags_row.addWidget(lt)

        if self._option.hf_repo and self._option.hf_repo in _RECOMMENDED_REPOS:
            rec = QLabel("Рек.")
            rec.setObjectName("recommended_badge")
            tags_row.addWidget(rec)

        tags_row.addStretch()
        name_col.addLayout(tags_row)

        row.addLayout(name_col, stretch=1)
        row.addSpacing(8)

        # ── Size label ────────────────────────────────────────────────
        size_lbl = QLabel(_fmt_size(self._option.size_mb))
        size_lbl.setObjectName("model_row_size")
        size_lbl.setMinimumWidth(int(56 * load_ui_scale()))
        size_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        row.addWidget(size_lbl)

        row.addSpacing(16)

        # ── Action zone ───────────────────────────────────────────────
        zone = QWidget()
        zone.setFixedWidth(220)
        zh = QHBoxLayout(zone)
        zh.setContentsMargins(0, 0, 0, 0)
        zh.setSpacing(8)

        # Status chip
        self._status_chip = QLabel()
        self._status_chip.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        if self._cached:
            self._status_chip.setText("Готова")
            self._status_chip.setObjectName("chip_ready")
        else:
            self._status_chip.setText("Нет")
            self._status_chip.setObjectName("chip_none")
        zh.addWidget(self._status_chip, stretch=1)

        # Progress bar (hidden by default; replaces status chip during download)
        self._progress_bar = QProgressBar()
        self._progress_bar.setObjectName("dl_progress")
        self._progress_bar.setRange(0, 0)
        self._progress_bar.setTextVisible(True)
        self._progress_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._progress_bar.setFixedHeight(22)
        self._progress_bar.hide()
        zh.addWidget(self._progress_bar, stretch=1)

        # Download button (shown when not cached and has hf_repo)
        if not self._cached and self._option.hf_repo:
            self._dl_btn = QPushButton("Загрузить")
            self._dl_btn.setObjectName("card_download_btn")
            self._dl_btn.setMinimumWidth(int(88 * load_ui_scale()))
            self._dl_btn.clicked.connect(self._on_download_clicked)
            zh.addWidget(self._dl_btn)

        # Cancel button (shown during active download)
        self._cancel_btn = QPushButton("Отменить")
        self._cancel_btn.setObjectName("chip_cancel_btn")
        self._cancel_btn.setMinimumWidth(int(76 * load_ui_scale()))
        self._cancel_btn.clicked.connect(self._on_cancel_clicked)
        self._cancel_btn.hide()
        zh.addWidget(self._cancel_btn)

        # Delete button (custom models only)
        if self._is_custom:
            del_btn = QPushButton("×")
            del_btn.setObjectName("custom_del_btn")
            _s = int(16 * load_ui_scale())
            del_btn.setFixedSize(_s, _s)
            del_btn.clicked.connect(
                lambda: self.remove_requested.emit(self._option.hf_repo or "")
            )
            zh.addWidget(del_btn)

        row.addWidget(zone)

    def _on_download_clicked(self) -> None:
        if self._option.hf_repo:
            self.download_requested.emit(self._option.hf_repo)

    def _on_cancel_clicked(self) -> None:
        if self._option.hf_repo:
            self.cancel_requested.emit(self._option.hf_repo)

    # ------------------------------------------------------------------
    # Public state API
    # ------------------------------------------------------------------

    def set_downloading(self, active: bool) -> None:
        if self._status_chip is not None:
            if not active:
                self._status_chip.setObjectName("chip_none")
                self._status_chip.setText("Нет")
                self._status_chip.style().unpolish(self._status_chip)
                self._status_chip.style().polish(self._status_chip)
            self._status_chip.setVisible(not active)

        if self._progress_bar is not None:
            if active:
                self._progress_bar.setRange(0, 0)
                self._progress_bar.setFormat("Загрузка…")
            self._progress_bar.setVisible(active)

        if self._dl_btn is not None:
            self._dl_btn.setVisible(not active)
        if self._cancel_btn is not None:
            self._cancel_btn.setVisible(active)

    def set_progress(self, pct: int) -> None:
        """Update progress bar. pct=-1 → indeterminate animation; 0-100 → fill."""
        if self._progress_bar is None or not self._progress_bar.isVisible():
            return
        if pct < 0:
            self._progress_bar.setRange(0, 0)
            self._progress_bar.setFormat("Загрузка…")
        else:
            self._progress_bar.setRange(0, 100)
            self._progress_bar.setValue(pct)
            self._progress_bar.setFormat(f"Загрузка {pct}%")

    def set_downloaded(self) -> None:
        self._cached = True
        if self._progress_bar is not None:
            self._progress_bar.hide()
        if self._status_chip is not None:
            self._status_chip.setObjectName("chip_ready")
            self._status_chip.setText("Готова")
            self._status_chip.style().unpolish(self._status_chip)
            self._status_chip.style().polish(self._status_chip)
            self._status_chip.show()
        if self._dl_btn is not None:
            self._dl_btn.hide()
        if self._cancel_btn is not None:
            self._cancel_btn.hide()

    def set_error(self, err: str = "") -> None:
        if self._progress_bar is not None:
            self._progress_bar.hide()
        if self._status_chip is not None:
            self._status_chip.setObjectName("chip_error")
            self._status_chip.setText("Ошибка")
            self._status_chip.setToolTip(_parse_dl_error(err))
            self._status_chip.style().unpolish(self._status_chip)
            self._status_chip.style().polish(self._status_chip)
            self._status_chip.show()
        if self._cancel_btn is not None:
            self._cancel_btn.hide()
        if self._dl_btn is not None:
            self._dl_btn.setEnabled(True)
            self._dl_btn.setVisible(True)

    @property
    def repo_id(self) -> str | None:
        return self._option.hf_repo

    def matches_filter(self, type_filter: str, search: str) -> bool:
        if type_filter != "all" and self._type_key != type_filter:
            return False
        if search:
            q = search.lower()
            name_hit = q in self._option.display_name.lower()
            repo_hit = bool(self._option.hf_repo and q in self._option.hf_repo.lower())
            if not (name_hit or repo_hit):
                return False
        return True


# ---------------------------------------------------------------------------
# Section
# ---------------------------------------------------------------------------

class _ManifestSection(QWidget):
    """Одна секция: заголовок типа + вертикальный список строк моделей."""

    download_requested = Signal(str)   # repo_id
    cancel_requested   = Signal(str)   # repo_id

    def __init__(
        self,
        title: str,
        type_key: str,
        options: list[ModelOption],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._rows:        list[_ModelRow]  = []
        self._type_key:    str              = type_key
        self._placeholder: Optional[QLabel] = None

        self._vbox = QVBoxLayout(self)
        self._vbox.setContentsMargins(0, 0, 0, 8)
        self._vbox.setSpacing(3)

        header = QLabel(title)
        header.setObjectName("section_title")
        self._vbox.addWidget(header)

        if options:
            for opt in options:
                row = _ModelRow(opt, type_key)
                row.download_requested.connect(self.download_requested)
                row.cancel_requested.connect(self.cancel_requested)
                self._vbox.addWidget(row)
                self._rows.append(row)
        else:
            self._placeholder = QLabel("Нет доступных моделей")
            self._placeholder.setObjectName("muted")
            self._vbox.addWidget(self._placeholder)

    def add_row(self, row: _ModelRow) -> None:
        """Добавляет строку в конец секции (убирает placeholder если он есть)."""
        if self._placeholder is not None:
            self._placeholder.hide()
            self._placeholder.deleteLater()
            self._placeholder = None
        row.download_requested.connect(self.download_requested)
        row.cancel_requested.connect(self.cancel_requested)
        self._vbox.addWidget(row)
        self._rows.append(row)

    def remove_row(self, repo_id: str) -> None:
        """Удаляет строку с заданным repo_id из секции."""
        for row in list(self._rows):
            if row.repo_id == repo_id:
                self._rows.remove(row)
                self._vbox.removeWidget(row)
                row.hide()
                row.deleteLater()
                return

    def update_visibility(self, type_filter: str, search: str) -> int:
        """Показывает/скрывает строки; скрывает секцию если совпадений нет."""
        visible = 0
        for row in self._rows:
            show = row.matches_filter(type_filter, search)
            row.setVisible(show)
            if show:
                visible += 1
        self.setVisible(visible > 0)
        return visible

    def find_row(self, repo_id: str) -> Optional[_ModelRow]:
        for row in self._rows:
            if row.repo_id == repo_id:
                return row
        return None


# ---------------------------------------------------------------------------
# ModelsScreen
# ---------------------------------------------------------------------------

class ModelsScreen(QWidget):
    """Экран просмотра и загрузки ML-моделей, сгруппированных по типу."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._sections:            list[_ManifestSection]  = []
        self._sections_by_type:    dict[str, _ManifestSection] = {}
        self._active_downloads:    dict[str, HFDownloadWorker] = {}
        self._custom_repo_to_type: dict[str, str]          = load_custom_models()
        self._active_filter:       str                     = "all"
        self._filter_btns:         dict[str, QPushButton]  = {}
        self._pending_repo:        str | None              = None
        self._build_ui()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def refresh(self, manifests: list[PluginManifest]) -> None:
        """Перестраивает строки из заданных манифестов."""
        while self._sections_layout.count() > 1:
            item = self._sections_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()
        self._sections.clear()
        self._sections_by_type.clear()

        by_type: dict[str, list[ModelOption]] = {}
        for m in manifests:
            if m.available_models:
                by_type.setdefault(m.model_type, []).extend(m.available_models)

        inserted = 0
        for type_key in _TYPE_ORDER:
            if type_key not in by_type:
                continue
            title   = _TYPE_LABEL.get(type_key, type_key)
            section = _ManifestSection(title, type_key, by_type[type_key])
            section.download_requested.connect(self._on_download_requested)
            section.cancel_requested.connect(self._on_cancel_requested)
            self._sections_layout.insertWidget(inserted, section)
            self._sections.append(section)
            self._sections_by_type[type_key] = section
            inserted += 1

        if inserted == 0:
            placeholder = QLabel("Плагины не загружены")
            placeholder.setObjectName("muted")
            self._sections_layout.insertWidget(0, placeholder)

        # Collect repo_ids already represented in manifest sections
        shown: set[str] = {
            row.repo_id
            for sec in self._sections
            for row in sec._rows
            if row.repo_id
        }

        # Restore saved custom models (added explicitly by the user in a previous session)
        for repo_id, type_key in self._custom_repo_to_type.items():
            if repo_id not in shown and is_cached(repo_id):
                self._add_custom_model_row(repo_id, type_key, save=False)
                shown.add(repo_id)

        # Surface any other fully-downloaded models from the HF cache
        for repo_id in list_cached_hf_repos():
            if repo_id not in shown:
                self._add_custom_model_row(repo_id, _guess_model_type(repo_id), save=False)
                shown.add(repo_id)

        self._apply_filter()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 32, 32, 32)
        outer.setSpacing(16)

        # Header row
        header = QHBoxLayout()
        title = QLabel("Модели")
        title.setObjectName("screen_title")
        header.addWidget(title)
        header.addStretch()
        add_model_btn = QPushButton("+ Добавить модель")
        add_model_btn.setObjectName("hf_browse_btn")
        add_model_btn.clicked.connect(self._open_browser)
        header.addWidget(add_model_btn)
        outer.addLayout(header)

        # Hint
        hint = QLabel(
            "Загрузите модели заранее или они скачаются сами при первом запуске. "
            "Кэш: ~/.cache/huggingface"
        )
        hint.setObjectName("muted")
        hint.setWordWrap(True)
        outer.addWidget(hint)

        # Filter bar: search + type pills
        filter_bar = QHBoxLayout()
        filter_bar.setSpacing(8)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Поиск моделей…")
        self._search.textChanged.connect(self._apply_filter)
        filter_bar.addWidget(self._search, stretch=1)

        for key, label in _FILTER_LABELS:
            btn = QPushButton(label)
            btn.setObjectName("filter_btn")
            btn.setCheckable(True)
            btn.setChecked(key == "all")
            btn.clicked.connect(lambda _, k=key: self._on_pill_clicked(k))
            filter_bar.addWidget(btn)
            self._filter_btns[key] = btn

        outer.addLayout(filter_bar)

        # HF Token banner (hidden by default; shown when requires_token model is clicked)
        self._token_banner = self._build_token_banner()
        self._token_banner.hide()
        outer.addWidget(self._token_banner)

        # Scrollable sections
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(scroll.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget()
        self._sections_layout = QVBoxLayout(container)
        self._sections_layout.setContentsMargins(0, 0, 0, 0)
        self._sections_layout.setSpacing(20)
        self._sections_layout.addStretch()

        scroll.setWidget(container)
        outer.addWidget(scroll, stretch=1)

    def _build_token_banner(self) -> QFrame:
        banner = QFrame()
        banner.setObjectName("token_banner")

        bh = QHBoxLayout(banner)
        bh.setContentsMargins(12, 8, 12, 8)
        bh.setSpacing(8)

        lbl = QLabel("Для этой модели нужен HuggingFace токен:")
        lbl.setObjectName("muted")
        bh.addWidget(lbl)

        self._token_field = QLineEdit()
        self._token_field.setPlaceholderText("hf_…")
        self._token_field.setEchoMode(QLineEdit.EchoMode.Password)
        saved = load_hf_token()
        if saved:
            self._token_field.setText(saved)
        bh.addWidget(self._token_field, stretch=1)

        save_btn = QPushButton("Сохранить и загрузить")
        save_btn.setObjectName("run_btn")
        save_btn.setMinimumWidth(int(164 * load_ui_scale()))
        save_btn.clicked.connect(self._on_token_banner_save)
        bh.addWidget(save_btn)

        dismiss_btn = QPushButton("×")
        _sd = int(16 * load_ui_scale())
        dismiss_btn.setFixedSize(_sd, _sd)
        dismiss_btn.setObjectName("custom_del_btn")
        dismiss_btn.clicked.connect(lambda: self._token_banner.hide())
        bh.addWidget(dismiss_btn)

        return banner

    # ------------------------------------------------------------------
    # Filter logic
    # ------------------------------------------------------------------

    def _on_pill_clicked(self, key: str) -> None:
        self._active_filter = key
        for k, btn in self._filter_btns.items():
            btn.setChecked(k == key)
        self._apply_filter()

    def _apply_filter(self) -> None:
        search = self._search.text().strip()
        for section in self._sections:
            section.update_visibility(self._active_filter, search)

    # ------------------------------------------------------------------
    # HF Browser Dialog
    # ------------------------------------------------------------------

    def _open_browser(self) -> None:
        from ui.qt.hf_browser_dialog import HFBrowserDialog
        dlg = HFBrowserDialog(initial_type="asr", parent=self)
        dlg.model_selected.connect(self._on_browser_model_selected)
        dlg.exec()

    def _on_browser_model_selected(self, repo_id: str, model_type: str) -> None:
        self._custom_repo_to_type[repo_id] = model_type
        if is_cached(repo_id):
            self._add_custom_model_row(repo_id, model_type)
        else:
            self._start_download(repo_id)

    # ------------------------------------------------------------------
    # Custom model management
    # ------------------------------------------------------------------

    def _add_custom_model_row(self, repo_id: str, type_key: str, *, save: bool = True) -> None:
        """Добавляет строку пользовательской модели в нужную секцию.

        save=True — явное добавление пользователем, сохраняется на диск.
        save=False — восстановление при refresh(), не перезаписывает настройки.
        """
        display_name = repo_id.split("/")[-1] if "/" in repo_id else repo_id
        opt = ModelOption(
            hf_repo=repo_id,
            display_name=display_name,
            languages=[],
            size_mb=0,
        )
        row = _ModelRow(opt, type_key, is_custom=True)
        row.cancel_requested.connect(self._on_cancel_requested)
        row.remove_requested.connect(self._on_remove_requested)

        section = self._sections_by_type.get(type_key)
        if section is None:
            title = _TYPE_LABEL.get(type_key, type_key)
            section = _ManifestSection(title, type_key, [])
            section.download_requested.connect(self._on_download_requested)
            section.cancel_requested.connect(self._on_cancel_requested)
            self._sections_layout.insertWidget(len(self._sections), section)
            self._sections.append(section)
            self._sections_by_type[type_key] = section

        section.add_row(row)
        row.set_downloaded()

        if save:
            self._custom_repo_to_type[repo_id] = type_key
            save_custom_models(self._custom_repo_to_type)

        self._apply_filter()

    def _on_remove_requested(self, repo_id: str) -> None:
        self._custom_repo_to_type.pop(repo_id, None)
        save_custom_models(self._custom_repo_to_type)
        for section in self._sections:
            section.remove_row(repo_id)

    # ------------------------------------------------------------------
    # Download management
    # ------------------------------------------------------------------

    def _on_download_requested(self, repo_id: str) -> None:
        self._start_download(repo_id)

    def _start_download(self, repo_id: str) -> None:
        if repo_id in self._active_downloads:
            return

        # Show token banner if model requires a token and none is saved
        card = self._find_card(repo_id)
        if card is not None and card._option.requires_token and not load_hf_token():
            self._pending_repo = repo_id
            self._token_banner.show()
            return

        token = load_hf_token() or None
        worker = HFDownloadWorker(repo_id=repo_id, token=token, parent=self)
        worker.started_dl.connect(self._on_dl_started)
        worker.progress_dl.connect(self._on_dl_progress)
        worker.finished_dl.connect(self._on_dl_finished)
        worker.error_dl.connect(self._on_dl_error)
        self._active_downloads[repo_id] = worker
        worker.start()

    def _on_cancel_requested(self, repo_id: str) -> None:
        worker = self._active_downloads.get(repo_id)
        if worker and worker.isRunning():
            worker.cancel()
        self._active_downloads.pop(repo_id, None)
        card = self._find_card(repo_id)
        if card:
            card.set_downloading(False)

    def _find_card(self, repo_id: str) -> Optional[_ModelRow]:
        for section in self._sections:
            row = section.find_row(repo_id)
            if row is not None:
                return row
        return None

    def _on_dl_started(self, repo_id: str) -> None:
        card = self._find_card(repo_id)
        if card:
            card.set_downloading(True)

    def _on_dl_progress(self, repo_id: str, pct: int) -> None:
        card = self._find_card(repo_id)
        if card:
            card.set_progress(pct)

    def _on_dl_finished(self, repo_id: str) -> None:
        self._active_downloads.pop(repo_id, None)
        if not is_cached(repo_id):
            # terminate() race: signal arrived but download is incomplete
            card = self._find_card(repo_id)
            if card:
                card.set_downloading(False)
            return
        if repo_id in self._custom_repo_to_type:
            type_key = self._custom_repo_to_type[repo_id]
            self._add_custom_model_row(repo_id, type_key)
        else:
            card = self._find_card(repo_id)
            if card:
                card.set_downloaded()

    def _on_dl_error(self, repo_id: str, err: str) -> None:
        self._active_downloads.pop(repo_id, None)
        card = self._find_card(repo_id)
        if card:
            card.set_error(err)

    # ------------------------------------------------------------------
    # Token banner actions
    # ------------------------------------------------------------------

    def _on_token_banner_save(self) -> None:
        token = self._token_field.text().strip()
        if token:
            save_hf_token(token)
        self._token_banner.hide()
        if self._pending_repo:
            repo = self._pending_repo
            self._pending_repo = None
            self._start_download(repo)
