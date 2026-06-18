from __future__ import annotations

from pathlib import Path

import pytest

from core.models.registry import ModelRegistry
from core.pipeline.registry import StageRegistry
from plugins import PLUGINS_DIR, setup_plugins

_PLUGIN_CODE = """\
from core.models.base import ASRModel

class _IntegASR(ASRModel):
    name = "integ-asr"
    def transcribe(self, segment, context):
        return "integ"

def register(model_registry, stage_registry):
    model_registry.register_asr("integ-asr", _IntegASR)
"""


def test_default_plugins_dir_is_plugins_folder():
    project_root = Path(__file__).parent.parent
    assert PLUGINS_DIR == project_root / "plugins"


def test_setup_plugins_loads_from_dir(tmp_path):
    (tmp_path / "integ_plugin.py").write_text(_PLUGIN_CODE)

    mr = ModelRegistry()
    sr = StageRegistry()
    setup_plugins(mr, sr, plugins_dir=tmp_path)

    assert "integ-asr" in mr.list_asr()


def test_setup_plugins_also_loads_entrypoints(tmp_path, monkeypatch):
    registered = []

    def _fake_fn(mr, sr):
        registered.append(True)

    fake_ep = type("EP", (), {"load": staticmethod(lambda: _fake_fn), "name": "fake"})()

    monkeypatch.setattr(
        "importlib.metadata.entry_points",
        lambda group: [fake_ep],
    )

    mr = ModelRegistry()
    sr = StageRegistry()
    setup_plugins(mr, sr, plugins_dir=tmp_path)

    assert registered == [True]


def test_setup_plugins_default_plugins_dir_used_when_not_specified():
    """setup_plugins() without plugins_dir arg uses PLUGINS_DIR (project/plugins/)."""
    mr = ModelRegistry()
    sr = StageRegistry()
    # Should not raise even if plugins/ dir has no .py plugins yet
    setup_plugins(mr, sr)
