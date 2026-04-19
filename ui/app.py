"""Application entry point — QApplication setup and placeholder asset generation."""

import os
import sys

from PyQt6.QtCore import QSettings
from PyQt6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import QApplication

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")

_PLACEHOLDERS = {
    "tree_default.png": (QColor("#F5C518"), 14),
    "tree_selected.png": (QColor("#44CC44"), 20),
    "rock_default.png": (QColor("#C8A46E"), 14),
    "rock_selected.png": (QColor("#66BB66"), 20),
    "alpha_icon.png": (QColor("#FF6600"), 20, "α"),
    "shiny_icon.png": (QColor("#FFD700"), 20, "✦"),
}


def ensure_placeholder_assets():
    os.makedirs(ASSETS_DIR, exist_ok=True)
    try:
        from PyQt6.QtGui import QPixmap
    except Exception:
        return

    for name, spec in _PLACEHOLDERS.items():
        path = os.path.join(ASSETS_DIR, name)
        if os.path.exists(path):
            continue
        color, size = spec[0], spec[1]
        label = spec[2] if len(spec) > 2 else None
        pm = QPixmap(size, size)
        pm.fill(QColor(0, 0, 0, 0))
        p = QPainter(pm)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QBrush(color))
        p.setPen(QPen(color.darker(140), 1))
        p.drawEllipse(1, 1, size - 2, size - 2)
        if label:
            font = QFont()
            font.setPointSize(max(size // 3, 6))
            font.setBold(True)
            p.setFont(font)
            p.setPen(QPen(QColor("white")))
            p.drawText(pm.rect(), 0x84, label)  # AlignCenter
        p.end()
        pm.save(path)


def run():
    app = QApplication(sys.argv)
    app.setApplicationName("LandmarkSeedFinder")
    app.setOrganizationName("LandmarkSeedFinder")

    ensure_placeholder_assets()

    settings = QSettings("LandmarkSeedFinder", "Settings")

    from ui.map_window import MapWindow
    window = MapWindow(settings)
    window.show()
    sys.exit(app.exec())
