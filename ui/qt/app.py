"""Точка входа GUI-приложения.

Настраивает логирование, создаёт QApplication и запускает главное окно.
"""

from __future__ import annotations

import logging
import os
import sys
import threading
from logging.handlers import RotatingFileHandler
from pathlib import Path


def _setup_logging() -> None:
    """Настраивает логирование в stderr и файл ``transcription_gui.log``.

    Файл пишется на уровне INFO с ротацией (чтобы не рос без предела); консоль —
    INFO по умолчанию и DEBUG только при ``USSR_DEBUG=1``.
    """
    log_path = Path("transcription_gui.log")
    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

    console = logging.StreamHandler(sys.stderr)
    console.setLevel(logging.DEBUG if os.environ.get("USSR_DEBUG") else logging.INFO)

    file_handler = RotatingFileHandler(
        log_path, maxBytes=2_000_000, backupCount=3, encoding="utf-8"
    )
    file_handler.setLevel(logging.INFO)

    logging.basicConfig(level=logging.DEBUG, format=fmt, handlers=[console, file_handler])
    logging.getLogger("ui").setLevel(logging.DEBUG)
    logging.getLogger("core").setLevel(logging.DEBUG)
    log = logging.getLogger("ui.app")
    log.info("Логирование запущено → %s", log_path.resolve())


from PySide6.QtWidgets import QApplication, QMessageBox

from ui.qt.main_window import MainWindow
from ui.qt.theme import apply_theme


def _install_excepthook() -> None:
    """Перехватывает необработанные исключения: пишет их в лог и показывает пользователю.

    Без этого исключение в слоте/обработчике UI-потока пропадает в stderr или роняет
    процесс без следа в ``transcription_gui.log``. Воркеры обрабатывают свои ошибки сами —
    здесь страхуется главный поток и прочие (не-Qt) потоки.
    """
    log = logging.getLogger("ui.excepthook")

    def _hook(exc_type, exc, tb) -> None:
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc, tb)
            return
        log.critical("Необработанное исключение", exc_info=(exc_type, exc, tb))
        if QApplication.instance() is not None:
            QMessageBox.critical(
                None,
                "Внутренняя ошибка",
                f"{exc_type.__name__}: {exc}\n\n"
                "Подробности записаны в transcription_gui.log.",
            )

    sys.excepthook = _hook

    def _thread_hook(args: threading.ExceptHookArgs) -> None:
        if issubclass(args.exc_type, KeyboardInterrupt):
            return
        name = args.thread.name if args.thread is not None else "?"
        log.critical(
            "Необработанное исключение в потоке %s",
            name,
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
        )

    threading.excepthook = _thread_hook


def main() -> None:
    """Инициализирует и запускает GUI-приложение.

    Настраивает логирование, применяет тему, создаёт и отображает главное окно.
    Вызов ``sys.exit`` с кодом QApplication.exec() завершает процесс.
    """
    _setup_logging()
    _install_excepthook()
    app = QApplication(sys.argv)
    apply_theme(app)
    window = MainWindow()
    window.show()
    exit_code = app.exec()
    logging.shutdown()
    os._exit(exit_code)
