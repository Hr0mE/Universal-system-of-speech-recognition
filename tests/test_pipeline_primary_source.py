"""Spec: Pipeline as the sole model data source.

Verifies that transcribe() and resume_transcription() use PipelineConfig as the
only data source for model configuration. ModelsConfig / YAML-path / SettingsDialog
paths are removed.
"""

from __future__ import annotations

import json
import wave
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from core.api.transcribe import TranscriptionResult, resume_transcription, transcribe
from core.config.pipeline_config import PipelineConfig, default_pipeline_config


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def wav_file(tmp_path: Path) -> Path:
    path = tmp_path / "test.wav"
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(b"\x00\x00" * 16000)
    return path


@pytest.fixture
def resume_run_dir(tmp_path: Path) -> Path:
    """Minimal run directory that resume_transcription() can parse."""
    run_dir = tmp_path / "runs" / "run_resume_test"
    run_dir.mkdir(parents=True)
    config_data = {
        "audio_path": str(tmp_path / "fake_audio.wav"),
        "audio_duration": 1.0,
        "window_seconds": 30.0,
        "stages": [],
        "models": {},
    }
    (run_dir / "config.yaml").write_text(
        yaml.safe_dump(config_data, allow_unicode=True), encoding="utf-8"
    )
    state_data = {
        "run_id": "run_resume_test",
        "status": "stopped",
        "last_stage_index": 0,
        "completed_stages": [],
    }
    (run_dir / "state.json").write_text(json.dumps(state_data), encoding="utf-8")
    return run_dir


def _engine_patch():
    """Context manager that patches PipelineEngine so it returns []."""
    mock = MagicMock()
    mock.return_value.run.return_value = []
    return patch("core.api.transcribe.PipelineEngine", mock)


# ---------------------------------------------------------------------------
# AC-1: transcribe(audio, None) calls build_stages_from_pipeline
# ---------------------------------------------------------------------------

def test_AC1_transcribe_none_calls_build_stages_from_pipeline(wav_file: Path, tmp_path: Path) -> None:
    """AC-1: models_config=None must route through build_stages_from_pipeline,
    not through the legacy ModelsConfig/build_stages path."""
    captured: dict = {}

    def fake_bsfp(pipeline_cfg, registry):
        captured["pipeline_cfg"] = pipeline_cfg
        return []

    with patch("core.api.transcribe.build_stages_from_pipeline", side_effect=fake_bsfp), \
         patch("core.api.transcribe.default_registry", return_value=MagicMock()), \
         patch("core.api.transcribe.setup_plugins"), \
         _engine_patch():
        transcribe(wav_file, models_config=None, runs_dir=tmp_path / "runs")

    assert "pipeline_cfg" in captured, (
        "build_stages_from_pipeline was not called — "
        "transcribe(None) still uses the ModelsConfig path"
    )
    assert isinstance(captured["pipeline_cfg"], PipelineConfig)


# ---------------------------------------------------------------------------
# AC-2: transcribe(audio, pipeline_cfg) calls build_stages_from_pipeline
# ---------------------------------------------------------------------------

def test_AC2_transcribe_pipeline_config_calls_build_stages_from_pipeline(wav_file: Path, tmp_path: Path) -> None:
    """AC-2: Explicit PipelineConfig must be forwarded to build_stages_from_pipeline."""
    pipeline_cfg = default_pipeline_config()
    captured: dict = {}

    def fake_bsfp(cfg, registry):
        captured["pipeline_cfg"] = cfg
        return []

    with patch("core.api.transcribe.build_stages_from_pipeline", side_effect=fake_bsfp), \
         patch("core.api.transcribe.default_registry", return_value=MagicMock()), \
         patch("core.api.transcribe.setup_plugins"), \
         _engine_patch():
        transcribe(wav_file, models_config=pipeline_cfg, runs_dir=tmp_path / "runs")

    assert captured.get("pipeline_cfg") is pipeline_cfg


# ---------------------------------------------------------------------------
# AC-3: resume_transcription(run_dir, None) calls build_stages_from_pipeline
# ---------------------------------------------------------------------------

def test_AC3_resume_none_calls_build_stages_from_pipeline(resume_run_dir: Path) -> None:
    """AC-3: resume_transcription(run_dir, None) must use default_pipeline_config(),
    not the legacy ModelsConfig path."""
    captured: dict = {}

    def fake_bsfp(pipeline_cfg, registry):
        captured["pipeline_cfg"] = pipeline_cfg
        return []

    with patch("core.api.transcribe.build_stages_from_pipeline", side_effect=fake_bsfp), \
         patch("core.api.transcribe.default_registry", return_value=MagicMock()), \
         patch("core.api.transcribe.setup_plugins"), \
         _engine_patch():
        resume_transcription(resume_run_dir, models_config=None)

    assert "pipeline_cfg" in captured, (
        "build_stages_from_pipeline was not called — "
        "resume_transcription(None) still uses the ModelsConfig path"
    )
    assert isinstance(captured["pipeline_cfg"], PipelineConfig)


# ---------------------------------------------------------------------------
# AC-4: resume_transcription(run_dir, pipeline_cfg) calls build_stages_from_pipeline
# ---------------------------------------------------------------------------

def test_AC4_resume_pipeline_config_calls_build_stages_from_pipeline(resume_run_dir: Path) -> None:
    """AC-4: Explicit PipelineConfig forwarded to build_stages_from_pipeline in resume."""
    pipeline_cfg = default_pipeline_config()
    captured: dict = {}

    def fake_bsfp(cfg, registry):
        captured["pipeline_cfg"] = cfg
        return []

    with patch("core.api.transcribe.build_stages_from_pipeline", side_effect=fake_bsfp), \
         patch("core.api.transcribe.default_registry", return_value=MagicMock()), \
         patch("core.api.transcribe.setup_plugins"), \
         _engine_patch():
        resume_transcription(resume_run_dir, models_config=pipeline_cfg)

    assert captured.get("pipeline_cfg") is pipeline_cfg


# ---------------------------------------------------------------------------
# AC-5: transcribe() with non-PipelineConfig / non-None raises TypeError
# ---------------------------------------------------------------------------

def test_AC5_transcribe_rejects_models_config_object(wav_file: Path, tmp_path: Path) -> None:
    """AC-5: Passing a ModelsConfig object to transcribe() must raise TypeError."""
    from core.config.models_config import DEFAULT_MODELS_CONFIG

    with pytest.raises(TypeError):
        transcribe(wav_file, models_config=DEFAULT_MODELS_CONFIG, runs_dir=tmp_path / "runs")


def test_AC5_transcribe_rejects_arbitrary_non_pipeline_object(wav_file: Path, tmp_path: Path) -> None:
    """AC-5: Passing any non-PipelineConfig non-None value raises TypeError."""
    with pytest.raises(TypeError):
        transcribe(wav_file, models_config={"asr": "dummy"}, runs_dir=tmp_path / "runs")


# ---------------------------------------------------------------------------
# AC-6: resume_transcription() with non-PipelineConfig / non-None raises TypeError
# ---------------------------------------------------------------------------

def test_AC6_resume_rejects_models_config_object(resume_run_dir: Path) -> None:
    """AC-6: Passing a ModelsConfig object to resume_transcription() must raise TypeError."""
    from core.config.models_config import DEFAULT_MODELS_CONFIG

    with pytest.raises(TypeError):
        resume_transcription(resume_run_dir, models_config=DEFAULT_MODELS_CONFIG)


def test_AC6_resume_rejects_arbitrary_non_pipeline_object(resume_run_dir: Path) -> None:
    """AC-6: Passing any non-PipelineConfig non-None value raises TypeError."""
    with pytest.raises(TypeError):
        resume_transcription(resume_run_dir, models_config={"asr": "dummy"})


# ---------------------------------------------------------------------------
# EC-1: transcribe(audio, None) produces the same config as default_pipeline_config()
# ---------------------------------------------------------------------------

def test_EC1_transcribe_none_equals_default_pipeline_config(wav_file: Path, tmp_path: Path) -> None:
    """EC-1: transcribe(audio, None) must pass default_pipeline_config() to the
    stage builder — same result as an explicit default_pipeline_config() call."""
    captured_cfgs: list[PipelineConfig] = []

    def fake_bsfp(cfg, registry):
        captured_cfgs.append(cfg)
        return []

    default_cfg = default_pipeline_config()

    with patch("core.api.transcribe.build_stages_from_pipeline", side_effect=fake_bsfp), \
         patch("core.api.transcribe.default_registry", return_value=MagicMock()), \
         patch("core.api.transcribe.setup_plugins"), \
         _engine_patch():
        transcribe(wav_file, models_config=None, runs_dir=tmp_path / "runs1")
        transcribe(wav_file, models_config=default_cfg, runs_dir=tmp_path / "runs2")

    assert len(captured_cfgs) == 2, (
        "Expected build_stages_from_pipeline to be called for both None and explicit config; "
        f"got {len(captured_cfgs)} call(s)"
    )
    assert captured_cfgs[0].to_dict() == captured_cfgs[1].to_dict(), (
        "transcribe(None) used a different PipelineConfig than default_pipeline_config()"
    )


# ---------------------------------------------------------------------------
# EC-2: Empty PipelineConfig produces no stages
# ---------------------------------------------------------------------------

def test_EC2_empty_pipeline_config_produces_no_stages(wav_file: Path, tmp_path: Path) -> None:
    """EC-2: PipelineConfig([]) must not raise — it simply produces zero stages."""
    empty_cfg = PipelineConfig(stages=[])
    captured: dict = {}

    def fake_bsfp(cfg, registry):
        captured["pipeline_cfg"] = cfg
        return []

    with patch("core.api.transcribe.build_stages_from_pipeline", side_effect=fake_bsfp), \
         patch("core.api.transcribe.default_registry", return_value=MagicMock()), \
         patch("core.api.transcribe.setup_plugins"), \
         _engine_patch():
        transcribe(wav_file, models_config=empty_cfg, runs_dir=tmp_path / "runs")

    assert captured.get("pipeline_cfg") is empty_cfg


# ---------------------------------------------------------------------------
# ERR-1: Missing audio file still raises FileNotFoundError
# ---------------------------------------------------------------------------

def test_ERR1_transcribe_raises_for_missing_audio(tmp_path: Path) -> None:
    """ERR-1: FileNotFoundError is raised before stage building for a missing audio file."""
    with pytest.raises(FileNotFoundError, match="Audio file not found"):
        transcribe(tmp_path / "nonexistent.wav", runs_dir=tmp_path / "runs")
