"""Управление масштабом интерфейса через динамический QSS.

Масштаб применяется без QGraphicsProxyWidget — все px-значения в stylesheet
умножаются на коэффициент через регулярное выражение.  Это сохраняет
полноценную поддержку drag & drop.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from PySide6.QtCore import QEvent, QObject, Qt, Signal

_SETTINGS_FILE = Path.home() / ".ussr_diplom" / "ui_settings.json"

SCALE_MIN = 0.6
SCALE_MAX = 2.0
SCALE_DEFAULT = 1.0


def load_ui_scale() -> float:
    try:
        data = json.loads(_SETTINGS_FILE.read_text(encoding="utf-8"))
        return float(data.get("ui_scale", SCALE_DEFAULT))
    except Exception:
        return SCALE_DEFAULT


def save_ui_scale(factor: float) -> None:
    try:
        _SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        existing: dict = {}
        if _SETTINGS_FILE.exists():
            try:
                existing = json.loads(_SETTINGS_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass
        existing["ui_scale"] = round(factor, 3)
        _SETTINGS_FILE.write_text(json.dumps(existing, indent=2), encoding="utf-8")
    except Exception:
        pass


def load_ui_theme() -> str:
    try:
        data = json.loads(_SETTINGS_FILE.read_text(encoding="utf-8"))
        theme = str(data.get("ui_theme", "dark"))
        return theme if theme in ("dark", "light") else "dark"
    except Exception:
        return "dark"


def save_ui_theme(theme: str) -> None:
    try:
        _SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        existing: dict = {}
        if _SETTINGS_FILE.exists():
            try:
                existing = json.loads(_SETTINGS_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass
        existing["ui_theme"] = theme
        _SETTINGS_FILE.write_text(json.dumps(existing, indent=2), encoding="utf-8")
    except Exception:
        pass


def load_hf_token() -> str:
    """Читает HuggingFace токен из файла настроек."""
    try:
        data = json.loads(_SETTINGS_FILE.read_text(encoding="utf-8"))
        return str(data.get("hf_token", ""))
    except Exception:
        return ""


def save_hf_token(token: str) -> None:
    """Сохраняет HuggingFace токен в файл настроек."""
    try:
        _SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        existing: dict = {}
        if _SETTINGS_FILE.exists():
            try:
                existing = json.loads(_SETTINGS_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass
        existing["hf_token"] = token
        _SETTINGS_FILE.write_text(json.dumps(existing, indent=2), encoding="utf-8")
    except Exception:
        pass


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
