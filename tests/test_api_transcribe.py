from __future__ import annotations

import struct
import wave
from pathlib import Path
from unittest.mock import patch

import pytest

from core.api.transcribe import TranscriptionResult, transcribe
from core.models.dummy import DummyASR, DummyLanguageModel
from core.models.registry import ModelRegistry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_dummy_registry() -> ModelRegistry:
    registry = ModelRegistry()
    registry.register_asr("faster-whisper", lambda **kw: DummyASR())
    registry.register_language("whisper-lid", lambda **kw: DummyLanguageModel())
    return registry


@pytest.fixture
def wav_file(tmp_path: Path) -> Path:
    path = tmp_path / "test.wav"
    n_frames = 16000  # 1 second at 16 kHz
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(b"\x00\x00" * n_frames)
    return path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_transcribe_returns_transcription_result(wav_file: Path, tmp_path: Path) -> None:
    with patch("core.api.transcribe.default_registry", return_value=_make_dummy_registry()), \
         patch("core.api.transcribe.setup_plugins"):
        result = transcribe(wav_file, runs_dir=tmp_path / "runs")
    assert isinstance(result, TranscriptionResult)
    assert len(result.segments) > 0
    assert result.run_dir.exists()


def test_transcribe_raises_for_missing_audio(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="Audio file not found"):
        transcribe(tmp_path / "nonexistent.wav", runs_dir=tmp_path / "runs")


def test_transcribe_raises_for_non_wav(tmp_path: Path) -> None:
    mp3 = tmp_path / "audio.mp3"
    mp3.write_bytes(b"fake")
    with pytest.raises(ValueError, match="Only .wav is supported"):
        transcribe(mp3, runs_dir=tmp_path / "runs")


def test_transcribe_uses_default_config_when_none(wav_file: Path, tmp_path: Path) -> None:
    with patch("core.api.transcribe.default_registry", return_value=_make_dummy_registry()), \
         patch("core.api.transcribe.setup_plugins"):
        result = transcribe(wav_file, models_config=None, runs_dir=tmp_path / "runs")
    assert isinstance(result, TranscriptionResult)


def test_transcribe_creates_run_dir(wav_file: Path, tmp_path: Path) -> None:
    with patch("core.api.transcribe.default_registry", return_value=_make_dummy_registry()), \
         patch("core.api.transcribe.setup_plugins"):
        result = transcribe(wav_file, runs_dir=tmp_path / "runs")
    assert result.run_dir.exists()
    assert result.run_dir.is_dir()


def test_transcribe_result_has_correct_run_id_format(wav_file: Path, tmp_path: Path) -> None:
    with patch("core.api.transcribe.default_registry", return_value=_make_dummy_registry()), \
         patch("core.api.transcribe.setup_plugins"):
        result = transcribe(wav_file, runs_dir=tmp_path / "runs")
    assert result.run_id.startswith("run_")


def test_transcribe_raises_type_error_for_invalid_models_config(wav_file: Path, tmp_path: Path) -> None:
    from core.config.models_config import DEFAULT_MODELS_CONFIG
    with pytest.raises(TypeError):
        transcribe(wav_file, models_config=DEFAULT_MODELS_CONFIG, runs_dir=tmp_path / "runs")
