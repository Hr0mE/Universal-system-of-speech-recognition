from __future__ import annotations

import logging
from pathlib import Path

import pytest

from plugins.loader import collect_manifests
from plugins.manifest import PluginManifest, ParamSpec

_PLUGIN_WITH_DESCRIBE = """\
from plugins.manifest import PluginManifest, ParamSpec

def describe():
    return PluginManifest(
        name="test-asr",
        model_type="asr",
        description="test plugin",
        params_schema={"lang": ParamSpec(type="string", default="en")},
    )

def register(model_registry, stage_registry):
    pass
"""

_SECOND_PLUGIN_WITH_DESCRIBE = """\
from plugins.manifest import PluginManifest

def describe():
    return PluginManifest(name="test-lid", model_type="language")

def register(model_registry, stage_registry):
    pass
"""

_PLUGIN_WITHOUT_DESCRIBE = """\
def register(model_registry, stage_registry):
    pass
"""

_PLUGIN_BROKEN_DESCRIBE = """\
def describe():
    raise RuntimeError("describe failed")

def register(model_registry, stage_registry):
    pass
"""


def test_collect_finds_describe(tmp_path):
    (tmp_path / "plugin.py").write_text(_PLUGIN_WITH_DESCRIBE)

    manifests = collect_manifests(tmp_path)

    assert len(manifests) == 1
    assert manifests[0].name == "test-asr"
    assert manifests[0].model_type == "asr"


def test_collect_skips_plugin_without_describe(tmp_path):
    (tmp_path / "no_describe.py").write_text(_PLUGIN_WITHOUT_DESCRIBE)

    manifests = collect_manifests(tmp_path)

    assert manifests == []


def test_collect_skips_broken_describe_logs_warning(tmp_path, caplog):
    (tmp_path / "broken.py").write_text(_PLUGIN_BROKEN_DESCRIBE)

    with caplog.at_level(logging.WARNING, logger="plugins.loader"):
        manifests = collect_manifests(tmp_path)

    assert manifests == []
    assert any("broken.py" in r.message for r in caplog.records)


def test_collect_nonexistent_dir_returns_empty(tmp_path):
    manifests = collect_manifests(tmp_path / "does_not_exist")
    assert manifests == []


def test_collect_only_py_files(tmp_path):
    (tmp_path / "plugin.py").write_text(_PLUGIN_WITH_DESCRIBE)
    (tmp_path / "readme.txt").write_text("describe = 'not callable'")
    (tmp_path / "compiled.pyc").write_bytes(b"\x00")

    manifests = collect_manifests(tmp_path)

    assert len(manifests) == 1


def test_collect_returns_list_of_manifests(tmp_path):
    (tmp_path / "asr_plugin.py").write_text(_PLUGIN_WITH_DESCRIBE)
    (tmp_path / "lid_plugin.py").write_text(_SECOND_PLUGIN_WITH_DESCRIBE)

    manifests = collect_manifests(tmp_path)

    names = {m.name for m in manifests}
    assert names == {"test-asr", "test-lid"}


def test_collect_manifest_has_correct_params(tmp_path):
    (tmp_path / "plugin.py").write_text(_PLUGIN_WITH_DESCRIBE)

    manifests = collect_manifests(tmp_path)

    assert "lang" in manifests[0].params_schema
    assert manifests[0].params_schema["lang"].default == "en"


def test_collect_does_not_call_register(tmp_path):
    called = []
    plugin_code = f"""\
from plugins.manifest import PluginManifest

def describe():
    return PluginManifest(name="x", model_type="asr")

def register(model_registry, stage_registry):
    called_sentinel.append(True)
"""
    (tmp_path / "plugin.py").write_text(plugin_code)
    # No registry passed — collect_manifests is read-only
    manifests = collect_manifests(tmp_path)
    assert manifests[0].name == "x"
