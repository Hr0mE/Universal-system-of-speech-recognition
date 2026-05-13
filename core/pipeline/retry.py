from __future__ import annotations

import logging
from typing import Any, Callable


def retry_on_error(
    fn: Callable[[], Any],
    retries: int = 3,
    logger: logging.Logger | None = None,
) -> Any | None:
    """Calls fn() up to `retries` times. Returns None if all attempts raise."""
    if retries < 1:
        raise ValueError(f"retries must be >= 1, got {retries}")
    for attempt in range(1, retries + 1):
        try:
            return fn()
        except Exception as exc:
            if logger:
                logger.warning("Attempt %d/%d failed: %s", attempt, retries, exc)
    return None
