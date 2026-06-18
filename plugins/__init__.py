"""Система плагинов: загрузка, манифесты, регистрация моделей и стадий."""

from __future__ import annotations

from pathlib import Path

from core.models.registry import ModelRegistry
from plugins.builtin_manifests import BUILTIN_MANIFESTS
from core.pipeline.registry import StageRegistry
from plugins.loader import (
    collect_entrypoint_manifests,
    collect_manifests,
    load_dir_plugins,
    load_entrypoint_plugins,
)
from plugins.manifest import PluginManifest

PLUGINS_DIR = Path(__file__).parent

__all__ = [
    "BUILTIN_MANIFESTS",
    "PLUGINS_DIR",
    "all_manifests",
    "collect_entrypoint_manifests",
    "collect_manifests",
    "load_dir_plugins",
    "load_entrypoint_plugins",
    "setup_plugins",
]


def all_manifests(plugins_dir: Path = PLUGINS_DIR) -> list[PluginManifest]:
    """Возвращает все манифесты: встроенные + файловые плагины + entry_points.

    Дедуплицирует по имени; встроенные манифесты имеют приоритет.

    Args:
        plugins_dir (Path): Директория для поиска файловых плагинов.

    Returns:
        list[PluginManifest]: Список уникальных манифестов.
    """
    seen: set[str] = set()
    result: list[PluginManifest] = []
    for m in (
        *BUILTIN_MANIFESTS,
        *collect_manifests(plugins_dir),
        *collect_entrypoint_manifests(),
    ):
        if m.name not in seen:
            seen.add(m.name)
            result.append(m)
    return result


def setup_plugins(
    model_registry: ModelRegistry,
    stage_registry: StageRegistry,
    plugins_dir: Path = PLUGINS_DIR,
) -> None:
    """Загружает плагины из локальной директории и установленных entry_points.

    Args:
        model_registry (ModelRegistry): Реестр моделей для регистрации плагинов.
        stage_registry (StageRegistry): Реестр стадий для регистрации плагинов.
        plugins_dir (Path): Директория для поиска файловых плагинов.
    """
    load_dir_plugins(model_registry, stage_registry, plugins_dir)
    load_entrypoint_plugins(model_registry, stage_registry)
