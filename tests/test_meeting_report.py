from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.export.report import (
    MeetingReport,
    SpeakerGroup,
    _fmt_time,
    build_meeting_report,
    export_json,
    export_txt,
)
from core.api.transcribe import TranscriptionResult
from core.pipeline.context import Segment


def _result(*segments: Segment, run_id: str = "run_test", audio_path: Path = Path("/a.wav"), duration_s: float = 60.0) -> TranscriptionResult:
    return TranscriptionResult(
        segments=list(segments),
        run_id=run_id,
        run_dir=Path("/tmp/run_test"),
        audio_path=audio_path,
        duration_s=duration_s,
    )


# ---------------------------------------------------------------------------
# _fmt_time
# ---------------------------------------------------------------------------


def test_fmt_time_seconds_only():
    assert _fmt_time(90) == "01:30"


def test_fmt_time_zero():
    assert _fmt_time(0) == "00:00"


def test_fmt_time_hours():
    assert _fmt_time(3661) == "1:01:01"


def test_fmt_time_exact_minute():
    assert _fmt_time(60) == "01:00"


# ---------------------------------------------------------------------------
# build_meeting_report
# ---------------------------------------------------------------------------


def test_build_groups_two_speakers():
    result = _result(
        Segment(0.0, 10.0, speaker_id="S1", language="en", text="Hi"),
        Segment(10.0, 20.0, speaker_id="S2", language="ru", text="Привет"),
    )
    report = build_meeting_report(result)
    assert len(report.speakers) == 2
    assert report.speakers[0].speaker_id == "S1"
    assert report.speakers[1].speaker_id == "S2"


def test_build_no_diarization():
    result = _result(
        Segment(0.0, 10.0, speaker_id=None, language="en", text="Hello"),
        Segment(10.0, 20.0, speaker_id=None, language="en", text="World"),
    )
    report = build_meeting_report(result)
    assert len(report.speakers) == 1
    assert report.speakers[0].speaker_id is None
    assert len(report.speakers[0].segments) == 2


def test_groups_sorted_by_first_appearance():
    result = _result(
        Segment(5.0, 10.0, speaker_id="S1", language="en", text="Late"),
        Segment(0.0, 5.0, speaker_id="S2", language="en", text="Early"),
    )
    report = build_meeting_report(result)
    # S2 appears first (start_time=0.0)
    assert report.speakers[0].speaker_id == "S2"
    assert report.speakers[1].speaker_id == "S1"


def test_total_duration_correct():
    result = _result(
        Segment(0.0, 10.0, speaker_id="S1"),
        Segment(20.0, 25.0, speaker_id="S1"),
    )
    report = build_meeting_report(result)
    assert report.speakers[0].total_duration == pytest.approx(15.0)


def test_report_metadata():
    result = _result(
        Segment(0.0, 5.0),
        run_id="run_xyz",
        audio_path=Path("/my/audio.wav"),
        duration_s=64.6,
    )
    report = build_meeting_report(result)
    assert report.run_id == "run_xyz"
    assert report.audio_path == "/my/audio.wav"
    assert report.duration_s == pytest.approx(64.6)


def test_empty_segments():
    result = _result()
    report = build_meeting_report(result)
    assert report.speakers == []


# ---------------------------------------------------------------------------
# export_json
# ---------------------------------------------------------------------------


def test_export_json_roundtrip(tmp_path: Path):
    result = _result(
        Segment(0.0, 30.0, speaker_id="S1", language="en", text="Hello world"),
    )
    report = build_meeting_report(result)
    path = tmp_path / "result.json"
    export_json(report, path)

    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["run_id"] == "run_test"
    assert data["duration_s"] == pytest.approx(60.0)
    assert len(data["speakers"]) == 1
    assert len(data["speakers"][0]["segments"]) == 1
    assert data["speakers"][0]["segments"][0]["text"] == "Hello world"


def test_export_json_no_speaker_id_in_segments(tmp_path: Path):
    result = _result(
        Segment(0.0, 10.0, speaker_id="S1", language="en", text="Hi"),
    )
    report = build_meeting_report(result)
    path = tmp_path / "result.json"
    export_json(report, path)

    data = json.loads(path.read_text(encoding="utf-8"))
    seg = data["speakers"][0]["segments"][0]
    assert "speaker_id" not in seg, "speaker_id should not be duplicated inside segments"


def test_export_json_structure_keys(tmp_path: Path):
    result = _result(Segment(0.0, 5.0, speaker_id="S1"))
    report = build_meeting_report(result)
    path = tmp_path / "r.json"
    export_json(report, path)

    data = json.loads(path.read_text(encoding="utf-8"))
    assert set(data.keys()) == {"run_id", "audio_path", "duration_s", "speakers"}
    grp = data["speakers"][0]
    assert "speaker_id" in grp
    assert "total_duration" in grp
    assert "segments" in grp


# ---------------------------------------------------------------------------
# export_txt
# ---------------------------------------------------------------------------


def test_export_txt_contains_speaker_id(tmp_path: Path):
    result = _result(
        Segment(0.0, 10.0, speaker_id="SPEAKER_00", language="en", text="Hello"),
    )
    report = build_meeting_report(result)
    path = tmp_path / "result.txt"
    export_txt(report, path)

    content = path.read_text(encoding="utf-8")
    assert "SPEAKER_00" in content


def test_export_txt_contains_formatted_time(tmp_path: Path):
    result = _result(
        Segment(0.0, 30.0, speaker_id="S1", language="en", text="Hello"),
    )
    report = build_meeting_report(result)
    path = tmp_path / "result.txt"
    export_txt(report, path)

    content = path.read_text(encoding="utf-8")
    assert "00:00" in content
    assert "00:30" in content


def test_export_txt_contains_run_id(tmp_path: Path):
    result = _result(Segment(0.0, 5.0), run_id="run_abc123")
    report = build_meeting_report(result)
    path = tmp_path / "r.txt"
    export_txt(report, path)

    content = path.read_text(encoding="utf-8")
    assert "run_abc123" in content


def test_export_txt_unknown_speaker_for_none(tmp_path: Path):
    result = _result(Segment(0.0, 5.0, speaker_id=None, text="hi"))
    report = build_meeting_report(result)
    path = tmp_path / "r.txt"
    export_txt(report, path)

    content = path.read_text(encoding="utf-8")
    assert "Unknown" in content
