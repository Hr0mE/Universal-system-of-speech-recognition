from __future__ import annotations

import pytest

from core.pipeline.context import PipelineContext, Segment
from core.pipeline.registry import StageRegistry
from core.pipeline.stage import Stage


class _SimpleStage(Stage):
    name = "simple"

    def run(self, segments: list[Segment], context: PipelineContext) -> list[Segment]:
        return segments


class _ParamStage(Stage):
    name = "param"

    def __init__(self, multiplier: int = 1) -> None:
        self.multiplier = multiplier

    def run(self, segments: list[Segment], context: PipelineContext) -> list[Segment]:
        return segments * self.multiplier


def test_register_and_create():
    registry = StageRegistry()
    registry.register("simple", _SimpleStage)

    stage = registry.create("simple")
    assert isinstance(stage, _SimpleStage)


def test_create_passes_kwargs():
    registry = StageRegistry()
    registry.register("param", _ParamStage)

    stage = registry.create("param", multiplier=3)
    assert isinstance(stage, _ParamStage)
    assert stage.multiplier == 3


def test_list_returns_sorted_names():
    registry = StageRegistry()
    registry.register("zebra", _SimpleStage)
    registry.register("alpha", _SimpleStage)
    registry.register("middle", _SimpleStage)

    assert registry.list() == ["alpha", "middle", "zebra"]


def test_duplicate_registration_raises():
    registry = StageRegistry()
    registry.register("simple", _SimpleStage)

    with pytest.raises(ValueError, match="already registered"):
        registry.register("simple", _SimpleStage)


def test_unknown_name_raises_with_known_list():
    registry = StageRegistry()
    registry.register("a", _SimpleStage)
    registry.register("b", _SimpleStage)

    with pytest.raises(KeyError) as exc_info:
        registry.create("missing")

    msg = str(exc_info.value)
    assert "missing" in msg
    assert "['a', 'b']" in msg


def test_register_callable_factory():
    registry = StageRegistry()

    def make_stage(multiplier: int = 2) -> _ParamStage:
        return _ParamStage(multiplier=multiplier)

    registry.register("factory", make_stage)
    stage = registry.create("factory", multiplier=5)

    assert isinstance(stage, _ParamStage)
    assert stage.multiplier == 5
