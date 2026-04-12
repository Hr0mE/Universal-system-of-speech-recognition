from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Segment:
    start_time: float
    end_time: float
    speaker_id: str | None = None
    language: str | None = None
    text: str | None = None

    @property
    def duration(self) -> float:
        return self.end_time - self.start_time

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PipelineContext:
    run_id: str
    audio_path: Path
    run_dir: Path
    audio_duration: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
