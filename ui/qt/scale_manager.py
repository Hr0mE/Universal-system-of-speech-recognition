"""Управление масштабом интерфейса через динамический QSS.

Масштаб применяется без QGraphicsProxyWidget — все px-значения в stylesheet
умножаются на коэффициент через регулярное выражение.  Это сохраняет
полноценную поддержку drag & drop.
"""

from __future__ import annotations

import json
import logging
import os
import re
import tempfile
from pathlib import Path

from PySide6.QtCore import QEvent, QObject, Qt, Signal

_log = logging.getLogger("ui.settings")

_SETTINGS_FILE = Path.home() / ".ussr_diplom" / "ui_settings.json"

SCALE_MIN = 0.6
SCALE_MAX = 2.0
SCALE_DEFAULT = 1.0


def _read_settings() -> dict:
    """Читает файл настроек одним местом. Нет файла → {}; повреждён → {} + предупреждение."""
    try:
        return json.loads(_SETTINGS_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (json.JSONDecodeError, OSError) as exc:
        _log.warning(
            "Файл настроек повреждён или нечитаем (%s) — использую значения по умолчанию", exc
        )
        return {}


def _update_settings(**changes) -> None:
    """Атомарно обновляет настройки: read-modify-write через временный файл + ``os.replace``.

    Атомарная замена защищает от потери всех настроек, если запись прервётся на полпути.
    """
    try:
        _SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = _read_settings()
        data.update(changes)
        fd, tmp = tempfile.mkstemp(
            dir=str(_SETTINGS_FILE.parent), prefix=".ui_settings_", suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            os.replace(tmp, _SETTINGS_FILE)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
    except OSError as exc:
        _log.warning("Не удалось сохранить настройки (%s)", exc)


def load_ui_scale() -> float:
    try:
        return float(_read_settings().get("ui_scale", SCALE_DEFAULT))
    except (TypeError, ValueError):
        return SCALE_DEFAULT


def save_ui_scale(factor: float) -> None:
    _update_settings(ui_scale=round(factor, 3))


def load_ui_theme() -> str:
    theme = str(_read_settings().get("ui_theme", "dark"))
    return theme if theme in ("dark", "light") else "dark"


def save_ui_theme(theme: str) -> None:
    _update_settings(ui_theme=theme)


def load_hf_token() -> str:
    """Читает HuggingFace токен из файла настроек."""
    return str(_read_settings().get("hf_token", ""))


def save_hf_token(token: str) -> None:
    """Сохраняет HuggingFace токен в файл настроек."""
    _update_settings(hf_token=token)


def load_custom_models() -> dict[str, str]:
    """Return {repo_id: model_type} for user-added models (persisted across sessions)."""
    val = _read_settings().get("custom_models", {})
    return dict(val) if isinstance(val, dict) else {}


def save_custom_models(models: dict[str, str]) -> None:
    """Persist {repo_id: model_type} for user-added models."""
    _update_settings(custom_models=models)


def scale_qss(qss: str, scale: float) -> str:
    """Умножает все ненулевые px-значения в строке QSS на ``scale``."""
    if abs(scale - 1.0) < 0.001:
        return qss

    def _replace(m: re.Match) -> str:
        val = int(m.group(1))
        return "0px" if val == 0 else f"{max(1, int(val * scale))}px"

    return re.sub(r"(\d+)px", _replace, qss)


class CtrlWheelZoomFilter(QObject):
    """Перехватывает Ctrl + колёсико мыши / тачпад на уровне QApplication.

    При установке через ``QApplication.installEventFilter(filter)``
    перехватывает все QWheelEvent с зажатым Ctrl и эмитирует сигналы
    масштабирования вместо того, чтобы прокручивать виджет.
    """

    zoom_in_requested  = Signal()
    zoom_out_requested = Signal()

    def eventFilter(self, _obj: QObject, event) -> bool:  # type: ignore[override]
        if event.type() == QEvent.Type.Wheel:
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                delta = event.angleDelta().y()
                if delta > 0:
                    self.zoom_in_requested.emit()
                elif delta < 0:
                    self.zoom_out_requested.emit()
                return True  # consume — не прокручивать виджет
        return False
