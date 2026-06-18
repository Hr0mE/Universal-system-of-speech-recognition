from __future__ import annotations

import logging
from pathlib import Path

import pytest

from core.models.registry import ModelRegistry
from core.pipeline.context import PipelineContext, Segment
from core.pipeline.registry import StageRegistry
from core.pipeline.stage import Stage
from plugins.loader import load_dir_plugins


def _make_registries() -> tuple[ModelRegistry, StageRegistry]:
    return ModelRegistry(), StageRegistry()


def _write_plugin(tmp_path: Path, name: str, content: str) -> Path:
    p = tmp_path / name
    p.write_text(content)
    return p


REGISTER_MODEL_PLUGIN = """\
from core.models.base import ASRModel
from core.pipeline.context import PipelineContext, Segment

class _PluginASR(ASRModel):
    name = "plugin-asr"
    def transcribe(self, segment, context):
        return "plugin"

def register(model_registry, stage_registry):
    model_registry.register_asr("plugin-asr", _PluginASR)
"""

REGISTER_STAGE_PLUGIN = """\
from core.pipeline.context import PipelineContext, Segment
from core.pipeline.stage import Stage

class _PluginStage(Stage):
    name = "plugin-stage"
    def run(self, segments, context):
        return segments

def register(model_registry, stage_registry):
    stage_registry.register("plugin-stage", _PluginStage)
"""

NO_REGISTER_PLUGIN = """\
x = 42
"""

BROKEN_PLUGIN = """\
def register(model_registry, stage_registry):
    raise ImportError("intentional failure")
"""

SYNTAX_ERROR_PLUGIN = """\
def register(
"""


def test_loads_plugin_register_is_called(tmp_path):
    called = []

    plugin_code = f"""\
def register(model_registry, stage_registry):
    called_marker.append(True)
"""
    plugin_file = tmp_path / "my_plugin.py"
    plugin_file.write_text("_sentinel = True\ndef register(m, s): pass\n")

    mr, sr = _make_registries()
    load_dir_plugins(mr, sr, tmp_path)


def test_plugin_registers_model(tmp_path):
    _write_plugin(tmp_path, "model_plugin.py", REGISTER_MODEL_PLUGIN)
    mr, sr = _make_registries()
    load_dir_plugins(mr, sr, tmp_path)

    assert "plugin-asr" in mr.list_asr()


def test_plugin_registers_stage(tmp_path):
    _write_plugin(tmp_path, "stage_plugin.py", REGISTER_STAGE_PLUGIN)
    mr, sr = _make_registries()
    load_dir_plugins(mr, sr, tmp_path)

    assert "plugin-stage" in sr.list()


def test_nonexistent_dir_does_not_crash(tmp_path):
    mr, sr = _make_registries()
    load_dir_plugins(mr, sr, tmp_path / "does_not_exist")


def test_file_without_register_is_skipped(tmp_path):
    _write_plugin(tmp_path, "no_register.py", NO_REGISTER_PLUGIN)
    mr, sr = _make_registries()
    load_dir_plugins(mr, sr, tmp_path)

    assert mr.list_asr() == []
    assert sr.list() == []


def test_runtime_error_in_register_logs_warning(tmp_path, caplog):
    _write_plugin(tmp_path, "broken.py", BROKEN_PLUGIN)
    mr, sr = _make_registries()

    with caplog.at_level(logging.WARNING, logger="plugins.loader"):
        load_dir_plugins(mr, sr, tmp_path)

    assert any("broken.py" in r.message for r in caplog.records)


def test_syntax_error_logs_warning(tmp_path, caplog):
    _write_plugin(tmp_path, "syntax_err.py", SYNTAX_ERROR_PLUGIN)
    mr, sr = _make_registries()

    with caplog.at_level(logging.WARNING, logger="plugins.loader"):
        load_dir_plugins(mr, sr, tmp_path)

    assert any("syntax_err.py" in r.message for r in caplog.records)


def test_only_py_files_loaded(tmp_path):
    (tmp_path / "not_a_plugin.txt").write_text("register = 'not callable'")
    (tmp_path / "compiled.pyc").write_bytes(b"\x00\x01")
    _write_plugin(tmp_path, "real.py", REGISTER_MODEL_PLUGIN)

    mr, sr = _make_registries()
    load_dir_plugins(mr, sr, tmp_path)

    assert mr.list_asr() == ["plugin-asr"]
