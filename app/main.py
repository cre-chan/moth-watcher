from __future__ import annotations

import time
from typing import Optional

from capture import VideoStream
from config import AppConfig
from detection import DetectorFactory, YOLOv8Detector
from monitoring import StateEstimator
from alerts import AlertSenderFactory, GmailAlertSender


def format_state(scores: dict[str, float]) -> str:
    return (
        f"molting={scores['molting_probability']:.3f}, "
        f"pupation={scores['pupation_probability']:.3f}, "
        f"hunger={scores['hunger_probability']:.3f}"
    )


def should_alert(scores: dict[str, float], config: AppConfig) -> bool:
    return (
        scores["molting_probability"] >= config.molting_threshold
        or scores["pupation_probability"] >= config.pupation_threshold
        or scores["hunger_probability"] >= config.hunger_threshold
    )

class App:
    def __init__(self, config: Optional[AppConfig] = None):
        self.config = config or AppConfig.load()
        self.stream = VideoStream(self.config.gopro_stream_url, self.config.frame_width, self.config.frame_height)
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

                _, features = self.detector.detect(frame)
                scores = self.estimator.update(features)
                print(f"State: {format_state(scores)}")

                if should_alert(scores, self.config):
                    now = time.time()
                    if self.last_alert_at is None or now - self.last_alert_at >= self.config.alert_cooldown_seconds:
                        self.sender.send(
                            f"Emergency detected. {format_state(scores)}"
                        )
                        print("Alert sent")
                        self.last_alert_at = now

                time.sleep(self.config.sample_interval_seconds)
        finally:
            self.stream.close()



if __name__ == "__main__":
    app = App()
    app.run()
