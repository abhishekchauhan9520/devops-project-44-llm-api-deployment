import os
import threading
import time
from collections import defaultdict


RATE_LIMIT_RPM = int(os.getenv("RATE_LIMIT_RPM", "60"))

_bucket_lock = threading.Lock()
_requests: dict[str, list[float]] = defaultdict(list)


def allow_request(identity: str) -> bool:
    now = time.time()
    window_start = now - 60.0
    with _bucket_lock:
        timestamps = [t for t in _requests[identity] if t > window_start]
        if len(timestamps) >= RATE_LIMIT_RPM:
            _requests[identity] = timestamps
            return False
        timestamps.append(now)
        _requests[identity] = timestamps
        return True
