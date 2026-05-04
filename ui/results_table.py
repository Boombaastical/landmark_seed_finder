"""Results table — displays AdvanceResult rows with icon columns."""

import os

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QHeaderView, QTableWidget, QTableWidgetItem

from core.landmark_loader import get_name_en
from core.seed_finder import AdvanceResult

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")

_COLUMNS = [
    "Advance", "Landmark #", "Landmark Code", "Species", "Gender", "α", "✦",
    "HP", "Atk", "Def", "SpA", "SpD", "Spe",
    "Level", "Ability", "Nature", "Height", "Weight",
]

_COL_ADVANCE = 0
_COL_LANDMARK = 1
_COL_LANDMARK_CODE = 2
_COL_SPECIES = 3
_COL_GENDER = 4
_COL_ALPHA = 5
_COL_SHINY = 6
_COL_HP = 7
_COL_ATK = 8
_COL_DEF = 9
_COL_SPA = 10
_COL_SPD = 11
_COL_SPE = 12
_COL_LEVEL = 13
_COL_ABILITY = 14
_COL_NATURE = 15
_COL_HEIGHT = 16
_COL_WEIGHT = 17


class _NumericItem(QTableWidgetItem):
    def __lt__(self, other):
        mine = self.data(Qt.ItemDataRole.UserRole)
        theirs = other.data(Qt.ItemDataRole.UserRole)
        if mine is not None and theirs is not None:
            return mine < theirs
        return super().__lt__(other)


def _cell(text: str, align=Qt.AlignmentFlag.AlignCenter) -> QTableWidgetItem:
    item = QTableWidgetItem(str(text))
    item.setTextAlignment(align)
    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
    return item


def _ncell(value, align=Qt.AlignmentFlag.AlignCenter) -> _NumericItem:
    item = _NumericItem(str(value))
    item.setData(Qt.ItemDataRole.UserRole, int(value))
    item.setTextAlignment(align)
    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
    return item


class ResultsTable(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(0, len(_COLUMNS), parent)
        self.setHorizontalHeaderLabels(_COLUMNS)

        hdr = self.horizontalHeader()
        for col in (_COL_ALPHA, _COL_SHINY):
            self.setColumnWidth(col, 28)
            hdr.setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(_COL_SPECIES, QHeaderView.ResizeMode.Stretch)
        for col in (_COL_ADVANCE, _COL_LANDMARK, _COL_LANDMARK_CODE, _COL_GENDER, _COL_LEVEL,
                    _COL_ABILITY, _COL_NATURE, _COL_HEIGHT, _COL_WEIGHT):
            hdr.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        for col in (_COL_HP, _COL_ATK, _COL_DEF, _COL_SPA, _COL_SPD, _COL_SPE):
            self.setColumnWidth(col, 36)
            hdr.setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)

        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(
            self.SelectionBehavior.SelectRows
        )
        self.setSortingEnabled(True)

        self._alpha_icon = self._load_icon("alpha_icon.png")
        self._shiny_icon = self._load_icon("shiny_icon.png")

    def _load_icon(self, name: str):
        path = os.path.join(ASSETS_DIR, name)
        if os.path.exists(path):
            return QPixmap(path).scaled(
                20, 20,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        return None

    def clear_results(self):
        self.setSortingEnabled(False)
        self.setRowCount(0)
        self.setSortingEnabled(True)

    def add_row(self, r: AdvanceResult):
        self.setSortingEnabled(False)
        row = self.rowCount()
        self.insertRow(row)

        self.setItem(row, _COL_ADVANCE, _ncell(r.advance))
        self.setItem(row, _COL_LANDMARK, _ncell(r.catch_order + 1))
        self.setItem(row, _COL_LANDMARK_CODE, _cell(r.identifier))
        self.setItem(
            row,
            _COL_SPECIES,
            _cell(get_name_en(r.species, r.form, r.is_alpha), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
        )
        self.setItem(row, _COL_GENDER, _cell(r.gender))

        # Alpha icon column
        alpha_item = QTableWidgetItem()
        alpha_item.setFlags(alpha_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        if r.is_alpha and self._alpha_icon:
            alpha_item.setData(Qt.ItemDataRole.DecorationRole, self._alpha_icon)
        elif r.is_alpha:
            alpha_item.setText("α")
        self.setItem(row, _COL_ALPHA, alpha_item)

        # Shiny icon column
        shiny_item = QTableWidgetItem()
        shiny_item.setFlags(shiny_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        if r.is_shiny and self._shiny_icon:
            shiny_item.setData(Qt.ItemDataRole.DecorationRole, self._shiny_icon)
        elif r.is_shiny:
            shiny_item.setText("✦")
        self.setItem(row, _COL_SHINY, shiny_item)

        for col_offset, iv in enumerate(r.ivs):
            self.setItem(row, _COL_HP + col_offset, _ncell(iv))

        self.setItem(row, _COL_LEVEL, _ncell(r.level))
        self.setItem(row, _COL_ABILITY, _ncell(r.ability))
        self.setItem(
            row,
            _COL_NATURE,
            _cell(r.nature, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
        )
        self.setItem(row, _COL_HEIGHT, _ncell(r.height))
        self.setItem(row, _COL_WEIGHT, _ncell(r.weight))

        self.setSortingEnabled(True)
