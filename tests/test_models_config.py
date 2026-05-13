from __future__ import annotations

from pathlib import Path

import pytest

from core.config.models_config import (
    ModelSpec,
    ModelsConfig,
    load_models_config,
)


def test_model_spec_from_string_shorthand():
    spec = ModelSpec.from_obj("dummy")
    assert spec == ModelSpec(name="dummy", params={})


def test_model_spec_from_dict_with_params():
    spec = ModelSpec.from_obj({"name": "dummy", "params": {"language": "ru"}})
    assert spec.name == "dummy"
    assert spec.params == {"language": "ru"}


def test_model_spec_from_dict_without_name_raises():
    with pytest.raises(ValueError, match="missing 'name'"):
        ModelSpec.from_obj({"params": {}})


def test_model_spec_rejects_non_dict_params():
    with pytest.raises(ValueError, match="must be a mapping"):
        ModelSpec.from_obj({"name": "dummy", "params": "ru"})


def test_model_spec_rejects_unknown_type():
    with pytest.raises(TypeError):
        ModelSpec.from_obj(42)


def test_models_config_from_dict_full():
    cfg = ModelsConfig.from_dict(
        {
            "asr": "dummy",
            "language_detection": {"name": "dummy", "params": {"language": "en"}},
            "diarization": "dummy",
        }
    )
    assert cfg.asr.name == "dummy"
    assert cfg.language_detection.params == {"language": "en"}
    assert cfg.diarization is not None
    assert cfg.diarization.name == "dummy"


def test_models_config_diarization_optional():
    cfg = ModelsConfig.from_dict(
        {"asr": "dummy", "language_detection": "dummy"}
    )
    assert cfg.diarization is None


def test_models_config_missing_required_keys_raises():
    with pytest.raises(ValueError, match="missing required keys"):
        ModelsConfig.from_dict({"asr": "dummy"})


def test_models_config_round_trip_through_dict():
    original = ModelsConfig.from_dict(
        {
            "asr": {"name": "dummy", "params": {"k": 1}},
            "language_detection": "dummy",
        }
    )
    restored = ModelsConfig.from_dict(original.to_dict())
    assert restored == original


def test_load_models_config_from_yaml(tmp_path: Path):
    path = tmp_path / "models.yaml"
    path.write_text(
        "asr: dummy\n"
        "language_detection:\n"
        "  name: dummy\n"
        "  params:\n"
        "    language: ru\n",
        encoding="utf-8",
    )
    cfg = load_models_config(path)
    assert cfg.asr == ModelSpec(name="dummy")
    assert cfg.language_detection.params == {"language": "ru"}


def test_load_models_config_rejects_non_mapping_yaml(tmp_path: Path):
    path = tmp_path / "models.yaml"
    path.write_text("- dummy\n", encoding="utf-8")
    with pytest.raises(ValueError, match="must be a mapping"):
        load_models_config(path)


def test_unknown_keys_in_config_raises():
    with pytest.raises(ValueError, match="Unknown keys"):
        ModelsConfig.from_dict(
            {
                "asr": "dummy",
                "language_detection": "dummy",
                "diarization_models": "dummy",  # typo — should be "diarization"
            }
        )


def test_unknown_keys_mentions_the_bad_key():
    with pytest.raises(ValueError, match="diarization_models"):
        ModelsConfig.from_dict(
            {"asr": "dummy", "language_detection": "dummy", "diarization_models": "x"}
        )
