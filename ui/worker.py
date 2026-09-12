import time

import torch
from PySide6.QtCore import QThread, Signal

from engine.enhance import enhance_image, EnhanceCancelled


class EnhanceWorker(QThread):
    progress = Signal(int, int)
    finished = Signal(object, float)
    cancelled = Signal()
    error = Signal(str)
    device_selected = Signal(str)

    def __init__(self, input_path, output_path, model_name, cancel_event):
        super().__init__()
        self.input_path = input_path
        self.output_path = output_path
        self.model_name = model_name
        self.cancel_event = cancel_event

    def run(self):
        device_name = "cuda" if torch.cuda.is_available() else "cpu"
        self.device_selected.emit(device_name)

        start = time.perf_counter()
        try:
            image = enhance_image(
                self.input_path, self.output_path, model_name=self.model_name,
                device=torch.device(device_name),
                progress_callback=lambda done, total: self.progress.emit(done, total),
                cancel_check=self.cancel_event.is_set,
            )
            self.finished.emit(image, time.perf_counter() - start)
        except EnhanceCancelled:
            self.cancelled.emit()
        except Exception as e:
            self.error.emit(str(e))
