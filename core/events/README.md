# core/events/ — Система событий

Реализует паттерн «наблюдатель» (Observer) через `EventBus`.
Pipeline публикует события — UI и CLI подписываются и реагируют.

## Файлы

| Файл | Описание |
|------|---------|
| `bus.py` | `EventBus` — pub/sub шина событий |
| `events.py` | Датаклассы всех событий |

## EventBus

```python
bus = EventBus()
bus.subscribe(PipelineStarted, lambda e: print(f"Старт: {e.run_id}"))
bus.subscribe(StageFinished, lambda e: print(f"Стадия {e.stage_index} готова"))

bus.publish(PipelineStarted(run_id="abc", audio_path="audio.wav",
                             total_stages=5, resume_after=0))
```

## Список событий

| Событие | Когда |
|---------|-------|
| `PipelineStarted` | Pipeline запущен |
| `PipelineFinished` | Pipeline завершён успешно |
| `PipelineFailed` | Pipeline завершён с ошибкой |
| `StageStarted` | Стадия начала выполнение |
| `StageFinished` | Стадия завершена |
| `StageSkipped` | Стадия пропущена (resume) |
| `ProgressUpdated` | Прогресс внутри стадии |
| `ModelDownloadStarted` | Началась загрузка модели |
| `ModelDownloadFinished` | Модель готова |

## Ссылки

- [core/ — Ядро](../README.md)
- [ui/qt/bus_bridge.py](../../ui/qt/bus_bridge.py) — Qt-мост
- [Документация разработчика: Events](../../docs/developer/events.rst)
