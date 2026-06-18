"""GUI-точка входа приложения транскрибации.

Запускает графический интерфейс PySide6.
Для CLI-режима используйте ``python main.py``.
"""

from __future__ import annotations

from ui.qt.app import main

if __name__ == "__main__":
    main()
