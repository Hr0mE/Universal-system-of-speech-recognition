"""Доменная модель именованного пресета конфигурации пайплайна."""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from core.config.pipeline_config import PipelineConfig


def _new_preset_id() -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = secrets.token_hex(3)
    return f"preset_{ts}_{suffix}"


@dataclass
class PipelinePreset:
    """Именованный пресет конфигурации пайплайна.

    Attributes:
        preset_id: Уникальный идентификатор вида ``preset_YYYYMMDD_HHMMSS_<hex6>``.
        name: Отображаемое имя пресета.
        config: Конфигурация пайплайна.
        created_at: Дата создания в формате ISO 8601.
    """

    preset_id: str
    name: str
    config: PipelineConfig
    created_at: str

    @classmethod
    def new(cls, name: str, config: PipelineConfig) -> "PipelinePreset":
        """Создаёт новый пресет с автогенерируемым ID и текущим временем.

        Raises:
            ValueError: Если ``name`` пустой.
        """
        if not name:
            raise ValueError("name cannot be empty")
        return cls(
            preset_id=_new_preset_id(),
            name=name,
            config=config,
            # microseconds (не seconds): пресеты, созданные в одну секунду, должны
            # сохранять детерминированный порядок «newest first» в load_all().
            created_at=datetime.now().isoformat(timespec="microseconds"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "preset_id": self.preset_id,
            "name": self.name,
            "created_at": self.created_at,
            "config": self.config.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PipelinePreset":
        return cls(
            preset_id=data["preset_id"],
            name=data["name"],
            created_at=data["created_at"],
            config=PipelineConfig.from_dict(data["config"]),
        )
