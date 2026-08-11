from __future__ import annotations

import time
from typing import Optional

from capture import VideoStream
from config import AppConfig
from detection import LarvaDetector
from inference import StateEstimator
from alerts import AlertSender


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


def run(config: Optional[AppConfig] = None) -> None:
    config = config or AppConfig.load()
    stream = VideoStream(config.gopro_stream_url, config.frame_width, config.frame_height)
    detector = LarvaDetector()
    estimator = StateEstimator()
    sender = AlertSender(
        smtp_host=config.smtp_host,
        smtp_port=config.smtp_port,
        username=config.smtp_username,
        password=config.smtp_password,
        from_address=config.smtp_from,
        to_address=config.smtp_to,
    )

    stream.start()
    last_alert_at: Optional[float] = None
    try:
        while True:
            frame = stream.read_frame()
            if frame is None:
                time.sleep(1.0)
                continue

            _, features = detector.detect(frame)
            scores = estimator.update(features)
            print(f"State: {format_state(scores)}")

            if should_alert(scores, config):
                now = time.time()
                if last_alert_at is None or now - last_alert_at >= config.alert_cooldown_seconds:
                    sender.send(
                        f"Emergency detected. {format_state(scores)}"
                    )
                    print("Alert sent")
                    last_alert_at = now

            time.sleep(config.sample_interval_seconds)
    finally:
        stream.close()


if __name__ == "__main__":
    run()
