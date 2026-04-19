"""Settings dialog — preferences, research levels, and search defaults."""

import os

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.landmark_loader import get_all_landmark_species, get_name_en


class SettingsDialog(QDialog):
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("Settings")
        self.setMinimumSize(520, 680)

        layout = QVBoxLayout(self)

        # --- Search defaults group ---
        defaults_box = QGroupBox("Search Defaults")
        defaults_layout = QVBoxLayout(defaults_box)

        adv_row = QHBoxLayout()
        adv_row.addWidget(QLabel("Max advances:"))
        self.max_advances_spin = QSpinBox()
        self.max_advances_spin.setRange(1, 999999)
        self.max_advances_spin.setValue(
            self.settings.value("max_advances_default", 3000, int)
        )
        adv_row.addWidget(self.max_advances_spin)
        adv_row.addStretch()
        defaults_layout.addLayout(adv_row)

        always_filter_row = QHBoxLayout()
        always_filter_row.addWidget(QLabel("Always search for:"))
        self.always_filter_combo = QComboBox()
        self.always_filter_combo.addItems(["Trees and Rocks", "Trees", "Rocks"])
        filter_map = {"both": 0, "trees": 1, "rocks": 2}
        saved_filter = self.settings.value("landmark_filter", "both")
        self.always_filter_combo.setCurrentIndex(filter_map.get(saved_filter, 0))
        always_filter_row.addWidget(self.always_filter_combo)
        always_filter_row.addStretch()
        defaults_layout.addLayout(always_filter_row)

        self.always_shiny_check = QCheckBox("Always search for shiny Pokémon")
        self.always_shiny_check.setChecked(
            self.settings.value("always_shiny", False, bool)
        )
        defaults_layout.addWidget(self.always_shiny_check)

        self.always_alpha_check = QCheckBox("Always search for alpha Pokémon")
        self.always_alpha_check.setChecked(
            self.settings.value("always_alpha", False, bool)
        )
        defaults_layout.addWidget(self.always_alpha_check)

        gap_row = QHBoxLayout()
        self.preset_gap_check = QCheckBox("Preset max gap:")
        self.preset_gap_check.setChecked(
            self.settings.value("preset_max_gap_enabled", False, bool)
        )
        gap_row.addWidget(self.preset_gap_check)
        self.preset_gap_spin = QSpinBox()
        self.preset_gap_spin.setRange(2, 8)
        self.preset_gap_spin.setValue(
            self.settings.value("preset_max_gap", 4, int)
        )
        self.preset_gap_spin.setEnabled(self.preset_gap_check.isChecked())
        gap_row.addWidget(self.preset_gap_spin)
        gap_row.addStretch()
        defaults_layout.addLayout(gap_row)
        self.preset_gap_check.toggled.connect(self.preset_gap_spin.setEnabled)

        # Save .txt checkbox only
        self.save_txt_check = QCheckBox("Save a .txt file of results when generating")
        self.save_txt_check.setChecked(
            self.settings.value("save_txt_file", False, bool)
        )
        defaults_layout.addWidget(self.save_txt_check)

        # pa8 download folder
        dl_row = QHBoxLayout()
        dl_row.addWidget(QLabel(".pa8 download folder:"))
        self.pa8_download_edit = QLineEdit()
        self.pa8_download_edit.setText(
            os.path.expanduser(self.settings.value("pa8_download_folder", "~/Downloads"))
        )
        dl_row.addWidget(self.pa8_download_edit)
        dl_browse_btn = QPushButton("Browse…")
        dl_browse_btn.clicked.connect(self._browse_pa8_download)
        dl_row.addWidget(dl_browse_btn)
        defaults_layout.addLayout(dl_row)

        # pa8 storage folder (label updates with save_txt toggle)
        self._storage_label = QLabel(self._storage_label_text())
        st_row = QHBoxLayout()
        st_row.addWidget(self._storage_label)
        self.pa8_storage_edit = QLineEdit()
        self.pa8_storage_edit.setPlaceholderText("Batch output folder…")
        self.pa8_storage_edit.setText(
            os.path.expanduser(self.settings.value("pa8_storage_folder", "~/Downloads"))
        )
        st_row.addWidget(self.pa8_storage_edit)
        st_browse_btn = QPushButton("Browse…")
        st_browse_btn.clicked.connect(self._browse_pa8_storage)
        st_row.addWidget(st_browse_btn)
        defaults_layout.addLayout(st_row)

        self.save_txt_check.toggled.connect(self._on_save_txt_toggled)

        layout.addWidget(defaults_box)

        # --- Research levels group ---
        research_box = QGroupBox("Species Research Levels")
        research_layout = QVBoxLayout(research_box)

        bottom_row = QHBoxLayout()
        self.charm_check = QCheckBox("Shiny Charm")
        self.charm_check.setChecked(
            self.settings.value("shiny_charm", False, bool)
        )
        self.charm_check.toggled.connect(self._on_charm_toggled)
        bottom_row.addWidget(self.charm_check)
        bottom_row.addStretch()
        bottom_row.addWidget(QLabel("Change all to:"))
        self.change_all_combo = QComboBox()
        self.change_all_combo.currentIndexChanged.connect(self._change_all_research)
        bottom_row.addWidget(self.change_all_combo)
        research_layout.addLayout(bottom_row)

        self.species_table = QTableWidget()
        self.species_table.setColumnCount(2)
        self.species_table.setHorizontalHeaderLabels(["Species", "Research Level"])
        self.species_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self.species_table.setColumnWidth(1, 160)
        self.species_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.species_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        research_layout.addWidget(self.species_table)
        layout.addWidget(research_box)

        # Buttons
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self._save)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        self._update_change_all_combo()
        self._populate_species()

    # ------------------------------------------------------------------

    def _storage_label_text(self) -> str:
        if self.save_txt_check.isChecked():
            return ".pa8 and .txt storage folder:"
        return ".pa8 storage folder:"

    def _on_save_txt_toggled(self, _checked: bool):
        self._storage_label.setText(self._storage_label_text())

    def _browse_pa8_download(self):
        current = self.pa8_download_edit.text() or os.path.expanduser("~/Downloads")
        folder = QFileDialog.getExistingDirectory(self, "Select .pa8 Download Folder", current)
        if folder:
            self.pa8_download_edit.setText(folder)

    def _browse_pa8_storage(self):
        current = self.pa8_storage_edit.text() or os.path.expanduser("~/Downloads")
        folder = QFileDialog.getExistingDirectory(self, "Select Storage Folder", current)
        if folder:
            self.pa8_storage_edit.setText(folder)

    def _populate_species(self):
        species_list = get_all_landmark_species()
        self.species_table.setRowCount(len(species_list))
        for row, species in enumerate(species_list):
            name_item = QTableWidgetItem(get_name_en(species))
            name_item.setData(Qt.ItemDataRole.UserRole, species)
            self.species_table.setItem(row, 0, name_item)

            combo = QComboBox()
            combo.addItems(["Base Research", "Research Level 10", "Perfect Research"])
            saved = self.settings.value(f"species/{species}/researchLevel", 0, int)
            combo.setCurrentIndex(saved)
            self.species_table.setCellWidget(row, 1, combo)

        if self.charm_check.isChecked():
            self._apply_charm_rule()

    def _apply_charm_rule(self):
        for row in range(self.species_table.rowCount()):
            combo = self.species_table.cellWidget(row, 1)
            if combo and combo.currentIndex() == 0:
                combo.setCurrentIndex(1)

    def _update_change_all_combo(self):
        self.change_all_combo.blockSignals(True)
        current = self.change_all_combo.currentText()
        self.change_all_combo.clear()
        if self.charm_check.isChecked():
            self.change_all_combo.addItems(["Research Level 10", "Perfect Research"])
        else:
            self.change_all_combo.addItems(
                ["Base Research", "Research Level 10", "Perfect Research"]
            )
        idx = self.change_all_combo.findText(current)
        self.change_all_combo.setCurrentIndex(max(idx, 0))
        self.change_all_combo.blockSignals(False)

    def _change_all_research(self, index):
        target = index + (1 if self.charm_check.isChecked() else 0)
        for row in range(self.species_table.rowCount()):
            combo = self.species_table.cellWidget(row, 1)
            if combo:
                combo.setCurrentIndex(target)

    def _on_charm_toggled(self, checked):
        if checked:
            self._apply_charm_rule()
        self._update_change_all_combo()

    def _save(self):
        self.settings.setValue("max_advances_default", self.max_advances_spin.value())
        self.settings.setValue("always_shiny", self.always_shiny_check.isChecked())
        self.settings.setValue("always_alpha", self.always_alpha_check.isChecked())
        self.settings.setValue(
            "preset_max_gap_enabled", self.preset_gap_check.isChecked()
        )
        self.settings.setValue("preset_max_gap", self.preset_gap_spin.value())
        self.settings.setValue("save_txt_file", self.save_txt_check.isChecked())
        self.settings.setValue("pa8_download_folder", self.pa8_download_edit.text())
        self.settings.setValue("pa8_storage_folder", self.pa8_storage_edit.text())
        self.settings.setValue("shiny_charm", self.charm_check.isChecked())
        filter_types = ["both", "trees", "rocks"]
        self.settings.setValue(
            "landmark_filter", filter_types[self.always_filter_combo.currentIndex()]
        )

        for row in range(self.species_table.rowCount()):
            item = self.species_table.item(row, 0)
            if item is None:
                continue
            species = item.data(Qt.ItemDataRole.UserRole)
            combo = self.species_table.cellWidget(row, 1)
            if combo:
                self.settings.setValue(
                    f"species/{species}/researchLevel", combo.currentIndex()
                )
        self.accept()
