"""Тесты хранилища пользовательских настроек (ui/qt/scale_manager.py).

Покрывают централизованные хелперы read-modify-write: roundtrip, сохранение чужих
ключей при частичном апдейте, атомарность записи и устойчивость к битому файлу.
"""

from __future__ import annotations

import json

import pytest

from ui.qt import scale_manager as sm


@pytest.fixture()
def settings_file(tmp_path, monkeypatch):
    """Перенаправляет хранилище настроек во временный файл на время теста."""
    path = tmp_path / "ui_settings.json"
    monkeypatch.setattr(sm, "_SETTINGS_FILE", path)
    return path


def test_scale_roundtrip(settings_file):
    sm.save_ui_scale(1.25)
    assert sm.load_ui_scale() == 1.25


def test_theme_roundtrip_and_validation(settings_file):
    sm.save_ui_theme("light")
    assert sm.load_ui_theme() == "light"
    # неизвестная тема → откат к "dark"
    sm.save_ui_theme("neon")
    assert sm.load_ui_theme() == "dark"


def test_token_and_custom_models_roundtrip(settings_file):
    sm.save_hf_token("hf_secret")
    sm.save_custom_models({"org/model": "asr"})
    assert sm.load_hf_token() == "hf_secret"
    assert sm.load_custom_models() == {"org/model": "asr"}


def test_partial_update_preserves_other_keys(settings_file):
    """Сохранение одного ключа не должно затирать остальные (read-modify-write)."""
    sm.save_ui_scale(1.5)
    sm.save_ui_theme("light")
    sm.save_hf_token("tok")

    data = json.loads(settings_file.read_text(encoding="utf-8"))
    assert data == {"ui_scale": 1.5, "ui_theme": "light", "hf_token": "tok"}


def test_atomic_write_leaves_no_temp_files(settings_file):
    sm.save_ui_scale(0.8)
    leftovers = list(settings_file.parent.glob(".ui_settings_*.tmp"))
    assert leftovers == [], f"остались временные файлы: {leftovers}"


def test_corrupt_file_falls_back_to_defaults(settings_file):
    settings_file.write_text("{ this is not json", encoding="utf-8")
    assert sm._read_settings() == {}
    assert sm.load_ui_scale() == sm.SCALE_DEFAULT
    assert sm.load_ui_theme() == "dark"
    assert sm.load_custom_models() == {}


def test_missing_file_returns_defaults(settings_file):
    assert not settings_file.exists()
    assert sm.load_ui_scale() == sm.SCALE_DEFAULT
    assert sm.load_hf_token() == ""
    assert sm.load_custom_models() == {}


def test_save_recovers_after_corruption(settings_file):
    """Битый файл не должен мешать последующему сохранению (перезапишется валидным)."""
    settings_file.write_text("garbage", encoding="utf-8")
    sm.save_ui_theme("light")
    assert sm.load_ui_theme() == "light"
    # файл снова валидный JSON
    assert json.loads(settings_file.read_text(encoding="utf-8"))["ui_theme"] == "light"
