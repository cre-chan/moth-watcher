import importlib
import os
import unittest
from unittest.mock import patch


class AppConfigEnvironmentTests(unittest.TestCase):
    def test_detection_and_gmail_settings_use_environment_values(self):
        """検出とGmailの環境変数がAppConfigへ反映されることを確認する。"""
        values = {
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
        self.assertEqual(config.gmail_token_file, "token.json")
        self.assertEqual(config.alert_recipient_email, "recipient@example.com")
        self.assertEqual(config.alert_sender_email, "sender@example.com")


if __name__ == "__main__":
    unittest.main()
