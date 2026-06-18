# ui/qt/ — Qt-приложение

Реализация GUI на PySide6 с тёмной темой и многоэкранной навигацией.

## Файлы

| Файл | Описание |
|------|---------|
| `app.py` | `main()` — точка входа: QApplication, тема, главное окно |
| `main_window.py` | `MainWindow` — QStackedWidget + NavBar + маршрутизация |
| `bus_bridge.py` | `BusToQtBridge` — мост EventBus → Qt signals |
| `worker.py` | `TranscribeWorker`, `ResumeWorker` — QThread-воркеры |
| `theme.py` | Константы цветов и `apply_theme()` |
| `nav_bar.py` | `NavBar` — боковая панель навигации |
| `audio_player.py` | `AudioPlayerWidget` — Play/Pause/Stop |
| `timeline.py` | `TimelineWidget` — временная шкала сегментов |
| `settings_dialog.py` | `SettingsDialog` — выбор модели и диаризации |
| `plugins_dialog.py` | `PluginsDialog` — просмотр плагинов |

## Экраны

Все экраны находятся в [`screens/`](screens/README.md).

## Поток данных

```
GUI Event (кнопка)
    ↓
MainWindow._on_start()
    ↓
ProcessingScreen.start(audio_path, models_config)
    ↓
TranscribeWorker (QThread)
    ↓
core.api.transcribe() → EventBus
    ↓
BusToQtBridge (сигналы Qt)
    ↓
ProcessingScreen слоты (_on_stage_started, _on_pipeline_done, ...)
```

## BusToQtBridge

Обеспечивает thread-safety: воркер публикует события из своего потока,
Qt автоматически доставляет сигналы в главный поток через `QueuedConnection`.

```python
bridge = BusToQtBridge()
bridge.stage_done.connect(screen._on_stage_done)
```

## Ссылки

- [ui/ — UI-слой](../README.md)
- [screens/ — Экраны](screens/README.md)
- [Документация разработчика: GUI](../../docs/developer/gui.rst)
