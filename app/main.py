from __future__ import annotations

import time
from typing import Optional

from app.alerts import AlertSenderFactory, GmailAlertSender
from app.capture import VideoStreamFactory
from app.config import AppConfig
from app.detection import DetectorFactory, YOLOv8Detector
from app.monitoring import EmergenceEvent, StateEstimator


ALERT_SUBJECT = "Watchmose emergence detected"


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
        self.estimator = StateEstimator(self.config.detection_window_seconds)
        self.sender: GmailAlertSender = AlertSenderFactory.create_gmail_sender_from_token(
            self.config.gmail_token_file,
            self.config.alert_recipient_email,
            self.config.alert_sender_email,
            self.config.alert_cooldown_seconds,
        )

    def _send_emergence_alert(
        self,
        event: EmergenceEvent,
        detection_message: str,
    ) -> None:
        body = (
            f"Moth count increased from {event.previous_count:g} "
            f"to {event.current_count:g}.\n"
            f"Detected at: {event.detected_at:.3f}\n\n"
            f"{detection_message}"
        )
        if self.sender.send(ALERT_SUBJECT, body) is not None:
            print("Alert sent")

    def run(self) -> None:
        self.stream.start()
        frame_interval = 1.0 / self.config.target_fps
        try:
            while True:
                loop_started_at = time.monotonic()
                frame = self.stream.read_frame()
                if frame is None:
                    time.sleep(1.0)
                    continue

                result = self.detector.detect(frame)
                message = format_detections(result)
                event = self.estimator.update(result, observed_at=time.time())
                print(message)

                if event is not None:
                    self._send_emergence_alert(event, message)

                elapsed = time.monotonic() - loop_started_at
                time.sleep(max(0.0, frame_interval - elapsed))
        finally:
            self.stream.close()



if __name__ == "__main__":
    app = App()
    app.run()
