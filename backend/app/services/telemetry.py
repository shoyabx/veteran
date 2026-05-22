from __future__ import annotations

import json
import time
from dataclasses import dataclass


@dataclass
class Timer:
    start: float
    @classmethod
    def begin(cls) -> 'Timer':
        return cls(start=time.perf_counter())
    def elapsed_ms(self) -> int:
        return int((time.perf_counter() - self.start) * 1000)


def log_telemetry(event: str, payload: dict) -> None:
    print(json.dumps({'event': event, **payload}, default=str))
