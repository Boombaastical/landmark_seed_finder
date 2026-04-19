"""Background worker — runs GPU seed search in a QThread."""

import os
import re
import shutil
from dataclasses import dataclass

from PyQt6.QtCore import QThread, pyqtSignal

from core.landmark_loader import get_name_en
from core.pa8_reader import ParsedPA8
from core.seed_finder import AdvanceResult, RunConfig, SeedFinder


@dataclass
class SeedJob:
    catch_order: int
    map_index: int
    identifier: str
    pa8: ParsedPA8
    landmark_data: dict
    pa8_path: str


def _next_batch_folder(base_dir: str) -> str:
    """Create and return the next Batch XXXX subfolder inside base_dir."""
    try:
        existing = [
            int(m.group(1))
            for d in os.listdir(base_dir)
            if (m := re.fullmatch(r"Batch (\d{4})", d))
        ]
    except OSError:
        existing = []
    next_n = max(existing, default=0) + 1
    folder = os.path.join(base_dir, f"Batch {next_n:04d}")
    os.makedirs(folder, exist_ok=True)
    return folder


class SeedWorker(QThread):
    progress_message = pyqtSignal(str)
    result_found = pyqtSignal(object)        # AdvanceResult
    landmark_started = pyqtSignal(int, str)  # (catch_order, identifier)
    landmark_done = pyqtSignal(int, str)     # (catch_order, identifier)
    all_done = pyqtSignal()
    error_occurred = pyqtSignal(str)

    def __init__(
        self,
        jobs: list,
        config: RunConfig,
        storage_folder: str = "",
        parent=None,
    ):
        super().__init__(parent)
        self._jobs = jobs
        self._config = config
        self._storage_folder = storage_folder
        self._cancelled = False
        self._batch_folder = ""

    def cancel(self):
        self._cancelled = True

    def run(self):
        try:
            finder = SeedFinder()
        except Exception as e:
            self.error_occurred.emit(f"Failed to initialize OpenCL: {e}")
            self.all_done.emit()
            return

        # Create the batch folder once per run if a storage folder is configured
        if self._storage_folder and os.path.isdir(self._storage_folder):
            try:
                self._batch_folder = _next_batch_folder(self._storage_folder)
            except Exception as e:
                self.error_occurred.emit(f"Could not create batch folder: {e}")

        for job in self._jobs:
            if self._cancelled:
                break

            self.landmark_started.emit(job.catch_order, job.identifier)
            self.progress_message.emit(
                f"Processing landmark {job.catch_order + 1}/{len(self._jobs)} "
                f"(ID: {job.identifier})…"
            )

            landmark_results = []

            def on_result(r: AdvanceResult):
                landmark_results.append(r)
                self.result_found.emit(r)

            try:
                finder.find_seeds_for_landmark(
                    job.pa8,
                    job.landmark_data,
                    job.map_index,
                    self._config,
                    job.catch_order,
                    progress_cb=lambda msg: self.progress_message.emit(msg),
                    result_cb=on_result,
                )
            except Exception as e:
                self.error_occurred.emit(
                    f"Error processing landmark {job.identifier}: {e}"
                )

            if self._batch_folder:
                self._move_pa8(job)
                if self._config.save_txt and landmark_results:
                    self._write_txt(job, landmark_results)

            self.landmark_done.emit(job.catch_order, job.identifier)

        self.all_done.emit()

    def _move_pa8(self, job: SeedJob):
        dest = os.path.join(self._batch_folder, os.path.basename(job.pa8_path))
        try:
            shutil.move(job.pa8_path, dest)
        except OSError as e:
            self.error_occurred.emit(f"Could not move {job.pa8_path}: {e}")

    def _write_txt(self, job: SeedJob, results: list):
        out_path = os.path.join(
            self._batch_folder,
            f"{job.catch_order}-{job.map_index}-{job.identifier}-results.txt",
        )
        try:
            with open(out_path, "w", encoding="utf-8") as f:
                for r in results:
                    iv_str = "/".join(str(iv) for iv in r.ivs)
                    f.write(
                        f"Encounter advance={r.advance}: "
                        f"{get_name_en(r.species, r.form, r.is_alpha)} "
                        f"shiny={r.is_shiny} level={r.level}\n"
                        f"iv_str={iv_str} ability={r.ability} "
                        f"gender={r.gender} nature={r.nature}\n"
                        f"height={r.height}\n"
                        f"weight={r.weight}\n"
                    )
        except OSError as e:
            self.error_occurred.emit(f"Could not write txt file: {e}")
