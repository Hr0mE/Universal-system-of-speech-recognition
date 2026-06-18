"""Абстрактный базовый класс стадии pipeline и реестр дескрипторов для UI.

Все стадии наследуют :class:`Stage` и реализуют метод :meth:`Stage.run`.
:class:`StageDescriptor` хранит метаданные этапа для отображения в сайдбаре.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from core.pipeline.context import PipelineContext, Segment


# ──────────────────────────────────────────────────────────────────────────────
# Stage descriptor registry
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class StageDescriptor:
    """UI-метаданные этапа пайплайна.

    Attributes:
        stage_id: Уникальный идентификатор этапа (совпадает с ``Stage.name``).
        display_name: Название для отображения в UI (может содержать ``\\n``).
        user_visible: ``False`` — скрыть из сайдбара (например, DummyStage).
        model_type: Тип модели для фильтрации манифестов (``None`` — алгоритмический этап).
        default_params: Параметры по умолчанию для алгоритмических этапов.
    """

    stage_id: str
    display_name: str
    user_visible: bool = True
    model_type: str | None = None
    default_params: dict[str, Any] = field(default_factory=dict)
    requires: frozenset[str] = field(default_factory=frozenset)
    produces: frozenset[str] = field(default_factory=frozenset)


_DESCRIPTOR_REGISTRY: dict[str, StageDescriptor] = {}


def register_stage(descriptor: StageDescriptor) -> StageDescriptor:
    """Регистрирует дескриптор этапа в глобальном реестре."""
    _DESCRIPTOR_REGISTRY[descriptor.stage_id] = descriptor
    return descriptor


def all_stage_descriptors() -> list[StageDescriptor]:
    """Возвращает все видимые пользователю дескрипторы в порядке регистрации."""
    return [d for d in _DESCRIPTOR_REGISTRY.values() if d.user_visible]


def get_stage_descriptor(stage_id: str) -> StageDescriptor | None:
    """Возвращает дескриптор по ``stage_id`` или ``None``."""
    return _DESCRIPTOR_REGISTRY.get(stage_id)


class Stage(ABC):
    """Абстрактная стадия pipeline.

    Каждая стадия трансформирует список сегментов и возвращает новый список.
    Движок :class:`PipelineEngine` вызывает стадии последовательно.

    Attributes:
        name (str): Уникальное имя стадии (используется для логирования и чекпоинтов).
    """

    name: str

    @abstractmethod
    def run(
        self,
        segments: list["Segment"],
        context: "PipelineContext",
    ) -> list["Segment"]:
        """Выполняет стадию и возвращает трансформированные сегменты.

        Args:
            segments (list[Segment]): Входные сегменты от предыдущей стадии.
            context (PipelineContext): Контекст запуска с метаданными и шиной событий.

        Returns:
            list[Segment]: Выходные сегменты для следующей стадии.
        """

    def on_stage_skipped(self, context: "PipelineContext") -> None:
        """Вызывается при пропуске стадии во время resume.

        Переопределите для освобождения ресурсов или логирования.

        Args:
            context (PipelineContext): Контекст текущего запуска.
        """
