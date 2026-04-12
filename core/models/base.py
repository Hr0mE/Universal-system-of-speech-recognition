from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.pipeline.context import PipelineContext, Segment


class ASRModel(ABC):
    """Turns a single audio segment into transcribed text."""

    name: str

    @abstractmethod
    def transcribe(
        self,
        segment: "Segment",
        context: "PipelineContext",
    ) -> str:
        ...


class LanguageModel(ABC):
    """Predicts the spoken language code (e.g. 'en', 'ru') for a segment."""

    name: str

    @abstractmethod
    def detect(
        self,
        segment: "Segment",
        context: "PipelineContext",
    ) -> str:
        ...


class DiarizationModel(ABC):
    """Produces speaker-labelled segment boundaries for the whole recording."""

    name: str

    @abstractmethod
    def diarize(self, context: "PipelineContext") -> list["Segment"]:
        ...
