# core/domain/ — Доменные сущности

Чистые доменные объекты без зависимостей от инфраструктуры.

## Файлы

| Файл | Описание |
|------|---------|
| `project.py` | `Project` — проект транскрибации |

## Project

```python
@dataclass
class Project:
    project_id: str      # уникальный ID (UUID4)
    name: str            # имя файла или пользовательское
    audio_path: str      # путь к аудиофайлу
    created_at: str      # ISO 8601
    status: str          # empty | processing | completed | stopped | failed
    duration_s: float    # длительность аудио в секундах
    last_run_id: str      # ID последнего запуска (или "")
```

## Создание и сериализация

```python
from core.domain.project import Project

project = Project.new(audio_path=Path("meeting.wav"))
d = project.to_dict()          # → dict для JSON
p2 = Project.from_dict(d)      # → Project из dict
```

## Ссылки

- [core/ — Ядро](../README.md)
- [core/storage/ — Хранилище](../storage/README.md)
