import importlib
import os
import unittest
from unittest.mock import MagicMock, patch

import numpy as np

from app.capture import VideoStream, VideoStreamFactory


class VideoStreamTests(unittest.TestCase):
    @patch("app.capture.cv2.VideoCapture")
    def test_initializes_capture_with_device_index(self, capture_cls):
        stream = VideoStream(2, 640, 480)

        capture_cls.assert_called_once_with(2)
        self.assertEqual(stream.device_index, 2)

    @patch("app.capture.cv2.VideoCapture")
    def test_start_accepts_open_device(self, capture_cls):
        capture_cls.return_value.isOpened.return_value = True

        VideoStream(0, 640, 480).start()

    @patch("app.capture.cv2.VideoCapture")
    def test_start_rejects_unavailable_device(self, capture_cls):
        capture_cls.return_value.isOpened.return_value = False

        with self.assertRaisesRegex(RuntimeError, "camera device: 3"):
            VideoStream(3, 640, 480).start()

    @patch("app.capture.cv2.VideoCapture")
    def test_read_frame_resizes_and_converts_to_grayscale(self, capture_cls):
        frame = np.zeros((10, 20, 3), dtype=np.uint8)
        frame[:, :, 1] = 255
        capture_cls.return_value.read.return_value = (True, frame)
        stream = VideoStream(0, 8, 6)

        result = stream.read_frame()

        self.assertEqual(result.shape, (6, 8))
        self.assertEqual(result.ndim, 2)

    @patch("app.capture.cv2.VideoCapture")
    def test_read_frame_raises_when_capture_fails(self, capture_cls):
        capture_cls.return_value.read.return_value = (False, None)

        with self.assertRaisesRegex(RuntimeError, "camera device: 1"):
            VideoStream(1, 640, 480).read_frame()

    @patch("app.capture.cv2.VideoCapture")
    def test_close_is_idempotent(self, capture_cls):
        capture = capture_cls.return_value
        stream = VideoStream(0, 640, 480)

        stream.close()
        stream.close()

        capture.release.assert_called_once_with()

    @patch("app.capture.cv2.VideoCapture")
    def test_factory_creates_device_stream(self, capture_cls):
        stream = VideoStreamFactory.create_from_device(4, 320, 240)

        self.assertIsInstance(stream, VideoStream)
        capture_cls.assert_called_once_with(4)
        self.assertEqual((stream.width, stream.height), (320, 240))

    def test_url_factory_is_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            VideoStreamFactory.create_from_url("rtsp://example.test/live", 640, 480)


class AppConfigCameraTests(unittest.TestCase):
    def test_camera_device_index_defaults_to_zero(self):
        with patch.dict(os.environ, {}, clear=True):
            import app.config as config_module
            config_module = importlib.reload(config_module)
            self.assertEqual(config_module.AppConfig.load().camera_device_index, 0)

    def test_camera_device_index_uses_environment_value(self):
        with patch.dict(os.environ, {"CAMERA_DEVICE_INDEX": "5"}, clear=True):
            import app.config as config_module
            config_module = importlib.reload(config_module)
            self.assertEqual(config_module.AppConfig.load().camera_device_index, 5)


if __name__ == "__main__":
    unittest.main()
