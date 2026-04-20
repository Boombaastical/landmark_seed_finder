"""Main application window."""

import os
import shutil

from PyQt6.QtCore import QSettings, Qt
from PyQt6.QtGui import QKeySequence
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from core.landmark_loader import DEFAULT_STORAGE_DIR, MAP_DISPLAY_NAMES, load_landmark
from core.pa8_reader import parse_pa8_file, read_pa8_files_from_folder
from core.seed_finder import RunConfig, compute_rolls
from core.statistics import format_stats, load_stats, update_stats
from ui.map_canvas import MapCanvas
from ui.results_table import ResultsTable
from ui.settings_dialog import SettingsDialog
from ui.worker import SeedJob, SeedWorker, _next_batch_folder


class MapWindow(QMainWindow):
    def __init__(self, settings: QSettings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self._worker = None  # SeedWorker or None
        self._current_results = []  # AdvanceResult list for current run
        self._batch_folder = ""   # batch folder for the current session
        self._run_index = 0       # increments each Generate within a session
        self._session_pa8_paths = []  # pa8 paths to move on Reset
        self.setWindowTitle("Landmark Seed Finder")
        self.resize(1200, 850)

        self._build_ui()
        self._load_settings_to_controls()
        last_map = self.settings.value("last_map_index", 0, int)
        self.map_combo.setCurrentIndex(last_map)
        self.canvas.load_map(last_map)
        self._refresh_stats_label()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(4)

        # Top bar
        top_bar = QHBoxLayout()
        self.map_combo = QComboBox()
        self.map_combo.addItems(MAP_DISPLAY_NAMES)
        self.map_combo.currentIndexChanged.connect(self._on_map_changed)
        top_bar.addWidget(QLabel("Map:"))
        top_bar.addWidget(self.map_combo)
        top_bar.addStretch()
        settings_btn = QPushButton("⚙ Settings")
        settings_btn.clicked.connect(self._open_settings)
        top_bar.addWidget(settings_btn)
        root.addLayout(top_bar)

        # Middle: map canvas + right controls panel
        middle = QHBoxLayout()
        middle.setSpacing(6)
        self.canvas = MapCanvas()
        self.canvas.landmark_selected.connect(self._on_landmark_selected)
        middle.addWidget(self.canvas, stretch=1)
        middle.addWidget(self._build_right_panel())
        root.addLayout(middle, stretch=2)

        # Results table
        self.results_table = ResultsTable()
        root.addWidget(self.results_table, stretch=1)

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

    def _build_right_panel(self) -> QWidget:
        panel = QWidget()
        panel.setFixedWidth(240)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # Landmark filter
        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Show:"))
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["Trees and Rocks", "Trees", "Rocks"])
        self.filter_combo.currentIndexChanged.connect(self._on_filter_changed)
        filter_row.addWidget(self.filter_combo)
        layout.addLayout(filter_row)

        # Search options
        search_box = QGroupBox("Search Options")
        sl = QVBoxLayout(search_box)

        adv_row = QHBoxLayout()
        adv_row.addWidget(QLabel("Max advances:"))
        self.max_advances_spin = QSpinBox()
        self.max_advances_spin.setRange(1, 999999)
        self.max_advances_spin.setValue(3000)
        adv_row.addWidget(self.max_advances_spin)
        sl.addLayout(adv_row)

        self.shiny_check = QCheckBox("Shiny only")
        sl.addWidget(self.shiny_check)
        self.alpha_check = QCheckBox("Alpha only")
        sl.addWidget(self.alpha_check)

        gap_row = QHBoxLayout()
        gap_row.addWidget(QLabel("Max gap:"))
        self.max_gap_spin = QSpinBox()
        self.max_gap_spin.setRange(2, 8)
        self.max_gap_spin.setValue(4)
        gap_row.addWidget(self.max_gap_spin)
        sl.addLayout(gap_row)
        layout.addWidget(search_box)

        # Folders
        folders_box = QGroupBox("Folders")
        fol = QVBoxLayout(folders_box)

        dl_row = QHBoxLayout()
        dl_row.addWidget(QLabel(".pa8 download:"))
        self.download_folder_edit = QLineEdit()
        self.download_folder_edit.setPlaceholderText("~/Downloads")
        dl_browse = QPushButton("…")
        dl_browse.setFixedWidth(28)
        dl_browse.clicked.connect(self._browse_download_folder)
        dl_row.addWidget(self.download_folder_edit)
        dl_row.addWidget(dl_browse)
        fol.addLayout(dl_row)

        st_row = QHBoxLayout()
        st_row.addWidget(QLabel(".pa8 storage:"))
        self.storage_folder_edit = QLineEdit()
        self.storage_folder_edit.setPlaceholderText("Batch output folder…")
        st_browse = QPushButton("…")
        st_browse.setFixedWidth(28)
        st_browse.clicked.connect(self._browse_storage_folder)
        st_row.addWidget(self.storage_folder_edit)
        st_row.addWidget(st_browse)
        fol.addLayout(st_row)

        layout.addWidget(folders_box)

        # Action buttons
        btn_row = QHBoxLayout()
        reset_btn = QPushButton("Reset (R)")
        reset_btn.setShortcut(QKeySequence("R"))
        reset_btn.clicked.connect(self._reset_selection)
        btn_row.addWidget(reset_btn)
        self.generate_btn = QPushButton("Generate")
        self.generate_btn.clicked.connect(self._on_generate)
        self.generate_btn.setShortcut(QKeySequence(Qt.Key.Key_Return))
        btn_row.addWidget(self.generate_btn)
        layout.addLayout(btn_row)

        # Progress bar (hidden at rest)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # indeterminate
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        # Step label (hidden at rest)
        self.step_label = QLabel("")
        self.step_label.setWordWrap(True)
        self.step_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.step_label.setStyleSheet("color: gray; font-size: 10px;")
        self.step_label.hide()
        layout.addWidget(self.step_label)

        # Statistics panel
        stats_box = QGroupBox("Statistics")
        stats_layout = QVBoxLayout(stats_box)
        self.stats_label = QLabel()
        self.stats_label.setTextFormat(Qt.TextFormat.PlainText)
        from PyQt6.QtGui import QFont, QFontDatabase
        mono_font = QFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        mono_font.setPointSize(10)
        self.stats_label.setFont(mono_font)
        stats_layout.addWidget(self.stats_label)
        layout.addWidget(stats_box)

        layout.addStretch()
        return panel

    # ------------------------------------------------------------------
    # Settings <-> controls sync
    # ------------------------------------------------------------------

    def _load_settings_to_controls(self):
        self.max_advances_spin.setValue(
            self.settings.value("max_advances_default", 3000, int)
        )
        self.shiny_check.setChecked(self.settings.value("always_shiny", False, bool))
        self.alpha_check.setChecked(self.settings.value("always_alpha", False, bool))
        if self.settings.value("preset_max_gap_enabled", False, bool):
            self.max_gap_spin.setValue(self.settings.value("preset_max_gap", 4, int))
        filter_map = {"both": 0, "trees": 1, "rocks": 2}
        saved_filter = self.settings.value("landmark_filter", "both")
        self.filter_combo.blockSignals(True)
        self.filter_combo.setCurrentIndex(filter_map.get(saved_filter, 0))
        self.filter_combo.blockSignals(False)
        self.canvas.set_landmark_filter(saved_filter)
        self.download_folder_edit.setText(
            os.path.expanduser(self.settings.value("pa8_download_folder", "~/Downloads"))
        )
        self.storage_folder_edit.setText(
            self.settings.value("pa8_storage_folder", DEFAULT_STORAGE_DIR)
        )

    def _open_settings(self):
        dlg = SettingsDialog(self.settings, self)
        if dlg.exec():
            self._load_settings_to_controls()

    def _refresh_stats_label(self):
        stats = load_stats()
        self.stats_label.setText(format_stats(stats))

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_map_changed(self, index: int):
        self._batch_folder = ""
        self._run_index = 0
        self._session_pa8_paths = []
        self.results_table.clear_results()
        self.canvas.load_map(index)
        self.settings.setValue("last_map_index", index)

    def _on_filter_changed(self, index: int):
        types = ["both", "trees", "rocks"]
        ft = types[index]
        self.canvas.set_landmark_filter(ft)
        self.settings.setValue("landmark_filter", ft)

    def _on_landmark_selected(self, identifier: str, map_index: int):
        pass  # preview handled inside MapCanvas

    def _browse_download_folder(self):
        current = self.download_folder_edit.text() or os.path.expanduser("~/Downloads")
        folder = QFileDialog.getExistingDirectory(self, "Select .pa8 Download Folder", current)
        if folder:
            self.download_folder_edit.setText(folder)
            self.settings.setValue("pa8_download_folder", folder)

    def _browse_storage_folder(self):
        current = self.storage_folder_edit.text() or os.path.expanduser("~/Downloads")
        folder = QFileDialog.getExistingDirectory(self, "Select Storage Folder", current)
        if folder:
            self.storage_folder_edit.setText(folder)
            self.settings.setValue("pa8_storage_folder", folder)

    def _reset_selection(self):
        if self._batch_folder and self._session_pa8_paths:
            for path in self._session_pa8_paths:
                if os.path.exists(path):
                    try:
                        shutil.move(path, os.path.join(self._batch_folder, os.path.basename(path)))
                    except OSError as e:
                        QMessageBox.warning(self, "Move Error", f"Could not move {path}:\n{e}")
        self._batch_folder = ""
        self._run_index = 0
        self._session_pa8_paths = []
        self.results_table.clear_results()
        self.canvas.set_locked(False)
        self.canvas.clear_selection()

    # ------------------------------------------------------------------
    # Generate / Cancel
    # ------------------------------------------------------------------

    def _on_generate(self):
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            return

        selected = self.canvas.get_selected_order()
        if not selected:
            QMessageBox.warning(self, "No Landmarks Selected",
                                "Please select at least one landmark on the map.")
            return

        folder = self.download_folder_edit.text().strip()
        if not os.path.isdir(folder):
            QMessageBox.warning(self, "Invalid Download Folder",
                                f"Download folder not found:\n{folder}")
            return

        pa8_paths = read_pa8_files_from_folder(folder)
        if len(pa8_paths) != len(selected):
            QMessageBox.warning(
                self, "File Count Mismatch",
                f"Selected {len(selected)} landmark(s) but found "
                f"{len(pa8_paths)} .pa8 file(s) in:\n{folder}\n\n"
                "Files are matched to landmarks in creation-date order.",
            )
            return

        map_index = self.canvas.map_index
        jobs = []
        for catch_order, (identifier, pa8_path) in enumerate(zip(selected, pa8_paths)):
            try:
                pa8 = parse_pa8_file(pa8_path)
            except Exception as e:
                QMessageBox.critical(self, "File Error", f"Could not read {pa8_path}:\n{e}")
                return
            try:
                landmark_data = load_landmark(map_index, identifier)
            except Exception as e:
                QMessageBox.critical(self, "Landmark Error",
                                     f"Could not load landmark {identifier}:\n{e}")
                return
            jobs.append(SeedJob(
                catch_order=catch_order,
                map_index=map_index,
                identifier=identifier,
                pa8=pa8,
                landmark_data=landmark_data,
                pa8_path=pa8_path,
            ))

        config = self._build_run_config()

        # Create the batch folder once per session (first Generate after Reset)
        if not self._batch_folder:
            storage_folder = self.storage_folder_edit.text().strip()
            if storage_folder and os.path.isdir(storage_folder):
                try:
                    self._batch_folder = _next_batch_folder(storage_folder)
                except Exception as e:
                    QMessageBox.warning(self, "Batch Folder Error",
                                        f"Could not create batch folder:\n{e}")

        # Track pa8 paths on first run so Reset knows what to move
        if not self._session_pa8_paths:
            self._session_pa8_paths = [job.pa8_path for job in jobs]

        self._current_results.clear()
        self.results_table.clear_results()
        self.generate_btn.setText("Cancel")
        self._set_controls_enabled(False)
        self.progress_bar.show()
        self.step_label.show()

        self._worker = SeedWorker(
            jobs, config,
            batch_folder=self._batch_folder,
            run_index=self._run_index,
            parent=self,
        )
        self._run_index += 1
        self._worker.landmark_started.connect(self._on_landmark_started)
        self._worker.progress_message.connect(self._on_progress_message)
        self._worker.result_found.connect(self._on_result_found)
        self._worker.error_occurred.connect(
            lambda msg: QMessageBox.warning(self, "Error", msg)
        )
        self._worker.all_done.connect(self._on_generation_done)
        self._worker.start()

    def _on_landmark_started(self, catch_order: int, total: int, identifier: str):
        self.status_bar.showMessage(f"Processing file {catch_order + 1}/{total}…")

    def _on_progress_message(self, msg: str):
        self.step_label.setText(msg)

    def _on_result_found(self, r):
        self._current_results.append(r)
        if self.shiny_check.isChecked() and not r.is_shiny:
            return
        if self.alpha_check.isChecked() and not r.is_alpha:
            return
        self.results_table.add_row(r)

    def _on_generation_done(self):
        self.generate_btn.setText("Generate")
        self._set_controls_enabled(True)
        self.progress_bar.hide()
        self.step_label.hide()
        self.canvas.set_locked(True)

        # Update statistics
        stats = update_stats(self._current_results)
        self.stats_label.setText(format_stats(stats))

        count = self.results_table.rowCount()
        self.status_bar.showMessage(
            f"Done — {count} result(s) found." if count else "Done — no results found."
        )

    def _set_controls_enabled(self, enabled: bool):
        self.map_combo.setEnabled(enabled)
        self.max_advances_spin.setEnabled(enabled)
        self.shiny_check.setEnabled(enabled)
        self.alpha_check.setEnabled(enabled)
        self.max_gap_spin.setEnabled(enabled)
        self.download_folder_edit.setEnabled(enabled)
        self.storage_folder_edit.setEnabled(enabled)
        self.canvas.setEnabled(enabled)

    def _build_run_config(self) -> RunConfig:
        charm = self.settings.value("shiny_charm", False, bool)
        species_rolls = {}
        from core.landmark_loader import get_all_landmark_species
        for species in get_all_landmark_species():
            level = self.settings.value(f"species/{species}/researchLevel", 0, int)
            species_rolls[species] = compute_rolls(level, charm)

        return RunConfig(
            species_rolls=species_rolls,
            default_rolls=1,
            max_gap=self.max_gap_spin.value(),
            max_advances=self.max_advances_spin.value(),
            look_for_shiny=self.shiny_check.isChecked(),
            look_for_alpha=self.alpha_check.isChecked(),
            save_txt=self.settings.value("save_txt_file", False, bool),
        )
