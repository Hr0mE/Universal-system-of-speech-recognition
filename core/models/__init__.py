from __future__ import annotations

from core.models.dummy import DummyASR, DummyDiarization, DummyLanguageModel
from core.models.registry import ModelRegistry


def _make_faster_whisper(**kwargs):
    """Lazy factory — imports faster_whisper only when requested."""
    from core.models.whisper_asr import FasterWhisperASR

    return FasterWhisperASR(**kwargs)


def _make_whisper_lid(**kwargs):
    """Lazy factory — imports faster_whisper only when requested."""
    from core.models.whisper_lid import WhisperLanguageDetector

    return WhisperLanguageDetector(**kwargs)


def _make_pyannote(**kwargs):
    """Lazy factory — imports pyannote.audio only when requested."""
    from core.models.pyannote_diarization import PyannoteDiarizationModel

    return PyannoteDiarizationModel(**kwargs)


def default_registry() -> ModelRegistry:
    """Registry pre-populated with dummy models and faster-whisper."""
    registry = ModelRegistry()
    registry.register_asr("dummy", DummyASR)
    registry.register_language("dummy", DummyLanguageModel)
    registry.register_diarization("dummy", DummyDiarization)
    registry.register_asr("faster-whisper", _make_faster_whisper)
    registry.register_language("whisper-lid", _make_whisper_lid)
    registry.register_diarization("pyannote", _make_pyannote)
    return registry


__all__ = ["ModelRegistry", "default_registry"]
