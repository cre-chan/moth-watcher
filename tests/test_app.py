import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from app.alerts import GmailAlertSender
from app.main import ALERT_SUBJECT, App, format_detections
from app.monitoring import EmergenceEvent


def make_config():
    return SimpleNamespace(
        camera_device_index=2,
        # Unit: pixels.
        frame_width=640,
        frame_height=480,
        yolov8_model_path="model.pt",
        gmail_token_file="token.json",
        alert_recipient_email="recipient@example.com",
        alert_sender_email="sender@example.com",
        # Unit: seconds.
        alert_cooldown_seconds=600,
        # Unit: frames per second (FPS).
        target_fps=30.0,
        # Unit: seconds.
        detection_window_seconds=1.0,
    )


def make_detection_result(count: int) -> dict[str, list]:
    """Detector出力を模擬し、bboxとfeaturesの件数を揃える。"""
    return {
        "bbox": [(10, 20, 30, 40) for _ in range(count)],
        "features": [
            {
                "confidence": 0.9,
                "class_id": 0,
                "centroid_x": 20.0,
                "centroid_y": 30.0,
            }
            for _ in range(count)
        ],
    }


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
            "token.json", "recipient@example.com", "sender@example.com", 600
        )
        self.assertIs(app.stream, video_stream.return_value)
        self.assertIs(app.detector, create_detector.return_value)
        self.assertIs(app.sender, create_sender.return_value)
        self.assertEqual(app.estimator.window_seconds, 1.0)

    @patch("app.main.AlertSenderFactory.create_gmail_sender_from_token")
    @patch("app.main.DetectorFactory.create_YOLOv8_detector")
    @patch("app.main.VideoStreamFactory.create_from_device")
    @patch("app.main.time.time", return_value=100.0)
    @patch("app.main.time.monotonic", side_effect=[0.0, 0.01])
    @patch("app.main.time.sleep", side_effect=KeyboardInterrupt)
    @patch("builtins.print")
    def test_run_sends_detection_email_and_closes_stream(
        self, print_mock, sleep, monotonic, current_time, video_stream, create_detector, create_sender
    ):
        """
        A detected moth is printed and emailed without estimating emergence.
        """
        app = App(make_config())
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
        app.estimator = Mock()
        app.estimator.update.return_value = EmergenceEvent(0.0, 1.0, 100.0)
        app.sender.send.return_value = {"id": "message-id"}

        with self.assertRaises(KeyboardInterrupt):
            app.run()

        app.stream.start.assert_called_once_with()
        app.detector.detect.assert_called_once_with(frame)
        app.estimator.update.assert_called_once_with(result, observed_at=100.0)
        app.sender.send.assert_called_once()
        subject, body = app.sender.send.call_args.args
        self.assertEqual(subject, ALERT_SUBJECT)
        self.assertIn("increased from 0 to 1", body)
        self.assertIn("bbox=(10, 20, 30, 40)", body)
        print_mock.assert_any_call(format_detections(result))
        sleep.assert_called_once()
        self.assertAlmostEqual(sleep.call_args.args[0], 1 / 30 - 0.01)
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
        app.estimator = Mock()
        app.estimator.update.return_value = None

        with self.assertRaises(KeyboardInterrupt):
            app.run()

        print_mock.assert_called_once_with("Moth detections: 0")
        app.sender.send.assert_not_called()
        app.stream.close.assert_called_once_with()

    @patch("app.main.AlertSenderFactory.create_gmail_sender_from_token")
    @patch("app.main.DetectorFactory.create_YOLOv8_detector")
    @patch("app.main.VideoStreamFactory.create_from_device")
    @patch("app.main.time.time", side_effect=[0.0, 1.0, 1.1])
    @patch(
        "app.main.time.monotonic",
        side_effect=[0.0, 0.01, 0.02, 0.03, 0.04, 0.05],
    )
    @patch("app.main.time.sleep", side_effect=[None, None, KeyboardInterrupt])
    @patch("builtins.print")
    def test_run_detects_emergence_from_detector_outputs(
        self,
        print_mock,
        sleep,
        monotonic,
        current_time,
        video_stream,
        create_detector,
        create_sender,
    ):
        app = App(make_config())
        app.stream.read_frame.return_value = object()
        # 実際のEstimatorに、基準値0から中央値が1増える検出系列を渡す。
        app.detector.detect.side_effect = [
            make_detection_result(0),
            make_detection_result(0),
            make_detection_result(2),
        ]
        app.sender.send.return_value = {"id": "message-id"}

        with self.assertRaises(KeyboardInterrupt):
            app.run()

        self.assertEqual(app.detector.detect.call_count, 3)
        # AppはEmergenceEventの発生時だけ通知するため、送信回数から間接的に検証する。
        app.sender.send.assert_called_once()
        subject, body = app.sender.send.call_args.args
        self.assertEqual(subject, ALERT_SUBJECT)
        self.assertIn("increased from 0 to 1", body)
        app.stream.close.assert_called_once_with()

    @patch("app.main.AlertSenderFactory.create_gmail_sender_from_token")
    @patch("app.main.DetectorFactory.create_YOLOv8_detector")
    @patch("app.main.VideoStreamFactory.create_from_device")
    @patch("app.main.time.time", side_effect=[0.0, 1.0, 1.1])
    @patch(
        "app.main.time.monotonic",
        side_effect=[0.0, 0.01, 0.02, 0.03, 0.04, 0.05],
    )
    @patch("app.main.time.sleep", side_effect=[None, None, KeyboardInterrupt])
    @patch("builtins.print")
    def test_run_does_not_detect_emergence_when_count_is_unchanged(
        self,
        print_mock,
        sleep,
        monotonic,
        current_time,
        video_stream,
        create_detector,
        create_sender,
    ):
        app = App(make_config())
        app.stream.read_frame.return_value = object()
        # 基準windowの完成後も中央値が増えない検出系列を渡す。
        app.detector.detect.side_effect = [make_detection_result(1)] * 3

        with self.assertRaises(KeyboardInterrupt):
            app.run()

        self.assertEqual(app.detector.detect.call_count, 3)
        # AppはEmergenceEventの発生時だけ通知するため、未送信から非発生を間接的に検証する。
        app.sender.send.assert_not_called()
        app.stream.close.assert_called_once_with()

    def test_format_detections_rejects_mismatched_lists(self):
        with self.assertRaisesRegex(ValueError, "different numbers"):
            format_detections({"bbox": [(1, 2, 3, 4)], "features": []})

    @patch("app.main.AlertSenderFactory.create_gmail_sender_from_token")
    @patch("app.main.DetectorFactory.create_YOLOv8_detector")
    @patch("app.main.VideoStreamFactory.create_from_device")
    @patch("app.main.time.time", side_effect=[100.0, 101.0])
    @patch("app.main.time.monotonic", side_effect=[0.0, 0.01, 0.02, 0.03])
    @patch("app.main.time.sleep", side_effect=[None, KeyboardInterrupt])
    @patch("builtins.print")
    def test_run_forwards_each_event_to_notification_sender(
        self, print_mock, sleep, monotonic, current_time, video_stream, create_detector, create_sender
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
        app.estimator = Mock()
        app.estimator.update.side_effect = [
            EmergenceEvent(0.0, 1.0, 100.0),
            EmergenceEvent(0.0, 1.0, 101.0),
        ]
        app.sender.send.side_effect = [{"id": "message-id"}, None]

        with self.assertRaises(KeyboardInterrupt):
            app.run()

        self.assertEqual(app.detector.detect.call_count, 2)
        self.assertEqual(app.sender.send.call_count, 2)
        print_mock.assert_any_call("Alert sent")
        app.stream.close.assert_called_once_with()

    @patch("app.alerts.time.monotonic", side_effect=[10.0, 11.0])
    @patch("app.alerts.build")
    def test_notification_sender_suppresses_messages_during_cooldown(
        self, build, monotonic
    ):
        credentials = Mock(valid=True, expired=False)
        sender = GmailAlertSender(
            credentials,
            None,
            "recipient@example.com",
            cooldown_seconds=60,
        )
        execute = build.return_value.users.return_value.messages.return_value.send.return_value.execute
        execute.return_value = {"id": "message-id"}

        first = sender.send("Emergence", "First event")
        second = sender.send("Emergence", "Duplicate event")

        self.assertEqual(first, {"id": "message-id"})
        self.assertIsNone(second)
        send = build.return_value.users.return_value.messages.return_value.send
        self.assertEqual(send.call_count, 1)


if __name__ == "__main__":
    unittest.main()
