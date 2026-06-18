"""Конфигурация пайплайна транскрибации, управляемая пользователем.

Предоставляет :class:`PipelineConfig` — единственный источник правды о составе,
порядке и параметрах этапов.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_CONFIG_PATH = Path.home() / ".ussr_diplom" / "pipeline.json"
_VERSION = 1

# Единственные stage_id, выставляемые в GUI
STAGE_DIARIZATION = "diarization"
STAGE_LANGUAGE_DETECTION = "language_detection"
STAGE_ASR = "asr"


@dataclass
class StageConfig:
    """Конфигурация одного пользовательского этапа пайплайна.

    Attributes:
        stage_id: Идентификатор этапа — ``"diarization"``, ``"language_detection"`` или ``"asr"``.
        enabled: Включён ли этап в пайплайн.
        model_name: Имя плагина/модели в реестре (например, ``"faster-whisper"``).
        params: Параметры модели, соответствующие схеме манифеста плагина.
    """

    stage_id: str
    enabled: bool
    model_name: str
    params: dict[str, Any] = field(default_factory=dict)
    lang_model_map: dict[str, dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage_id": self.stage_id,
            "enabled": self.enabled,
            "model_name": self.model_name,
            "params": dict(self.params),
            "lang_model_map": {k: dict(v) for k, v in self.lang_model_map.items()},
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StageConfig":
        raw_map = data.get("lang_model_map") or {}
        return cls(
            stage_id=str(data["stage_id"]),
            enabled=bool(data["enabled"]),
            model_name=str(data["model_name"]),
            params=dict(data.get("params") or {}),
            lang_model_map={k: dict(v) for k, v in raw_map.items()},
        )


@dataclass
class PipelineConfig:
    """Полная конфигурация пайплайна: упорядоченный список пользовательских этапов.

    Порядок элементов в :attr:`stages` соответствует порядку выполнения этапов.
    """

    stages: list[StageConfig] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    def get_stage(self, stage_id: str) -> StageConfig | None:
        for s in self.stages:
            if s.stage_id == stage_id:
                return s
        return None

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": _VERSION,
            "stages": [s.to_dict() for s in self.stages],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PipelineConfig":
        stages = [StageConfig.from_dict(s) for s in data.get("stages", [])]
        return cls(stages=stages)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, path: Path = _CONFIG_PATH) -> None:
        """Сохраняет конфигурацию в JSON-файл."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path = _CONFIG_PATH) -> "PipelineConfig":
        """Загружает конфигурацию из JSON-файла.

        Raises:
            FileNotFoundError: Если файл не существует.
        """
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls.from_dict(data)


def load_pipeline_config(path: Path = _CONFIG_PATH) -> PipelineConfig:
    """Загружает ``PipelineConfig`` из файла, fallback — дефолтный конфиг."""
    try:
        return PipelineConfig.load(path)
    except (FileNotFoundError, KeyError, ValueError, json.JSONDecodeError):
        return default_pipeline_config()


def default_pipeline_config() -> PipelineConfig:
    """Возвращает ``PipelineConfig``, соответствующий ``DEFAULT_MODELS_CONFIG``."""
    return PipelineConfig(stages=[
        StageConfig(
            stage_id="segmentation",
            enabled=True,
            model_name="",
            params={"window_seconds": 30.0},
        ),
        StageConfig(
            stage_id="min_duration_filter",
            enabled=True,
            model_name="",
            params={"min_seconds": 0.5},
        ),
        StageConfig(
            stage_id=STAGE_DIARIZATION,
            enabled=False,
            model_name="pyannote",
            params={"hf_token": "", "min_speakers": 1, "max_speakers": 10},
        ),
        StageConfig(
            stage_id=STAGE_LANGUAGE_DETECTION,
            enabled=True,
            model_name="whisper-lid",
            params={"model_size": "tiny", "device": "cpu"},
        ),
        StageConfig(
            stage_id=STAGE_ASR,
            enabled=True,
            model_name="faster-whisper",
            params={"model_size": "tiny", "device": "cpu", "compute_type": "int8"},
        ),
    ])
