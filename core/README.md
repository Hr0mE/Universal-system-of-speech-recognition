# core/ — Ядро приложения

Содержит всю бизнес-логику: pipeline транскрибации, ML-модели, систему событий,
хранилище данных, конфигурацию и экспорт результатов.

## Пакеты

| Пакет | Описание |
|-------|---------|
| [`api/`](api/README.md) | Высокоуровневый API: `transcribe()`, `TranscriptionResult` |
| [`config/`](config/README.md) | Конфигурация моделей: `ModelsConfig`, `ModelSpec` |
| [`domain/`](domain/README.md) | Доменные сущности: `Project` |
| [`events/`](events/README.md) | EventBus (pub/sub) и датаклассы событий |
| [`export/`](export/README.md) | Экспорт: `MeetingReport`, JSON, TXT |
| [`models/`](models/README.md) | Абстракции и реестр ML-моделей |
| [`pipeline/`](pipeline/README.md) | Pipeline: Stage, Engine, Context, State |
| [`storage/`](storage/README.md) | Хранилище: RunManager, ProjectStore |

## Как связаны пакеты

```
api/ → pipeline/ → models/
              ↓
           events/ → (UI через BusToQtBridge)
              ↓
           storage/
              ↓
           export/
```

## Пример использования

```python
from core.api.transcribe import transcribe

result = transcribe(
    Path("meeting.wav"),
    models_config=Path("configs/models_whisper.yaml"),
)
print(f"Сегментов: {len(result.segments)}")
```

## Ссылки

- [Документация разработчика](../docs/developer/index.rst)
- [Главный README](../README.md)
