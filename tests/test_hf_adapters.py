from __future__ import annotations

"""Failing tests for HF Transformers backend adapters and related events.

These tests are written BEFORE the feature is implemented, so they all FAIL
on the current codebase.  They cover:
  AC-1..AC-7, EC-1, EC-2, ERR-1, ERR-2
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from core.models.base import ASRModel, LanguageModel
from core.models.transformers_asr import TransformersASR
from core.models.transformers_lid import TransformersLID
from core.pipeline.context import PipelineContext, Segment
from core.models.registry import ModelRegistry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ctx() -> PipelineContext:
    return PipelineContext(
        run_id="r1",
        audio_path=Path("/tmp/fake.wav"),
        run_dir=Path("/tmp/r1"),
        audio_duration=30.0,
    )


def _segment(start: float = 0.0, end: float = 5.0) -> Segment:
    return Segment(start_time=start, end_time=end)


# ---------------------------------------------------------------------------
# AC-1: TransformersASR interface & lazy loading
# ---------------------------------------------------------------------------


def test_ac1_transformers_asr_is_asr_model():
    asr = TransformersASR(repo_id="some/model")
    assert isinstance(asr, ASRModel)


def test_ac1_transformers_asr_name():
    assert TransformersASR.name == "transformers-asr"


def test_ac1_transformers_asr_pipeline_none_after_init():
    asr = TransformersASR(repo_id="some/model")
    assert asr._pipeline is None


# ---------------------------------------------------------------------------
# AC-2: TransformersASR.transcribe returns str and calls pipeline
# ---------------------------------------------------------------------------


def test_ac2_transcribe_returns_str():
    mock_pipeline = MagicMock(return_value={"text": "hello world"})
    with patch.object(TransformersASR, "_get_pipeline", return_value=mock_pipeline):
        asr = TransformersASR(repo_id="some/model")
        result = asr.transcribe(_segment(), _ctx())
    assert isinstance(result, str)
    assert result == "hello world"


def test_ac2_transcribe_calls_pipeline_with_numpy():
    mock_pipeline = MagicMock(return_value={"text": "ok"})
    with patch.object(TransformersASR, "_get_pipeline", return_value=mock_pipeline):
        asr = TransformersASR(repo_id="some/model")
        asr.transcribe(_segment(0.0, 1.0), _ctx())
    call_args = mock_pipeline.call_args
    # First positional arg must be a numpy array
    passed = call_args[0][0] if call_args[0] else call_args[1].get("inputs")
    assert isinstance(passed, np.ndarray)


# ---------------------------------------------------------------------------
# AC-3: TransformersLID interface & lazy loading
# ---------------------------------------------------------------------------


def test_ac3_transformers_lid_is_language_model():
    lid = TransformersLID(repo_id="some/model")
    assert isinstance(lid, LanguageModel)


def test_ac3_transformers_lid_name():
    assert TransformersLID.name == "transformers-lid"


def test_ac3_transformers_lid_pipeline_none_after_init():
    lid = TransformersLID(repo_id="some/model")
    assert lid._pipeline is None


# ---------------------------------------------------------------------------
# AC-4: TransformersLID.detect returns language code str
# ---------------------------------------------------------------------------


def test_ac4_detect_returns_language_code():
    mock_pipeline = MagicMock(return_value=[{"label": "ru", "score": 0.99}])
    with patch.object(TransformersLID, "_get_pipeline", return_value=mock_pipeline):
        lid = TransformersLID(repo_id="some/model")
        result = lid.detect(_segment(), _ctx())
    assert isinstance(result, str)
    assert result == "ru"


# ---------------------------------------------------------------------------
# AC-5: transformers_asr plugin registers "transformers-asr"
# ---------------------------------------------------------------------------


def test_ac5_plugin_registers_transformers_asr():
    from plugins.transformers_asr import register

    model_registry = ModelRegistry()
    stage_registry = MagicMock()
    register(model_registry, stage_registry)
    assert "transformers-asr" in model_registry.list_asr()


# ---------------------------------------------------------------------------
# AC-6: transformers_lid plugin registers "transformers-lid"
# ---------------------------------------------------------------------------


def test_ac6_plugin_registers_transformers_lid():
    from plugins.transformers_lid import register

    model_registry = ModelRegistry()
    stage_registry = MagicMock()
    register(model_registry, stage_registry)
    assert "transformers-lid" in model_registry.list_language()


# ---------------------------------------------------------------------------
# AC-7: HFDownloadProgress event exists as frozen dataclass
# ---------------------------------------------------------------------------


def test_ac7_hf_download_progress_event_exists():
    from core.events.events import HFDownloadProgress, PipelineEvent

    evt = HFDownloadProgress(
        run_id="r1",
        repo_id="some/model",
        downloaded_bytes=1024,
        total_bytes=4096,
    )
    assert isinstance(evt, PipelineEvent)
    assert evt.run_id == "r1"
    assert evt.repo_id == "some/model"
    assert evt.downloaded_bytes == 1024
    assert evt.total_bytes == 4096


def test_ac7_hf_download_started_and_finished_exist():
    from core.events.events import HFDownloadFinished, HFDownloadStarted, PipelineEvent

    started = HFDownloadStarted(run_id="r1", repo_id="some/model")
    finished = HFDownloadFinished(run_id="r1", repo_id="some/model")
    assert isinstance(started, PipelineEvent)
    assert isinstance(finished, PipelineEvent)
    assert started.repo_id == "some/model"
    assert finished.repo_id == "some/model"


def test_ac7_hf_download_progress_is_frozen():
    from core.events.events import HFDownloadProgress

    evt = HFDownloadProgress(
        run_id="r1", repo_id="some/model", downloaded_bytes=0, total_bytes=100
    )
    with pytest.raises((AttributeError, TypeError)):
        evt.downloaded_bytes = 999  # type: ignore[misc]


# ---------------------------------------------------------------------------
# EC-1: zero-duration segment returns ""
# ---------------------------------------------------------------------------


def test_ec1_zero_duration_returns_empty_string():
    mock_pipeline = MagicMock(return_value={"text": "should not be called"})
    with patch.object(TransformersASR, "_get_pipeline", return_value=mock_pipeline):
        asr = TransformersASR(repo_id="some/model")
        result = asr.transcribe(Segment(start_time=5.0, end_time=5.0), _ctx())
    assert result == ""
    mock_pipeline.assert_not_called()


# ---------------------------------------------------------------------------
# EC-2: builtin manifests model_size is "string" not "enum"
# ---------------------------------------------------------------------------


def test_ec2_faster_whisper_model_size_type_is_string():
    from plugins.builtin_manifests import BUILTIN_MANIFESTS

    fw = next(m for m in BUILTIN_MANIFESTS if m.name == "faster-whisper")
    assert fw.params_schema["model_size"].type == "string"


def test_ec2_whisper_lid_model_size_type_is_string():
    from plugins.builtin_manifests import BUILTIN_MANIFESTS

    lid = next(m for m in BUILTIN_MANIFESTS if m.name == "whisper-lid")
    assert lid.params_schema["model_size"].type == "string"


# ---------------------------------------------------------------------------
# ERR-1: TransformersASR empty repo_id raises ValueError
# ---------------------------------------------------------------------------


def test_err1_transformers_asr_empty_repo_id_raises():
    with pytest.raises(ValueError):
        TransformersASR(repo_id="")


# ---------------------------------------------------------------------------
# ERR-2: TransformersLID empty repo_id raises ValueError
# ---------------------------------------------------------------------------


def test_err2_transformers_lid_empty_repo_id_raises():
    with pytest.raises(ValueError):
        TransformersLID(repo_id="")
