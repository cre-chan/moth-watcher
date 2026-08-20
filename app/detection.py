from __future__ import annotations

import cv2
import numpy as np
import sys


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


class YOLOv8Detector:
    """
    YOLOv8を使用した検出器クラス
    """
    def __init__(self, model_path: str):
        self.model_path = model_path
        self._model = None

    def _load_model(self):
        if self._model is not None:
            return self._model
        try:
            from ultralytics import YOLO
        except ImportError as exc:
            python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
            raise RuntimeError(
                "ultralytics is required for YOLOv8 detection. "
                f"Current Python version is {python_version}. "
                "This project installs ultralytics only on Python < 3.13."
            ) from exc
        self._model = YOLO(self.model_path)
        return self._model

    def detect(self, img: np.ndarray) -> dict[str, list]:
        """
        YOLOv8を使用して検出を行うメソッド。
        このメソッドは入力画像から蛾の成虫を検出し、検出結果のバウンディングボックスと特徴量を返す。

        args:
            img (np.ndarray): 入力画像（BGR形式）
        
        returns:
            Dictionary containing the bounding boxes and features of the detected object as follows:
            {
                "bbox": [(x, y, w, h), ...],    # List of bounding boxes
                                                # when no object is detected, it will be an empty list
                "features": [{
                    "confidence": float,
                    "class_id": int,
                    "centroid_x": float,
                    "centroid_y": float
                }, ...]                         # List of features corresponding to each detected object
                                                # when no object is detected, it will be an empty list
            }           
        """
        if img is None:
            raise ValueError("img must not be None")
        if not isinstance(img, np.ndarray):
            raise TypeError(f"img must be np.ndarray. got: {type(img)}")

        model = self._load_model()
        # 既存のストリームはグレースケールを返すため、推論前にBGRへ揃える
        if img.ndim == 2:
            infer_img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        elif img.ndim == 3:
            infer_img = img
        else:
            raise ValueError(f"Unexpected image shape: {img.shape}")

        prediction = model.predict(source=infer_img, verbose=False)
        if not prediction:
            return {"bbox": [], "features": []}

        boxes = prediction[0].boxes
        if boxes is None or boxes.xyxy is None:
            return {"bbox": [], "features": []}

        bboxes: list[tuple[int, int, int, int]] = []
        features: list[dict[str, float | int]] = []

        xyxy_values = boxes.xyxy.cpu().numpy()
        conf_values = boxes.conf.cpu().numpy() if boxes.conf is not None else []
        cls_values = boxes.cls.cpu().numpy() if boxes.cls is not None else []

        for idx, xyxy in enumerate(xyxy_values):
            x1, y1, x2, y2 = [float(v) for v in xyxy]
            x = int(round(x1))
            y = int(round(y1))
            w = int(round(max(0.0, x2 - x1)))
            h = int(round(max(0.0, y2 - y1)))

            bboxes.append((x, y, w, h))
            confidence = float(conf_values[idx]) if len(conf_values) > idx else 0.0
            class_id = int(cls_values[idx]) if len(cls_values) > idx else 0
            features.append(
                {
                    "confidence": confidence,
                    "class_id": class_id,
                    "centroid_x": float(x + w / 2.0),
                    "centroid_y": float(y + h / 2.0),
                }
            )

        return {"bbox": bboxes, "features": features}

class DetectorFactory:
    """
    検出器のファクトリークラス
    2026/08/20: yolov8の検出器だけ実装しました。
    """
    @staticmethod
    def create_detector(detector_type: str, **kwargs) -> LarvaDetector:
        if detector_type == "larva":
            return LarvaDetector(**kwargs)
        else:
            raise ValueError(f"Unknown detector type: {detector_type}")

    @staticmethod
    def create_YOLOv8_detector(model_path: str) -> YOLOv8Detector:
        """
        *.pt形式ファイルのパスを指定してYOLOv8の検出器を作成する。
        """
        return YOLOv8Detector(model_path)

    @staticmethod
    def create_yolov8_detector(model_path: str) -> YOLOv8Detector:
        """ 
        create_yolov8_detectorはcreate_YOLOv8_detectorのエイリアスです。
        """
        return YOLOv8Detector(model_path)