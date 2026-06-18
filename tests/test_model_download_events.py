from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from core.events.bus import EventBus
from core.events.events import ModelDownloadFinished, ModelDownloadStarted
from core.models.whisper_asr import FasterWhisperASR
from core.models.whisper_lid import WhisperLanguageDetector


def _make_context(run_id: str = "test-run", bus: EventBus | None = None):
    ctx = MagicMock()
    ctx.run_id = run_id
    ctx.event_bus = bus or EventBus()
    ctx.audio_path = Path("/fake/audio.wav")
    return ctx


def _make_segment(start: float = 0.0, end: float = 1.0):
    seg = MagicMock()
    seg.start_time = start
    seg.end_time = end
    seg.language = "en"
    return seg


# ── FasterWhisperASR ─────────────────────────────────────────────────────────

def test_download_events_published_on_first_transcribe():
    bus = EventBus()
    received = []
    bus.subscribe(ModelDownloadStarted, received.append)
    bus.subscribe(ModelDownloadFinished, received.append)

    fake_audio = np.zeros(16000, dtype=np.float32)
    fake_model = MagicMock()
    fake_model.transcribe.return_value = (iter([]), MagicMock())

    asr = FasterWhisperASR(model_size="tiny")
    ctx = _make_context(bus=bus)

    with patch.object(asr, "_get_audio", return_value=fake_audio), \
         patch("faster_whisper.WhisperModel", return_value=fake_model):
        asr.transcribe(_make_segment(), ctx)

    assert len(received) == 2
    assert isinstance(received[0], ModelDownloadStarted)
    assert isinstance(received[1], ModelDownloadFinished)
    assert received[0].model_name == "faster-whisper"
    assert received[0].repo_id == "tiny"
    assert received[0].run_id == "test-run"


def test_download_events_not_published_twice():
    bus = EventBus()
    received = []
    bus.subscribe(ModelDownloadStarted, received.append)

    fake_audio = np.zeros(16000, dtype=np.float32)
    fake_model = MagicMock()
    fake_model.transcribe.return_value = (iter([]), MagicMock())

    asr = FasterWhisperASR(model_size="tiny")
    ctx = _make_context(bus=bus)

    with patch.object(asr, "_get_audio", return_value=fake_audio), \
         patch("faster_whisper.WhisperModel", return_value=fake_model):
        asr.transcribe(_make_segment(), ctx)
        asr.transcribe(_make_segment(1.0, 2.0), ctx)

    assert len(received) == 1


def test_download_events_skipped_without_event_bus():
    fake_audio = np.zeros(16000, dtype=np.float32)
    fake_model = MagicMock()
    fake_model.transcribe.return_value = (iter([]), MagicMock())

    asr = FasterWhisperASR(model_size="tiny")
    ctx = MagicMock()
    ctx.run_id = "no-bus-run"
    ctx.event_bus = None
    ctx.audio_path = Path("/fake/audio.wav")

    with patch.object(asr, "_get_audio", return_value=fake_audio), \
         patch("faster_whisper.WhisperModel", return_value=fake_model):
        result = asr.transcribe(_make_segment(), ctx)

    assert result == ""


# ── WhisperLanguageDetector ───────────────────────────────────────────────────

def test_lid_download_events_published_on_first_detect():
    bus = EventBus()
    received = []
    bus.subscribe(ModelDownloadStarted, received.append)
    bus.subscribe(ModelDownloadFinished, received.append)

    fake_audio = np.zeros(16000, dtype=np.float32)
    fake_model = MagicMock()
    fake_model.detect_language.return_value = ("en", 0.99, MagicMock())

    lid = WhisperLanguageDetector(model_size="tiny")
    ctx = _make_context(bus=bus)

    with patch.object(lid, "_get_audio", return_value=fake_audio), \
         patch("faster_whisper.WhisperModel", return_value=fake_model):
        lid.detect(_make_segment(), ctx)

    assert len(received) == 2
    assert received[0].model_name == "whisper-lid"
