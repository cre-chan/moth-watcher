import unittest

from app.monitoring import EmergenceEvent, StateEstimator


class StateEstimatorTests(unittest.TestCase):
    @staticmethod
    def result(count: int) -> dict[str, list]:
        """count個の検出結果を返す。"""
        return {"bbox": [(0, 0, 1, 1)] * count, "features": [{}] * count}

    def test_first_complete_window_only_sets_baseline(self):
        """
        最初の完全なwindowで羽化は検出されないことを検証する。

        1.0秒はwindow完成の境界値であり、0.0秒と0.5秒は完成前を表す。
        初期観測だけでは羽化と判定しない、という誤通知防止仕様に対応する。
        """
        estimator = StateEstimator(window_seconds=1.0)

        self.assertIsNone(estimator.update(self.result(1), observed_at=0.0))
        self.assertIsNone(estimator.update(self.result(1), observed_at=0.5))
        self.assertIsNone(estimator.update(self.result(1), observed_at=1.0))
        self.assertEqual(estimator.previous_median, 1.0)

    def test_increase_by_one_emits_event(self):
        """window中央値が基準から合計1増えたときにイベントが発生することを検証する。

        1.1秒時点の中央値1.5では増加が0.5なので保留し、1.2秒時点で中央値を
        2.0にすることで、偶数件の中央値が0.5ずつ動く境界条件を再現している。
        羽化の判定閾値を中央値の増加1以上とする仕様に対応する。
        """
        estimator = StateEstimator(window_seconds=1.0)
        estimator.update(self.result(1), observed_at=0.0)
        estimator.update(self.result(1), observed_at=1.0)

        self.assertIsNone(estimator.update(self.result(2), observed_at=1.1))
        event = estimator.update(self.result(2), observed_at=1.2)

        self.assertEqual(
            event,
            EmergenceEvent(previous_count=1.0, current_count=2.0, detected_at=1.2),
        )

    def test_increase_by_multiple_moths_emits_one_event(self):
        """複数匹の増加を検出しても1件の羽化イベントだけを発生させることを検証する。

        検出数を1から4へ急増させ、同じ増加が連続windowへ残る状況を再現している。
        増加量にかかわらず1回の増加を1イベントとして扱う重複通知防止仕様に対応する。
        """
        estimator = StateEstimator(window_seconds=1.0)
        estimator.update(self.result(1), observed_at=0.0)
        estimator.update(self.result(1), observed_at=1.0)

        event = estimator.update(self.result(4), observed_at=1.1)
        duplicate = estimator.update(self.result(4), observed_at=1.2)

        self.assertIsInstance(event, EmergenceEvent)
        self.assertIsNone(duplicate)

    def test_same_or_lower_median_does_not_emit_event(self):
        """中央値が同じ場合と低下した場合にイベントを発生させないことを検証する。

        基準値2に対して同値2と減少値0を与え、非増加の両経路を再現している。
        減少は通知せず、次の増加判定に使う比較基準だけを更新する仕様に対応する。
        """
        estimator = StateEstimator(window_seconds=1.0)
        estimator.update(self.result(2), observed_at=0.0)
        estimator.update(self.result(2), observed_at=1.0)

        self.assertIsNone(estimator.update(self.result(2), observed_at=1.1))
        self.assertIsNone(estimator.update(self.result(0), observed_at=2.2))
        self.assertEqual(estimator.previous_median, 0.0)

    def test_expired_observations_are_removed(self):
        """現在の時間windowより古い観測値が中央値計算から除外されることを検証する。

        1.6秒時点の1秒windowは0.6秒以降なので、0.0秒と0.5秒を期限切れにする。
        フレーム数ではなく観測時刻に基づくsliding windowを使う仕様に対応する。
        """
        estimator = StateEstimator(window_seconds=1.0)
        estimator.update(self.result(1), observed_at=0.0)
        estimator.update(self.result(2), observed_at=0.5)

        estimator.update(self.result(3), observed_at=1.6)

        self.assertEqual(list(estimator.observations), [(1.6, 3)])

    def test_rejects_timestamp_that_moves_backwards(self):
        """直前より古い観測時刻を受け付けず、計算順序を保護することを検証する。

        1.0秒の後に0.9秒を渡し、時刻が0.1秒逆行する不正入力を明示的に作る。
        時系列順を前提とするwindowの破損を例外で防止する入力制約に対応する。
        """
        estimator = StateEstimator(window_seconds=1.0)
        estimator.update(self.result(1), observed_at=1.0)

        with self.assertRaisesRegex(ValueError, "must not move backwards"):
            estimator.update(self.result(1), observed_at=0.9)


if __name__ == "__main__":
    unittest.main()
