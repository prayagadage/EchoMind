"""Thread-safe event bus implementing the Publish-Subscribe pattern.

Decouples event producers (e.g. AudioEngine) from event consumers
(e.g. Whisper STT, Keyword Alerts, UI visualizers).
"""

from collections import defaultdict
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Any, TypeVar

from loguru import logger

T = TypeVar("T")
EventHandler = Callable[[Any], None]


class EventBus:
    """Thread-safe asynchronous Event Bus routing typed domain events."""

    def __init__(self, max_workers: int = 4) -> None:
        """Initialize EventBus with background execution thread pool.

        Args:
            max_workers: Maximum worker threads for executing event subscribers.
        """
        self._subscribers: dict[type[Any], list[EventHandler]] = defaultdict(list)
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix="event_bus_worker"
        )
        logger.debug(f"EventBus initialized with max_workers={max_workers}")

    def subscribe(self, event_type: type[T], handler: Callable[[T], None]) -> None:
        """Register a subscriber handler for a specific event type.

        Args:
            event_type: The class of the event to listen for.
            handler: Callable invoked when an event of event_type is published.
        """
        if handler not in self._subscribers[event_type]:
            self._subscribers[event_type].append(handler)
            logger.debug(
                f"Subscribed handler '{handler.__name__}' "
                f"to event '{event_type.__name__}'"
            )

    def unsubscribe(self, event_type: type[T], handler: Callable[[T], None]) -> None:
        """Unregister a subscriber handler for an event type.

        Args:
            event_type: The class of the event.
            handler: Callable to remove.
        """
        if handler in self._subscribers[event_type]:
            self._subscribers[event_type].remove(handler)
            logger.debug(
                f"Unsubscribed handler '{handler.__name__}' "
                f"from event '{event_type.__name__}'"
            )

    def publish(self, event: Any) -> None:
        """Publish an event to all registered subscribers asynchronously.

        Args:
            event: The event instance to dispatch.
        """
        event_type = type(event)
        subscribers = self._subscribers.get(event_type, [])

        if not subscribers:
            return

        for handler in subscribers:
            self._executor.submit(self._safe_dispatch, handler, event)

    def _safe_dispatch(self, handler: EventHandler, event: Any) -> None:
        """Safely execute subscriber handler isolating exceptions.

        Args:
            handler: Subscriber callable to invoke.
            event: Event object payload.
        """
        try:
            handler(event)
        except Exception as exc:
            logger.error(
                f"Error in EventBus handler '{handler.__name__}' for event "
                f"'{type(event).__name__}': {exc}",
                exc_info=True,
            )

    def shutdown(self) -> None:
        """Shutdown the underlying thread pool executor."""
        logger.debug("Shutting down EventBus executor pool...")
        self._executor.shutdown(wait=False)
