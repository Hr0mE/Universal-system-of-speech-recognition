from __future__ import annotations

from pathlib import Path

from core.events.bus import EventBus
from core.events.events import PipelineFailed, PipelineStarted, StageStarted


def make_started(run_id: str = "r1") -> PipelineStarted:
    return PipelineStarted(
        run_id=run_id,
        audio_path=Path("/tmp/x.wav"),
        total_stages=2,
        resume_after=0,
    )


def test_subscribe_and_publish_delivers_event():
    bus = EventBus()
    received: list[PipelineStarted] = []
    bus.subscribe(PipelineStarted, received.append)

    event = make_started()
    bus.publish(event)

    assert received == [event]


def test_multiple_handlers_called_in_subscription_order():
    bus = EventBus()
    calls: list[str] = []
    bus.subscribe(PipelineStarted, lambda e: calls.append("a"))
    bus.subscribe(PipelineStarted, lambda e: calls.append("b"))
    bus.subscribe(PipelineStarted, lambda e: calls.append("c"))

    bus.publish(make_started())

    assert calls == ["a", "b", "c"]


def test_handler_exception_does_not_break_other_handlers():
    bus = EventBus()
    calls: list[str] = []

    def bad(_event):
        calls.append("bad")
        raise ValueError("handler blew up")

    def good(_event):
        calls.append("good")

    bus.subscribe(PipelineStarted, bad)
    bus.subscribe(PipelineStarted, good)

    bus.publish(make_started())

    assert calls == ["bad", "good"]


def test_unsubscribe_stops_further_delivery():
    bus = EventBus()
    received: list[PipelineStarted] = []
    unsubscribe = bus.subscribe(PipelineStarted, received.append)

    bus.publish(make_started("first"))
    unsubscribe()
    bus.publish(make_started("second"))

    assert len(received) == 1
    assert received[0].run_id == "first"


def test_publish_with_no_subscribers_is_noop():
    bus = EventBus()
    bus.publish(make_started())


def test_handlers_are_matched_by_exact_type_only():
    bus = EventBus()
    started_calls: list = []
    failed_calls: list = []

    bus.subscribe(PipelineStarted, started_calls.append)
    bus.subscribe(PipelineFailed, failed_calls.append)

    bus.publish(make_started())

    assert len(started_calls) == 1
    assert failed_calls == []


def test_unsubscribe_is_idempotent():
    bus = EventBus()
    unsubscribe = bus.subscribe(StageStarted, lambda e: None)
    unsubscribe()
    unsubscribe()
