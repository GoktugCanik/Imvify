from PySide6.QtWidgets import QMainWindow, QLabel, QPushButton, QVBoxLayout, QWidget, QFileDialog

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap

IMAGE_FILTER = "Images (*.png *.jpg *.jpeg *.bmp *.webp)"

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("IMVIFY")
        self.resize(800, 600)
        self.setAcceptDrops(True)

        self.preview_label = QLabel("Drop an image here")
        self.preview_label.setAlignment(Qt.AlignCenter)

        open_button = QPushButton("Open")
        open_button.clicked.connect(self.open_image_dialog)

        layout = QVBoxLayout()
        layout.addWidget(open_button)
        layout.addWidget(self.preview_label, stretch=1)

        container = QWidget()
        container.setLayout(layout)

        self.setCentralWidget(container)

    def open_image_dialog(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open Image", "", IMAGE_FILTER)
        if path:
            self.load_image(path)

    def load_image(self, path):
        pixmap = QPixmap(path)
        if pixmap.isNull():
            self.preview_label.setText(f"Failed to load image from: {path} ")
            return

        self.image_path = path
        self.preview_label.setPixmap(pixmap.scaled(self.preview_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            self.load_image(urls[0].toLocalFile())