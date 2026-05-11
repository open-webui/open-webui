"""
Async Utilities

Shared utilities for async operations including:
- Concurrent execution with semaphore control
- Parallel batch processing
- Rate-limited async operations
"""

import asyncio
import logging
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    List,
    Optional,
    Tuple,
    TypeVar,
    Union,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")
R = TypeVar("R")


async def gather_with_concurrency(
    tasks: List[Awaitable[T]],
    max_concurrent: int = 10,
    return_exceptions: bool = True,
) -> List[Union[T, Exception]]:
    """
    Execute async tasks with controlled concurrency.

    This is a common pattern for limiting parallel operations to prevent
    resource exhaustion (memory, connections, API rate limits).

    Args:
        tasks: List of awaitable tasks to execute
        max_concurrent: Maximum number of concurrent tasks (default: 10)
        return_exceptions: If True, exceptions are returned in results.
                          If False, first exception is raised.

    Returns:
        List of results in the same order as input tasks.
        Failed tasks return Exception objects if return_exceptions=True.

    Example:
        >>> async def fetch(url):
        ...     async with aiohttp.ClientSession() as session:
        ...         async with session.get(url) as resp:
        ...             return await resp.text()
        >>> urls = ["http://example.com"] * 100
        >>> tasks = [fetch(url) for url in urls]
        >>> results = await gather_with_concurrency(tasks, max_concurrent=10)
    """
    if not tasks:
        return []

    if max_concurrent <= 0:
        max_concurrent = len(tasks)  # Unlimited

    semaphore = asyncio.Semaphore(max_concurrent)

    async def limited_task(task: Awaitable[T]) -> T:
        async with semaphore:
            return await task

    limited_tasks = [limited_task(task) for task in tasks]
    return await asyncio.gather(*limited_tasks, return_exceptions=return_exceptions)


async def process_batch_parallel(
    items: List[T],
    processor: Callable[[T], Awaitable[R]],
    max_concurrent: int = 5,
    on_progress: Optional[Callable[[int, int], Awaitable[None]]] = None,
    yield_interval: int = 0,
    yield_delay: float = 0.0,
) -> Tuple[List[R], List[Dict[str, Any]]]:
    """
    Process a batch of items in parallel with controlled concurrency.

    Provides a clean abstraction for parallel processing with:
    - Semaphore-based concurrency control
    - Error isolation (one failure doesn't stop others)
    - Progress callbacks
    - Periodic yields to keep event loop responsive

    Args:
        items: List of items to process
        processor: Async function to process each item
        max_concurrent: Maximum parallel processors (default: 5)
        on_progress: Optional async callback(processed_count, total_count)
        yield_interval: Yield to event loop every N items (0 = disabled)
        yield_delay: Delay in seconds when yielding (default: 0)

    Returns:
        Tuple of (successful_results, errors)
        - successful_results: List of successful processor outputs
        - errors: List of dicts with {index, item, error}

    Example:
        >>> async def embed_text(text):
        ...     return await embedding_service.embed(text)
        >>> texts = ["Hello", "World", "Test"]
        >>> results, errors = await process_batch_parallel(
        ...     items=texts,
        ...     processor=embed_text,
        ...     max_concurrent=5
        ... )
    """
    if not items:
        return [], []

    successful_results: List[R] = []
    errors: List[Dict[str, Any]] = []
    processed_count = 0
    total_count = len(items)

    semaphore = asyncio.Semaphore(max_concurrent)

    async def process_with_semaphore(index: int, item: T) -> Tuple[int, Optional[R], Optional[Exception]]:
        async with semaphore:
            try:
                result = await processor(item)
                return index, result, None
            except Exception as e:
                return index, None, e

    # Create all tasks
    tasks = [process_with_semaphore(i, item) for i, item in enumerate(items)]

    # Process with gather (maintains order via index)
    results = await asyncio.gather(*tasks, return_exceptions=False)

    # Sort by index and collect results
    for index, result, error in sorted(results, key=lambda x: x[0]):
        processed_count += 1

        if error:
            errors.append(
                {
                    "index": index,
                    "item": items[index],
                    "error": error,
                }
            )
            logger.debug(f"Item {index} failed: {error}")
        else:
            successful_results.append(result)

        # Progress callback
        if on_progress:
            await on_progress(processed_count, total_count)

        # Periodic yield to event loop
        if yield_interval > 0 and processed_count % yield_interval == 0:
            await asyncio.sleep(yield_delay)

    return successful_results, errors


async def retry_async(
    func: Callable[[], Awaitable[T]],
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exponential: bool = True,
    retryable_exceptions: Tuple[type, ...] = (Exception,),
) -> T:
    """
    Retry an async function with exponential backoff.

    Args:
        func: Async function to retry (takes no arguments)
        max_retries: Maximum retry attempts (default: 3)
        base_delay: Initial delay in seconds (default: 1.0)
        max_delay: Maximum delay cap in seconds (default: 30.0)
        exponential: Use exponential backoff (default: True)
        retryable_exceptions: Tuple of exception types to retry on

    Returns:
        Result of successful function call

    Raises:
        Last exception if all retries fail

    Example:
        >>> async def flaky_api_call():
        ...     return await api.call()
        >>> result = await retry_async(
        ...     flaky_api_call,
        ...     max_retries=3,
        ...     retryable_exceptions=(aiohttp.ClientError,)
        ... )
    """
    import random

    last_exception = None

    for attempt in range(max_retries):
        try:
            return await func()
        except retryable_exceptions as e:
            last_exception = e

            if attempt < max_retries - 1:
                if exponential:
                    delay = min(max_delay, base_delay * (2**attempt) + random.uniform(0, 1))
                else:
                    delay = base_delay

                logger.debug(f"Retry {attempt + 1}/{max_retries} after {delay:.1f}s: {e}")
                await asyncio.sleep(delay)
            else:
                logger.warning(f"All {max_retries} retries failed: {e}")

    raise last_exception
