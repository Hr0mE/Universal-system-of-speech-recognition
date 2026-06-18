"""Конфигурация моделей pipeline.

Содержит датаклассы :class:`ModelSpec` и :class:`ModelsConfig`, а также
функцию :func:`load_models_config` для загрузки из YAML.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class ModelSpec:
    """Спецификация одной модели из конфигурации: имя в реестре + параметры.

    Attributes:
        name (str): Имя модели в :class:`ModelRegistry`.
        params (dict): Параметры, передаваемые фабрике при создании экземпляра.
    """

    name: str
    params: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_obj(cls, obj: Any) -> "ModelSpec":
        """Создаёт :class:`ModelSpec` из строки или словаря конфигурации.

        Args:
            obj (Any): Строка (только имя) или словарь ``{name, params}``.

        Returns:
            ModelSpec: Спецификация модели.

        Raises:
            ValueError: Если в словаре отсутствует ключ ``name`` или ``params`` не является mapping.
            TypeError: Если тип ``obj`` не поддерживается.
        """
        if isinstance(obj, str):
            return cls(name=obj)
        if isinstance(obj, dict):
            if "name" not in obj:
                raise ValueError(f"Model spec missing 'name': {obj!r}")
            params = obj.get("params") or {}
            if not isinstance(params, dict):
                raise ValueError(
                    f"Model spec 'params' must be a mapping, got {type(params).__name__}"
                )
            return cls(name=str(obj["name"]), params=dict(params))
        raise TypeError(f"Invalid model spec: {obj!r}")

    def to_dict(self) -> dict[str, Any]:
        """Сериализует спецификацию в словарь.

        Returns:
            dict[str, Any]: Словарь с полями dataclass.
        """
        return asdict(self)


@dataclass(frozen=True)
class ModelsConfig:
    """Снимок конфигурации моделей pipeline.

    Attributes:
        asr (ModelSpec): Основная ASR-модель.
        language_detection (ModelSpec): Модель определения языка.
        diarization (ModelSpec | None): Опциональная модель диаризации.
        asr_per_language (dict[str, ModelSpec] | None): Словарь моделей ASR по языкам.
    """

    asr: ModelSpec
    language_detection: ModelSpec
    diarization: ModelSpec | None = None
    asr_per_language: dict[str, ModelSpec] | None = None

    _KNOWN_KEYS = frozenset({"asr", "language_detection", "diarization", "asr_per_language"})

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ModelsConfig":
        """Создаёт конфигурацию из словаря (прочитанного из YAML).

        Args:
            data (dict[str, Any]): Словарь с ключами ``asr``, ``language_detection``
                и опционально ``diarization``, ``asr_per_language``.

        Returns:
            ModelsConfig: Конфигурация моделей.

        Raises:
            ValueError: При неизвестных ключах или отсутствии обязательных полей.
        """
        unknown = sorted(set(data) - cls._KNOWN_KEYS)
        if unknown:
            raise ValueError(f"Unknown keys in models config: {unknown}")
        missing = [k for k in ("asr", "language_detection") if k not in data]
        if missing:
            raise ValueError(
                f"Models config missing required keys: {missing}"
            )
        diar_obj = data.get("diarization")
        apl_obj = data.get("asr_per_language")
        asr_per_language: dict[str, ModelSpec] | None = None
        if apl_obj is not None:
            if not isinstance(apl_obj, dict):
                raise ValueError("asr_per_language must be a mapping")
            asr_per_language = {
                lang: ModelSpec.from_obj(spec) for lang, spec in apl_obj.items()
            }
        return cls(
            asr=ModelSpec.from_obj(data["asr"]),
            language_detection=ModelSpec.from_obj(data["language_detection"]),
            diarization=ModelSpec.from_obj(diar_obj) if diar_obj else None,
            asr_per_language=asr_per_language,
        )

    def to_dict(self) -> dict[str, Any]:
        """Сериализует конфигурацию в словарь для сохранения в YAML.

        Returns:
            dict[str, Any]: Словарь с конфигурацией всех моделей.
        """
        out: dict[str, Any] = {
            "asr": self.asr.to_dict(),
            "language_detection": self.language_detection.to_dict(),
        }
        if self.diarization is not None:
            out["diarization"] = self.diarization.to_dict()
        if self.asr_per_language is not None:
            out["asr_per_language"] = {
                lang: spec.to_dict()
                for lang, spec in self.asr_per_language.items()
            }
        return out


def load_models_config(path: Path) -> ModelsConfig:
    """Загружает конфигурацию моделей из YAML-файла.

    Args:
        path (Path): Путь к YAML-файлу конфигурации.

    Returns:
        ModelsConfig: Конфигурация моделей.

    Raises:
        ValueError: Если содержимое файла не является mapping на верхнем уровне.
    """
    raw = path.read_text(encoding="utf-8")
    data = yaml.safe_load(raw) or {}
    if not isinstance(data, dict):
        raise ValueError(
            f"Models config must be a mapping at the top level: {path}"
        )
    return ModelsConfig.from_dict(data)


DEFAULT_MODELS_CONFIG = ModelsConfig(
    asr=ModelSpec(
        name="faster-whisper",
        params={"model_size": "tiny", "device": "cpu", "compute_type": "int8"},
    ),
    language_detection=ModelSpec(
        name="whisper-lid",
        params={"model_size": "tiny", "device": "cpu", "compute_type": "int8"},
    ),
    diarization=None,
    asr_per_language=None,
)
