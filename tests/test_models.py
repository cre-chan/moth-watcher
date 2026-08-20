"""AIモデルの YOLOv8 推論を検証するテスト。"""

from __future__ import annotations

import os
from pathlib import Path
import unittest

import cv2

from app.detection import DetectorFactory
from helper.models import train_YOLOv8_model
import numpy as np

class TestAIModel(unittest.TestCase):
    """AIモデルのテストケース。"""

    def setUp(self):
        self.dataset_images_dir = Path(
            "data/ami_dataset/ami_traps/camera_trap_images/images"
        ).resolve()
        self.default_model_path = Path("models/yolov8_model.pt").resolve()
        self.model_path = Path(os.getenv("YOLOV8_MODEL_PATH", str(self.default_model_path))).resolve()
        self.enable_training = os.getenv("YOLOV8_TRAIN_FOR_TEST", "0") == "1"

        if not self.model_path.is_file():
            if not self.enable_training:
                self.skipTest(
                    "YOLOv8 model file was not found. "
                    "Set YOLOV8_MODEL_PATH or enable YOLOV8_TRAIN_FOR_TEST=1."
                )
            trained_path = train_YOLOv8_model(
                output_root="models/ami_yolov8",
                run_name="test_one_class",
                epochs=1,
                imgsz=320,
                batch=8,
                max_samples=64,
            )
            self.model_path = Path(trained_path).resolve()

        if not self.dataset_images_dir.is_dir():
            self.skipTest(f"AMI dataset image directory does not exist: {self.dataset_images_dir}")

        image_candidates = sorted(
            p for p in self.dataset_images_dir.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png"}
        )
        if not image_candidates:
            self.skipTest(f"No sample images found in {self.dataset_images_dir}")

        self.sample_image_path = image_candidates[0]
        self.detector = DetectorFactory.create_yolov8_detector(str(self.model_path))

    def test_detector_factory_aliases(self):
        detector_lower = DetectorFactory.create_yolov8_detector(str(self.model_path))
        detector_upper = DetectorFactory.create_YOLOv8_detector(str(self.model_path))
        self.assertEqual(detector_lower.model_path, detector_upper.model_path)

    def test_YOLOv8_detect_output_schema(self):
        """
        The test checks that the YOLOv8 detector returns a dictionary with 'bbox' and 'features' keys,
        and that the values are lists of the expected structure.
        """
        img = cv2.imread(str(self.sample_image_path))
        self.assertIsNotNone(img)

        result = self.detector.detect(img)
        self.assertIn("bbox", result)
        self.assertIn("features", result)
        self.assertIsInstance(result["bbox"], list)
        self.assertIsInstance(result["features"], list)
        self.assertEqual(len(result["bbox"]), len(result["features"]))

        for bbox in result["bbox"]:
            self.assertEqual(len(bbox), 4)
            for value in bbox:
                self.assertIsInstance(value, int)

        for feature in result["features"]:
            self.assertIn("confidence", feature)
            self.assertIn("class_id", feature)
            self.assertIn("centroid_x", feature)
            self.assertIn("centroid_y", feature)
            self.assertIsInstance(feature["confidence"], float)
            self.assertIsInstance(feature["class_id"], int)
            self.assertIsInstance(feature["centroid_x"], float)
            self.assertIsInstance(feature["centroid_y"], float)

    def test_YOLOv8_detect_no_detections(self):
        """
        このテストは白い画像blank_imageを生成する
        detectorは次のようなdictionaryを返すことを期待する:
        {
            "bbox": [],
            "features": []
        }
        """
        # Create a blank image (black) with no objects
        blank_image = 255 * np.ones(shape=[640, 640, 3], dtype=np.uint8)

        result = self.detector.detect(blank_image)
        self.assertIn("bbox", result)
        self.assertIn("features", result)
        self.assertIsInstance(result["bbox"], list)
        self.assertIsInstance(result["features"], list)
        self.assertEqual(len(result["bbox"]), 0)
        self.assertEqual(len(result["features"]), 0)

    def _read_yolo_boxes(self, label_path: Path) -> list[tuple[float, float, float, float]]:
        """YOLO形式のGTボックスを (cx, cy, w, h) で返す。"""
        boxes: list[tuple[float, float, float, float]] = []
        if not label_path.is_file():
            return boxes
        for raw_line in label_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) != 5:
                continue
            _, cx, cy, w, h = (float(part) for part in parts)
            boxes.append((cx, cy, w, h))
        return boxes

    def _iou(self, box_a: tuple[float, float, float, float], box_b: tuple[float, float, float, float]) -> float:
        """YOLO形式の2つのbbox間のIoUを計算する。"""
        cx_a, cy_a, w_a, h_a = box_a
        cx_b, cy_b, w_b, h_b = box_b

        x1_a = cx_a - w_a / 2.0
        y1_a = cy_a - h_a / 2.0
        x2_a = cx_a + w_a / 2.0
        y2_a = cy_a + h_a / 2.0

        x1_b = cx_b - w_b / 2.0
        y1_b = cy_b - h_b / 2.0
        x2_b = cx_b + w_b / 2.0
        y2_b = cy_b + h_b / 2.0

        inter_x1 = max(x1_a, x1_b)
        inter_y1 = max(y1_a, y1_b)
        inter_x2 = min(x2_a, x2_b)
        inter_y2 = min(y2_a, y2_b)
        inter_w = max(0.0, inter_x2 - inter_x1)
        inter_h = max(0.0, inter_y2 - inter_y1)
        inter_area = inter_w * inter_h

        area_a = max(0.0, (x2_a - x1_a) * (y2_a - y1_a))
        area_b = max(0.0, (x2_b - x1_b) * (y2_b - y1_b))
        union = area_a + area_b - inter_area
        return inter_area / union if union > 0.0 else 0.0

    def test_TOLOv8_detction_precision(self):
        """
        このテストは検証用画像で、各画像ごとの検出精度をIoUベースで計算し、
        0〜1の範囲に収まることを確認する。
        """
        val_dir = Path("models/ami_yolov8/prepared_dataset")
        image_dir = val_dir / "images" / "val"
        label_dir = val_dir / "labels" / "val"
        if not image_dir.is_dir() or not label_dir.is_dir():
            self.skipTest(f"Prepared validation dataset is missing: {val_dir}")

        samples: list[float] = []
        for image_path in sorted(image_dir.iterdir())[:10]:
            if image_path.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
                continue
            label_path = label_dir / f"{image_path.stem}.txt"
            if not label_path.is_file():
                continue

            img = cv2.imread(str(image_path))
            if img is None:
                continue

            result = self.detector.detect(img)
            gt_boxes = self._read_yolo_boxes(label_path)
            pred_boxes = []
            for x, y, w, h in result["bbox"]:
                cx = x + w / 2.0
                cy = y + h / 2.0
                pred_boxes.append((cx, cy, float(w), float(h)))

            if not gt_boxes and not pred_boxes:
                precision = 1.0
            elif not pred_boxes:
                precision = 0.0
            else:
                matches = 0
                for pred_box in pred_boxes:
                    if any(self._iou(pred_box, gt_box) >= 0.1 for gt_box in gt_boxes):
                        matches += 1
                precision = matches / len(pred_boxes)

            self.assertTrue(np.isfinite(precision))
            self.assertGreaterEqual(precision, 0.0)
            self.assertLessEqual(precision, 1.0)
            samples.append(precision)

        self.assertTrue(samples, "No validation samples were usable for precision measurement")

    def test_YOLOv8_detect_counts(self):
        """
        このテストは検証用画像で検出数が一貫していることを確認する。
        bbox と features の件数が一致し、負でない整数であることを検証する。
        """
        val_dir = Path("models/ami_yolov8/prepared_dataset")
        image_dir = val_dir / "images" / "val"
        if not image_dir.is_dir():
            self.skipTest(f"Prepared validation image directory is missing: {image_dir}")

        for image_path in sorted(image_dir.iterdir())[:10]:
            if image_path.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
                continue

            image = cv2.imread(str(image_path))
            if image is None:
                continue

            result = self.detector.detect(image)
            bbox_count = len(result["bbox"])
            feature_count = len(result["features"])

            self.assertEqual(bbox_count, feature_count)
            self.assertGreaterEqual(bbox_count, 0)
            self.assertLessEqual(bbox_count, 100)

            for bbox in result["bbox"]:
                self.assertEqual(len(bbox), 4)
                for value in bbox:
                    self.assertIsInstance(value, int)

            for feature in result["features"]:
                self.assertIn("confidence", feature)
                self.assertIn("class_id", feature)
                self.assertIn("centroid_x", feature)
                self.assertIn("centroid_y", feature)
                self.assertGreaterEqual(feature["confidence"], 0.0)
                self.assertLessEqual(feature["confidence"], 1.0)
                self.assertIsInstance(feature["class_id"], int)
                self.assertIsInstance(feature["centroid_x"], float)
                self.assertIsInstance(feature["centroid_y"], float)

            break

if __name__ == "__main__":
    unittest.main()
