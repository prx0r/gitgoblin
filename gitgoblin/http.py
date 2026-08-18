from __future__ import annotations

import email.utils
import json
import random
import time
from pathlib import Path
from typing import Any, Iterable

import httpx

from .hashing import sha256_json


class HTTPError(RuntimeError):
    pass


class RateLimiter:
    """Per-source rate limiter with token bucket algorithm."""

    def __init__(self) -> None:
        self._last_call: dict[str, float] = {}
        self._min_interval: dict[str, float] = {}

    def configure(self, source: str, min_interval: float) -> None:
        self._min_interval[source] = min_interval

    def wait(self, source: str) -> None:
        if source not in self._min_interval:
            return
        now = time.time()
        last = self._last_call.get(source, 0)
        wait_time = self._min_interval[source] - (now - last)
        if wait_time > 0:
            time.sleep(wait_time)
        self._last_call[source] = time.time()


class ResilientHTTP:
    """HTTP client with bounded retries, Retry-After handling, disk GET cache, and per-source rate limiting.

    The cache is deliberately conservative: it is only used when callers pass cache_ttl_seconds.
    Network errors never silently become successful observations.
    """

    def __init__(
        self,
        *,
        user_agent: str,
        timeout: float = 20.0,
        max_retries: int = 3,
        cache_dir: str | Path = "data/http_cache",
        transport: httpx.BaseTransport | None = None,
        rate_limiter: RateLimiter | None = None,
        rate_limits: dict[str, float] | None = None,
    ) -> None:
        self.max_retries = max_retries
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.rate_limiter = rate_limiter or RateLimiter()
        if rate_limits:
            for source, interval in rate_limits.items():
                self.rate_limiter.configure(source, interval)
        self.client = httpx.Client(
            timeout=timeout,
            headers={"User-Agent": user_agent, "Accept": "application/json"},
            follow_redirects=True,
            transport=transport,
        )

    def close(self) -> None:
        self.client.close()

    def _cache_path(self, url: str, params: dict[str, Any] | None) -> Path:
        key = sha256_json({"url": url, "params": params or {}})
        return self.cache_dir / f"{key}.json"

    def get_json(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        cache_ttl_seconds: float | None = None,
        source: str | None = None,
    ) -> Any:
        if source:
            self.rate_limiter.wait(source)
        cache_path = self._cache_path(url, params)
        if cache_ttl_seconds is not None and cache_path.exists():
            age = time.time() - cache_path.stat().st_mtime
            if age <= cache_ttl_seconds:
                return json.loads(cache_path.read_text(encoding="utf-8"))["body"]

        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                response = self.client.get(url, params=params, headers=headers)
                if response.status_code in {403, 429, 500, 502, 503, 504}:
                    if attempt >= self.max_retries:
                        raise HTTPError(f"GET {response.url} failed: {response.status_code} {response.text[:300]}")
                    self._wait(response, attempt)
                    continue
                response.raise_for_status()
                body = response.json()
                if cache_ttl_seconds is not None:
                    cache_path.write_text(
                        json.dumps({"fetched_at": time.time(), "body": body}, default=str), encoding="utf-8"
                    )
                return body
            except (httpx.HTTPError, ValueError, HTTPError) as exc:
                last_error = exc
                if attempt >= self.max_retries:
                    break
                time.sleep(min(8.0, (2**attempt) + random.random() * 0.2))
        raise HTTPError(str(last_error) if last_error else f"GET failed: {url}")

    def get_text(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        source: str | None = None,
    ) -> str:
        if source:
            self.rate_limiter.wait(source)
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                response = self.client.get(url, params=params, headers=headers)
                if response.status_code in {403, 429, 500, 502, 503, 504}:
                    if attempt >= self.max_retries:
                        raise HTTPError(f"GET {response.url} failed: {response.status_code}")
                    self._wait(response, attempt)
                    continue
                response.raise_for_status()
                return response.text
            except (httpx.HTTPError, HTTPError) as exc:
                last_error = exc
                if attempt >= self.max_retries:
                    break
                time.sleep(min(8.0, (2**attempt) + random.random() * 0.2))
        raise HTTPError(str(last_error) if last_error else f"GET failed: {url}")

    def paginate_json(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        pages: int = 1,
        page_size: int = 100,
        source: str | None = None,
    ) -> Iterable[Any]:
        if source:
            self.rate_limiter.wait(source)
        params = dict(params or {})
        params.setdefault("per_page", page_size)
        for page in range(1, pages + 1):
            params["page"] = page
            body = self.get_json(url, params=params, headers=headers, source=source)
            if not isinstance(body, list):
                raise HTTPError(f"Expected list from {url}, got {type(body).__name__}")
            for item in body:
                yield item
            if len(body) < page_size:
                break

    @staticmethod
    def _wait(response: httpx.Response, attempt: int) -> None:
        retry_after = response.headers.get("retry-after")
        seconds: float | None = None
        if retry_after:
            try:
                seconds = float(retry_after)
            except ValueError:
                try:
                    when = email.utils.parsedate_to_datetime(retry_after).timestamp()
                    seconds = max(0.0, when - time.time())
                except Exception:
                    seconds = None
        if seconds is None and response.headers.get("x-ratelimit-remaining") == "0":
            try:
                seconds = max(0.0, float(response.headers["x-ratelimit-reset"]) - time.time())
            except Exception:
                seconds = None
        if seconds is None:
            seconds = min(30.0, 2**attempt)
        time.sleep(min(seconds, 60.0))
