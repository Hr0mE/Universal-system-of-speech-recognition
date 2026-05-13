from __future__ import annotations

import pytest

from core.models import default_registry
from core.models.base import ASRModel, DiarizationModel, LanguageModel
from core.models.dummy import DummyASR, DummyDiarization, DummyLanguageModel
from core.models.registry import ModelRegistry
from core.pipeline.context import PipelineContext, Segment


class _CustomASR(ASRModel):
    name = "custom"

    def __init__(self, prefix: str = ">>") -> None:
        self.prefix = prefix

    def transcribe(self, segment: Segment, context: PipelineContext) -> str:
        return f"{self.prefix} ok"


def test_register_and_create_asr_with_params():
    registry = ModelRegistry()
    registry.register_asr("custom", _CustomASR)

    model = registry.create_asr("custom", prefix="!!")
    assert isinstance(model, _CustomASR)
    assert model.prefix == "!!"


def test_create_unknown_asr_raises_with_known_list():
    registry = ModelRegistry()
    registry.register_asr("a", DummyASR)
    registry.register_asr("b", DummyASR)

    with pytest.raises(KeyError) as exc_info:
        registry.create_asr("missing")
    msg = str(exc_info.value)
    assert "asr" in msg
    assert "missing" in msg
    assert "['a', 'b']" in msg


def test_double_registration_raises():
    registry = ModelRegistry()
    registry.register_asr("dummy", DummyASR)
    with pytest.raises(ValueError, match="already registered"):
        registry.register_asr("dummy", DummyASR)


def test_kinds_are_isolated_so_same_name_works_across_kinds():
    registry = ModelRegistry()
    registry.register_asr("dummy", DummyASR)
    registry.register_language("dummy", DummyLanguageModel)
    registry.register_diarization("dummy", DummyDiarization)

    assert isinstance(registry.create_asr("dummy"), ASRModel)
    assert isinstance(registry.create_language("dummy"), LanguageModel)
    assert isinstance(registry.create_diarization("dummy"), DiarizationModel)


def test_list_returns_sorted_names():
    registry = ModelRegistry()
    registry.register_asr("zeta", DummyASR)
    registry.register_asr("alpha", DummyASR)
    assert registry.list_asr() == ["alpha", "zeta"]


def test_default_registry_ships_dummies():
    registry = default_registry()
    assert "dummy" in registry.list_asr()
    assert "dummy" in registry.list_language()
    assert "dummy" in registry.list_diarization()

    asr = registry.create_asr("dummy")
    lid = registry.create_language("dummy", language="ru")
    diar = registry.create_diarization("dummy")

    assert isinstance(asr, ASRModel)
    assert isinstance(lid, LanguageModel)
    assert isinstance(diar, DiarizationModel)
    assert lid.language == "ru"


def test_create_passes_kwargs_through_to_factory():
    registry = default_registry()
    lid = registry.create_language("dummy", language="de")
    assert lid.language == "de"


def test_dummy_name_attribute_matches_registry_key():
    """model.name must equal the key used to register it in default_registry."""
    registry = default_registry()
    assert DummyASR.name == "dummy"
    assert DummyLanguageModel.name == "dummy"
    assert DummyDiarization.name == "dummy"
