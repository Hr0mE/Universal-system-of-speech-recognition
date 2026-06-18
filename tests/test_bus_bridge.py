from __future__ import annotations

from pathlib import Path

import pytest

from core.events.events import (
    ModelDownloadFinished,
    ModelDownloadStarted,
    PipelineFailed,
    PipelineFinished,
    PipelineStarted,
    ProgressUpdated,
    StageFinished,
    StageStarted,
)
from ui.qt.bus_bridge import BusToQtBridge


@pytest.fixture
def bridge(qapp):
    return BusToQtBridge()


def test_bridge_emits_pipeline_started(qtbot, bridge: BusToQtBridge) -> None:
    with qtbot.waitSignal(bridge.pipeline_started, timeout=1000) as blocker:
        bridge.bus.publish(
            PipelineStarted(
                run_id="r1",
                audio_path=Path("/x.wav"),
                total_stages=3,
                resume_after=0,
            )
        )
    assert blocker.args == [3, 0]


def test_bridge_emits_stage_started(qtbot, bridge: BusToQtBridge) -> None:
    with qtbot.waitSignal(bridge.stage_started, timeout=1000) as blocker:
        bridge.bus.publish(
            StageStarted(run_id="r1", stage_index=1, stage_name="segmentation")
        )
    assert blocker.args == [1, "segmentation"]


def test_bridge_emits_stage_done(qtbot, bridge: BusToQtBridge) -> None:
    with qtbot.waitSignal(bridge.stage_done, timeout=1000) as blocker:
        bridge.bus.publish(
            StageFinished(
                run_id="r1",
                stage_index=2,
                stage_name="asr",
                segments_count=5,
                artifact=None,
            )
        )
    assert blocker.args == [2, "asr", 5]


def test_bridge_emits_pipeline_done(qtbot, bridge: BusToQtBridge) -> None:
    with qtbot.waitSignal(bridge.pipeline_done, timeout=1000) as blocker:
        bridge.bus.publish(PipelineFinished(run_id="r1", segments_count=42))
    assert blocker.args == [42]


def test_bridge_emits_pipeline_failed(qtbot, bridge: BusToQtBridge) -> None:
    with qtbot.waitSignal(bridge.pipeline_failed, timeout=1000) as blocker:
        bridge.bus.publish(PipelineFailed(run_id="r1", error="boom"))
    assert blocker.args == ["boom"]


def test_bridge_emits_model_downloading(qtbot, bridge: BusToQtBridge) -> None:
    with qtbot.waitSignal(bridge.model_downloading, timeout=1000) as blocker:
        bridge.bus.publish(
            ModelDownloadStarted(run_id="r1", model_name="whisper", repo_id="Systran/x")
        )
    assert blocker.args == ["whisper", "Systran/x"]


def test_bridge_emits_model_ready(qtbot, bridge: BusToQtBridge) -> None:
    with qtbot.waitSignal(bridge.model_ready, timeout=1000) as blocker:
        bridge.bus.publish(
            ModelDownloadFinished(run_id="r1", model_name="whisper", repo_id="Systran/x")
        )
    assert blocker.args == ["whisper"]


def test_bridge_emits_progress_updated(qtbot, bridge: BusToQtBridge) -> None:
    with qtbot.waitSignal(bridge.progress_updated, timeout=1000) as blocker:
        bridge.bus.publish(
            ProgressUpdated(run_id="r1", stage_index=2, stage_name="asr", current=50, total=100)
        )
    assert blocker.args == [2, 50, 100]
