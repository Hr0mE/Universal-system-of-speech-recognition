"""Утилита повторных попыток при сбоях ML-моделей.

Используется стадиями ASR и LID для обеспечения устойчивости к временным ошибкам.
"""

from __future__ import annotations

import logging
from typing import Any, Callable


def retry_on_error(
    fn: Callable[[], Any],
    retries: int = 3,
    logger: logging.Logger | None = None,
) -> Any | None:
    """Вызывает функцию до ``retries`` раз.  При всех неудачах возвращает ``None``.

    Args:
        fn (Callable[[], Any]): Функция без аргументов для вызова.
        retries (int): Максимальное число попыток (не менее 1).
        logger (logging.Logger | None): Логгер для предупреждений при сбоях.

    Returns:
        Any | None: Результат первого успешного вызова или ``None``.

    Raises:
        ValueError: Если ``retries`` < 1.
    """
    if retries < 1:
        raise ValueError(f"retries must be >= 1, got {retries}")
    for attempt in range(1, retries + 1):
        try:
            return fn()
        except Exception as exc:
            if logger:
                logger.warning("Attempt %d/%d failed: %s", attempt, retries, exc)
    return None
