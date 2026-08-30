import importlib
import os
import unittest
from unittest.mock import patch


class AppConfigEnvironmentTests(unittest.TestCase):
    def test_detection_and_gmail_settings_use_environment_values(self):
        """検出とGmailの環境変数がAppConfigへ反映されることを確認する。"""
        values = {
            "TARGET_FPS": "24",
            "DETECTION_WINDOW_SECONDS": "2.5",
            "YOLOV8_MODEL_PATH": "custom.pt",
            "GMAIL_TOKEN_PATH": "token.json",
            "GMAIL_RECIPIENT": "recipient@example.com",
            "GMAIL_SENDER": "sender@example.com",
        }
        with patch.dict(os.environ, values, clear=True):
            import app.config as config_module
            config_module = importlib.reload(config_module)
            config = config_module.AppConfig.load()

        self.assertEqual(config.yolov8_model_path, "custom.pt")
        self.assertEqual(config.target_fps, 24.0)
        self.assertEqual(config.detection_window_seconds, 2.5)
        self.assertEqual(config.gmail_token_file, "token.json")
        self.assertEqual(config.alert_recipient_email, "recipient@example.com")
        self.assertEqual(config.alert_sender_email, "sender@example.com")

    def test_processing_settings_use_defaults(self):
        """処理設定の既定値が30 FPS、1秒windowであることを確認する。"""
        with patch.dict(os.environ, {}, clear=True):
            import app.config as config_module
            config_module = importlib.reload(config_module)
            config = config_module.AppConfig.load()

        self.assertEqual(config.target_fps, 30.0)
        self.assertEqual(config.detection_window_seconds, 1.0)

    def test_validate_rejects_non_positive_processing_settings(self):
        from app.config import AppConfig

        config = AppConfig(
            target_fps=0,
            detection_window_seconds=1.0,
            gmail_token_file="token.json",
            alert_recipient_email="recipient@example.com",
        )
        with self.assertRaisesRegex(ValueError, "TARGET_FPS"):
            config.validate()


if __name__ == "__main__":
    unittest.main()
