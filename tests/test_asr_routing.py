from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from core.config.models_config import ModelSpec, ModelsConfig
from core.models import default_registry
from core.models.base import ASRModel
from core.pipeline.context import PipelineContext, Segment
from core.pipeline.stages import ASRStage


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ctx() -> PipelineContext:
    return PipelineContext(
        run_id="r1",
        audio_path=Path("/tmp/fake.wav"),
        run_dir=Path("/tmp/r1"),
        audio_duration=60.0,
    )


def _seg(language: str | None = None) -> Segment:
    return Segment(start_time=0.0, end_time=5.0, language=language)


def _mock_asr(label: str) -> ASRModel:
    """Return a mock ASRModel whose transcribe returns its label."""
    m = MagicMock(spec=ASRModel)
    m.transcribe.return_value = label
    return m


# ---------------------------------------------------------------------------
# ASRStage dispatch tests
# ---------------------------------------------------------------------------


def test_no_lang_models_always_uses_default():
    default = _mock_asr("default")
    stage = ASRStage(model=default)
    result = stage.run([_seg("en"), _seg("ru"), _seg(None)], _ctx())
    assert [s.text for s in result] == ["default", "default", "default"]
    assert default.transcribe.call_count == 3


def test_known_language_uses_lang_model():
    default = _mock_asr("default")
    en_model = _mock_asr("en-text")
    stage = ASRStage(model=default, lang_models={"en": en_model})
    result = stage.run([_seg("en")], _ctx())
    assert result[0].text == "en-text"
    en_model.transcribe.assert_called_once()
    default.transcribe.assert_not_called()


def test_unknown_language_falls_back_to_default():
    default = _mock_asr("default")
    stage = ASRStage(model=default, lang_models={"en": _mock_asr("en-text")})
    result = stage.run([_seg("fr")], _ctx())
    assert result[0].text == "default"
    default.transcribe.assert_called_once()


def test_none_language_falls_back_to_default():
    default = _mock_asr("default")
    stage = ASRStage(model=default, lang_models={"en": _mock_asr("en-text")})
    result = stage.run([_seg(None)], _ctx())
    assert result[0].text == "default"
    default.transcribe.assert_called_once()


def test_multiple_segments_dispatch_correctly():
    default = _mock_asr("default")
    en_model = _mock_asr("en-text")
    ru_model = _mock_asr("ru-text")
    stage = ASRStage(
        model=default, lang_models={"en": en_model, "ru": ru_model}
    )
    segments = [_seg("en"), _seg("ru"), _seg("fr"), _seg(None)]
    result = stage.run(segments, _ctx())
    assert result[0].text == "en-text"
    assert result[1].text == "ru-text"
    assert result[2].text == "default"
    assert result[3].text == "default"
    en_model.transcribe.assert_called_once()
    ru_model.transcribe.assert_called_once()
    assert default.transcribe.call_count == 2


# ---------------------------------------------------------------------------
# ModelsConfig.asr_per_language parsing
# ---------------------------------------------------------------------------


def test_models_config_asr_per_language_parsed():
    cfg = ModelsConfig.from_dict(
        {
            "asr": "dummy",
            "language_detection": "dummy",
            "asr_per_language": {
                "en": {"name": "faster-whisper", "params": {"language": "en"}},
                "ru": {"name": "faster-whisper", "params": {"language": "ru"}},
            },
        }
    )
    assert cfg.asr_per_language is not None
    assert set(cfg.asr_per_language.keys()) == {"en", "ru"}
    assert cfg.asr_per_language["en"] == ModelSpec(
        name="faster-whisper", params={"language": "en"}
    )
    assert cfg.asr_per_language["ru"].params == {"language": "ru"}


def test_models_config_no_asr_per_language_is_none():
    cfg = ModelsConfig.from_dict({"asr": "dummy", "language_detection": "dummy"})
    assert cfg.asr_per_language is None


def test_models_config_asr_per_language_round_trip():
    original = ModelsConfig.from_dict(
        {
            "asr": "dummy",
            "language_detection": "dummy",
            "asr_per_language": {
                "en": {"name": "faster-whisper", "params": {"language": "en"}},
            },
        }
    )
    restored = ModelsConfig.from_dict(original.to_dict())
    assert restored == original


def test_models_config_asr_per_language_not_a_mapping_raises():
    with pytest.raises(ValueError, match="asr_per_language must be a mapping"):
        ModelsConfig.from_dict(
            {
                "asr": "dummy",
                "language_detection": "dummy",
                "asr_per_language": "en: faster-whisper",
            }
        )


# ---------------------------------------------------------------------------
# build_stages integration with registry
# ---------------------------------------------------------------------------


def test_build_stages_creates_lang_models():
    from main import build_stages

    cfg = ModelsConfig.from_dict(
        {
            "asr": "dummy",
            "language_detection": "dummy",
            "asr_per_language": {
                "en": "dummy",
                "ru": "dummy",
            },
        }
    )
    registry = default_registry()
    stages = build_stages(30.0, cfg, registry)
    asr_stage = stages[-1]
    assert isinstance(asr_stage, ASRStage)
    assert set(asr_stage.lang_models.keys()) == {"en", "ru"}


def test_build_stages_no_lang_models_when_config_absent():
    from main import build_stages

    cfg = ModelsConfig.from_dict(
        {"asr": "dummy", "language_detection": "dummy"}
    )
    registry = default_registry()
    stages = build_stages(30.0, cfg, registry)
    asr_stage = stages[-1]
    assert isinstance(asr_stage, ASRStage)
    assert asr_stage.lang_models == {}
