import importlib
import os
import unittest
from unittest.mock import MagicMock, patch

import numpy as np

from app.capture import VideoStream, VideoStreamFactory


class VideoStreamTests(unittest.TestCase):
    @patch("app.capture.cv2.VideoCapture")
    def test_initializes_capture_with_device_index(self, capture_cls):
        """指定したデバイス番号で映像キャプチャが初期化されることを確認する。"""
        stream = VideoStreamFactory.create_from_device(2, 640, 480)

        capture_cls.assert_called_once_with(2)
        self.assertEqual(stream.device_index, 2)

    @patch("app.capture.cv2.VideoCapture")
    def test_start_accepts_open_device(self, capture_cls):
        """利用可能なカメラデバイスを正常に開始できることを確認する。"""
        with patch.dict(os.environ, {"SHOW_CAPTURE_WINDOW": "true"}):
            VideoStreamFactory.create_from_device(0, 640, 480).start()

    @patch("app.capture.cv2.VideoCapture")
    def test_start_rejects_unavailable_device(self, capture_cls):
        """利用できないカメラデバイスの開始時に例外が発生することを確認する。"""
        capture_cls.return_value.isOpened.return_value = False

        with self.assertRaisesRegex(RuntimeError, "camera device: 3"):
            VideoStreamFactory.create_from_device(3, 640, 480).start()

    @patch("app.capture.cv2.VideoCapture")
    def test_read_frame_resizes_and_converts_to_grayscale(self, capture_cls):
        """読み込んだフレームが指定サイズのグレースケール画像になることを確認する。"""
        frame = np.zeros((10, 20, 3), dtype=np.uint8)
        frame[:, :, 1] = 255
        capture_cls.return_value.read.return_value = (True, frame)
        stream = VideoStreamFactory.create_from_device(0, 8, 6)

        result = stream.read_frame()

        self.assertEqual(result.shape, (6, 8))
        self.assertEqual(result.ndim, 2)

    @patch("app.capture.cv2.VideoCapture")
    def test_read_frame_raises_when_capture_fails(self, capture_cls):
        """フレームの取得に失敗した場合に例外が発生することを確認する。"""
        capture_cls.return_value.read.return_value = (False, None)

        with self.assertRaisesRegex(RuntimeError, "camera device: 1"):
            VideoStreamFactory.create_from_device(1, 640, 480).read_frame()

    @patch("app.capture.cv2.VideoCapture")
    def test_close_is_idempotent(self, capture_cls):
        """複数回終了してもキャプチャの解放が一度だけ行われることを確認する。"""
        capture = capture_cls.return_value
        stream = VideoStreamFactory.create_from_device(0, 640, 480)

        stream.close()
        stream.close()

        capture.release.assert_called_once_with()

    @patch("app.capture.cv2.VideoCapture")
    def test_factory_creates_device_stream(self, capture_cls):
        """Factoryが指定された設定のVideoStreamを生成することを確認する。"""
        stream = VideoStreamFactory.create_from_device(4, 320, 240)

        self.assertIsInstance(stream, VideoStream)
        capture_cls.assert_called_once_with(4)
        self.assertEqual((stream.width, stream.height), (320, 240))

    def test_url_factory_is_not_implemented(self):
        """未対応のURLストリーム生成がNotImplementedErrorを送出することを確認する。"""
        with self.assertRaises(NotImplementedError):
            VideoStreamFactory.create_from_url("rtsp://example.test/live", 640, 480)


class AppConfigCameraTests(unittest.TestCase):
    def test_camera_device_index_defaults_to_zero(self):
        """環境変数がない場合のカメラデバイス番号が0であることを確認する。"""
        with patch.dict(os.environ, {}, clear=True):
            import app.config as config_module
            config_module = importlib.reload(config_module)
            self.assertEqual(config_module.AppConfig.load().camera_device_index, 0)

    def test_camera_device_index_uses_environment_value(self):
        """環境変数で指定したカメラデバイス番号が設定に反映されることを確認する。"""
        with patch.dict(os.environ, {"CAMERA_DEVICE_INDEX": "5"}, clear=True):
            import app.config as config_module
            config_module = importlib.reload(config_module)
            self.assertEqual(config_module.AppConfig.load().camera_device_index, 5)


if __name__ == "__main__":
    unittest.main()
