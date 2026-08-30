from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from statistics import median
import time


@dataclass(frozen=True)
class EmergenceEvent:
    """成虫数の増加から確定した1件の羽化イベント。"""

    previous_count: float
    current_count: float
    detected_at: float

    @property
    def count_increase(self) -> float:
        return self.current_count - self.previous_count


class StateEstimator:
    """時刻ベースのsliding windowで成虫数の増加を検出する。"""

    def __init__(self, window_seconds: float = 1.0):
        if window_seconds <= 0:
            raise ValueError("window_seconds must be greater than 0.")
        self.window_seconds = window_seconds
        self.observations: deque[tuple[float, int]] = deque()
        self.started_at: float | None = None
        self.previous_median: float | None = None
        self.last_median: float | None = None
        self.increase_in_progress = False

    def update(
        self,
        result: dict[str, list],
        observed_at: float | None = None,
    ) -> EmergenceEvent | None:
        """検出数を追加し、直前のwindow中央値から1以上増えた場合に通知する。"""
        bboxes = result.get("bbox")
        if not isinstance(bboxes, list):
            raise ValueError("Detection result must contain a list value for 'bbox'.")

        timestamp = time.time() if observed_at is None else observed_at
        if self.observations and timestamp < self.observations[-1][0]:
            raise ValueError("observed_at must not move backwards.")
        if self.started_at is None:
            self.started_at = timestamp

        self.observations.append((timestamp, len(bboxes)))
        window_start = timestamp - self.window_seconds
        while self.observations and self.observations[0][0] < window_start:
            self.observations.popleft()

        # 最初のwindowが満たされるまでは比較基準を作らない。
        if timestamp - self.started_at < self.window_seconds:
            return None

        current_median = float(median(count for _, count in self.observations))
        if self.previous_median is None:
            self.previous_median = current_median
            self.last_median = current_median
            return None

        previous_median = self.previous_median
        if self.increase_in_progress:
            # 1回の増加がwindow内で段階的に現れてもイベントを分割しない。
            if self.last_median is not None and current_median <= self.last_median:
                self.increase_in_progress = False
                self.previous_median = current_median
            self.last_median = current_median
            return None

        if current_median < previous_median:
            # 減少は通知せず、次の増加を測るための基準だけを更新する。
            self.previous_median = current_median
            self.last_median = current_median
            return None
        if current_median - previous_median < 1:
            # 偶数件の中央値が0.5ずつ動いても、合計+1を見逃さない。
            self.last_median = current_median
            return None

        self.increase_in_progress = True
        self.last_median = current_median

        return EmergenceEvent(
            previous_count=previous_median,
            current_count=current_median,
            detected_at=timestamp,
        )
