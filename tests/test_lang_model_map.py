"""Tests for StageConfig.lang_model_map and build_stages_from_pipeline integration.

Spec: lang_model_map в StageConfig и build_stages_from_pipeline
Coverage: AC-1..AC-5, EC-1
"""

from __future__ import annotations

import pytest

from core.config.pipeline_config import PipelineConfig, StageConfig
from core.models import default_registry
from core.pipeline.stages import ASRStage


# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────

def _asr_cfg(**kwargs) -> StageConfig:
    return StageConfig(
        stage_id="asr",
        enabled=True,
        model_name="dummy",
        **kwargs,
    )


def _pipeline(lang_model_map: dict) -> PipelineConfig:
    return PipelineConfig(stages=[_asr_cfg(lang_model_map=lang_model_map)])


# ─────────────────────────────────────────────────────────────────────
# AC-1: StageConfig serializes lang_model_map
# ─────────────────────────────────────────────────────────────────────

def test_ac1_empty_lang_model_map_present_in_serialized_dict():
    cfg = _asr_cfg()
    d = cfg.to_dict()
    assert "lang_model_map" in d
    assert d["lang_model_map"] == {}


def test_ac1_populated_lang_model_map_serialized_correctly():
    cfg = _asr_cfg(lang_model_map={
        "ru": {"model_name": "faster-whisper", "model_size": "large-v3"},
        "zh": {"model_name": "faster-whisper", "model_size": "medium"},
    })
    d = cfg.to_dict()
    assert d["lang_model_map"] == {
        "ru": {"model_name": "faster-whisper", "model_size": "large-v3"},
        "zh": {"model_name": "faster-whisper", "model_size": "medium"},
    }


# ─────────────────────────────────────────────────────────────────────
# AC-2: StageConfig.from_dict() restores lang_model_map
# ─────────────────────────────────────────────────────────────────────

def test_ac2_from_dict_restores_lang_model_map():
    data = {
        "stage_id": "asr",
        "enabled": True,
        "model_name": "dummy",
        "params": {},
        "lang_model_map": {
            "ru": {"model_name": "faster-whisper", "model_size": "large-v3"},
        },
    }
    cfg = StageConfig.from_dict(data)
    assert cfg.lang_model_map == {
        "ru": {"model_name": "faster-whisper", "model_size": "large-v3"},
    }


def test_ac2_round_trip_preserves_lang_model_map():
    original = _asr_cfg(lang_model_map={
        "en": {"model_name": "dummy", "model_size": "tiny"},
    })
    restored = StageConfig.from_dict(original.to_dict())
    assert restored.lang_model_map == original.lang_model_map


# ─────────────────────────────────────────────────────────────────────
# AC-3: Missing key → empty dict (backward compat)
# ─────────────────────────────────────────────────────────────────────

def test_ac3_missing_lang_model_map_key_defaults_to_empty_dict():
    data = {
        "stage_id": "asr",
        "enabled": True,
        "model_name": "dummy",
        "params": {},
    }
    cfg = StageConfig.from_dict(data)
    assert cfg.lang_model_map == {}


# ─────────────────────────────────────────────────────────────────────
# AC-4: build_stages_from_pipeline with non-empty lang_model_map
# ─────────────────────────────────────────────────────────────────────

def test_ac4_build_stages_creates_lang_models_from_map():
    from core.api.transcribe import build_stages_from_pipeline

    pipeline = _pipeline(lang_model_map={
        "ru": {"model_name": "dummy"},
        "en": {"model_name": "dummy"},
    })
    stages = build_stages_from_pipeline(pipeline, default_registry())

    asr = next((s for s in stages if isinstance(s, ASRStage)), None)
    assert asr is not None
    assert set(asr.lang_models.keys()) == {"ru", "en"}


def test_ac4_lang_model_instances_are_asr_models():
    from core.api.transcribe import build_stages_from_pipeline
    from core.models.base import ASRModel

    pipeline = _pipeline(lang_model_map={"ru": {"model_name": "dummy"}})
    stages = build_stages_from_pipeline(pipeline, default_registry())

    asr = next(s for s in stages if isinstance(s, ASRStage))
    assert isinstance(asr.lang_models["ru"], ASRModel)


# ─────────────────────────────────────────────────────────────────────
# AC-5: build_stages_from_pipeline with empty lang_model_map
# ─────────────────────────────────────────────────────────────────────

def test_ac5_empty_lang_model_map_produces_empty_lang_models():
    from core.api.transcribe import build_stages_from_pipeline

    pipeline = _pipeline(lang_model_map={})
    stages = build_stages_from_pipeline(pipeline, default_registry())

    asr = next(s for s in stages if isinstance(s, ASRStage))
    assert asr.lang_models == {}


# ─────────────────────────────────────────────────────────────────────
# EC-1: Missing model_name → fallback to stage_cfg.model_name
# ─────────────────────────────────────────────────────────────────────

def test_ec1_missing_model_name_in_entry_falls_back_to_stage_model_name():
    from core.api.transcribe import build_stages_from_pipeline

    pipeline = _pipeline(lang_model_map={"ru": {}})
    # Should not raise — "dummy" from stage_cfg.model_name is used as fallback
    stages = build_stages_from_pipeline(pipeline, default_registry())

    asr = next(s for s in stages if isinstance(s, ASRStage))
    assert "ru" in asr.lang_models
