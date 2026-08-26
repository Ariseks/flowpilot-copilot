from __future__ import annotations

import json
import logging
import time
from collections import defaultdict, deque
from threading import Lock
from typing import Any

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response


class JsonFormatter(logging.Formatter):
    """Emit one compact JSON object per log record for container collection."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
            "level": record.levelname.lower(),
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "event"):
            payload["event"] = record.event
        if hasattr(record, "fields"):
            payload.update(record.fields)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def configure_logging() -> None:
    root = logging.getLogger()
    if root.handlers:
        for handler in root.handlers:
            handler.setFormatter(JsonFormatter())
        root.setLevel(logging.INFO)
        return
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)
    root.setLevel(logging.INFO)


class Metrics:
    def __init__(self) -> None:
        self._lock = Lock()
        self.started_at = time.time()
        self.requests_total = 0
        self.responses_total = 0
        self.errors_total = 0
        self.rate_limited_total = 0
        self.in_flight = 0
        self.by_method: dict[str, int] = defaultdict(int)
        self.by_path: dict[str, int] = defaultdict(int)
        self.by_status: dict[str, int] = defaultdict(int)
        self.latencies_ms: deque[float] = deque(maxlen=500)

    def request_started(self) -> None:
        with self._lock:
            self.requests_total += 1
            self.in_flight += 1

    def request_finished(self, method: str, path: str, status_code: int, latency_ms: float) -> None:
        with self._lock:
            self.responses_total += 1
            self.in_flight = max(0, self.in_flight - 1)
            self.by_method[method] += 1
            self.by_path[path] += 1
            self.by_status[str(status_code)] += 1
            self.latencies_ms.append(latency_ms)
            if status_code >= 500:
                self.errors_total += 1

    def rate_limited(self) -> None:
        with self._lock:
            self.rate_limited_total += 1

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            latencies = sorted(self.latencies_ms)
            return {
                "uptime_seconds": round(time.time() - self.started_at, 3),
                "requests_total": self.requests_total,
                "responses_total": self.responses_total,
                "errors_total": self.errors_total,
                "rate_limited_total": self.rate_limited_total,
                "in_flight": self.in_flight,
                "by_method": dict(sorted(self.by_method.items())),
                "by_path": dict(sorted(self.by_path.items())),
                "by_status": dict(sorted(self.by_status.items())),
                "latency_ms": {
                    "count": len(latencies),
                    "p50": _percentile(latencies, 0.50),
                    "p95": _percentile(latencies, 0.95),
                    "max": round(latencies[-1], 2) if latencies else 0,
                },
            }


def _percentile(values: list[float], ratio: float) -> float:
    if not values:
        return 0
    index = min(len(values) - 1, max(0, int(round((len(values) - 1) * ratio))))
    return round(values[index], 2)


class FixedWindowLimiter:
    """Small single-process limiter for demo protection, not a distributed quota."""

    def __init__(self, limit: int, window_seconds: int) -> None:
        self.limit = max(0, limit)
        self.window_seconds = max(1, window_seconds)
        self._lock = Lock()
        self._windows: dict[str, tuple[int, int]] = {}

    def allow(self, key: str) -> bool:
        if self.limit == 0:
            return True
        now = int(time.time())
        window = now // self.window_seconds
        with self._lock:
            current_window, count = self._windows.get(key, (window, 0))
            if current_window != window:
                count = 0
                current_window = window
            if count >= self.limit:
                self._windows[key] = (current_window, count)
                return False
            self._windows[key] = (current_window, count + 1)
            if len(self._windows) > 2048:
                self._windows = {
                    item_key: item
                    for item_key, item in self._windows.items()
                    if item[0] >= window
                }
            return True


class ObservabilityMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, metrics: Metrics, limiter: FixedWindowLimiter, logger: logging.Logger) -> None:
        super().__init__(app)
        self.metrics = metrics
        self.limiter = limiter
        self.logger = logger

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        if path.startswith("/api/"):
            client_host = request.client.host if request.client else "unknown"
            if not self.limiter.allow(client_host):
                self.metrics.rate_limited()
                self.logger.warning(
                    "request rate limited",
                    extra={"event": "rate_limited", "fields": {"method": request.method, "path": path}},
                )
                return JSONResponse(
                    {"detail": "请求过于频繁，请稍后重试"},
                    status_code=429,
                    headers={"Retry-After": str(self.limiter.window_seconds)},
                )

        started = time.perf_counter()
        self.metrics.request_started()
        try:
            response = await call_next(request)
        except Exception:
            latency_ms = (time.perf_counter() - started) * 1000
            self.metrics.request_finished(request.method, path, 500, latency_ms)
            self.logger.exception(
                "request failed",
                extra={"event": "request_failed", "fields": {"method": request.method, "path": path, "status_code": 500, "latency_ms": round(latency_ms, 2)}},
            )
            raise
        latency_ms = (time.perf_counter() - started) * 1000
        self.metrics.request_finished(request.method, path, response.status_code, latency_ms)
        self.logger.info(
            "request completed",
            extra={
                "event": "request_completed",
                "fields": {
                    "method": request.method,
                    "path": path,
                    "status_code": response.status_code,
                    "latency_ms": round(latency_ms, 2),
                },
            },
        )
        response.headers["X-Request-Latency-Ms"] = str(round(latency_ms, 2))
        return response
