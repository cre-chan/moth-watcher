from __future__ import annotations
import os

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

class DebugVideoStream:
    """
    This class is used for debugging the AI models. It reads images from the test dataset
    instead of reading from the GoPro stream.
    """
    def __init__(self, dataset_path: str, width: int, height: int):
        self.dataset_path = dataset_path
        self.width = width
        self.height = height
        self.image_files = sorted(
            [f for f in os.listdir(dataset_path) if f.lower().endswith((".jpg", ".jpeg", ".png"))]
        )
        self.index = 0

    def start(self) -> None:
        if not self.image_files:
            raise RuntimeError(f"No images found in dataset path: {self.dataset_path}")

    def read_frame(self) -> np.ndarray | None:
        if self.index >= len(self.image_files):
            return None
        image_file = self.image_files[self.index]
        image_path = os.path.join(self.dataset_path, image_file)
        frame = cv2.imread(image_path)
        if frame is None:
            return None
        resized = cv2.resize(frame, (self.width, self.height))
        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
        self.index += 1
        return gray

    def close(self) -> None:
        pass

class VideoStreamFactory:
    @staticmethod
    def create_from_device(device_index: int, width: int, height: int) -> VideoStream:
        None

    @staticmethod
    def create_from_url(stream_url: str, width: int, height: int) -> VideoStream:
        None