from __future__ import annotations

import time
from typing import Optional

from app.alerts import AlertSenderFactory, GmailAlertSender
from app.capture import VideoStreamFactory
from app.config import AppConfig
from app.detection import DetectorFactory, YOLOv8Detector
from app.monitoring import StateEstimator


ALERT_SUBJECT = "Watchmose moth detected"


def format_detections(result: dict[str, list]) -> str:
    """YOLOの対応するbbox/featuresを、人とテストが読める形式へ整形する。"""
    bboxes = result.get("bbox")
    features = result.get("features")
    if not isinstance(bboxes, list) or not isinstance(features, list):
        raise ValueError("Detection result must contain list values for 'bbox' and 'features'.")
    if len(bboxes) != len(features):
        raise ValueError("Detection result has different numbers of 'bbox' and 'features'.")

    lines = [f"Moth detections: {len(bboxes)}"]
    for index, (bbox, feature) in enumerate(zip(bboxes, features), start=1):
        lines.append(
            f"#{index}: bbox={bbox}, confidence={feature['confidence']:.3f}, "
            f"class_id={feature['class_id']}, "
            f"centroid=({feature['centroid_x']:.1f}, {feature['centroid_y']:.1f})"
        )
    return "\n".join(lines)

class App:
    def __init__(self, config: Optional[AppConfig] = None):
        self.config = config or AppConfig.load()
        if isinstance(self.config, AppConfig):
            self.config.validate()
        self.stream = VideoStreamFactory.create_from_device(
            self.config.camera_device_index,
            self.config.frame_width,
            self.config.frame_height,
        )
        self.detector: YOLOv8Detector = DetectorFactory.create_YOLOv8_detector(
            self.config.yolov8_model_path
            )
        self.estimator = StateEstimator()
        self.sender: GmailAlertSender = AlertSenderFactory.create_gmail_sender_from_token(
            self.config.gmail_token_file,
            self.config.alert_recipient_email,
            self.config.alert_sender_email,
        )
        self.last_alert_at: Optional[float] = None

    def run(self) -> None:
        self.stream.start()
        try:
            while True:
                frame = self.stream.read_frame()
                if frame is None:
                    time.sleep(1.0)
                    continue

                result = self.detector.detect(frame)
                # 羽化判定の将来実装に向け、検出結果全体を推定器へ渡す。
                self.estimator.update(result)
                message = format_detections(result)
                print(message)

                if result["bbox"]:
                    now = time.time()
                    if self.last_alert_at is None or now - self.last_alert_at >= self.config.alert_cooldown_seconds:
                        self.sender.send(
                            ALERT_SUBJECT,
                            f"Moth detection only; emergence is not determined.\n\n{message}",
                        )
                        print("Alert sent")
                        self.last_alert_at = now

                time.sleep(self.config.sample_interval_seconds)
        finally:
            self.stream.close()



if __name__ == "__main__":
    app = App()
    app.run()
