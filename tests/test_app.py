import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from app.main import ALERT_SUBJECT, App, format_detections


def make_config():
    return SimpleNamespace(
        camera_device_index=2,
        frame_width=640,
        frame_height=480,
        yolov8_model_path="model.pt",
        gmail_token_file="token.json",
        alert_recipient_email="recipient@example.com",
        alert_sender_email="sender@example.com",
        alert_cooldown_seconds=600,
        sample_interval_seconds=2.0,
    )


class TestApp(unittest.TestCase):
    @patch("app.main.AlertSenderFactory.create_gmail_sender_from_token")
    @patch("app.main.DetectorFactory.create_YOLOv8_detector")
    @patch("app.main.VideoStreamFactory.create_from_device")
    def test_init_creates_dependencies_from_config(
        self, video_stream, create_detector, create_sender
    ):
        """
        Test that the App class initializes its dependencies correctly from the configuration.
        """
        config = make_config()

        app = App(config)

        video_stream.assert_called_once_with(2, 640, 480)
        create_detector.assert_called_once_with("model.pt")
        create_sender.assert_called_once_with(
            "token.json", "recipient@example.com", "sender@example.com"
        )
        self.assertIs(app.stream, video_stream.return_value)
        self.assertIs(app.detector, create_detector.return_value)
        self.assertIs(app.sender, create_sender.return_value)
        self.assertIsNone(app.last_alert_at)

    @patch("app.main.AlertSenderFactory.create_gmail_sender_from_token")
    @patch("app.main.DetectorFactory.create_YOLOv8_detector")
    @patch("app.main.VideoStreamFactory.create_from_device")
    @patch("app.main.time.sleep", side_effect=KeyboardInterrupt)
    @patch("builtins.print")
    def test_run_sends_detection_email_and_closes_stream(
        self, print_mock, sleep, video_stream, create_detector, create_sender
    ):
        """
        A detected moth is printed and emailed without estimating emergence.
        """
        app = App(make_config())
        app.estimator = Mock()
        frame = object()
        result = {
            "bbox": [(10, 20, 30, 40)],
            "features": [{
                "confidence": 0.9,
                "class_id": 0,
                "centroid_x": 25.0,
                "centroid_y": 40.0,
            }],
        }
        app.stream.read_frame.return_value = frame
        app.detector.detect.return_value = result

        with self.assertRaises(KeyboardInterrupt):
            app.run()

        app.stream.start.assert_called_once_with()
        app.detector.detect.assert_called_once_with(frame)
        app.estimator.update.assert_called_once_with(result)
        app.sender.send.assert_called_once()
        subject, body = app.sender.send.call_args.args
        self.assertEqual(subject, ALERT_SUBJECT)
        self.assertIn("emergence is not determined", body)
        self.assertIn("bbox=(10, 20, 30, 40)", body)
        print_mock.assert_any_call(format_detections(result))
        sleep.assert_called_once_with(2.0)
        app.stream.close.assert_called_once_with()

    @patch("app.main.AlertSenderFactory.create_gmail_sender_from_token")
    @patch("app.main.DetectorFactory.create_YOLOv8_detector")
    @patch("app.main.VideoStreamFactory.create_from_device")
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

    @patch("app.main.AlertSenderFactory.create_gmail_sender_from_token")
    @patch("app.main.DetectorFactory.create_YOLOv8_detector")
    @patch("app.main.VideoStreamFactory.create_from_device")
    @patch("app.main.time.sleep", side_effect=KeyboardInterrupt)
    @patch("builtins.print")
    def test_run_does_not_send_email_when_nothing_is_detected(
        self, print_mock, sleep, video_stream, create_detector, create_sender
    ):
        app = App(make_config())
        app.stream.read_frame.return_value = object()
        app.detector.detect.return_value = {"bbox": [], "features": []}

        with self.assertRaises(KeyboardInterrupt):
            app.run()

        print_mock.assert_called_once_with("Moth detections: 0")
        app.sender.send.assert_not_called()
        app.stream.close.assert_called_once_with()

    def test_format_detections_rejects_mismatched_lists(self):
        with self.assertRaisesRegex(ValueError, "different numbers"):
            format_detections({"bbox": [(1, 2, 3, 4)], "features": []})

    @patch("app.main.AlertSenderFactory.create_gmail_sender_from_token")
    @patch("app.main.DetectorFactory.create_YOLOv8_detector")
    @patch("app.main.VideoStreamFactory.create_from_device")
    @patch("app.main.time.time", side_effect=[100.0, 101.0])
    @patch("app.main.time.sleep", side_effect=[None, KeyboardInterrupt])
    @patch("builtins.print")
    def test_run_does_not_resend_during_cooldown(
        self, print_mock, sleep, current_time, video_stream, create_detector, create_sender
    ):
        app = App(make_config())
        app.stream.read_frame.return_value = object()
        app.detector.detect.return_value = {
            "bbox": [(10, 20, 30, 40)],
            "features": [{
                "confidence": 0.9,
                "class_id": 0,
                "centroid_x": 25.0,
                "centroid_y": 40.0,
            }],
        }

        with self.assertRaises(KeyboardInterrupt):
            app.run()

        self.assertEqual(app.detector.detect.call_count, 2)
        app.sender.send.assert_called_once()
        app.stream.close.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
