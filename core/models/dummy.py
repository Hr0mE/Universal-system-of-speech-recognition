"""Заглушки ML-моделей для тестирования pipeline.

Все классы реализуют соответствующие абстрактные интерфейсы без загрузки
реальных весов, что позволяет тестировать pipeline без ML-зависимостей.
"""

from __future__ import annotations

from core.models.base import ASRModel, DiarizationModel, LanguageModel
from core.pipeline.context import PipelineContext, Segment


class DummyASR(ASRModel):
    """Заглушка ASR-модели, возвращающая метку с временным интервалом."""

    name = "dummy"

    def transcribe(self, segment: Segment, context: PipelineContext) -> str:
        """Возвращает строку-метку с временными границами сегмента.

        Args:
            segment (Segment): Входной сегмент.
            context (PipelineContext): Контекст выполнения (не используется).

        Returns:
            str: Строка вида ``"[dummy asr 0.0-30.0s]"``.
        """
        return (
            f"[dummy asr {segment.start_time:.1f}-{segment.end_time:.1f}s]"
        )


class DummyLanguageModel(LanguageModel):
    """Заглушка LID-модели, всегда возвращающая фиксированный язык."""

    name = "dummy"

    def __init__(self, language: str = "en") -> None:
        """Инициализирует заглушку с указанным языком.

        Args:
            language (str): Код языка, который будет возвращаться при детекции.
        """
        self.language = language

    def detect(self, segment: Segment, context: PipelineContext) -> str:
        """Возвращает фиксированный код языка.

        Args:
            segment (Segment): Входной сегмент (не используется).
            context (PipelineContext): Контекст выполнения (не используется).

        Returns:
            str: Фиксированный код языка, заданный при инициализации.
        """
        return self.language


class DummyDiarization(DiarizationModel):
    """Заглушка модели диаризации, создающая один сегмент на весь аудиофайл."""

    name = "dummy"

    def diarize(self, context: PipelineContext) -> list[Segment]:
        """Возвращает один сегмент, охватывающий всё аудио, с speaker_id='S1'.

        Args:
            context (PipelineContext): Контекст с длительностью аудио.

        Returns:
            list[Segment]: Список из одного сегмента.
        """
        return [
            Segment(
                start_time=0.0,
                end_time=context.audio_duration,
                speaker_id="S1",
            )
        ]
