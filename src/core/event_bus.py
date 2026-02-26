"""Event bus for asynchronous event handling"""

import asyncio
from typing import Callable, Dict, List, Optional
from collections import defaultdict
import logging
from datetime import datetime

from .event import Event, EventType


class EventBus:
    """Asynchronous event bus

    Responsible for event subscription, publishing, and dispatching. Uses a priority queue
    to process events and supports concurrent event handling by multiple subscribers.
    """

    def __init__(self, max_queue_size: int = 10000):
        """Initialize event bus

        Args:
            max_queue_size: Maximum size of the event queue
        """
        self._subscribers: Dict[EventType, List[Callable]] = defaultdict(list)
        self._event_queue: asyncio.PriorityQueue = asyncio.PriorityQueue(maxsize=max_queue_size)
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._logger = logging.getLogger(__name__)
        self._event_counter = 0

    def subscribe(self, event_type: EventType, handler: Callable):
        """Subscribe to events

        Args:
            event_type: Event type
            handler: Event handler function (can be synchronous or asynchronous)
        """
        self._subscribers[event_type].append(handler)
        self._logger.info(f"Handler {handler.__name__} subscribed to {event_type.value}")

    def unsubscribe(self, event_type: EventType, handler: Callable):
        """Unsubscribe from events

        Args:
            event_type: Event type
            handler: Event handler function
        """
        if handler in self._subscribers[event_type]:
            self._subscribers[event_type].remove(handler)
            self._logger.info(f"Handler {handler.__name__} unsubscribed from {event_type.value}")

    async def publish(self, event: Event):
        """Publish event

        Args:
            event: Event object
        """
        if not self._running:
            self._logger.warning("Event bus is not running, event will be queued")

        # Use counter to ensure events with the same priority are processed in publication order
        self._event_counter += 1
        await self._event_queue.put((event.priority, self._event_counter, event))
        self._logger.debug(f"Event published: {event.event_type.value} (priority={event.priority})")

    async def start(self):
        """Start event loop"""
        if self._running:
            self._logger.warning("Event bus is already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._event_loop())
        self._logger.info("Event bus started")

    async def stop(self):
        """Stop event loop"""
        if not self._running:
            return

        self._running = False

        # Wait for current task to complete
        if self._task:
            try:
                await asyncio.wait_for(self._task, timeout=5.0)
            except asyncio.TimeoutError:
                self._logger.warning("Event bus stop timeout, cancelling task")
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass

        self._logger.info("Event bus stopped")

    async def _event_loop(self):
        """Event loop main function"""
        while self._running:
            try:
                # Wait for event with 1 second timeout
                priority, counter, event = await asyncio.wait_for(
                    self._event_queue.get(),
                    timeout=1.0
                )
                await self._dispatch(event)
            except asyncio.TimeoutError:
                # Continue loop on timeout
                continue
            except Exception as e:
                self._logger.error(f"Error in event loop: {e}", exc_info=True)

    async def _dispatch(self, event: Event):
        """Dispatch event to subscribers

        Args:
            event: Event object
        """
        handlers = self._subscribers.get(event.event_type, [])

        if not handlers:
            self._logger.debug(f"No handlers for event type: {event.event_type.value}")
            return

        # Execute all handlers concurrently
        tasks = [self._safe_handle(handler, event) for handler in handlers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Check for errors
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self._logger.error(
                    f"Handler {handlers[i].__name__} failed for event {event.event_type.value}: {result}",
                    exc_info=result
                )

    async def _safe_handle(self, handler: Callable, event: Event):
        """Safely execute handler

        Args:
            handler: Event handler function
            event: Event object
        """
        try:
            if asyncio.iscoroutinefunction(handler):
                await handler(event)
            else:
                # Execute synchronous function in thread pool
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, handler, event)
        except Exception as e:
            self._logger.error(f"Handler {handler.__name__} failed: {e}", exc_info=True)
            raise

    def get_queue_size(self) -> int:
        """Get current queue size"""
        return self._event_queue.qsize()

    def is_running(self) -> bool:
        """Check if event bus is running"""
        return self._running

    def get_subscribers_count(self, event_type: Optional[EventType] = None) -> int:
        """Get subscriber count

        Args:
            event_type: Event type, if None returns total count of all subscribers

        Returns:
            Subscriber count
        """
        if event_type is None:
            return sum(len(handlers) for handlers in self._subscribers.values())
        return len(self._subscribers.get(event_type, []))
