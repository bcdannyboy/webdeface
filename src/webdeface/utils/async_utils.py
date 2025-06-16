"""Async utility functions and helpers."""

import asyncio
import logging
from collections.abc import Awaitable, Coroutine
from typing import Any, Optional, TypeVar

from .types import AsyncTimeoutError

logger = logging.getLogger(__name__)

T = TypeVar("T")


async def run_with_timeout(
    coro: Awaitable[T], timeout: float, timeout_message: Optional[str] = None
) -> T:
    """Run a coroutine with a timeout."""
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError as e:
        msg = timeout_message or f"Operation timed out after {timeout}s"
        logger.warning(msg)
        raise AsyncTimeoutError(msg) from e


async def gather_with_limit(
    *coroutines: Awaitable[T], limit: int = 10, return_exceptions: bool = False
) -> list[Any]:
    """Run coroutines concurrently with a concurrency limit."""
    semaphore = asyncio.Semaphore(limit)

    async def limited_coro(coro: Awaitable[T]) -> T:
        async with semaphore:
            return await coro

    # Wrap all coroutines with the semaphore
    limited_coroutines = [limited_coro(coro) for coro in coroutines]

    return await asyncio.gather(
        *limited_coroutines, return_exceptions=return_exceptions
    )


async def retry_async(
    coro_func: Coroutine[Any, Any, T],
    max_retries: int = 3,
    delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,),
) -> T:
    """Retry an async function with exponential backoff."""
    last_exception = None
    current_delay = delay

    for attempt in range(max_retries + 1):
        try:
            return await coro_func
        except exceptions as e:
            last_exception = e

            if attempt == max_retries:
                logger.error(f"All {max_retries + 1} attempts failed")
                break

            logger.warning(
                f"Attempt {attempt + 1} failed, retrying in {current_delay}s: {str(e)}"
            )
            await asyncio.sleep(current_delay)
            current_delay *= backoff_factor

    # If we get here, all retries failed
    raise last_exception


class AsyncContextManager:
    """Base class for async context managers."""

    async def __aenter__(self):
        await self.setup()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.cleanup()

    async def setup(self) -> None:
        """Setup the context manager."""
        pass

    async def cleanup(self) -> None:
        """Cleanup the context manager."""
        pass


class AsyncBatch:
    """Process items in batches asynchronously."""

    def __init__(self, batch_size: int = 10, delay_between_batches: float = 0.1):
        self.batch_size = batch_size
        self.delay_between_batches = delay_between_batches

    async def process(
        self, items: list[Any], processor: Coroutine[Any, Any, T]
    ) -> list[T]:
        """Process items in batches."""
        results = []

        for i in range(0, len(items), self.batch_size):
            batch = items[i : i + self.batch_size]
            batch_coroutines = [processor(item) for item in batch]

            batch_results = await asyncio.gather(
                *batch_coroutines, return_exceptions=True
            )
            results.extend(batch_results)

            # Delay between batches to avoid overwhelming resources
            if i + self.batch_size < len(items):
                await asyncio.sleep(self.delay_between_batches)

        return results


async def safe_gather(*coroutines: Awaitable[T]) -> list[Optional[T]]:
    """Gather coroutines safely, returning None for failed ones."""
    results = await asyncio.gather(*coroutines, return_exceptions=True)

    safe_results = []
    for result in results:
        if isinstance(result, Exception):
            logger.warning(f"Coroutine failed: {str(result)}")
            safe_results.append(None)
        else:
            safe_results.append(result)

    return safe_results


class PeriodicTask:
    """Run a task periodically."""

    def __init__(
        self,
        coro_func: Coroutine[Any, Any, None],
        interval: float,
        start_immediately: bool = True,
    ):
        self.coro_func = coro_func
        self.interval = interval
        self.start_immediately = start_immediately
        self._task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()

    async def start(self) -> None:
        """Start the periodic task."""
        if self._task and not self._task.done():
            return

        self._stop_event.clear()
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        """Stop the periodic task."""
        self._stop_event.set()

        if self._task:
            await self._task

    async def _run(self) -> None:
        """Run the periodic task."""
        if self.start_immediately:
            try:
                await self.coro_func
            except Exception as e:
                logger.error(f"Periodic task failed: {str(e)}")

        while not self._stop_event.is_set():
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self.interval)
                # If we reach here, stop was requested
                break
            except asyncio.TimeoutError:
                # Timeout is expected - time to run the task
                try:
                    await self.coro_func
                except Exception as e:
                    logger.error(f"Periodic task failed: {str(e)}")


def create_task_with_error_handling(
    coro: Coroutine[Any, Any, T], task_name: str = "unnamed_task"
) -> asyncio.Task[T]:
    """Create a task with automatic error handling."""

    async def wrapped_coro() -> T:
        try:
            return await coro
        except Exception as e:
            logger.error(f"Task '{task_name}' failed: {str(e)}", exc_info=True)
            raise

    task = asyncio.create_task(wrapped_coro())
    task.set_name(task_name)
    return task
