"""A deterministic, dependency-free TTS engine for tests."""

from __future__ import annotations

from typing import Callable, List, Optional

import numpy as np

from audiobooker.engine import Engine


class FakeEngine(Engine):
    """Produces a sine tone whose length is proportional to the text."""

    name = "fake"

    def __init__(
        self,
        sample_rate: int = 8000,
        chars_per_second: float = 200.0,
        fail_on: Optional[Callable[[str], bool]] = None,
        fail_times: int = 0,
    ):
        self.sample_rate = sample_rate
        self.chars_per_second = chars_per_second
        self.fail_on = fail_on
        self.fail_times = fail_times
        self.remaining_failures = fail_times
        self.calls: List[str] = []
        self.prepares = 0

    def prepare(self) -> None:
        self.prepares += 1

    def generate(self, text: str, *, exaggeration: float, cfg_weight: float) -> np.ndarray:
        self.calls.append(text)
        if self.fail_on is not None and self.fail_on(text) and self.remaining_failures != 0:
            if self.remaining_failures > 0:
                self.remaining_failures -= 1
            raise RuntimeError("synthetic engine failure")

        frames = max(1, int(len(text) / self.chars_per_second * self.sample_rate))
        timeline = np.arange(frames, dtype=np.float32) / self.sample_rate
        return (0.2 * np.sin(2.0 * np.pi * 220.0 * timeline)).astype(np.float32)


class CountingFailer:
    """Fails on the n-th call (1-based), optionally only once."""

    def __init__(self, target: int, times: int = 1):
        self.target = target
        self.times = times
        self.seen = 0

    def __call__(self, text: str) -> bool:
        self.seen += 1
        if self.seen == self.target and self.times > 0:
            self.times -= 1
            return True
        return False
