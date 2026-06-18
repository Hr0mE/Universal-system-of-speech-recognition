"""Загрузчик плагинов: директорный скан и entrypoints.

Поддерживает два способа обнаружения плагинов:
- Сканирование директории ``plugins/`` и вызов ``register()`` у каждого файла.
- Загрузка через ``importlib.metadata`` entry_points группы ``ussr_diplom.plugins``.
"""

from __future__ import annotations

import importlib.metadata
import importlib.util
import logging
from pathlib import Path

from core.models.registry import ModelRegistry
from core.pipeline.registry import StageRegistry
from plugins.manifest import PluginManifest

_log = logging.getLogger(__name__)

# Внутренние файлы самой plugin-системы — не являются пользовательскими плагинами.
# timestamp_asr.py здесь — потому что он зарегистрирован как entry_point в pyproject.toml
# и устанавливается при uv sync; dir scan + entry_points привели бы к двойной регистрации.
_INTERNAL_FILES = frozenset({
    "__init__.py",
    "loader.py",
    "manifest.py",
    "builtin_manifests.py",
    "timestamp_asr.py",
})


def load_dir_plugins(
    model_registry: ModelRegistry,
    stage_registry: StageRegistry,
    plugins_dir: Path,
) -> None:
    """Загружает все ``*.py`` файлы из ``plugins_dir`` и регистрирует плагины.

    Для каждого файла вызывает функцию ``register(model_registry, stage_registry)``
    если она присутствует.  Внутренние файлы системы плагинов пропускаются.

    Args:
        model_registry (ModelRegistry): Реестр моделей для регистрации.
        stage_registry (StageRegistry): Реестр стадий для регистрации.
        plugins_dir (Path): Директория с файлами плагинов.
    """
    if not plugins_dir.is_dir():
        return

    for path in sorted(plugins_dir.glob("*.py")):
        if path.name not in _INTERNAL_FILES:
            _load_file_plugin(path, model_registry, stage_registry)


def _load_file_plugin(
    path: Path,
    model_registry: ModelRegistry,
    stage_registry: StageRegistry,
) -> None:
    module_name = f"_plugin_{path.stem}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        _log.warning("Could not load plugin %s: no spec", path)
        return

    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)  # type: ignore[union-attr]
    except Exception as exc:
        _log.warning("Failed to import plugin %s: %s", path.name, exc)
        return

    register_fn = getattr(module, "register", None)
    if register_fn is None:
        return

    try:
        register_fn(model_registry, stage_registry)
    except Exception as exc:
        _log.warning("Plugin %s register() raised: %s", path.name, exc)


def collect_manifests(plugins_dir: Path) -> list[PluginManifest]:
    """Собирает манифесты плагинов из директории (read-only).

    Импортирует ``*.py`` из ``plugins_dir`` и вызывает ``describe()`` при наличии.
    Не вызывает ``register()`` и не изменяет реестры — только метаданные для GUI.

    Args:
        plugins_dir (Path): Директория с файлами плагинов.

    Returns:
        list[PluginManifest]: Список манифестов найденных плагинов.
    """
    if not plugins_dir.is_dir():
        return []

    manifests: list[PluginManifest] = []
    for path in sorted(plugins_dir.glob("*.py")):
        if path.name in _INTERNAL_FILES:
            continue
        manifest = _collect_file_manifest(path)
        if manifest is not None:
            manifests.append(manifest)
    return manifests


def _collect_file_manifest(path: Path) -> PluginManifest | None:
    module_name = f"_manifest_{path.stem}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        return None

    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)  # type: ignore[union-attr]
    except Exception as exc:
        _log.warning("Failed to import plugin %s for manifest: %s", path.name, exc)
        return None

    describe_fn = getattr(module, "describe", None)
    if describe_fn is None:
        return None

    try:
        return describe_fn()
    except Exception as exc:
        _log.warning("Plugin %s describe() raised: %s", path.name, exc)
        return None


def collect_entrypoint_manifests(
    group: str = "ussr_diplom.plugins",
) -> list[PluginManifest]:
    """Собирает манифесты из установленных entry_point плагинов (read-only).

    Не вызывает ``register()`` — только читает метаданные для GUI.

    Args:
        group (str): Группа entry_points для поиска плагинов.

    Returns:
        list[PluginManifest]: Список манифестов найденных плагинов.
    """
    manifests: list[PluginManifest] = []
    try:
        eps = importlib.metadata.entry_points(group=group)
    except Exception as exc:
        _log.warning("Could not discover entry_points for %r: %s", group, exc)
        return []

    for ep in eps:
        module_path = ep.value.split(":")[0]
        try:
            module = importlib.import_module(module_path)
        except Exception as exc:
            _log.warning("Failed to import module for entry_point %r: %s", ep.name, exc)
            continue

        describe_fn = getattr(module, "describe", None)
        if describe_fn is None:
            continue

        try:
            manifests.append(describe_fn())
        except Exception as exc:
            _log.warning("Entry_point %r describe() raised: %s", ep.name, exc)

    return manifests


def load_entrypoint_plugins(
    model_registry: ModelRegistry,
    stage_registry: StageRegistry,
    group: str = "ussr_diplom.plugins",
) -> None:
    """Загружает плагины, объявленные через ``importlib.metadata`` entry_points.

    Args:
        model_registry (ModelRegistry): Реестр моделей для регистрации.
        stage_registry (StageRegistry): Реестр стадий для регистрации.
        group (str): Группа entry_points для поиска плагинов.
    """
    try:
        eps = importlib.metadata.entry_points(group=group)
    except Exception as exc:
        _log.warning("Could not discover entry_points for %r: %s", group, exc)
        return

    for ep in eps:
        try:
            fn = ep.load()
        except Exception as exc:
            _log.warning("Failed to load entry_point %r: %s", ep.name, exc)
            continue

        try:
            fn(model_registry, stage_registry)
        except Exception as exc:
            _log.warning("Entry_point %r register() raised: %s", ep.name, exc)
