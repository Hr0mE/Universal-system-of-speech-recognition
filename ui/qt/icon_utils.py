"""SVG-иконки: загрузка и перекраска под текущую тему.

Themify SVG-файлы содержат hardcoded fill="#000000". Эта утилита заменяет
fill-цвет на нужный перед рендерингом через QSvgRenderer → QIcon.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QByteArray
from PySide6.QtGui import QIcon, QPixmap, QPainter
from PySide6.QtSvg import QSvgRenderer

ICONS_DIR = Path(__file__).parent / "resources" / "icons"


def svg_icon(name: str, color: str = "#E1E1E6", size: int = 16) -> QIcon:
    """Load a Themify SVG icon recolored to the given hex color.

    Args:
        name:  SVG filename without extension (e.g. "folder", "server").
        color: Hex fill color (e.g. "#E1E1E6").
        size:  Square pixel size of the resulting icon.
    """
    path = ICONS_DIR / f"{name}.svg"
    content = path.read_text(encoding="utf-8")
    content = content.replace('fill="#000000"', f'fill="{color}"')
    renderer = QSvgRenderer(QByteArray(content.encode("utf-8")))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)
