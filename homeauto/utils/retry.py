import time
import functools
from typing import Callable, Type, Tuple


def retry_with_backoff(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,)
):
    """
    Decorator for retrying a function with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts
        base_delay: Initial delay between retries in seconds
        backoff_factor: Multiplier for delay after each retry
        exceptions: Tuple of exception types to catch and retry
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            delay = base_delay
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        time.sleep(delay)
                        delay *= backoff_factor

            # All attempts exhausted, raise the last exception
            raise last_exception

        return wrapper
    return decorator
