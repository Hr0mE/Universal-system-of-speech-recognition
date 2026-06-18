# core/pipeline/ — Pipeline транскрибации

Реализует паттерн «цепочка обязанностей» (Chain of Responsibility):
каждый `Stage` обрабатывает список сегментов и передаёт результат следующему.

## Файлы

| Файл | Описание |
|------|---------|
| `stage.py` | Абстрактный класс `Stage` |
| `stages.py` | Конкретные стадии: сегментация, диаризация, ASR и др. |
| `engine.py` | `PipelineEngine` — оркестратор запуска стадий |
| `context.py` | `PipelineContext`, `Segment` — данные прогона |
| `state.py` | `PipelineState` — состояние для resume |
| `registry.py` | `StageRegistry` — реестр стадий плагинов |
| `retry.py` | Декоратор `retry_on_error` |

## Стадии по умолчанию

1. `FixedWindowSegmentationStage` — нарезка на окна (30 с)
2. `DiarizationStage` — разделение спикеров (pyannote)
3. `MinDurationFilterStage` — фильтрация коротких сегментов
4. `LanguageDetectionStage` — определение языка (whisper-lid)
5. `ASRStage` — распознавание речи (faster-whisper)

## Resume-механизм

`PipelineEngine` принимает `PipelineState` с номером последней завершённой стадии.
Стадии до этого номера вызывают `on_stage_skipped()` и эмитируют `StageSkipped`.

```python
engine = PipelineEngine(stages=stages, run_manager=run_manager, event_bus=bus)
engine.run(context, state=saved_state, initial_segments=loaded_segments)
```

## Ссылки

- [core/ — Ядро](../README.md)
- [Документация разработчика: Pipeline](../../docs/developer/pipeline.rst)
