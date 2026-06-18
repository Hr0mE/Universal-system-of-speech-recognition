"""Абстрактные базовые классы ML-моделей.

Определяет интерфейсы :class:`ASRModel`, :class:`LanguageModel` и
:class:`DiarizationModel`, которые реализуются конкретными бэкендами
(Whisper, Pyannote и др.).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.pipeline.context import PipelineContext, Segment


class ASRModel(ABC):
    """Turns a single audio segment into transcribed text."""

    name: str

    @abstractmethod
    def transcribe(
        self,
        segment: "Segment",
        context: "PipelineContext",
    ) -> str:
        """Транскрибирует аудиосегмент и возвращает текст.

        Args:
            segment (Segment): Временной интервал для распознавания.
            context (PipelineContext): Контекст с путём к аудиофайлу.

        Returns:
            str: Распознанный текст или пустая строка.
        """


class LanguageModel(ABC):
    """Определяет код разговорного языка сегмента (например, ``'ru'``, ``'en'``)."""

    name: str

    @abstractmethod
    def detect(
        self,
        segment: "Segment",
        context: "PipelineContext",
    ) -> str:
        """Определяет язык аудиосегмента.

        Args:
            segment (Segment): Временной интервал для анализа.
            context (PipelineContext): Контекст с путём к аудиофайлу.

        Returns:
            str: Код языка ISO 639-1 (например, ``'ru'``).
        """


class DiarizationModel(ABC):
    """Определяет границы сегментов с метками говорящих для всей записи."""

    name: str

    @abstractmethod
    def diarize(self, context: "PipelineContext") -> list["Segment"]:
        """Выполняет диаризацию всей записи.

        Args:
            context (PipelineContext): Контекст с путём к аудиофайлу.

        Returns:
            list[Segment]: Сегменты с заполненным ``speaker_id``.
        """
