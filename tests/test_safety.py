# tests/test_safety.py
"""Tests for the safety module."""

import os
import sys
from unittest import mock

import pytest

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "mcp-servers", "handson-server"),
)


class TestActionTimeout:
    def test_fast_action_succeeds(self):
        from tools.safety import with_timeout
        result = with_timeout(lambda: "ok", timeout=5.0)
        assert result == "ok"

    def test_slow_action_raises(self):
        import time
        from tools.safety import with_timeout, ActionTimeoutError
        with pytest.raises(ActionTimeoutError):
            with_timeout(lambda: time.sleep(10), timeout=0.1)


class TestCircuitBreaker:
    def test_resets_on_success(self):
        from tools.safety import CircuitBreaker
        cb = CircuitBreaker(max_failures=3)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        assert cb.is_open is False
        assert cb.consecutive_failures == 0

    def test_opens_after_max_failures(self):
        from tools.safety import CircuitBreaker
        cb = CircuitBreaker(max_failures=3)
        cb.record_failure()
        cb.record_failure()
        cb.record_failure()
        assert cb.is_open is True

    def test_check_raises_when_open(self):
        from tools.safety import CircuitBreaker, CircuitOpenError
        cb = CircuitBreaker(max_failures=2)
        cb.record_failure()
        cb.record_failure()
        with pytest.raises(CircuitOpenError):
            cb.check()

    def test_check_ok_when_closed(self):
        from tools.safety import CircuitBreaker
        cb = CircuitBreaker(max_failures=5)
        cb.record_failure()
        cb.check()  # Should not raise


class TestDesktopGuard:
    @mock.patch("tools.safety._desktop_state", {"on_isolated": True})
    def test_allows_when_isolated(self):
        from tools.safety import check_desktop_guard
        # Should not raise
        check_desktop_guard()

    @mock.patch("tools.safety._desktop_state", {"on_isolated": False})
    def test_returns_none_when_not_isolated(self):
        from tools.safety import check_desktop_guard
        result = check_desktop_guard()
        assert result is None  # Not on isolated desktop is fine — returns None
