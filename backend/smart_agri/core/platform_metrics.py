
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from threading import Lock


@dataclass
class PlatformMetricsRegistry:
    request_counts: Counter = field(default_factory=Counter)
    response_status_counts: Counter = field(default_factory=Counter)
    response_time_ms_total: Counter = field(default_factory=Counter)
    _lock: Lock = field(default_factory=Lock)

    def record(self, path: str, method: str, status_code: int, duration_ms: int) -> None:
        key = f"{method} {path}"
        with self._lock:
            self.request_counts[key] += 1
            self.response_status_counts[f"{status_code}"] += 1
            self.response_time_ms_total[key] += max(duration_ms, 0)

    def snapshot(self) -> dict[str, dict[str, int]]:
        with self._lock:
            average_response_ms = {
                key: int(self.response_time_ms_total[key] / count)
                for key, count in self.request_counts.items() if count
            }
            return {
                'requests': dict(self.request_counts),
                'status_codes': dict(self.response_status_counts),
                'average_response_ms': average_response_ms,
            }


platform_metrics = PlatformMetricsRegistry()
