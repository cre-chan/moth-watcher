import unittest

from app.monitoring import StateEstimator


class StateEstimatorTests(unittest.TestCase):
    def test_update_returns_none_while_estimation_is_not_implemented(self):
        """羽化判定の実装前は検出結果を渡しても値を返さないことを確認する。"""
        estimator = StateEstimator()
        result = {"bbox": [], "features": []}

        self.assertIsNone(estimator.update(result))


if __name__ == "__main__":
    unittest.main()
