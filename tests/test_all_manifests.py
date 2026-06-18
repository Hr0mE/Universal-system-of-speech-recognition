from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from plugins import BUILTIN_MANIFESTS, all_manifests
from plugins.loader import collect_entrypoint_manifests
from plugins.manifest import PluginManifest
from plugins.timestamp_asr import describe as timestamp_describe


# ------------------------------------------------------------------
# all_manifests()
# ------------------------------------------------------------------

def test_all_manifests_includes_all_builtins(tmp_path: Path) -> None:
    result = all_manifests(tmp_path)  # пустая tmp_path — только встроенные и entry_points
    builtin_names = {m.name for m in BUILTIN_MANIFESTS}
    result_names = {m.name for m in result}
    assert builtin_names.issubset(result_names)


def test_all_manifests_deduplicates_by_name(tmp_path: Path) -> None:
    names = [m.name for m in all_manifests(tmp_path)]
    assert len(names) == len(set(names))


def test_all_manifests_includes_file_plugin(tmp_path: Path) -> None:
    (tmp_path / "my_plugin.py").write_text(
        "from plugins.manifest import PluginManifest\n"
        "def describe():\n"
        "    return PluginManifest(name='my-plugin', model_type='asr')\n"
        "def register(mr, sr): pass\n"
    )
    result = all_manifests(tmp_path)
    assert any(m.name == "my-plugin" for m in result)


def test_all_manifests_builtin_wins_over_file_plugin(tmp_path: Path) -> None:
    first_builtin = BUILTIN_MANIFESTS[0]
    (tmp_path / "dup.py").write_text(
        "from plugins.manifest import PluginManifest\n"
        f"def describe():\n"
        f"    return PluginManifest(name='{first_builtin.name}', model_type='asr', description='override')\n"
        "def register(mr, sr): pass\n"
    )
    result = all_manifests(tmp_path)
    found = next(m for m in result if m.name == first_builtin.name)
    assert found.description == first_builtin.description  # встроенный не перезаписан


# ------------------------------------------------------------------
# collect_entrypoint_manifests()
# ------------------------------------------------------------------

def test_collect_entrypoint_manifests_returns_empty_for_unknown_group() -> None:
    result = collect_entrypoint_manifests(group="nonexistent.group.xyz")
    assert result == []


def test_collect_entrypoint_manifests_skips_module_without_describe() -> None:
    import types
    fake_module = types.ModuleType("fake_no_describe")
    # нет атрибута describe

    class FakeEP:
        value = "fake_no_describe:register"
        name = "fake"

    with patch("importlib.metadata.entry_points", return_value=[FakeEP()]), \
         patch("importlib.import_module", return_value=fake_module):
        result = collect_entrypoint_manifests()
    assert result == []


def test_collect_entrypoint_manifests_returns_manifest_when_describe_present() -> None:
    import types
    fake_module = types.ModuleType("fake_with_describe")
    fake_module.describe = lambda: PluginManifest(name="ep-plugin", model_type="asr")  # type: ignore[attr-defined]

    class FakeEP:
        value = "fake_with_describe:register"
        name = "fake"

    with patch("importlib.metadata.entry_points", return_value=[FakeEP()]), \
         patch("importlib.import_module", return_value=fake_module):
        result = collect_entrypoint_manifests()
    assert len(result) == 1
    assert result[0].name == "ep-plugin"


# ------------------------------------------------------------------
# timestamp_asr.describe()
# ------------------------------------------------------------------

def test_timestamp_asr_has_describe() -> None:
    manifest = timestamp_describe()
    assert isinstance(manifest, PluginManifest)
    assert manifest.model_type == "asr"
    assert "fmt" in manifest.params_schema
