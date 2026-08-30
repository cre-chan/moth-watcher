from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class AppConfig:
    camera_device_index: int = int(os.getenv("CAMERA_DEVICE_INDEX", "0"))
    # Unit: pixels.
    frame_width: int = int(os.getenv("FRAME_WIDTH", "640"))
    frame_height: int = int(os.getenv("FRAME_HEIGHT", "480"))
    # Unit: frames per second (FPS).
    target_fps: float = float(os.getenv("TARGET_FPS", "30"))
    # Unit: seconds.
    detection_window_seconds: float = float(
        os.getenv("DETECTION_WINDOW_SECONDS", "1.0")
    )
    # Unit: seconds.
    alert_cooldown_seconds: int = int(os.getenv("ALERT_COOLDOWN_SECONDS", "600"))
    yolov8_model_path: str = os.getenv(
        "YOLOV8_MODEL_PATH",
        "models/ami_yolov8/full_train/weights/best.pt",
    )
    gmail_token_file: str = os.getenv("GMAIL_TOKEN_PATH", "")
    alert_recipient_email: str = os.getenv("GMAIL_RECIPIENT", "")
    alert_sender_email: str | None = os.getenv("GMAIL_SENDER")

    @classmethod
    def load(cls) -> "AppConfig":
        return cls()

    def validate(self) -> None:
        # 起動前に、処理周期と必須のGmail設定をまとめて検証する。
        if self.target_fps <= 0:
            raise ValueError("TARGET_FPS must be greater than 0.")
        if self.detection_window_seconds <= 0:
            raise ValueError("DETECTION_WINDOW_SECONDS must be greater than 0.")

        missing = []
        if not self.gmail_token_file:
            missing.append("GMAIL_TOKEN_PATH")
        if not self.alert_recipient_email:
            missing.append("GMAIL_RECIPIENT")
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
