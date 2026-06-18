from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import pytest

from core.models.base import ASRModel
from core.models.registry import ModelRegistry
from core.pipeline.context import PipelineContext, Segment
from core.pipeline.registry import StageRegistry
from plugins.loader import load_entrypoint_plugins

_GROUP = "ussr_diplom.plugins"


def _make_registries() -> tuple[ModelRegistry, StageRegistry]:
    return ModelRegistry(), StageRegistry()


class _FakeASR(ASRModel):
    name = "ep-asr"

    def transcribe(self, segment: Segment, context: PipelineContext) -> str:
        return "ep"


def _ep_register(model_registry: ModelRegistry, stage_registry: StageRegistry) -> None:
    model_registry.register_asr("ep-asr", _FakeASR)


def test_no_entrypoints_does_not_crash():
    mr, sr = _make_registries()
    with patch("importlib.metadata.entry_points", return_value=[]):
        load_entrypoint_plugins(mr, sr)


def test_entrypoint_register_fn_is_called():
    mr, sr = _make_registries()
    mock_fn = MagicMock()
    ep = MagicMock()
    ep.load.return_value = mock_fn

    with patch("importlib.metadata.entry_points", return_value=[ep]):
        load_entrypoint_plugins(mr, sr)

    mock_fn.assert_called_once_with(mr, sr)


def test_model_registered_via_entrypoint():
    mr, sr = _make_registries()
    ep = MagicMock()
    ep.load.return_value = _ep_register

    with patch("importlib.metadata.entry_points", return_value=[ep]):
        load_entrypoint_plugins(mr, sr)

    assert "ep-asr" in mr.list_asr()


def test_broken_entrypoint_load_logs_warning(caplog):
    mr, sr = _make_registries()
    ep = MagicMock()
    ep.name = "broken-ep"
    ep.load.side_effect = ImportError("missing dep")

    with patch("importlib.metadata.entry_points", return_value=[ep]):
        with caplog.at_level(logging.WARNING, logger="plugins.loader"):
            load_entrypoint_plugins(mr, sr)

    assert any("broken-ep" in r.message for r in caplog.records)


def test_broken_entrypoint_register_logs_warning(caplog):
    mr, sr = _make_registries()

    def _raise(model_registry, stage_registry):
        raise RuntimeError("oops")

    ep = MagicMock()
    ep.name = "failing-ep"
    ep.load.return_value = _raise

    with patch("importlib.metadata.entry_points", return_value=[ep]):
        with caplog.at_level(logging.WARNING, logger="plugins.loader"):
            load_entrypoint_plugins(mr, sr)

    assert any("failing-ep" in r.message for r in caplog.records)


def test_custom_group_is_passed_to_entry_points():
    mr, sr = _make_registries()
    with patch("importlib.metadata.entry_points", return_value=[]) as mock_ep:
        load_entrypoint_plugins(mr, sr, group="my.custom.group")

    mock_ep.assert_called_once_with(group="my.custom.group")
