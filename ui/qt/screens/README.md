# ui/qt/screens/ — Экраны приложения

Каждый экран — самостоятельный `QWidget`, добавленный в `QStackedWidget` главного окна.

## Экраны

| Файл | Класс | Описание |
|------|-------|---------|
| `projects.py` | `ProjectsScreen` | Список проектов (стартовый экран) |
| `welcome.py` | `WelcomeScreen` | Импорт аудиофайла (drag-and-drop) |
| `processing.py` | `ProcessingScreen` | Прогресс транскрибации |
| `result.py` | `ResultScreen` | Просмотр и экспорт результата |
| `editor.py` | `TranscriptEditorScreen` | Редактирование сегментов |
| `models.py` | `ModelsScreen` | Просмотр доступных моделей |
| `run_history.py` | `RunHistoryScreen` | История запусков |

## Карта переходов

```
ProjectsScreen
  ├── [+ Новый проект] → WelcomeScreen
  │     └── [Начать] → ProcessingScreen
  │           ├── [Успех] → ResultScreen
  │           │     └── [Редактировать] → TranscriptEditorScreen
  │           └── [Назад] → WelcomeScreen / ProjectsScreen
  ├── [Проект] → WelcomeScreen (с предзаполненным файлом)
  ├── [История] → RunHistoryScreen
  └── [Модели] → ModelsScreen
```

## Сигналы экранов

Каждый экран использует `Signal` для общения с `MainWindow`, не зная о других экранах:

```python
# Пример из WelcomeScreen
file_accepted = Signal(Path)       # новый запуск
resume_requested = Signal(Path)    # возобновление
```

## Ссылки

- [ui/qt/ — Qt-приложение](../README.md)
- [Документация разработчика: GUI](../../../docs/developer/gui.rst)
