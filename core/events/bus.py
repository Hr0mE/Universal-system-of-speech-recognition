from __future__ import annotations

import logging
import threading
from collections import defaultdict
from typing import Callable, TypeVar

from core.events.events import PipelineEvent

logger = logging.getLogger(__name__)

E = TypeVar("E", bound=PipelineEvent)
Handler = Callable[[E], None]


class EventBus:
    """Synchronous, type-based publish/subscribe bus.

    Handlers subscribe to a specific event class and receive every event
    whose `type(event) is that class`. Dispatch is in-order of subscription.
    Exceptions raised by a handler are logged and do not break the pipeline.
    """

    def __init__(self) -> None:
        self._handlers: dict[type, list[Handler]] = defaultdict(list)
        self._lock = threading.RLock()

    def subscribe(
        self, event_type: type[E], handler: Handler
    ) -> Callable[[], None]:
        with self._lock:
            self._handlers[event_type].append(handler)

        def unsubscribe() -> None:
            with self._lock:
                try:
                    self._handlers[event_type].remove(handler)
                except ValueError:
                    pass

        return unsubscribe

    def publish(self, event: PipelineEvent) -> None:
        with self._lock:
            handlers = list(self._handlers.get(type(event), ()))
        for handler in handlers:
            try:
                handler(event)
            except Exception:
                logger.exception(
                    "EventBus handler %r failed on %s",
                    handler,
                    type(event).__name__,
                )
