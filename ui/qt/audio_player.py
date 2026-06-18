"""Компактный виджет воспроизведения аудио.

Строка управления с кнопками Play/Pause, Stop и отображением позиции.
Использует QMediaPlayer и эмитирует ``position_changed`` для синхронизации
с TimelineWidget в редакторе транскрипта.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QUrl, Signal
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget



def _fmt_time(seconds: float) -> str:
    s = max(0, int(seconds))
    if s < 3600:
        m, sec = divmod(s, 60)
        return f"{m}:{sec:02d}"
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{h}:{m:02d}:{sec:02d}"


class AudioPlayerWidget(QWidget):
    """Compact transport bar: Play/Pause, Stop, time display."""

    position_changed = Signal(float)  # seconds

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._duration: float = 0.0

        self._player = QMediaPlayer()
        self._audio_out = QAudioOutput()
        self._player.setAudioOutput(self._audio_out)
        self._player.positionChanged.connect(self._on_position)
        self._player.durationChanged.connect(self._on_duration)
        self._player.playbackStateChanged.connect(self._update_play_btn)

        self.setMinimumHeight(36)
        self.setObjectName("audio_player")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(8)

        self._play_btn = QPushButton("▶")
        self._play_btn.setObjectName("player_btn")
        self._play_btn.setToolTip("Воспроизвести / Пауза")
        self._play_btn.clicked.connect(self._toggle_play)
        layout.addWidget(self._play_btn)

        self._stop_btn = QPushButton("■")
        self._stop_btn.setObjectName("player_btn")
        self._stop_btn.setToolTip("Остановить")
        self._stop_btn.clicked.connect(self._stop)
        layout.addWidget(self._stop_btn)

        self._time_label = QLabel("0:00 / 0:00")
        self._time_label.setObjectName("player_time")
        layout.addWidget(self._time_label)

        layout.addStretch()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_file(self, path: Path) -> None:
        self._player.stop()
        self._player.setSource(QUrl.fromLocalFile(str(path)))
        self._duration = 0.0
        self._update_time_label(0.0)
        self._update_play_btn()

    def seek(self, seconds: float) -> None:
        self._player.setPosition(int(seconds * 1000))

    def clear(self) -> None:
        self._player.stop()
        self._player.setSource(QUrl())
        self._duration = 0.0
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

    def _on_position(self, ms: int) -> None:
        t = ms / 1000.0
        self._update_time_label(t)
        self.position_changed.emit(t)

    def _on_duration(self, ms: int) -> None:
        self._duration = ms / 1000.0
        self._update_time_label(
            self._player.position() / 1000.0
        )

    def _update_play_btn(self) -> None:
        playing = (
            self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
        )
        self._play_btn.setText("⏸" if playing else "▶")

    def _update_time_label(self, pos: float) -> None:
        self._time_label.setText(f"{_fmt_time(pos)} / {_fmt_time(self._duration)}")
