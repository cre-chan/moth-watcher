import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from app.main import App


def make_config():
    return SimpleNamespace(
        gopro_stream_url="rtsp://camera/live",
        frame_width=640,
        frame_height=480,
        yolov8_model_path="model.pt",
        gmail_token_file="token.json",
        alert_recipient_email="recipient@example.com",
        alert_sender_email="sender@example.com",
        molting_threshold=0.75,
        pupation_threshold=0.75,
        hunger_threshold=0.75,
        alert_cooldown_seconds=600,
        sample_interval_seconds=2.0,
    )


class TestApp(unittest.TestCase):
    @patch("app.main.AlertSenderFactory.create_gmail_sender_from_token")
    @patch("app.main.DetectorFactory.create_YOLOv8_detector")
    @patch("app.main.StateEstimator")
    @patch("app.main.VideoStream")
    def test_init_creates_dependencies_from_config(
        self, video_stream, state_estimator, create_detector, create_sender
    ):
        """
        Test that the App class initializes its dependencies correctly from the configuration.
        """
        config = make_config()

        app = App(config)

        video_stream.assert_called_once_with("rtsp://camera/live", 640, 480)
        create_detector.assert_called_once_with("model.pt")
        state_estimator.assert_called_once_with()
        create_sender.assert_called_once_with(
            "token.json", "recipient@example.com", "sender@example.com"
        )
        self.assertIs(app.stream, video_stream.return_value)
        self.assertIs(app.detector, create_detector.return_value)
        self.assertIs(app.estimator, state_estimator.return_value)
        self.assertIs(app.sender, create_sender.return_value)
        self.assertIsNone(app.last_alert_at)

    @patch("app.main.AlertSenderFactory.create_gmail_sender_from_token")
    @patch("app.main.DetectorFactory.create_YOLOv8_detector")
    @patch("app.main.VideoStream")
    @patch("app.main.time.sleep", side_effect=KeyboardInterrupt)
    def test_run_processes_frame_and_closes_stream(
        self, sleep, video_stream, create_detector, create_sender
    ):
        """
        Test that App.run gets a frame, processes it successfully, and closes the stream when interrupted.
        We mock the functions as follows:
        - video_stream.read_frame returns a dummy frame.
        - detector.detect returns dummy features.
        - estimator.update returns dummy scores.
        """
        app = App(make_config())
        frame = object()
        features = {"area": 10}
        scores = {
            "molting_probability": 0.1,
            "pupation_probability": 0.2,
            "hunger_probability": 0.3,
        }
        app.stream.read_frame.return_value = frame
        app.detector.detect.return_value = (Mock(), features)
        app.estimator = Mock()
        app.estimator.update.return_value = scores

        with self.assertRaises(KeyboardInterrupt):
            app.run()

        app.stream.start.assert_called_once_with()
        app.detector.detect.assert_called_once_with(frame)
        app.estimator.update.assert_called_once_with(features)
        app.sender.send.assert_not_called()
        sleep.assert_called_once_with(2.0)
        app.stream.close.assert_called_once_with()

    @patch("app.main.AlertSenderFactory.create_gmail_sender_from_token")
    @patch("app.main.DetectorFactory.create_YOLOv8_detector")
    @patch("app.main.VideoStream")
    @patch("app.main.time.sleep", side_effect=KeyboardInterrupt)
    def test_run_retries_and_closes_when_frame_is_unavailable(
        self, sleep, video_stream, create_detector, create_sender
    ):
        """
        When the stream returns None for a frame, the app should sleep for 1 second and retry.
        """
        app = App(make_config())
        app.stream.read_frame.return_value = None

        with self.assertRaises(KeyboardInterrupt):
            app.run()

        sleep.assert_called_once_with(1.0)
        app.detector.detect.assert_not_called()
        app.stream.close.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
