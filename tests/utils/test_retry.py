import pytest
import time
from homeauto.utils.retry import retry_with_backoff


def test_retry_succeeds_first_try():
    call_count = 0

    @retry_with_backoff(max_attempts=3, base_delay=0.1)
    def succeeds_immediately():
        nonlocal call_count
        call_count += 1
        return "success"

    result = succeeds_immediately()
    assert result == "success"
    assert call_count == 1


def test_retry_succeeds_after_failures():
    call_count = 0

    @retry_with_backoff(max_attempts=3, base_delay=0.1)
    def succeeds_on_third_try():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ConnectionError("Failed")
        return "success"

    result = succeeds_on_third_try()
    assert result == "success"
    assert call_count == 3


def test_retry_exhausts_attempts():
    call_count = 0

    @retry_with_backoff(max_attempts=3, base_delay=0.1)
    def always_fails():
        nonlocal call_count
        call_count += 1
        raise ConnectionError("Always fails")

    with pytest.raises(ConnectionError):
        always_fails()

    assert call_count == 3
