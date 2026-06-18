# core/storage/ — Хранилище данных

Управляет сохранением и загрузкой данных запусков и проектов.

## Файлы

| Файл | Описание |
|------|---------|
| `run_manager.py` | `RunManager` — директории и файлы отдельного запуска |
| `project_store.py` | `ProjectStore` — JSON-хранилище проектов |
| `run_history_service.py` | `RunHistoryService` — история всех запусков |

## Структура файлов на диске

```
runs/
  run_20240605_143022_abc123/
    config.json       # конфигурация запуска (audio_path, модели, stages)
    state.json        # состояние (completed_stages, status)
    stage_1_segmentation.json
    stage_2_diarization.json
    stage_3_asr.json
    result.json       # итоговый результат (TranscriptionResult)
    result.txt        # текстовый экспорт

projects/
  projects.json       # список проектов [{project_id, name, ...}]
```

## Использование

```python
from core.storage.run_manager import RunManager
from core.storage.project_store import ProjectStore

run_manager = RunManager(runs_root=Path("runs"))
run_dir = run_manager.create_run(run_id, audio_path, config)

store = ProjectStore(projects_dir=Path("projects"))
store.save(project)
projects = store.load_all()
```

## Ссылки

- [core/ — Ядро](../README.md)
- [Документация разработчика: Storage](../../docs/developer/storage.rst)
