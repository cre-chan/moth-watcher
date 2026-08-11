from __future__ import annotations

import math
from collections import deque


class StateEstimator:
    def __init__(self, history_size: int = 8):
        self.history_size = history_size
        self.history: deque[dict[str, float]] = deque(maxlen=history_size)

    def update(self, features: dict[str, float]) -> dict[str, float]:
        self.history.append(features)
        if len(self.history) < 2:
            return self._default_scores()

        latest = self.history[-1]
        prev = self.history[-2]
        area_change = latest["area"] - prev["area"]
        centroid_move = math.hypot(latest["centroid_x"] - prev["centroid_x"], latest["centroid_y"] - prev["centroid_y"])
        extent_change = latest["extent"] - prev["extent"]
        circularity_change = latest["circularity"] - prev["circularity"]

        molting_score = min(1.0, max(0.0, 0.4 + 0.3 * max(0.0, area_change / 100.0) + 0.3 * max(0.0, extent_change)))
        pupation_score = min(1.0, max(0.0, 0.2 + 0.4 * max(0.0, -extent_change) + 0.4 * max(0.0, -circularity_change)))
        hunger_score = min(1.0, max(0.0, 0.3 + 0.4 * max(0.0, centroid_move / 50.0) + 0.3 * max(0.0, abs(area_change) / 100.0)))

        return {
            "molting_probability": round(molting_score, 3),
            "pupation_probability": round(pupation_score, 3),
            "hunger_probability": round(hunger_score, 3),
        }

    def _default_scores(self) -> dict[str, float]:
        return {
            "molting_probability": 0.0,
            "pupation_probability": 0.0,
            "hunger_probability": 0.0,
        }
