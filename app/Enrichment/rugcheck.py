# app/Enrichment/rugcheck.py
import asyncio
import time
import logging
from typing import List, Dict, Optional, Any, Tuple
from pathlib import Path
from app.config import RUGCHECK_BASE
import httpx

logger = logging.getLogger(__name__)




class RugCheckError(Exception):
    pass


class RugCheckClient:
    """
    Async client for RugCheck token report endpoint with:
      - Global rate limiting (requests_per_second)
      - Batch fetching (serial by default to respect rate limit)
      - Simple TTL cache to avoid re-requesting recently fetched reports

    Usage:
        client = RugCheckClient(requests_per_second=1, cache_ttl=300)
        reports = await client.batch_fetch_reports(["MintAddr1", "MintAddr2"])
    """

    def __init__(
        self,
        base_url: str = RUGCHECK_BASE,
        requests_per_second: float = 1.0,
        cache_ttl: int = 300,
        timeout: float = 10.0,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
    ):
        """
        Args:
            base_url: base URL for RugCheck (no trailing slash)
            requests_per_second: allowed average rate (1.0 => 1 req / sec)
            cache_ttl: seconds to keep cached reports (simple in-memory cache)
            timeout: per-request timeout in seconds
            max_retries: number of attempts on transient failures
            backoff_factor: base for exponential backoff (delay = backoff_factor * 2**attempt)
        """
        if base_url.endswith("/"):
            base_url = base_url[:-1]
        self.base_url = base_url
        self.requests_per_second = float(requests_per_second) if requests_per_second > 0 else 1.0
        self.cache_ttl = int(cache_ttl)
        self.timeout = timeout
        self.max_retries = int(max_retries)
        self.backoff_factor = float(backoff_factor)

        # rate control
        self._last_request_ts = 0.0
        self._rate_lock = asyncio.Lock()

        # in-memory cache: address -> (fetched_at_ts, response_dict)
        self._cache: Dict[str, Tuple[float, Any]] = {}

        # client session — created lazily in async context
        self._client: Optional[httpx.AsyncClient] = None

    async def _ensure_client(self):
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout, limits=httpx.Limits(max_keepalive_connections=10))
    
    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _rate_wait(self):
        """
        Global rate limiter: ensures at least spacing based on requests_per_second
        Called before each external request.
        """
        async with self._rate_lock:
            now = time.monotonic()
            min_interval = 1.0 / self.requests_per_second
            elapsed = now - self._last_request_ts
            if elapsed < min_interval:
                wait_for = (min_interval - elapsed)
                logger.debug(f"RugCheck rate limiter sleeping for {wait_for:.3f}s")
                await asyncio.sleep(wait_for)
            # update timestamp to current time after sleeping
            self._last_request_ts = time.monotonic()

    def _is_cached(self, address: str) -> bool:
        if address not in self._cache:
            return False
        ts, _ = self._cache[address]
        if (time.time() - ts) > self.cache_ttl:
            # expired
            del self._cache[address]
            return False
        return True

    def _get_cached(self, address: str) -> Any:
        return self._cache[address][1]

    def _set_cache(self, address: str, payload: Any):
        self._cache[address] = (time.time(), payload)

    async def fetch_report(self, address: str) -> Dict[str, Any]:
        """
        Fetch RugCheck token report for a single mint address.
        Uses retries and respects rate limit. Saves response in cache.

        Returns:
            report_json (dict) on success

        Raises:
            RugCheckError on non-recoverable failure
        """
        # Normalize address string
        addr = address.strip()
        # Return cached copy if available
        if self._is_cached(addr):
            logger.debug(f"RugCheck cache hit for {addr}")
            return self._get_cached(addr)

        await self._ensure_client()

        # Attempt with retries
        last_exc: Optional[Exception] = None
        for attempt in range(self.max_retries):
            try:
                await self._rate_wait()
                url = f"{self.base_url}/tokens/{addr}/report"
                logger.debug(f"RugCheck GET {url} (attempt {attempt+1})")
                resp = await self._client.get(url)
                # Accept 200 and 404 (404 -> return a structured empty report)
                if resp.status_code == 200:
                    data = resp.json()
                    # cache and return
                    self._set_cache(addr, data)
                    return data
                elif resp.status_code == 404:
                    logger.warning(f"RugCheck report not found for {addr} (404). Caching empty result.")
                    empty = {"found": False, "address": addr}
                    self._set_cache(addr, empty)
                    return empty
                else:
                    # treat other 4xx/5xx as retriable up to retry count (but log)
                    logger.warning(
                        f"RugCheck returned status {resp.status_code} for {addr}: {resp.text[:200]}"
                    )
                    last_exc = RugCheckError(f"HTTP {resp.status_code}: {resp.text}")
            except (httpx.RequestError, httpx.HTTPStatusError) as e:
                last_exc = e
                logger.warning(f"RugCheck request error for {addr} (attempt {attempt+1}): {e}")
            # exponential backoff before next attempt
            backoff = self.backoff_factor * (2 ** attempt)
            await asyncio.sleep(backoff)

        # If we get here, we failed all retries
        logger.error(f"RugCheck: failed to fetch report for {addr} after {self.max_retries} attempts")
        raise RugCheckError(f"Failed to fetch RugCheck report for {addr}") from last_exc

    async def batch_fetch_reports(
        self,
        addresses: List[str],
        concurrency: int = 1,
        progress_callback: Optional[Any] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Fetch reports for multiple addresses. Respects global rate limit.
        Default concurrency=1 (serial) to easily respect 1 req/sec policy.
        If you set concurrency > 1, the global rate limiter still spaces calls appropriately,
        but you may get small concurrency benefits if you expect some requests to be served from cache.

        Args:
            addresses: list of mint addresses (strings)
            concurrency: number of concurrent worker tasks (default 1)
            progress_callback: optional callable(index, total, addr) for progress reporting

        Returns:
            mapping address -> report dict (or {"error": "..."} on failure)
        """
        # normalize and unique addresses preserving order
        seen = set()
        unique_addresses = []
        for a in addresses:
            if not a:
                continue
            a_norm = a.strip()
            if a_norm not in seen:
                seen.add(a_norm)
                unique_addresses.append(a_norm)

        total = len(unique_addresses)
        results: Dict[str, Dict[str, Any]] = {}

        # If cache contains everything, return early
        all_cached = all(self._is_cached(addr) for addr in unique_addresses)
        if all_cached:
            for addr in unique_addresses:
                results[addr] = self._get_cached(addr)
            return results

        # Worker coroutine that pulls from queue
        queue: asyncio.Queue = asyncio.Queue()
        for addr in unique_addresses:
            queue.put_nowait(addr)

        async def worker(worker_id: int):
            while not queue.empty():
                addr = await queue.get()
                try:
                    if self._is_cached(addr):
                        results[addr] = self._get_cached(addr)
                    else:
                        report = await self.fetch_report(addr)
                        results[addr] = report
                except Exception as e:
                    logger.exception(f"RugCheck worker {worker_id} failed for {addr}: {e}")
                    results[addr] = {"error": str(e)}
                finally:
                    if progress_callback:
                        try:
                            progress_callback(len(results), total, addr)
                        except Exception:
                            pass
                    queue.task_done()

        # Launch workers (default concurrency 1 ensures serial execution respecting rate)
        workers = [asyncio.create_task(worker(i)) for i in range(max(1, int(concurrency)))]
        await queue.join()
        # cancel leftover tasks
        for w in workers:
            w.cancel()
        # wait for workers to finish cancellation
        await asyncio.gather(*workers, return_exceptions=True)

        return results

    # Optional convenience method to clear cache (for testing or forced refresh)
    def clear_cache(self):
        self._cache.clear()
