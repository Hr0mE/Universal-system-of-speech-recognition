"""Компактный виджет воспроизведения аудио.

Строка управления с кнопками Play/Pause, Stop, seek-слайдером, отображением позиции
и контролем скорости. Использует QMediaPlayer и эмитирует ``position_changed``
для синхронизации с TimelineWidget в редакторе транскрипта.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt, QUrl, Signal
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QSlider, QWidget

from ui.qt.icon_utils import svg_icon
from ui.qt.scale_manager import load_ui_theme

_ICON_COLOR_DARK  = "#E1E1E6"
_ICON_COLOR_LIGHT = "#18181B"

_SPEED_STEPS: tuple[tuple[str, float], ...] = (
    ("0.75×", 0.75),
    ("1×",    1.0),
    ("1.5×",  1.5),
)


def _fmt_time(seconds: float) -> str:
    s = max(0, int(seconds))
    if s < 3600:
        m, sec = divmod(s, 60)
        return f"{m}:{sec:02d}"
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{h}:{m:02d}:{sec:02d}"


class AudioPlayerWidget(QWidget):
    """Compact transport bar: Play/Pause, Stop, seek slider, time, speed, zoom."""

    position_changed = Signal(float)  # seconds
    zoom_changed     = Signal(float)  # zoom factor 1.0–8.0

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._duration: float = 0.0
        self._icon_color = _ICON_COLOR_DARK if load_ui_theme() == "dark" else _ICON_COLOR_LIGHT

        self._player = QMediaPlayer()
        self._audio_out = QAudioOutput()
        self._player.setAudioOutput(self._audio_out)
        self._player.positionChanged.connect(self._on_position)
        self._player.durationChanged.connect(self._on_duration)
        self._player.playbackStateChanged.connect(self._update_play_btn)

        self.setMinimumHeight(44)
        self.setObjectName("audio_player")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(8)

        self._play_btn = QPushButton()
        self._play_btn.setObjectName("player_btn")
        self._play_btn.setIconSize(QSize(16, 16))
        self._play_btn.setToolTip("Воспроизвести / Пауза")
        self._play_btn.clicked.connect(self._toggle_play)
        layout.addWidget(self._play_btn)

        self._stop_btn = QPushButton()
        self._stop_btn.setObjectName("player_btn")
        self._stop_btn.setIconSize(QSize(16, 16))
        self._stop_btn.setToolTip("Остановить")
        self._stop_btn.clicked.connect(self._stop)
        layout.addWidget(self._stop_btn)

        self._seek = QSlider(Qt.Orientation.Horizontal)
        self._seek.setObjectName("player_seek")
        self._seek.setRange(0, 0)
        self._seek.sliderMoved.connect(self._player.setPosition)
        layout.addWidget(self._seek, stretch=1)

        self._time_label = QLabel("0:00 / 0:00")
        self._time_label.setObjectName("player_time")
        layout.addWidget(self._time_label)

        self._speed_btns: list[tuple[QPushButton, float]] = []
        for label, rate in _SPEED_STEPS:
            btn = QPushButton(label)
            btn.setObjectName("player_speed_btn")
            btn.setProperty("active", rate == 1.0)
            btn.clicked.connect(lambda checked=False, r=rate: self._set_speed(r))
            layout.addWidget(btn)
            self._speed_btns.append((btn, rate))

        layout.addSpacing(8)

        zoom_lbl = QLabel("zoom")
        zoom_lbl.setObjectName("player_zoom_lbl")
        layout.addWidget(zoom_lbl)

        self._zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self._zoom_slider.setObjectName("player_zoom")
        self._zoom_slider.setRange(10, 80)   # / 10 → 1.0 до 8.0
        self._zoom_slider.setValue(10)
        self._zoom_slider.setFixedWidth(80)
        self._zoom_slider.setToolTip("Масштаб временной шкалы")
        self._zoom_slider.valueChanged.connect(
            lambda v: self.zoom_changed.emit(v / 10.0)
        )
        layout.addWidget(self._zoom_slider)

        self._update_play_btn()
        self._stop_btn.setIcon(svg_icon("control-stop", self._icon_color))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_file(self, path: Path) -> None:
        self._player.stop()
        self._player.setSource(QUrl.fromLocalFile(str(path)))
        self._duration = 0.0
        self._seek.setRange(0, 0)
        self._update_time_label(0.0)
        self._update_play_btn()

    def seek(self, seconds: float) -> None:
        self._player.setPosition(int(seconds * 1000))

    def clear(self) -> None:
        self._player.stop()
        self._player.setSource(QUrl())
        self._duration = 0.0
        self._seek.setRange(0, 0)
        self._seek.setValue(0)
        self._update_time_label(0.0)
        self._update_play_btn()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _toggle_play(self) -> None:
        state = self._player.playbackState()
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self._player.pause()
        else:
            self._player.play()

    def _stop(self) -> None:
        self._player.stop()

    def _set_speed(self, rate: float) -> None:
        self._player.setPlaybackRate(rate)
        for btn, r in self._speed_btns:
            btn.setProperty("active", r == rate)
            btn.style().polish(btn)

    def _on_position(self, ms: int) -> None:
        t = ms / 1000.0
        self._update_time_label(t)
        self._seek.blockSignals(True)
        self._seek.setValue(ms)
        self._seek.blockSignals(False)
        self.position_changed.emit(t)

    def _on_duration(self, ms: int) -> None:
        self._duration = ms / 1000.0
        self._seek.setRange(0, ms)
        self._update_time_label(self._player.position() / 1000.0)

    def set_theme(self, mode: str) -> None:
        self._icon_color = _ICON_COLOR_DARK if mode == "dark" else _ICON_COLOR_LIGHT
        self._update_play_btn()
        self._stop_btn.setIcon(svg_icon("control-stop", self._icon_color))

    def _update_play_btn(self) -> None:
        playing = (
            self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
        )
        icon_name = "control-pause" if playing else "control-play"
        self._play_btn.setIcon(svg_icon(icon_name, self._icon_color))

    def _update_time_label(self, pos: float) -> None:
        self._time_label.setText(f"{_fmt_time(pos)} / {_fmt_time(self._duration)}")
