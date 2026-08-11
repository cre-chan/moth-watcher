from __future__ import annotations

import cv2
import numpy as np


class VideoStream:
    def __init__(self, stream_url: str, width: int, height: int):
        self.stream_url = stream_url
        self.width = width
        self.height = height
        self.cap = cv2.VideoCapture(stream_url)

    def start(self) -> None:
        if not self.cap.isOpened():
            raise RuntimeError(f"Unable to open stream: {self.stream_url}")

    def read_frame(self) -> np.ndarray | None:
        ok, frame = self.cap.read()
        if not ok or frame is None:
            return None
        resized = cv2.resize(frame, (self.width, self.height))
        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
        return gray

    def close(self) -> None:
        if self.cap is not None:
            self.cap.release()
