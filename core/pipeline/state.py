from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

# Status values: pending | running | completed | failed
STATUS_PENDING = "pending"
STATUS_RUNNING = "running"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"


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
        self.last_stage_index = index
        if name not in self.completed_stages:
            self.completed_stages.append(name)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PipelineState":
        return cls(
            run_id=data["run_id"],
            completed_stages=list(data.get("completed_stages", [])),
            last_stage_index=int(data.get("last_stage_index", 0)),
            status=str(data.get("status", STATUS_PENDING)),
        )
