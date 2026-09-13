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

IMAGE_FILTER = "Images (*.png *.jpg *.jpeg *.bmp *.webp)"
SAVE_FILTER = "PNG (*.png);;JPEG (*.jpg *.jpeg)"
LARGE_IMAGE_PIXELS = 12_000_000  # ~12 MP; warn before running anything bigger
MODEL_CHOICES = ["swinir-m", "realesr-general-x4v3", "bsrgan"]


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("IMVIFY")
        self.resize(800, 600)
        self.setAcceptDrops(True)

        self.image_path = None
        self.result_image = None
        self.cancel_event = None
        self.settings = QSettings("imvify", "IMVIFY")

        self.comparison_view = BeforeAfterView()

        open_button = QPushButton("Open")
        open_button.clicked.connect(self.open_image_dialog)

        self.model_combo = QComboBox()
        self.model_combo.addItems(MODEL_CHOICES)

        self.run_button = QPushButton("Run")
        self.run_button.clicked.connect(self.run_enhance)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel_enhance)

        self.save_button = QPushButton("Save")
        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self.save_result)

        self.device_label = QLabel("Device: -")
        self.stat_label = QLabel("")

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)

        controls_layout = QHBoxLayout()
        controls_layout.addWidget(open_button)
        controls_layout.addWidget(self.model_combo)
        controls_layout.addWidget(self.run_button)
        controls_layout.addWidget(self.cancel_button)
        controls_layout.addWidget(self.save_button)
        controls_layout.addWidget(self.device_label)
        controls_layout.addWidget(self.stat_label)

        layout = QVBoxLayout()
        layout.addLayout(controls_layout)
        layout.addWidget(self.comparison_view, stretch=1)
        layout.addWidget(self.progress_bar)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def open_image_dialog(self):
        start_dir = self.settings.value("last_dir", "")
        path, _ = QFileDialog.getOpenFileName(self, "Open Image", start_dir, IMAGE_FILTER)
        if path:
            self.settings.setValue("last_dir", str(Path(path).parent))
            self.load_image(path)

    def load_image(self, path):
        pixmap = QPixmap(path)
        if pixmap.isNull():
            QMessageBox.critical(self, "Open failed", f"Couldn't load image:\n{path}")
            return

        self.image_path = path
        self.result_image = None
        self.save_button.setEnabled(False)
        self.comparison_view.set_before(pixmap)
        self.comparison_view.set_after(None)
        self.comparison_view.setFocus()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            self.load_image(urls[0].toLocalFile())

    def run_enhance(self):
        if not self.image_path:
            QMessageBox.warning(self, "No image", "Open an image first.")
            return

        try:
            with PILImage.open(self.image_path) as img:
                width, height = img.size
        except Exception as e:
            QMessageBox.critical(self, "Cannot read image", f"Couldn't read the image file:\n{e}")
            return

        if width * height > LARGE_IMAGE_PIXELS:
            reply = QMessageBox.question(
                self, "Large image",
                f"This image is {width}x{height} ({width * height / 1_000_000:.1f} MP) and may take "
                "a long time or use a lot of memory to process. Continue anyway?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return

        self.cancel_event = threading.Event()
        self.run_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.save_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        model_name = self.model_combo.currentText()
        self.worker = EnhanceWorker(self.image_path, "output.png", model_name, self.cancel_event)
        self.worker.progress.connect(self.on_progress)
        self.worker.finished.connect(self.on_finished)
        self.worker.cancelled.connect(self.on_cancelled)
        self.worker.error.connect(self.on_error)
        self.worker.device_selected.connect(self.on_device_selected)
        self.worker.start()

    def cancel_enhance(self):
        if self.cancel_event:
            self.cancel_event.set()
        self.cancel_button.setEnabled(False)

    def on_progress(self, done, total):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(done)

    def on_device_selected(self, device):
        self.device_label.setText(f"Device: {device.upper()}")

    def on_finished(self, image, elapsed):
        self.run_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.progress_bar.setVisible(False)

        self.result_image = image
        self.save_button.setEnabled(True)
        self.comparison_view.set_after(QPixmap.fromImage(image.toqimage()))
        self.stat_label.setText(f"Last run: {elapsed:.2f}s")
        self.comparison_view.setFocus()

    def on_cancelled(self):
        self.run_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.progress_bar.setVisible(False)
        QMessageBox.information(self, "Cancelled", "Enhancement cancelled.")

    def on_error(self, message):
        self.run_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, "Enhance failed", message)

    def save_result(self):
        if self.result_image is None:
            return

        start_dir = self.settings.value("last_dir", "")
        path, selected_filter = QFileDialog.getSaveFileName(self, "Save Result", start_dir, SAVE_FILTER)
        if not path:
            return

        if "JPEG" in selected_filter or path.lower().endswith((".jpg", ".jpeg")):
            quality, ok = QInputDialog.getInt(self, "JPEG Quality", "Quality (1-100):", 95, 1, 100)
            if not ok:
                return
            self.result_image.convert("RGB").save(path, quality=quality)
        else:
            self.result_image.save(path)
