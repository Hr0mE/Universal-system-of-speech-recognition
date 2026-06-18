"""Плагин отладочной ASR-модели на основе временны́х меток.

Возвращает временной интервал сегмента вместо реальной транскрипции,
что полезно для проверки корректности pipeline без ML-зависимостей.
"""

from __future__ import annotations

from core.models.base import ASRModel
from core.models.registry import ModelRegistry
from core.pipeline.context import PipelineContext, Segment
from core.pipeline.registry import StageRegistry
from plugins.manifest import ParamSpec, PluginManifest


class TimestampASR(ASRModel):
    """Отладочная ASR-модель, возвращающая временны́е метки сегмента.

    Полезна для отладки pipeline: сразу видно, какие сегменты дошли
    до транскрипции и каковы их границы, без запуска реального ML.

    Attributes:
        name (str): Имя модели в реестре — ``"timestamp-asr"``.

    Args:
        fmt (str): Строка форматирования с полями ``{start}``, ``{end}``,
            ``{lang}`` и ``{speaker}``.
    """

    name = "timestamp-asr"

    def __init__(
        self,
        fmt: str = "[{start:.1f}s – {end:.1f}s | lang={lang} | spk={speaker}]",
    ) -> None:
        """Инициализирует модель со строкой форматирования.

        Args:
            fmt (str): Шаблон вывода с поддерживаемыми полями.
        """
        self.fmt = fmt

    def transcribe(self, segment: Segment, context: PipelineContext) -> str:
        """Форматирует временны́е метки сегмента как текст транскрипции.

        Args:
            segment (Segment): Входной сегмент с границами и метаданными.
            context (PipelineContext): Контекст выполнения (не используется).

        Returns:
            str: Отформатированная строка с временны́ми метками.
        """
        return self.fmt.format(
            start=segment.start_time,
            end=segment.end_time,
            lang=segment.language or "?",
            speaker=segment.speaker_id or "?",
        )


def describe() -> PluginManifest:
    """Возвращает манифест плагина для GUI.

    Returns:
        PluginManifest: Метаданные плагина TimestampASR.
    """
    return PluginManifest(
        name=TimestampASR.name,
        model_type="asr",
        description="Отладочная модель — возвращает временны́е метки сегмента без ML",
        params_schema={
            "fmt": ParamSpec(
                type="string",
                default="[{start:.1f}s – {end:.1f}s | lang={lang} | spk={speaker}]",
                description="Строка форматирования: {start}, {end}, {lang}, {speaker}",
            ),
        },
    )


def register(model_registry: ModelRegistry, stage_registry: StageRegistry) -> None:
    """Регистрирует TimestampASR в реестре моделей.

    Args:
        model_registry (ModelRegistry): Реестр моделей приложения.
        stage_registry (StageRegistry): Реестр стадий (не используется).
    """
    model_registry.register_asr(TimestampASR.name, TimestampASR)
