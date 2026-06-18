from __future__ import annotations

import pytest

from plugins.manifest import ModelOption, ParamSpec, PluginManifest

VALID_TYPES = ("asr", "language", "diarization", "stage")


# ── ParamSpec ────────────────────────────────────────────────────────────────

def test_param_spec_from_dict_string():
    ps = ParamSpec.from_dict({"type": "string", "default": "cpu"})
    assert ps.type == "string"
    assert ps.default == "cpu"
    assert ps.values is None


def test_param_spec_from_dict_float():
    ps = ParamSpec.from_dict({"type": "float", "default": 0.5, "description": "threshold"})
    assert ps.type == "float"
    assert ps.default == 0.5
    assert ps.description == "threshold"


def test_param_spec_from_dict_enum():
    ps = ParamSpec.from_dict({
        "type": "enum",
        "default": "tiny",
        "values": ["tiny", "small", "medium", "large"],
    })
    assert ps.type == "enum"
    assert ps.default == "tiny"
    assert ps.values == ["tiny", "small", "medium", "large"]


def test_param_spec_enum_without_values_raises():
    with pytest.raises(ValueError, match="values"):
        ParamSpec.from_dict({"type": "enum", "default": "tiny"})


def test_param_spec_to_dict_roundtrip_string():
    original = ParamSpec(type="string", default="cpu", description="compute device")
    assert ParamSpec.from_dict(original.to_dict()) == original


def test_param_spec_to_dict_roundtrip_enum():
    original = ParamSpec(
        type="enum", default="tiny",
        values=["tiny", "small", "large"],
        description="model size",
    )
    assert ParamSpec.from_dict(original.to_dict()) == original


# ── PluginManifest ───────────────────────────────────────────────────────────

def test_manifest_from_dict_minimal():
    m = PluginManifest.from_dict({"name": "my-asr", "model_type": "asr"})
    assert m.name == "my-asr"
    assert m.model_type == "asr"
    assert m.description == ""
    assert m.hf_repo is None
    assert m.params_schema == {}


def test_manifest_from_dict_full():
    data = {
        "name": "faster-whisper",
        "model_type": "asr",
        "description": "Whisper on CTranslate2",
        "hf_repo": "Systran/faster-whisper-large-v3",
        "params_schema": {
            "model_size": {"type": "enum", "default": "tiny", "values": ["tiny", "large"]},
            "device": {"type": "string", "default": "cpu"},
        },
    }
    m = PluginManifest.from_dict(data)
    assert m.hf_repo == "Systran/faster-whisper-large-v3"
    assert "model_size" in m.params_schema
    assert m.params_schema["model_size"].type == "enum"
    assert m.params_schema["device"].default == "cpu"


def test_manifest_to_dict_roundtrip():
    original = PluginManifest(
        name="my-model",
        model_type="language",
        description="test model",
        hf_repo="org/repo",
        params_schema={
            "lang": ParamSpec(type="string", default="ru"),
        },
    )
    assert PluginManifest.from_dict(original.to_dict()) == original


def test_manifest_unknown_model_type_raises():
    with pytest.raises(ValueError, match="model_type"):
        PluginManifest.from_dict({"name": "x", "model_type": "unknown"})


@pytest.mark.parametrize("model_type", VALID_TYPES)
def test_manifest_all_valid_model_types_accepted(model_type):
    m = PluginManifest.from_dict({"name": "x", "model_type": model_type})
    assert m.model_type == model_type


def test_manifest_missing_name_raises():
    with pytest.raises((KeyError, ValueError)):
        PluginManifest.from_dict({"model_type": "asr"})


def test_manifest_missing_model_type_raises():
    with pytest.raises((KeyError, ValueError)):
        PluginManifest.from_dict({"name": "x"})


# ── ModelOption ──────────────────────────────────────────────────────────────

def test_model_option_from_dict_minimal():
    opt = ModelOption.from_dict({
        "hf_repo": "Systran/faster-whisper-tiny",
        "display_name": "Whisper Tiny (75 MB)",
        "languages": [],
        "size_mb": 75,
    })
    assert opt.hf_repo == "Systran/faster-whisper-tiny"
    assert opt.display_name == "Whisper Tiny (75 MB)"
    assert opt.languages == []
    assert opt.size_mb == 75
    assert opt.requires_token is False
    assert opt.description == ""


def test_model_option_requires_token_default_false():
    opt = ModelOption(
        hf_repo="org/repo",
        display_name="Model",
        languages=[],
        size_mb=100,
    )
    assert opt.requires_token is False


def test_model_option_to_dict_roundtrip():
    original = ModelOption(
        hf_repo="pyannote/speaker-diarization-3.1",
        display_name="Pyannote 3.1",
        languages=["ru", "en"],
        size_mb=600,
        requires_token=True,
        description="Needs HF token",
    )
    restored = ModelOption.from_dict(original.to_dict())
    assert restored == original


def test_model_option_to_dict_omits_false_token():
    opt = ModelOption(hf_repo="a/b", display_name="X", languages=[], size_mb=10)
    d = opt.to_dict()
    assert "requires_token" not in d


def test_manifest_with_available_models_roundtrip():
    original = PluginManifest(
        name="faster-whisper",
        model_type="asr",
        available_models=[
            ModelOption("Systran/faster-whisper-tiny", "Tiny", [], 75),
            ModelOption("Systran/faster-whisper-small", "Small", [], 244),
        ],
    )
    restored = PluginManifest.from_dict(original.to_dict())
    assert restored == original
    assert len(restored.available_models) == 2


def test_manifest_without_available_models_backward_compat():
    m = PluginManifest.from_dict({"name": "old-plugin", "model_type": "asr"})
    assert m.available_models == []
