"""Состояние выполнения pipeline и константы статусов.

Используется :class:`PipelineEngine` для отслеживания прогресса и поддержки
возобновления прерванных запусков (resume).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

STATUS_PENDING = "pending"
STATUS_RUNNING = "running"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"
STATUS_STOPPED = "stopped"


@dataclass
class PipelineState:
    """Tracks which stages of a run have been completed.

    `last_stage_index` is the 1-based index of the last fully completed stage
    (0 means nothing has finished yet). A stage with index <= last_stage_index
    is considered done and will be skipped on resume.
    """

    run_id: str
    completed_stages: list[str] = field(default_factory=list)
    last_stage_index: int = 0
    status: str = STATUS_PENDING

    def mark_stage_done(self, index: int, name: str) -> None:
        """Отмечает стадию как завершённую.

        Args:
            index (int): 1-based индекс завершённой стадии.
            name (str): Имя стадии.
        """
        self.last_stage_index = index
        if name not in self.completed_stages:
            self.completed_stages.append(name)

    def to_dict(self) -> dict[str, Any]:
        """Сериализует состояние в словарь для записи в state.json.

        Returns:
            dict[str, Any]: Словарь с полями dataclass.
        """
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PipelineState":
        """Восстанавливает состояние из словаря, прочитанного из state.json.

        Args:
            data (dict[str, Any]): Словарь с полями состояния.

        Returns:
            PipelineState: Восстановленный объект состояния.
        """
        return cls(
            run_id=data["run_id"],
            completed_stages=list(data.get("completed_stages", [])),
            last_stage_index=int(data.get("last_stage_index", 0)),
            status=str(data.get("status", STATUS_PENDING)),
        )
