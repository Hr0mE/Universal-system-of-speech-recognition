# core/api/ — Высокоуровневый API транскрибации

Единая точка входа для запуска pipeline из кода или CLI.

## Файлы

| Файл | Описание |
|------|---------|
| `transcribe.py` | `transcribe()`, `resume_transcription()`, `TranscriptionResult` |
| `__init__.py` | Реэкспорт: `transcribe`, `TranscriptionResult` |

## Основные сущности

### `TranscriptionResult`

```python
@dataclass
class TranscriptionResult:
    segments: list[Segment]   # результат pipeline
    run_id: str               # уникальный ID запуска
    run_dir: Path             # директория с артефактами
    audio_path: str           # путь к исходному аудио
    duration_s: float         # длительность в секундах
```

### `transcribe()`

```python
result = transcribe(
    audio_path=Path("audio.wav"),
    models_config=Path("configs/models_whisper.yaml"),
    runs_dir=Path("runs"),
    window_seconds=30.0,
    event_bus=bus,          # опционально — для подписки на события
)
```

### `resume_transcription()`

```python
result = resume_transcription(run_id="run_20240605_143022_abc123")
```

## Ссылки

- [core/ — Ядро](../README.md)
- [Документация разработчика: API](../../docs/developer/api.rst)
