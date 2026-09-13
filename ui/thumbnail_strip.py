from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QScrollArea, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QFrame,
)

THUMB_SIZE = 80

STATUS_TEXT = {"idle": "", "running": "Running…", "done": "Done", "error": "Error"}
STATUS_COLOR = {"idle": "#888888", "running": "#2b8fd6", "done": "#2ba84a", "error": "#c0392b"}


class ThumbnailItem(QFrame):
    clicked = Signal(object)
    remove_requested = Signal(object)

    def __init__(self, pixmap, parent=None):
        super().__init__(parent)
        width = THUMB_SIZE + 16
        height = THUMB_SIZE + 56
        self.setFixedSize(width, height)
        self.setFrameShape(QFrame.Box)
        self._status = "idle"
        self._selected = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 22, 4, 4)
        layout.setSpacing(4)

        self.image_label = QLabel()
        self.image_label.setPixmap(
            pixmap.scaled(THUMB_SIZE, THUMB_SIZE, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )
        self.image_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.image_label)

        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)

        # Overlaid on top of the layout (not managed by it) so it's always
        # drawn as a clearly visible badge, regardless of how tight the
        # thumbnail's own layout gets.
        self.remove_button = QPushButton("×", self)
        self.remove_button.setFixedSize(20, 20)
        self.remove_button.move(width - 24, 2)
        self.remove_button.setCursor(Qt.PointingHandCursor)
        self.remove_button.setStyleSheet(
            "QPushButton {"
            "   background-color: #c0392b; color: white; border: none;"
            "   border-radius: 10px; font-weight: bold; }"
            "QPushButton:hover { background-color: #e74c3c; }"
            "QPushButton:disabled { background-color: #999999; }"
        )
        self.remove_button.clicked.connect(lambda: self.remove_requested.emit(self))
        self.remove_button.raise_()

        self._apply_style()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self)
        super().mousePressEvent(event)

    def set_status(self, status):
        self._status = status
        self.status_label.setText(STATUS_TEXT.get(status, ""))
        self._apply_style()

    def set_selected(self, selected):
        self._selected = selected
        self._apply_style()

    def set_remove_enabled(self, enabled):
        self.remove_button.setEnabled(enabled)

    def _apply_style(self):
        border_color = "#000000" if self._selected else STATUS_COLOR.get(self._status, "#888888")
        border_width = 3 if self._selected else 2
        self.setStyleSheet(f"QFrame {{ border: {border_width}px solid {border_color}; }}")


class ThumbnailStrip(QWidget):
    itemClicked = Signal(int)
    itemRemoveRequested = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.items = []

        self.container = QWidget()
        self.container_layout = QHBoxLayout(self.container)
        self.container_layout.setContentsMargins(4, 4, 4, 4)
        self.container_layout.setSpacing(6)
        self.container_layout.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.container)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFixedHeight(THUMB_SIZE + 70)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    def add_item(self, pixmap):
        item = ThumbnailItem(pixmap)
        item.clicked.connect(self._on_item_clicked)
        item.remove_requested.connect(self._on_item_remove_requested)
        self.container_layout.insertWidget(self.container_layout.count() - 1, item)
        self.items.append(item)
        return len(self.items) - 1

    def remove_item(self, index):
        item = self.items.pop(index)
        self.container_layout.removeWidget(item)
        item.deleteLater()

    def set_status(self, index, status):
        self.items[index].set_status(status)

    def set_remove_enabled(self, index, enabled):
        self.items[index].set_remove_enabled(enabled)

    def set_selected(self, index):
        for i, item in enumerate(self.items):
            item.set_selected(i == index)

    def _on_item_clicked(self, item):
        self.itemClicked.emit(self.items.index(item))

    def _on_item_remove_requested(self, item):
        self.itemRemoveRequested.emit(self.items.index(item))
