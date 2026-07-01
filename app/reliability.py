"""Runtime reliability helpers for the Flask API."""

from __future__ import annotations

import logging
import time
import uuid
from collections import defaultdict, deque
from threading import Lock
from typing import Deque, Dict, Tuple

from flask import Response, current_app, g, jsonify, request
from werkzeug.exceptions import HTTPException


LOGGER_NAME = "ai_job_recommender"
PROTECTED_ENDPOINTS = {
    "telegram_jobs_ingest",
    "telegram_jobs_refresh",
}


def configure_logging(level: str) -> logging.Logger:
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.addFilter(RequestIdFilter())
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)s %(name)s "
                "request_id=%(request_id)s %(message)s"
            )
        )
        logger.addHandler(handler)
    return logger


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            record.request_id = getattr(g, "request_id", "-")
        except RuntimeError:
            record.request_id = "-"
        return True


class InMemoryRateLimiter:
    """Small per-process rate limiter suitable for a single Flask worker."""

    def __init__(self) -> None:
        self._events: Dict[str, Deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def allow(self, key: str, limit: int, window_seconds: int = 60) -> Tuple[bool, int]:
        now = time.monotonic()
        cutoff = now - window_seconds
        with self._lock:
            events = self._events[key]
            while events and events[0] < cutoff:
                events.popleft()
            remaining = max(0, limit - len(events))
            if remaining <= 0:
                return False, 0
            events.append(now)
            return True, remaining - 1

    def clear(self) -> None:
        with self._lock:
            self._events.clear()


rate_limiter = InMemoryRateLimiter()


def request_id() -> str:
    incoming = request.headers.get("X-Request-Id", "").strip()
    return incoming[:80] if incoming else uuid.uuid4().hex


def client_ip() -> str:
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",", 1)[0].strip()
    return request.remote_addr or "unknown"


def reliability_before_request():
    g.request_id = request_id()
    if request.method == "OPTIONS":
        return None

    auth_response = _require_api_key_if_configured()
    if auth_response is not None:
        return auth_response

    return _check_rate_limit()


def reliability_after_request(response: Response) -> Response:
    response.headers["X-Request-Id"] = getattr(g, "request_id", "-")
    if hasattr(g, "rate_limit_remaining"):
        response.headers["X-RateLimit-Remaining"] = str(g.rate_limit_remaining)
    current_app.logger.info(
        "%s %s -> %s",
        request.method,
        request.path,
        response.status_code,
    )
    return response


def _require_api_key_if_configured():
    api_key = current_app.config.get("API_KEY", "")
    require_key = bool(current_app.config.get("REQUIRE_API_KEY", False))
    if not api_key and not require_key:
        return None
    if request.endpoint not in PROTECTED_ENDPOINTS and not require_key:
        return None

    supplied = request.headers.get("X-API-Key") or request.args.get("api_key")
    if supplied and api_key and supplied == api_key:
        return None
    return jsonify({"error": "API key required", "request_id": g.request_id}), 401


def _check_rate_limit():
    if not current_app.config.get("RATE_LIMIT_ENABLED", True):
        return None
    is_write = request.method in {"POST", "PUT", "PATCH", "DELETE"}
    limit = (
        current_app.config.get("RATE_LIMIT_WRITE_PER_MINUTE", 30)
        if is_write
        else current_app.config.get("RATE_LIMIT_PUBLIC_PER_MINUTE", 120)
    )
    key = f"{client_ip()}:{request.endpoint or request.path}:{request.method}"
    allowed, remaining = rate_limiter.allow(key, int(limit), window_seconds=60)
    g.rate_limit_remaining = remaining
    if allowed:
        return None
    return jsonify({"error": "Rate limit exceeded", "request_id": g.request_id}), 429


def json_http_error(error: HTTPException):
    response = jsonify(
        {
            "error": error.description or error.name,
            "request_id": getattr(g, "request_id", "-"),
        }
    )
    response.status_code = error.code or 500
    return response


def json_unhandled_error(error: Exception):
    current_app.logger.exception("Unhandled API error: %s", error)
    response = jsonify(
        {
            "error": "Internal server error",
            "request_id": getattr(g, "request_id", "-"),
        }
    )
    response.status_code = 500
    return response
