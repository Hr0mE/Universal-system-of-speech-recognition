from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.hf_catalog import CatalogModel, is_cached, list_local_models, search_models


# ── CatalogModel ─────────────────────────────────────────────────────────────

def test_catalog_model_fields():
    m = CatalogModel(
        repo_id="Systran/faster-whisper-small",
        downloads=12345,
        languages=["en", "ru"],
        pipeline_tag="automatic-speech-recognition",
        cached=False,
    )
    assert m.repo_id == "Systran/faster-whisper-small"
    assert m.downloads == 12345
    assert m.languages == ["en", "ru"]
    assert m.pipeline_tag == "automatic-speech-recognition"
    assert m.cached is False


# ── search_models ─────────────────────────────────────────────────────────────

def _make_hf_model(repo_id: str, downloads: int = 0, tags: list[str] | None = None):
    m = MagicMock()
    m.id = repo_id
    m.downloads = downloads
    m.tags = tags or []
    return m


def test_search_models_returns_list():
    fake_models = [
        _make_hf_model("org/model-a", 1000, ["en"]),
        _make_hf_model("org/model-b", 500, ["ru"]),
    ]
    with patch("core.hf_catalog.list_models", return_value=iter(fake_models)):
        results = search_models("automatic-speech-recognition")
    assert len(results) == 2
    assert all(isinstance(r, CatalogModel) for r in results)
    assert results[0].repo_id == "org/model-a"
    assert results[0].downloads == 1000


def test_search_models_network_error_returns_empty():
    with patch("core.hf_catalog.list_models", side_effect=Exception("Network error")):
        results = search_models("automatic-speech-recognition")
    assert results == []


def test_search_models_401_returns_empty():
    with patch("core.hf_catalog.list_models", side_effect=Exception("401 Unauthorized")):
        results = search_models("automatic-speech-recognition", token="bad-token")
    assert results == []


def test_search_models_passes_language_filter():
    with patch("core.hf_catalog.list_models", return_value=iter([])) as mock_list:
        search_models("automatic-speech-recognition", language="ru")
    call_kwargs = mock_list.call_args[1]
    assert call_kwargs.get("filter") == "ru"  # list_models uses filter= not language=


# ── is_cached ────────────────────────────────────────────────────────────────

def test_is_cached_true_when_fully_downloaded(tmp_path, monkeypatch):
    # is_cached считает модель скачанной только когда HF записал refs/main
    # (полный snapshot), а не просто создал директорию.
    monkeypatch.setattr("core.hf_catalog._HF_CACHE_ROOT", tmp_path)
    refs_main = tmp_path / "models--Systran--faster-whisper-tiny" / "refs" / "main"
    refs_main.parent.mkdir(parents=True)
    refs_main.write_text("0123abcd")
    assert is_cached("Systran/faster-whisper-tiny") is True


def test_is_cached_false_for_partial_download(tmp_path, monkeypatch):
    # Директория есть (snapshot_download создаёт её сразу), но refs/main ещё нет
    # → загрузка не завершена → не cached.
    monkeypatch.setattr("core.hf_catalog._HF_CACHE_ROOT", tmp_path)
    (tmp_path / "models--Systran--faster-whisper-tiny").mkdir()
    assert is_cached("Systran/faster-whisper-tiny") is False


def test_is_cached_false_when_dir_missing(tmp_path, monkeypatch):
    monkeypatch.setattr("core.hf_catalog._HF_CACHE_ROOT", tmp_path)
    assert is_cached("Systran/faster-whisper-missing") is False


# ── list_local_models ─────────────────────────────────────────────────────────

def test_list_local_models_returns_subdirs(tmp_path):
    (tmp_path / "faster-whisper-tiny").mkdir()
    (tmp_path / "faster-whisper-small").mkdir()
    (tmp_path / "not-a-dir.txt").write_text("file")
    result = list_local_models(tmp_path)
    assert set(result) == {"faster-whisper-tiny", "faster-whisper-small"}


def test_list_local_models_empty_dir(tmp_path):
    assert list_local_models(tmp_path) == []


def test_list_local_models_missing_dir(tmp_path):
    missing = tmp_path / "nonexistent"
    assert list_local_models(missing) == []
