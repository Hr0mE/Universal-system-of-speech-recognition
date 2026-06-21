"""Главное окно приложения.

Содержит NavBar (боковую панель) и QStackedWidget с экранами приложения.
Управляет навигацией, хранилищем проектов и конфигурацией моделей.
"""

from __future__ import annotations

import wave
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtGui import QCloseEvent, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QMainWindow,
    QStackedWidget,
    QWidget,
)

from core.api.transcribe import TranscriptionResult, find_resumable_run, load_run_result
from core.config.pipeline_config import PipelineConfig, default_pipeline_config, load_pipeline_config
from core.domain.project import Project
from core.storage.project_store import ProjectStore
from plugins import PLUGINS_DIR, all_manifests
from plugins.manifest import PluginManifest
from ui.qt.nav_bar import NavBar
from ui.qt.scale_manager import (
    CtrlWheelZoomFilter,
    load_ui_scale, save_ui_scale,
    load_ui_theme, save_ui_theme,
    SCALE_MIN, SCALE_MAX,
)
from ui.qt.theme import apply_theme
from ui.qt.toast import ToastLevel, ToastManager
from ui.qt.screens.editor import TranscriptEditorScreen
from ui.qt.screens.models import ModelsScreen
from ui.qt.screens.pipeline_editor import PipelineEditorScreen
from ui.qt.screens.processing import ProcessingScreen
from ui.qt.screens.projects import ProjectsScreen
from ui.qt.screens.result import ResultScreen
from ui.qt.screens.welcome import WelcomeScreen

_SCREEN_PROJECTS    = 0
_SCREEN_WELCOME     = 1
_SCREEN_PROCESSING  = 2
_SCREEN_RESULT      = 3
_SCREEN_MODELS      = 4
_SCREEN_EDITOR      = 5
_SCREEN_PIPELINE    = 6

_PROJECTS_DIR = Path("projects")
_RUNS_DIR     = Path("runs")


def _try_wav_duration(path: Path) -> float:
    try:
        with wave.open(str(path)) as wf:
            return wf.getnframes() / wf.getframerate()
    except Exception:
        return 0.0


class MainWindow(QMainWindow):
    """Главное окно приложения транскрибации.

    Организует навигацию между экранами через QStackedWidget.
    Управляет состоянием проектов, конфигурацией моделей и переходами
    между экранами Welcome → Processing → Result.
    """

    def __init__(self) -> None:
        """Инициализирует главное окно и все дочерние экраны."""
        super().__init__()
        self.setWindowTitle("Расшифровка")
        self.setMinimumSize(620, 460)
        self.resize(1300, 820)

        self._pipeline_config: PipelineConfig = default_pipeline_config()
        self._all_manifests: list[PluginManifest] = all_manifests(PLUGINS_DIR)
        self._restore_settings()

        self._project_store = ProjectStore(_PROJECTS_DIR)
        self._current_project: Project | None = None    # currently viewed project
        self._processing_project: Project | None = None # project with active/stopped run
        self._current_result: TranscriptionResult | None = None
        self._prev_screen: int = _SCREEN_PROJECTS       # screen before ResultScreen

        self._scale: float = load_ui_scale()
        self._pending_scale: float = self._scale
        self._theme: str = load_ui_theme()
        self._scale_timer = QTimer(self)
        self._scale_timer.setSingleShot(True)
        self._scale_timer.setInterval(150)
        self._scale_timer.timeout.connect(self._on_scale_timer)
        self._build_ui()
        self._nav.update_theme_btn(self._theme)
        self._toast = ToastManager(self)
        self._refresh_nav()
        self._open_startup_screen()
        # Apply saved scale and theme after window is fully built
        self._apply_scale(self._scale)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        hbox = QHBoxLayout(root)
        hbox.setContentsMargins(0, 0, 0, 0)
        hbox.setSpacing(0)

        self._setup_zoom_shortcuts()

        # Left sidebar
        self._nav = NavBar()
        self._nav.new_project_requested.connect(self.show_welcome)
        self._nav.project_selected.connect(self._on_project_selected)
        self._nav.projects_requested.connect(self.show_projects)
        self._nav.models_requested.connect(self.show_models)
        self._nav.pipeline_requested.connect(self.show_pipeline)
        self._nav.settings_requested.connect(self.show_pipeline)
        self._nav.theme_toggle_requested.connect(self._on_theme_toggle)
        hbox.addWidget(self._nav)

        # Content area
        self._stack = QStackedWidget()
        hbox.addWidget(self._stack, stretch=1)

        self._projects_screen = ProjectsScreen()
        self._projects_screen.new_project_requested.connect(self.show_welcome)
        self._projects_screen.run_selected.connect(self._on_run_selected)
        self._projects_screen.resume_run_requested.connect(self._on_history_resume_requested)
        self._projects_screen.file_accepted.connect(self._on_file_accepted)
        self._stack.addWidget(self._projects_screen)   # 0

        self._welcome = WelcomeScreen()
        self._welcome.file_accepted.connect(self._on_file_accepted)
        self._welcome.resume_requested.connect(self._on_resume_requested)
        self._welcome.settings_requested.connect(self.show_pipeline)
        self._welcome.back_requested.connect(self.show_projects)
        self._stack.addWidget(self._welcome)            # 1

        self._processing = ProcessingScreen()
        self._processing.processing_finished.connect(self._on_result_ready)
        self._processing.back_requested.connect(self.show_projects)
        self._processing.resume_requested.connect(self._on_processing_resume_requested)
        self._processing.error_occurred.connect(self._on_processing_error)
        self._processing.user_stopped.connect(self._on_processing_stopped)
        self._stack.addWidget(self._processing)         # 2

        self._result = ResultScreen()
        self._result.back_requested.connect(self._on_result_back)
        self._result.edit_requested.connect(self._on_edit_requested)
        self._stack.addWidget(self._result)             # 3

        self._models_screen = ModelsScreen()
        self._stack.addWidget(self._models_screen)      # 4

        self._editor = TranscriptEditorScreen()
        self._editor.back_requested.connect(self._on_editor_back)
        self._editor.saved.connect(self._on_editor_saved)
        self._stack.addWidget(self._editor)             # 5

        self._pipeline_screen = PipelineEditorScreen()
        self._pipeline_screen.pipeline_saved.connect(self._on_pipeline_saved)
        self._pipeline_screen.store_requested.connect(self.show_models)
        self._stack.addWidget(self._pipeline_screen)    # 6

    # ------------------------------------------------------------------
    # Screen navigation
    # ------------------------------------------------------------------

    def show_projects(self) -> None:
        self._nav.mark_section("projects")
        self._nav.mark_active(None)
        self._nav.repaint()
        self._processing.reset()
        self._abandon_current_project()
        self._projects_screen.refresh(_RUNS_DIR)
        self._refresh_nav()
        self._stack.setCurrentIndex(_SCREEN_PROJECTS)

    def show_welcome(self) -> None:
        self._processing.reset()
        self._result.reset()
        self._abandon_current_project()
        self._welcome._show_drop_zone()
        self._update_config_hint()
        self._current_result = None
        self._nav.mark_active(None)
        self._nav.mark_section(None)
        self._stack.setCurrentIndex(_SCREEN_WELCOME)

    def show_models(self) -> None:
        self._nav.mark_section("models")
        self._nav.mark_active(None)
        self._nav.repaint()
        self._abandon_current_project()
        self._models_screen.refresh(self._all_manifests)
        self._stack.setCurrentIndex(_SCREEN_MODELS)

    def show_pipeline(self) -> None:
        self._nav.mark_section("pipeline")
        self._nav.mark_active(None)
        self._nav.repaint()
        self._abandon_current_project()
        self._pipeline_screen.load(self._pipeline_config, self._all_manifests, restore_missing=False)
        self._stack.setCurrentIndex(_SCREEN_PIPELINE)

    def _show_processing(self, audio_path: Path) -> None:
        self._processing.reset()
        self._processing.start(audio_path, self._pipeline_config)
        self._nav.mark_section(None)
        self._stack.setCurrentIndex(_SCREEN_PROCESSING)

    def _show_result(self, result: TranscriptionResult) -> None:
        self._prev_screen = self._stack.currentIndex()
        self._current_result = result
        self._result.show_result(result)
        self._nav.mark_section(None)
        self._stack.setCurrentIndex(_SCREEN_RESULT)
        if self._current_project:
            self._nav.mark_active(self._current_project.project_id)

    def _on_result_back(self) -> None:
        self.show_projects()

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_file_accepted(self, audio_path: Path) -> None:
        duration = _try_wav_duration(audio_path)
        project = Project.new(
            name=audio_path.name,
            audio_path=str(audio_path),
            duration_s=duration,
        )
        project.status = "processing"
        self._current_project = project
        self._processing_project = project
        self._project_store.save(project)
        self._refresh_nav()
        self._nav.mark_active(project.project_id)
        self._show_processing(audio_path)

    def _on_result_ready(self, result: TranscriptionResult) -> None:
        proj = self._processing_project
        if proj:
            proj.status = "completed"
            proj.run_ids.append(result.run_id)
            self._project_store.save(proj)
            self._processing_project = None
            self._refresh_nav()
        self._current_result = result
        if self._stack.currentIndex() == _SCREEN_PROCESSING:
            if self._processing._stopped_by_user:
                # Воркер добежал после нажатия «Стоп» — проект уже сохранён как completed,
                # но автоматически переходить к результату не нужно.
                pass
            else:
                if proj:
                    self._current_project = proj
                self._show_result(result)
        elif self._stack.currentIndex() == _SCREEN_PROJECTS:
            self._projects_screen.refresh(_RUNS_DIR)

    def _on_project_selected(self, project_id: str) -> None:
        self._abandon_current_project()
        project = self._project_store.load(project_id)
        if project is None:
            return
        self._current_project = project

        if project.status == "completed" and project.last_run_id():
            run_dir = _RUNS_DIR / project.last_run_id()
            result = load_run_result(run_dir)
            if result:
                self._show_result(result)
                return

        audio_path = Path(project.audio_path)
        if audio_path.exists():
            if project.status in ("failed", "stopped"):
                self._welcome.show_resume(audio_path, project.status)
            else:
                self._welcome.show_file(audio_path)
        else:
            self._welcome._show_drop_zone()
        self._update_config_hint()
        self._nav.mark_active(project_id)
        self._stack.setCurrentIndex(_SCREEN_WELCOME)

    def _on_processing_resume_requested(self, audio_path: Path) -> None:
        """Resume button clicked while still on ProcessingScreen."""
        run_dir = find_resumable_run(Path("runs"), str(audio_path))
        if run_dir is None:
            return
        # Reactivate project status
        proj = self._current_project or self._processing_project
        if proj and proj.status != "processing":
            proj.status = "processing"
            self._project_store.save(proj)
            self._processing_project = proj
            self._refresh_nav()
        self._processing.start_resume(run_dir, audio_path, self._pipeline_config)
        # Stack already on _SCREEN_PROCESSING

    def _on_resume_requested(self, audio_path: Path) -> None:
        if not self._current_project:
            self._on_file_accepted(audio_path)
            return
        proj = self._current_project
        proj.status = "processing"
        self._project_store.save(proj)
        self._processing_project = proj
        self._refresh_nav()
        self._nav.mark_active(proj.project_id)
        run_dir = find_resumable_run(Path("runs"), proj.audio_path)
        self._processing.reset()
        if run_dir is not None:
            self._processing.start_resume(run_dir, audio_path, self._pipeline_config)
        else:
            self._show_processing(audio_path)
            return
        self._stack.setCurrentIndex(_SCREEN_PROCESSING)

    def _on_history_resume_requested(self, run_id: str) -> None:
        run_dir    = _RUNS_DIR / run_id
        state_file = run_dir / "state.json"
        config_file = run_dir / "config.yaml"
        if not (state_file.exists() and config_file.exists()):
            return
        try:
            import yaml as _yaml
            cfg = _yaml.safe_load(config_file.read_text(encoding="utf-8"))
            audio_path = Path(cfg.get("audio_path", ""))
        except Exception:
            return
        if not audio_path.exists():
            return
        self._abandon_current_project()
        self._current_project = None
        self._processing.reset()
        self._processing.start_resume(run_dir, audio_path, self._pipeline_config)
        self._stack.setCurrentIndex(_SCREEN_PROCESSING)

    def _on_run_selected(self, run_id: str) -> None:
        run_dir = _RUNS_DIR / run_id
        result = load_run_result(run_dir)
        if result:
            self._current_project = None
            self._show_result(result)

    def _on_processing_stopped(self) -> None:
        proj = self._processing_project
        if proj and proj.status == "processing":
            proj.status = "stopped"
            self._project_store.save(proj)
            self._refresh_nav()
        # Не сбрасываем _processing_project — пользователь может возобновить

    def _on_processing_error(self) -> None:
        if self._processing_project and self._processing_project.status == "processing":
            self._processing_project.status = "failed"
            self._project_store.save(self._processing_project)
            self._processing_project = None
            self._refresh_nav()

    def _on_edit_requested(self) -> None:
        if self._current_result:
            self._editor.load(self._current_result)
            self._stack.setCurrentIndex(_SCREEN_EDITOR)

    def _on_pipeline_saved(self, config: PipelineConfig) -> None:
        self._pipeline_config = config
        config.save()
        self._update_config_hint()
        self._toast.show("Настройка сохранена", ToastLevel.SUCCESS)

    def _on_editor_back(self) -> None:
        if self._current_result:
            self._show_result(self._current_result)
        else:
            self.show_projects()

    def _on_editor_saved(self, result: TranscriptionResult) -> None:
        self._current_result = result

    # ------------------------------------------------------------------
    # Startup
    # ------------------------------------------------------------------

    def _open_startup_screen(self) -> None:
        self._projects_screen.refresh(_RUNS_DIR)
        if self._projects_screen.run_count():
            self._nav.mark_section("projects")
            self._stack.setCurrentIndex(_SCREEN_PROJECTS)
        else:
            self._update_config_hint()
            self._stack.setCurrentIndex(_SCREEN_WELCOME)

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------

    def _update_config_hint(self) -> None:
        asr = self._pipeline_config.get_stage("asr")
        diar = self._pipeline_config.get_stage("diarization")
        name = asr.model_name if asr else "?"
        size = asr.params.get("model_size", "?") if asr else "?"
        suffix = " + diar" if (diar and diar.enabled) else ""
        self._welcome.set_config_hint(f"{name} / {size}{suffix}")

    def _save_settings(self) -> None:
        self._pipeline_config.save()

    def _restore_settings(self) -> None:
        self._pipeline_config = load_pipeline_config()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _refresh_nav(self) -> None:
        self._nav.set_projects(self._project_store.load_all())

    # ------------------------------------------------------------------
    # Zoom
    # ------------------------------------------------------------------

    def _setup_zoom_shortcuts(self) -> None:
        for seq in ("Ctrl++", "Ctrl+="):
            QShortcut(QKeySequence(seq), self).activated.connect(self._zoom_in)
        QShortcut(QKeySequence("Ctrl+-"), self).activated.connect(self._zoom_out)
        QShortcut(QKeySequence("Ctrl+0"), self).activated.connect(self._zoom_reset)
        QShortcut(QKeySequence("Ctrl+Shift+L"), self).activated.connect(self._on_theme_toggle)

        self._zoom_filter = CtrlWheelZoomFilter()
        self._zoom_filter.zoom_in_requested.connect(self._zoom_in)
        self._zoom_filter.zoom_out_requested.connect(self._zoom_out)
        QApplication.instance().installEventFilter(self._zoom_filter)

    def _zoom_in(self) -> None:
        self._pending_scale = min(SCALE_MAX, round(self._pending_scale + 0.1, 2))
        self._scale_timer.start()

    def _zoom_out(self) -> None:
        self._pending_scale = max(SCALE_MIN, round(self._pending_scale - 0.1, 2))
        self._scale_timer.start()

    def _zoom_reset(self) -> None:
        self._pending_scale = 1.0
        self._apply_scale(1.0)

    def _on_scale_timer(self) -> None:
        self._apply_scale(self._pending_scale)

    def _apply_scale(self, scale: float) -> None:
        self._scale = max(SCALE_MIN, min(SCALE_MAX, scale))
        self._pending_scale = self._scale
        apply_theme(QApplication.instance(), self._scale, self._theme)
        self._nav.set_scale(self._scale)
        self._editor.set_scale(self._scale)

    def _on_theme_toggle(self) -> None:
        self._theme = "light" if self._theme == "dark" else "dark"
        self._nav.update_theme_btn(self._theme)
        self._editor.set_theme(self._theme)
        # Defer stylesheet recompute to the next event-loop iteration so the
        # toggle animation gets at least one paint frame before Qt re-evaluates
        # all QSS rules against the full widget tree (~100+ widgets × 200 rules).
        QTimer.singleShot(0, self._commit_theme)

    def _commit_theme(self) -> None:
        apply_theme(QApplication.instance(), self._scale, self._theme)

    def closeEvent(self, event: QCloseEvent) -> None:
        save_ui_scale(self._scale)
        save_ui_theme(self._theme)
        worker = self._processing._worker
        if worker is not None and worker.isRunning():
            if hasattr(worker, "stop_requested"):
                worker.stop_requested.set()
            worker.wait(3000)
        event.accept()

    def _abandon_current_project(self) -> None:
        """Called on navigation. Marks the in-flight project stopped/failed if worker is not running."""
        worker_running = (
            self._processing._worker is not None
            and self._processing._worker.isRunning()
        )
        proj = self._processing_project
        if proj is not None and proj.status == "processing" and not worker_running:
            proj.status = "stopped" if self._processing._stopped_by_user else "failed"
            self._project_store.save(proj)
            self._processing_project = None
            self._refresh_nav()
        # If worker IS running: leave _processing_project alive for _on_result_ready
        self._current_project = None
