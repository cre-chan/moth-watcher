from __future__ import annotations

import cv2
import numpy as np


class LarvaDetector:
    """
    幼虫の検出器クラス
    """
    def __init__(self, min_area: int = 200, blur_kernel: int = 9):
        self.min_area = min_area
        self.blur_kernel = blur_kernel

    def detect(self, gray_frame: np.ndarray) -> tuple[tuple[int, int, int, int] | None, dict[str, float]]:
        blurred = cv2.GaussianBlur(gray_frame, (self.blur_kernel, self.blur_kernel), 0)
        _, thresh = cv2.threshold(blurred, 120, 255, cv2.THRESH_BINARY_INV)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        best_box = None
        features: dict[str, float] = {
            "area": 0.0,
            "extent": 0.0,
            "circularity": 0.0,
            "centroid_x": 0.0,
            "centroid_y": 0.0,
        }

        for contour in contours:
            area = cv2.contourArea(contour)
            if area < self.min_area:
                continue
            x, y, w, h = cv2.boundingRect(contour)
            rect_area = w * h
            extent = area / rect_area if rect_area else 0.0
            perimeter = cv2.arcLength(contour, True)
            circularity = 4.0 * np.pi * area / (perimeter * perimeter) if perimeter else 0.0
            if best_box is None or area > features["area"]:
                best_box = (x, y, w, h)
                features.update({
                    "area": float(area),
                    "extent": float(extent),
                    "circularity": float(circularity),
                    "centroid_x": float(x + w / 2.0),
                    "centroid_y": float(y + h / 2.0),
                })

        return best_box, features
