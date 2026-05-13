from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.models import default_registry
from core.models.base import DiarizationModel
from core.models.pyannote_diarization import PyannoteDiarizationModel
from core.pipeline.context import PipelineContext, Segment
from core.pipeline.stages import DiarizationStage, FixedWindowSegmentationStage


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ctx(duration: float = 60.0) -> PipelineContext:
    return PipelineContext(
        run_id="r1",
        audio_path=Path("/tmp/fake.wav"),
        run_dir=Path("/tmp/r1"),
        audio_duration=duration,
    )


def _make_turn(start: float, end: float) -> MagicMock:
    turn = MagicMock()
    turn.start = start
    turn.end = end
    return turn


def _make_mock_pipeline(turns: list[tuple[float, float, str]]) -> MagicMock:
    """Build a mock pyannote Pipeline whose itertracks yields given turns."""
    annotation = MagicMock()
    annotation.itertracks.return_value = [
        (_make_turn(start, end), None, speaker)
        for start, end, speaker in turns
    ]
    output = MagicMock()
    output.speaker_diarization = annotation
    pipeline = MagicMock()
    pipeline.return_value = output
    return pipeline


# ---------------------------------------------------------------------------
# Class / interface tests
# ---------------------------------------------------------------------------


def test_pyannote_is_diarization_model():
    assert issubclass(PyannoteDiarizationModel, DiarizationModel)


def test_pyannote_name():
    assert PyannoteDiarizationModel.name == "pyannote"


def test_default_params():
    model = PyannoteDiarizationModel()
    assert model.model_path == "pyannote/speaker-diarization-3.1"
    assert model.hf_token is None
    assert model.device == "cpu"


def test_custom_params():
    model = PyannoteDiarizationModel(
        model_path="models/local-diar", hf_token="hf_tok", device="cuda"
    )
    assert model.model_path == "models/local-diar"
    assert model.hf_token == "hf_tok"
    assert model.device == "cuda"


# ---------------------------------------------------------------------------
# Lazy init
# ---------------------------------------------------------------------------


def test_pipeline_not_loaded_until_diarize_called():
    model = PyannoteDiarizationModel()
    assert model._pipeline is None


def test_pipeline_loaded_on_first_diarize():
    mock_pipeline = _make_mock_pipeline([])
    with patch(
        "core.models.pyannote_diarization.PyannoteDiarizationModel._get_pipeline",
        return_value=mock_pipeline,
    ):
        model = PyannoteDiarizationModel()
        model.diarize(_ctx())
    mock_pipeline.assert_called_once()


# ---------------------------------------------------------------------------
# diarize() output
# ---------------------------------------------------------------------------


def test_diarize_returns_segments_with_speaker_ids():
    turns = [(0.0, 5.0, "SPEAKER_00"), (5.0, 12.0, "SPEAKER_01")]
    mock_pipeline = _make_mock_pipeline(turns)
    with patch(
        "core.models.pyannote_diarization.PyannoteDiarizationModel._get_pipeline",
        return_value=mock_pipeline,
    ):
        model = PyannoteDiarizationModel()
        result = model.diarize(_ctx())

    assert len(result) == 2
    assert result[0] == Segment(start_time=0.0, end_time=5.0, speaker_id="SPEAKER_00")
    assert result[1] == Segment(start_time=5.0, end_time=12.0, speaker_id="SPEAKER_01")


def test_empty_diarization_returns_empty_list():
    mock_pipeline = _make_mock_pipeline([])
    with patch(
        "core.models.pyannote_diarization.PyannoteDiarizationModel._get_pipeline",
        return_value=mock_pipeline,
    ):
        model = PyannoteDiarizationModel()
        result = model.diarize(_ctx())
    assert result == []


# ---------------------------------------------------------------------------
# HF token resolution
# ---------------------------------------------------------------------------


def test_hf_token_from_env_var(monkeypatch):
    monkeypatch.setenv("HF_TOKEN", "hf_from_env")
    monkeypatch.delenv("HF_TOKEN", raising=False)
    monkeypatch.setenv("HF_TOKEN", "hf_from_env")

    mock_torch = MagicMock()
    mock_pipeline_cls = MagicMock()
    mock_pipeline_instance = MagicMock()
    mock_pipeline_cls.from_pretrained.return_value = mock_pipeline_instance
    mock_pipeline_instance.to.return_value = mock_pipeline_instance

    with patch.dict("sys.modules", {"torch": mock_torch, "pyannote.audio": MagicMock()}):
        with patch(
            "core.models.pyannote_diarization.PyannoteDiarizationModel._get_pipeline"
        ) as mock_get:
            mock_get.return_value = _make_mock_pipeline([])
            model = PyannoteDiarizationModel(hf_token="hf_from_config")
            # Directly test _get_pipeline token selection via os.environ mock
            import os
            original = os.environ.get("HF_TOKEN")

    # Test the token precedence logic directly
    model = PyannoteDiarizationModel(hf_token="hf_from_config")
    with patch.dict("os.environ", {"HF_TOKEN": "hf_from_env"}):
        with patch("torch.device"):
            with patch("pyannote.audio.Pipeline") as MockPipeline:
                mock_inst = MagicMock()
                mock_inst.to.return_value = mock_inst
                MockPipeline.from_pretrained.return_value = mock_inst
                model._get_pipeline()
        MockPipeline.from_pretrained.assert_called_once_with(
            model.model_path, token="hf_from_env"
        )


def test_hf_token_from_constructor_when_no_env(monkeypatch):
    monkeypatch.delenv("HF_TOKEN", raising=False)
    model = PyannoteDiarizationModel(hf_token="hf_from_config")
    with patch("torch.device"):
        with patch("pyannote.audio.Pipeline") as MockPipeline:
            mock_inst = MagicMock()
            mock_inst.to.return_value = mock_inst
            MockPipeline.from_pretrained.return_value = mock_inst
            model._get_pipeline()
    MockPipeline.from_pretrained.assert_called_once_with(
        model.model_path, token="hf_from_config"
    )


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


def test_pyannote_registered_in_default_registry():
    registry = default_registry()
    assert "pyannote" in registry.list_diarization()


def test_registry_creates_pyannote_with_params():
    registry = default_registry()
    model = registry.create_diarization(
        "pyannote", model_path="models/local", device="cpu"
    )
    assert isinstance(model, PyannoteDiarizationModel)
    assert model.model_path == "models/local"


# ---------------------------------------------------------------------------
# build_stages() integration
# ---------------------------------------------------------------------------


def test_build_stages_uses_diarization_stage_when_configured():
    from core.config.models_config import ModelsConfig
    from main import build_stages

    cfg = ModelsConfig.from_dict(
        {
            "asr": "dummy",
            "language_detection": "dummy",
            "diarization": "dummy",
        }
    )
    registry = default_registry()
    stages = build_stages(30.0, cfg, registry)
    assert isinstance(stages[0], DiarizationStage)


def test_build_stages_uses_segmentation_when_no_diarization():
    from core.config.models_config import ModelsConfig
    from main import build_stages

    cfg = ModelsConfig.from_dict({"asr": "dummy", "language_detection": "dummy"})
    registry = default_registry()
    stages = build_stages(30.0, cfg, registry)
    assert isinstance(stages[0], FixedWindowSegmentationStage)


# ---------------------------------------------------------------------------
# Integration test
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_integration_diarization(tmp_path: Path):
    """Real pyannote pipeline on a short WAV file. Needs HF_TOKEN env var."""
    import os

    audio = Path("old_shoes.wav")
    if not audio.exists():
        pytest.skip("old_shoes.wav not found")
    token = os.environ.get("HF_TOKEN")
    if not token:
        pytest.skip("HF_TOKEN not set")

    model = PyannoteDiarizationModel(device="cpu")
    ctx = PipelineContext(
        run_id="test",
        audio_path=audio,
        run_dir=tmp_path,
        audio_duration=0.0,
    )
    result = model.diarize(ctx)
    assert isinstance(result, list)
    assert all(isinstance(s, Segment) for s in result)
    assert all(s.speaker_id is not None for s in result)
