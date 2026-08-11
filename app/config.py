from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class AppConfig:
    gopro_stream_url: str = os.getenv("GOPRO_STREAM_URL", "rtsp://gopro:8554/live")
    frame_width: int = int(os.getenv("FRAME_WIDTH", "640"))
    frame_height: int = int(os.getenv("FRAME_HEIGHT", "480"))
    sample_interval_seconds: float = float(os.getenv("SAMPLE_INTERVAL_SECONDS", "2.0"))
    molting_threshold: float = float(os.getenv("MOLTING_THRESHOLD", "0.75"))
    pupation_threshold: float = float(os.getenv("PUPATION_THRESHOLD", "0.75"))
    hunger_threshold: float = float(os.getenv("HUNGER_THRESHOLD", "0.75"))
    alert_cooldown_seconds: int = int(os.getenv("ALERT_COOLDOWN_SECONDS", "600"))
    smtp_host: str = os.getenv("SMTP_HOST", "smtp.example.com")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_username: str = os.getenv("SMTP_USERNAME", "")
    smtp_password: str = os.getenv("SMTP_PASSWORD", "")
    smtp_from: str = os.getenv("SMTP_FROM", "watchmose@example.com")
    smtp_to: str = os.getenv("SMTP_TO", "")

    @classmethod
    def load(cls) -> "AppConfig":
        return cls()
