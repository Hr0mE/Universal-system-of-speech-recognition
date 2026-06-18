"""Модели данных контекста pipeline.

Содержит :class:`Segment` — единицу обработки аудио, и :class:`PipelineContext` —
контейнер метаданных, передаваемый через все стадии.
"""

from __future__ import annotations

import threading
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from core.events.bus import EventBus


class PipelineCancelled(Exception):
    """Raised inside a stage when stop_requested is set between segments."""


@dataclass
class Segment:
    """Единица обработки аудио: временной интервал с результатами анализа.

    Attributes:
        start_time (float): Начало сегмента в секундах.
        end_time (float): Конец сегмента в секундах.
        speaker_id (str | None): Идентификатор говорящего после диаризации.
        language (str | None): Код языка (например, ``'ru'``, ``'en'``) после LID.
        text (str | None): Транскрибированный текст после ASR.
    """

    start_time: float
    end_time: float
    speaker_id: str | None = None
    language: str | None = None
    text: str | None = None

    @property
    def duration(self) -> float:
        """Длительность сегмента в секундах."""
        return self.end_time - self.start_time

    def to_dict(self) -> dict[str, Any]:
        """Преобразует сегмент в словарь для сериализации в JSON.

        Returns:
            dict[str, Any]: Словарь с полями dataclass.
        """
        return asdict(self)


@dataclass
class PipelineContext:
    """Контекст выполнения pipeline, передаваемый через все стадии.

    Attributes:
        run_id (str): Уникальный идентификатор запуска.
        audio_path (Path): Путь к исходному аудиофайлу.
        run_dir (Path): Директория для сохранения артефактов.
        audio_duration (float): Длительность аудио в секундах.
        metadata (dict): Дополнительные метаданные для стадий.
        event_bus (EventBus | None): Шина событий (устанавливается движком).
        current_stage_index (int): Индекс текущей стадии (устанавливается движком).
        stop_requested (threading.Event): Событие для отмены pipeline из UI.
    """

    run_id: str
    audio_path: Path
    run_dir: Path
    audio_duration: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    event_bus: "EventBus | None" = field(default=None, repr=False, compare=False)
    current_stage_index: int = field(default=0, repr=False, compare=False)
    stop_requested: threading.Event = field(
        default_factory=threading.Event, repr=False, compare=False
    )
