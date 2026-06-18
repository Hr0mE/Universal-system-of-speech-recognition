"""Точка входа GUI-приложения.

Настраивает логирование, создаёт QApplication и запускает главное окно.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path


def _setup_logging() -> None:
    """Настраивает логирование в stderr и файл ``transcription_gui.log``."""
    log_path = Path("transcription_gui.log")
    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    handlers: list[logging.Handler] = [
        logging.StreamHandler(sys.stderr),
        logging.FileHandler(log_path, encoding="utf-8"),
    ]
    logging.basicConfig(level=logging.DEBUG, format=fmt, handlers=handlers)
    logging.getLogger("ui").setLevel(logging.DEBUG)
    logging.getLogger("core").setLevel(logging.DEBUG)
    log = logging.getLogger("ui.app")
    log.info("Логирование запущено → %s", log_path.resolve())


from PySide6.QtWidgets import QApplication

from ui.qt.main_window import MainWindow
from ui.qt.theme import apply_theme


def main() -> None:
    """Инициализирует и запускает GUI-приложение.

    Настраивает логирование, применяет тему, создаёт и отображает главное окно.
    Вызов ``sys.exit`` с кодом QApplication.exec() завершает процесс.
    """
    _setup_logging()
    app = QApplication(sys.argv)
    apply_theme(app)
    window = MainWindow()
    window.show()
    exit_code = app.exec()
    logging.shutdown()
    os._exit(exit_code)
