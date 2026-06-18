# core/export/ — Экспорт результатов

Преобразует `TranscriptionResult` в структурированные отчёты и файлы экспорта.

## Файлы

| Файл | Описание |
|------|---------|
| `report.py` | `MeetingReport`, `SpeakerGroup`, `build_meeting_report()`, `export_json()`, `export_txt()` |

## MeetingReport

```python
@dataclass
class MeetingReport:
    run_id: str
    audio_path: str
    duration_s: float
    speakers: list[SpeakerGroup]   # группы по спикеру

@dataclass
class SpeakerGroup:
    speaker_id: str | None
    total_duration: float
    segments: list[Segment]
```

## Использование

```python
from core.export import build_meeting_report, export_json, export_txt

report = build_meeting_report(result)
export_json(report, Path("result.json"))
export_txt(report, Path("result.txt"))
```

## Формат JSON

```json
{
  "run_id": "run_20240605_143022_abc123",
  "duration_s": 312.5,
  "speakers": [
    {
      "speaker_id": "SPEAKER_00",
      "total_duration": 145.2,
      "segments": [...]
    }
  ]
}
```

## Ссылки

- [core/ — Ядро](../README.md)
- [Документация пользователя: Экспорт](../../docs/user/export.rst)
