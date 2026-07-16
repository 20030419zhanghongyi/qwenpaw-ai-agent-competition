"""Shared input isolation, request rate limits, and audit persistence."""

from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Callable
from datetime import timedelta
import hashlib
import hmac
import logging
import threading
import time
from typing import Any

from fastapi import HTTPException, Request, Response, status
from sqlalchemy import delete

from app.core.config import settings
from app.db.base import utc_now
from app.db.models import AuditEvent
from app.db.session import SessionLocal

logger = logging.getLogger("macau_storywalk.guardrails")

TEXT_LIMIT = (20, 60.0)
EXPENSIVE_LIMIT = (5, 60.0)


def sanitize_untrusted_text(value: str, *, max_length: int = 4000) -> str:
    """Keep user content data-only: remove controls and cap prompt size."""
    cleaned = "".join(char for char in (value or "") if char == "\n" or ord(char) >= 32).strip()
    return cleaned[:max_length]


class SlidingWindowLimiter:
    def __init__(self) -> None:
        self._hits: dict[tuple[str, str], deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str, bucket: str, *, limit: int, window_seconds: float) -> int | None:
        now = time.monotonic()
        with self._lock:
            hits = self._hits[(key, bucket)]
            while hits and hits[0] <= now - window_seconds:
                hits.popleft()
            if len(hits) >= limit:
                return max(1, int(window_seconds - (now - hits[0])))
            hits.append(now)
        return None

    def clear(self) -> None:
        with self._lock:
            self._hits.clear()


rate_limiter = SlidingWindowLimiter()


def rate_limit(bucket: str) -> Callable[[Request, Response], None]:
    limit, window = EXPENSIVE_LIMIT if bucket == "expensive" else TEXT_LIMIT

    def dependency(request: Request, response: Response) -> None:
        client_ip = request.client.host if request.client else "unknown"
        retry_after = rate_limiter.check(client_ip, bucket, limit=limit, window_seconds=window)
        if retry_after is not None:
            response.headers["Retry-After"] = str(retry_after)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="request rate limit exceeded; retry later",
                headers={"Retry-After": str(retry_after)},
            )

    return dependency


def _hash_subject(subject: str | None) -> str | None:
    if not subject:
        return None
    secret = settings.audit_hash_salt or settings.jwt_secret
    return hmac.new(secret.encode(), subject.encode(), hashlib.sha256).hexdigest()


def record_audit(
    *,
    kind: str,
    status: str,
    subject: str | None = None,
    agent_id: str | None = None,
    latency_ms: int | None = None,
    tokens: dict[str, int] | None = None,
    decision: str | None = None,
    input_chars: int | None = None,
    output_chars: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Persist non-sensitive audit metadata. Failure never blocks product flow."""
    try:
        cutoff = utc_now() - timedelta(days=settings.audit_retention_days)
        with SessionLocal() as session:
            session.execute(delete(AuditEvent).where(AuditEvent.created_at < cutoff))
            session.add(
                AuditEvent(
                    kind=kind,
                    status=status,
                    subject_hash=_hash_subject(subject),
                    agent_id=agent_id,
                    model_version=settings.model_version,
                    prompt_version=settings.prompt_version,
                    latency_ms=latency_ms,
                    token_usage=tokens,
                    metadata_json=metadata,
                    decision=decision,
                    input_chars=input_chars,
                    output_chars=output_chars,
                )
            )
            session.commit()
    except Exception as exc:  # noqa: BLE001
        logger.warning("audit persistence failed: %s", exc)
