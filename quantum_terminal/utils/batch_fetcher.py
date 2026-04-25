"""Batch fetcher for efficient API requests with concurrency.

Provides functionality to:
- Batch multiple tickers into single API calls (50 tickers → 1 call)
- Handle partial failures gracefully
- Manage concurrency with semaphores
- Log batch operations with tracing
"""

import asyncio
from typing import Any, Callable, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Semaphore

from quantum_terminal.utils.logger import get_logger

logger = get_logger(__name__)


class BatchFetcher:
    """Fetches data in batches with concurrency control.

    Automatically groups requests to optimize API usage and manage
    rate limits through semaphore-based concurrency control.
    """

    DEFAULT_BATCH_SIZE = 50
    DEFAULT_MAX_WORKERS = 5

    def __init__(
        self,
        batch_size: int = DEFAULT_BATCH_SIZE,
        max_workers: int = DEFAULT_MAX_WORKERS,
    ):
        """Initialize batch fetcher.

        Args:
            batch_size: Maximum number of items per batch (default: 50).
            max_workers: Maximum concurrent workers (default: 5).

        Examples:
            >>> fetcher = BatchFetcher(batch_size=50, max_workers=5)
        """
        self.batch_size = batch_size
        self.max_workers = max_workers
        self.semaphore = Semaphore(max_workers)

        logger.info(
            f"BatchFetcher initialized: "
            f"batch_size={batch_size}, max_workers={max_workers}"
        )

    def batch_items(self, items: list[str], batch_size: Optional[int] = None) -> list[list[str]]:
        """Split items into batches.

        Args:
            items: List of items to batch.
            batch_size: Batch size override. Uses instance default if None.

        Returns:
            List of batches.

        Examples:
            >>> fetcher = BatchFetcher()
            >>> tickers = ["AAPL", "GOOGL", "MSFT", ...]
            >>> batches = fetcher.batch_items(tickers)
            >>> for batch in batches:
            ...     results.extend(fetch_batch(batch))
        """
        size = batch_size or self.batch_size

        if not items:
            return []

        batches = [items[i : i + size] for i in range(0, len(items), size)]
        logger.debug(f"Split {len(items)} items into {len(batches)} batches of ~{size}")

        return batches

    def fetch_batch(
        self,
        items: list[str],
        fetch_func: Callable[[list[str]], dict[str, Any]],
        timeout: float = 30.0,
    ) -> tuple[dict[str, Any], list[str]]:
        """Fetch a single batch with error handling.

        Args:
            items: Items to fetch.
            fetch_func: Function to call with batch (receives list, returns dict).
            timeout: Request timeout in seconds.

        Returns:
            Tuple of (results_dict, failed_items_list).

        Examples:
            >>> results, failed = fetcher.fetch_batch(["AAPL", "GOOGL"], yfinance.download)
        """
        failed = []
        results = {}

        try:
            logger.debug(f"Fetching batch of {len(items)} items")
            batch_results = fetch_func(items)

            if isinstance(batch_results, dict):
                results = batch_results
            else:
                logger.warning(f"Unexpected fetch_func return type: {type(batch_results)}")
                return {}, items

            # Check for partial failures
            for item in items:
                if item not in results or results[item] is None:
                    failed.append(item)

            if failed:
                logger.warning(f"Batch partial failure: {len(failed)}/{len(items)} items failed")
            else:
                logger.debug(f"Batch successful: {len(items)} items fetched")

            return results, failed

        except asyncio.TimeoutError:
            logger.error(f"Batch fetch timeout after {timeout}s for {len(items)} items")
            return {}, items

        except Exception as e:
            logger.error(f"Batch fetch error: {type(e).__name__}: {e}")
            return {}, items

    def fetch_all(
        self,
        items: list[str],
        fetch_func: Callable[[list[str]], dict[str, Any]],
        batch_size: Optional[int] = None,
        timeout: float = 30.0,
        retry_failed: bool = True,
    ) -> tuple[dict[str, Any], list[str]]:
        """Fetch all items in parallel batches.

        Args:
            items: Items to fetch.
            fetch_func: Function to call for each batch.
            batch_size: Batch size override.
            timeout: Request timeout per batch.
            retry_failed: Whether to retry failed items individually.

        Returns:
            Tuple of (all_results_dict, permanently_failed_items_list).

        Examples:
            >>> tickers = ["AAPL", "GOOGL", "MSFT", ...]
            >>> results, failed = fetcher.fetch_all(
            ...     tickers,
            ...     fetch_func=yfinance.download,
            ...     retry_failed=True
            ... )
        """
        batches = self.batch_items(items, batch_size)
        all_results = {}
        all_failed = []

        try:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {}

                for i, batch in enumerate(batches):
                    self.semaphore.acquire()
                    future = executor.submit(self._fetch_with_semaphore, batch, fetch_func, timeout)
                    futures[future] = (i, batch)

                # Collect results as they complete
                for future in as_completed(futures, timeout=timeout * len(batches)):
                    batch_idx, batch_items = futures[future]

                    try:
                        batch_results, batch_failed = future.result()
                        all_results.update(batch_results)
                        all_failed.extend(batch_failed)

                        logger.debug(
                            f"Batch {batch_idx} complete: "
                            f"{len(batch_results)} success, {len(batch_failed)} failed"
                        )

                    except Exception as e:
                        logger.error(f"Batch {batch_idx} failed: {e}")
                        all_failed.extend(batch_items)

            # Retry individual failed items if requested
            if retry_failed and all_failed:
                logger.info(f"Retrying {len(all_failed)} failed items individually")
                for item in all_failed:
                    try:
                        result = fetch_func([item])
                        if result and item in result:
                            all_results[item] = result[item]
                            all_failed.remove(item)
                            logger.debug(f"Retry successful for {item}")
                        else:
                            logger.debug(f"Retry failed for {item}")
                    except Exception as e:
                        logger.warning(f"Retry error for {item}: {e}")

            logger.info(
                f"Fetch all complete: {len(all_results)} success, {len(all_failed)} failed"
            )
            return all_results, all_failed

        except Exception as e:
            logger.error(f"Fetch all fatal error: {e}")
            return all_results, all_failed

    def _fetch_with_semaphore(
        self,
        batch: list[str],
        fetch_func: Callable,
        timeout: float,
    ) -> tuple[dict[str, Any], list[str]]:
        """Fetch batch with semaphore protection.

        Args:
            batch: Items to fetch.
            fetch_func: Fetch function.
            timeout: Request timeout.

        Returns:
            Tuple of (results, failed).
        """
        try:
            return self.fetch_batch(batch, fetch_func, timeout)
        finally:
            self.semaphore.release()


class AsyncBatchFetcher:
    """Asynchronous batch fetcher for async/await patterns.

    Provides async/await support for batch operations.
    """

    def __init__(
        self,
        batch_size: int = BatchFetcher.DEFAULT_BATCH_SIZE,
        max_concurrent: int = BatchFetcher.DEFAULT_MAX_WORKERS,
    ):
        """Initialize async batch fetcher.

        Args:
            batch_size: Maximum items per batch.
            max_concurrent: Maximum concurrent fetches.
        """
        self.batch_size = batch_size
        self.semaphore = asyncio.Semaphore(max_concurrent)
        logger.info(f"AsyncBatchFetcher initialized: {batch_size} items, {max_concurrent} concurrent")

    def batch_items(self, items: list[str]) -> list[list[str]]:
        """Split items into batches.

        Args:
            items: Items to batch.

        Returns:
            List of batches.
        """
        return [items[i : i + self.batch_size] for i in range(0, len(items), self.batch_size)]

    async def fetch_batch(
        self,
        batch: list[str],
        fetch_func: Callable,
        timeout: float = 30.0,
    ) -> tuple[dict[str, Any], list[str]]:
        """Fetch batch asynchronously.

        Args:
            batch: Items to fetch.
            fetch_func: Async fetch function.
            timeout: Request timeout.

        Returns:
            Tuple of (results, failed).
        """
        try:
            async with self.semaphore:
                results = await asyncio.wait_for(fetch_func(batch), timeout=timeout)
                return results, []
        except asyncio.TimeoutError:
            logger.error(f"Async batch timeout after {timeout}s")
            return {}, batch
        except Exception as e:
            logger.error(f"Async batch error: {e}")
            return {}, batch

    async def fetch_all(
        self,
        items: list[str],
        fetch_func: Callable,
        timeout: float = 30.0,
    ) -> tuple[dict[str, Any], list[str]]:
        """Fetch all items asynchronously in batches.

        Args:
            items: Items to fetch.
            fetch_func: Async fetch function.
            timeout: Request timeout per batch.

        Returns:
            Tuple of (all_results, failed_items).

        Examples:
            >>> async def fetch_quotes(tickers):
            ...     # Async implementation
            ...     pass
            >>> fetcher = AsyncBatchFetcher()
            >>> results, failed = await fetcher.fetch_all(
            ...     ["AAPL", "GOOGL"],
            ...     fetch_quotes
            ... )
        """
        batches = self.batch_items(items)
        tasks = [self.fetch_batch(batch, fetch_func, timeout) for batch in batches]

        results = {}
        failed = []

        try:
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            for batch_result in batch_results:
                if isinstance(batch_result, Exception):
                    logger.error(f"Batch error: {batch_result}")
                    failed.extend(items)
                else:
                    batch_results_dict, batch_failed = batch_result
                    results.update(batch_results_dict)
                    failed.extend(batch_failed)

            logger.info(f"Async fetch complete: {len(results)} success, {len(failed)} failed")
            return results, failed

        except Exception as e:
            logger.error(f"Async fetch all error: {e}")
            return results, items
