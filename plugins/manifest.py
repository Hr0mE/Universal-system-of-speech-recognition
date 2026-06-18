"""Декларативные метаданные плагинов.

Содержит датаклассы :class:`PluginManifest`, :class:`ModelOption` и
:class:`ParamSpec`, описывающие возможности плагина для GUI.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

_VALID_MODEL_TYPES = frozenset({"asr", "language", "diarization", "stage"})
_VALID_PARAM_TYPES = frozenset({"string", "int", "float", "bool", "enum"})


@dataclass(frozen=True)
class ModelOption:
    """Конкретная версия модели, доступная для загрузки с HuggingFace Hub.

    Attributes:
        hf_repo (str): Репозиторий HuggingFace (например, ``"openai/whisper-tiny"``).
        display_name (str): Отображаемое имя модели в GUI.
        languages (list[str]): Список поддерживаемых кодов языков.
        size_mb (int): Приблизительный размер модели в МБ.
        requires_token (bool): Требуется ли HuggingFace токен для загрузки.
        description (str): Описание модели для GUI.
    """

    hf_repo: str
    display_name: str
    languages: list[str]
    size_mb: int
    requires_token: bool = False
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Сериализует вариант модели в словарь.

        Returns:
            dict[str, Any]: Словарь с полями объекта (опциональные поля опускаются).
        """
        d: dict[str, Any] = {
            "hf_repo": self.hf_repo,
            "display_name": self.display_name,
            "languages": list(self.languages),
            "size_mb": self.size_mb,
        }
        if self.requires_token:
            d["requires_token"] = True
        if self.description:
            d["description"] = self.description
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ModelOption":
        return cls(
            hf_repo=data["hf_repo"],
            display_name=data["display_name"],
            languages=list(data.get("languages", [])),
            size_mb=int(data["size_mb"]),
            requires_token=bool(data.get("requires_token", False)),
            description=data.get("description", ""),
        )


@dataclass(frozen=True)
class ParamSpec:
    """Описание одного параметра модели для рендеринга формы в GUI.

    Attributes:
        type (str): Тип параметра: ``"string"``, ``"int"``, ``"float"``,
            ``"bool"`` или ``"enum"``.
        default (Any): Значение по умолчанию.
        values (list[str] | None): Допустимые значения для типа ``"enum"``.
        description (str): Подсказка для пользователя в GUI.
    """

    type: str
    default: Any
    values: list[str] | None = None
    description: str = ""

    def __post_init__(self) -> None:
        """Валидирует, что enum-тип имеет непустой список значений.

        Raises:
            ValueError: Если тип ``"enum"`` и ``values`` пуст или ``None``.
        """
        if self.type == "enum" and not self.values:
            raise ValueError(
                "ParamSpec with type='enum' must have a non-empty 'values' list"
            )

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"type": self.type, "default": self.default}
        if self.values is not None:
            d["values"] = list(self.values)
        if self.description:
            d["description"] = self.description
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ParamSpec":
        return cls(
            type=data["type"],
            default=data["default"],
            values=data.get("values"),
            description=data.get("description", ""),
        )


@dataclass(frozen=True)
class PluginManifest:
    """Декларативные метаданные плагина для построения форм конфига в GUI.

    Attributes:
        name (str): Уникальное имя плагина (совпадает с именем в реестре).
        model_type (str): Тип модели: ``"asr"``, ``"language"``, ``"diarization"``
            или ``"stage"``.
        description (str): Краткое описание для отображения в GUI.
        hf_repo (str | None): Репозиторий HuggingFace по умолчанию.
        params_schema (dict[str, ParamSpec]): Схема параметров конфигурации.
        available_models (list[ModelOption]): Список доступных вариантов модели.
    """

    name: str
    model_type: str
    description: str = ""
    hf_repo: str | None = None
    params_schema: dict[str, ParamSpec] = field(default_factory=dict)
    available_models: list[ModelOption] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Валидирует тип модели.

        Raises:
            ValueError: Если ``model_type`` не входит в допустимые значения.
        """
        if self.model_type not in _VALID_MODEL_TYPES:
            raise ValueError(
                f"Invalid model_type: {self.model_type!r}. "
                f"Must be one of {sorted(_VALID_MODEL_TYPES)}"
            )

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "name": self.name,
            "model_type": self.model_type,
        }
        if self.description:
            d["description"] = self.description
        if self.hf_repo is not None:
            d["hf_repo"] = self.hf_repo
        if self.params_schema:
            d["params_schema"] = {k: v.to_dict() for k, v in self.params_schema.items()}
        if self.available_models:
            d["available_models"] = [m.to_dict() for m in self.available_models]
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PluginManifest":
        params_schema = {
            k: ParamSpec.from_dict(v)
            for k, v in data.get("params_schema", {}).items()
        }
        available_models = [
            ModelOption.from_dict(m) for m in data.get("available_models", [])
        ]
        return cls(
            name=data["name"],
            model_type=data["model_type"],
            description=data.get("description", ""),
            hf_repo=data.get("hf_repo"),
            params_schema=params_schema,
            available_models=available_models,
        )
