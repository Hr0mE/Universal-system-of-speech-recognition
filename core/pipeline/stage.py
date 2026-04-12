from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.pipeline.context import PipelineContext, Segment


class Stage(ABC):
    name: str

    @abstractmethod
    def run(
        self,
        segments: list["Segment"],
        context: "PipelineContext",
    ) -> list["Segment"]:
        ...
