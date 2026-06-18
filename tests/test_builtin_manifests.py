from __future__ import annotations

import pytest

from core.models.manifests import BUILTIN_MANIFESTS
from plugins import BUILTIN_MANIFESTS as PLUGINS_BUILTIN_MANIFESTS
from plugins import PLUGINS_DIR, all_manifests, collect_manifests
from plugins.manifest import PluginManifest

_VALID_TYPES = {"asr", "language", "diarization", "stage"}
_EXPECTED_BUILTIN_NAMES = {"dummy", "faster-whisper", "whisper-lid", "pyannote"}


def test_builtin_manifests_is_list():
    assert isinstance(BUILTIN_MANIFESTS, list)
    assert all(isinstance(m, PluginManifest) for m in BUILTIN_MANIFESTS)


def test_all_builtin_names_unique():
    names = [m.name for m in BUILTIN_MANIFESTS]
    assert len(names) == len(set(names)), "Duplicate names in BUILTIN_MANIFESTS"


def test_builtin_model_types_are_valid():
    for m in BUILTIN_MANIFESTS:
        assert m.model_type in _VALID_TYPES, f"{m.name!r} has invalid model_type {m.model_type!r}"


def test_expected_builtin_names_present():
    names = {m.name for m in BUILTIN_MANIFESTS}
    assert _EXPECTED_BUILTIN_NAMES.issubset(names)


def test_faster_whisper_manifest_has_model_size_param():
    fw = next(m for m in BUILTIN_MANIFESTS if m.name == "faster-whisper")
    assert "model_size" in fw.params_schema
    ps = fw.params_schema["model_size"]
    assert ps.type == "string"  # changed: accepts any HF repo_id, not just enum values
    assert ps.default == "tiny"


def test_faster_whisper_has_hf_repo():
    fw = next(m for m in BUILTIN_MANIFESTS if m.name == "faster-whisper")
    assert fw.hf_repo is not None
    assert "whisper" in fw.hf_repo.lower()


def test_pyannote_manifest_is_diarization():
    pyan = next(m for m in BUILTIN_MANIFESTS if m.name == "pyannote")
    assert pyan.model_type == "diarization"


def test_whisper_lid_is_language_type():
    lid = next(m for m in BUILTIN_MANIFESTS if m.name == "whisper-lid")
    assert lid.model_type == "language"


def test_builtin_manifests_exported_from_plugins():
    assert PLUGINS_BUILTIN_MANIFESTS is BUILTIN_MANIFESTS


def test_timestamp_asr_plugin_has_describe():
    # timestamp_asr — entry_point плагин, виден через all_manifests(), не через collect_manifests()
    manifests = all_manifests(PLUGINS_DIR)
    names = {m.name for m in manifests}
    assert "timestamp-asr" in names


def test_timestamp_asr_manifest_has_fmt_param():
    manifests = all_manifests(PLUGINS_DIR)
    ts = next(m for m in manifests if m.name == "timestamp-asr")
    assert "fmt" in ts.params_schema
    assert ts.params_schema["fmt"].type == "string"


def test_combined_all_manifests_no_duplicates():
    plugin_manifests = collect_manifests(PLUGINS_DIR)
    all_manifests = BUILTIN_MANIFESTS + plugin_manifests
    names = [m.name for m in all_manifests]
    assert len(names) == len(set(names)), "Duplicate names across builtin + plugin manifests"


# ── available_models ─────────────────────────────────────────────────────────

def test_faster_whisper_has_available_models():
    fw = next(m for m in BUILTIN_MANIFESTS if m.name == "faster-whisper")
    assert len(fw.available_models) > 0


def test_faster_whisper_models_have_hf_repos():
    fw = next(m for m in BUILTIN_MANIFESTS if m.name == "faster-whisper")
    for opt in fw.available_models:
        assert opt.hf_repo, f"Empty hf_repo in ModelOption: {opt.display_name}"


def test_pyannote_available_model_requires_token():
    pyan = next(m for m in BUILTIN_MANIFESTS if m.name == "pyannote")
    assert len(pyan.available_models) > 0
    assert all(opt.requires_token for opt in pyan.available_models)


def test_model_options_sizes_are_positive():
    for manifest in BUILTIN_MANIFESTS:
        for opt in manifest.available_models:
            assert opt.size_mb > 0, (
                f"{manifest.name} → {opt.display_name}: size_mb must be positive"
            )
