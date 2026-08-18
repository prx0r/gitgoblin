# GitGoblin API Reference Index

## Data Sources

| Source | Doc | Rate Limit | Auth | Cache TTL |
|--------|-----|------------|------|-----------|
| GitHub | [github.md](github.md) | 5,000 req/hr (auth) | PAT required | 5-60 min |
| OpenAlex | [openalex.md](openalex.md) | ~$1/day free | Optional | 30 min |
| arXiv | [arxiv.md](arxiv.md) | 3s delay between reqs | None | 24 hours |
| HackerNews | [hackernews.md](hackernews.md) | None documented | None | 30 min |
| ecosyste.ms | [ecosystems.md](ecosystems.md) | Unknown, be conservative | May need key | 1 hour |
| RSS/Atom | [rss.md](rss.md) | 2-5s per feed | None | varies |

## Rate Limiting Strategy

GitGoblin uses per-source rate limiting via `RateLimiter`:

```python
rate_limits = {
    "github": 3.0,       # 1 req per 3s
    "openalex": 0.5,     # 1 req per 0.5s
    "arxiv": 3.5,        # 1 req per 3.5s
    "hackernews": 1.0,   # 1 req per 1s
    "rss": 30.0,         # 1 req per 30s per feed
    "ecosystems": 5.0,   # 1 req per 5s
}
```

## Response Headers Monitored

### GitHub
- `x-ratelimit-remaining` — remaining requests
- `x-ratelimit-reset` — Unix timestamp when limit resets
- `retry-after` — seconds to wait (on 429)

### All Sources
- `Retry-After` — HTTP standard retry header
- `429 Too Many Requests` — rate limited
- `403 Forbidden` — may indicate rate limit or auth issue

## Error Handling

All collectors use `ResilientHTTP` which:
1. Retries on 403, 429, 500, 502, 503, 504
2. Respects `Retry-After` and `x-ratelimit-reset` headers
3. Uses exponential backoff with jitter
4. Caches successful responses to reduce API calls
5. Never silently converts errors to observations
