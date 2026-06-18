"""Конкретные реализации стадий pipeline.

Предоставляет пять стадий: сегментация, фильтрация, диаризация,
определение языка и распознавание речи (ASR).
"""

from __future__ import annotations

import logging
from dataclasses import replace
from typing import TYPE_CHECKING

from core.events.events import ProgressUpdated
from core.pipeline.context import PipelineCancelled, PipelineContext, Segment
from core.pipeline.port_types import LANGUAGE_LABELS, SEGMENTS, SPEAKER_LABELS, TRANSCRIPT
from core.pipeline.retry import retry_on_error
from core.pipeline.stage import Stage, StageDescriptor, register_stage

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from core.models.base import (
        ASRModel,
        DiarizationModel,
        LanguageModel,
    )


class DummyStage(Stage):
    """Пустая стадия-заглушка для тестирования pipeline."""

    name = "dummy"

    def run(
        self,
        segments: list[Segment],
        context: PipelineContext,
    ) -> list[Segment]:
        """Возвращает входные сегменты без изменений.

        Args:
            segments (list[Segment]): Входные сегменты.
            context (PipelineContext): Контекст запуска.

        Returns:
            list[Segment]: Те же сегменты без изменений.
        """
        return segments


class FixedWindowSegmentationStage(Stage):
    """Cuts the audio timeline into fixed-length windows.

    Pure transformation: produces time intervals only. Persistence is handled
    by the engine via RunManager.
    """

    name = "segmentation"

    def __init__(self, window_seconds: float = 30.0):
        """Инициализирует стадию сегментации.

        Args:
            window_seconds (float): Длина одного окна в секундах.

        Raises:
            ValueError: Если ``window_seconds`` <= 0.
        """
        if window_seconds <= 0:
            raise ValueError("window_seconds must be > 0")
        self.window_seconds = window_seconds

    def run(
        self,
        segments: list[Segment],
        context: PipelineContext,
    ) -> list[Segment]:
        """Нарезает таймлайн аудио на равные окна.

        Args:
            segments (list[Segment]): Игнорируется (стадия является источником).
            context (PipelineContext): Должен содержать ``audio_duration > 0``.

        Returns:
            list[Segment]: Список временных интервалов.

        Raises:
            ValueError: Если ``context.audio_duration`` <= 0.
        """
        duration = context.audio_duration
        if duration <= 0:
            raise ValueError(
                "PipelineContext.audio_duration must be set before segmentation"
            )

        result: list[Segment] = []
        start = 0.0
        while start < duration:
            end = min(start + self.window_seconds, duration)
            result.append(Segment(start_time=start, end_time=end))
            start = end

        return result


class MinDurationFilterStage(Stage):
    """Drops segments shorter than `min_seconds`.

    Placed after DiarizationStage to remove sub-word speaker turns that cause
    LID mis-detections and Whisper hallucinations.
    """

    name = "min_duration_filter"

    def __init__(self, min_seconds: float = 0.3) -> None:
        """Инициализирует фильтр коротких сегментов.

        Args:
            min_seconds (float): Минимальная допустимая длительность в секундах.

        Raises:
            ValueError: Если ``min_seconds`` <= 0.
        """
        if min_seconds <= 0:
            raise ValueError("min_seconds must be > 0")
        self.min_seconds = min_seconds

    def run(
        self,
        segments: list[Segment],
        _context: PipelineContext,
    ) -> list[Segment]:
        """Удаляет сегменты короче порогового значения.

        Args:
            segments (list[Segment]): Входные сегменты.
            _context (PipelineContext): Не используется.

        Returns:
            list[Segment]: Сегменты с длительностью >= ``min_seconds``.
        """
        return [s for s in segments if s.end_time - s.start_time >= self.min_seconds]


class DiarizationStage(Stage):
    """Produces initial speaker-labelled segments via a DiarizationModel.

    Discards any incoming segments — diarization is a source, not a filter.
    """

    name = "diarization"

    def __init__(self, model: "DiarizationModel") -> None:
        """Инициализирует стадию диаризации.

        Args:
            model (DiarizationModel): Модель определения говорящих.
        """
        self.model = model

    def run(
        self,
        segments: list[Segment],
        context: PipelineContext,
    ) -> list[Segment]:
        """Запускает диаризацию и возвращает размеченные по спикерам сегменты.

        Args:
            segments (list[Segment]): Игнорируется (стадия является источником).
            context (PipelineContext): Контекст с путём к аудиофайлу.

        Returns:
            list[Segment]: Сегменты с заполненным ``speaker_id``.
        """
        return self.model.diarize(context)


class LanguageDetectionStage(Stage):
    """Fills `segment.language` for every segment using a LanguageModel.

    On failure, keeps the segment with language=None so ASR can still run
    it with the default model.
    """

    name = "language_detection"

    def __init__(self, model: "LanguageModel", retries: int = 3) -> None:
        """Инициализирует стадию определения языка.

        Args:
            model (LanguageModel): Модель определения языка.
            retries (int): Количество повторных попыток при ошибке модели.
        """
        self.model = model
        self.retries = retries

    def run(
        self,
        segments: list[Segment],
        context: PipelineContext,
    ) -> list[Segment]:
        """Заполняет поле ``language`` для каждого сегмента.

        При сбое модели сегмент сохраняется с ``language=None``, чтобы ASR
        мог обработать его с моделью по умолчанию.

        Args:
            segments (list[Segment]): Входные сегменты.
            context (PipelineContext): Контекст с событием отмены.

        Returns:
            list[Segment]: Сегменты с заполненным полем ``language``.

        Raises:
            PipelineCancelled: Если установлен флаг ``stop_requested``.
        """
        result: list[Segment] = []
        for s in segments:
            if context.stop_requested.is_set():
                logger.info("LanguageDetectionStage: stop requested, прерываем")
                raise PipelineCancelled()
            lang = retry_on_error(
                lambda seg=s: self.model.detect(seg, context),
                retries=self.retries,
                logger=logger,
            )
            if lang is None:
                logger.warning(
                    "Language detection failed for segment [%.2f, %.2f], keeping with language=None",
                    s.start_time, s.end_time,
                )
            result.append(replace(s, language=lang))
        return result


class ASRStage(Stage):
    """Fills `segment.text` for every segment using an ASRModel.

    If `lang_models` is provided, segments are dispatched to the matching
    model by `segment.language`; unknown or None languages fall back to
    `model`.
    """

    name = "asr"

    def __init__(
        self,
        model: "ASRModel",
        lang_models: "dict[str, ASRModel] | None" = None,
        retries: int = 3,
    ) -> None:
        """Инициализирует стадию ASR.

        Args:
            model (ASRModel): Основная ASR-модель (используется при неизвестном языке).
            lang_models (dict[str, ASRModel] | None): Словарь ``{язык: модель}``
                для маршрутизации по языку сегмента.
            retries (int): Количество повторных попыток при ошибке модели.
        """
        self.model = model
        self.lang_models: dict[str, "ASRModel"] = lang_models or {}
        self.retries = retries

    def run(
        self,
        segments: list[Segment],
        context: PipelineContext,
    ) -> list[Segment]:
        """Транскрибирует каждый сегмент и заполняет поле ``text``.

        Сегменты без текста после успешного ASR удаляются из результата.

        Args:
            segments (list[Segment]): Входные сегменты с заполненным ``language``.
            context (PipelineContext): Контекст с шиной событий для прогресса.

        Returns:
            list[Segment]: Сегменты с непустым ``text``.

        Raises:
            PipelineCancelled: Если установлен флаг ``stop_requested``.
        """
        total = len(segments)
        result: list[Segment] = []
        for i, s in enumerate(segments, start=1):
            if context.stop_requested.is_set():
                logger.info("ASRStage: stop requested после сегмента %d/%d, прерываем", i - 1, total)
                raise PipelineCancelled()
            asr = self.lang_models.get(s.language or "", self.model)
            text = retry_on_error(
                lambda seg=s, m=asr: m.transcribe(seg, context),
                retries=self.retries,
                logger=logger,
            )
            if text is None:
                logger.warning(
                    "ASR failed for segment [%.2f, %.2f], skipping",
                    s.start_time, s.end_time,
                )
            elif text:
                result.append(replace(s, text=text))
            if context.event_bus is not None:
                context.event_bus.publish(
                    ProgressUpdated(
                        run_id=context.run_id,
                        stage_index=context.current_stage_index,
                        stage_name=self.name,
                        current=i,
                        total=total,
                    )
                )
        return result


# ──────────────────────────────────────────────────────────────────────────────
# Stage descriptor registrations (UI metadata)
# ──────────────────────────────────────────────────────────────────────────────

register_stage(StageDescriptor("dummy", "Тест-заглушка", user_visible=False))
register_stage(StageDescriptor(
    "segmentation", "Сегментация",
    default_params={"window_seconds": 30.0},
    requires=frozenset(),
    produces=frozenset({SEGMENTS}),
))
register_stage(StageDescriptor(
    "min_duration_filter", "Фильтр по длительности",
    default_params={"min_seconds": 0.5},
    requires=frozenset({SEGMENTS}),
    produces=frozenset({SEGMENTS}),
))
register_stage(StageDescriptor(
    "diarization", "Диаризация",
    model_type="diarization",
    requires=frozenset(),
    produces=frozenset({SEGMENTS, SPEAKER_LABELS}),
))
register_stage(StageDescriptor(
    "language_detection", "Определение языка",
    model_type="language",
    requires=frozenset({SEGMENTS}),
    produces=frozenset({SEGMENTS, LANGUAGE_LABELS}),
))
register_stage(StageDescriptor(
    "asr", "Транскрипция\n(ASR)",
    model_type="asr",
    requires=frozenset({SEGMENTS}),
    produces=frozenset({SEGMENTS, TRANSCRIPT}),
))
