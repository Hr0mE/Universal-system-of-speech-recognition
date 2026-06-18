from __future__ import annotations

import struct
import wave
from pathlib import Path
from unittest.mock import patch

import pytest

from core.api.transcribe import TranscriptionResult
from core.config.pipeline_config import default_pipeline_config
from core.pipeline.context import Segment
from ui.qt.bus_bridge import BusToQtBridge
from ui.qt.worker import TranscribeWorker


@pytest.fixture
def wav_file(tmp_path: Path) -> Path:
    path = tmp_path / "test.wav"
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(b"\x00\x00" * 16000)
    return path


def _make_result(run_dir: Path) -> TranscriptionResult:
    return TranscriptionResult(
        segments=[Segment(start_time=0.0, end_time=1.0, text="hello", language="en")],
        run_id="run_test",
        run_dir=run_dir,
    )


def test_worker_emits_finished_on_success(qtbot, tmp_path: Path, wav_file: Path) -> None:
    bridge = BusToQtBridge()
    result_obj = _make_result(tmp_path)

    with patch("ui.qt.worker.transcribe", return_value=result_obj):
        worker = TranscribeWorker(wav_file, default_pipeline_config(), bridge, tmp_path)
        with qtbot.waitSignal(worker.result_ready, timeout=3000) as blocker:
            worker.start()
        worker.wait()

    assert blocker.args[0] is result_obj


def test_worker_emits_failed_on_exception(qtbot, tmp_path: Path, wav_file: Path) -> None:
    bridge = BusToQtBridge()

    with patch("ui.qt.worker.transcribe", side_effect=RuntimeError("oops")):
        worker = TranscribeWorker(wav_file, default_pipeline_config(), bridge, tmp_path)
        with qtbot.waitSignal(worker.failed, timeout=3000) as blocker:
            worker.start()
        worker.wait()

    assert "oops" in blocker.args[0]


def test_worker_passes_event_bus_to_transcribe(qtbot, tmp_path: Path, wav_file: Path) -> None:
    bridge = BusToQtBridge()
    captured: dict = {}

    def fake_transcribe(audio_path, models_config=None, *, runs_dir, window_seconds=30.0, event_bus=None, stop_requested=None):
        captured["event_bus"] = event_bus
        return _make_result(tmp_path)

    with patch("ui.qt.worker.transcribe", side_effect=fake_transcribe):
        worker = TranscribeWorker(wav_file, default_pipeline_config(), bridge, tmp_path)
        with qtbot.waitSignal(worker.result_ready, timeout=3000):
            worker.start()
        worker.wait()

    assert captured["event_bus"] is bridge.bus
