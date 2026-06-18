"""Tests for PipelinePreset domain model and PipelinePresetStore storage."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from core.config.pipeline_config import PipelineConfig, StageConfig
from core.domain.pipeline_preset import PipelinePreset
from core.storage.pipeline_preset_store import PipelinePresetStore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _simple_config() -> PipelineConfig:
    return PipelineConfig(stages=[
        StageConfig(
            stage_id="asr",
            enabled=True,
            model_name="faster-whisper",
            params={"model_size": "tiny", "device": "cpu", "compute_type": "int8"},
        )
    ])


def _full_config() -> PipelineConfig:
    return PipelineConfig(stages=[
        StageConfig(stage_id="segmentation", enabled=True, model_name="",
                    params={"window_seconds": 30.0}),
        StageConfig(stage_id="diarization", enabled=False, model_name="pyannote",
                    params={"hf_token": "", "min_speakers": 1, "max_speakers": 10}),
        StageConfig(stage_id="asr", enabled=True, model_name="faster-whisper",
                    params={"model_size": "small", "device": "cuda", "compute_type": "float16"}),
    ])


# ---------------------------------------------------------------------------
# AC-1: PipelinePreset.new(name, config) creates a preset with auto-generated
#        preset_id (format preset_YYYYMMDD_HHMMSS_<hex6>), current created_at,
#        and the given name / config.
# ---------------------------------------------------------------------------

def test_ac1_new_preset_has_auto_generated_id():
    config = _simple_config()
    preset = PipelinePreset.new("My preset", config)

    assert preset.preset_id.startswith("preset_")
    parts = preset.preset_id.split("_")
    # preset_YYYYMMDD_HHMMSS_hex6  →  ['preset', 'YYYYMMDD', 'HHMMSS', 'hex6']
    assert len(parts) == 4
    assert len(parts[1]) == 8   # YYYYMMDD
    assert len(parts[2]) == 6   # HHMMSS
    assert len(parts[3]) == 6   # hex6


def test_ac1_new_preset_stores_name_and_config():
    config = _simple_config()
    preset = PipelinePreset.new("Fast ASR", config)

    assert preset.name == "Fast ASR"
    assert preset.config is config


def test_ac1_new_preset_has_created_at_iso():
    preset = PipelinePreset.new("x", _simple_config())

    # Must be parseable ISO 8601 — basic smoke check
    from datetime import datetime
    dt = datetime.fromisoformat(preset.created_at)
    assert dt.year >= 2024


def test_ac1_two_new_presets_have_different_ids():
    p1 = PipelinePreset.new("a", _simple_config())
    time.sleep(0.01)
    p2 = PipelinePreset.new("b", _simple_config())
    assert p1.preset_id != p2.preset_id


# ---------------------------------------------------------------------------
# AC-2: PipelinePresetStore.save(preset) writes {preset_id}.json to
#        presets_dir; the file contains valid JSON with all preset fields.
# ---------------------------------------------------------------------------

def test_ac2_save_creates_json_file(tmp_path: Path):
    store = PipelinePresetStore(tmp_path / "presets")
    preset = PipelinePreset.new("Saved preset", _simple_config())
    store.save(preset)

    expected = tmp_path / "presets" / f"{preset.preset_id}.json"
    assert expected.exists()


def test_ac2_saved_json_contains_all_fields(tmp_path: Path):
    store = PipelinePresetStore(tmp_path / "presets")
    preset = PipelinePreset.new("Full preset", _full_config())
    store.save(preset)

    path = tmp_path / "presets" / f"{preset.preset_id}.json"
    data = json.loads(path.read_text(encoding="utf-8"))

    assert data["preset_id"] == preset.preset_id
    assert data["name"] == "Full preset"
    assert "created_at" in data
    assert "config" in data
    assert "stages" in data["config"]


def test_ac2_save_creates_presets_dir_if_missing(tmp_path: Path):
    presets_dir = tmp_path / "deep" / "nested" / "presets"
    store = PipelinePresetStore(presets_dir)
    preset = PipelinePreset.new("p", _simple_config())
    store.save(preset)

    assert (presets_dir / f"{preset.preset_id}.json").exists()


# ---------------------------------------------------------------------------
# AC-3: PipelinePresetStore.load(preset_id) returns PipelinePreset or None.
# ---------------------------------------------------------------------------

def test_ac3_load_returns_saved_preset(tmp_path: Path):
    store = PipelinePresetStore(tmp_path / "presets")
    preset = PipelinePreset.new("Loaded preset", _simple_config())
    store.save(preset)

    loaded = store.load(preset.preset_id)

    assert loaded is not None
    assert loaded.preset_id == preset.preset_id
    assert loaded.name == "Loaded preset"


def test_ac3_load_returns_none_for_unknown_id(tmp_path: Path):
    store = PipelinePresetStore(tmp_path / "presets")
    result = store.load("preset_99991231_235959_ffffff")
    assert result is None


# ---------------------------------------------------------------------------
# AC-4: PipelinePresetStore.load_all() returns all presets sorted by
#        created_at descending (newest first).
# ---------------------------------------------------------------------------

def test_ac4_load_all_returns_all_saved_presets(tmp_path: Path):
    store = PipelinePresetStore(tmp_path / "presets")
    p1 = PipelinePreset.new("alpha", _simple_config())
    time.sleep(0.01)
    p2 = PipelinePreset.new("beta", _simple_config())
    store.save(p1)
    store.save(p2)

    all_presets = store.load_all()
    ids = [p.preset_id for p in all_presets]

    assert len(all_presets) == 2
    assert p1.preset_id in ids
    assert p2.preset_id in ids


def test_ac4_load_all_sorted_newest_first(tmp_path: Path):
    store = PipelinePresetStore(tmp_path / "presets")
    p1 = PipelinePreset.new("older", _simple_config())
    time.sleep(0.05)
    p2 = PipelinePreset.new("newer", _simple_config())
    store.save(p1)
    store.save(p2)

    all_presets = store.load_all()

    assert all_presets[0].preset_id == p2.preset_id
    assert all_presets[1].preset_id == p1.preset_id


# ---------------------------------------------------------------------------
# AC-5: PipelinePresetStore.delete(preset_id) removes the file;
#        subsequent load(preset_id) returns None.
# ---------------------------------------------------------------------------

def test_ac5_delete_removes_file(tmp_path: Path):
    store = PipelinePresetStore(tmp_path / "presets")
    preset = PipelinePreset.new("to delete", _simple_config())
    store.save(preset)

    store.delete(preset.preset_id)

    assert store.load(preset.preset_id) is None


def test_ac5_delete_file_is_gone_from_disk(tmp_path: Path):
    store = PipelinePresetStore(tmp_path / "presets")
    preset = PipelinePreset.new("gone", _simple_config())
    store.save(preset)
    json_path = tmp_path / "presets" / f"{preset.preset_id}.json"
    assert json_path.exists()

    store.delete(preset.preset_id)

    assert not json_path.exists()


# ---------------------------------------------------------------------------
# AC-6: PipelinePreset.to_dict() / from_dict() round-trip preserves all fields
#        including nested PipelineConfig stages.
# ---------------------------------------------------------------------------

def test_ac6_roundtrip_preserves_preset_id_and_name():
    preset = PipelinePreset.new("Roundtrip", _full_config())
    restored = PipelinePreset.from_dict(preset.to_dict())

    assert restored.preset_id == preset.preset_id
    assert restored.name == preset.name
    assert restored.created_at == preset.created_at


def test_ac6_roundtrip_preserves_pipeline_config_stages():
    config = _full_config()
    preset = PipelinePreset.new("Config roundtrip", config)
    restored = PipelinePreset.from_dict(preset.to_dict())

    assert len(restored.config.stages) == len(config.stages)
    for orig, rest in zip(config.stages, restored.config.stages):
        assert rest.stage_id == orig.stage_id
        assert rest.enabled == orig.enabled
        assert rest.model_name == orig.model_name
        assert rest.params == orig.params


def test_ac6_roundtrip_via_json_string():
    preset = PipelinePreset.new("JSON roundtrip", _full_config())
    data = json.dumps(preset.to_dict(), ensure_ascii=False)
    restored = PipelinePreset.from_dict(json.loads(data))

    assert restored.preset_id == preset.preset_id
    assert len(restored.config.stages) == 3


# ---------------------------------------------------------------------------
# EC-1: load_all() on an empty or nonexistent directory returns [].
# ---------------------------------------------------------------------------

def test_ec1_load_all_on_nonexistent_dir_returns_empty(tmp_path: Path):
    store = PipelinePresetStore(tmp_path / "does_not_exist_yet")
    result = store.load_all()
    assert result == []


def test_ec1_load_all_on_empty_dir_returns_empty(tmp_path: Path):
    presets_dir = tmp_path / "empty_presets"
    presets_dir.mkdir()
    store = PipelinePresetStore(presets_dir)
    result = store.load_all()
    assert result == []


# ---------------------------------------------------------------------------
# EC-2: A corrupted JSON file is silently skipped by load_all().
# ---------------------------------------------------------------------------

def test_ec2_corrupted_file_skipped_in_load_all(tmp_path: Path):
    presets_dir = tmp_path / "presets"
    store = PipelinePresetStore(presets_dir)
    good_preset = PipelinePreset.new("good", _simple_config())
    store.save(good_preset)

    # Write a corrupted file alongside the valid one
    (presets_dir / "preset_bad.json").write_text("not valid json{{{", encoding="utf-8")

    result = store.load_all()
    assert len(result) == 1
    assert result[0].preset_id == good_preset.preset_id


# ---------------------------------------------------------------------------
# EC-3: delete() on a nonexistent preset_id does not raise.
# ---------------------------------------------------------------------------

def test_ec3_delete_nonexistent_does_not_raise(tmp_path: Path):
    store = PipelinePresetStore(tmp_path / "presets")
    # Should not raise any exception
    store.delete("preset_00000000_000000_000000")


# ---------------------------------------------------------------------------
# ERR-1: PipelinePreset.new(name="", config=...) raises ValueError.
# ---------------------------------------------------------------------------

def test_err1_empty_name_raises_value_error():
    with pytest.raises(ValueError):
        PipelinePreset.new("", _simple_config())
