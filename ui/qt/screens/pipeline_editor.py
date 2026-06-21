"""Экран редактора пайплайна транскрибации."""

from __future__ import annotations

from typing import Any

from pathlib import Path

from PySide6.QtCore import QMimeData, QPoint, Qt, Signal
from PySide6.QtGui import QCursor, QDrag
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from core.config.pipeline_config import PipelineConfig, StageConfig, default_pipeline_config
from core.domain.pipeline_preset import PipelinePreset
import core.pipeline.stages as _stages_module  # noqa: F401 — registers StageDescriptors
from core.pipeline.compatibility import (
    StageIssue,
    StagePortState,
    TAG_LABELS,
    check_compatibility,
    compute_port_states,
)
from core.pipeline.stage import all_stage_descriptors, get_stage_descriptor
from core.storage.pipeline_preset_store import PipelinePresetStore
from plugins.manifest import ParamSpec, PluginManifest
from ui.qt.scale_manager import load_ui_scale

_PRESETS_DIR = Path.home() / ".ussr_diplom" / "presets"

# Hex colors for HTML tooltips (dark theme; light theme support deferred)
_TT_OK  = "#34D399"   # SUCCESS
_TT_ERR = "#F87171"   # ERROR
_TT_NEW = "#818CF8"   # ACCENT_TEXT
_TT_OLD = "#71717A"   # TEXT_MUTED


def _left_flap_tooltip(port: StagePortState) -> str:
    """HTML tooltip for the left (input) port flap."""
    if not port.requires:
        return ""
    rows = ["<b>Что нужно этапу:</b>"]
    for tag in sorted(port.requires):
        label = TAG_LABELS.get(tag, tag)
        if tag in port.available_before:
            rows.append(f"<span style='color:{_TT_OK}'>✓ {label}</span>")
        else:
            rows.append(f"<span style='color:{_TT_ERR}'>✗ {label}</span>")
    return "<html><body>" + "<br>".join(rows) + "</body></html>"


def _right_flap_tooltip(port: StagePortState) -> str:
    """HTML tooltip for the right (output) port flap — accumulated stream."""
    if not port.available_after:
        return ""
    rows = ["<b>Накоплено к этому моменту:</b>"]
    # New tags added by this stage (only if enabled → actually in available_after)
    new_tags = port.produces & port.available_after
    for tag in sorted(new_tags):
        rows.append(f"<span style='color:{_TT_NEW}'>▶ {TAG_LABELS.get(tag, tag)}</span>")
    # Older tags (available before this stage)
    for tag in sorted(port.available_before):
        rows.append(f"<span style='color:{_TT_OLD}'>• {TAG_LABELS.get(tag, tag)}</span>")
    if len(rows) == 1:  # header only
        return ""
    return "<html><body>" + "<br>".join(rows) + "</body></html>"


_CARD_WIDTH        = 210
_CARD_HEIGHT       = 240
_SMALL_CARD_WIDTH  = 130
_SMALL_CARD_HEIGHT = 68

# ISO 639-1 codes shown in the language-per-model selector
_LANG_OPTIONS: list[tuple[str, str]] = [
    ("ru", "Русский"),
    ("en", "English"),
    ("zh", "中文"),
    ("de", "Deutsch"),
    ("fr", "Français"),
    ("es", "Español"),
    ("ja", "日本語"),
    ("ko", "한국어"),
    ("ar", "العربية"),
    ("pt", "Português"),
    ("uk", "Українська"),
    ("tr", "Türkçe"),
    ("it", "Italiano"),
    ("nl", "Nederlands"),
    ("pl", "Polski"),
    ("sv", "Svenska"),
]


# ──────────────────────────────────────────────────────────────────────────────
# _LangModelRow — одна строка в секции «Модели по языку»
# ──────────────────────────────────────────────────────────────────────────────

class _LangModelRow(QWidget):
    """Строка «язык → модель + параметры» в диалоге настройки ASR."""

    removed = Signal(object)   # emits self

    def __init__(
        self,
        asr_manifests: list[PluginManifest],
        lang_code: str = "",
        spec: dict | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._manifests = asr_manifests
        self._spec: dict = {k: v for k, v in (spec or {}).items() if k != "model_name"}
        self._param_widgets: dict[str, QWidget] = {}
        self._build(lang_code, (spec or {}).get("model_name", ""))

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def _build(self, lang_code: str, model_name: str) -> None:
        vbox = QVBoxLayout(self)
        vbox.setContentsMargins(0, 2, 0, 2)
        vbox.setSpacing(4)

        # ── Top row: language + model + remove button ──────────────────
        top = QHBoxLayout()
        top.setSpacing(8)

        self._lang_combo = QComboBox()
        self._lang_combo.setMinimumWidth(int(160 * load_ui_scale()))
        for code, name in _LANG_OPTIONS:
            self._lang_combo.addItem(f"{name} ({code})", userData=code)
        for i, (code, _) in enumerate(_LANG_OPTIONS):
            if code == lang_code:
                self._lang_combo.setCurrentIndex(i)
                break
        top.addWidget(self._lang_combo)

        self._model_combo = QComboBox()
        self._model_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        for i, m in enumerate(self._manifests):
            self._model_combo.addItem(m.description or m.name, userData=m.name)
            if m.name == model_name:
                self._model_combo.setCurrentIndex(i)
        self._model_combo.currentIndexChanged.connect(self._on_model_changed)
        top.addWidget(self._model_combo)

        del_btn = QPushButton("✕")
        del_btn.setObjectName("preset_chip_del")
        _s = int(28 * load_ui_scale())
        del_btn.setFixedSize(_s, _s)
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_btn.clicked.connect(lambda: self.removed.emit(self))
        top.addWidget(del_btn)

        vbox.addLayout(top)

        # ── Params row ────────────────────────────────────────────────
        self._params_container = QWidget()
        self._params_layout = QHBoxLayout(self._params_container)
        self._params_layout.setContentsMargins(0, 0, 0, 0)
        self._params_layout.setSpacing(8)
        vbox.addWidget(self._params_container)

        self._rebuild_params()

    # ------------------------------------------------------------------
    # Params
    # ------------------------------------------------------------------

    def _current_manifest(self) -> PluginManifest | None:
        idx = self._model_combo.currentIndex()
        return self._manifests[idx] if 0 <= idx < len(self._manifests) else None

    def _rebuild_params(self) -> None:
        while self._params_layout.count():
            item = self._params_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._param_widgets.clear()

        manifest = self._current_manifest()
        if not manifest or not manifest.params_schema:
            self._params_container.hide()
            return

        self._params_container.show()
        for param_name, pspec in manifest.params_schema.items():
            lbl = QLabel(pspec.description or param_name)
            lbl.setObjectName("muted")
            self._params_layout.addWidget(lbl)
            val = self._spec.get(param_name, pspec.default)
            widget = self._make_param_widget(pspec, val)
            self._param_widgets[param_name] = widget
            self._params_layout.addWidget(widget)

        self._params_layout.addStretch()

    def _make_param_widget(self, spec: ParamSpec, value: Any) -> QWidget:
        if spec.type == "enum" and spec.values:
            combo = QComboBox()
            for v in spec.values:
                combo.addItem(v, userData=v)
            idx = spec.values.index(str(value)) if str(value) in spec.values else 0
            combo.setCurrentIndex(idx)
            combo.setMinimumWidth(72)
            return combo
        if spec.type == "bool":
            cb = QCheckBox()
            cb.setChecked(bool(value))
            return cb
        if spec.type == "int":
            sb = QSpinBox()
            sb.setRange(-99999, 99999)
            sb.setValue(int(value) if value is not None else int(spec.default))
            sb.setMinimumWidth(56)
            return sb
        if spec.type == "float":
            dsb = QDoubleSpinBox()
            dsb.setRange(-99999.0, 99999.0)
            dsb.setDecimals(3)
            dsb.setValue(float(value) if value is not None else float(spec.default))
            dsb.setMinimumWidth(72)
            return dsb
        le = QLineEdit()
        le.setText(str(value) if value is not None else str(spec.default))
        le.setMinimumWidth(72)
        return le

    def _on_model_changed(self, _index: int) -> None:
        manifest = self._current_manifest()
        if manifest:
            self._spec = {k: v.default for k, v in manifest.params_schema.items()}
        self._rebuild_params()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def collect(self) -> tuple[str, dict]:
        """Returns (lang_code, spec_dict) where spec_dict includes model_name + params."""
        lang_code: str = self._lang_combo.currentData() or ""
        manifest = self._current_manifest()
        if not manifest:
            return lang_code, {}

        result: dict = {"model_name": manifest.name}
        for param_name, widget in self._param_widgets.items():
            if isinstance(widget, QComboBox):
                result[param_name] = widget.currentData() or widget.currentText()
            elif isinstance(widget, QCheckBox):
                result[param_name] = widget.isChecked()
            elif isinstance(widget, (QSpinBox, QDoubleSpinBox)):
                result[param_name] = widget.value()
            elif isinstance(widget, QLineEdit):
                result[param_name] = widget.text()
        return lang_code, result


# ──────────────────────────────────────────────────────────────────────────────
# StageConfigDialog
# ──────────────────────────────────────────────────────────────────────────────

class StageConfigDialog(QDialog):
    """Модальный диалог настройки одного этапа пайплайна."""

    store_requested = Signal()

    def __init__(
        self,
        stage_config: StageConfig,
        manifests: list[PluginManifest],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._stage_config = stage_config
        self._manifests = manifests
        self._param_widgets: dict[str, QWidget] = {}
        self._descriptor = get_stage_descriptor(stage_config.stage_id)
        self._is_algo = self._descriptor is not None and self._descriptor.model_type is None

        stage_label = (self._descriptor.display_name if self._descriptor else stage_config.stage_id).replace("\n", " ")
        self.setWindowTitle(f"{stage_label} — Настройка")
        self.setMinimumWidth(420)
        self._build_ui()

    def get_result(self) -> StageConfig:
        if self._is_algo:
            model_name = ""
        else:
            manifest = self._current_manifest()
            model_name = manifest.name if manifest else self._stage_config.model_name

        lang_model_map: dict[str, dict] = {}
        if hasattr(self, "_lang_rows"):
            for row in self._lang_rows:
                lang_code, spec = row.collect()
                if lang_code:
                    lang_model_map[lang_code] = spec

        return StageConfig(
            stage_id=self._stage_config.stage_id,
            enabled=self._stage_config.enabled,
            model_name=model_name,
            params=self._collect_params(),
            lang_model_map=lang_model_map,
        )

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 16)
        root.setSpacing(14)

        self._model_section = QWidget()
        model_row = QHBoxLayout(self._model_section)
        model_row.setContentsMargins(0, 0, 0, 0)
        model_row.addWidget(QLabel("Модель:"))
        self._model_combo = QComboBox()
        self._model_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._populate_model_combo()
        self._model_combo.currentIndexChanged.connect(self._on_model_changed)
        model_row.addWidget(self._model_combo)
        if self._is_algo:
            self._model_section.hide()
        root.addWidget(self._model_section)

        self._params_widget = QWidget()
        self._params_layout = QVBoxLayout(self._params_widget)
        self._params_layout.setContentsMargins(0, 0, 0, 0)
        self._params_layout.setSpacing(8)
        root.addWidget(self._params_widget)
        self._build_param_widgets()

        if self._stage_config.stage_id == "asr":
            self._build_lang_map_section(root)

        root.addStretch()

        btn_row = QHBoxLayout()
        self._store_btn = QPushButton("Магазин моделей")
        self._store_btn.clicked.connect(self._on_store)
        if self._is_algo:
            self._store_btn.hide()
        btn_row.addWidget(self._store_btn)
        btn_row.addStretch()
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        btn_row.addWidget(buttons)
        root.addLayout(btn_row)

    def _populate_model_combo(self) -> None:
        _d = get_stage_descriptor(self._stage_config.stage_id)
        model_type = _d.model_type if _d else ""
        self._filtered_manifests = [m for m in self._manifests if m.model_type == model_type]
        self._model_combo.blockSignals(True)
        self._model_combo.clear()
        current_idx = 0
        for i, m in enumerate(self._filtered_manifests):
            self._model_combo.addItem(m.description or m.name, userData=m.name)
            if m.name == self._stage_config.model_name:
                current_idx = i
        self._model_combo.setCurrentIndex(current_idx)
        self._model_combo.blockSignals(False)

    def _algo_param_schema(self) -> dict[str, ParamSpec]:
        """Синтезирует схему параметров для алгоритмических этапов из default_params."""
        if not self._descriptor:
            return {}
        result: dict[str, ParamSpec] = {}
        for k, v in self._descriptor.default_params.items():
            if isinstance(v, bool):
                result[k] = ParamSpec(type="bool", default=v, description=k)
            elif isinstance(v, int):
                result[k] = ParamSpec(type="int", default=v, description=k)
            elif isinstance(v, float):
                result[k] = ParamSpec(type="float", default=v, description=k)
            else:
                result[k] = ParamSpec(type="string", default=str(v), description=k)
        return result

    def _build_param_widgets(self) -> None:
        while self._params_layout.count():
            item = self._params_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._param_widgets.clear()

        schema: dict[str, ParamSpec]
        if self._is_algo:
            schema = self._algo_param_schema()
        else:
            manifest = self._current_manifest()
            schema = manifest.params_schema if manifest else {}

        if not schema:
            lbl = QLabel("Нет настраиваемых параметров")
            lbl.setObjectName("muted")
            self._params_layout.addWidget(lbl)
            return

        for param_name, spec in schema.items():
            row = QHBoxLayout()
            lbl = QLabel(spec.description or param_name)
            lbl.setMinimumWidth(160)
            row.addWidget(lbl)
            current_val = self._stage_config.params.get(param_name, spec.default)
            widget = self._make_param_widget(spec, current_val)
            self._param_widgets[param_name] = widget
            row.addWidget(widget)
            c = QWidget()
            c.setLayout(row)
            self._params_layout.addWidget(c)

    def _make_param_widget(self, spec: ParamSpec, value: Any) -> QWidget:
        if spec.type == "enum" and spec.values:
            combo = QComboBox()
            for v in spec.values:
                combo.addItem(v, userData=v)
            idx = spec.values.index(str(value)) if str(value) in spec.values else 0
            combo.setCurrentIndex(idx)
            return combo
        if spec.type == "bool":
            cb = QCheckBox()
            cb.setChecked(bool(value))
            return cb
        if spec.type == "int":
            sb = QSpinBox()
            sb.setRange(-99999, 99999)
            sb.setValue(int(value) if value is not None else int(spec.default))
            return sb
        if spec.type == "float":
            dsb = QDoubleSpinBox()
            dsb.setRange(-99999.0, 99999.0)
            dsb.setDecimals(3)
            dsb.setValue(float(value) if value is not None else float(spec.default))
            return dsb
        le = QLineEdit()
        le.setText(str(value) if value is not None else str(spec.default))
        return le

    def _collect_params(self) -> dict[str, Any]:
        schema = self._algo_param_schema() if self._is_algo else (
            m.params_schema if (m := self._current_manifest()) else {}
        )
        if not schema:
            return dict(self._stage_config.params)
        result: dict[str, Any] = {}
        for param_name, spec in schema.items():
            widget = self._param_widgets.get(param_name)
            if widget is None:
                result[param_name] = self._stage_config.params.get(param_name, spec.default)
            elif isinstance(widget, QComboBox):
                result[param_name] = widget.currentData() or widget.currentText()
            elif isinstance(widget, QCheckBox):
                result[param_name] = widget.isChecked()
            elif isinstance(widget, (QSpinBox, QDoubleSpinBox)):
                result[param_name] = widget.value()
            elif isinstance(widget, QLineEdit):
                result[param_name] = widget.text()
            else:
                result[param_name] = spec.default
        return result

    def _current_manifest(self) -> PluginManifest | None:
        if not hasattr(self, "_filtered_manifests") or not self._filtered_manifests:
            return None
        idx = self._model_combo.currentIndex()
        return self._filtered_manifests[idx] if 0 <= idx < len(self._filtered_manifests) else None

    def _on_model_changed(self, _index: int) -> None:
        manifest = self._current_manifest()
        if manifest:
            merged = {k: v.default for k, v in manifest.params_schema.items()}
            for k, v in self._stage_config.params.items():
                if k in merged:
                    merged[k] = v
            self._stage_config = StageConfig(
                stage_id=self._stage_config.stage_id,
                enabled=self._stage_config.enabled,
                model_name=manifest.name,
                params=merged,
            )
        self._build_param_widgets()

    def _on_store(self) -> None:
        self.store_requested.emit()
        self.reject()

    # ------------------------------------------------------------------
    # Lang-model mapping section (ASR only)
    # ------------------------------------------------------------------

    def _build_lang_map_section(self, root: QVBoxLayout) -> None:
        self.setMinimumWidth(520)

        sep = QFrame()
        sep.setObjectName("nav_divider")
        sep.setFixedHeight(1)
        root.addWidget(sep)

        hdr = QHBoxLayout()
        hdr.setContentsMargins(0, 4, 0, 0)
        lbl = QLabel("Модели по языку")
        lbl.setObjectName("section_title")
        hdr.addWidget(lbl)
        hdr.addStretch()
        add_btn = QPushButton("+ Добавить язык")
        add_btn.setFixedHeight(28)
        add_btn.clicked.connect(self._on_add_lang_row)
        hdr.addWidget(add_btn)
        root.addLayout(hdr)

        hint = QLabel("Если язык определён автоматически — используется соответствующая модель вместо дефолтной.")
        hint.setObjectName("muted")
        hint.setWordWrap(True)
        root.addWidget(hint)

        self._lang_rows: list[_LangModelRow] = []
        self._lang_rows_widget = QWidget()
        self._lang_rows_layout = QVBoxLayout(self._lang_rows_widget)
        self._lang_rows_layout.setContentsMargins(0, 0, 0, 0)
        self._lang_rows_layout.setSpacing(2)
        self._lang_rows_layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self._lang_rows_widget)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setMinimumHeight(40)
        scroll.setMaximumHeight(200)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        root.addWidget(scroll)

        self._asr_manifests = [m for m in self._manifests if m.model_type == "asr"]
        for lang_code, spec in self._stage_config.lang_model_map.items():
            self._insert_lang_row(lang_code, spec)

    def _insert_lang_row(self, lang_code: str = "", spec: dict | None = None) -> None:
        row = _LangModelRow(self._asr_manifests, lang_code=lang_code, spec=spec)
        row.removed.connect(self._on_remove_lang_row)
        self._lang_rows.append(row)
        count = self._lang_rows_layout.count()
        self._lang_rows_layout.insertWidget(count - 1, row)

    def _on_add_lang_row(self) -> None:
        self._insert_lang_row()

    def _on_remove_lang_row(self, row: object) -> None:
        r = row  # type: ignore[assignment]
        if r in self._lang_rows:
            self._lang_rows.remove(r)
        self._lang_rows_layout.removeWidget(r)  # type: ignore[arg-type]
        r.deleteLater()  # type: ignore[attr-defined]


# ──────────────────────────────────────────────────────────────────────────────
# Sidebar item — перетаскиваемый элемент в боковой панели
# ──────────────────────────────────────────────────────────────────────────────

class _SidebarItem(QLabel):
    """Строка в боковой панели этапов. Перетаскиваемая когда этап не на доске."""

    _MIME_PREFIX = "sidebar:"
    double_clicked = Signal(str)  # stage_id — only when off_board

    def __init__(self, stage_id: str, name: str, parent: QWidget | None = None) -> None:
        super().__init__(name, parent)
        self._stage_id = stage_id
        self._drag_start: QPoint | None = None
        self.setObjectName("sidebar_stage_item")
        self.set_state("off_board")

    def set_state(self, state: str) -> None:
        self.setProperty("item_state", state)
        self.style().polish(self)

    def mousePressEvent(self, event):  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):  # type: ignore[override]
        if (
            self._drag_start is None
            or not (event.buttons() & Qt.MouseButton.LeftButton)
            or self.property("item_state") != "off_board"
        ):
            return
        if (event.position().toPoint() - self._drag_start).manhattanLength() < 8:
            return
        self._drag_start = None
        drag = QDrag(self)
        mime = QMimeData()
        mime.setText(self._MIME_PREFIX + self._stage_id)
        drag.setMimeData(mime)
        drag.exec(Qt.DropAction.MoveAction)

    def mouseReleaseEvent(self, event):  # type: ignore[override]
        self._drag_start = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):  # type: ignore[override]
        if (
            event.button() == Qt.MouseButton.LeftButton
            and self.property("item_state") == "off_board"
        ):
            self.double_clicked.emit(self._stage_id)
        else:
            super().mouseDoubleClickEvent(event)




# ──────────────────────────────────────────────────────────────────────────────
# Port indicators
# ──────────────────────────────────────────────────────────────────────────────

class _PortFlap(QFrame):
    """Colored 12×48px flap on the left or right edge of a StageTile.

    Left flap  — input status: green (all met) / red (missing) / gray (none required).
    Right flap — always gray; tooltip shows accumulated stream tags.

    Mouse and drag events are forwarded to the parent tile so drag-to-reorder
    works from anywhere on the tile including over the flaps.
    """

    def __init__(self, side: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("port_flap_left" if side == "left" else "port_flap_right")
        self.setFixedSize(12, 48)
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.setAcceptDrops(False)

    def set_state(self, flap_state: str, tooltip: str = "") -> None:
        self.setProperty("flap_state", flap_state)
        self.style().polish(self)
        self.setToolTip(tooltip)

    def mousePressEvent(self, event) -> None:    # type: ignore[override]
        event.ignore()

    def mouseMoveEvent(self, event) -> None:     # type: ignore[override]
        event.ignore()

    def mouseReleaseEvent(self, event) -> None:  # type: ignore[override]
        event.ignore()

    def wheelEvent(self, event) -> None:         # type: ignore[override]
        event.ignore()


class _TileStatusBar(QFrame):
    """4px bottom strip for SmallStageTile split into input (left) and output (right).

    Left half colour:  green (ok) / red (error) / gray (neutral).
    Right half colour: always gray; tooltip shows accumulated stream tags.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("tile_status_bar")
        self.setFixedHeight(4)
        self.setAcceptDrops(False)

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)

        self._in_bar = QFrame()
        self._in_bar.setObjectName("tile_bar_in")
        row.addWidget(self._in_bar, stretch=1)

        self._out_bar = QFrame()
        self._out_bar.setObjectName("tile_bar_out")
        row.addWidget(self._out_bar, stretch=1)

    def set_state(self, in_state: str, in_tip: str = "", out_tip: str = "") -> None:
        self._in_bar.setProperty("bar_state", in_state)
        self._in_bar.style().polish(self._in_bar)
        self._in_bar.setToolTip(in_tip)
        self._out_bar.setToolTip(out_tip)

    def mousePressEvent(self, event) -> None:    # type: ignore[override]
        event.ignore()

    def mouseMoveEvent(self, event) -> None:     # type: ignore[override]
        event.ignore()

    def mouseReleaseEvent(self, event) -> None:  # type: ignore[override]
        event.ignore()


# ──────────────────────────────────────────────────────────────────────────────
# StageTile — большая вертикальная карточка
# ──────────────────────────────────────────────────────────────────────────────

class StageTile(QFrame):
    """Карточка этапа пайплайна.

    - Клик по карточке переключает включён/выключен (кроме кнопки «Настроить»).
    - Перетаскивание за любое место карточки инициирует QDrag для переупорядочивания.
    - Номер в левом верхнем углу обновляется через :meth:`set_number`.
    - Включён — фиолетовая рамка/подсветка, выключен — серая.
    """

    toggle_changed   = Signal(str, bool)  # stage_id, enabled
    config_requested = Signal(str)        # stage_id
    swap_requested   = Signal(str, str)   # src_stage_id, dst_stage_id

    def __init__(
        self,
        stage_config: StageConfig,
        number: int = 1,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._stage_config = stage_config
        self._drag_start: QPoint | None = None
        self.setObjectName("stage_tile")
        self.setFixedSize(_CARD_WIDTH, _CARD_HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setAcceptDrops(True)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self._build(number)
        self._apply_state()

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def stage_config(self) -> StageConfig:
        return self._stage_config

    def set_number(self, n: int) -> None:
        self._num_lbl.setText(str(n))

    def update_config(self, cfg: StageConfig) -> None:
        self._stage_config = cfg
        self._model_lbl.setText(cfg.model_name)
        self._apply_state()

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def _build(self, number: int) -> None:
        cfg = self._stage_config
        # Inner padding shrinks 12px on each side to leave room for flaps
        vbox = QVBoxLayout(self)
        vbox.setContentsMargins(26, 12, 26, 14)
        vbox.setSpacing(0)

        # ── Шапка: номер слева ────────────────────────────────────────
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(0)

        self._num_lbl = QLabel(str(number))
        self._num_lbl.setObjectName("stage_num")
        self._num_lbl.setFixedSize(22, 22)
        self._num_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.addWidget(self._num_lbl)
        header.addStretch()

        vbox.addLayout(header)
        vbox.addSpacing(10)

        # ── Название этапа (центр) ────────────────────────────────────
        _d = get_stage_descriptor(cfg.stage_id)
        name_lbl = QLabel(_d.display_name if _d else cfg.stage_id)
        name_lbl.setObjectName("stage_card_title")
        name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_lbl.setWordWrap(True)
        vbox.addWidget(name_lbl)

        # ── Растяжка — прижимает модель и кнопку к низу ──────────────
        vbox.addStretch()

        # ── Название модели (снизу, над кнопкой) ─────────────────────
        self._model_lbl = QLabel(cfg.model_name)
        self._model_lbl.setObjectName("stage_card_model")
        self._model_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._model_lbl.setWordWrap(True)
        vbox.addWidget(self._model_lbl)

        vbox.addSpacing(8)

        # ── Кнопка настройки ──────────────────────────────────────────
        btn = QPushButton("Настроить")
        btn.setCursor(Qt.CursorShape.ArrowCursor)
        btn.clicked.connect(lambda: self.config_requested.emit(cfg.stage_id))
        vbox.addWidget(btn)

        # ── Флэпы (абсолютное позиционирование поверх карточки) ───────
        self._left_flap  = _PortFlap("left",  parent=self)
        self._right_flap = _PortFlap("right", parent=self)
        self._left_flap.set_state("neutral")
        self._right_flap.set_state("neutral")
        self._position_flaps()

    def _position_flaps(self) -> None:
        h = self.height()
        flap_h = min(48, h - 16)
        y = (h - flap_h) // 2
        self._left_flap.setFixedHeight(flap_h)
        self._right_flap.setFixedHeight(flap_h)
        self._left_flap.move(0, y)
        self._right_flap.move(self.width() - 12, y)
        self._left_flap.raise_()
        self._right_flap.raise_()

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._position_flaps()

    # ------------------------------------------------------------------
    # State → visual
    # ------------------------------------------------------------------

    def _apply_state(self) -> None:
        self.setProperty("tile_state", "on" if self._stage_config.enabled else "off")
        self.style().polish(self)

    def set_port_state(self, port: StagePortState | None) -> None:
        """Update left/right flaps based on port compatibility snapshot."""
        if port is None or not self._stage_config.enabled:
            self._left_flap.set_state("neutral")
            self._right_flap.set_state("neutral", "")
            return

        left_state = "error" if port.issue else ("ok" if port.requires else "neutral")
        self._left_flap.set_state(left_state, _left_flap_tooltip(port))
        self._right_flap.set_state("neutral", _right_flap_tooltip(port))

    def set_warning(self, issue: StageIssue | None) -> None:
        if issue is not None:
            tags = ", ".join(TAG_LABELS.get(t, t) for t in sorted(issue.missing_tags))
            self.setToolTip(f"Требуется: {tags}")
        else:
            self.setToolTip("")

    # ------------------------------------------------------------------
    # Click → toggle / drag → reorder
    # Toggle fires on release only when the mouse didn't travel (no drag).
    # ------------------------------------------------------------------

    def mousePressEvent(self, event):  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start = event.position().toPoint()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):  # type: ignore[override]
        if self._drag_start is None or not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        if (event.position().toPoint() - self._drag_start).manhattanLength() < 12:
            return
        self._drag_start = None
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        drag = QDrag(self)
        mime = QMimeData()
        mime.setText(self._stage_config.stage_id)
        pixmap = self.grab()
        small = pixmap.scaled(
            pixmap.width() * 2 // 3,
            pixmap.height() * 2 // 3,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        drag.setPixmap(small)
        drag.setHotSpot(QPoint(small.width() // 2, 12))
        drag.setMimeData(mime)
        drag.exec(Qt.DropAction.MoveAction)

    def mouseReleaseEvent(self, event):  # type: ignore[override]
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        if event.button() == Qt.MouseButton.LeftButton and self._drag_start is not None:
            # No drag happened → treat as toggle click
            self._drag_start = None
            new_enabled = not self._stage_config.enabled
            self._stage_config = StageConfig(
                self._stage_config.stage_id,
                new_enabled,
                self._stage_config.model_name,
                self._stage_config.params,
                self._stage_config.lang_model_map,
            )
            self._apply_state()
            self.toggle_changed.emit(self._stage_config.stage_id, new_enabled)
        else:
            self._drag_start = None
        super().mouseReleaseEvent(event)

    # ------------------------------------------------------------------
    # Drop target
    # ------------------------------------------------------------------

    def dragEnterEvent(self, event):  # type: ignore[override]
        text = event.mimeData().text()
        if (
            event.mimeData().hasText()
            and not text.startswith(_SidebarItem._MIME_PREFIX)
            and text != self._stage_config.stage_id
        ):
            self.setProperty("drag_over", True)
            self.style().polish(self)
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):  # type: ignore[override]
        self.setProperty("drag_over", False)
        self.style().polish(self)
        super().dragLeaveEvent(event)

    def dropEvent(self, event):  # type: ignore[override]
        src_id = event.mimeData().text()
        self.setProperty("drag_over", False)
        self.style().polish(self)
        self.swap_requested.emit(src_id, self._stage_config.stage_id)
        event.acceptProposedAction()


# ──────────────────────────────────────────────────────────────────────────────
# SmallStageTile — компактная карточка (малый режим)
# ──────────────────────────────────────────────────────────────────────────────

class SmallStageTile(QFrame):
    """Компактная карточка этапа для плотного режима сетки (130×68 px).

    Клик — toggle включения/выключения.
    Правый клик — контекстное меню «Настроить».
    Drag & drop работает так же, как у :class:`StageTile`.
    """

    toggle_changed   = Signal(str, bool)
    config_requested = Signal(str)
    swap_requested   = Signal(str, str)

    def __init__(
        self,
        stage_config: StageConfig,
        number: int = 1,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._stage_config = stage_config
        self._drag_start: QPoint | None = None
        self.setObjectName("stage_tile")
        self.setFixedSize(_SMALL_CARD_WIDTH, _SMALL_CARD_HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setAcceptDrops(True)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self._build(number)
        self._apply_state()

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def stage_config(self) -> StageConfig:
        return self._stage_config

    def set_number(self, n: int) -> None:
        self._num_lbl.setText(str(n))

    def update_config(self, cfg: StageConfig) -> None:
        self._stage_config = cfg
        self._model_lbl.setText(cfg.model_name or "")
        self._apply_state()

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def _build(self, number: int) -> None:
        cfg = self._stage_config
        vbox = QVBoxLayout(self)
        vbox.setContentsMargins(8, 8, 8, 8)
        vbox.setSpacing(4)

        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        top.setSpacing(4)

        self._num_lbl = QLabel(str(number))
        self._num_lbl.setObjectName("stage_num")
        self._num_lbl.setFixedSize(18, 18)
        self._num_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        top.addWidget(self._num_lbl)

        _d = get_stage_descriptor(cfg.stage_id)
        name = (_d.display_name if _d else cfg.stage_id).replace("\n", " ")
        name_lbl = QLabel(name)
        name_lbl.setObjectName("stage_card_title_sm")
        name_lbl.setWordWrap(False)
        name_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        top.addWidget(name_lbl, stretch=1)
        vbox.addLayout(top)

        self._model_lbl = QLabel(cfg.model_name or "")
        self._model_lbl.setObjectName("stage_card_model")
        self._model_lbl.setWordWrap(False)
        vbox.addWidget(self._model_lbl)
        vbox.addStretch()

        # ── Статус-полоска (абсолютно внизу карточки) ─────────────────
        self._status_bar = _TileStatusBar(parent=self)
        self._status_bar.setFixedWidth(self.width())
        self._status_bar.move(0, self.height() - 4)
        self._status_bar.raise_()

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._status_bar.setFixedWidth(self.width())
        self._status_bar.move(0, self.height() - 4)

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------

    def _apply_state(self) -> None:
        self.setProperty("tile_state", "on" if self._stage_config.enabled else "off")
        self.style().polish(self)

    def set_port_state(self, port: StagePortState | None) -> None:
        """Update status bar based on port compatibility snapshot."""
        if port is None or not self._stage_config.enabled:
            self._status_bar.set_state("neutral")
            return

        in_state = "error" if port.issue else ("ok" if port.requires else "neutral")
        self._status_bar.set_state(
            in_state,
            in_tip=_left_flap_tooltip(port),
            out_tip=_right_flap_tooltip(port),
        )

    def set_warning(self, issue: StageIssue | None) -> None:
        if issue is not None:
            tags = ", ".join(TAG_LABELS.get(t, t) for t in sorted(issue.missing_tags))
            self.setToolTip(f"Требуется: {tags}")
        else:
            self.setToolTip("")

    # ------------------------------------------------------------------
    # Mouse — click to toggle, drag to reorder
    # ------------------------------------------------------------------

    def mousePressEvent(self, event):  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start = event.position().toPoint()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):  # type: ignore[override]
        if self._drag_start is None or not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        if (event.position().toPoint() - self._drag_start).manhattanLength() < 12:
            return
        self._drag_start = None
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        drag = QDrag(self)
        mime = QMimeData()
        mime.setText(self._stage_config.stage_id)
        pixmap = self.grab()
        small = pixmap.scaled(
            pixmap.width() * 2 // 3, pixmap.height() * 2 // 3,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        drag.setPixmap(small)
        drag.setHotSpot(QPoint(small.width() // 2, 8))
        drag.setMimeData(mime)
        drag.exec(Qt.DropAction.MoveAction)

    def mouseReleaseEvent(self, event):  # type: ignore[override]
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        if event.button() == Qt.MouseButton.LeftButton and self._drag_start is not None:
            self._drag_start = None
            new_enabled = not self._stage_config.enabled
            self._stage_config = StageConfig(
                self._stage_config.stage_id, new_enabled,
                self._stage_config.model_name, self._stage_config.params,
                self._stage_config.lang_model_map,
            )
            self._apply_state()
            self.toggle_changed.emit(self._stage_config.stage_id, new_enabled)
        else:
            self._drag_start = None
        super().mouseReleaseEvent(event)

    def contextMenuEvent(self, event):  # type: ignore[override]
        menu = QMenu(self)
        act = menu.addAction("Настроить…")
        if menu.exec(event.globalPos()) == act:
            self.config_requested.emit(self._stage_config.stage_id)

    # ------------------------------------------------------------------
    # Drop target
    # ------------------------------------------------------------------

    def dragEnterEvent(self, event):  # type: ignore[override]
        text = event.mimeData().text()
        if (
            event.mimeData().hasText()
            and not text.startswith(_SidebarItem._MIME_PREFIX)
            and text != self._stage_config.stage_id
        ):
            self.setProperty("drag_over", True)
            self.style().polish(self)
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):  # type: ignore[override]
        self.setProperty("drag_over", False)
        self.style().polish(self)
        super().dragLeaveEvent(event)

    def dropEvent(self, event):  # type: ignore[override]
        src_id = event.mimeData().text()
        self.setProperty("drag_over", False)
        self.style().polish(self)
        self.swap_requested.emit(src_id, self._stage_config.stage_id)
        event.acceptProposedAction()


# ──────────────────────────────────────────────────────────────────────────────
# Card grid — адаптивная сетка карточек
# ──────────────────────────────────────────────────────────────────────────────

class _StageCardGrid(QWidget):
    """Адаптивная сетка карточек этапов.

    Количество столбцов вычисляется автоматически по ширине виджета.
    Drag & drop: вставка по позиции курсора; карточка-на-карточку — swap.
    Должна быть помещена внутрь внешнего QScrollArea.
    """

    stage_toggled          = Signal(str, bool)
    stage_config_requested = Signal(str)
    stages_changed         = Signal()

    _SPACING = 12

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._cards: list[StageTile | SmallStageTile] = []
        self._all_configs: dict[str, StageConfig] = {}
        self._cols: int = 3
        self._view_mode: str = "large"
        self._pending_drop_idx: int = -1

        self._layout = QGridLayout(self)
        self._layout.setContentsMargins(0, 8, 0, 8)
        self._layout.setHorizontalSpacing(self._SPACING)
        self._layout.setVerticalSpacing(self._SPACING)

        self._list_placeholder = QLabel("Вид списка\n— в разработке", self)
        self._list_placeholder.setObjectName("muted")
        self._list_placeholder.setAlignment(
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter
        )
        self._list_placeholder.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self._list_placeholder.hide()

        # Floating drop indicator (not in layout)
        self._drop_line = QFrame(self)
        self._drop_line.setObjectName("drop_gap")
        self._drop_line.setProperty("drop_gap_active", "true")
        self._drop_line.setFixedWidth(4)
        self._drop_line.hide()

        self.setAcceptDrops(True)

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._update_cols()

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def load_stages(self, stages: list[StageConfig]) -> None:
        for card in self._cards:
            card.hide()
            card.deleteLater()
        self._cards.clear()
        for i, cfg in enumerate(stages):
            card = self._make_tile(cfg, i + 1)
            card.toggle_changed.connect(self._on_toggle)
            card.config_requested.connect(self.stage_config_requested)
            card.swap_requested.connect(self._on_swap)
            self._cards.append(card)
        self._rebuild_layout()

    def current_stages(self) -> list[StageConfig]:
        return [c.stage_config() for c in self._cards]

    def update_stage_config(self, updated: StageConfig) -> None:
        for card in self._cards:
            if card.stage_config().stage_id == updated.stage_id:
                card.update_config(updated)
                break

    def update_stage_enabled(self, stage_id: str, enabled: bool) -> None:
        for card in self._cards:
            if card.stage_config().stage_id == stage_id:
                cfg = card.stage_config()
                card.update_config(StageConfig(cfg.stage_id, enabled, cfg.model_name, cfg.params, cfg.lang_model_map))
                break

    def update_warnings(self, issues: dict[str, StageIssue]) -> None:
        for card in self._cards:
            card.set_warning(issues.get(card.stage_config().stage_id))

    def update_port_states(self, port_states: dict[str, StagePortState]) -> None:
        for card in self._cards:
            card.set_port_state(port_states.get(card.stage_config().stage_id))

    def set_all_configs(self, configs: dict[str, StageConfig]) -> None:
        self._all_configs = configs

    def remove_stage(self, stage_id: str) -> None:
        idx = next((i for i, c in enumerate(self._cards) if c.stage_config().stage_id == stage_id), -1)
        if idx < 0:
            return
        card = self._cards.pop(idx)
        card.deleteLater()
        self._rebuild_layout()
        self.stages_changed.emit()

    def add_stage_at_end(self, stage_id: str) -> None:
        self._add_stage_at(stage_id, len(self._cards))

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _update_cols(self) -> None:
        if self._view_mode == "list":
            return
        available = self.width()
        if available <= 0:
            return
        card_w = _SMALL_CARD_WIDTH if self._view_mode == "small" else _CARD_WIDTH
        new_cols = max(1, available // (card_w + self._SPACING))
        if new_cols != self._cols:
            self._cols = new_cols
            self._rebuild_layout()

    def set_view_mode(self, mode: str) -> None:
        """Переключает режим: ``"large"``, ``"small"`` или ``"list"``."""
        if mode == self._view_mode:
            return
        stages = [c.stage_config() for c in self._cards]
        self._view_mode = mode
        if mode != "list":
            avail = self.width()
            if avail > 0:
                card_w = _SMALL_CARD_WIDTH if mode == "small" else _CARD_WIDTH
                self._cols = max(1, avail // (card_w + self._SPACING))
        self.load_stages(stages)

    def _make_tile(self, cfg: StageConfig, number: int) -> "StageTile | SmallStageTile":
        if self._view_mode == "small":
            return SmallStageTile(cfg, number)
        return StageTile(cfg, number)

    def _rebuild_layout(self) -> None:
        while self._layout.count():
            self._layout.takeAt(0)
        self._list_placeholder.hide()

        # Reset stretches from previous build
        for c in range(self._layout.columnCount() + 1):
            self._layout.setColumnStretch(c, 0)
        for r in range(self._layout.rowCount() + 1):
            self._layout.setRowStretch(r, 0)

        if self._view_mode == "list":
            self._list_placeholder.show()
            self._layout.addWidget(self._list_placeholder, 0, 0)
            self._layout.setRowStretch(0, 1)
            self._layout.setColumnStretch(0, 1)
            return

        for i, card in enumerate(self._cards):
            row, col = divmod(i, self._cols)
            self._layout.addWidget(card, row, col)

        # Push empty space to bottom-right so cards stay top-left
        n_rows = max(1, (len(self._cards) + self._cols - 1) // self._cols) if self._cards else 1
        self._layout.setColumnStretch(self._cols, 1)
        self._layout.setRowStretch(n_rows, 1)

        self._update_numbers()

    def _update_numbers(self) -> None:
        for i, card in enumerate(self._cards):
            card.set_number(i + 1)

    def _on_toggle(self, stage_id: str, enabled: bool) -> None:
        self.update_stage_enabled(stage_id, enabled)
        self.stage_toggled.emit(stage_id, enabled)
        self.stages_changed.emit()

    def _on_swap(self, src_id: str, dst_id: str) -> None:
        src_idx = next((i for i, c in enumerate(self._cards) if c.stage_config().stage_id == src_id), -1)
        dst_idx = next((i for i, c in enumerate(self._cards) if c.stage_config().stage_id == dst_id), -1)
        if src_idx < 0 or dst_idx < 0 or src_idx == dst_idx:
            return
        self._cards[src_idx], self._cards[dst_idx] = self._cards[dst_idx], self._cards[src_idx]
        self._rebuild_layout()
        self.stages_changed.emit()

    def _add_stage_at(self, stage_id: str, idx: int) -> None:
        cfg = self._all_configs.get(stage_id)
        if cfg is None:
            return
        card = self._make_tile(cfg, 1)
        card.toggle_changed.connect(self._on_toggle)
        card.config_requested.connect(self.stage_config_requested)
        card.swap_requested.connect(self._on_swap)
        self._cards.insert(idx, card)
        self._rebuild_layout()
        self.stages_changed.emit()

    # ------------------------------------------------------------------
    # Drop target — insert-by-position for empty-space/between-card drops;
    # card-on-card swap is handled by StageTile.dropEvent / _on_swap.
    # ------------------------------------------------------------------

    def dragEnterEvent(self, event) -> None:  # type: ignore[override]
        if event.mimeData().hasText():
            text = event.mimeData().text()
            skip = "" if text.startswith(_SidebarItem._MIME_PREFIX) else text
            self._pending_drop_idx = self._calc_insert_idx(
                event.position().toPoint(), skip
            )
            self._update_drop_line()
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event) -> None:  # type: ignore[override]
        if event.mimeData().hasText():
            text = event.mimeData().text()
            skip = "" if text.startswith(_SidebarItem._MIME_PREFIX) else text
            self._pending_drop_idx = self._calc_insert_idx(
                event.position().toPoint(), skip
            )
            self._update_drop_line()
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragLeaveEvent(self, event) -> None:  # type: ignore[override]
        self._drop_line.hide()
        self._pending_drop_idx = -1
        super().dragLeaveEvent(event)

    def dropEvent(self, event) -> None:  # type: ignore[override]
        self._drop_line.hide()
        self._pending_drop_idx = -1
        if not event.mimeData().hasText():
            event.ignore()
            return

        text = event.mimeData().text()
        from_sidebar = text.startswith(_SidebarItem._MIME_PREFIX)
        stage_id = text[len(_SidebarItem._MIME_PREFIX):] if from_sidebar else text

        skip = "" if from_sidebar else stage_id
        idx = self._calc_insert_idx(event.position().toPoint(), skip)

        if from_sidebar:
            already = any(c.stage_config().stage_id == stage_id for c in self._cards)
            if not already:
                self._add_stage_at(stage_id, idx)
        else:
            src_idx = next(
                (i for i, c in enumerate(self._cards)
                 if c.stage_config().stage_id == stage_id),
                -1,
            )
            if src_idx >= 0:
                card = self._cards.pop(src_idx)
                if src_idx < idx:
                    idx -= 1
                self._cards.insert(idx, card)
                self._rebuild_layout()
                self.stages_changed.emit()

        event.acceptProposedAction()

    # ------------------------------------------------------------------
    # Insertion-point helpers
    # ------------------------------------------------------------------

    def _calc_insert_idx(self, pos: QPoint, skip_id: str) -> int:
        """Nearest insertion index for cursor at ``pos`` (widget-local coords)."""
        if not self._cards:
            return 0

        best_idx = len(self._cards)
        best_dist: float = float("inf")

        for i, card in enumerate(self._cards):
            if skip_id and card.stage_config().stage_id == skip_id:
                continue
            geo = card.geometry()
            cy = geo.center().y()

            # Gap BEFORE card i
            gx = geo.left() - self._SPACING // 2
            d = abs(pos.x() - gx) * 2 + abs(pos.y() - cy)
            if d < best_dist:
                best_dist = d
                best_idx = i

            # Gap AFTER card i
            gx = geo.right() + self._SPACING // 2
            d = abs(pos.x() - gx) * 2 + abs(pos.y() - cy)
            if d < best_dist:
                best_dist = d
                best_idx = i + 1

        return max(0, min(best_idx, len(self._cards)))

    def _update_drop_line(self) -> None:
        """Positions and shows the drop indicator for _pending_drop_idx."""
        idx = self._pending_drop_idx
        if idx < 0 or self._view_mode == "list" or not self._cards:
            self._drop_line.hide()
            return

        if idx == 0:
            ref = self._cards[0].geometry()
            x = max(0, ref.left() - self._SPACING // 2 - 2)
            y, h = ref.top(), ref.height()
        elif idx >= len(self._cards):
            ref = self._cards[-1].geometry()
            x = ref.right() + self._SPACING // 2 - 2
            y, h = ref.top(), ref.height()
        else:
            prev = self._cards[idx - 1].geometry()
            nxt  = self._cards[idx].geometry()
            if abs(prev.top() - nxt.top()) < 10:
                x = (prev.right() + nxt.left()) // 2 - 2
                y, h = prev.top(), prev.height()
            else:
                x = prev.right() + self._SPACING // 2 - 2
                y, h = prev.top(), prev.height()

        self._drop_line.setFixedSize(4, max(4, h))
        self._drop_line.move(x, y)
        self._drop_line.show()
        self._drop_line.raise_()

# ──────────────────────────────────────────────────────────────────────────────
# Clickable header bar for the sidebar
# ──────────────────────────────────────────────────────────────────────────────

class _ClickableBar(QFrame):
    """Полоса-кнопка: клик в любом месте испускает clicked."""

    clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event):  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


# ──────────────────────────────────────────────────────────────────────────────
# Stages sidebar
# ──────────────────────────────────────────────────────────────────────────────

class _StageSidebar(QWidget):
    """Правая панель с перечнем всех этапов пайплайна.

    - Активные (включённые) — фиолетовый.
    - Неактивные (выключенные) — белый/основной текст.
    - Не на доске — серый.
    - Кнопка ›/‹ сворачивает панель в узкую полоску.
    """

    collapse_toggled            = Signal(bool)  # True = свёрнут
    remove_from_board_requested = Signal(str)  # stage_id
    add_to_board_requested      = Signal(str)  # stage_id (double-click on off_board item)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._collapsed = False
        self.setObjectName("pipeline_sidebar")
        self.setMinimumWidth(120)
        self.setAcceptDrops(True)
        self._build_ui()

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def update_states(
        self,
        stages: list[StageConfig],
        issues: dict[str, StageIssue] | None = None,
    ) -> None:
        """Обновляет цветовое состояние каждого элемента списка."""
        on_board = {s.stage_id for s in stages}
        active = {s.stage_id for s in stages if s.enabled}
        for sid, item in self._rows.items():
            if sid not in on_board:
                state = "off_board"
            elif sid in active:
                state = "active"
            else:
                state = "inactive"
            item.set_state(state)

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        vbox = QVBoxLayout(self)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)
        vbox.setAlignment(Qt.AlignmentFlag.AlignTop)  # кнопка всегда прилипает к верху

        # ── Заголовочная полоса — вся кликабельна ────────────────────
        self._top_bar = _ClickableBar()
        self._top_bar.setObjectName("sidebar_bar")
        self._top_bar.setFixedHeight(40)
        self._top_bar.setToolTip("Свернуть панель")
        self._top_bar.setProperty("bar_collapsed", "false")
        self._top_bar.clicked.connect(self._on_toggle)
        self._bar_row = QHBoxLayout(self._top_bar)
        self._bar_row.setContentsMargins(8, 0, 8, 0)
        self._bar_row.setSpacing(4)

        self._title_lbl = QLabel("ЭТАПЫ")
        self._title_lbl.setObjectName("sidebar_title")
        sp = self._title_lbl.sizePolicy()
        sp.setRetainSizeWhenHidden(False)
        self._title_lbl.setSizePolicy(sp)
        self._bar_row.addWidget(self._title_lbl)
        self._bar_row.addStretch()

        self._arrow_lbl = QLabel("›")
        self._arrow_lbl.setObjectName("sidebar_arrow")
        self._arrow_lbl.setFixedSize(20, 20)
        self._arrow_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._bar_row.addWidget(self._arrow_lbl)

        vbox.addWidget(self._top_bar)

        # ── Список этапов ─────────────────────────────────────────────
        self._list_area = QScrollArea()
        self._list_area.setWidgetResizable(True)
        self._list_area.setFrameShape(QFrame.Shape.NoFrame)
        self._list_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        _sp = self._list_area.sizePolicy()
        _sp.setRetainSizeWhenHidden(False)
        self._list_area.setSizePolicy(_sp)

        list_container = QWidget()
        list_layout = QVBoxLayout(list_container)
        list_layout.setContentsMargins(6, 6, 6, 6)
        list_layout.setSpacing(2)

        self._rows: dict[str, _SidebarItem] = {}
        for descriptor in all_stage_descriptors():
            name = descriptor.display_name.replace("\n", " ")
            item = _SidebarItem(descriptor.stage_id, name)
            item.double_clicked.connect(self.add_to_board_requested)
            list_layout.addWidget(item)
            self._rows[descriptor.stage_id] = item

        list_layout.addStretch()
        self._list_area.setWidget(list_container)
        vbox.addWidget(self._list_area)

    # ------------------------------------------------------------------
    # Drop target (принимает карточки с доски)
    # ------------------------------------------------------------------

    def dragEnterEvent(self, event):  # type: ignore[override]
        text = event.mimeData().text()
        if event.mimeData().hasText() and not text.startswith(_SidebarItem._MIME_PREFIX):
            self._set_drop_highlight(True)
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):  # type: ignore[override]
        self._set_drop_highlight(False)
        super().dragLeaveEvent(event)

    def dropEvent(self, event):  # type: ignore[override]
        self._set_drop_highlight(False)
        text = event.mimeData().text()
        if not text.startswith(_SidebarItem._MIME_PREFIX):
            self.remove_from_board_requested.emit(text)
        event.acceptProposedAction()

    def _set_drop_highlight(self, on: bool) -> None:
        self.setProperty("sidebar_drop_active", "true" if on else "false")
        self.style().polish(self)

    # ------------------------------------------------------------------
    # Toggle collapse
    # ------------------------------------------------------------------

    def _on_toggle(self) -> None:
        self._collapsed = not self._collapsed
        self._list_area.setVisible(not self._collapsed)
        self._title_lbl.setVisible(not self._collapsed)
        if self._collapsed:
            self._arrow_lbl.setText("‹")
            self._top_bar.setToolTip("Развернуть панель")
        else:
            self._arrow_lbl.setText("›")
            self._top_bar.setToolTip("Свернуть панель")
        self._top_bar.setProperty("bar_collapsed", "true" if self._collapsed else "false")
        self._top_bar.style().polish(self._top_bar)
        self.collapse_toggled.emit(self._collapsed)


# ──────────────────────────────────────────────────────────────────────────────
# _PresetChip — пилюля-чип одного пресета
# ──────────────────────────────────────────────────────────────────────────────

class _PresetChip(QFrame):
    """Горизонтальный чип пресета с кнопкой удаления и поддержкой DnD-переупорядочивания."""

    clicked    = Signal(object)   # PipelinePreset
    delete_req = Signal(str)      # preset_id
    move_req   = Signal(str, str) # src_preset_id → dst_preset_id

    _MIME = "preset:"

    def __init__(self, preset: PipelinePreset, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._preset = preset
        self._drag_start: QPoint | None = None
        self.setObjectName("preset_chip")
        self.setAcceptDrops(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._build()
        self._apply_state("")

    @property
    def preset(self) -> PipelinePreset:
        return self._preset

    def set_state(self, state: str) -> None:
        """state: 'saved' | 'active' | '' """
        self._apply_state(state)

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def _build(self) -> None:
        row = QHBoxLayout(self)
        row.setContentsMargins(10, 0, 4, 0)
        row.setSpacing(4)

        name = self._preset.name
        if len(name) > 20:
            name = name[:18] + "…"
        self._name_lbl = QLabel(name)
        self._name_lbl.setToolTip(self._preset.name)
        self._name_lbl.setObjectName("chip_label")
        row.addWidget(self._name_lbl)

        del_btn = QPushButton("✕")
        del_btn.setObjectName("preset_chip_del")
        del_btn.setToolTip("Удалить пресет")
        del_btn.setCursor(Qt.CursorShape.ArrowCursor)
        del_btn.clicked.connect(lambda: self.delete_req.emit(self._preset.preset_id))
        row.addWidget(del_btn)

    def _apply_state(self, state: str) -> None:
        self.setProperty("chip_state", state)
        self.setProperty("chip_drop", "false")
        self.style().polish(self)
        self._name_lbl.setProperty("chip_state", state)
        self._name_lbl.setProperty("chip_hovered", "false")
        self._name_lbl.style().polish(self._name_lbl)

    def enterEvent(self, event) -> None:  # type: ignore[override]
        if not self.property("chip_state"):
            self._name_lbl.setProperty("chip_hovered", "true")
            self._name_lbl.style().polish(self._name_lbl)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # type: ignore[override]
        self._name_lbl.setProperty("chip_hovered", "false")
        self._name_lbl.style().polish(self._name_lbl)
        super().leaveEvent(event)

    # ------------------------------------------------------------------
    # Mouse: click to load, drag to reorder
    # ------------------------------------------------------------------

    def mousePressEvent(self, event):  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):  # type: ignore[override]
        if self._drag_start is None or not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        if (event.position().toPoint() - self._drag_start).manhattanLength() < 8:
            return
        self._drag_start = None
        drag = QDrag(self)
        mime = QMimeData()
        mime.setText(self._MIME + self._preset.preset_id)
        pixmap = self.grab()
        drag.setPixmap(pixmap)
        drag.setHotSpot(QPoint(pixmap.width() // 2, pixmap.height() // 2))
        drag.setMimeData(mime)
        drag.exec(Qt.DropAction.MoveAction)

    def mouseReleaseEvent(self, event):  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton and self._drag_start is not None:
            self._drag_start = None
            self.clicked.emit(self._preset)
        else:
            self._drag_start = None
        super().mouseReleaseEvent(event)

    # ------------------------------------------------------------------
    # Drop target
    # ------------------------------------------------------------------

    def dragEnterEvent(self, event):  # type: ignore[override]
        if event.mimeData().hasText() and event.mimeData().text().startswith(self._MIME):
            src_id = event.mimeData().text()[len(self._MIME):]
            if src_id != self._preset.preset_id:
                self.setProperty("chip_drop", "true")
                self.style().polish(self)
                event.acceptProposedAction()
                return
        event.ignore()

    def dragLeaveEvent(self, event):  # type: ignore[override]
        self.setProperty("chip_drop", "false")
        self.style().polish(self)
        super().dragLeaveEvent(event)

    def dropEvent(self, event):  # type: ignore[override]
        self.setProperty("chip_drop", "false")
        self.style().polish(self)
        src_id = event.mimeData().text()[len(self._MIME):]
        self.move_req.emit(src_id, self._preset.preset_id)
        event.acceptProposedAction()


# ──────────────────────────────────────────────────────────────────────────────
# _PresetStrip — горизонтальная строка пресетов
# ──────────────────────────────────────────────────────────────────────────────

class _PresetStrip(QWidget):
    """Горизонтальная строка чипов пресетов под заголовком редактора пайплайна.

    Позволяет быстро переключаться между пресетами, сохранять текущий конфиг,
    удалять пресеты и перетаскивать чипы для изменения порядка.
    """

    preset_load_req = Signal(object)  # PipelinePreset

    def __init__(
        self,
        store: PipelinePresetStore,
        current_config_cb,  # callable() → PipelineConfig
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._store = store
        self._current_config_cb = current_config_cb
        self._chips: list[_PresetChip] = []
        self._active_id: str | None = None
        self._saved_id: str | None = None
        self.setObjectName("preset_strip")
        self._build_ui()
        self._reload()
        # Восстанавливаем выделение из прошлой сессии
        raw_active, raw_saved = self._store.load_selection()
        valid_ids = {c.preset.preset_id for c in self._chips}
        self._active_id = raw_active if raw_active in valid_ids else None
        self._saved_id = raw_saved if raw_saved in valid_ids else None
        self._refresh_chip_states()

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def refresh(self) -> None:
        """Перезагружает чипы из хранилища (вызывается извне при необходимости)."""
        self._reload()

    def mark_active(self, preset_id: str | None) -> None:
        """Помечает чип как загруженный (серый текст — ещё не сохранён)."""
        self._active_id = preset_id
        self._refresh_chip_states()
        self._store.save_selection(self._active_id, self._saved_id)

    def mark_saved(self) -> None:
        """Помечает активный чип как сохранённый (фиолетовый текст)."""
        self._saved_id = self._active_id
        self._refresh_chip_states()
        self._store.save_selection(self._active_id, self._saved_id)

    def save_active_preset(self, config: PipelineConfig) -> None:
        """Перезаписывает конфиг активного пресета текущим состоянием доски."""
        if self._active_id is None:
            return
        old = self._store.load(self._active_id)
        if old is None:
            return
        updated = PipelinePreset(
            preset_id=old.preset_id,
            name=old.name,
            config=config,
            created_at=old.created_at,
        )
        self._store.save(updated)
        for chip in self._chips:
            if chip.preset.preset_id == self._active_id:
                chip._preset = updated
                break

    def _refresh_chip_states(self) -> None:
        for chip in self._chips:
            pid = chip.preset.preset_id
            if pid == self._active_id:
                state = "saved" if pid == self._saved_id else "active"
            elif pid == self._saved_id:
                state = "pinned"
            else:
                state = ""
            chip.set_state(state)

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        self._row = QHBoxLayout(self)
        self._row.setContentsMargins(0, 0, 0, 0)
        self._row.setSpacing(6)

        # Кнопка «+» — всегда первой
        self._add_btn = QPushButton("+")
        self._add_btn.setObjectName("preset_add_btn")
        self._add_btn.setToolTip("Сохранить текущую конфигурацию как пресет")
        self._add_btn.setFixedHeight(28)
        self._add_btn.clicked.connect(self._on_add_clicked)
        self._row.addWidget(self._add_btn)

        # Мини-инпут (скрыт по умолчанию)
        self._name_input = QLineEdit()
        self._name_input.setPlaceholderText("Название пресета…")
        self._name_input.setFixedHeight(30)
        self._name_input.setMaximumWidth(180)
        self._name_input.returnPressed.connect(self._on_save_confirm)
        self._name_input.hide()
        self._row.addWidget(self._name_input)

        _si = int(28 * load_ui_scale())
        self._confirm_btn = QPushButton("✓")
        self._confirm_btn.setObjectName("preset_strip_icon_btn")
        self._confirm_btn.setFixedSize(_si, _si)
        self._confirm_btn.setToolTip("Сохранить")
        self._confirm_btn.clicked.connect(self._on_save_confirm)
        self._confirm_btn.hide()
        self._row.addWidget(self._confirm_btn)

        self._cancel_btn = QPushButton("✕")
        self._cancel_btn.setObjectName("preset_strip_icon_btn")
        self._cancel_btn.setFixedSize(_si, _si)
        self._cancel_btn.setToolTip("Отмена")
        self._cancel_btn.clicked.connect(self._on_save_cancel)
        self._cancel_btn.hide()
        self._row.addWidget(self._cancel_btn)

        # Спейсер — прижимает чипы влево
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._spacer = spacer
        self._row.addWidget(spacer)

    def _reload(self) -> None:
        """Пересоздаёт список чипов из хранилища."""
        for chip in self._chips:
            self._row.removeWidget(chip)
            chip.deleteLater()
        self._chips.clear()

        presets = self._store.load_ordered()
        # Вставляем чипы после кнопки «+» и мини-инпута (индексы 0–3), перед спейсером
        spacer_idx = self._row.indexOf(self._spacer)
        for i, preset in enumerate(presets):
            chip = _PresetChip(preset)
            chip.clicked.connect(self._on_chip_clicked)
            chip.delete_req.connect(self._on_chip_delete)
            chip.move_req.connect(self._on_chip_move)
            self._chips.append(chip)
            self._row.insertWidget(spacer_idx + i, chip)

        self._refresh_chip_states()
        self.setVisible(bool(presets))

    # ------------------------------------------------------------------
    # Inline save input
    # ------------------------------------------------------------------

    def _on_add_clicked(self) -> None:
        self._name_input.clear()
        self._name_input.show()
        self._confirm_btn.show()
        self._cancel_btn.show()
        self._name_input.setFocus()

    def _on_save_confirm(self) -> None:
        name = self._name_input.text().strip()
        if not name:
            self._name_input.setFocus()
            return
        self._name_input.hide()
        self._confirm_btn.hide()
        self._cancel_btn.hide()
        preset = PipelinePreset.new(name, self._current_config_cb())
        self._store.save(preset)
        self._store.save_order(
            [c.preset.preset_id for c in self._chips] + [preset.preset_id]
        )
        self._reload()
        self.mark_active(preset.preset_id)

    def _on_save_cancel(self) -> None:
        self._name_input.hide()
        self._confirm_btn.hide()
        self._cancel_btn.hide()

    # ------------------------------------------------------------------
    # Chip interactions
    # ------------------------------------------------------------------

    def _on_chip_clicked(self, preset: PipelinePreset) -> None:
        self.mark_active(preset.preset_id)
        self.preset_load_req.emit(preset)

    def _on_chip_delete(self, preset_id: str) -> None:
        reply = QMessageBox.question(
            self,
            "Удалить пресет",
            "Удалить этот пресет? Действие необратимо.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self._store.delete(preset_id)
        remaining_ids = [c.preset.preset_id for c in self._chips if c.preset.preset_id != preset_id]
        self._store.save_order(remaining_ids)
        if self._active_id == preset_id:
            self._active_id = None
        if self._saved_id == preset_id:
            self._saved_id = None
        self._store.save_selection(self._active_id, self._saved_id)
        self._reload()

    def _on_chip_move(self, src_id: str, dst_id: str) -> None:
        """Меняет местами чип src и чип dst."""
        src_idx = next((i for i, c in enumerate(self._chips) if c.preset.preset_id == src_id), -1)
        dst_idx = next((i for i, c in enumerate(self._chips) if c.preset.preset_id == dst_id), -1)
        if src_idx < 0 or dst_idx < 0 or src_idx == dst_idx:
            return

        self._chips[src_idx], self._chips[dst_idx] = self._chips[dst_idx], self._chips[src_idx]

        # Пересобираем порядок виджетов в layout без пересоздания.
        # Фиксированных виджетов до чипов: +, input, confirm, cancel → 4 штуки.
        for chip in self._chips:
            self._row.removeWidget(chip)
        for i, chip in enumerate(self._chips):
            self._row.insertWidget(4 + i, chip)

        self._store.save_order([c.preset.preset_id for c in self._chips])


# ──────────────────────────────────────────────────────────────────────────────
# PipelineEditorScreen
# ──────────────────────────────────────────────────────────────────────────────

class PipelineEditorScreen(QWidget):
    """Экран редактора пайплайна."""

    pipeline_saved  = Signal(object)  # PipelineConfig
    store_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._manifests: list[PluginManifest] = []
        self._dirty: bool = False
        self._build_ui()

    def load(self, config: PipelineConfig, manifests: list[PluginManifest], *, restore_missing: bool = True) -> None:
        self._manifests = manifests
        defaults = {s.stage_id: s for s in default_pipeline_config().stages}

        # Merge: config stages first (user order + settings), then append any
        # built-in stages that are missing from the saved config so they are
        # never accidentally lost when pipeline.json is partial.
        merged: dict[str, StageConfig] = {}
        for s in config.stages:
            merged[s.stage_id] = s
        for stage_id, default_cfg in defaults.items():
            if stage_id not in merged:
                merged[stage_id] = default_cfg

        # all_configs: full map for sidebar "add stage" lookup
        all_configs = {**defaults, **merged}
        self._grid.set_all_configs(all_configs)

        # Board order: saved stages first, then (when loading the main config)
        # any built-in stages absent from the saved config so they aren't lost
        # when pipeline.json is partial. Presets skip this step so that
        # explicitly removed stages stay removed.
        saved_ids = [s.stage_id for s in config.stages]
        extra_ids = [sid for sid in defaults if sid not in set(saved_ids)] if restore_missing else []
        board_stages = [merged[sid] for sid in saved_ids + extra_ids]
        self._grid.load_stages(board_stages)
        self._refresh_compatibility()
        self._dirty = False
        self._update_dirty_indicator()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 32, 32, 32)
        outer.setSpacing(16)

        header_row = QHBoxLayout()
        title = QLabel("Обработка")
        title.setObjectName("screen_title")
        header_row.addWidget(title)
        header_row.addStretch()

        # View mode switcher
        self._btn_view_large = QPushButton("Крупные")
        self._btn_view_small = QPushButton("Мелкие")
        self._view_btn_group = QButtonGroup(self)
        self._view_btn_group.setExclusive(True)
        for btn, mode, tip in (
            (self._btn_view_large, "large", "Крупные плитки"),
            (self._btn_view_small, "small", "Мелкие плитки"),
        ):
            btn.setObjectName("view_toggle_btn")
            btn.setCheckable(True)
            btn.setToolTip(tip)
            self._view_btn_group.addButton(btn)
            header_row.addWidget(btn)
        self._btn_view_large.setChecked(True)
        self._btn_view_large.clicked.connect(lambda: self._set_view("large"))
        self._btn_view_small.clicked.connect(lambda: self._set_view("small"))
        header_row.addSpacing(12)

        self._dirty_lbl = QLabel("Изменено ·")
        self._dirty_lbl.setObjectName("pipeline_dirty_label")
        self._dirty_lbl.hide()
        header_row.addWidget(self._dirty_lbl)
        header_row.addSpacing(8)

        save_btn = QPushButton("Сохранить")
        save_btn.setObjectName("run_btn")
        save_btn.setMinimumWidth(int(110 * load_ui_scale()))
        save_btn.clicked.connect(self._on_save)
        header_row.addWidget(save_btn)
        outer.addLayout(header_row)

        store = PipelinePresetStore(_PRESETS_DIR)
        self._strip = _PresetStrip(
            store,
            current_config_cb=lambda: PipelineConfig(stages=self._grid.current_stages()),
        )
        self._strip.preset_load_req.connect(self._on_preset_load)
        outer.addWidget(self._strip)

        hint = QLabel(
            "Кликните карточку для включения / выключения этапа. "
            "Перетащите карточку для изменения порядка. "
            "Нажмите «Настроить» для выбора модели и параметров."
        )
        hint.setObjectName("muted")
        hint.setWordWrap(True)
        outer.addWidget(hint)

        # ── Сплиттер: область карточек (слева) + боковая панель (справа) ─
        self._splitter = QSplitter(Qt.Orientation.Horizontal)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)
        self._grid = _StageCardGrid()
        self._grid.stage_config_requested.connect(self._on_config_requested)
        self._grid.stages_changed.connect(self._on_stages_changed)

        _grid_scroll = QScrollArea()
        _grid_scroll.setWidgetResizable(True)
        _grid_scroll.setFrameShape(QFrame.Shape.NoFrame)
        _grid_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        _grid_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        _grid_scroll.setWidget(self._grid)
        left_layout.addWidget(_grid_scroll, stretch=1)
        self._splitter.addWidget(left)

        self._sidebar = _StageSidebar()
        self._sidebar.collapse_toggled.connect(self._on_sidebar_toggled)
        self._sidebar.remove_from_board_requested.connect(self._on_remove_from_board)
        self._sidebar.add_to_board_requested.connect(self._on_add_to_board_end)
        self._splitter.addWidget(self._sidebar)
        self._splitter.setCollapsible(0, False)
        self._splitter.setCollapsible(1, False)
        self._splitter.setSizes([700, 200])

        outer.addWidget(self._splitter, 1)

    # ------------------------------------------------------------------
    # Sidebar helpers
    # ------------------------------------------------------------------

    def _refresh_compatibility(self) -> None:
        stages = self._grid.current_stages()
        port_states = compute_port_states(stages)
        issues = {sid: ps.issue for sid, ps in port_states.items() if ps.issue}
        self._grid.update_warnings(issues)
        self._grid.update_port_states(port_states)
        self._sidebar.update_states(stages, issues)

    def _on_stages_changed(self) -> None:
        self._dirty = True
        self._update_dirty_indicator()
        self._refresh_compatibility()

    def _refresh_sidebar(self) -> None:
        self._refresh_compatibility()

    def _update_dirty_indicator(self) -> None:
        if hasattr(self, "_dirty_lbl"):
            self._dirty_lbl.setVisible(self._dirty)

    def hideEvent(self, event) -> None:  # type: ignore[override]
        if self._dirty:
            config = PipelineConfig(stages=self._grid.current_stages())
            self.pipeline_saved.emit(config)
            self._dirty = False
            self._update_dirty_indicator()
        super().hideEvent(event)

    def _on_remove_from_board(self, stage_id: str) -> None:
        self._grid.remove_stage(stage_id)
        self._refresh_sidebar()

    def _on_add_to_board_end(self, stage_id: str) -> None:
        self._grid.add_stage_at_end(stage_id)
        self._refresh_sidebar()

    def _on_sidebar_toggled(self, collapsed: bool) -> None:
        if collapsed:
            current = self._splitter.sizes()
            self._sidebar_width = max(current[1], 160)
            self._sidebar.setFixedWidth(36)
            self._splitter.setSizes([current[0] + current[1] - 36, 36])
        else:
            w = getattr(self, "_sidebar_width", 200)
            self._sidebar.setMinimumWidth(120)
            self._sidebar.setMaximumWidth(16_777_215)
            total = sum(self._splitter.sizes())
            self._splitter.setSizes([total - w, w])

    # ------------------------------------------------------------------
    # View mode
    # ------------------------------------------------------------------

    def _set_view(self, mode: str) -> None:
        self._grid.set_view_mode(mode)
        self._refresh_compatibility()

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _on_save(self) -> None:
        config = PipelineConfig(stages=self._grid.current_stages())
        self.pipeline_saved.emit(config)
        self._strip.save_active_preset(config)
        self._strip.mark_saved()
        self._dirty = False
        self._update_dirty_indicator()

    def _on_preset_load(self, preset: PipelinePreset) -> None:
        self.load(preset.config, self._manifests, restore_missing=False)
        self._strip.mark_active(preset.preset_id)

    def _on_config_requested(self, stage_id: str) -> None:
        stage_cfg = next(
            (s for s in self._grid.current_stages() if s.stage_id == stage_id), None
        )
        if stage_cfg is None:
            return
        dlg = StageConfigDialog(stage_cfg, self._manifests, parent=self)
        dlg.store_requested.connect(self.store_requested)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._grid.update_stage_config(dlg.get_result())
            self._dirty = True
            self._update_dirty_indicator()
            self._refresh_sidebar()
