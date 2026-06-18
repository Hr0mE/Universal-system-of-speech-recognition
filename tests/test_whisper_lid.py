from __future__ import annotations

"""Tests for WhisperLanguageDetector.

Unit tests use a mock WhisperModel and mock decode_audio — run offline in
milliseconds.  The integration test is guarded by the ``integration`` marker
and actually downloads the whisper-tiny model.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from core.models.base import LanguageModel
from core.models.whisper_lid import WhisperLanguageDetector
from core.pipeline.context import PipelineContext, Segment


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ctx(audio_path: Path = Path("/tmp/fake.wav")) -> PipelineContext:
    return PipelineContext(
        run_id="r1",
        audio_path=audio_path,
        run_dir=Path("/tmp/r1"),
        audio_duration=30.0,
    )


def _silent_audio(seconds: float = 30.0, sr: int = 16_000) -> np.ndarray:
    return np.zeros(int(seconds * sr), dtype=np.float32)


def _make_mock_model(language: str = "en", probability: float = 0.99) -> MagicMock:
    """Return a MagicMock that mimics WhisperModel.detect_language."""
    mock_model = MagicMock()
    mock_model.detect_language.return_value = (language, probability, [])
    return mock_model


# ---------------------------------------------------------------------------
# Class & registration tests (no model loading)
# ---------------------------------------------------------------------------


def test_whisper_lid_is_language_model():
    assert isinstance(WhisperLanguageDetector(), LanguageModel)


def test_whisper_lid_name():
    assert WhisperLanguageDetector.name == "whisper-lid"


def test_default_params():
    lid = WhisperLanguageDetector()
    assert lid.model_size == "tiny"
    assert lid.device == "cpu"
    assert lid.compute_type == "int8"


def test_custom_params():
    lid = WhisperLanguageDetector(model_size="base", device="cuda", compute_type="float16")
    assert lid.model_size == "base"
    assert lid.device == "cuda"
    assert lid.compute_type == "float16"


def test_model_not_loaded_until_detect_called():
    lid = WhisperLanguageDetector()
    assert lid._model is None


def test_whisper_lid_registered_in_default_registry():
    from core.models import default_registry

    registry = default_registry()
    assert "whisper-lid" in registry.list_language()


def test_registry_creates_whisper_lid_with_params():
    from core.models import default_registry

    registry = default_registry()
    lid = registry.create_language("whisper-lid", model_size="base")
    assert isinstance(lid, WhisperLanguageDetector)
    assert lid.model_size == "base"


# ---------------------------------------------------------------------------
# Detection unit tests (mocked WhisperModel + mocked decode_audio)
# ---------------------------------------------------------------------------


@patch("core.models.whisper_lid.WhisperLanguageDetector._get_model")
@patch("core.models.whisper_lid.WhisperLanguageDetector._get_audio")
def test_detect_returns_language_code(mock_audio, mock_model):
    mock_audio.return_value = _silent_audio(10.0)
    mock_model.return_value = _make_mock_model("ru")

    lid = WhisperLanguageDetector()
    segment = Segment(start_time=0.0, end_time=5.0)
    result = lid.detect(segment, _ctx())

    assert result == "ru"


@patch("core.models.whisper_lid.WhisperLanguageDetector._get_model")
@patch("core.models.whisper_lid.WhisperLanguageDetector._get_audio")
def test_detect_slices_correct_samples(mock_audio, mock_model):
    sr = 16_000
    full_audio = np.arange(sr * 20, dtype=np.float32)
    mock_audio.return_value = full_audio
    mock_model.return_value = _make_mock_model()

    lid = WhisperLanguageDetector()
    segment = Segment(start_time=5.0, end_time=10.0)
    lid.detect(segment, _ctx())

    call_args = mock_model.return_value.detect_language.call_args
    passed_chunk = call_args[0][0]
    assert len(passed_chunk) == 5 * sr
    np.testing.assert_array_equal(passed_chunk, full_audio[5 * sr : 10 * sr])


@patch("core.models.whisper_lid.WhisperLanguageDetector._get_model")
@patch("core.models.whisper_lid.WhisperLanguageDetector._get_audio")
def test_detect_empty_chunk_returns_en_without_calling_model(mock_audio, mock_model):
    mock_audio.return_value = _silent_audio(3.0)
    mock_model.return_value = _make_mock_model()

    lid = WhisperLanguageDetector()
    # segment beyond audio length → empty slice
    result = lid.detect(Segment(start_time=100.0, end_time=200.0), _ctx())

    assert result == "en"
    mock_model.return_value.detect_language.assert_not_called()


@patch("core.models.whisper_lid.WhisperLanguageDetector._get_model")
@patch("core.models.whisper_lid.WhisperLanguageDetector._get_audio")
def test_detect_returns_only_language_not_probability(mock_audio, mock_model):
    mock_audio.return_value = _silent_audio(10.0)
    mock_model.return_value = _make_mock_model("fr", probability=0.75)

    lid = WhisperLanguageDetector()
    result = lid.detect(Segment(start_time=0.0, end_time=5.0), _ctx())

    assert result == "fr"
    assert isinstance(result, str)


# ---------------------------------------------------------------------------
# Audio cache test (mocked decode_audio)
# ---------------------------------------------------------------------------


def test_get_audio_caches_after_first_load(tmp_path: Path):
    audio_file = tmp_path / "test.wav"
    audio_file.write_bytes(b"")

    fake_samples = np.zeros(16_000, dtype=np.float32)

    with patch(
        "core.models.whisper_utils._load_wav", return_value=fake_samples
    ) as mock_load:
        lid = WhisperLanguageDetector()
        _ = lid._get_audio(audio_file)
        _ = lid._get_audio(audio_file)

    mock_load.assert_called_once()


# ---------------------------------------------------------------------------
# Integration test — downloads tiny model (~75MB), requires network
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_real_language_detection():
    """End-to-end: load real audio, run tiny whisper LID, get a language code."""
    audio_path = (
        Path(__file__).parent.parent / "assets" / "old_shoes.wav"
    )
    if not audio_path.exists():
        pytest.skip("old_shoes.wav not found")

    lid = WhisperLanguageDetector(model_size="tiny")
    ctx = PipelineContext(
        run_id="integration",
        audio_path=audio_path,
        run_dir=Path("/tmp"),
        audio_duration=64.6,
    )
    segment = Segment(start_time=0.0, end_time=30.0)
    language = lid.detect(segment, ctx)

    assert isinstance(language, str)
    assert len(language) == 2, f"Expected 2-char BCP-47 code, got: {language!r}"
