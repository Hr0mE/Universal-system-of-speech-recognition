from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class RunConfig:
    """Snapshot of all parameters needed to reproduce a pipeline run."""

    audio_path: str
    audio_duration: float
    window_seconds: float
    stages: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
