import time
from collections import deque


class Profiler:
    def __init__(self, window_size: int = 60) -> None:
        self.window_size = window_size
        self.timings: dict[str, deque[float]] = {}
        self.active_sections: dict[str, float] = {}

    def start_section(self, name: str) -> None:
        self.active_sections[name] = time.perf_counter()

    def end_section(self, name: str) -> None:
        start_time = self.active_sections.pop(name, None)
        if start_time is None:
            return

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        self.record(name, elapsed_ms)

    def record(self, name: str, elapsed_ms: float) -> None:
        if name not in self.timings:
            self.timings[name] = deque(maxlen=self.window_size)
        self.timings[name].append(elapsed_ms)

    def get_average(self, name: str) -> float:
        values = self.timings.get(name)
        if not values:
            return 0.0
        return sum(values) / len(values)

    def get_latest(self, name: str) -> float:
        values = self.timings.get(name)
        if not values:
            return 0.0
        return values[-1]

    def reset(self) -> None:
        self.timings.clear()
        self.active_sections.clear()
