"""Async utilities for parallel processing optimization."""

import asyncio
import functools
import time
from typing import Any, Callable, List, Optional, TypeVar
from shared.utils.logging import setup_logging

logger = setup_logging(__name__)

T = TypeVar('T')


class RateLimiter:
    """Token bucket rate limiter for API calls."""

    def __init__(self, max_requests: int, time_window: float):
        """
        Initialize rate limiter.

        Args:
            max_requests: Maximum requests allowed in time window
            time_window: Time window in seconds
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.tokens = max_requests
        self.last_update = time.time()
        self._lock = asyncio.Lock()

    async def acquire(self):
        """Acquire a token, waiting if necessary."""
        async with self._lock:
            now = time.time()
            elapsed = now - self.last_update

            # Refill tokens based on elapsed time
            self.tokens = min(
                self.max_requests,
                self.tokens + (elapsed * self.max_requests / self.time_window)
            )
            self.last_update = now

            # Wait if no tokens available
            if self.tokens < 1:
                wait_time = (1 - self.tokens) * self.time_window / self.max_requests
                logger.debug(f"Rate limit reached, waiting {wait_time:.2f}s")
                await asyncio.sleep(wait_time)
                self.tokens = 1

            self.tokens -= 1


async def retry_with_backoff(
    func: Callable,
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,)
) -> Any:
    """
    Retry a function with exponential backoff.

    Args:
        func: Function to retry
        max_retries: Maximum number of retries
        initial_delay: Initial delay in seconds
        backoff_factor: Multiplier for delay after each retry
        exceptions: Tuple of exceptions to catch and retry

    Returns:
        Result from successful function call

    Raises:
        Last exception if all retries failed
    """
    delay = initial_delay
    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            # Call the function
            result = func()
            # Check if result is a coroutine and await it
            if asyncio.iscoroutine(result):
                return await result
            else:
                return result
        except exceptions as e:
            last_exception = e
            if attempt == max_retries:
                logger.error(f"All {max_retries} retries failed: {str(e)}")
                raise

            logger.warning(f"Attempt {attempt + 1} failed: {str(e)}, retrying in {delay:.2f}s")
            await asyncio.sleep(delay)
            delay *= backoff_factor

    raise last_exception


async def run_with_timeout(
    coro,
    timeout: float,
    task_name: str = "Task"
) -> Any:
    """
    Run a coroutine with a timeout.

    Args:
        coro: Coroutine to run
        timeout: Timeout in seconds
        task_name: Name for logging

    Returns:
        Result from coroutine

    Raises:
        asyncio.TimeoutError: If timeout is exceeded
    """
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        logger.error(f"{task_name} timed out after {timeout}s")
        raise


async def gather_with_progress(
    tasks: List,
    task_names: Optional[List[str]] = None,
    return_exceptions: bool = True
) -> List[Any]:
    """
    Run multiple tasks in parallel with progress logging.

    Args:
        tasks: List of coroutines/tasks to run
        task_names: Optional names for logging
        return_exceptions: Whether to return exceptions instead of raising

    Returns:
        List of results
    """
    if not task_names:
        task_names = [f"Task {i+1}" for i in range(len(tasks))]

    logger.info(f"Starting {len(tasks)} tasks in parallel: {', '.join(task_names)}")

    # Wrap tasks with progress tracking
    pending_tasks = []
    for task, name in zip(tasks, task_names):
        pending_tasks.append(_track_task_progress(task, name))

    results = await asyncio.gather(*pending_tasks, return_exceptions=return_exceptions)

    # Log summary
    success_count = sum(1 for r in results if not isinstance(r, Exception))
    logger.info(f"Parallel execution complete: {success_count}/{len(tasks)} tasks succeeded")

    return results


async def _track_task_progress(task, name: str) -> Any:
    """Track and log progress of a single task."""
    start_time = time.time()
    logger.debug(f"[{name}] Started")

    try:
        result = await task
        duration = time.time() - start_time
        logger.info(f"[{name}] Completed in {duration:.2f}s")
        return result
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"[{name}] Failed after {duration:.2f}s: {str(e)}")
        raise


async def run_in_batches(
    items: List[T],
    batch_size: int,
    max_concurrent: int,
    process_func: Callable[[List[T]], Any],
    batch_name: str = "Batch"
) -> List[Any]:
    """
    Process items in batches with controlled concurrency.

    Args:
        items: Items to process
        batch_size: Size of each batch
        max_concurrent: Maximum concurrent batches
        process_func: Function to process each batch
        batch_name: Name for logging

    Returns:
        List of results from all batches
    """
    batches = [items[i:i + batch_size] for i in range(0, len(items), batch_size)]
    logger.info(f"Processing {len(items)} items in {len(batches)} batches (max {max_concurrent} concurrent)")

    all_results = []

    # Process batches in groups to limit concurrency
    for group_start in range(0, len(batches), max_concurrent):
        group_end = min(group_start + max_concurrent, len(batches))
        batch_group = batches[group_start:group_end]

        logger.info(f"Processing batch group {group_start+1}-{group_end} of {len(batches)}")

        # Create tasks for this group
        tasks = [process_func(batch) for batch in batch_group]

        # Execute group in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Collect successful results
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"{batch_name} {group_start + i + 1} failed: {str(result)}")
            else:
                all_results.append(result)

    logger.info(f"Batch processing complete: {len(all_results)}/{len(batches)} batches succeeded")
    return all_results


class ProgressTracker:
    """Track progress of multi-step operations."""

    def __init__(self, total_steps: int, operation_name: str):
        """
        Initialize progress tracker.

        Args:
            total_steps: Total number of steps
            operation_name: Name of the operation
        """
        self.total_steps = total_steps
        self.operation_name = operation_name
        self.current_step = 0
        self.start_time = time.time()
        self._lock = asyncio.Lock()

    async def increment(self, step_name: str = ""):
        """Increment progress and log."""
        async with self._lock:
            self.current_step += 1
            elapsed = time.time() - self.start_time
            progress_pct = (self.current_step / self.total_steps) * 100

            log_msg = f"[{self.operation_name}] Progress: {self.current_step}/{self.total_steps} ({progress_pct:.1f}%)"
            if step_name:
                log_msg += f" - {step_name}"
            log_msg += f" | Elapsed: {elapsed:.1f}s"

            logger.info(log_msg)

    async def complete(self):
        """Mark operation as complete."""
        elapsed = time.time() - self.start_time
        logger.info(f"[{self.operation_name}] Complete: {self.total_steps} steps in {elapsed:.2f}s")
