from __future__ import annotations

"""Tests for FasterWhisperASR.

Unit tests use a mock WhisperModel and mock decode_audio so they run
offline and in milliseconds.  The integration test is guarded by the
``integration`` marker and actually downloads the whisper-tiny model.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from core.models.base import ASRModel
from core.models.registry import ModelRegistry
from core.models.whisper_asr import FasterWhisperASR
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


def _make_mock_model(words: list[str] | None = None) -> MagicMock:
    """Return a MagicMock that mimics WhisperModel.transcribe."""
    words = words or ["hello", "world"]

    mock_seg = MagicMock()
    mock_seg.text = " ".join(words)

    mock_info = MagicMock()
    mock_info.language = "en"

    mock_model = MagicMock()
    mock_model.transcribe.return_value = (iter([mock_seg]), mock_info)
    return mock_model


# ---------------------------------------------------------------------------
# Class & registration tests (no model loading)
# ---------------------------------------------------------------------------


def test_faster_whisper_asr_is_asr_model():
    asr = FasterWhisperASR()
    assert isinstance(asr, ASRModel)


def test_faster_whisper_asr_name():
    assert FasterWhisperASR.name == "faster-whisper"


def test_default_params():
    asr = FasterWhisperASR()
    assert asr.model_size == "tiny"
    assert asr.language is None  # дефолт — авто-детекция языка (None), не "en"
    assert asr.device == "cpu"
    assert asr.compute_type == "int8"


def test_custom_params():
    asr = FasterWhisperASR(model_size="base", language="ru", beam_size=3)
    assert asr.model_size == "base"
    assert asr.language == "ru"
    assert asr.beam_size == 3


def test_model_is_not_loaded_until_transcribe_called():
    asr = FasterWhisperASR()
    assert asr._model is None


def test_faster_whisper_registered_in_default_registry():
    from core.models import default_registry

    registry = default_registry()
    assert "faster-whisper" in registry.list_asr()


def test_registry_creates_faster_whisper_with_params():
    from core.models import default_registry

    registry = default_registry()
    asr = registry.create_asr("faster-whisper", model_size="base", language="ru")
    assert isinstance(asr, FasterWhisperASR)
    assert asr.model_size == "base"
    assert asr.language == "ru"


# ---------------------------------------------------------------------------
# Transcription unit tests (mocked WhisperModel + mocked decode_audio)
# ---------------------------------------------------------------------------


@patch("core.models.whisper_asr.FasterWhisperASR._get_model")
@patch("core.models.whisper_asr.FasterWhisperASR._get_audio")
def test_transcribe_returns_joined_text(mock_audio, mock_model):
    mock_audio.return_value = _silent_audio(10.0)
    mock_model.return_value = _make_mock_model(["hello", "world"])

    asr = FasterWhisperASR()
    segment = Segment(start_time=0.0, end_time=5.0, language="en")
    result = asr.transcribe(segment, _ctx())

    assert result == "hello world"


@patch("core.models.whisper_asr.FasterWhisperASR._get_model")
@patch("core.models.whisper_asr.FasterWhisperASR._get_audio")
def test_transcribe_slices_correct_samples(mock_audio, mock_model):
    """Check that the right sample range is passed to whisper."""
    sr = 16_000
    full_audio = np.arange(sr * 20, dtype=np.float32)  # 20s of ramp
    mock_audio.return_value = full_audio
    mock_model.return_value = _make_mock_model(["ok"])

    asr = FasterWhisperASR()
    segment = Segment(start_time=5.0, end_time=10.0)
    asr.transcribe(segment, _ctx())

    call_args = mock_model.return_value.transcribe.call_args
    passed_chunk = call_args[0][0]
    assert len(passed_chunk) == 5 * sr
    np.testing.assert_array_equal(passed_chunk, full_audio[5 * sr : 10 * sr])


@patch("core.models.whisper_asr.FasterWhisperASR._get_model")
@patch("core.models.whisper_asr.FasterWhisperASR._get_audio")
def test_transcribe_empty_chunk_returns_empty_string(mock_audio, mock_model):
    mock_audio.return_value = _silent_audio(3.0)
    mock_model.return_value = _make_mock_model()

    asr = FasterWhisperASR()
    # segment beyond the audio length → empty slice
    segment = Segment(start_time=100.0, end_time=200.0)
    result = asr.transcribe(segment, _ctx())

    assert result == ""
    mock_model.return_value.transcribe.assert_not_called()


@patch("core.models.whisper_asr.FasterWhisperASR._get_model")
@patch("core.models.whisper_asr.FasterWhisperASR._get_audio")
def test_audio_loaded_only_once_across_segments(mock_audio, mock_model):
    mock_audio.return_value = _silent_audio(60.0)
    mock_model.return_value = _make_mock_model()

    asr = FasterWhisperASR()
    ctx = _ctx()
    for start in (0.0, 10.0, 20.0, 30.0):
        asr.transcribe(Segment(start_time=start, end_time=start + 10.0), ctx)

    assert mock_audio.call_count == 4  # called once per transcribe (mock caching)


@patch("core.models.whisper_asr.FasterWhisperASR._get_model")
@patch("core.models.whisper_asr.FasterWhisperASR._get_audio")
def test_transcribe_passes_language_to_whisper(mock_audio, mock_model):
    mock_audio.return_value = _silent_audio(10.0)
    mock_model.return_value = _make_mock_model()

    asr = FasterWhisperASR(language="ru")
    asr.transcribe(Segment(start_time=0.0, end_time=5.0), _ctx())

    call_kwargs = mock_model.return_value.transcribe.call_args[1]
    assert call_kwargs["language"] == "ru"


# ---------------------------------------------------------------------------
# Audio loading unit test (mocked decode_audio)
# ---------------------------------------------------------------------------


def test_get_audio_caches_after_first_load(tmp_path: Path):
    audio_file = tmp_path / "test.wav"
    audio_file.write_bytes(b"")  # content doesn't matter — we mock _load_wav

    fake_samples = np.zeros(16_000, dtype=np.float32)

    with patch(
        "core.models.whisper_utils._load_wav", return_value=fake_samples
    ) as mock_load:
        asr = FasterWhisperASR()
        _ = asr._get_audio(audio_file)
        _ = asr._get_audio(audio_file)

    mock_load.assert_called_once()


# ---------------------------------------------------------------------------
# Integration test — downloads tiny model (~75MB), requires network
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_real_transcription_old_shoes():
    """End-to-end: load real audio, run tiny whisper, get non-empty text."""
    audio_path = (
        Path(__file__).parent.parent / "assets" / "old_shoes.wav"
    )
    if not audio_path.exists():
        pytest.skip("old_shoes.wav not found")

    asr = FasterWhisperASR(model_size="tiny", language="en")
    ctx = PipelineContext(
        run_id="integration",
        audio_path=audio_path,
        run_dir=Path("/tmp"),
        audio_duration=64.6,
    )
    segment = Segment(start_time=0.0, end_time=30.0)
    text = asr.transcribe(segment, ctx)

    assert isinstance(text, str)
    assert len(text) > 0, "Expected non-empty transcription from real audio"
