"""Shared pytest isolation for mutable runtime state."""

import pytest

from app.guardrails.runtime import rate_limiter


@pytest.fixture(autouse=True)
def isolate_runtime_state():
    """Reset shared rate counters without overriding settings from .env."""
    rate_limiter.clear()
    yield
    rate_limiter.clear()
