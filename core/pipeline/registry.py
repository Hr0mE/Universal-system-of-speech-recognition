"""Реестр фабрик стадий pipeline.

Зарезервирован для будущей конфигурируемой сборки pipeline из плагинов.
В текущей реализации стадии собираются напрямую в :func:`build_stages`.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from core.pipeline.stage import Stage

StageFactory = Callable[..., Stage]


class StageRegistry:
    """Реестр фабрик стадий pipeline: имя → фабрика.

    Зеркалирует API :class:`ModelRegistry`.

    Note:
        В текущей реализации зарезервирован для будущего использования.
        :func:`build_stages` в ``core/api/transcribe.py`` собирает стадии напрямую
        из конфигурации, не запрашивая этот реестр.  Плагины могут регистрировать
        стадии для анонсирования их наличия.
    """

    def __init__(self) -> None:
        """Инициализирует пустой реестр стадий."""
        self._stages: dict[str, StageFactory] = {}

    def register(self, name: str, factory: type[Stage] | StageFactory) -> None:
        """Регистрирует фабрику стадии по имени.

        Args:
            name (str): Уникальное имя стадии.
            factory (type[Stage] | StageFactory): Класс или фабричная функция стадии.

        Raises:
            ValueError: Если имя уже зарегистрировано.
        """
        if name in self._stages:
            raise ValueError(f"Stage already registered: {name!r}")
        self._stages[name] = factory

    def create(self, name: str, **kwargs: Any) -> Stage:
        """Создаёт экземпляр стадии по имени.

        Args:
            name (str): Имя зарегистрированной стадии.
            **kwargs: Параметры для конструктора стадии.

        Returns:
            Stage: Экземпляр стадии.

        Raises:
            KeyError: Если стадия не зарегистрирована.
        """
        if name not in self._stages:
            known = sorted(self._stages)
            raise KeyError(f"Unknown stage: {name!r}. Registered: {known}")
        return self._stages[name](**kwargs)

    def list(self) -> list[str]:
        """Возвращает отсортированный список зарегистрированных стадий."""
        return sorted(self._stages)

    def __len__(self) -> int:
        """Возвращает количество зарегистрированных стадий."""
        return len(self._stages)
