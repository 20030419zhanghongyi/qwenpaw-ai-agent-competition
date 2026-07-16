"""Short-lived, anonymous session deduplication for POI proximity prompts."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import threading


class TriggerState:
    """Keep only the last prompt time for a ``(session_id, poi_id)`` pair.

    State is deliberately process-local: it avoids retaining location histories
    or requiring a migration for the competition MVP.
    """

    def __init__(self, cooldown: timedelta = timedelta(minutes=10)) -> None:
        self._cooldown = cooldown
        self._last_prompted: dict[tuple[str, str], datetime] = {}
        self._lock = threading.Lock()

    def allow_prompt(self, *, session_id: str, poi_id: str, now: datetime | None = None) -> bool:
        """Return whether a POI prompt may be shown, recording allowed prompts."""
        current = now or datetime.now(timezone.utc)
        if current.tzinfo is None:
            current = current.replace(tzinfo=timezone.utc)

        with self._lock:
            expires_before = current - self._cooldown
            self._last_prompted = {
                key: timestamp
                for key, timestamp in self._last_prompted.items()
                if timestamp > expires_before
            }
            key = (session_id, poi_id)
            previous = self._last_prompted.get(key)
            if previous is not None and current - previous < self._cooldown:
                return False
            self._last_prompted[key] = current
            return True

    def clear(self) -> None:
        """Clear process-local state; used by tests and local development."""
        with self._lock:
            self._last_prompted.clear()


trigger_state = TriggerState()
