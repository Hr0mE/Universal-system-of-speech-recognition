from __future__ import annotations

from plugins.manifest import ModelOption, ParamSpec, PluginManifest

_WHISPER_MODELS = [
    ModelOption("Systran/faster-whisper-tiny",    "Whisper Tiny (75 MB)",     [], 75),
    ModelOption("Systran/faster-whisper-base",    "Whisper Base (145 MB)",    [], 145),
    ModelOption("Systran/faster-whisper-small",   "Whisper Small (244 MB)",   [], 244),
    ModelOption("Systran/faster-whisper-medium",  "Whisper Medium (769 MB)",  [], 769),
    ModelOption("Systran/faster-whisper-large-v3","Whisper Large v3 (3.1 GB)",[], 3100),
]

BUILTIN_MANIFESTS: list[PluginManifest] = [
    PluginManifest(
        name="faster-whisper",
        model_type="asr",
        description="Whisper на CTranslate2, работает на CPU без GPU",
        hf_repo="Systran/faster-whisper-large-v3",
        available_models=_WHISPER_MODELS,
        params_schema={
            "model_size": ParamSpec(
                type="string",
                default="tiny",
                description="Размер модели: больше = точнее, медленнее",
            ),
            "device": ParamSpec(
                type="string",
                default="cpu",
                description="Устройство вычислений: cpu или cuda",
            ),
            "compute_type": ParamSpec(
                type="enum",
                default="int8",
                values=["int8", "float16", "float32"],
                description="Тип вычислений (квантизация)",
            ),
        },
    ),
    PluginManifest(
        name="whisper-lid",
        model_type="language",
        description="Определение языка через Whisper (faster-whisper)",
        hf_repo="Systran/faster-whisper-large-v3",
        available_models=_WHISPER_MODELS,
        params_schema={
            "model_size": ParamSpec(
                type="string",
                default="tiny",
                description="Размер модели Whisper для LID",
            ),
            "device": ParamSpec(
                type="string",
                default="cpu",
                description="Устройство вычислений",
            ),
        },
    ),
    PluginManifest(
        name="pyannote",
        model_type="diarization",
        description="Диаризация спикеров через pyannote.audio",
        hf_repo="pyannote/speaker-diarization-3.1",
        available_models=[
            ModelOption(
                hf_repo="pyannote/speaker-diarization-3.1",
                display_name="Pyannote Speaker Diarization 3.1",
                languages=[],
                size_mb=600,
                requires_token=True,
                description="Требует принятия условий использования на HuggingFace и HF_TOKEN",
            ),
        ],
        params_schema={
            "hf_token": ParamSpec(
                type="string",
                default="",
                description="HuggingFace токен (или задать через HF_TOKEN в .env)",
            ),
            "min_speakers": ParamSpec(
                type="int",
                default=1,
                description="Минимальное число спикеров",
            ),
            "max_speakers": ParamSpec(
                type="int",
                default=10,
                description="Максимальное число спикеров",
            ),
        },
    ),
    PluginManifest(
        name="dummy",
        model_type="asr",
        description="Заглушка для тестов — возвращает временны́е метки без ML",
        params_schema={},
    ),
]

__all__ = ["BUILTIN_MANIFESTS"]
