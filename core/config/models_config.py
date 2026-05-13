from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class ModelSpec:
    """Single model entry from a models config: a registered name + ctor params."""

    name: str
    params: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_obj(cls, obj: Any) -> "ModelSpec":
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
        return asdict(self)


@dataclass(frozen=True)
class ModelsConfig:
    """Snapshot of which models the pipeline should resolve from the registry."""

    asr: ModelSpec
    language_detection: ModelSpec
    diarization: ModelSpec | None = None
    asr_per_language: dict[str, ModelSpec] | None = None

    _KNOWN_KEYS = frozenset({"asr", "language_detection", "diarization", "asr_per_language"})

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ModelsConfig":
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
    raw = path.read_text(encoding="utf-8")
    data = yaml.safe_load(raw) or {}
    if not isinstance(data, dict):
        raise ValueError(
            f"Models config must be a mapping at the top level: {path}"
        )
    return ModelsConfig.from_dict(data)
