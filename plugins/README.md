# plugins/ — Система плагинов

Позволяет добавлять новые ML-модели и стадии pipeline без изменения ядра.
Плагины регистрируются через локальные файлы или `entry_points` (pip-пакеты).

## Файлы

| Файл | Описание |
|------|---------|
| `manifest.py` | `PluginManifest`, `ModelOption`, `ParamSpec` |
| `loader.py` | `load_dir_plugins()`, `load_entrypoint_plugins()`, `collect_manifests()` |
| `builtin_manifests.py` | Встроенные манифесты (faster-whisper, pyannote) |
| `timestamp_asr.py` | Пример плагина ASR с временными метками |
| `__init__.py` | `setup_plugins()`, `all_manifests()` |

## Как создать плагин

### 1. Реализовать модель

```python
from core.models.base import ASRModel

class MyModel(ASRModel):
    def transcribe(self, segments, audio_path, language=None):
        ...
```

### 2. Добавить манифест

```python
from plugins.manifest import PluginManifest, ModelOption

MANIFEST = PluginManifest(
    name="my-model",
    model_type="asr",
    description="Моя модель",
    available_models=[ModelOption(id="my-model-base", display_name="Base", size_mb=150)],
)

def register(model_registry, stage_registry):
    model_registry.register_asr("my-model", MyModel)
```

### 3. Разместить файл

Поместите `my_plugin.py` в директорию `plugins/` — он будет загружен автоматически.

## Через entry_points

```toml
# pyproject.toml
[project.entry-points."ussr_diplom.plugins"]
my-model = "my_package.plugin:register"
```

## Ссылки

- [Главный README](../README.md)
- [core/models/ — Модели](../core/models/README.md)
- [Документация разработчика: Plugins](../docs/developer/plugins.rst)
