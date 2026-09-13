import threading

from PySide6.QtCore import Qt, QSettings
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QMainWindow, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QWidget,
    QFileDialog, QProgressBar, QMessageBox, QComboBox, QInputDialog,
)
from PIL import Image as PILImage
from pathlib import Path

from .worker import EnhanceWorker
from .comparison_view import BeforeAfterView
from .thumbnail_strip import ThumbnailStrip

IMAGE_FILTER = "Images (*.png *.jpg *.jpeg *.bmp *.webp)"
SAVE_FILTER = "PNG (*.png);;JPEG (*.jpg *.jpeg)"
LARGE_IMAGE_PIXELS = 12_000_000  # ~12 MP; warn before running anything bigger
MODEL_CHOICES = ["swinir-m", "realesr-general-x4v3", "bsrgan"]


class BatchItem:
    def __init__(self, path, before_pixmap):
        self.path = path
        self.before_pixmap = before_pixmap
        self.result_image = None
        self.result_pixmap = None
        self.elapsed = None
        self.status = "idle"  # idle | running | done | error
        self.error_message = None


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("IMVIFY")
        self.resize(900, 700)
        self.setAcceptDrops(True)

        self.batch = []
        self.current_item = None
        self.active_item = None
        self.cancel_event = None

        self.batch_mode = False
        self.batch_queue = []
        self.batch_cancel_requested = False
        self.batch_total = 0
        self.batch_completed = 0
        self.batch_errors = []

        self.settings = QSettings("imvify", "IMVIFY")

        self.comparison_view = BeforeAfterView()
        self.thumbnail_strip = ThumbnailStrip()
        self.thumbnail_strip.itemClicked.connect(self.select_item)
        self.thumbnail_strip.itemRemoveRequested.connect(self.remove_item)

        open_button = QPushButton("Open")
        open_button.clicked.connect(self.open_image_dialog)

        self.model_combo = QComboBox()
        self.model_combo.addItems(MODEL_CHOICES)

        self.run_button = QPushButton("Run")
        self.run_button.clicked.connect(self.start_single_run)

        self.run_all_button = QPushButton("Run All")
        self.run_all_button.clicked.connect(self.start_batch_run)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel_enhance)

        self.save_button = QPushButton("Save")
        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self.save_result)

        self.save_all_button = QPushButton("Save All")
        self.save_all_button.setEnabled(False)
        self.save_all_button.clicked.connect(self.save_all_result)

        self.device_label = QLabel("Device: -")
        self.stat_label = QLabel("")
        self.batch_progress_label = QLabel("")

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)

        controls_layout = QHBoxLayout()
        controls_layout.addWidget(open_button)
        controls_layout.addWidget(self.model_combo)
        controls_layout.addWidget(self.run_button)
        controls_layout.addWidget(self.run_all_button)
        controls_layout.addWidget(self.cancel_button)
        controls_layout.addWidget(self.save_button)
        controls_layout.addWidget(self.save_all_button)

        status_layout = QHBoxLayout()
        status_layout.addWidget(self.device_label)
        status_layout.addWidget(self.stat_label)
        status_layout.addWidget(self.batch_progress_label)
        status_layout.addStretch(1)

        layout = QVBoxLayout()
        layout.addLayout(controls_layout)
        layout.addLayout(status_layout)
        layout.addWidget(self.comparison_view, stretch=1)
        layout.addWidget(self.thumbnail_strip)
        layout.addWidget(self.progress_bar)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self._refresh_controls()

    # ---- loading images ----

    def open_image_dialog(self):
        start_dir = self.settings.value("last_dir", "")
        paths, _ = QFileDialog.getOpenFileNames(self, "Open Images", start_dir, IMAGE_FILTER)
        if paths:
            self.settings.setValue("last_dir", str(Path(paths[0]).parent))
            self.add_images(paths)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        paths = [url.toLocalFile() for url in event.mimeData().urls() if url.toLocalFile()]
        if paths:
            self.add_images(paths)

    def add_images(self, paths):
        failed = []
        first_new_index = None

        for path in paths:
            pixmap = QPixmap(path)
            if pixmap.isNull():
                failed.append(path)
                continue

            self.batch.append(BatchItem(path, pixmap))
            self.thumbnail_strip.add_item(pixmap)
            if first_new_index is None:
                first_new_index = len(self.batch) - 1

        if failed:
            QMessageBox.warning(
                self, "Some images failed to load",
                "Couldn't load:\n" + "\n".join(failed),
            )

        if self.current_item is None and first_new_index is not None:
            self.select_item(first_new_index)

        self._refresh_controls()

    def select_item(self, index):
        if index < 0 or index >= len(self.batch):
            return

        self.current_item = self.batch[index]
        item = self.current_item

        self.thumbnail_strip.set_selected(index)
        self.comparison_view.set_before(item.before_pixmap)
        self.comparison_view.set_after(item.result_pixmap)
        self.comparison_view.setFocus()

        if item.elapsed is not None:
            self.stat_label.setText(f"Last run: {item.elapsed:.2f}s")
        elif item.error_message:
            self.stat_label.setText(f"Error: {item.error_message}")
        else:
            self.stat_label.setText("")

        self._refresh_controls()

    def remove_item(self, index):
        if index < 0 or index >= len(self.batch):
            return

        item = self.batch[index]
        if item.status == "running":
            return

        reply = QMessageBox.question(
            self, "Remove image",
            f"Remove \"{Path(item.path).name}\" from the batch?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        del self.batch[index]
        self.thumbnail_strip.remove_item(index)

        if item is self.current_item:
            self.current_item = None
            if self.batch:
                self.select_item(min(index, len(self.batch) - 1))
            else:
                self.comparison_view.set_before(None)
                self.comparison_view.set_after(None)
                self.stat_label.setText("")

        self._refresh_controls()

    # ---- running ----

    def start_single_run(self):
        if self.active_item is not None or self.current_item is None:
            return

        item = self.current_item
        if not self._confirm_size_ok(item.path):
            return

        self.batch_mode = False
        self._start_item(item)

    def start_batch_run(self):
        if self.active_item is not None:
            return

        pending = [it for it in self.batch if it.status in ("idle", "error")]
        if not pending:
            QMessageBox.information(
                self, "Nothing to run",
                "Every image already has a result. Use Run to re-process the selected image.",
            )
            return

        self.batch_mode = True
        self.batch_cancel_requested = False
        self.batch_queue = pending
        self.batch_total = len(pending)
        self.batch_completed = 0
        self.batch_errors = []
        self._advance_batch()

    def _advance_batch(self):
        while self.batch_queue:
            item = self.batch_queue.pop(0)
            if item not in self.batch:
                continue
            self._start_item(item)
            return
        self._finish_batch()

    def _finish_batch(self):
        self.batch_mode = False
        self.batch_cancel_requested = False
        self.batch_progress_label.setText("")
        if self.batch_errors:
            QMessageBox.warning(
                self, "Batch finished with errors",
                "Some images failed:\n" + "\n".join(self.batch_errors),
            )
        self.batch_errors = []
        self._refresh_controls()

    def _start_item(self, item):
        self.active_item = item
        item.status = "running"
        item.error_message = None

        idx = self.batch.index(item)
        self.thumbnail_strip.set_status(idx, "running")
        self.thumbnail_strip.set_remove_enabled(idx, False)

        if item is self.current_item:
            self.stat_label.setText("Running…")

        if self.batch_mode:
            self.batch_progress_label.setText(f"Image {self.batch_completed + 1}/{self.batch_total}")

        self.cancel_event = threading.Event()
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        model_name = self.model_combo.currentText()
        self.worker = EnhanceWorker(item.path, "output.png", model_name, self.cancel_event)
        self.worker.progress.connect(self.on_progress)
        self.worker.finished.connect(self.on_finished)
        self.worker.cancelled.connect(self.on_cancelled)
        self.worker.error.connect(self.on_error)
        self.worker.device_selected.connect(self.on_device_selected)
        self.worker.start()

        self._refresh_controls()

    def cancel_enhance(self):
        if self.batch_mode:
            self.batch_cancel_requested = True
            self.batch_queue = []
            self.batch_progress_label.setText(
                f"Cancelling… (finishing image {self.batch_completed + 1}/{self.batch_total})"
            )
        elif self.cancel_event:
            self.cancel_event.set()

        self._refresh_controls()

    def _confirm_size_ok(self, path):
        try:
            with PILImage.open(path) as img:
                width, height = img.size
        except Exception as e:
            QMessageBox.critical(self, "Cannot read image", f"Couldn't read the image file:\n{e}")
            return False

        if width * height > LARGE_IMAGE_PIXELS:
            reply = QMessageBox.question(
                self, "Large image",
                f"This image is {width}x{height} ({width * height / 1_000_000:.1f} MP) and may take "
                "a long time or use a lot of memory to process. Continue anyway?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
            )
            return reply == QMessageBox.Yes
        return True

    # ---- worker callbacks ----

    def on_progress(self, done, total):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(done)

    def on_device_selected(self, device):
        self.device_label.setText(f"Device: {device.upper()}")

    def on_finished(self, image, elapsed):
        item = self.active_item
        self.active_item = None

        item.status = "done"
        item.error_message = None
        item.result_image = image
        item.result_pixmap = QPixmap.fromImage(image.toqimage())
        item.elapsed = elapsed

        if item in self.batch:
            idx = self.batch.index(item)
            self.thumbnail_strip.set_status(idx, "done")
            self.thumbnail_strip.set_remove_enabled(idx, True)

        if item is self.current_item:
            self.comparison_view.set_after(item.result_pixmap)
            self.stat_label.setText(f"Last run: {elapsed:.2f}s")

        self.progress_bar.setVisible(False)
        self._after_item_finished()

    def on_cancelled(self):
        item = self.active_item
        self.active_item = None

        if item is not None:
            item.status = "idle"
            if item in self.batch:
                idx = self.batch.index(item)
                self.thumbnail_strip.set_status(idx, "idle")
                self.thumbnail_strip.set_remove_enabled(idx, True)
            if item is self.current_item:
                self.stat_label.setText("")

        self.progress_bar.setVisible(False)
        QMessageBox.information(self, "Cancelled", "Enhancement cancelled.")
        self._refresh_controls()

    def on_error(self, message):
        item = self.active_item
        self.active_item = None

        if item is not None:
            item.status = "error"
            item.error_message = message
            if item in self.batch:
                idx = self.batch.index(item)
                self.thumbnail_strip.set_status(idx, "error")
                self.thumbnail_strip.set_remove_enabled(idx, True)
            if item is self.current_item:
                self.stat_label.setText(f"Error: {message}")

        self.progress_bar.setVisible(False)

        if self.batch_mode:
            if item is not None:
                self.batch_errors.append(f"{Path(item.path).name}: {message}")
            self._after_item_finished()
        else:
            QMessageBox.critical(self, "Enhance failed", message)
            self._refresh_controls()

    def _after_item_finished(self):
        if self.batch_mode:
            self.batch_completed += 1
            if self.batch_cancel_requested:
                self._finish_batch()
            else:
                self._advance_batch()
        else:
            self._refresh_controls()

    # ---- saving ----

    def save_result(self):
        item = self.current_item
        if item is None or item.result_image is None:
            return

        start_dir = self.settings.value("last_dir", "")
        suggested_name = f"{Path(item.path).stem}_enhanced.png"
        default_path = str(Path(start_dir) / suggested_name) if start_dir else suggested_name

        path, selected_filter = QFileDialog.getSaveFileName(self, "Save Result", default_path, SAVE_FILTER)
        if not path:
            return

        self._write_result(item.result_image, path, selected_filter)

    def _write_result(self, image, path, selected_filter):
        if "JPEG" in selected_filter or path.lower().endswith((".jpg", ".jpeg")):
            quality, ok = QInputDialog.getInt(self, "JPEG Quality", "Quality (1-100):", 95, 1, 100)
            if not ok:
                return
            image.convert("RGB").save(path, quality=quality)
        else:
            image.save(path)

    def save_all_result(self):
        completed = [it for it in self.batch if it.result_image is not None]
        if not completed:
            return

        start_dir = self.settings.value("last_dir", "")
        folder = QFileDialog.getExistingDirectory(self, "Save All - Choose Output Folder", start_dir)
        if not folder:
            return

        used_names = set()
        errors = []
        for item in completed:
            stem = Path(item.path).stem
            candidate = f"{stem}_enhanced.png"
            counter = 2
            while candidate in used_names or (Path(folder) / candidate).exists():
                candidate = f"{stem}_enhanced ({counter}).png"
                counter += 1
            used_names.add(candidate)

            try:
                item.result_image.save(str(Path(folder) / candidate))
            except Exception as e:
                errors.append(f"{Path(item.path).name}: {e}")

        if errors:
            QMessageBox.warning(
                self, "Save All finished with errors",
                "Some files failed to save:\n" + "\n".join(errors),
            )
        else:
            QMessageBox.information(self, "Save All", f"Saved {len(completed)} image(s) to:\n{folder}")

    # ---- control state ----

    def _refresh_controls(self):
        running = self.active_item is not None

        self.run_button.setEnabled(not running and self.current_item is not None)

        pending_exists = any(it.status in ("idle", "error") for it in self.batch)
        self.run_all_button.setEnabled(not running and pending_exists)

        self.cancel_button.setEnabled(running and not self.batch_cancel_requested)

        self.save_button.setEnabled(self.current_item is not None and self.current_item.result_image is not None)

        any_result = any(it.result_image is not None for it in self.batch)
        self.save_all_button.setEnabled(any_result)
