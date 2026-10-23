"""Small in-process sliding-window rate limiter.

Good enough for a single-process deployment and demos. Behind several workers or
servers, swap this for a shared store (e.g. Flask-Limiter with Redis) – the
decorator interface stays the same.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from functools import wraps

from flask import current_app, request

from .errors import APIError

_hits: dict[str, deque] = defaultdict(deque)
_lock = threading.Lock()


def _client_key() -> str:
    # request.remote_addr is used deliberately: trusting X-Forwarded-For without a
    # configured proxy (werkzeug ProxyFix) would let clients spoof their identity.
    return request.remote_addr or "unknown"


def rate_limit(limit: int, per_seconds: int, scope: str):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if current_app.config.get("RATE_LIMIT_ENABLED", True):
                key = f"{scope}:{_client_key()}"
                now = time.monotonic()
                with _lock:
                    q = _hits[key]
                    while q and now - q[0] > per_seconds:
                        q.popleft()
                    if len(q) >= limit:
                        retry = int(per_seconds - (now - q[0])) + 1
                        raise APIError(f"Too many requests. Please wait {retry} seconds and try again.",
                                       429, "rate_limited", {"retry_after_seconds": retry})
                    q.append(now)
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def reset_rate_limits():
    with _lock:
        _hits.clear()
