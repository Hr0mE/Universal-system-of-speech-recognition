from __future__ import annotations

import pytest

from core.config.config import RunConfig
from core.pipeline.context import Segment
from core.pipeline.state import STATUS_COMPLETED, PipelineState
from core.storage.run_manager import RunManager


def test_create_run_creates_directory(run_manager: RunManager):
    run_dir = run_manager.create_run("run_xyz")
    assert run_dir.exists()
    assert run_dir.name == "run_xyz"


def test_save_and_load_config_dataclass(run_manager: RunManager):
    run_dir = run_manager.create_run("run_xyz")
    config = RunConfig(
        audio_path="/tmp/a.wav",
        audio_duration=123.5,
        window_seconds=30.0,
        stages=["dummy", "segmentation"],
    )
    run_manager.save_config(run_dir, config)

    loaded = run_manager.load_config(run_dir)

    assert loaded["audio_path"] == "/tmp/a.wav"
    assert loaded["audio_duration"] == 123.5
    assert loaded["stages"] == ["dummy", "segmentation"]


def test_save_config_accepts_plain_dict(run_manager: RunManager):
    run_dir = run_manager.create_run("run_xyz")
    run_manager.save_config(run_dir, {"foo": "bar"})
    assert run_manager.load_config(run_dir) == {"foo": "bar"}


def test_save_config_rejects_unsupported_type(run_manager: RunManager):
    run_dir = run_manager.create_run("run_xyz")
    with pytest.raises(TypeError):
        run_manager.save_config(run_dir, "not a config")


def test_save_and_load_state_roundtrip(run_manager: RunManager):
    run_dir = run_manager.create_run("run_xyz")
    state = PipelineState(run_id="run_xyz")
    state.mark_stage_done(1, "dummy")
    state.mark_stage_done(2, "segmentation")
    state.status = STATUS_COMPLETED

    run_manager.save_state(run_dir, state)
    loaded = run_manager.load_state(run_dir)

    assert loaded == state


def test_save_and_load_stage_result_roundtrip(run_manager: RunManager):
    run_dir = run_manager.create_run("run_xyz")
    segments = [
        Segment(start_time=0.0, end_time=10.0, speaker_id="A"),
        Segment(start_time=10.0, end_time=20.0, speaker_id="B", language="ru"),
    ]

    run_manager.save_stage_result(run_dir, 2, "segmentation", segments)
    loaded = run_manager.load_stage_result(run_dir, 2, "segmentation")

    assert loaded == segments


def test_stage_filename_is_zero_padded():
    assert (
        RunManager._stage_filename(1, "dummy") == "stage_01_dummy.json"
    )
    assert (
        RunManager._stage_filename(12, "asr") == "stage_12_asr.json"
    )
