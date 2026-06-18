"""Доменная модель проекта транскрибации.

Проект — центральная сущность: связывает аудиофайл с историей запусков pipeline.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

ProjectStatus = Literal["empty", "processing", "completed", "failed", "stopped"]


def _new_project_id() -> str:
    """Генерирует уникальный идентификатор проекта.

    Returns:
        str: Строка вида ``"proj_YYYYMMDD_HHMMSS_<hex6>"``.
    """
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = secrets.token_hex(3)
    return f"proj_{ts}_{suffix}"


@dataclass
class Project:
    """Проект транскрибации: аудиофайл + история запусков pipeline.

    Attributes:
        project_id (str): Уникальный идентификатор проекта.
        name (str): Отображаемое имя проекта.
        audio_path (str): Абсолютный путь к аудиофайлу.
        created_at (str): Дата создания в формате ISO 8601.
        status (ProjectStatus): Текущий статус проекта.
        run_ids (list[str]): Список идентификаторов запусков pipeline.
        duration_s (float): Длительность аудио в секундах.
    """

    project_id: str
    name: str
    audio_path: str
    created_at: str
    status: ProjectStatus = "empty"
    run_ids: list[str] = field(default_factory=list)
    duration_s: float = 0.0

    @classmethod
    def new(cls, name: str, audio_path: str, duration_s: float = 0.0) -> "Project":
        """Создаёт новый проект с автогенерируемым ID и текущим временем.

        Args:
            name (str): Имя проекта.
            audio_path (str): Абсолютный путь к аудиофайлу.
            duration_s (float): Длительность аудио в секундах.

        Returns:
            Project: Новый объект проекта со статусом ``"empty"``.
        """
        return cls(
            project_id=_new_project_id(),
            name=name,
            audio_path=audio_path,
            created_at=datetime.now().isoformat(timespec="seconds"),
            duration_s=duration_s,
        )

    def last_run_id(self) -> str | None:
        """Возвращает идентификатор последнего запуска или ``None``.

        Returns:
            str | None: Последний run_id из списка или ``None`` при пустом списке.
        """
        return self.run_ids[-1] if self.run_ids else None

    def to_dict(self) -> dict:
        """Сериализует проект в словарь для записи в JSON.

        Returns:
            dict: Словарь с полями проекта.
        """
        return {
            "project_id": self.project_id,
            "name": self.name,
            "audio_path": self.audio_path,
            "created_at": self.created_at,
            "status": self.status,
            "run_ids": list(self.run_ids),
            "duration_s": self.duration_s,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Project":
        """Восстанавливает проект из словаря (прочитанного из JSON).

        Args:
            data (dict): Словарь с полями проекта.

        Returns:
            Project: Восстановленный объект.
        """
        return cls(
            project_id=data["project_id"],
            name=data["name"],
            audio_path=data["audio_path"],
            created_at=data["created_at"],
            status=data.get("status", "empty"),
            run_ids=list(data.get("run_ids", [])),
            duration_s=float(data.get("duration_s", 0.0)),
        )
