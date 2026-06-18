# core/config/ — Конфигурация моделей

Загружает и валидирует YAML-конфигурации моделей.

## Файлы

| Файл | Описание |
|------|---------|
| `models_config.py` | `ModelsConfig`, `ModelSpec`, `load_models_config()` |
| `config.py` | Прочие настройки приложения |

## Структура YAML

```yaml
# configs/models_whisper.yaml
asr:
  name: faster-whisper
  params:
    model_size: base
    device: cpu
    compute_type: int8

language_detection:
  name: whisper-lid
  params: {}

diarization:          # опционально
  name: pyannote
  params:
    hf_token: hf_...
```

## Использование

```python
from core.config.models_config import load_models_config

config = load_models_config(Path("configs/models_whisper.yaml"))
print(config.asr.name)          # "faster-whisper"
print(config.asr.params)        # {"model_size": "base", ...}
print(config.diarization)       # None или ModelSpec
```

## Готовые конфигурации

| Файл | Описание |
|------|---------|
| `configs/models_whisper.yaml` | Whisper без диаризации |
| `configs/models_diarization.yaml` | Whisper + pyannote |
| `configs/models_hf.yaml` | HuggingFace-модели |
| `configs/models_timestamp.yaml` | Timestamp ASR плагин |

## Ссылки

- [core/ — Ядро](../README.md)
