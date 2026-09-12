from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QPainter, QPen, QColor
from PySide6.QtWidgets import QWidget


class BeforeAfterView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.before_pixmap = None
        self.after_pixmap = None
        self.slider_pos = 0.5
        self._flicker_saved_pos = None

        self.zoom = None
        self.pan_offset = QPointF(0.0, 0.0)
        self._pan_last_pos = None

        self.setMinimumHeight(200)
        self.setFocusPolicy(Qt.StrongFocus)

    def set_before(self, pixmap):
        self.before_pixmap = pixmap
        self.zoom = None
        self.pan_offset = QPointF(0 ,0)
        self.update()

    def set_after(self, pixmap):
        self.after_pixmap = pixmap
        self.update()

    def _visible_source_rect(self, img_size):
        visible_w = min(self.width() / self.zoom, img_size.width())
        visible_h = min(self.height() / self.zoom, img_size.height())
        
        center_x = img_size.width() / 2 + self.pan_offset.x()
        center_y = img_size.height() / 2 + self.pan_offset.y()
        
        x = max(0, min(center_x - visible_w / 2, img_size.width() - visible_w))
        y = max(0, min(center_y - visible_h / 2, img_size.height() - visible_h))
        return QRectF(x, y, visible_w, visible_h)

    def paintEvent(self, event):
        if self.width() == 0 or self.height() == 0:
            return

        painter = QPainter(self)

        if self.before_pixmap is None:
            painter.drawText(self.rect(), Qt.AlignCenter, "Drop an image here")
            return

        img_size = self.before_pixmap.size()
        if self.zoom is None:
            scale = min(self.width() / img_size.width(), self.height() / img_size.height())
            target_w = img_size.width() * scale
            target_h = img_size.height() * scale
            target_rect = QRectF((self.width() - target_w) / 2, (self.height() - target_h) / 2, target_w, target_h)
            source_rect = QRectF(0, 0, img_size.width(), img_size.height())
        else:
            target_rect = QRectF(self.rect())
            source_rect = self._visible_source_rect(img_size)

        painter.drawPixmap(target_rect, self.before_pixmap, source_rect)

        if self.after_pixmap is not None:
            divider_x = target_rect.left() + target_rect.width() * self.slider_pos

            painter.setClipRect(QRectF(
                target_rect.left(), target_rect.top(),
                divider_x - target_rect.left(), target_rect.height(),
            ))
            painter.drawPixmap(target_rect, self.after_pixmap, source_rect)
            painter.setClipping(False)

            painter.setPen(QPen(QColor("red"), 2))
            painter.drawLine(int(divider_x), int(target_rect.top()), int(divider_x), int(target_rect.bottom()))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._update_slider(event.position().x())
        elif event.button() == Qt.RightButton:
            self._pan_last_pos = event.position()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            self._update_slider(event.position().x())
        elif event.buttons() & Qt.RightButton and self.zoom is not None and self._pan_last_pos is not None:
            delta = event.position() - self._pan_last_pos
            self._pan_last_pos = event.position()
            self.pan_offset -= QPointF(delta.x() / self.zoom, delta.y() / self.zoom)
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.RightButton:
            self._pan_last_pos = None

    def wheelEvent(self, event):
        if self.before_pixmap is None:
            return

        img_size = self.before_pixmap.size()
        current_scale = self.zoom if self.zoom is not None else min(
            self.width() / img_size.width(), self.height() / img_size.height()
        )

        factor = 1.25 if event.angleDelta().y() > 0 else 0.8
        self.zoom = max(0.1, min(current_scale * factor, 8.0))
        self.update()

    def _update_slider(self, x):
        if self.width() > 0:
            self.slider_pos = min(max(x / self.width(), 0.0), 1.0)
            self.update()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Space and not event.isAutoRepeat() and self._flicker_saved_pos is None:
            self._flicker_saved_pos = self.slider_pos
            self.slider_pos = 1.0
            self.update()
        elif event.key() == Qt.Key_0:
            self.zoom = None
            self.pan_offset = QPointF(0, 0)
            self.update()
        elif event.key() == Qt.Key_1:
            self.zoom = 1.0
            self.pan_offset = QPointF(0, 0)
            self.update()
        else:
            super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key_Space and not event.isAutoRepeat() and self._flicker_saved_pos is not None:
            self.slider_pos = self._flicker_saved_pos
            self._flicker_saved_pos = None
            self.update()
        else:
            super().keyReleaseEvent(event)
